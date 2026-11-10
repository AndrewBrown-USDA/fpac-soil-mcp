"""Geospatial geometry parsing, validation, WKT formatting, and equal-area acreage engine.

Provides functions to validate GeoJSON Polygon and MultiPolygon inputs, repair topology,
calculate ellipsoidal geodetic acreage, convert geometries safely to WKT strings,
and compute deterministic SHA-256 geometry hashes.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from pyproj import Geod, Transformer
from shapely import ops as shapely_ops
from shapely import wkt as shapely_wkt
from shapely.errors import GEOSException, ShapelyError
from shapely.geometry import (
    LinearRing,
    LineString,
    MultiLineString,
    MultiPolygon,
    Point,
    Polygon,
    mapping,
    shape,
)
from shapely.validation import make_valid

_WKT_PREFIX_PATTERN = re.compile(
    r"^(POINT|POLYGON|MULTIPOLYGON|LINESTRING|MULTILINESTRING|GEOMETRYCOLLECTION)\s*\(",
    re.IGNORECASE,
)

# Standard WGS84 Geoid for ellipsoidal geodesic area calculations
_GEOD = Geod(ellps="WGS84")

# Conversion factor: square meters to acres (1 acre = 4046.8564224 square meters)
_SQ_METERS_PER_ACRE = 4046.8564224

# Unit conversion factors to meters
_UNIT_TO_METERS = {
    "meter": 1.0,
    "meters": 1.0,
    "m": 1.0,
    "foot": 0.3048,
    "feet": 0.3048,
    "ft": 0.3048,
    "mile": 1609.344,
    "miles": 1609.344,
    "mi": 1609.344,
}

# Coordinate transformers between WGS84 (EPSG:4326) and Equal Area (EPSG:6933)
_TO_EQUAL_AREA = Transformer.from_crs("EPSG:4326", "EPSG:6933", always_xy=True)
_TO_WGS84 = Transformer.from_crs("EPSG:6933", "EPSG:4326", always_xy=True)


class GeometryError(Exception):
    """Base exception for geometry processing and validation errors."""


class GeometryValidationError(GeometryError):
    """Raised when geometry format, coordinates, or topology are invalid."""


def normalize_ring_winding(ring: LinearRing, clockwise: bool = True) -> list[list[float]]:
    """Normalize a ring's winding for an Esri REST polygon."""
    coords = list(ring.coords)
    if (clockwise and ring.is_ccw) or (not clockwise and not ring.is_ccw):
        coords.reverse()
    return [list(coordinate) for coordinate in coords]


def polygon_to_esri_rings(geom: Polygon | MultiPolygon) -> list[list[list[float]]]:
    """Convert polygon geometry to Esri rings with normalized winding."""
    rings: list[list[list[float]]] = []
    polygons = [geom] if isinstance(geom, Polygon) else list(geom.geoms)

    for polygon in polygons:
        rings.append(normalize_ring_winding(polygon.exterior, clockwise=True))
        rings.extend(
            normalize_ring_winding(interior, clockwise=False) for interior in polygon.interiors
        )

    return rings


def validate_wkt_string(wkt: str) -> str:
    """Validate that a WKT string starts with a recognized geometry type.

    Args:
        wkt: WKT string.

    Returns:
        Sanitized and trimmed WKT string.

    Raises:
        GeometryValidationError: If WKT string is empty or does not match recognized prefix.
    """
    cleaned = wkt.strip()
    if not cleaned:
        raise GeometryValidationError("WKT geometry string cannot be empty.")
    if not _WKT_PREFIX_PATTERN.match(cleaned):
        raise GeometryValidationError(
            f"Invalid WKT geometry format: '{cleaned[:50]}...'. Must begin with a recognized geometry type."
        )
    return cleaned


