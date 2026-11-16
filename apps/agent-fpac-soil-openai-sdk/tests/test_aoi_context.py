"""Offline tests for the map AOI as chat session context (ADR 0016).

The browser sends ``custom_inputs.active_aoi = {aoi_ref, geometry, summary}``; the agent
server validates it, adds a coordinate-free note to the instructions and swaps the
geometry into ``geojson``/``geometry`` tool arguments that equal the AOI reference.
Substitution tests run the real ``McpServer`` class with only its client session faked.
Synthetic geometry only; ``MARK`` is a coordinate value that must not reach the note.
"""

import asyncio
import logging
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import mlflow
import pytest
from agent_server import agent as agent_module
from agent_server import aoi_context, geo
from agent_server.agent import init_fpac_mcp_server
from agent_server.aoi_context import (
    ActiveAoi,
    bind_active_aoi,
    instruction_note,
    parse_active_aoi,
    read_active_aoi,
    substitute_arguments,
)
from mcp.types import CallToolResult
from mlflow.types.responses import ResponsesAgentRequest

REF = "aoi-0a1b2c3d"
MARK = 0.123457
SQUARE = {"type": "Polygon", "coordinates": [[[0, 0], [MARK, 0], [MARK, 1], [0, 1], [0, 0]]]}
MULTI = {"type": "MultiPolygon", "coordinates": [SQUARE["coordinates"]]}
LESA_TOOL = "calculate_preliminary_lesa"
NOTICE = "Preliminary screening only; not a regulatory determination."


def _summary() -> dict:
    analysis = {
        "total_aoi_acres": 12.34,
        "coverage_status": "complete",
        "farmland_summary": {"prime_acres": 10.0, "prime_pct": 81.0},
        "map_units": [{"musym": "Ab", "muname": "Synthetic loam", "calculated_acres": 10.0}],
        "regulatory_notice": NOTICE,
    }
    return geo.build_chat_summary(analysis, REF)


def _active(**overrides) -> dict:
    return {"aoi_ref": REF, "geometry": SQUARE, "summary": _summary(), **overrides}


def _request(custom_inputs: dict | None = None) -> ResponsesAgentRequest:
    return ResponsesAgentRequest(
        input=[{"role": "user", "content": "Run a preliminary LESA on my AOI."}],
        custom_inputs=custom_inputs,
    )


# --- reading and validating active_aoi ---------------------------------------------------


@pytest.mark.parametrize("geometry", [SQUARE, MULTI], ids=["polygon", "multipolygon"])
def test_valid_active_aoi_is_read(geometry):
    aoi = read_active_aoi(_request({"active_aoi": _active(geometry=geometry)}))
    assert aoi == ActiveAoi(REF, geometry, aoi.summary_text, 12.3)  # summary rounds acres
    assert NOTICE in aoi.summary_text


@pytest.mark.parametrize(
    "custom_inputs",
    [None, {}, {"session_id": "s-1"}, {"active_aoi": None}],
    ids=["no-custom-inputs", "empty", "other-keys", "null"],
)
def test_absent_active_aoi_is_none(custom_inputs):
    assert read_active_aoi(_request(custom_inputs)) is None


@pytest.mark.parametrize(
    "raw",
    [
        "aoi-0a1b2c3d",
        _active(aoi_ref="aoi-XYZ"),
        _active(aoi_ref="aoi-0a1b2c3d-extra"),
        _active(aoi_ref=None),
        _active(geometry={"type": "Point", "coordinates": [0, 0]}),
        _active(geometry={"type": "Polygon", "coordinates": [[[0, 0], [1, 1]]]}),
        _active(geometry={"type": "Polygon", "coordinates": "bad"}),
        _active(geometry=None),
    ],
    ids=[
        "not-object",
        "bad-ref",
        "ref-suffix",
        "no-ref",
        "point",
        "short-ring",
        "bad-coordinates",
        "no-geometry",
    ],
)
def test_invalid_active_aoi_is_ignored(raw, caplog):
    with caplog.at_level(logging.INFO, logger=aoi_context.__name__):
        assert read_active_aoi(_request({"active_aoi": raw})) is None
    assert str(MARK) not in caplog.text


def test_vertex_limit_applies(monkeypatch):
    monkeypatch.setenv("GEO_MAX_VERTICES", "4")
    assert read_active_aoi(_request({"active_aoi": _active()})) is None
    monkeypatch.setenv("GEO_MAX_VERTICES", "5")
    assert read_active_aoi(_request({"active_aoi": _active()})) is not None


def test_size_limit_applies(monkeypatch):
    monkeypatch.setenv("GEO_MAX_VERTICES", "1000000")
    ring = [[i * 1e-9 + MARK, MARK] for i in range(20000)] + [[MARK, MARK]]
    big = {"type": "Polygon", "coordinates": [ring]}
    assert read_active_aoi(_request({"active_aoi": _active(geometry=big)})) is None


