"""Separate, request-scoped corridor context (ADR 0016)."""

import copy
import json
import math
import re
from dataclasses import dataclass
from typing import Any, Literal

from databricks_openai.agents import McpServer
from pydantic import BaseModel, ValidationError

from agent_server import geo

CORRIDOR_REF_PATTERN = re.compile(r"corridor-[0-9a-f]{8}")
CORRIDOR_TOOL = "analyze_corridor_fppa"
MAX_ALTERNATIVES = 10


class InvalidCorridor(Exception):
    """An invalid corridor context, ignored without exposing its contents."""


class LineGeometry(BaseModel):
    type: Literal["LineString"]
    coordinates: list[Any]


@dataclass(frozen=True)
class ActiveCorridor:
    corridor_ref: str
    centerline: dict[str, Any]
    buffer_distance: float
    buffer_units: Literal["feet", "meters", "miles"]
    alternatives: tuple[dict[str, Any], ...] = ()
    indirect_geometry: dict[str, Any] | None = None


def _line(raw: Any) -> dict[str, Any]:
    try:
        line = LineGeometry.model_validate(raw)
        coordinates = line.coordinates
        if len(coordinates) < 2 or not all(geo._is_position(point) for point in coordinates):
            raise InvalidCorridor("centerline is malformed")
        if any(
            not (-180 <= float(point[0]) <= 180 and -90 <= float(point[1]) <= 90)
            or not all(math.isfinite(float(value)) for value in point)
            for point in coordinates
        ):
            raise InvalidCorridor("centerline is malformed")
        return line.model_dump()
    except (ValidationError, TypeError, ValueError):
        raise InvalidCorridor("centerline is malformed") from None


def _polygon(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict) or raw.get("type") not in ("Polygon", "MultiPolygon"):
        raise InvalidCorridor("indirect geometry is malformed")
    try:
        size = len(json.dumps(raw, allow_nan=False))
        geometry = geo.PolygonGeometry.model_validate(raw)
        vertices = geo.count_vertices(geometry)
    except (TypeError, ValueError, ValidationError, geo.GeoRequestError):
        raise InvalidCorridor("indirect geometry is malformed") from None
    if size > geo.MAX_BODY_BYTES or vertices > geo.max_vertices():
        raise InvalidCorridor("indirect geometry exceeds limits")
    coordinates = geometry.coordinates
    polygons = [coordinates] if geometry.type == "Polygon" else coordinates
    for polygon in polygons:
        for ring in polygon:
            if ring[0] != ring[-1]:
                raise InvalidCorridor("indirect geometry is malformed")
            for point in ring:
                if not (
                    -180 <= float(point[0]) <= 180
                    and -90 <= float(point[1]) <= 90
                    and all(math.isfinite(float(value)) for value in point)
                ):
                    raise InvalidCorridor("indirect geometry is malformed")
    return geometry.model_dump()


def parse_active_corridor(raw: Any) -> ActiveCorridor:
    """Validate a corridor reference and bounded tool inputs."""
    if not isinstance(raw, dict):
        raise InvalidCorridor("active_corridor is not an object")
    reference = raw.get("corridor_ref")
    if not isinstance(reference, str) or not CORRIDOR_REF_PATTERN.fullmatch(reference):
        raise InvalidCorridor("corridor_ref is invalid")
    centerline = _line(raw.get("centerline"))
    distance = raw.get("buffer_distance")
    if isinstance(distance, bool) or not isinstance(distance, int | float):
        raise InvalidCorridor("buffer distance is invalid")
    if not math.isfinite(float(distance)) or distance <= 0:
        raise InvalidCorridor("buffer distance is invalid")
    units = raw.get("buffer_units")
    if units not in ("feet", "meters", "miles"):
        raise InvalidCorridor("buffer units are invalid")
    alternatives_raw = raw.get("alternatives", [])
    if not isinstance(alternatives_raw, list) or len(alternatives_raw) > MAX_ALTERNATIVES:
        raise InvalidCorridor("alternatives exceed limits")
    alternatives = tuple(_line(item) for item in alternatives_raw)
    indirect = raw.get("indirect_geometry")
    return ActiveCorridor(
        reference,
        centerline,
        float(distance),
        units,
        alternatives,
        _polygon(indirect) if indirect is not None else None,
    )


def read_active_corridor(request: Any) -> ActiveCorridor | None:
    custom_inputs = getattr(request, "custom_inputs", None)
    if not isinstance(custom_inputs, dict) or custom_inputs.get("active_corridor") is None:
        return None
    try:
        return parse_active_corridor(custom_inputs["active_corridor"])
    except InvalidCorridor:
        return None


def instruction_note(corridor: ActiveCorridor) -> str:
    """Give the model a coordinate-free reference and tool-use instruction."""
    return (
        "A corridor is attached to this conversation ("
        f"{corridor.corridor_ref}; buffer {corridor.buffer_distance:g} "
        f"{corridor.buffer_units} on each side). For corridor screening, pass "
        f'"{corridor.corridor_ref}" as the centerline reference; the app supplies '
        "the validated corridor geometry and settings. Do not write coordinates. "
        "Use this context only for corridor screening."
    )


def substitute_arguments(
    tool_name: str, arguments: dict[str, Any] | None, corridor: ActiveCorridor
) -> dict[str, Any] | None:
    if tool_name != CORRIDOR_TOOL or not arguments:
        return arguments
    result = copy.deepcopy(arguments)
    value = result.get("centerline")
    if isinstance(value, str) and value.strip() == corridor.corridor_ref:
        result.update(
            centerline=copy.deepcopy(corridor.centerline),
            buffer_distance=corridor.buffer_distance,
            buffer_units=corridor.buffer_units,
            alternatives=copy.deepcopy(list(corridor.alternatives)),
        )
        if corridor.indirect_geometry is not None:
            result["indirect_geometry"] = copy.deepcopy(corridor.indirect_geometry)
    return result


def bind_active_corridor(server: McpServer, corridor: ActiveCorridor) -> McpServer:
    """Substitute only corridor tool calls, retaining the existing traced path."""
    original = server.call_tool

    async def call_tool(tool_name: str, arguments: dict[str, Any] | None, **kwargs: Any) -> Any:
        return await original(
            tool_name, substitute_arguments(tool_name, arguments, corridor), **kwargs
        )

    server.call_tool = call_tool
    return server
