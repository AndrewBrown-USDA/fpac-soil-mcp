"""Server map result contract for the analyze tools (ADR 0017).

Models and builders for the additive ``map`` block that
``analyze_farmland_by_polygon`` and ``analyze_corridor_fppa`` return. Numbers in
the responses always come from exact geometry; this module only shapes the
display copy (simplification, size cap) and the server-owned legends.

This module must not import ``fpac_soil_mcp.models`` or the analyzers at import
time: ``models`` imports it.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterable, Mapping, Sequence
from typing import Any, Literal

import shapely
from pydantic import BaseModel, Field
from shapely import wkt as shapely_wkt
from shapely.errors import GEOSException, ShapelyError
from shapely.geometry import mapping, shape
from shapely.geometry.base import BaseGeometry

from fpac_soil_mcp.geometry import _TO_EQUAL_AREA, _TO_WGS84

logger = logging.getLogger(__name__)

MAP_SCHEMA_VERSION = "1.0"
DISPLAY_CRS = "EPSG:4326"
AUTHORITY_LABEL = "Preliminary Machine Estimate"

LayerKind = Literal["polygon", "line", "point"]
LayerDelivery = Literal["inline_geojson", "omitted"]
LayerAuthority = Literal["user_input", "machine_estimate", "reference_data"]
LegendPattern = Literal[
    "solid", "diagonal_hatch", "cross_hatch", "dot_stipple", "outline", "dashed_outline"
]
GeometryWithProperties = tuple[BaseGeometry, dict[str, Any]]


class MapLegendItem(BaseModel):
    """One legend entry; ``value`` matches the layer's ``style_key`` property."""

    value: str = Field(description="Feature property value this entry styles")
    label: str = Field(description="Display label")
    color: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$", description="Hex colour")
    pattern: LegendPattern = Field(default="solid", description="Secondary visual cue")
    code: str | None = Field(default=None, description="Text code shown with the colour")


class MapLayer(BaseModel):
    """One drawable layer of a map result."""

    id: str = Field(description="Stable layer id (ADR 0017)")
    title: str = Field(description="Display title")
    kind: LayerKind = Field(description="Geometry kind")
    delivery: LayerDelivery = Field(
        default="omitted", description="inline_geojson when features are included"
    )
    authority: LayerAuthority = Field(description="Authority level of the layer content")
    source: str = Field(description="Data source service name")
    data_vintage: str | None = Field(default=None, description="Data vintage when known")
    style_key: str | None = Field(
        default=None, description="Feature property that legend values match"
    )
    legend: list[MapLegendItem] = Field(default_factory=list, description="Server legend")
    simplified: bool = Field(default=False, description="Display copy was simplified")
    simplify_tolerance_m: float | None = Field(
        default=None, description="Simplification tolerance in metres (EPSG:6933)"
    )
    truncated: bool = Field(default=False, description="Features dropped by the size cap")
    feature_count: int | None = Field(
        default=None, description="Features in feature_collection; null when omitted"
    )
    feature_collection: dict[str, Any] | None = Field(
        default=None, description="GeoJSON FeatureCollection; null when omitted"
    )


class MapBlock(BaseModel):
    """Map result block: display CRS, bounds of inline layers, layers, warnings."""

    display_crs: str = Field(default=DISPLAY_CRS, description="CRS of inline geometry")
    bounds: list[float] | None = Field(
        default=None,
        description="[min_lon, min_lat, max_lon, max_lat] of inline layers; null if none",
    )
    layers: list[MapLayer] = Field(default_factory=list, description="Layers, bottom to top")
    warnings: list[str] = Field(default_factory=list, description="Display warnings")


class ResultAuthority(BaseModel):
    """Authority of an analysis result: always a preliminary machine estimate."""

    level: Literal["machine_estimate"] = "machine_estimate"
    label: str = AUTHORITY_LABEL
    official_filing: Literal[False] = False


