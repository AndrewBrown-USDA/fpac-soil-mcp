"""MCP request context utilities for metadata and tool execution (stub for G18)."""

from __future__ import annotations

from typing import Any


def extract_request_meta(context: Any = None) -> dict[str, Any]:
    """Extract request metadata dictionary from FastMCP Context (stub for G18).

    Args:
        context: Optional FastMCP Context instance.

    Returns:
        Dictionary of request metadata (currently empty stub).
    """
    if context is None:
        return {}
    meta = getattr(context, "meta", None)
    if isinstance(meta, dict):
        return meta
    return {}
