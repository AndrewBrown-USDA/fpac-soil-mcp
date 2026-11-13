"""Tests for agent_server.config (env getters and the chat system prompt)."""

from unittest.mock import MagicMock

import pytest
from agent_server import config
from common.matching import policy_missing_requirements

ENV_NAMES = ("AGENT_MODEL", "FPAC_MCP_URL", "FPAC_MCP_APP", "FPAC_MCP_TIMEOUT_SECONDS")
DEFAULT_URL = "https://mcp-fpac-soil-7474654188777746.aws.databricksapps.com/mcp"
DEV_BASE = "https://mcp-fpac-soil-dev-0000.aws.databricksapps.com"


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    for name in ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(config, "_RESOLVED_MCP_URLS", {})


def _assert_defaults():
    assert config.agent_model() == "models.ai.gpt-5-6-luna"
    assert (
        config.fpac_mcp_url() == "https://mcp-fpac-soil-7474654188777746.aws.databricksapps.com/mcp"
    )
    assert config.fpac_mcp_timeout_seconds() == 180.0


def test_defaults_when_unset():
    _assert_defaults()


def test_defaults_when_blank(monkeypatch):
    for name in ENV_NAMES:
        monkeypatch.setenv(name, "  ")
    _assert_defaults()


def test_env_overrides(monkeypatch):
    monkeypatch.setenv("AGENT_MODEL", " databricks-claude-sonnet-4-5 ")
    monkeypatch.setenv("FPAC_MCP_URL", "https://example.com/mcp")
    monkeypatch.setenv("FPAC_MCP_TIMEOUT_SECONDS", "45")
    assert config.agent_model() == "databricks-claude-sonnet-4-5"
    assert config.fpac_mcp_url() == "https://example.com/mcp"
    assert config.fpac_mcp_timeout_seconds() == 45.0


@pytest.mark.parametrize("raw", ["abc", "0", "-5"])
def test_invalid_timeout_raises(monkeypatch, raw):
    monkeypatch.setenv("FPAC_MCP_TIMEOUT_SECONDS", raw)
    with pytest.raises(ValueError, match="FPAC_MCP_TIMEOUT_SECONDS"):
        config.fpac_mcp_timeout_seconds()


@pytest.mark.parametrize(
    ("model", "expected"),
    [
        ("models.ai.gpt-5-6-luna", True),
        ("system.ai.gpt-5-6-sol", True),
        ("databricks-gpt-5-6-luna", True),
        ("models.ai.claude-sonnet-4-5", False),
        ("databricks-claude-sonnet-4-5", False),
        ("models.ai.gpt-oss-120b", False),
    ],
)
def test_reasoning_effort_rule(model, expected):
    assert config.uses_reasoning_effort_none(model) is expected


def test_default_model_is_not_disabled_model():
    # databricks-claude-sonnet-5-5 is disabled in this workspace (403 PERMISSION_DENIED).
    assert config.DEFAULT_AGENT_MODEL != "databricks-claude-sonnet-5-5"


@pytest.mark.parametrize(
    "phrase",
    ["7 CFR Part 657", "AD-1006", "NRCS-CPA-106", "do not estimate, infer, or invent values"],
)
def test_prompt_contains_required_phrases(phrase):
    assert phrase in config.load_system_prompt()


def test_prompt_carries_shared_policy():
    assert policy_missing_requirements(config.load_system_prompt()) == []


def test_prompt_preserves_site_assessment_interview_and_confirmation_rules():
    prompt = config.load_system_prompt().lower()
    assert "use the validated criteria resource supplied in context as the sole source" in prompt
    assert "ask one criterion at a time" in prompt
    assert "preserve unknown, unavailable, and skipped values as such" in prompt
    assert "when the user has an attached aoi during the site assessment interview" in prompt
    assert "request combined cdl context automatically once" in prompt
    assert "never supply or score the criterion 2 site-perimeter percentage" in prompt
    assert "do not submit or score before confirmation" in prompt
    assert "complete answer/evidence summary" in prompt


@pytest.mark.parametrize(
    "phrase",
    [
        "evaluation agent",
        "[forced-tool]",
        "get_farmland_classification",
        "analyze_",
        "calculate_preliminary_lesa",
        "explain_fppa_screening_scope",
    ],
)
def test_prompt_does_not_steer(phrase):
    assert phrase not in config.load_system_prompt()


def test_prompt_is_cached():
    assert config.load_system_prompt() is config.load_system_prompt()


def test_mcp_app_resolves_through_lookup_once(monkeypatch):
    monkeypatch.setenv("FPAC_MCP_APP", " mcp-fpac-soil-dev ")
    calls = []

    def lookup(name):
        calls.append(name)
        return DEV_BASE + "/"

    assert config.fpac_mcp_url(lookup) == DEV_BASE + "/mcp"
    assert config.fpac_mcp_url(lookup) == DEV_BASE + "/mcp"
    assert calls == ["mcp-fpac-soil-dev"]


def test_explicit_url_wins_over_mcp_app(monkeypatch):
    monkeypatch.setenv("FPAC_MCP_APP", "mcp-fpac-soil-dev")
    monkeypatch.setenv("FPAC_MCP_URL", "https://example.com/mcp")
    lookup = MagicMock()
    assert config.fpac_mcp_url(lookup) == "https://example.com/mcp"
    lookup.assert_not_called()


def test_default_without_mcp_app_does_not_look_up():
    lookup = MagicMock()
    assert config.fpac_mcp_url(lookup) == DEFAULT_URL
    lookup.assert_not_called()


@pytest.mark.parametrize(
    ("lookup", "message"),
    [
        (None, "no app lookup"),
        (MagicMock(side_effect=RuntimeError("PERMISSION_DENIED R6-MARKER")), "Could not resolve"),
        (MagicMock(return_value=None), "https URL"),
        (MagicMock(return_value="http://insecure.example"), "https URL"),
    ],
)
def test_mcp_app_lookup_failures_never_fall_back(monkeypatch, lookup, message):
    monkeypatch.setenv("FPAC_MCP_APP", "mcp-fpac-soil-dev")
    with pytest.raises(config.McpServerLookupError, match=message) as excinfo:
        config.fpac_mcp_url(lookup)
    assert "R6-MARKER" not in str(excinfo.value)
    assert config._RESOLVED_MCP_URLS == {}