# Values match polygon_analysis.categorize_farmland_class outputs.
_FARMLAND_LEGEND: tuple[tuple[str, str, str, str, LegendPattern], ...] = (
    ("prime", "Prime farmland", "P", "#2E7D32", "solid"),
    (
        "conditional_prime",
        "Prime farmland if conditions are met",
        "P*",
        "#81C784",
        "diagonal_hatch",
    ),
    ("statewide", "Farmland of statewide importance", "S", "#F9A825", "diagonal_hatch"),
    ("unique", "Unique farmland", "U", "#6A1B9A", "cross_hatch"),
    ("local", "Farmland of local importance", "L", "#0288D1", "dot_stipple"),
    ("not_prime", "Not prime farmland", "NP", "#9E9E9E", "outline"),
    ("unmapped", "Unmapped", "UM", "#FFFFFF", "diagonal_hatch"),
)
FARMLAND_CLASS_VALUES: tuple[str, ...] = tuple(item[0] for item in _FARMLAND_LEGEND)

URBAN_CONTEXT_COLOR = "#5C6BC0"
CORRIDOR_DIRECT_COLOR = "#E53935"
ALTERNATIVE_COLORS: tuple[str, ...] = ("#1E88E5", "#8E24AA", "#00897B", "#F4511E")
NEUTRAL_OUTLINE_COLOR = "#424242"


def farmland_legend() -> list[MapLegendItem]:
    """Return the server legend for the ``farmland_classes`` layer."""
    return [
        MapLegendItem(value=value, label=label, code=code, color=color, pattern=pattern)
        for value, label, code, color, pattern in _FARMLAND_LEGEND
    ]


def single_legend(
    value: str, label: str, color: str, pattern: LegendPattern = "outline"
) -> list[MapLegendItem]:
    """Return a one-entry legend for outline layers (AOI, urban, corridor, counties)."""
    return [MapLegendItem(value=value, label=label, color=color, pattern=pattern)]


def _project(geom: BaseGeometry, transformer) -> BaseGeometry:
    return shapely.transform(geom, lambda x, y: transformer.transform(x, y), interleaved=False)


def simplify_for_display(geoms: Sequence[BaseGeometry], tolerance_m: float) -> list[BaseGeometry]:
    """Simplify display copies with topology preserved at ``tolerance_m`` in EPSG:6933.

    A geometry whose simplified copy is empty or invalid is returned unchanged.
    """
    if tolerance_m <= 0:
        return list(geoms)
    simplified: list[BaseGeometry] = []
    for geom in geoms:
        try:
            projected = _project(geom, _TO_EQUAL_AREA)
            reduced = shapely.simplify(projected, tolerance_m, preserve_topology=True)
            candidate = _project(reduced, _TO_WGS84)
        except (GEOSException, ShapelyError, ValueError) as exc:
            logger.warning("Display simplification failed; keeping exact geometry: %s", exc)
            simplified.append(geom)
            continue
        if candidate.is_empty or not candidate.is_valid:
            simplified.append(geom)
        else:
            simplified.append(candidate)
    return simplified


def build_layer(
    *,
    layer_id: str,
    title: str,
    kind: LayerKind,
    authority: LayerAuthority,
    source: str,
    features: Sequence[GeometryWithProperties] | None,
    include_map: bool,
    data_vintage: str | None = None,
    style_key: str | None = None,
    legend: Sequence[MapLegendItem] | None = None,
    simplify_tolerance_m: float | None = None,
) -> MapLayer:
    """Build one layer; descriptor only unless ``include_map`` is true.

    ``features`` are exact (geometry, properties) pairs in WGS84. When
    ``simplify_tolerance_m`` is positive the display copy is simplified.
    """
    layer = MapLayer(
        id=layer_id,
        title=title,
        kind=kind,
        authority=authority,
        source=source,
        data_vintage=data_vintage,
        style_key=style_key,
        legend=list(legend or []),
    )
    if not include_map:
        return layer

    pairs = list(features or [])
    geoms = [geom for geom, _ in pairs]
    if simplify_tolerance_m and simplify_tolerance_m > 0:
        geoms = simplify_for_display(geoms, simplify_tolerance_m)
        layer.simplified = True
        layer.simplify_tolerance_m = simplify_tolerance_m

    layer.feature_collection = {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "geometry": mapping(geom), "properties": dict(props)}
            for geom, (_, props) in zip(geoms, pairs, strict=True)
        ],
    }
    layer.feature_count = len(pairs)
    layer.delivery = "inline_geojson"
    return layer