def validate_and_sanitize_polygon_wkt(wkt: str) -> str:
    """Parse, validate, and sanitize a WKT Polygon or MultiPolygon string.

    Parses the WKT using Shapely, verifies that it is a valid Polygon or MultiPolygon
    with WGS84 coordinate bounds, and returns normalized WKT to prevent SQL injection.

    Args:
        wkt: WKT Polygon or MultiPolygon string.

    Returns:
        Normalized and sanitized WKT string.

    Raises:
        GeometryValidationError: If WKT is empty, malformed, not a Polygon/MultiPolygon, or out of bounds.
    """
    cleaned = wkt.strip()
    if not cleaned:
        raise GeometryValidationError("WKT geometry string cannot be empty.")

    try:
        geom = shapely_wkt.loads(cleaned)
    except (GEOSException, ShapelyError, Exception) as exc:
        raise GeometryValidationError(f"Invalid WKT geometry format: {exc}") from exc

    if not isinstance(geom, (Polygon, MultiPolygon)):
        raise GeometryValidationError(
            f"WKT geometry must be a Polygon or MultiPolygon; received '{geom.geom_type}'."
        )

    if geom.is_empty:
        raise GeometryValidationError("WKT geometry is empty.")

    minx, miny, maxx, maxy = geom.bounds
    if not (-180.0 <= minx <= 180.0 and -180.0 <= maxx <= 180.0):
        raise GeometryValidationError(
            f"Longitude coordinates outside valid range [-180, 180]: minx={minx}, maxx={maxx}"
        )
    if not (-90.0 <= miny <= 90.0 and -90.0 <= maxy <= 90.0):
        raise GeometryValidationError(
            f"Latitude coordinates outside valid range [-90, 90]: miny={miny}, maxy={maxy}"
        )

    if not geom.is_valid:
        repaired = make_valid(geom)
        if isinstance(repaired, (Polygon, MultiPolygon)) and not repaired.is_empty:
            geom = repaired
        else:
            raise GeometryValidationError(
                "WKT geometry is topologically invalid and could not be repaired."
            )

    return geom.wkt


def parse_geojson_geometry(
    geojson_input: dict[str, Any] | str,
    allow_point: bool = False,
    allow_line: bool = False,
) -> Polygon | MultiPolygon | Point | LineString | MultiLineString:
    """Parse and validate a GeoJSON geometry dictionary or JSON string into a Shapely geometry.

    Accepts GeoJSON Feature, FeatureCollection (single geometry), or raw geometry dicts.

    Args:
        geojson_input: GeoJSON object as dict or JSON string.
        allow_point: If True, allows Point geometry in addition to Polygon/MultiPolygon.
        allow_line: If True, allows LineString/MultiLineString geometry.

    Returns:
        Shapely Polygon, MultiPolygon, Point, LineString, or MultiLineString instance.

    Raises:
        GeometryValidationError: If GeoJSON structure is invalid or geometry type is disallowed.
    """
    if isinstance(geojson_input, str):
        try:
            geom_dict = json.loads(geojson_input)
        except json.JSONDecodeError as exc:
            raise GeometryValidationError(f"Invalid GeoJSON string: {exc}") from exc
    elif isinstance(geojson_input, dict):
        geom_dict = geojson_input
    else:
        raise GeometryValidationError(
            f"GeoJSON input must be a dict or string; received {type(geojson_input).__name__}."
        )

    # Unwrap Feature or FeatureCollection if supplied
    if geom_dict.get("type") == "Feature":
        geom_dict = geom_dict.get("geometry") or {}
    elif geom_dict.get("type") == "FeatureCollection":
        features = geom_dict.get("features", [])
        if not features:
            raise GeometryValidationError("FeatureCollection contains no features.")
        geom_dict = features[0].get("geometry") or {}

    geom_type = geom_dict.get("type")
    allowed_types = ["Polygon", "MultiPolygon"]
    if allow_point:
        allowed_types.append("Point")
    if allow_line:
        allowed_types.extend(["LineString", "MultiLineString"])

    if geom_type not in allowed_types:
        raise GeometryValidationError(
            f"Unsupported geometry type: '{geom_type}'. Allowed types: {', '.join(allowed_types)}."
        )

    try:
        geom = shape(geom_dict)
    except Exception as exc:
        raise GeometryValidationError(f"Failed to parse GeoJSON geometry: {exc}") from exc

    if geom.is_empty:
        raise GeometryValidationError("Geometry is empty.")

    # Validate coordinate bounds [-180, -90, 180, 90]
    minx, miny, maxx, maxy = geom.bounds
    if not (-180.0 <= minx <= 180.0 and -180.0 <= maxx <= 180.0):
        raise GeometryValidationError(
            f"Longitude coordinates outside valid range [-180, 180]: minx={minx}, maxx={maxx}"
        )
    if not (-90.0 <= miny <= 90.0 and -90.0 <= maxy <= 90.0):
        raise GeometryValidationError(
            f"Latitude coordinates outside valid range [-90, 90]: miny={miny}, maxy={maxy}"
        )

    # Topology validation and automated repair for polygons
    if isinstance(geom, (Polygon, MultiPolygon)) and not geom.is_valid:
        repaired = make_valid(geom)
        if isinstance(repaired, (Polygon, MultiPolygon)) and not repaired.is_empty:
            geom = repaired
        else:
            raise GeometryValidationError(
                "Geometry is topologically invalid and could not be repaired."
            )

    return geom


