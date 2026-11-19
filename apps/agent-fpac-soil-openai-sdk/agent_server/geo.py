"""Out-of-band AOI screening for the map panel (ADR 0016).

``POST /api/geo/screen`` calls the deployed MCP tools directly; it never runs the
model or opens an MLflow trace. The response has a browser-only ``display`` part,
which may contain geometry, and a server-built ``chat_summary`` that is assembled
from an allowlist and never contains geometry. Nothing here logs request bodies,
MCP arguments or MCP results, and nothing is cached between requests.
"""

import json
import logging
import math
import os
import secrets
from typing import Any, Literal

from agents.mcp.server import MCPServerStreamableHttp
from databricks.sdk import WorkspaceClient
from databricks_openai.agents import McpServer
from pydantic import BaseModel, Field, ValidationError

from agent_server.agent import init_fpac_mcp_server
from agent_server.config import local_dev_enabled

logger = logging.getLogger(__name__)

MAX_BODY_BYTES = 256 * 1024
DEFAULT_MAX_VERTICES = 2000
MAX_SUMMARY_MAP_UNITS = 10
MAX_SUMMARY_TEXT_CHARS = 2000
NON_PRIME_LIMITATION = (
    "Not-prime classification is a screening category only; it is not an official "
    "FPPA determination or a finding of exemption."
)
ANALYSIS_TOOL = "analyze_farmland_by_polygon"
CORRIDOR_TOOL = "analyze_corridor_fppa"
SOIL_POLYGONS_TOOL = "get_soil_polygons_by_geometry"
# Tools whose results carry an ADR 0017 ``map`` block; the only tools /api/geo/map calls.
MAP_TOOLS = (ANALYSIS_TOOL, CORRIDOR_TOOL, SOIL_POLYGONS_TOOL)

FARMLAND_CLASSES = (
    ("prime_farmland", "Prime farmland"),
    ("conditional_prime", "Prime farmland if conditions are met"),
    ("statewide_importance", "Farmland of statewide importance"),
    ("local_importance", "Farmland of local importance"),
    ("unique_farmland", "Unique farmland"),
    ("not_prime", "Not prime farmland"),
    ("unmapped", "Unmapped"),
    ("unknown", "Unknown classification"),
    ("total_fppa_protected", "Total FPPA-protected farmland"),
)


class GeoRequestError(Exception):
    """A request rejected with a bounded message that never echoes the input."""

    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


class PolygonGeometry(BaseModel):
    type: Literal["Polygon", "MultiPolygon"]
    coordinates: list[Any]


class ScreenRequest(BaseModel):
    geometry: PolygonGeometry
    name: str | None = Field(default=None, max_length=80)
    # The browser's active AOI reference, so the map summary and the chat use one reference.
    aoi_ref: str | None = Field(default=None, pattern=r"^aoi-[0-9a-f]{8}$")


def max_vertices() -> int:
    try:
        value = int(os.environ.get("GEO_MAX_VERTICES", DEFAULT_MAX_VERTICES))
    except ValueError:
        return DEFAULT_MAX_VERTICES
    return value if value > 0 else DEFAULT_MAX_VERTICES


def _is_position(value: Any) -> bool:
    return (
        isinstance(value, list)
        and 2 <= len(value) <= 3
        and all(isinstance(n, int | float) and not isinstance(n, bool) for n in value)
    )


def _ring_vertices(ring: Any) -> int:
    if not isinstance(ring, list) or len(ring) < 4 or not all(_is_position(p) for p in ring):
        raise GeoRequestError(422, "Each polygon ring needs at least 4 [x, y] positions.")
    return len(ring)


def _polygon_vertices(polygon: Any) -> int:
    if not isinstance(polygon, list) or not polygon:
        raise GeoRequestError(422, "A polygon needs at least one ring.")
    return sum(_ring_vertices(ring) for ring in polygon)


def count_vertices(geometry: PolygonGeometry) -> int:
    if geometry.type == "Polygon":
        return _polygon_vertices(geometry.coordinates)
    if not geometry.coordinates:
        raise GeoRequestError(422, "A MultiPolygon needs at least one polygon.")
    return sum(_polygon_vertices(polygon) for polygon in geometry.coordinates)


