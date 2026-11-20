"""Tests that both handlers connect the fpac-soil-mcp server and build the agent from it.

No network: McpServer, WorkspaceClient, the health check, create_agent, and Runner are
all patched. The decorated handlers return a coroutine or async generator, so they are
driven with asyncio.run (the app has no pytest-asyncio).
"""

import asyncio
import json
import logging
from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock, MagicMock

import mlflow
import pytest
from agent_server import agent as agent_module
from agent_server import config as config_module
from agents.exceptions import UserError
from agents.mcp.server import MCPServerStreamableHttp
from databricks_openai.agents import McpServer
from mcp.shared.exceptions import McpError
from mcp.types import CallToolResult, ErrorData, TextContent
from mlflow.types.responses import ResponsesAgentRequest

DEFAULT_URL = "https://mcp-fpac-soil-7474654188777746.aws.databricksapps.com/mcp"


def _request(content: str = "hi") -> ResponsesAgentRequest:
    return ResponsesAgentRequest(input=[{"role": "user", "content": content}])


async def _empty_events():
    return
    yield  # pragma: no cover - makes this an async generator


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    for name in (
        "AGENT_MODEL",
        "FPAC_MCP_URL",
        "FPAC_MCP_APP",
        "FPAC_MCP_TIMEOUT_SECONDS",
        "FPAC_LOCAL_DEV",
        "LOCAL_LLM_BASE_URL",
        "FPAC_LOCAL_MLFLOW_TRACING",
        "FPAC_LOCAL_MLFLOW_DIR",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(config_module, "_RESOLVED_MCP_URLS", {})


@pytest.fixture
def patched(monkeypatch, valid_site_assessment_criteria_resource):
    """Patch everything the handlers call; returns the mocks."""
    server = MagicMock(name="server")
    server.read_resource = AsyncMock(return_value=valid_site_assessment_criteria_resource)
    server.call_tool = AsyncMock(return_value=SimpleNamespace(isError=False))
    mocks = SimpleNamespace(
        server=server,
        workspace_client=MagicMock(name="WorkspaceClient"),
        init=MagicMock(return_value=server),
        connect=AsyncMock(return_value=([server], [])),
        configure_openai_client=MagicMock(name="configure_openai_client"),
        create_agent=MagicMock(return_value=MagicMock(name="agent")),
        run=AsyncMock(return_value=SimpleNamespace(new_items=[])),
        run_streamed=MagicMock(return_value=SimpleNamespace(stream_events=_empty_events)),
    )
    monkeypatch.setattr(agent_module, "WorkspaceClient", mocks.workspace_client)
    monkeypatch.setattr(agent_module, "init_fpac_mcp_server", mocks.init)
    monkeypatch.setattr(agent_module, "connect_healthy_mcp_servers", mocks.connect)
    monkeypatch.setattr(agent_module, "configure_openai_client", mocks.configure_openai_client)
    monkeypatch.setattr(agent_module, "create_agent", mocks.create_agent)
    monkeypatch.setattr(agent_module.Runner, "run", mocks.run)
    monkeypatch.setattr(agent_module.Runner, "run_streamed", mocks.run_streamed)
    return mocks


def _run_invoke(request=None):
    return asyncio.run(agent_module.invoke_handler(request or _request()))


def _run_stream(request=None):
    async def collect():
        return [event async for event in agent_module.stream_handler(request or _request())]

    return asyncio.run(collect())


def test_init_fpac_mcp_server_defaults(monkeypatch):
    mcp_server = MagicMock(name="FpacMcpServer")
    monkeypatch.setattr(agent_module, "FpacMcpServer", mcp_server)
    ws = MagicMock(name="ws")
    result = agent_module.init_fpac_mcp_server(ws)
    assert result is mcp_server.return_value
    mcp_server.assert_called_once_with(
        url=DEFAULT_URL, name="fpac-soil-mcp", workspace_client=ws, timeout=180.0
    )


def test_init_fpac_mcp_server_env_overrides(monkeypatch):
    mcp_server = MagicMock(name="FpacMcpServer")
    monkeypatch.setattr(agent_module, "FpacMcpServer", mcp_server)
    monkeypatch.setenv("FPAC_MCP_URL", "https://example.com/mcp")
    monkeypatch.setenv("FPAC_MCP_TIMEOUT_SECONDS", "30")
    ws = MagicMock(name="ws")
    agent_module.init_fpac_mcp_server(ws)
    mcp_server.assert_called_once_with(
        url="https://example.com/mcp", name="fpac-soil-mcp", workspace_client=ws, timeout=30.0
    )


MAP_META_KEY = "gov.usda.fpac-soil/map"
TRACE_MARKER = "R6-TRACE-MARKER"


def _meta_result() -> CallToolResult:
    feature = {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [1.5, 2.5]},
        "properties": {"note": TRACE_MARKER},
    }
    return CallToolResult(
        content=[TextContent(type="text", text='{"map": {}}')],
        structuredContent={"map": {"layers": [{"id": "aoi", "delivery": "meta_geojson"}]}},
        isError=False,
        _meta={
            MAP_META_KEY: {
                "layers": {
                    "aoi": {
                        "feature_collection": {"type": "FeatureCollection", "features": [feature]}
                    },
                    "urban_context": {"truncated": True},
                }
            },
            "io.modelcontextprotocol/serverInfo": {"name": "fpac-soil-mcp"},
        },
    )


