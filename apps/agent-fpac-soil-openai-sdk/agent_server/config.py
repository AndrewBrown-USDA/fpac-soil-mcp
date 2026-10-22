"""Runtime configuration for the FPAC Soil agent.

This module is pure (stdlib only) so it can be imported and tested without
Databricks credentials. Environment variables are read at call time, not at
import time.
"""

import functools
import os
from pathlib import Path

DEFAULT_AGENT_MODEL = "databricks-gpt-5-6-luna"
DEFAULT_FPAC_MCP_URL = "https://mcp-fpac-soil-7474654188777746.aws.databricksapps.com/mcp"
DEFAULT_FPAC_MCP_TIMEOUT_SECONDS = 180.0

PROMPT_PATH = Path(__file__).parent / "prompts" / "system_prompt.txt"


def _env_or_default(name: str, default: str) -> str:
    """Return the stripped env value, or ``default`` when unset or blank."""
    value = os.environ.get(name, "").strip()
    return value or default


def agent_model() -> str:
    """Model serving endpoint for the agent (env ``AGENT_MODEL``)."""
    return _env_or_default("AGENT_MODEL", DEFAULT_AGENT_MODEL)


def fpac_mcp_url() -> str:
    """URL of the fpac-soil-mcp server (env ``FPAC_MCP_URL``)."""
    return _env_or_default("FPAC_MCP_URL", DEFAULT_FPAC_MCP_URL)


def fpac_mcp_timeout_seconds() -> float:
    """MCP client timeout in seconds (env ``FPAC_MCP_TIMEOUT_SECONDS``).

    Raises:
        ValueError: if the value is not a number or is not positive.
    """
    raw = os.environ.get("FPAC_MCP_TIMEOUT_SECONDS", "").strip()
    if not raw:
        return DEFAULT_FPAC_MCP_TIMEOUT_SECONDS
    try:
        value = float(raw)
    except ValueError:
        value = None
    if value is None or not value > 0:
        msg = f"FPAC_MCP_TIMEOUT_SECONDS must be a positive number, got {raw!r}"
        raise ValueError(msg)
    return value


def uses_reasoning_effort_none(model: str) -> bool:
    """Return True for GPT-5 endpoints, which need ``reasoning_effort="none"`` for tools."""
    return model.startswith("databricks-gpt-5")


@functools.lru_cache(maxsize=1)
def load_system_prompt() -> str:
    """Load the chat system prompt once."""
    return PROMPT_PATH.read_text(encoding="utf-8").strip()