def parse_screen_request(raw: bytes) -> ScreenRequest:
    """Validate the raw body; every error message is fixed text."""
    if len(raw) > MAX_BODY_BYTES:
        raise GeoRequestError(422, f"Request body exceeds {MAX_BODY_BYTES // 1024} KB.")
    try:
        payload = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        raise GeoRequestError(422, "Request body must be JSON.") from None
    if not isinstance(payload, dict) or not isinstance(payload.get("geometry"), dict):
        raise GeoRequestError(422, "Request body needs a 'geometry' object.")
    if payload["geometry"].get("type") not in ("Polygon", "MultiPolygon"):
        raise GeoRequestError(422, "Geometry type must be Polygon or MultiPolygon.")
    try:
        request = ScreenRequest.model_validate(payload)
    except ValidationError:
        raise GeoRequestError(422, "Request does not match the screening schema.") from None
    limit = max_vertices()
    if count_vertices(request.geometry) > limit:
        raise GeoRequestError(422, f"Geometry has more than {limit} vertices.")
    return request


class ToolFailure(Exception):
    """An MCP tool reported an error (``isError`` or an ``error`` key)."""


def parse_tool_result(result: Any) -> dict[str, Any]:
    """Return the tool's JSON object from a ``CallToolResult``."""
    if getattr(result, "isError", False):
        raise ToolFailure
    data = getattr(result, "structuredContent", None)
    if isinstance(data, dict) and set(data) == {"result"} and isinstance(data["result"], dict):
        data = data["result"]
    if not isinstance(data, dict):
        data = None
        for item in getattr(result, "content", None) or []:
            text = getattr(item, "text", None)
            if not text:
                continue
            try:
                parsed = json.loads(text)
            except ValueError:
                continue
            if isinstance(parsed, dict):
                data = parsed
                break
    if data is None:
        raise ToolFailure
    if data.get("error"):
        raise ToolFailure
    return data


def _num(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return round(float(value), 1)


def _short_text(value: Any, limit: int = 120) -> str | None:
    if not isinstance(value, str):
        return None
    return value[:limit]


def _result_notice(value: Any) -> str | None:
    """Keep the MCP notice and add the not-prime interpretation limit.

    The notice must come from the MCP result (ADR 0003, ADR 0016 amendment
    2026-11-17). The limitation sentence never stands in for it: without an MCP
    notice this returns None, so the browser shows the result as invalid.
    """
    server_notice = _short_text(value, 800)
    if server_notice and server_notice.strip():
        return f"{server_notice} {NON_PRIME_LIMITATION}"[:1000]
    return None


def select_display_analysis(analysis: dict[str, Any]) -> dict[str, Any]:
    """Fields the map panel shows; browser-only."""
    urban = analysis.get("urban_screening")
    urban = urban if isinstance(urban, dict) else {}
    source = analysis.get("source")
    source = source if isinstance(source, dict) else {}
    units = []
    for unit in analysis.get("map_units") or []:
        if isinstance(unit, dict):
            units.append(
                {
                    "mukey": _short_text(unit.get("mukey"), 32),
                    "musym": _short_text(unit.get("musym"), 32),
                    "muname": _short_text(unit.get("muname")),
                    "farmlndcl": _short_text(unit.get("farmlndcl")),
                    "acres": _num(unit.get("calculated_acres")),
                    "pct": _num(unit.get("percentage_of_aoi")),
                }
            )
    return {
        "total_aoi_acres": _num(analysis.get("total_aoi_acres")),
        "status": _short_text(analysis.get("status"), 40),
        "coverage_status": _short_text(analysis.get("coverage_status"), 40),
        "farmland_summary": analysis.get("farmland_summary") or {},
        "urban_intersected": urban.get("is_urban_intersected")
        if isinstance(urban.get("is_urban_intersected"), bool)
        else None,
        "map_units": units,
        "source": {
            "service_name": _short_text(source.get("service_name")),
            "timestamp_utc": _short_text(source.get("timestamp_utc"), 40),
        },
    }


def build_chat_summary(analysis: dict[str, Any], aoi_ref: str) -> dict[str, Any]:
    """Allowlisted, geometry-free summary; the only screening data that may reach chat."""
    farmland = analysis.get("farmland_summary")
    farmland = farmland if isinstance(farmland, dict) else {}
    classes: dict[str, dict[str, float | None]] = {}
    for key, _label in FARMLAND_CLASSES:
        acres = _num(farmland.get(f"{key}_acres"))
        pct = _num(farmland.get(f"{key}_pct"))
        if acres is not None or pct is not None:
            classes[key] = {"acres": acres, "pct": pct}

    urban = analysis.get("urban_screening")
    urban = urban if isinstance(urban, dict) else {}
    urban_summary: dict[str, Any] = {}
    if isinstance(urban.get("is_urban_intersected"), bool):
        urban_summary["urban_intersected"] = urban["is_urban_intersected"]
    if _num(urban.get("urban_acres")) is not None:
        urban_summary["urban_acres"] = _num(urban.get("urban_acres"))

    units = [u for u in analysis.get("map_units") or [] if isinstance(u, dict)]
    units.sort(key=lambda u: _num(u.get("calculated_acres")) or 0.0, reverse=True)
    top_units = [
        {
            "musym": _short_text(u.get("musym"), 32),
            "muname": _short_text(u.get("muname")),
            "farmlndcl": _short_text(u.get("farmlndcl")),
            "acres": _num(u.get("calculated_acres")),
        }
        for u in units[:MAX_SUMMARY_MAP_UNITS]
    ]

    source = analysis.get("source")
    source = source if isinstance(source, dict) else {}
    return {
        "aoi_ref": aoi_ref,
        "total_aoi_acres": _num(analysis.get("total_aoi_acres")),
        "status": _short_text(analysis.get("status"), 40),
        "coverage_status": _short_text(analysis.get("coverage_status"), 40),
        "farmland_classes": classes,
        "urban_screening": urban_summary,
        "map_units": top_units,
        "source": {
            "service_name": _short_text(source.get("service_name")),
            "timestamp_utc": _short_text(source.get("timestamp_utc"), 40),
        },
        "regulatory_notice": _result_notice(analysis.get("regulatory_notice")),
    }


def failed_chat_summary(aoi_ref: str) -> dict[str, Any]:
    return {"aoi_ref": aoi_ref, "status": "screening_failed"}


def _fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:,.1f}"


