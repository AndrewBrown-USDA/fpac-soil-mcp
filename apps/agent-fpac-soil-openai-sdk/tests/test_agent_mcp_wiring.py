"""Tests that both handlers connect the fpac-soil-mcp server and build the agent from it.

No network: McpServer, WorkspaceClient, the health check, create_agent, and Runner are
all patched. The decorated handlers return a coroutine or async generator, so they are
driven with asyncio.run (the app has no pytest-asyncio).
"""

import asyncio
import json
import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from agent_server import agent as agent_module
from agent_server import config as config_module
from agents.exceptions import UserError
from mcp.shared.exceptions import McpError
from mcp.types import ErrorData
from mlflow.types.responses import ResponsesAgentRequest

DEFAULT_URL = "https://mcp-fpac-soil-7474654188777746.aws.databricksapps.com/mcp"


def _request() -> ResponsesAgentRequest:
    return ResponsesAgentRequest(input=[{"role": "user", "content": "hi"}])


async def _empty_events():
    return
    yield  # pragma: no cover - makes this an async generator


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    for name in ("AGENT_MODEL", "FPAC_MCP_URL", "FPAC_MCP_APP", "FPAC_MCP_TIMEOUT_SECONDS"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(config_module, "_RESOLVED_MCP_URLS", {})


@pytest.fixture
def patched(monkeypatch, valid_site_assessment_criteria_resource):
    """Patch everything the handlers call; returns the mocks."""
    server = MagicMock(name="server")
    server.read_resource = AsyncMock(return_value=valid_site_assessment_criteria_resource)
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


def _run_invoke():
    return asyncio.run(agent_module.invoke_handler(_request()))


def _run_stream():
    async def collect():
        return [event async for event in agent_module.stream_handler(_request())]

    return asyncio.run(collect())


def test_init_fpac_mcp_server_defaults(monkeypatch):
    mcp_server = MagicMock(name="McpServer")
    monkeypatch.setattr(agent_module, "McpServer", mcp_server)
    ws = MagicMock(name="ws")
    result = agent_module.init_fpac_mcp_server(ws)
    assert result is mcp_server.return_value
    mcp_server.assert_called_once_with(
        url=DEFAULT_URL, name="fpac-soil-mcp", workspace_client=ws, timeout=180.0
    )


def test_init_fpac_mcp_server_env_overrides(monkeypatch):
    mcp_server = MagicMock(name="McpServer")
    monkeypatch.setattr(agent_module, "McpServer", mcp_server)
    monkeypatch.setenv("FPAC_MCP_URL", "https://example.com/mcp")
    monkeypatch.setenv("FPAC_MCP_TIMEOUT_SECONDS", "30")
    ws = MagicMock(name="ws")
    agent_module.init_fpac_mcp_server(ws)
    mcp_server.assert_called_once_with(
        url="https://example.com/mcp", name="fpac-soil-mcp", workspace_client=ws, timeout=30.0
    )


def test_init_fpac_mcp_server_resolves_mcp_app(monkeypatch):
    mcp_server = MagicMock(name="McpServer")
    monkeypatch.setattr(agent_module, "McpServer", mcp_server)
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
    )
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
