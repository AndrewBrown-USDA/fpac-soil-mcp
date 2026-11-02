"""The map AOI as chat session context (ADR 0016).

The browser keeps one AOI per conversation and sends it with each chat turn as
``custom_inputs.active_aoi = {aoi_ref, geometry, summary}``. This module validates it
with the screening route's limits, writes a short instruction note for the model (the
reference and the latest screening summary, never coordinates), and swaps the geometry
into MCP tool arguments that name the AOI reference. Nothing is kept between requests.
"""

import copy
import json
import logging
import re
from dataclasses import dataclass
from typing import Any

from databricks_openai.agents import McpServer
from pydantic import ValidationError

logger = logging.getLogger(__name__)

AOI_REF_PATTERN = re.compile(r"aoi-[0-9a-f]{8}")
GEOMETRY_ARGUMENTS = ("geojson", "geometry")


class InvalidAoi(Exception):
    """An ``active_aoi`` that is ignored; the message is fixed text, never input."""


@dataclass(frozen=True)
class ActiveAoi:
    aoi_ref: str
    geometry: dict[str, Any]
    summary_text: str | None = None
    total_acres: float | None = None


def _number(value: Any) -> float | None:
    if isinstance(value, int | float) and not isinstance(value, bool):
        return float(value)
    return None


def parse_active_aoi(raw: Any) -> ActiveAoi:
    """Validate one ``active_aoi`` object with the ``/api/geo/screen`` limits."""
    # Imported here: geo imports agent, which imports this module.
    from agent_server import geo

    if not isinstance(raw, dict):
        raise InvalidAoi("active_aoi is not an object")
    aoi_ref = raw.get("aoi_ref")
    if not isinstance(aoi_ref, str) or not AOI_REF_PATTERN.fullmatch(aoi_ref):
        raise InvalidAoi("aoi_ref does not match aoi-<8 hex>")
    geometry = raw.get("geometry")
    if not isinstance(geometry, dict) or geometry.get("type") not in ("Polygon", "MultiPolygon"):
        raise InvalidAoi("geometry is not a Polygon or MultiPolygon")
    try:
        size = len(json.dumps(geometry))
    except (TypeError, ValueError):
        raise InvalidAoi("geometry is not JSON") from None
    if size > geo.MAX_BODY_BYTES:
        raise InvalidAoi("geometry exceeds the size limit")
    try:
        parsed = geo.PolygonGeometry.model_validate(geometry)
        vertices = geo.count_vertices(parsed)
    except (ValidationError, geo.GeoRequestError):
        raise InvalidAoi("geometry is malformed") from None
    if vertices > geo.max_vertices():
        raise InvalidAoi("geometry exceeds the vertex limit")

    summary_text: str | None = None
    total_acres: float | None = None
    summary = raw.get("summary")
    if isinstance(summary, dict):
        total_acres = _number(summary.get("total_aoi_acres"))
        try:
            summary_text = geo.render_chat_summary_text({**summary, "aoi_ref": aoi_ref})
        except (AttributeError, TypeError, ValueError):
            summary_text = None
    return ActiveAoi(aoi_ref, parsed.model_dump(), summary_text, total_acres)


def read_active_aoi(request: Any) -> ActiveAoi | None:
    """Return the request's active AOI, or None when absent or invalid; never raises."""
    custom_inputs = getattr(request, "custom_inputs", None)
    if not isinstance(custom_inputs, dict) or custom_inputs.get("active_aoi") is None:
        return None
    try:
        return parse_active_aoi(custom_inputs["active_aoi"])
    except InvalidAoi as exc:
        logger.info("Ignoring active_aoi: %s", exc)
        return None


def instruction_note(aoi: ActiveAoi) -> str:
    """The per-turn note for the model: reference, acres and summary, no coordinates."""
    size = f", about {aoi.total_acres:,.1f} acres" if aoi.total_acres is not None else ""
    lines = [
        (
            "The user has a map area of interest (AOI) attached to this conversation: "
            f"{aoi.aoi_ref}{size}."
        ),
        (
            f'To run a tool on this AOI, pass the string "{aoi.aoi_ref}" as the tool\'s '
            "`geojson` or `geometry` argument; the app substitutes the AOI shape. Do not ask "
            "the user for the GeoJSON and do not write coordinates yourself."
        ),
    ]
    if aoi.summary_text:
        lines += ["Latest map screening of this AOI:", aoi.summary_text]
    else:
        lines.append("No map screening summary is attached; run the tools on the AOI as needed.")
    return "\n".join(lines)


def substitute_arguments(arguments: dict[str, Any] | None, aoi: ActiveAoi) -> dict[str, Any] | None:
    """Replace a ``geojson``/``geometry`` argument equal to the AOI reference."""
    if not arguments:
        return arguments
    result = dict(arguments)
    for key in GEOMETRY_ARGUMENTS:
        value = result.get(key)
        if isinstance(value, str) and value.strip() == aoi.aoi_ref:
            result[key] = copy.deepcopy(aoi.geometry)
    return result


def bind_active_aoi(server: McpServer, aoi: ActiveAoi) -> McpServer:
    """Make ``server.call_tool`` substitute the AOI; the traced ``McpServer`` path stays."""
    original = server.call_tool

    async def call_tool(tool_name: str, arguments: dict[str, Any] | None, **kwargs: Any) -> Any:
        return await original(tool_name, substitute_arguments(arguments, aoi), **kwargs)

    server.call_tool = call_tool
    return server