def render_chat_summary_text(summary: dict[str, Any]) -> str:
    lines = ["Map screening result (preliminary)", f"AOI: {summary.get('aoi_ref')}"]
    if summary.get("status") == "screening_failed":
        lines.append("The screening failed; no soil results are available for this AOI.")
        return "\n".join(lines)[:MAX_SUMMARY_TEXT_CHARS]
    lines.append(
        f"Total area: {_fmt(summary.get('total_aoi_acres'))} acres; "
        f"coverage: {summary.get('coverage_status') or 'n/a'}"
    )
    if summary.get("status"):
        lines.append(f"Status: {summary['status']}")
    urban = summary.get("urban_screening") or {}
    if "urban_intersected" in urban:
        flag = "yes" if urban["urban_intersected"] else "no"
        lines.append(f"Intersects a 2020 Census Urban Area: {flag}")
    labels = dict(FARMLAND_CLASSES)
    classes = summary.get("farmland_classes") or {}
    if classes:
        lines.append("Farmland classes:")
        for key, values in classes.items():
            lines.append(
                f"- {labels.get(key, key)}: {_fmt(values.get('acres'))} ac "
                f"({_fmt(values.get('pct'))}%)"
            )
    units = summary.get("map_units") or []
    if units:
        lines.append("Largest map units:")
        for unit in units:
            lines.append(
                f"- {unit.get('musym') or '?'} {unit.get('muname') or ''}: "
                f"{_fmt(unit.get('acres'))} ac, {unit.get('farmlndcl') or 'n/a'}"
            )
    notice = summary.get("regulatory_notice")
    body = "\n".join(lines)
    if notice:
        room = MAX_SUMMARY_TEXT_CHARS - len(body) - len("\nNotice: ")
        body = f"{body}\nNotice: {notice[: max(room, 0)]}"
    return body[:MAX_SUMMARY_TEXT_CHARS]


def new_aoi_ref() -> str:
    return f"aoi-{secrets.token_hex(4)}"