@pytest.mark.parametrize(
    "summary",
    [None, "text", {"farmland_classes": ["not", "a", "dict"]}],
    ids=["none", "string", "malformed"],
)
def test_missing_or_bad_summary_keeps_the_aoi(summary):
    aoi = parse_active_aoi(_active(summary=summary))
    assert aoi.aoi_ref == REF
    assert aoi.geometry == SQUARE
    assert aoi.summary_text is None


# --- instruction note --------------------------------------------------------------------


def test_note_has_reference_acres_and_summary_but_no_coordinates():
    note = instruction_note(parse_active_aoi(_active()))
    assert REF in note
    assert "12.3 acres" in note
    assert "`geojson` or `geometry`" in note
    assert NOTICE in note
    assert str(MARK) not in note
    assert "coordinates" not in note.lower().replace("do not write coordinates", "")


def test_note_without_summary():
    note = instruction_note(parse_active_aoi(_active(summary=None)))
    assert REF in note
    assert "No map screening summary" in note
    assert str(MARK) not in note


@pytest.mark.parametrize("summary", ["default", None])
def test_note_tells_the_model_to_call_the_tool_when_asked(summary):
    # Trial 44.8.1: with a summary attached the model answered "screen this AOI" from
    # the summary and made no tool call.
    raw = _active() if summary == "default" else _active(summary=None)
    note = instruction_note(parse_active_aoi(raw))
    assert "When the user asks to run, screen or analyze this AOI, call the tool" in note
    assert "do not answer such a request from the summary alone" in note


# --- argument substitution ---------------------------------------------------------------


@pytest.mark.parametrize("key", ["geojson", "geometry"])
def test_reference_is_replaced_with_geometry(key):
    aoi = parse_active_aoi(_active())
    arguments = {key: REF, "project_name": "Synthetic"}
    result = substitute_arguments(arguments, aoi)
    assert result == {key: SQUARE, "project_name": "Synthetic"}
    assert arguments == {key: REF, "project_name": "Synthetic"}  # input not mutated
    result[key]["coordinates"].clear()
    assert aoi.geometry == SQUARE  # each call gets its own copy


@pytest.mark.parametrize(
    "arguments",
    [
        None,
        {},
        {"geojson": "aoi-ffffffff"},
        {"geometry": SQUARE},
        {"project_name": REF},
        {"geojson": f"near {REF}"},
    ],
    ids=["none", "empty", "other-ref", "real-geometry", "other-key", "embedded"],
)
def test_other_arguments_are_unchanged(arguments):
    assert substitute_arguments(arguments, parse_active_aoi(_active())) == arguments


class FakeSession:
    def __init__(self):
        self.calls: list[tuple[str, dict | None]] = []

    async def call_tool(self, name, arguments=None, *args, **kwargs):
        self.calls.append((name, arguments))
        return CallToolResult(content=[], structuredContent={"ok": True}, isError=False)


def _real_server() -> tuple:
    server = init_fpac_mcp_server(MagicMock(name="WorkspaceClient"))
    session = FakeSession()
    server.session = session
    return server, session


@contextmanager
def _local_experiment(tmp_path):
    previous = mlflow.get_tracking_uri()
    mlflow.set_tracking_uri(f"sqlite:///{tmp_path / 'mlflow.db'}")
    try:
        experiment_id = mlflow.create_experiment("aoi-context-traces")
        mlflow.set_experiment(experiment_id=experiment_id)

        def count() -> int:
            if hasattr(mlflow, "flush_trace_async_logging"):
                mlflow.flush_trace_async_logging()
            return len(mlflow.MlflowClient().search_traces(locations=[experiment_id]))

        yield count
    finally:
        mlflow.set_tracking_uri(previous)


def _lesa_arguments() -> dict:
    return {"project_name": "Synthetic", "geometry": REF, "project_type": "site"}


def test_bound_server_sends_geometry_to_the_mcp_session(tmp_path):
    """The LESA call from the deployed check: the reference reaches MCP as the shape."""
    server, session = _real_server()
    bind_active_aoi(server, parse_active_aoi(_active()))

    with _local_experiment(tmp_path) as trace_count:
        asyncio.run(server.call_tool(LESA_TOOL, _lesa_arguments()))
        traces = trace_count()

    assert session.calls == [
        (LESA_TOOL, {"project_name": "Synthetic", "geometry": SQUARE, "project_type": "site"})
    ]
    assert traces == 1  # the chat path keeps the traced McpServer.call_tool


def test_bound_server_forwards_meta_keyword(tmp_path):
    server, session = _real_server()
    bind_active_aoi(server, parse_active_aoi(_active()))
    with _local_experiment(tmp_path):
        asyncio.run(server.call_tool(LESA_TOOL, _lesa_arguments(), meta={"k": "v"}))
    assert session.calls[0][1]["geometry"] == SQUARE


