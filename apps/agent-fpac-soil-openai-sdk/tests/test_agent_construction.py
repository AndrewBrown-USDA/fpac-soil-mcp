"""Tests for create_agent (model, prompt, reasoning settings, and tools)."""

from unittest.mock import MagicMock

import pytest
from agent_server import agent as agent_module
from agent_server.config import load_system_prompt


@pytest.fixture(autouse=True)
def _clear_model_env(monkeypatch):
    monkeypatch.delenv("AGENT_MODEL", raising=False)


def test_default_agent():
    agent = agent_module.create_agent()
    assert agent.model == "models.ai.gpt-5-6-luna"
    assert agent.model_settings.reasoning.effort == "none"
    assert agent.tools == []
    assert agent.mcp_servers == []
    assert agent.instructions == load_system_prompt()


def test_non_gpt5_model_has_no_reasoning(monkeypatch):
    monkeypatch.setenv("AGENT_MODEL", "models.ai.claude-sonnet-4-5")
    agent = agent_module.create_agent()
    assert agent.model == "models.ai.claude-sonnet-4-5"
    assert agent.model_settings.reasoning is None


def test_tools_unavailable_note():
    agent = agent_module.create_agent(tools_unavailable=True)
    assert agent.instructions.startswith(load_system_prompt())
    assert agent.instructions.endswith(agent_module.TOOLS_UNAVAILABLE_NOTE)


def test_mcp_servers_passthrough():
    servers = [object()]
    agent = agent_module.create_agent(mcp_servers=servers)
    assert agent.mcp_servers is servers


def test_client_uses_ai_gateway(monkeypatch):
    # UC model service names only resolve on /ai-gateway; /serving-endpoints returns 404.
    client = MagicMock(spec=agent_module.AsyncDatabricksOpenAI)
    constructor = MagicMock(return_value=client)
    set_default = MagicMock()
    monkeypatch.setattr(agent_module, "AsyncDatabricksOpenAI", constructor)
    monkeypatch.setattr(agent_module, "set_default_openai_client", set_default)
    agent_module.configure_openai_client.cache_clear()
    assert agent_module.configure_openai_client() is client
    constructor.assert_called_once_with(use_ai_gateway=True)
    set_default.assert_called_once_with(client)


def test_template_tool_removed():
    assert not hasattr(agent_module, "get_current_time")
