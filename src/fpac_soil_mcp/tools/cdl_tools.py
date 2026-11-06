"""MCP tools for USDA NASS Cropland Data Layer screening."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from pyproj import Transformer
from shapely.geometry import MultiPolygon, Polygon
from shapely.ops import transform

from fpac_soil_mcp.cdl_client import CDLClient
from fpac_soil_mcp.cdl_models import CDLAnalysisStatus, CDLHistogramResponse
from fpac_soil_mcp.geometry import (
    GeometryValidationError,
    compute_geometry_hash,
    parse_geojson_geometry,
)


def _esri_rings(geometry: Polygon | MultiPolygon) -> list[list[list[float]]]:
    polygons = [geometry] if isinstance(geometry, Polygon) else list(geometry.geoms)
    rings: list[list[list[float]]] = []
    for polygon in polygons:
        rings.append([list(point) for point in polygon.exterior.coords])
        rings.extend([list(point) for point in interior.coords] for interior in polygon.interiors)
    return rings


def _fallback_geometry_hash(value: Any) -> str:
    try:
        serialized = json.dumps(value, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError):
        serialized = repr(value)
    return f"sha256:{hashlib.sha256(serialized.encode('utf-8')).hexdigest()}"


def analyze_cdl_histogram(
    geojson: dict[str, Any] | str,
    product_vintage: str,
    qualifying_class_values: list[int],
    nodata_class_values: list[int] | None = None,
) -> CDLHistogramResponse:
    """Compute preliminary NASS CDL land-cover histogram evidence for a polygon AOI."""
    geometry_hash = _fallback_geometry_hash(geojson)
    if not product_vintage.strip():
        return CDLHistogramResponse(
            status=CDLAnalysisStatus.INVALID,
            geometry_hash=geometry_hash,
            error_message="product_vintage must be a non-empty value.",
        )
    if not qualifying_class_values:
        return CDLHistogramResponse(
            status=CDLAnalysisStatus.INVALID,
            geometry_hash=geometry_hash,
            product_vintage=product_vintage,
            error_message="qualifying_class_values must contain at least one CDL class value.",
        )
    if any(value < 0 for value in qualifying_class_values):
        return CDLHistogramResponse(
            status=CDLAnalysisStatus.INVALID,
            geometry_hash=geometry_hash,
            product_vintage=product_vintage,
            error_message="qualifying_class_values must contain non-negative integers.",
        )

    try:
        geometry = parse_geojson_geometry(geojson)
        geometry_hash = compute_geometry_hash(geometry)
        client = CDLClient()
        metadata = client.get_service_metadata()
        spatial_reference = metadata.spatial_reference or "4326"
        if spatial_reference.isdigit() and spatial_reference != "4326":
            geometry = transform(
                Transformer.from_crs(
                    "EPSG:4326", f"EPSG:{spatial_reference}", always_xy=True
                ).transform,
                geometry,
            )
        if metadata.full_extent:
            minx, miny, maxx, maxy = geometry.bounds
            extent = metadata.full_extent
            if (
                maxx < extent["xmin"]
                or minx > extent["xmax"]
                or maxy < extent["ymin"]
                or miny > extent["ymax"]
            ):
                return CDLHistogramResponse(
                    status=CDLAnalysisStatus.UNAVAILABLE,
                    geometry_hash=geometry_hash,
                    product_vintage=product_vintage,
                    service_metadata=metadata,
                    error_message="AOI is outside the validated CDL ImageServer extent.",
                )
        return client.analyze_polygon_histogram(
            geometry={
                "rings": _esri_rings(geometry),
                "spatialReference": {"wkid": int(spatial_reference)},
            },
            geometry_hash=geometry_hash,
            product_vintage=product_vintage,
            qualifying_class_values=set(qualifying_class_values),
            nodata_class_values=set(nodata_class_values or [0]),
        )
    except GeometryValidationError as exc:
        return CDLHistogramResponse(
            status=CDLAnalysisStatus.INVALID,
            geometry_hash=geometry_hash,
            product_vintage=product_vintage,
            error_message=str(exc),
        )
    except (TypeError, ValueError, RuntimeError) as exc:
        return CDLHistogramResponse(
            status=(
                CDLAnalysisStatus.ERROR
                if isinstance(exc, RuntimeError)
                else CDLAnalysisStatus.INVALID
            ),
            geometry_hash=geometry_hash,
            product_vintage=product_vintage,
            error_message=str(exc),
        )
