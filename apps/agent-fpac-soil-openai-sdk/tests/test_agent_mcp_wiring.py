"""Tests that both handlers connect the fpac-soil-mcp server and build the agent from it.

No network: McpServer, WorkspaceClient, the health check, create_agent, and Runner are
all patched. The decorated handlers return a coroutine or async generator, so they are
driven with asyncio.run (the app has no pytest-asyncio).
"""

import asyncio
import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from agent_server import agent as agent_module
from mlflow.types.responses import ResponsesAgentRequest

DEFAULT_URL = "https://mcp-fpac-soil-7474654188777746.aws.databricksapps.com/mcp"


def _request() -> ResponsesAgentRequest:
    return ResponsesAgentRequest(input=[{"role": "user", "content": "hi"}])


async def _empty_events():
    return
    yield  # pragma: no cover - makes this an async generator


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    for name in ("AGENT_MODEL", "FPAC_MCP_URL", "FPAC_MCP_TIMEOUT_SECONDS"):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def patched(monkeypatch):
    """Patch everything the handlers call; returns the mocks."""
    server = MagicMock(name="server")
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


@pytest.mark.parametrize("run_handler", [_run_invoke, _run_stream], ids=["invoke", "stream"])
def test_handler_healthy_path(patched, caplog, run_handler):
    with caplog.at_level(logging.INFO, logger=agent_module.__name__):
        run_handler()
    patched.configure_openai_client.assert_called_once_with()
    patched.init.assert_called_once_with(patched.workspace_client.return_value)
    servers_arg = patched.connect.await_args.args[1]
    assert servers_arg == [patched.server]
    patched.create_agent.assert_called_once_with(
        mcp_servers=[patched.server], tools_unavailable=False
    )
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