def test_init_fpac_mcp_server_returns_the_trace_guarded_subclass():
    server = agent_module.init_fpac_mcp_server(MagicMock(name="ws"))
    assert type(server) is agent_module.FpacMcpServer
    assert isinstance(server, McpServer)


def test_fpac_server_keeps_map_meta_out_of_the_trace(monkeypatch, tmp_path):
    result = _meta_result()
    expected_meta = result.model_dump(by_alias=True)["_meta"]
    parent = AsyncMock(return_value=result)
    monkeypatch.setattr(MCPServerStreamableHttp, "call_tool", parent)
    server = agent_module.init_fpac_mcp_server(MagicMock(name="ws"))
    arguments = {"geojson": "aoi-0123abcd"}

    previous = mlflow.get_tracking_uri()
    mlflow.set_tracking_uri(f"sqlite:///{tmp_path / 'mlflow.db'}")
    try:
        experiment_id = mlflow.create_experiment("fpac-trace-guard")
        mlflow.set_experiment(experiment_id=experiment_id)
        returned = asyncio.run(server.call_tool("analyze_farmland_by_polygon", arguments))
        if hasattr(mlflow, "flush_trace_async_logging"):
            mlflow.flush_trace_async_logging()
        traces = mlflow.MlflowClient().search_traces(locations=[experiment_id])
    finally:
        mlflow.set_tracking_uri(previous)

    # The caller gets the result untouched.
    assert returned is result
    assert result.model_dump(by_alias=True)["_meta"] == expected_meta
    parent.assert_awaited_once_with(server, "analyze_farmland_by_polygon", arguments)

    assert len(traces) == 1
    (span,) = traces[0].data.spans
    assert span.name == "analyze_farmland_by_polygon"
    assert span.span_type == "TOOL"
    assert span.inputs == {"tool_name": "analyze_farmland_by_polygon", "arguments": arguments}
    recorded = json.dumps(traces[0].to_dict())
    assert "coordinates" not in recorded
    assert TRACE_MARKER not in recorded
    stub = span.outputs["_meta"][MAP_META_KEY]
    assert stub["omitted_from_trace"] is True
    assert stub["layers"] == ["aoi", "urban_context"]
    assert stub["bytes"] > 0
    assert span.outputs["_meta"]["io.modelcontextprotocol/serverInfo"] == {"name": "fpac-soil-mcp"}
    assert span.outputs["structuredContent"]["map"]["layers"][0]["delivery"] == "meta_geojson"


