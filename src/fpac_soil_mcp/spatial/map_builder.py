"""Server map result contract builders and display geometry processors (ADR 0017).

Builders for the ``map`` block that the map tools return. The block body only
describes layers; display geometry goes into a private ``MapDisplay`` that the
MCP layer returns in result ``_meta`` under ``MAP_META_KEY``. Numbers in the
responses always come from exact geometry; this module only shapes the display
copy (simplification, size cap) and the server-owned legends.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Container, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import shapely
from shapely import wkt as shapely_wkt
from shapely.errors import GEOSException, ShapelyError
from shapely.geometry import mapping, shape
from shapely.geometry.base import BaseGeometry

from fpac_soil_mcp.models.map import (
    AUTHORITY_LABEL,
    DISPLAY_CRS,
    MAP_META_KEY,
    MAP_SCHEMA_VERSION,
    LayerAuthority,
    LayerDelivery,
    LayerKind,
    LegendPattern,
    MapBlock,
    MapDisplay,
    MapLayer,
    MapLayerDisplay,
    MapLegendItem,
    ResultAuthority,
)
from fpac_soil_mcp.spatial.geometry import _TO_EQUAL_AREA, _TO_WGS84

logger = logging.getLogger(__name__)

GeometryWithProperties = tuple[BaseGeometry, dict[str, Any]]

# Values match categorize_farmland_class outputs.
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
    ("unknown", "Unknown classification", "?", "#BDBDBD", "dot_stipple"),
    ("unmapped", "Unmapped", "UM", "#FFFFFF", "diagonal_hatch"),
)
FARMLAND_CLASS_VALUES: tuple[str, ...] = tuple(item[0] for item in _FARMLAND_LEGEND)

URBAN_CONTEXT_COLOR = "#5C6BC0"
CORRIDOR_DIRECT_COLOR = "#E53935"
ALTERNATIVE_COLORS: tuple[str, ...] = ("#1E88E5", "#8E24AA", "#00897B", "#F4511E")
NEUTRAL_OUTLINE_COLOR = "#424242"


def categorize_farmland_class(farmlndcl: str | None) -> str:
    """Classify a SSURGO farmlndcl string into normalized category key."""
    if not farmlndcl:
        return "unmapped"

    desc = farmlndcl.strip().lower()
    if desc == "all areas are prime farmland":
        return "prime"
    if "prime farmland if" in desc:
        return "conditional_prime"
    if "statewide importance" in desc:
        return "statewide"
    if "local importance" in desc:
        return "local"
    if "unique importance" in desc or "unique farmland" in desc:
        return "unique"
    if "not prime farmland" in desc:
        return "not_prime"
    return "unknown"


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
) -> LayerBuild:
    """Build one layer description, plus its display data when ``include_map`` is true.

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
        return LayerBuild(layer=layer, display=None)

    pairs = list(features or [])
    geoms = [geom for geom, _ in pairs]
    display = MapLayerDisplay()
    if simplify_tolerance_m and simplify_tolerance_m > 0:
        geoms = simplify_for_display(geoms, simplify_tolerance_m)
        display.simplified = True
        display.simplify_tolerance_m = simplify_tolerance_m

    display.feature_collection = {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "geometry": mapping(geom), "properties": dict(props)}
            for geom, (_, props) in zip(geoms, pairs, strict=True)
        ],
    }
    display.feature_count = len(pairs)
    layer.delivery = "meta_geojson"
    return LayerBuild(layer=layer, display=display)


def bounds_of(display: MapDisplay) -> list[float] | None:
    """Return [min_lon, min_lat, max_lon, max_lat] over display layers, or None."""
    bounds: list[float] | None = None
    for layer in display.layers.values():
        if not layer.feature_collection:
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


@dataclass(frozen=True)
class LayerBuild:
    """One built layer: its body description and its display data (None when omitted)."""

    layer: MapLayer
    display: MapLayerDisplay | None


def _feature_collection_bytes(display: MapLayerDisplay | None) -> int:
    if display is None or display.feature_collection is None:
        return 0
    return len(json.dumps(display.feature_collection, separators=(",", ":")).encode("utf-8"))