def calculate_acreage(geom: Polygon | MultiPolygon) -> float:
    """Calculate geodesic ellipsoidal surface acreage of a geometry on WGS84.

    Args:
        geom: Shapely Polygon or MultiPolygon in WGS84 geographic coordinates.

    Returns:
        Calculated area in acres (rounded to 2 decimal places, minimum 0.0).
    """
    if geom.is_empty:
        return 0.0

    total_sq_meters = 0.0
    polygons = [geom] if isinstance(geom, Polygon) else list(geom.geoms)

    for poly in polygons:
        # Outer exterior ring area (positive)
        lons, lats = poly.exterior.coords.xy
        ext_area, _ = _GEOD.polygon_area_perimeter(lons, lats)
        poly_sq_meters = abs(ext_area)

        # Subtract interior hole rings (if any)
        for interior in poly.interiors:
            hole_lons, hole_lats = interior.coords.xy
            hole_area, _ = _GEOD.polygon_area_perimeter(hole_lons, hole_lats)
            poly_sq_meters -= abs(hole_area)

        total_sq_meters += max(0.0, poly_sq_meters)

    acres = total_sq_meters / _SQ_METERS_PER_ACRE
    return round(acres, 2)


def calculate_geodesic_length(geom: LineString | MultiLineString) -> float:
    """Calculate geodesic perimeter length in meters for line geometry."""
    if geom.is_empty:
        return 0.0
    lines = [geom] if isinstance(geom, LineString) else list(geom.geoms)
    total_meters = 0.0
    for line in lines:
        lons, lats = line.coords.xy
        total_meters += _GEOD.line_length(lons, lats)
    return total_meters


def geometry_to_wkt(geom: Polygon | MultiPolygon) -> str:
    """Convert a Shapely Polygon or MultiPolygon to a validated WKT string.

    Args:
        geom: Shapely Polygon or MultiPolygon.

    Returns:
        WKT string.
    """
    wkt_str = geom.wkt
    return validate_wkt_string(wkt_str)