def test_local_mcp_client_avoids_workspace_client(monkeypatch):
    monkeypatch.setenv("FPAC_LOCAL_DEV", "1")
    monkeypatch.setenv("FPAC_MCP_URL", "http://127.0.0.1:8001/mcp")
    server = MagicMock(name="local_mcp_server")
    constructor = MagicMock(return_value=server)
    monkeypatch.setattr(agent_module, "MCPServerStreamableHttp", constructor)

    assert agent_module.init_fpac_mcp_server() is server
    constructor.assert_called_once_with(
        name="fpac-soil-mcp",
        params={"url": "http://127.0.0.1:8001/mcp", "timeout": 180.0},
    )


def test_local_openai_client_uses_local_endpoint(monkeypatch):
    monkeypatch.setenv("FPAC_LOCAL_DEV", "1")
    monkeypatch.setenv("LOCAL_LLM_BASE_URL", "http://127.0.0.1:8090/v1")
    client = MagicMock()
    constructor = MagicMock(return_value=client)
    set_default = MagicMock()
    monkeypatch.setattr(agent_module, "AsyncOpenAI", constructor)
    monkeypatch.setattr(agent_module, "set_default_openai_client", set_default)
    agent_module.configure_openai_client.cache_clear()

    assert agent_module.configure_openai_client() is client
    constructor.assert_called_once_with(base_url="http://127.0.0.1:8090/v1", api_key="local-dev")
    set_default.assert_called_once_with(client)


def test_local_mlflow_tracing_requires_opt_in(monkeypatch):
    agent_module._local_mlflow_configured_uri = None
    monkeypatch.setenv("FPAC_LOCAL_DEV", "1")
    set_uri = MagicMock()
    set_experiment = MagicMock()
    autolog = MagicMock()
    monkeypatch.setattr(agent_module.mlflow, "set_tracking_uri", set_uri)
    monkeypatch.setattr(agent_module.mlflow, "set_experiment", set_experiment)
    monkeypatch.setattr(agent_module.mlflow.openai, "autolog", autolog)

    assert not agent_module.configure_local_mlflow_tracing()
    set_uri.assert_not_called()
    set_experiment.assert_not_called()
    autolog.assert_not_called()


def test_local_mlflow_tracing_configures_explicit_external_store(monkeypatch, tmp_path):
    agent_module._local_mlflow_configured_uri = None
    monkeypatch.setenv("FPAC_LOCAL_DEV", "1")
    monkeypatch.setenv("FPAC_LOCAL_MLFLOW_TRACING", "1")
    tracking_path = tmp_path / "mlruns"
    tracking_uri = f"sqlite:///{tracking_path / 'mlflow.db'}"
    monkeypatch.setenv("FPAC_LOCAL_MLFLOW_DIR", str(tracking_path))
    set_uri = MagicMock()
    set_experiment = MagicMock()
    autolog = MagicMock()
    monkeypatch.setattr(agent_module.mlflow, "set_tracking_uri", set_uri)
    monkeypatch.setattr(agent_module.mlflow, "set_experiment", set_experiment)
    monkeypatch.setattr(agent_module.mlflow.openai, "autolog", autolog)

    assert agent_module.configure_local_mlflow_tracing()
    set_uri.assert_called_once_with(tracking_uri)
    set_experiment.assert_called_once_with("fpac-soil-local")
    autolog.assert_called_once_with()


def test_init_fpac_mcp_server_resolves_mcp_app(monkeypatch):
    mcp_server = MagicMock(name="FpacMcpServer")
    monkeypatch.setattr(agent_module, "FpacMcpServer", mcp_server)
    monkeypatch.setenv("FPAC_MCP_APP", "mcp-fpac-soil-dev")
    ws = MagicMock(name="ws")
    ws.apps.get.return_value.url = "https://mcp-fpac-soil-dev-0000.aws.databricksapps.com"
    agent_module.init_fpac_mcp_server(ws)
    ws.apps.get.assert_called_once_with(name="mcp-fpac-soil-dev")
    assert (
        mcp_server.call_args.kwargs["url"]
        == "https://mcp-fpac-soil-dev-0000.aws.databricksapps.com/mcp"
    )