def enforce_size_cap(block: MapBlock, max_bytes: int) -> MapBlock:
    """Drop whole display layers from the end until the GeoJSON fits ``max_bytes``.

    A dropped layer keeps a ``{truncated: true}`` display entry without features,
    its body description becomes ``delivery: omitted``, and a warning names it.
    Bounds are recomputed. A block without display data is returned unchanged.
    """
    display = block.display
    if display is None:
        return block
    entries = [display.layers.get(layer.id) for layer in block.layers]
    sizes = [_feature_collection_bytes(entry) for entry in entries]
    total = sum(sizes)
    for index in range(len(block.layers) - 1, -1, -1):
        if total <= max_bytes:
            break
        layer = block.layers[index]
        if layer.delivery != "meta_geojson" or entries[index] is None:
            continue
        total -= sizes[index]
        display.layers[layer.id] = MapLayerDisplay(truncated=True)
        layer.delivery = "omitted"
        display.warnings.append(
            f"Layer '{layer.title}' was not drawn: map data exceeded the "
            f"{max_bytes:,}-byte limit. Acreage and results are unaffected."
        )
    display.bounds = bounds_of(display)
    return block


def build_map_block(builds: Sequence[LayerBuild], max_bytes: int) -> MapBlock:
    """Assemble a map block, attach display data if any layer has it, apply the size cap."""
    block = MapBlock(layers=[build.layer for build in builds])
    displays = {build.layer.id: build.display for build in builds if build.display is not None}
    if displays:
        block._display = MapDisplay(layers=displays)
    return enforce_size_cap(block, max_bytes)


# Map unit productivity keys a farmland feature carries when the analyzer fetched
# ratings (Plan 44 A7); same names as ``SoilMapUnitAcreage``.
PRODUCTIVITY_PROPERTIES = (
    "productivity_rating",
    "productivity_rating_class",
    "productivity_rating_source",
)


def with_productivity(
    rows: Iterable[Mapping[str, Any]],
    ratings: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Copies of ``rows`` with each map unit's productivity keys from ``ratings`` (by mukey).

    Rows whose mukey has no rating are copied unchanged.
    """
    out: list[dict[str, Any]] = []
    for row in rows:
        rating = ratings.get(str(row.get("mukey", "")))
        extra = {key: rating.get(key) for key in PRODUCTIVITY_PROPERTIES} if rating else {}
        out.append({**row, **extra})
    return out


def productivity_by_mukey(units: Iterable[Any], rated: Container[str]) -> dict[str, dict[str, Any]]:
    """Productivity keys of the response map units whose mukey is in ``rated``."""
    return {
        unit.mukey: {key: getattr(unit, key) for key in PRODUCTIVITY_PROPERTIES}
        for unit in units
        if unit.mukey in rated
    }


def features_from_sda_rows(rows: Iterable[Mapping[str, Any]]) -> list[GeometryWithProperties]:
    """Convert SDA ``get_spatial_intersection(return_geom=True)`` rows to map features.

    Rows without a parseable WKT ``geom`` are skipped. Properties: ``mukey``,
    ``musym``, ``muname``, ``farmlndcl``, ``farmland_class`` and ``area_ac``,
    plus the ``PRODUCTIVITY_PROPERTIES`` a row carries (see ``with_productivity``).
    Ported from ``tools.soil_lookup_tools.get_soil_polygons_by_geometry``.
    """
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
                    **{key: row[key] for key in PRODUCTIVITY_PROPERTIES if key in row},
                },
            )
        )
    return features


__all__ = [
    "ALTERNATIVE_COLORS",
    "AUTHORITY_LABEL",
    "CORRIDOR_DIRECT_COLOR",
    "DISPLAY_CRS",
    "FARMLAND_CLASS_VALUES",
    "MAP_META_KEY",
    "MAP_SCHEMA_VERSION",
    "NEUTRAL_OUTLINE_COLOR",
    "PRODUCTIVITY_PROPERTIES",
    "URBAN_CONTEXT_COLOR",
    "GeometryWithProperties",
    "LayerAuthority",
    "LayerBuild",
    "LayerDelivery",
    "LayerKind",
    "LegendPattern",
    "MapBlock",
    "MapDisplay",
    "MapLayer",
    "MapLayerDisplay",
    "MapLegendItem",
    "ResultAuthority",
    "bounds_of",
    "build_layer",
    "build_map_block",
    "categorize_farmland_class",
    "enforce_size_cap",
    "farmland_legend",
    "features_from_sda_rows",
    "productivity_by_mukey",
    "simplify_for_display",
    "single_legend",
    "with_productivity",
]