async def _call_tool_untraced(server: McpServer, name: str, arguments: dict[str, Any]) -> Any:
    """Call an MCP tool without the ``@mlflow.trace`` wrapper on ``McpServer.call_tool``.

    ``databricks_openai`` decorates ``McpServer.call_tool`` with ``@mlflow.trace``, which
    records the full arguments (the AOI) and result (soil polygons) as a trace. The parent
    implementation makes the same call without tracing (ADR 0016).
    """
    return await MCPServerStreamableHttp.call_tool(server, name, arguments)


# Result ``_meta`` key holding map display geometry (ADR 0017, Plan 59). The app does
# not import server code, so the key string is repeated here.
MAP_META_KEY = "gov.usda.fpac-soil/map"
DISPLAY_CRS = "EPSG:4326"
# Per-layer display fields from ``_meta`` and their values when a layer has none.
_LAYER_DISPLAY_DEFAULTS: dict[str, Any] = {
    "simplified": False,
    "simplify_tolerance_m": None,
    "truncated": False,
    "feature_count": None,
    "feature_collection": None,
}


def map_meta(raw: Any) -> dict[str, Any] | None:
    """Return the map display entry from a ``CallToolResult``'s ``_meta``, if any."""
    meta = getattr(raw, "meta", None)
    entry = meta.get(MAP_META_KEY) if isinstance(meta, dict) else None
    return entry if isinstance(entry, dict) else None