def test_connect_runs_without_tools_when_lookup_fails(monkeypatch):
    monkeypatch.setattr(agent_module, "WorkspaceClient", MagicMock())
    monkeypatch.setattr(
        agent_module,
        "init_fpac_mcp_server",
        MagicMock(side_effect=config_module.McpServerLookupError("lookup failed")),
    )
    create = MagicMock(name="create_agent")
    monkeypatch.setattr(agent_module, "create_agent", create)

    async def connect():
        from contextlib import AsyncExitStack

        async with AsyncExitStack() as stack:
            return await agent_module._connect_fpac_agent(stack)

    result = asyncio.run(connect())

    assert result is create.return_value
    create.assert_called_once_with(mcp_servers=[], tools_unavailable=True)


@pytest.mark.parametrize("run_handler", [_run_invoke, _run_stream], ids=["invoke", "stream"])
def test_handler_healthy_path(patched, caplog, run_handler):
    with caplog.at_level(logging.INFO, logger=agent_module.__name__):
        run_handler()
    patched.configure_openai_client.assert_called_once_with()
    patched.init.assert_called_once_with(patched.workspace_client.return_value)
    servers_arg = patched.connect.await_args.args[1]
    assert servers_arg == [patched.server]
    patched.create_agent.assert_called_once_with(
        mcp_servers=[patched.server],
        tools_unavailable=False,
        site_assessment_context=agent_module._site_assessment_criteria_context(
            patched.server.read_resource.return_value
        ),
        history_items=ANY,
    )
    # The Site Assessment tools read recorded answers from the same history the run gets.
    if patched.run.call_args:
        messages = patched.run.call_args.args[1]
    else:
        messages = patched.run_streamed.call_args.kwargs["input"]
    assert patched.create_agent.call_args.kwargs["history_items"] == messages
    patched.server.read_resource.assert_awaited_once_with("fppa://site-assessment-criteria")
    assert not [r for r in caplog.records if r.name == agent_module.__name__]


@pytest.mark.parametrize("run_handler", [_run_invoke, _run_stream], ids=["invoke", "stream"])
def test_handler_unavailable_path(patched, caplog, run_handler):
    patched.connect.return_value = ([], ["fpac-soil-mcp"])
    with caplog.at_level(logging.INFO, logger=agent_module.__name__):
        run_handler()
    patched.configure_openai_client.assert_called_once_with()
    patched.create_agent.assert_called_once_with(mcp_servers=[], tools_unavailable=True)
    # The health check owns the WARNING (with traceback); the handler adds one INFO summary.
    records = [r for r in caplog.records if r.name == agent_module.__name__]
    assert [r.levelno for r in records] == [logging.INFO]
    assert "fpac-soil-mcp" in records[0].getMessage()


def test_invoke_runs_agent_from_mcp(patched):
    _run_invoke()
    assert patched.run.await_args.args[0] is patched.create_agent.return_value


def test_stream_runs_agent_from_mcp(patched):
    assert _run_stream() == []
    assert patched.run_streamed.call_args.args[0] is patched.create_agent.return_value


def test_template_server_removed():
    assert not hasattr(agent_module, "init_mcp_server")


def test_invalid_site_assessment_resource_disables_interview_context(patched):
    patched.server.read_resource.return_value = SimpleNamespace(
        contents=[SimpleNamespace(text='{"schema_version":"1.0","criteria":[]}')]
    )

    async def connect():
        from contextlib import AsyncExitStack

        async with AsyncExitStack() as stack:
            return await agent_module._connect_fpac_agent(stack)

    asyncio.run(connect())
    assert (
        patched.create_agent.call_args.kwargs["site_assessment_context"]
        == agent_module.SITE_ASSESSMENT_RESOURCE_UNAVAILABLE_NOTE
    )