def test_unbound_server_sends_the_reference_string(tmp_path):
    """Control: without the binding the model's reference string reaches MCP unchanged."""
    server, session = _real_server()
    with _local_experiment(tmp_path):
        asyncio.run(server.call_tool(LESA_TOOL, _lesa_arguments()))
    assert session.calls == [(LESA_TOOL, _lesa_arguments())]


# --- handlers ----------------------------------------------------------------------------


async def _empty_events():
    return
    yield  # pragma: no cover - makes this an async generator


@pytest.fixture
def patched(monkeypatch, valid_site_assessment_criteria_resource):
    server = MagicMock(name="server")
    original_call_tool = server.call_tool
    server.read_resource = AsyncMock(return_value=valid_site_assessment_criteria_resource)
    mocks = SimpleNamespace(
        server=server,
        original_call_tool=original_call_tool,
        criteria_resource=valid_site_assessment_criteria_resource,
        connect=AsyncMock(return_value=([server], [])),
        create_agent=MagicMock(return_value=MagicMock(name="agent")),
        run=AsyncMock(return_value=SimpleNamespace(new_items=[])),
        run_streamed=MagicMock(return_value=SimpleNamespace(stream_events=_empty_events)),
    )
    monkeypatch.setattr(agent_module, "configure_openai_client", MagicMock())
    monkeypatch.setattr(agent_module, "WorkspaceClient", MagicMock())
    monkeypatch.setattr(agent_module, "init_fpac_mcp_server", MagicMock(return_value=server))
    monkeypatch.setattr(agent_module, "connect_healthy_mcp_servers", mocks.connect)
    monkeypatch.setattr(agent_module, "create_agent", mocks.create_agent)
    monkeypatch.setattr(agent_module.Runner, "run", mocks.run)
    monkeypatch.setattr(agent_module.Runner, "run_streamed", mocks.run_streamed)
    return mocks


def _run_invoke(request):
    return asyncio.run(agent_module.invoke_handler(request))


def _run_stream(request):
    async def collect():
        return [event async for event in agent_module.stream_handler(request)]

    return asyncio.run(collect())


HANDLERS = pytest.mark.parametrize("run", [_run_invoke, _run_stream], ids=["invoke", "stream"])


@HANDLERS
def test_handler_with_active_aoi_adds_note_and_binds_server(patched, run):
    run(_request({"active_aoi": _active()}))
    expected_note = instruction_note(parse_active_aoi(_active()))
    patched.create_agent.assert_called_once_with(
        mcp_servers=[patched.server],
        aoi_note=expected_note,
        site_assessment_context=agent_module._site_assessment_criteria_context(
            patched.criteria_resource
        ),
    )
    patched.server.read_resource.assert_awaited_once_with("fppa://site-assessment-criteria")
    assert patched.server.call_tool is not patched.original_call_tool
    assert patched.connect.await_args.args[1] == [patched.server]


@HANDLERS
def test_handler_model_input_is_unchanged_by_the_aoi(patched, run):
    run(_request({"active_aoi": _active()}))
    if patched.run.await_args:
        messages = patched.run.await_args.args[1]
    else:
        messages = patched.run_streamed.call_args.kwargs["input"]
    assert str(MARK) not in repr(messages)
    assert REF not in repr(messages)


@HANDLERS
@pytest.mark.parametrize(
    "custom_inputs",
    [None, {"session_id": "s-1"}, {"active_aoi": {"aoi_ref": "bad"}}],
    ids=["none", "no-aoi", "invalid-aoi"],
)
def test_handler_without_aoi_behaves_as_before(patched, run, custom_inputs):
    run(_request(custom_inputs))
    patched.create_agent.assert_called_once_with(
        mcp_servers=[patched.server],
        tools_unavailable=False,
        site_assessment_context=agent_module._site_assessment_criteria_context(
            patched.criteria_resource
        ),
    )
    patched.server.read_resource.assert_awaited_once_with("fppa://site-assessment-criteria")
    assert patched.server.call_tool is not patched.original_call_tool


@HANDLERS
def test_handler_with_aoi_and_tools_unavailable_keeps_the_unavailable_note(patched, run):
    patched.connect.return_value = ([], ["fpac-soil-mcp"])
    run(_request({"active_aoi": _active()}))
    patched.create_agent.assert_called_once_with(mcp_servers=[], tools_unavailable=True)


def test_create_agent_appends_the_note():
    note = instruction_note(parse_active_aoi(_active()))
    plain = agent_module.create_agent(mcp_servers=[])
    with_note = agent_module.create_agent(mcp_servers=[], aoi_note=note)
    assert with_note.instructions == f"{plain.instructions}\n\n{note}"
    unavailable = agent_module.create_agent(mcp_servers=[], tools_unavailable=True, aoi_note=note)
    assert note not in unavailable.instructions
