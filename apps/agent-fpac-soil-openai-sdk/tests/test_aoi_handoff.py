"""Focused evidence for AOI request/output and privacy boundaries."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from agent_server.history import sanitize_custom_inputs


def test_custom_inputs_keep_only_opaque_session_metadata():
    inputs = {
        "session_id": "session-123",
        "active_aoi_id": "aoi-opaque",
        "geometry": {"type": "Polygon", "coordinates": [[[1, 2], [3, 4], [1, 2]]]},
        "bbox": [1, 2, 3, 4],
        "parcel_properties": {"owner": "producer"},
    }

    assert sanitize_custom_inputs(inputs) == {"session_id": "session-123"}


def test_custom_inputs_with_no_session_id_are_not_forwarded():
    assert sanitize_custom_inputs({"active_aoi_id": "aoi-opaque"}) == {}
    assert sanitize_custom_inputs(None) == {}


def test_invoke_does_not_pass_custom_inputs_to_model(monkeypatch):
    from agent_server import agent as agent_module
    from mlflow.types.responses import ResponsesAgentRequest

    request = ResponsesAgentRequest(
        input=[{"role": "user", "content": "screen the selected site"}],
        custom_inputs={
            "session_id": "session-123",
            "geometry": {"type": "Polygon", "coordinates": [[[1, 2], [3, 4], [1, 2]]]},
        },
    )
    server = MagicMock()
    runner_result = SimpleNamespace(new_items=[])

    monkeypatch.setattr(agent_module, "configure_openai_client", MagicMock())
    monkeypatch.setattr(agent_module, "WorkspaceClient", MagicMock())
    monkeypatch.setattr(
        agent_module,
        "connect_healthy_mcp_servers",
        AsyncMock(return_value=([server], [])),
    )
    monkeypatch.setattr(
        agent_module,
        "init_fpac_mcp_server",
        MagicMock(return_value=server),
    )
    monkeypatch.setattr(
        agent_module,
        "create_agent",
        MagicMock(return_value=MagicMock()),
    )
    run = AsyncMock(return_value=runner_result)
    monkeypatch.setattr(agent_module.Runner, "run", run)
    monkeypatch.setattr(agent_module.mlflow, "update_current_trace", MagicMock())

    asyncio.run(agent_module.invoke_handler(request))

    assert run.await_args.args[1][0]["role"] == "user"
    assert run.await_args.args[1][0]["content"] == "screen the selected site"
    assert "coordinates" not in repr(run.await_args.args[1])