def _confirmed_site_summary(
    resource,
    state="answered",
    band_id="range_20_90_1",
    criterion_number=1,
    confirmed=True,
):
    criteria = json.loads(resource.contents[0].text)
    criterion = next(
        criterion
        for criterion in criteria["criteria"]
        if criterion["criterion_number"] == criterion_number
    )
    band = next(band for band in criterion["bands"] if band["id"] == band_id)
    return {
        "type": "site_assessment_confirmed_summary",
        "confirmed": confirmed,
        "answers": [
            {
                "type": "site_assessment_answer",
                "criterion_number": criterion_number,
                "answer_state": state,
                "answer": band_id if state == "answered" else None,
                "selected_band": band if state != "skipped" else None,
                "points": band["points"] if state == "answered" else None,
                "evidence": "",
                "comment": "",
                "provenance": "user",
            }
        ],
    }


@pytest.mark.parametrize("run_handler", [_run_invoke, _run_stream], ids=["invoke", "stream"])
@pytest.mark.parametrize(
    ("case", "state", "fact", "band_id"),
    [
        ("missing-confirmation", "answered", 24, "range_20_90_1"),
        ("malformed-confirmation", "answered", 24, "range_20_90_1"),
        ("absent-inputs", "answered", None, "range_20_90_1"),
        ("stale-answer", "answered", 24, "range_20_90_2"),
        ("matching-answer", "answered", 24, "range_20_90_1"),
        ("matching-unknown", "unknown", "unknown", "unknown"),
        ("matching-skipped", "skipped", "skipped", "below_20"),
    ],
)
def test_site_assessment_mcp_gate_is_consistent_for_invoke_and_stream(
    patched, run_handler, case, state, fact, band_id
):
    summary = _confirmed_site_summary(patched.server.read_resource.return_value, state, band_id)
    if case == "malformed-confirmation":
        summary["answers"] = "invalid"
    request_content = "hello" if case == "missing-confirmation" else json.dumps(summary)
    tool_arguments = {"project_type": "site"}
    if case != "absent-inputs":
        tool_arguments["site_assessment_inputs"] = {"criteria_facts": {"1": {"percentage": fact}}}
    forwarded_call = patched.server.call_tool
    tool_results = []

    async def run_agent(*args, **kwargs):
        tool_results.append(
            await patched.server.call_tool("calculate_preliminary_lesa", tool_arguments)
        )
        return SimpleNamespace(new_items=[])

    async def stream_events():
        tool_results.append(
            await patched.server.call_tool("calculate_preliminary_lesa", tool_arguments)
        )
        if False:
            yield None

    patched.run.side_effect = run_agent
    patched.run_streamed.side_effect = lambda *args, **kwargs: SimpleNamespace(
        stream_events=stream_events
    )
    run_handler(_request(request_content))

    should_forward = case in {
        "matching-answer",
        "matching-unknown",
        "matching-skipped",
    }
    if should_forward:
        forwarded_call.assert_awaited_once()
        assert tool_results[0].isError is False
    else:
        forwarded_call.assert_not_awaited()
        assert tool_results[0].isError is True
        assert tool_results[0].content[0].text