def map_block(result: dict[str, Any], meta: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Build the browser map block from the body descriptors and the ``_meta`` display.

    The shape is the pre-Plan 59 block: ``{display_crs, bounds, warnings, layers}``,
    each layer the body descriptor plus its display fields. A layer is
    ``inline_geojson`` only when ``_meta`` holds its feature collection. Browser-only.
    """
    block = result.get("map")
    if not isinstance(block, dict):
        return None
    display = meta if isinstance(meta, dict) else {}
    entries = display.get("layers")
    entries = entries if isinstance(entries, dict) else {}
    layers = []
    for layer in block.get("layers") or []:
        if not isinstance(layer, dict):
            continue
        entry = entries.get(layer.get("id"))
        entry = entry if isinstance(entry, dict) else {}
        merged = {
            **layer,
            **{key: entry.get(key, default) for key, default in _LAYER_DISPLAY_DEFAULTS.items()},
        }
        if not isinstance(merged["feature_collection"], dict):
            merged["feature_collection"] = None
        merged["delivery"] = "omitted" if merged["feature_collection"] is None else "inline_geojson"
        layers.append(merged)
    bounds = display.get("bounds")
    warnings = display.get("warnings")
    crs = display.get("display_crs")
    return {
        "display_crs": crs if isinstance(crs, str) else DISPLAY_CRS,
        "bounds": bounds if isinstance(bounds, list) else None,
        "warnings": warnings if isinstance(warnings, list) else [],
        "layers": layers,
    }


async def screen_aoi(request: ScreenRequest) -> dict[str, Any]:
    """Screen one AOI without model invocation or MLflow trace capture."""
    geometry = request.geometry.model_dump()
    aoi_ref = request.aoi_ref or new_aoi_ref()
    try:
        async with init_fpac_mcp_server(
            None if local_dev_enabled() else WorkspaceClient()
        ) as server:
            analysis_result = await _call_tool_untraced(
                server,
                ANALYSIS_TOOL,
                {"geojson": geometry, "include_map": True},
            )
    except Exception as exc:  # noqa: BLE001 - every MCP failure becomes a bounded 502
        # Exception text may echo tool arguments, so only the type is logged.
        logger.warning("AOI screening MCP call failed (%s).", type(exc).__name__)
        raise GeoRequestError(502, "screening_unavailable") from None

    try:
        analysis = parse_tool_result(analysis_result)
    except ToolFailure:
        logger.warning("AOI screening tool reported an error.")
        summary = failed_chat_summary(aoi_ref)
        return {
            "aoi_ref": aoi_ref,
            "display": {"error": "screening_failed", "regulatory_notice": None},
            "chat_summary": summary,
            "chat_summary_text": render_chat_summary_text(summary),
        }

    summary = build_chat_summary(analysis, aoi_ref)
    block = map_block(analysis, map_meta(analysis_result))
    return {
        "aoi_ref": aoi_ref,
        "display": {
            "analysis": select_display_analysis(analysis),
            "map": block,
            "regulatory_notice": summary["regulatory_notice"],
        },
        "chat_summary": summary,
        "chat_summary_text": render_chat_summary_text(summary),
    }


def parse_corridor_request(raw: bytes) -> Any:
    """Validate a direct corridor request using the shared corridor-context contract."""
    from agent_server.corridor_context import InvalidCorridor, parse_active_corridor

    if len(raw) > MAX_BODY_BYTES:
        raise GeoRequestError(413, f"Request body exceeds {MAX_BODY_BYTES // 1024} KB.")
    try:
        payload = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        raise GeoRequestError(400, "Request body must be JSON.") from None
    allowed = {
        "corridor_ref",
        "centerline",
        "buffer_distance",
        "buffer_units",
        "alternatives",
        "indirect_geometry",
    }
    if not isinstance(payload, dict) or set(payload) - allowed:
        raise GeoRequestError(400, "Request does not match the corridor schema.")
    try:
        return parse_active_corridor(payload)
    except InvalidCorridor:
        raise GeoRequestError(400, "Request does not match the corridor schema.") from None


def _corridor_number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    try:
        number = float(value)
    except OverflowError:
        return None
    return round(number, 1) if math.isfinite(number) else None


def select_display_corridor(result: dict[str, Any], corridor: Any) -> dict[str, Any]:
    """Return bounded, allowlisted corridor facts for the browser; geometry stays in map."""
    impact = result.get("impact_breakdown")
    impact = impact if isinstance(impact, dict) else {}
    segments = result.get("county_segments")
    display_segments = []
    if isinstance(segments, list):
        for segment in segments[:100]:
            if not isinstance(segment, dict):
                continue
            display_segments.append(
                {
                    "county_name": _short_text(segment.get("county_name"), 100),
                    "state_name": _short_text(segment.get("state_name"), 80),
                    "direct_acres": _corridor_number(segment.get("direct_acres")),
                    "indirect_acres": _corridor_number(segment.get("indirect_acres")),
                    "total_segment_acres": _corridor_number(segment.get("total_segment_acres")),
                    "coverage_status": _short_text(segment.get("coverage_status"), 40),
                }
            )
    alternatives = result.get("alternatives")
    display_alternatives = []
    if isinstance(alternatives, list):
        for alternative in alternatives[:10]:
            if not isinstance(alternative, dict):
                continue
            display_alternatives.append(
                {
                    "alternative_id": _short_text(alternative.get("alternative_id"), 100),
                    "total_project_acres": _corridor_number(alternative.get("total_project_acres")),
                    "direct_acres": _corridor_number(alternative.get("direct_acres")),
                    "indirect_acres": _corridor_number(alternative.get("indirect_acres")),
                    "total_fppa_protected_acres": _corridor_number(
                        alternative.get("total_fppa_protected_acres")
                    ),
                    "total_fppa_protected_pct": _corridor_number(
                        alternative.get("total_fppa_protected_pct")
                    ),
                }
            )
    return {
        "corridor_ref": corridor.corridor_ref,
        "status": "preliminary_screening",
        "buffer_distance": _corridor_number(result.get("buffer_distance")),
        "buffer_units": _short_text(result.get("buffer_units"), 16),
        "impact_breakdown": {
            "direct_acres": _corridor_number(impact.get("direct_acres")),
            "indirect_acres": _corridor_number(impact.get("indirect_acres")),
            "total_project_acres": _corridor_number(impact.get("total_project_acres")),
        },
        "composite_relative_rating": _corridor_number(result.get("composite_relative_rating")),
        "county_segments": display_segments,
        "alternatives": display_alternatives,
        "regulatory_notice": _result_notice(result.get("regulatory_notice")),
    }


async def screen_corridor(corridor: Any) -> dict[str, Any]:
    """Screen a validated corridor with one stateless, untraced MCP call."""
    arguments: dict[str, Any] = {
        "centerline": corridor.centerline,
        "buffer_distance": corridor.buffer_distance,
        "buffer_units": corridor.buffer_units,
        "alternatives": [
            {"alternative_id": f"Alternative {index}", "centerline": line}
            for index, line in enumerate(corridor.alternatives, start=1)
        ],
        "include_map": True,
    }
    if corridor.indirect_geometry is not None:
        arguments["indirect_geometry"] = corridor.indirect_geometry
    try:
        async with init_fpac_mcp_server(
            None if local_dev_enabled() else WorkspaceClient()
        ) as server:
            raw = await _call_tool_untraced(server, CORRIDOR_TOOL, arguments)
    except Exception as exc:  # noqa: BLE001 - exception text may contain geometry
        logger.warning("Corridor screening MCP call failed (%s).", type(exc).__name__)
        raise GeoRequestError(502, "corridor_screening_unavailable") from None
    try:
        result = parse_tool_result(raw)
    except ToolFailure:
        logger.warning("Corridor screening tool reported an error.")
        raise GeoRequestError(502, "corridor_screening_unavailable") from None
    return {
        "display": select_display_corridor(result, corridor),
        "map": map_block(result, map_meta(raw)),
        "regulatory_notice": _result_notice(result.get("regulatory_notice")),
        "status": "preliminary_screening",
    }


class MapRequest(BaseModel):
    tool: Literal[
        "analyze_farmland_by_polygon", "analyze_corridor_fppa", "get_soil_polygons_by_geometry"
    ]
    arguments: dict[str, Any]
    active_aoi: dict[str, Any] | None = None


def parse_map_request(raw: bytes) -> tuple[str, dict[str, Any]]:
    """Validate a ``/api/geo/map`` body and return ``(tool, arguments)``.

    ``aoi_ref`` arguments are replaced with the ``active_aoi`` geometry and
    ``include_map`` is forced on. Every error message is fixed text.
    """
    # Imported here: aoi_context imports this module lazily for the same reason.
    from agent_server.aoi_context import InvalidAoi, parse_active_aoi, substitute_arguments

    if len(raw) > MAX_BODY_BYTES:
        raise GeoRequestError(413, f"Request body exceeds {MAX_BODY_BYTES // 1024} KB.")
    try:
        payload = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        raise GeoRequestError(400, "Request body must be JSON.") from None
    if not isinstance(payload, dict):
        raise GeoRequestError(400, "Request body must be a JSON object.")
    if payload.get("tool") not in MAP_TOOLS:
        raise GeoRequestError(400, "Tool is not available for maps.")
    try:
        request = MapRequest.model_validate(payload)
    except ValidationError:
        raise GeoRequestError(400, "Request does not match the map schema.") from None
    arguments = dict(request.arguments)
    if request.active_aoi is not None:
        try:
            aoi = parse_active_aoi(request.active_aoi)
        except InvalidAoi:
            raise GeoRequestError(400, "active_aoi is invalid.") from None
        arguments = substitute_arguments(arguments, aoi) or arguments
    arguments["include_map"] = True
    return request.tool, arguments


async def map_for_tool(tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Call one map tool without MLflow trace capture and return its display result.

    Raises ``GeoRequestError(502)`` on MCP failure or a tool error; nothing from the
    arguments or the result is logged or echoed.
    """
    try:
        async with init_fpac_mcp_server(
            None if local_dev_enabled() else WorkspaceClient()
        ) as server:
            raw = await _call_tool_untraced(server, tool, arguments)
    except Exception as exc:  # noqa: BLE001 - every MCP failure becomes a bounded 502
        logger.warning("Map MCP call failed (%s).", type(exc).__name__)
        raise GeoRequestError(502, "map_unavailable") from None
    try:
        result = parse_tool_result(raw)
    except ToolFailure:
        logger.warning("Map tool reported an error.")
        raise GeoRequestError(502, "map_unavailable") from None
    authority = result.get("authority")
    return {
        "tool": tool,
        "map": map_block(result, map_meta(raw)),
        "regulatory_notice": _result_notice(result.get("regulatory_notice")),
        "authority": authority if isinstance(authority, dict) else None,
        "status": _short_text(result.get("status"), 40),
        "coverage_status": _short_text(result.get("coverage_status"), 40),
    }
