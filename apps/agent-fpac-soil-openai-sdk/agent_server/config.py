"""Runtime configuration for the FPAC Soil agent.

This module is pure (stdlib only) so it can be imported and tested without
Databricks credentials. Environment variables are read at call time, not at
import time.
"""

import functools
import os
from collections.abc import Callable
from pathlib import Path

# Unity Catalog model service name. The workspace no longer serves the legacy
# ``databricks-*`` endpoint names, and the Apps "Model" resource injects this form.
DEFAULT_AGENT_MODEL = "models.ai.gpt-5-6-luna"
DEFAULT_FPAC_MCP_URL = "https://mcp-fpac-soil-7474654188777746.aws.databricksapps.com/mcp"
DEFAULT_FPAC_MCP_TIMEOUT_SECONDS = 180.0

PROMPT_PATH = Path(__file__).parent / "prompts" / "system_prompt.txt"


def _env_or_default(name: str, default: str) -> str:
    """Return the stripped env value, or ``default`` when unset or blank."""
    value = os.environ.get(name, "").strip()
    return value or default


def agent_model() -> str:
    """Unity Catalog model service for the agent (env ``AGENT_MODEL``)."""
    return _env_or_default("AGENT_MODEL", DEFAULT_AGENT_MODEL)


class McpServerLookupError(RuntimeError):
    """``FPAC_MCP_APP`` could not be resolved; the message is fixed text."""


# App name -> resolved MCP URL, once per process.
_RESOLVED_MCP_URLS: dict[str, str] = {}


def fpac_mcp_app() -> str | None:
    """Name of the fpac-soil-mcp server app (env ``FPAC_MCP_APP``, from the ``mcp_server``
    app resource via ``valueFrom``), or None when unset or blank."""
    return os.environ.get("FPAC_MCP_APP", "").strip() or None


def fpac_mcp_url(app_url_lookup: Callable[[str], str | None] | None = None) -> str:
    """URL of the fpac-soil-mcp server.

    Order: an explicit ``FPAC_MCP_URL`` (local runs, tests); else the URL of the app
    named by ``FPAC_MCP_APP``, looked up once per process with ``app_url_lookup``
    (app name -> app base URL) plus ``/mcp``; else the default. A set ``FPAC_MCP_APP``
    that cannot be resolved raises rather than falling back to the default server.

    Raises:
        McpServerLookupError: if ``FPAC_MCP_APP`` is set and the lookup fails, is not
            available, or returns something other than an ``https://`` URL.
    """
    explicit = os.environ.get("FPAC_MCP_URL", "").strip()
    if explicit:
        return explicit
    app = fpac_mcp_app()
    if app is None:
        return DEFAULT_FPAC_MCP_URL
    if app in _RESOLVED_MCP_URLS:
        return _RESOLVED_MCP_URLS[app]
    if app_url_lookup is None:
        raise McpServerLookupError("FPAC_MCP_APP is set but no app lookup is available.")
    try:
        base = app_url_lookup(app)
    except Exception:  # noqa: BLE001 - any lookup failure is one bounded error
        raise McpServerLookupError("Could not resolve FPAC_MCP_APP to an app URL.") from None
    if not isinstance(base, str) or not base.startswith("https://"):
        raise McpServerLookupError("FPAC_MCP_APP did not resolve to an https URL.")
    url = f"{base.rstrip('/')}/mcp"
    _RESOLVED_MCP_URLS[app] = url
    return url


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
    """Return True for GPT-5 models, which need ``reasoning_effort="none"`` for tools.

    Matches both ``models.ai.gpt-5-*`` service names and legacy ``databricks-gpt-5-*`` names.
    """
    return model.rsplit(".", 1)[-1].removeprefix("databricks-").startswith("gpt-5")


@functools.lru_cache(maxsize=1)
def load_system_prompt() -> str:
    """Load the chat system prompt once."""
    return PROMPT_PATH.read_text(encoding="utf-8").strip()
