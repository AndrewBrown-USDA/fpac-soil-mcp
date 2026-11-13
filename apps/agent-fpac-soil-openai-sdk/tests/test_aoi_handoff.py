"""Focused evidence for AOI request and trace-session boundaries.

The handlers pass only normalized ``request.input`` to the model. The MLflow trace
session comes from ``get_session_id``, which prefers ``context.conversation_id`` (what
the vendored chat UI sends) over ``custom_inputs.session_id``. No network: everything
the handlers call is patched, following ``test_agent_mcp_wiring.py``.
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from agent_server import agent as agent_module
from mlflow.types.responses import ResponsesAgentRequest

AOI_CUSTOM_INPUTS = {
    "session_id": "session-123",
    "geometry": {"type": "Polygon", "coordinates": [[[1, 2], [3, 4], [1, 2]]]},
}


async def _empty_events():
    return
    yield  # pragma: no cover - makes this an async generator


@pytest.fixture
def patched(monkeypatch, valid_site_assessment_criteria_resource):
    """Patch everything the handlers call; returns the mocks."""
    server = MagicMock(name="server")
    server.read_resource = AsyncMock(return_value=valid_site_assessment_criteria_resource)
    mocks = SimpleNamespace(
        server=server,
        run=AsyncMock(return_value=SimpleNamespace(new_items=[])),
        run_streamed=MagicMock(return_value=SimpleNamespace(stream_events=_empty_events)),
        update_current_trace=MagicMock(name="update_current_trace"),
    )
    monkeypatch.setattr(agent_module, "configure_openai_client", MagicMock())
    monkeypatch.setattr(agent_module, "WorkspaceClient", MagicMock())
    monkeypatch.setattr(
        agent_module, "connect_healthy_mcp_servers", AsyncMock(return_value=([server], []))
    )
    monkeypatch.setattr(agent_module, "init_fpac_mcp_server", MagicMock(return_value=server))
    monkeypatch.setattr(agent_module, "create_agent", MagicMock(return_value=MagicMock()))
    monkeypatch.setattr(agent_module.Runner, "run", mocks.run)
    monkeypatch.setattr(agent_module.Runner, "run_streamed", mocks.run_streamed)
    monkeypatch.setattr(agent_module.mlflow, "update_current_trace", mocks.update_current_trace)
    return mocks


def _run_invoke(request):
    return asyncio.run(agent_module.invoke_handler(request))


def _run_stream(request):
    async def collect():
        return [event async for event in agent_module.stream_handler(request)]

    return asyncio.run(collect())


def _aoi_request() -> ResponsesAgentRequest:
    return ResponsesAgentRequest(
        input=[{"role": "user", "content": "screen the selected site"}],
        custom_inputs=AOI_CUSTOM_INPUTS,
    )


def test_invoke_does_not_pass_custom_inputs_to_model(patched):
    _run_invoke(_aoi_request())

    messages = patched.run.await_args.args[1]
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "screen the selected site"
    assert "coordinates" not in repr(messages)


def test_stream_does_not_pass_custom_inputs_to_model(patched):
    assert _run_stream(_aoi_request()) == []

    messages = patched.run_streamed.call_args.kwargs["input"]
    assert messages[0]["content"] == "screen the selected site"
    assert "coordinates" not in repr(messages)


@pytest.mark.parametrize("run_handler", [_run_invoke, _run_stream], ids=["invoke", "stream"])
def test_conversation_id_sets_trace_session(patched, run_handler):
    request = ResponsesAgentRequest(
        input=[{"role": "user", "content": "hi"}],
        context={"conversation_id": "conv-1", "user_id": "user@example.gov"},
    )

    run_handler(request)

    patched.update_current_trace.assert_called_once_with(
        metadata={"mlflow.trace.session": "conv-1"}
    )
