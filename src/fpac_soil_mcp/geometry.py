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

from pyproj import Geod
from shapely import wkt as shapely_wkt
from shapely.errors import GEOSException, ShapelyError
from shapely.geometry import MultiPolygon, Point, Polygon, mapping, shape
from shapely.validation import make_valid

_WKT_PREFIX_PATTERN = re.compile(
    r"^(POINT|POLYGON|MULTIPOLYGON|LINESTRING|MULTILINESTRING|GEOMETRYCOLLECTION)\s*\(",
    re.IGNORECASE,
)

# Standard WGS84 Geoid for ellipsoidal geodesic area calculations
_GEOD = Geod(ellps="WGS84")

# Conversion factor: square meters to acres (1 acre = 4046.8564224 square meters)
_SQ_METERS_PER_ACRE = 4046.8564224


class GeometryError(Exception):
    """Base exception for geometry processing and validation errors."""


class GeometryValidationError(GeometryError):
    """Raised when geometry format, coordinates, or topology are invalid."""


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
) -> Polygon | MultiPolygon | Point:
    """Parse and validate a GeoJSON geometry dictionary or JSON string into a Shapely geometry.

    Accepts GeoJSON Feature, FeatureCollection (single geometry), or raw geometry dicts.

    Args:
        geojson_input: GeoJSON object as dict or JSON string.
        allow_point: If True, allows Point geometry in addition to Polygon/MultiPolygon.

    Returns:
        Shapely Polygon, MultiPolygon, or Point instance.

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
    allowed_types = (
        ("Polygon", "MultiPolygon", "Point") if allow_point else ("Polygon", "MultiPolygon")
    )
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


def geometry_to_wkt(geom: Polygon | MultiPolygon) -> str:
    """Convert a Shapely Polygon or MultiPolygon to a validated WKT string.

    Args:
        geom: Shapely Polygon or MultiPolygon.

    Returns:
        WKT string.
    """
    wkt_str = geom.wkt
    return validate_wkt_string(wkt_str)


def compute_geometry_hash(
    geojson_dict_or_geom: dict[str, Any] | Polygon | MultiPolygon | Point,
) -> str:
    """Compute deterministic SHA-256 hash of a normalized geometry.

    Args:
        geojson_dict_or_geom: GeoJSON geometry dict or Shapely geometry.

    Returns:
        Hex-encoded SHA-256 hash string prefixed with 'sha256:'.
    """
    if isinstance(geojson_dict_or_geom, (Polygon, MultiPolygon, Point)):
        norm_dict = mapping(geojson_dict_or_geom)
    elif isinstance(geojson_dict_or_geom, dict):
        parsed = parse_geojson_geometry(geojson_dict_or_geom, allow_point=True)
        norm_dict = mapping(parsed)
    else:
        raise GeometryValidationError("Invalid input type for compute_geometry_hash.")

    # Serialize normalized dictionary with sorted keys for reproducible hashing
    serialized = json.dumps(norm_dict, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"sha256:{hashlib.sha256(serialized).hexdigest()}"