@pytest.mark.parametrize("run_handler", [_run_invoke, _run_stream], ids=["invoke", "stream"])
@pytest.mark.parametrize(
    ("case", "band_id", "confirmed", "project_acres", "county_average", "criterion7_fact"),
    [
        ("missing-confirmation", "below_average_8", True, 180, 200, None),
        ("unconfirmed", "below_average_8", False, 180, 200, None),
        ("incomplete-pair", "below_average_8", True, 180, None, None),
        ("missing-criterion7-answer", "range_20_90_1", True, 180, 200, None),
        ("mismatched-band", "below_average_9", True, 180, 200, None),
        ("conflicting-dual-inputs", "below_average_8", True, 180, 200, 85),
        ("matching-dual-inputs", "below_average_8", True, 180, 200, 90),
        ("matching-band", "below_average_8", True, 180, 200, None),
    ],
)
def test_farm_acre_criterion7_gate_is_consistent_for_invoke_and_stream(
    patched,
    run_handler,
    case,
    band_id,
    confirmed,
    project_acres,
    county_average,
    criterion7_fact,
):
    summary = _confirmed_site_summary(
        patched.server.read_resource.return_value,
        band_id=band_id,
        criterion_number=1 if case == "missing-criterion7-answer" else 7,
        confirmed=confirmed,
    )
    request_content = "hello" if case == "missing-confirmation" else json.dumps(summary)
    site_inputs = {"project_farm_acres": project_acres}
    if county_average is not None:
        site_inputs["county_average_farm_acres"] = county_average
    if criterion7_fact is not None:
        site_inputs["criteria_facts"] = {"7": {"percentage": criterion7_fact}}
    tool_arguments = {
        "project_type": "site",
        "site_assessment_inputs": site_inputs,
    }
    forwarded_call = patched.server.call_tool
    tool_results = []

    async def run_agent(*args, **kwargs):
        tool_results.append(
            await patched.server.call_tool("calculate_preliminary_lesa", tool_arguments)
        )
        return SimpleNamespace(new_items=[])

    async def stream_events():
        tool_results.append(
            await patched.server.call_tool("calculate_preliminary_lesa", tool_arguments)
        )
        if False:
            yield None

    patched.run.side_effect = run_agent
    patched.run_streamed.side_effect = lambda *args, **kwargs: SimpleNamespace(
        stream_events=stream_events
    )
    run_handler(_request(request_content))

    if case == "matching-band":
        forwarded_call.assert_awaited_once()
        assert tool_results[0].isError is False
    else:
        forwarded_call.assert_not_awaited()
        assert tool_results[0].isError is True
        assert tool_results[0].content[0].text


@pytest.mark.parametrize(
    ("target", "field", "value"),
    [
        ("band", "id", "  "),
        ("band", "id", "range_20_90_1"),
        ("band", "label", ""),
        ("band", "points", "0"),
        ("band", "points", 16),
        ("band", "points", True),
        ("criterion", "max_points", True),
        ("band", "min", "0"),
        ("band", "min", 1),
        ("band", "max", 25),
        ("band", "max_inclusive", True),
        ("band", "min_inclusive", False),
    ],
    ids=[
        "empty-id",
        "duplicate-id",
        "empty-label",
        "non-numeric-points",
        "points-over-maximum",
        "boolean-points",
        "invalid-maximum-points",
        "non-numeric-minimum",
        "percentage-ranges-must-start-at-zero",
        "percentage-range-gap",
        "overlapping-inclusive-boundary",
        "zero-must-be-included",
    ],
)
def test_invalid_site_assessment_band_fields_are_rejected(
    target, field, value, valid_site_assessment_criteria_resource
):
    payload = json.loads(valid_site_assessment_criteria_resource.contents[0].text)
    if target == "criterion":
        payload["criteria"][0][field] = value
    else:
        band_id = "above_90" if field == "points" and value == 16 else "below_20"
        band = next(band for band in payload["criteria"][0]["bands"] if band["id"] == band_id)
        band[field] = value
    resource = SimpleNamespace(contents=[SimpleNamespace(text=json.dumps(payload))])

    with pytest.raises((TypeError, ValueError)):
        agent_module._site_assessment_criteria_context(resource)


def test_malformed_site_assessment_band_disables_interview_context(
    patched, valid_site_assessment_criteria_resource
):
    payload = json.loads(valid_site_assessment_criteria_resource.contents[0].text)
    payload["criteria"][0]["bands"][0]["label"] = " "
    patched.server.read_resource.return_value = SimpleNamespace(
        contents=[SimpleNamespace(text=json.dumps(payload))]
    )

    async def connect():
        from contextlib import AsyncExitStack

        async with AsyncExitStack() as stack:
            return await agent_module._connect_fpac_agent(stack)

    asyncio.run(connect())
    assert (
        patched.create_agent.call_args.kwargs["site_assessment_context"]
        == agent_module.SITE_ASSESSMENT_RESOURCE_UNAVAILABLE_NOTE
    )


