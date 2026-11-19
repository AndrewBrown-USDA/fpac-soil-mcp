"""Map tool results: body for the model, display geometry in result ``_meta`` (ADR 0017)."""

from __future__ import annotations

import functools
from collections.abc import Callable
from typing import Any, Protocol

from fastmcp.tools import ToolResult

from fpac_soil_mcp.models.map import MAP_META_KEY, MapBlock


class MapResponse(Protocol):
    """A tool response model that carries a ``map`` block."""

    map: MapBlock

    def model_dump(self, *, mode: str = ...) -> dict[str, Any]: ...


def meta_tool(func: Callable[..., MapResponse]) -> Callable[..., ToolResult]:
    """Wrap a sync map tool so its display geometry goes to result ``_meta``.

    The body (``structured_content`` and the one JSON text block) is the model
    dump, which has no display data. The display, when ``include_map`` built
    one, goes under ``_meta[MAP_META_KEY]``.
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> ToolResult:
        result = func(*args, **kwargs)
        body = result.model_dump(mode="json")
        display = result.map.display
        meta = {MAP_META_KEY: display.model_dump(mode="json")} if display is not None else None
        # content=body: FastMCP serializes the dict to one compact JSON text block,
        # the same text it wrote for a returned Pydantic model before (see STATE_59).
        return ToolResult(content=body, structured_content=body, meta=meta)

    return wrapper


__all__ = ["meta_tool"]
