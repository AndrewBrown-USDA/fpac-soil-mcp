"""Authenticated smoke check for the deployed FPAC Soil MCP app."""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Sequence
from urllib.parse import urlsplit

_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parents[1]
_APP_NAME = "mcp-fpac-soil"
_TOOL_NAME = "explain_fppa_screening_scope"


class SmokeError(RuntimeError):
    """A fixed, sanitized smoke-check failure."""


def _git(*args: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
    except Exception:  # noqa: BLE001 -- git metadata is best effort
        return "unknown"
    return result.stdout.strip() or "unknown"


def _git_sha() -> str:
    return _git("rev-parse", "HEAD")


def _resolve_endpoint(workspace_client: Any) -> str:
    """Resolve the app URL from the current workspace and append the MCP path."""
    try:
        app = workspace_client.apps.get(name=_APP_NAME)
        base_url = app.url
        parsed = urlsplit(base_url)
    except Exception:  # noqa: BLE001 -- do not surface SDK details or credentials
        raise SmokeError("Could not resolve the mcp-fpac-soil app URL.") from None
    if parsed.scheme != "https" or not parsed.netloc:
        raise SmokeError("The mcp-fpac-soil app did not provide a valid HTTPS URL.")
    if parsed.path.rstrip("/").endswith("/mcp"):
        return base_url.rstrip("/")
    return f"{base_url.rstrip('/')}/mcp"


def _run_as_auth(config: Any) -> Any:
    """Adapt fresh Databricks SDK auth headers to FastMCP's HTTP auth interface."""
    try:
        import httpx2
    except ImportError:
        raise SmokeError("The FastMCP HTTP auth dependency is unavailable.") from None

    class DatabricksRunAsAuth(httpx2.Auth):
        async def async_auth_flow(self, request: Any):
            try:
                headers = config.authenticate()
            except Exception:  # noqa: BLE001 -- sanitize SDK authentication errors
                raise SmokeError("Databricks run-as authentication failed.") from None
            for name, value in headers.items():
                request.headers[name] = value
            yield request

    return DatabricksRunAsAuth()


def _tool_name(tool: Any) -> str | None:
    if isinstance(tool, dict):
        name = tool.get("name")
    else:
        name = getattr(tool, "name", None)
    return name if isinstance(name, str) else None


def _valid_tool_result(result: Any) -> bool:
    is_error = getattr(result, "is_error", getattr(result, "isError", False))
    if is_error:
        return False
    content = getattr(result, "content", None)
    structured = getattr(result, "structured_content", getattr(result, "structuredContent", None))
    return bool(content) or structured is not None


async def _smoke(
    endpoint: str,
    auth: Any,
    client_factory: Any,
) -> None:
    """Initialize, discover, and call the static tool within one client context."""
    try:
        client = client_factory(endpoint, auth=auth)
        async with client:
            tools = await client.list_tools()
            if not any(_tool_name(tool) == _TOOL_NAME for tool in tools):
                raise SmokeError("The MCP server did not expose the expected smoke tool.")
            result = await client.call_tool(_TOOL_NAME, {})
            if not _valid_tool_result(result):
                raise SmokeError("The MCP smoke tool returned an invalid result.")
    except SmokeError:
        raise
    except Exception:  # noqa: BLE001 -- errors may contain sensitive SDK/HTTP details
        raise SmokeError("MCP initialization, discovery, or tool invocation failed.") from None


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke-test authenticated access to FPAC Soil MCP.")
    return parser.parse_args(argv)


async def run_async(
    *,
    workspace_client: Any | None = None,
    client_factory: Any | None = None,
) -> dict[str, str]:
    """Run the smoke check and return sanitized metadata only."""
    try:
        if workspace_client is None:
            from databricks.sdk import WorkspaceClient

            workspace_client = WorkspaceClient()
        endpoint = _resolve_endpoint(workspace_client)
        auth = _run_as_auth(workspace_client.config)
        if client_factory is None:
            from fastmcp import Client

            client_factory = Client
        await _smoke(endpoint, auth, client_factory)
    except SmokeError:
        raise
    except Exception:  # noqa: BLE001 -- avoid disclosing optional-import/auth details
        raise SmokeError("Could not initialize the Databricks-authenticated smoke client.") from None

    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "commit_sha": _git_sha(),
        "endpoint_host": urlsplit(endpoint).hostname or "unknown",
        "principal_label": "databricks-run-as",
        "auth_mode": "databricks-sdk-run-as",
        "session_mode": "stateful-streamable-http",
        "tool_name": _TOOL_NAME,
        "status": "success",
    }


async def run(argv: Sequence[str] | None = None) -> dict[str, str]:
    _parse_args(argv)
    return await run_async()


def main(argv: Sequence[str] | None = None) -> int:
    try:
        result = asyncio.run(run(argv))
    except SmokeError as exc:
        print(f"T2 smoke failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