def validate_and_sanitize_line_wkt(wkt: str) -> str:
    """Parse, validate, and sanitize a WKT LineString or MultiLineString string.

    Parses the WKT using Shapely, verifies that it is a valid LineString or MultiLineString
    with WGS84 coordinate bounds, and returns normalized WKT to prevent SQL injection.

    Args:
        wkt: WKT LineString or MultiLineString string.

    Returns:
        Normalized and sanitized WKT string.

    Raises:
        GeometryValidationError: If WKT is empty, malformed, not a LineString/MultiLineString, or out of bounds.
    """
    cleaned = wkt.strip()
    if not cleaned:
        raise GeometryValidationError("WKT geometry string cannot be empty.")

    try:
        geom = shapely_wkt.loads(cleaned)
    except (GEOSException, ShapelyError, Exception) as exc:
        raise GeometryValidationError(f"Invalid WKT geometry format: {exc}") from exc

    if not isinstance(geom, (LineString, MultiLineString)):
        raise GeometryValidationError(
            f"WKT geometry must be a LineString or MultiLineString; received '{geom.geom_type}'."
        )

    if geom.is_empty:
        raise GeometryValidationError("WKT geometry is empty.")

    minx, miny, maxx, maxy = geom.bounds
    if not (-180.0 <= minx <= 180.0 and -180.0 <= maxx <= 180.0):
        raise GeometryValidationError(
            f"Longitude coordinates outside valid range [-180, 180]: minx={minx}, maxx={maxx}"
        )
    if not (-90.0 <= miny <= 90.0 and -90.0 <= maxy <= 90.0):
        raise GeometryValidationError(
            f"Latitude coordinates outside valid range [-90, 90]: miny={miny}, maxy={maxy}"
        )

    return geom.wkt


def buffer_centerline(
    centerline_input: dict[str, Any] | str | LineString | MultiLineString,
    buffer_distance: float,
    distance_unit: str = "feet",
    cap_style: str = "round",
) -> Polygon | MultiPolygon:
    """Buffer a linear corridor centerline in equal-area projection space and return a WGS84 polygon.

    Projects the input centerline to EPSG:6933 (NSIDC EASE-Grid 2.0 Global equal-area),
    applies the requested buffer distance in meters, and reprojects the resulting footprint
    back to WGS84 (EPSG:4326) with topological validity repair.

    Args:
        centerline_input: GeoJSON dict/string, WKT string, or Shapely LineString/MultiLineString.
        buffer_distance: Non-negative buffer distance (e.g. 50.0, 100.0).
        distance_unit: Unit of buffer distance ('feet', 'foot', 'meters', 'meter', 'miles', 'mile').
        cap_style: End cap style: 'round', 'flat', or 'square'.

    Returns:
        Shapely Polygon or MultiPolygon in WGS84 coordinates.

    Raises:
        GeometryValidationError: If centerline is invalid, distance is negative, or unit is unrecognized.
    """
    if buffer_distance <= 0:
        raise GeometryValidationError("buffer_distance must be a positive number.")

    unit_clean = distance_unit.strip().lower()
    if unit_clean not in _UNIT_TO_METERS:
        raise GeometryValidationError(
            f"Unrecognized distance_unit '{distance_unit}'. Allowed units: {', '.join(sorted(_UNIT_TO_METERS.keys()))}."
        )

    buffer_meters = buffer_distance * _UNIT_TO_METERS[unit_clean]

    # Resolve centerline geometry
    if isinstance(centerline_input, (LineString, MultiLineString)):
        geom = centerline_input
    elif isinstance(centerline_input, str) and _WKT_PREFIX_PATTERN.match(centerline_input.strip()):
        wkt_clean = validate_and_sanitize_line_wkt(centerline_input)
        geom = shapely_wkt.loads(wkt_clean)
    else:
        geom = parse_geojson_geometry(centerline_input, allow_line=True)
        if not isinstance(geom, (LineString, MultiLineString)):
            raise GeometryValidationError(
                f"Centerline geometry must be LineString or MultiLineString; received '{geom.geom_type}'."
            )

    # Reproject to Equal Area space (EPSG:6933)
    projected = shapely_ops.transform(_TO_EQUAL_AREA.transform, geom)

    # Apply buffer in meters
    cap_style_int = 1  # round
    if cap_style == "flat":
        cap_style_int = 2
    elif cap_style == "square":
        cap_style_int = 3

    buffered_projected = projected.buffer(buffer_meters, cap_style=cap_style_int)

    # Reproject back to WGS84
    buffered_wgs84 = shapely_ops.transform(_TO_WGS84.transform, buffered_projected)

    if not buffered_wgs84.is_valid:
        repaired = make_valid(buffered_wgs84)
        if isinstance(repaired, (Polygon, MultiPolygon)) and not repaired.is_empty:
            buffered_wgs84 = repaired
        else:
            raise GeometryValidationError(
                "Buffered corridor geometry is topologically invalid and could not be repaired."
            )

    return buffered_wgs84


