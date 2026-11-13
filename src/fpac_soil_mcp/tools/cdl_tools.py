"""MCP tools for USDA NASS Cropland Data Layer screening."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any

from pyproj import Transformer
from shapely.geometry import MultiPolygon, Polygon
from shapely.ops import transform, unary_union

from fpac_soil_mcp.authority import Provenance
from fpac_soil_mcp.cdl_client import (
    CDLClient,
    CDLVintageAmbiguous,
    CDLVintageUnavailable,
)
from fpac_soil_mcp.cdl_models import (
    CDLAnalysisStatus,
    CDLClassDistribution,
    CDLContextResponse,
    CDLContextZoneResult,
    CDLHistogramResponse,
)
from fpac_soil_mcp.geometry import (
    GeometryValidationError,
    buffer_polygon,
    compute_geometry_hash,
    parse_geojson_geometry,
    polygon_to_esri_rings,
)


@lru_cache(maxsize=1)
def _get_cdl_client() -> CDLClient:
    """Reuse the client so its metadata and raster-table caches span tool calls."""
    return CDLClient()


def _fallback_geometry_hash(value: Any) -> str:
    try:
        serialized = json.dumps(value, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError):
        serialized = repr(value)
    return f"sha256:{hashlib.sha256(serialized.encode('utf-8')).hexdigest()}"


def _parse_cdl_geometry(geojson: dict[str, Any] | str) -> Polygon | MultiPolygon:
    value = geojson
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return parse_geojson_geometry(geojson)

    if isinstance(value, dict) and value.get("type") == "FeatureCollection":
        features = value.get("features")
        if not isinstance(features, list) or not features:
            raise GeometryValidationError("FeatureCollection contains no features.")
        geometries = [parse_geojson_geometry(feature) for feature in features]
        geometry = unary_union(geometries)
        if not isinstance(geometry, (Polygon, MultiPolygon)):
            raise GeometryValidationError(
                "FeatureCollection must contain polygon geometries that form a Polygon or MultiPolygon."
            )
        return geometry

    return parse_geojson_geometry(value)


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
        geometry = _parse_cdl_geometry(geojson)
        geometry_hash = compute_geometry_hash(geometry)
        client = _get_cdl_client()
        metadata = client.get_service_metadata()
        spatial_reference = metadata.spatial_reference or "4326"
        if spatial_reference.isdigit() and spatial_reference != "4326":
            geometry = transform(
                Transformer.from_crs(
                    "EPSG:4326", f"EPSG:{spatial_reference}", always_xy=True
                ).transform,
                geometry,
            )
        if not metadata.full_extent:
            return CDLHistogramResponse(
                status=CDLAnalysisStatus.UNAVAILABLE,
                geometry_hash=geometry_hash,
                product_vintage=product_vintage,
                service_metadata=metadata,
                error_message="Complete AOI coverage cannot be established from ImageServer extent metadata.",
            )
        minx, miny, maxx, maxy = geometry.bounds
        extent = metadata.full_extent
        if (
            minx < extent["xmin"]
            or maxx > extent["xmax"]
            or miny < extent["ymin"]
            or maxy > extent["ymax"]
        ):
            return CDLHistogramResponse(
                status=CDLAnalysisStatus.UNAVAILABLE,
                geometry_hash=geometry_hash,
                product_vintage=product_vintage,
                service_metadata=metadata,
                error_message="Complete AOI coverage cannot be established from the validated CDL ImageServer extent.",
            )
        return client.analyze_polygon_histogram(
            geometry={
                "rings": polygon_to_esri_rings(geometry),
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


def analyze_cdl_context(geojson: dict[str, Any] | str) -> CDLContextResponse:
    """Return full CDL class distributions for an AOI and two exterior bands."""
    geometry_hash = _fallback_geometry_hash(geojson)
    try:
        aoi = _parse_cdl_geometry(geojson)
        geometry_hash = compute_geometry_hash(aoi)
        client = _get_cdl_client()
        metadata = client.get_service_metadata()
        selected_vintage = client.resolve_latest_product_vintage(metadata=metadata)
        spatial_reference = metadata.spatial_reference or "4326"
        zones = (
            ("aoi", aoi),
            ("one_mile_ring", buffer_polygon(aoi, 1609.344)),
            ("thirty_meter_band", buffer_polygon(aoi, 30.0)),
        )
        zone_results = []
        for zone_name, zone_geometry in zones:
            zone_hash = compute_geometry_hash(zone_geometry)
            service_geometry = zone_geometry
            if spatial_reference.isdigit() and spatial_reference != "4326":
                service_geometry = transform(
                    Transformer.from_crs(
                        "EPSG:4326", f"EPSG:{spatial_reference}", always_xy=True
                    ).transform,
                    service_geometry,
                )
            if not metadata.full_extent:
                zone_results.append(
                    _unavailable_context_zone(
                        zone_name,
                        zone_hash,
                        selected_vintage,
                        metadata.endpoint,
                        "Complete coverage cannot be established because ImageServer extent metadata is unavailable.",
                    )
                )
                continue
            minx, miny, maxx, maxy = service_geometry.bounds
            extent = metadata.full_extent
            if (
                minx < extent["xmin"]
                or maxx > extent["xmax"]
                or miny < extent["ymin"]
                or maxy > extent["ymax"]
            ):
                zone_results.append(
                    _unavailable_context_zone(
                        zone_name,
                        zone_hash,
                        selected_vintage,
                        metadata.endpoint,
                        "Complete coverage cannot be established from the validated ImageServer extent.",
                    )
                )
                continue

            histogram = client.analyze_polygon_histogram(
                geometry={
                    "rings": polygon_to_esri_rings(service_geometry),
                    "spatialReference": {"wkid": int(spatial_reference)}
                    if spatial_reference.isdigit()
                    else {"wkt": spatial_reference},
                },
                geometry_hash=zone_hash,
                product_vintage=selected_vintage,
                qualifying_class_values=None,
            )
            zone_results.append(_context_zone_from_histogram(zone_name, histogram))

        zone_statuses = [zone.status for zone in zone_results]
        successes = sum(
            status in {CDLAnalysisStatus.SUCCESS, CDLAnalysisStatus.PARTIAL}
            for status in zone_statuses
        )
        if successes == len(zone_results) and all(
            status is CDLAnalysisStatus.SUCCESS for status in zone_statuses
        ):
            overall_status = CDLAnalysisStatus.SUCCESS
        elif successes:
            overall_status = CDLAnalysisStatus.PARTIAL
        else:
            overall_status = zone_statuses[0]
        return CDLContextResponse(
            status=overall_status,
            geometry_hash=geometry_hash,
            product_vintage=selected_vintage,
            vintage_verified=True,
            aoi=zone_results[0],
            one_mile_ring=zone_results[1],
            thirty_meter_band=zone_results[2],
        )
    except GeometryValidationError as exc:
        return CDLContextResponse(
            status=CDLAnalysisStatus.INVALID,
            geometry_hash=geometry_hash,
            error_message=str(exc),
        )
    except CDLVintageUnavailable as exc:
        return CDLContextResponse(
            status=CDLAnalysisStatus.UNAVAILABLE,
            geometry_hash=geometry_hash,
            error_message=str(exc),
        )
    except CDLVintageAmbiguous as exc:
        return CDLContextResponse(
            status=CDLAnalysisStatus.AMBIGUOUS,
            geometry_hash=geometry_hash,
            error_message=str(exc),
        )
    except (TypeError, ValueError, RuntimeError) as exc:
        return CDLContextResponse(
            status=CDLAnalysisStatus.ERROR
            if isinstance(exc, RuntimeError)
            else CDLAnalysisStatus.AMBIGUOUS,
            geometry_hash=geometry_hash,
            error_message=str(exc),
        )


def _unavailable_context_zone(
    zone: str,
    geometry_hash: str,
    product_vintage: str,
    source: str,
    error_message: str,
) -> CDLContextZoneResult:
    provenance = Provenance(
        source_name="USDA NASS Cropland Data Layer ImageServer",
        source_reference=source,
        timestamp_utc=datetime.now(UTC),
        method_version="cdl-context-v1",
        configuration_version=f"product_{product_vintage}",
    )
    return CDLContextZoneResult(
        zone=zone,
        status=CDLAnalysisStatus.UNAVAILABLE,
        geometry_hash=geometry_hash,
        product_vintage=product_vintage,
        vintage_verified=True,
        source=provenance.source_name,
        provenance=provenance,
        error_message=error_message,
    )


def _context_zone_from_histogram(zone: str, response: CDLHistogramResponse) -> CDLContextZoneResult:
    total = response.total_pixel_count or 0
    classes = [
        CDLClassDistribution(
            class_value=item.class_value,
            class_name=item.class_name,
            pixel_count=item.pixel_count,
            share_pct=(item.pixel_count / total * 100) if total else 0,
        )
        for item in response.histogram
    ]
    status = response.status
    if (
        status is CDLAnalysisStatus.SUCCESS
        and response.coverage_pct is not None
        and response.coverage_pct < 100
    ):
        status = CDLAnalysisStatus.PARTIAL
    return CDLContextZoneResult(
        zone=zone,
        status=status,
        geometry_hash=response.geometry_hash,
        classes=classes,
        total_pixel_count=response.total_pixel_count,
        nodata_pixel_count=response.nodata_pixel_count,
        coverage_pct=response.coverage_pct,
        coverage_verified=response.coverage_verified,
        product_vintage=response.product_vintage,
        vintage_verified=response.vintage_verified,
        source=response.provenance.source_name if response.provenance else None,
        provenance=response.provenance,
        error_message=response.error_message,
    )