@pytest.mark.parametrize(
    "error",
    [
        McpError(ErrorData(code=-32603, message="Resource read failed.")),
        UserError("Failed to read resource on MCP server 'fpac-soil-mcp': Request failed."),
    ],
    ids=["mcp-resource-error", "mcp-transport-error"],
)
def test_resource_read_failures_disable_interview_context(patched, error):
    patched.server.read_resource.side_effect = error

    async def connect():
        from contextlib import AsyncExitStack

        async with AsyncExitStack() as stack:
            return await agent_module._connect_fpac_agent(stack)

    asyncio.run(connect())
    assert (
        patched.create_agent.call_args.kwargs["site_assessment_context"]
        == agent_module.SITE_ASSESSMENT_RESOURCE_UNAVAILABLE_NOTE
    )


def test_unexpected_resource_read_error_propagates(patched):
    patched.server.read_resource.side_effect = RuntimeError("implementation bug")

    async def connect():
        from contextlib import AsyncExitStack

        async with AsyncExitStack() as stack:
            return await agent_module._connect_fpac_agent(stack)

    with pytest.raises(RuntimeError, match="implementation bug"):
        asyncio.run(connect())


def test_validated_resource_context_contains_all_criteria(valid_site_assessment_criteria_resource):
    context = agent_module._site_assessment_criteria_context(
        valid_site_assessment_criteria_resource
    )
    assert "fppa://site-assessment-criteria" in context
    payload = json.loads(valid_site_assessment_criteria_resource.contents[0].text)
    assert all(criterion["question"] in context for criterion in payload["criteria"])
    assert "Unknown or unavailable" in context


def test_valid_resource_wires_tools_into_agent(
    monkeypatch, valid_site_assessment_criteria_resource
):
    server = MagicMock(name="server")
    server.read_resource = AsyncMock(return_value=valid_site_assessment_criteria_resource)
    monkeypatch.setattr(agent_module, "WorkspaceClient", MagicMock())
    monkeypatch.setattr(agent_module, "init_fpac_mcp_server", MagicMock(return_value=server))
    monkeypatch.setattr(
        agent_module,
        "connect_healthy_mcp_servers",
        AsyncMock(return_value=([server], [])),
    )
    constructed = MagicMock(name="Agent")
    monkeypatch.setattr(agent_module, "Agent", constructed)

    async def connect():
        from contextlib import AsyncExitStack

        async with AsyncExitStack() as stack:
            await agent_module._connect_fpac_agent(stack)

    asyncio.run(connect())

    assert [tool.name for tool in constructed.call_args.kwargs["tools"]] == [
        "get_site_assessment_question",
        "record_site_assessment_answer",
        "show_site_assessment_summary",
    ]


@pytest.mark.parametrize("handler", ["invoke", "stream"])
def test_handlers_repair_orphan_tool_calls_before_running(patched, handler):
    # Session 2fc10f43: a replayed call with no output made every later turn fail.
    request = ResponsesAgentRequest(
        input=[
            {"role": "user", "content": "below average"},
            {
                "type": "function_call",
                "call_id": "call_orphan",
                "name": "record_site_assessment_answer",
                "arguments": "{}",
            },
            {"role": "user", "content": "try again"},
        ]
    )

    if handler == "invoke":
        _run_invoke(request)
        messages = patched.run.call_args.args[1]
    else:
        _run_stream(request)
        messages = patched.run_streamed.call_args.kwargs["input"]

    outputs = [m for m in messages if m.get("type") == "function_call_output"]
    assert [m["call_id"] for m in outputs] == ["call_orphan"]
    assert messages.index(outputs[0]) == 2