def erase_geometries(
    base_geom: Polygon | MultiPolygon,
    erase_geom: Polygon | MultiPolygon,
) -> Polygon | MultiPolygon:
    """Erase an overlapping geometry from a base geometry to prevent double-counting.

    Computes topological difference: base_geom - erase_geom. Useful for subtracting direct
    right-of-way corridor polygons from indirect construction staging areas.

    Args:
        base_geom: Base Shapely Polygon or MultiPolygon.
        erase_geom: Eraser Shapely Polygon or MultiPolygon.

    Returns:
        Resulting difference Polygon or MultiPolygon (empty polygon if fully erased).

    Raises:
        GeometryValidationError: If inputs are invalid or difference operation fails.
    """
    if not isinstance(base_geom, (Polygon, MultiPolygon)):
        raise GeometryValidationError(
            f"base_geom must be Polygon or MultiPolygon; received '{type(base_geom).__name__}'."
        )
    if not isinstance(erase_geom, (Polygon, MultiPolygon)):
        raise GeometryValidationError(
            f"erase_geom must be Polygon or MultiPolygon; received '{type(erase_geom).__name__}'."
        )

    if base_geom.is_empty:
        return Polygon()
    if erase_geom.is_empty:
        return base_geom

    try:
        diff = base_geom.difference(erase_geom)
    except Exception as exc:
        raise GeometryValidationError(f"Failed to calculate geometry difference: {exc}") from exc

    if not diff.is_valid:
        diff = make_valid(diff)

    # Filter non-polygonal fragments if any (e.g. lines, points from exact boundary overlaps)
    if isinstance(diff, (Polygon, MultiPolygon)):
        return diff
    elif hasattr(diff, "geoms"):
        poly_parts = [g for g in diff.geoms if isinstance(g, (Polygon, MultiPolygon))]
        if not poly_parts:
            return Polygon()
        if len(poly_parts) == 1 and isinstance(poly_parts[0], Polygon):
            return poly_parts[0]
        all_polys = []
        for p in poly_parts:
            if isinstance(p, Polygon):
                all_polys.append(p)
            else:
                all_polys.extend(p.geoms)
        return MultiPolygon(all_polys)

    return Polygon()


def compute_geometry_hash(
    geojson_dict_or_geom: dict[str, Any]
    | Polygon
    | MultiPolygon
    | Point
    | LineString
    | MultiLineString,
) -> str:
    """Compute deterministic SHA-256 hash of a normalized geometry.

    Args:
        geojson_dict_or_geom: GeoJSON geometry dict or Shapely geometry.

    Returns:
        Hex-encoded SHA-256 hash string prefixed with 'sha256:'.
    """
    if isinstance(
        geojson_dict_or_geom, (Polygon, MultiPolygon, Point, LineString, MultiLineString)
    ):
        norm_dict = mapping(geojson_dict_or_geom)
    elif isinstance(geojson_dict_or_geom, dict):
        parsed = parse_geojson_geometry(geojson_dict_or_geom, allow_point=True, allow_line=True)
        norm_dict = mapping(parsed)
    else:
        raise GeometryValidationError("Invalid input type for compute_geometry_hash.")

    # Serialize normalized dictionary with sorted keys for reproducible hashing
    serialized = json.dumps(norm_dict, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"sha256:{hashlib.sha256(serialized).hexdigest()}"