def bounds_of(layers: Iterable[MapLayer]) -> list[float] | None:
    """Return [min_lon, min_lat, max_lon, max_lat] over inline layers, or None."""
    bounds: list[float] | None = None
    for layer in layers:
        if layer.delivery != "inline_geojson" or not layer.feature_collection:
            continue
        for feature in layer.feature_collection.get("features", []):
            geometry = feature.get("geometry")
            if not geometry:
                continue
            minx, miny, maxx, maxy = shape(geometry).bounds
            if bounds is None:
                bounds = [minx, miny, maxx, maxy]
            else:
                bounds = [
                    min(bounds[0], minx),
                    min(bounds[1], miny),
                    max(bounds[2], maxx),
                    max(bounds[3], maxy),
                ]
    return [round(value, 6) for value in bounds] if bounds is not None else None


def _feature_collection_bytes(layer: MapLayer) -> int:
    if layer.feature_collection is None:
        return 0
    return len(json.dumps(layer.feature_collection, separators=(",", ":")).encode("utf-8"))


def enforce_size_cap(block: MapBlock, max_bytes: int) -> MapBlock:
    """Drop whole inline layers from the end until the GeoJSON fits ``max_bytes``.

    A dropped layer keeps its descriptor with ``delivery: omitted`` and
    ``truncated: true``, and a warning names it. Bounds are recomputed.
    """
    sizes = [_feature_collection_bytes(layer) for layer in block.layers]
    total = sum(sizes)
    for index in range(len(block.layers) - 1, -1, -1):
        if total <= max_bytes:
            break
        layer = block.layers[index]
        if layer.delivery != "inline_geojson":
            continue
        total -= sizes[index]
        layer.feature_collection = None
        layer.feature_count = None
        layer.delivery = "omitted"
        layer.truncated = True
        block.warnings.append(
            f"Layer '{layer.title}' was not drawn: map data exceeded the "
            f"{max_bytes:,}-byte limit. Acreage and results are unaffected."
        )
    block.bounds = bounds_of(block.layers)
    return block


def build_map_block(layers: Sequence[MapLayer], max_bytes: int) -> MapBlock:
    """Assemble a map block, apply the size cap and set bounds."""
    return enforce_size_cap(MapBlock(layers=list(layers)), max_bytes)


def features_from_sda_rows(rows: Iterable[Mapping[str, Any]]) -> list[GeometryWithProperties]:
    """Convert SDA ``get_spatial_intersection(return_geom=True)`` rows to map features.

    Rows without a parseable WKT ``geom`` are skipped. Properties: ``mukey``,
    ``musym``, ``muname``, ``farmlndcl``, ``farmland_class`` and ``area_ac``.
    Ported from ``tools.soil_lookup_tools.get_soil_polygons_by_geometry``.
    """
    from fpac_soil_mcp.polygon_analysis import categorize_farmland_class

    features: list[GeometryWithProperties] = []
    for row in rows:
        geom_wkt = row.get("geom")
        if not geom_wkt:
            continue
        try:
            geom = shapely_wkt.loads(geom_wkt)
        except (GEOSException, ShapelyError, ValueError, TypeError) as exc:
            logger.warning("Could not parse returned WKT geometry: %s", exc)
            continue
        if geom.is_empty:
            continue
        try:
            area_val = float(row.get("area_ac") or 0.0)
        except (ValueError, TypeError):
            area_val = 0.0
        farmlndcl = row.get("farmlndcl")
        features.append(
            (
                geom,
                {
                    "mukey": str(row.get("mukey", "")),
                    "musym": row.get("musym"),
                    "muname": row.get("muname"),
                    "farmlndcl": farmlndcl,
                    "farmland_class": categorize_farmland_class(farmlndcl),
                    "area_ac": round(area_val, 2),
                },
            )
        )
    return features
