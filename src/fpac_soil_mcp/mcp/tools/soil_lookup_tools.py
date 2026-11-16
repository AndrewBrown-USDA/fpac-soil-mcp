"""Soil classification and geometry lookup tools."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Annotated, Any, Literal

from pydantic import Field
from shapely import wkt as shapely_wkt
from shapely.errors import GEOSException, ShapelyError
from shapely.geometry import MultiPolygon, Polygon, mapping

from fpac_soil_mcp.clients.sda import SDAClient, SDAClientError, SDAValidationError
from fpac_soil_mcp.core.config import settings
from fpac_soil_mcp.core.constants import REGULATORY_LIMITATIONS, REGULATORY_NOTICE
from fpac_soil_mcp.mcp.tools.spatial_analysis_tools import IncludeMap
from fpac_soil_mcp.models.soil import (
    FarmlandClassificationResponse,
    QuerySource,
    SoilMapUnit,
    ToolError,
)
from fpac_soil_mcp.spatial.geometry import (
    GeometryValidationError,
    calculate_acreage,
    geometry_to_wkt,
    parse_geojson_geometry,
)
from fpac_soil_mcp.spatial.map_builder import (
    MAP_SCHEMA_VERSION,
    NEUTRAL_OUTLINE_COLOR,
    ResultAuthority,
    build_layer,
    build_map_block,
    farmland_legend,
    features_from_sda_rows,
    single_legend,
)

logger = logging.getLogger(__name__)


def get_farmland_classification_by_point(
    latitude: Annotated[float, Field(ge=-90, le=90, allow_inf_nan=False)],
    longitude: Annotated[float, Field(ge=-180, le=180, allow_inf_nan=False)],
) -> FarmlandClassificationResponse:
    """Query USDA NRCS Soil Data Access for soil map unit and farmland classification at a point.

    Retrieves SSURGO map unit attributes (mukey, musym, muname, farmlndcl, areasymbol)
    intersecting the specified WGS84 geographic coordinate (latitude, longitude).

    Args:
        latitude: Latitude in decimal degrees [-90.0, 90.0] (WGS84).
        longitude: Longitude in decimal degrees [-180.0, 180.0] (WGS84).

    Returns:
        FarmlandClassificationResponse containing soil map unit details, coverage status,
        source metadata, and FPPA regulatory notices.
    """
    timestamp = datetime.now(UTC).isoformat()
    client = SDAClient()

    try:
        raw_results = client.get_by_point(latitude=latitude, longitude=longitude)
    except SDAClientError as exc:
        logger.error("Error querying SDA by point (%f, %f): %s", latitude, longitude, exc)
        return FarmlandClassificationResponse(
            query_type="point",
            input_query={"latitude": latitude, "longitude": longitude},
            map_units=[],
            coverage_status="no_data",
            error=ToolError(
                code="validation_error"
                if isinstance(exc, SDAValidationError)
                else "upstream_error",
                message=str(exc),
                source="USDA NRCS Soil Data Access (SDA)",
            ),
            source=QuerySource(
                service="USDA NRCS Soil Data Access",
                endpoint=client.base_url,
                timestamp_utc=timestamp,
            ),
            limitations=[*REGULATORY_LIMITATIONS, f"Query error: {exc}"],
            regulatory_notice=REGULATORY_NOTICE,
        )

    # Empty result handling (water, unmapped area, out-of-bounds)
    if not raw_results:
        return FarmlandClassificationResponse(
            query_type="point",
            input_query={"latitude": latitude, "longitude": longitude},
            map_units=[],
            coverage_status="unmapped",
            source=QuerySource(
                service="USDA NRCS Soil Data Access",
                endpoint=client.base_url,
                timestamp_utc=timestamp,
            ),
            limitations=[
                *REGULATORY_LIMITATIONS,
                "No SSURGO soil survey data available at this location (may be open water, unmapped area, or outside US soil survey coverage)",
            ],
            regulatory_notice=REGULATORY_NOTICE,
        )

    # Convert raw rows to SoilMapUnit models
    map_units = [SoilMapUnit.model_validate(row) for row in raw_results]

    return FarmlandClassificationResponse(
        query_type="point",
        input_query={"latitude": latitude, "longitude": longitude},
        map_units=map_units,
        coverage_status="covered",
        source=QuerySource(
            service="USDA NRCS Soil Data Access",
            endpoint=client.base_url,
            timestamp_utc=timestamp,
        ),
        limitations=REGULATORY_LIMITATIONS,
        regulatory_notice=REGULATORY_NOTICE,
    )


def get_farmland_classification_by_mukey(
    mukey: Annotated[
        str,
        Field(
            pattern=r"^[1-9][0-9]*$",
            description="SSURGO Map Unit Key (numeric positive integer)",
        ),
    ],
) -> FarmlandClassificationResponse:
    """Query USDA NRCS Soil Data Access for soil map unit details by Map Unit Key (mukey).

    Retrieves SSURGO map unit attributes (mukey, musym, muname, farmlndcl, areasymbol)
    for the specified map unit key.

    Args:
        mukey: SSURGO map unit key (positive integer or string representation of integer).

    Returns:
        FarmlandClassificationResponse containing map unit information, source metadata,
        and FPPA regulatory notices.
    """
    timestamp = datetime.now(UTC).isoformat()
    client = SDAClient()

    try:
        raw_results = client.get_by_mukey(mukey=mukey)
    except (SDAValidationError, ValueError) as exc:
        return FarmlandClassificationResponse(
            query_type="mukey",
            input_query={"mukey": mukey},
            map_units=[],
            coverage_status="no_data",
            error=ToolError(
                code="validation_error",
                message=str(exc),
                source="mukey parameter validation",
            ),
            source=QuerySource(
                service="USDA NRCS Soil Data Access",
                endpoint=client.base_url,
                timestamp_utc=timestamp,
            ),
            limitations=[*REGULATORY_LIMITATIONS, f"Query error: {exc}"],
            regulatory_notice=REGULATORY_NOTICE,
        )
    except SDAClientError as exc:
        logger.error("Error querying SDA by mukey %s: %s", mukey, exc)
        return FarmlandClassificationResponse(
            query_type="mukey",
            input_query={"mukey": mukey},
            map_units=[],
            coverage_status="no_data",
            error=ToolError(
                code="validation_error"
                if isinstance(exc, SDAValidationError)
                else "upstream_error",
                message=str(exc),
                source="USDA NRCS Soil Data Access (SDA)",
            ),
            source=QuerySource(
                service="USDA NRCS Soil Data Access",
                endpoint=client.base_url,
                timestamp_utc=timestamp,
            ),
            limitations=[*REGULATORY_LIMITATIONS, f"Query error: {exc}"],
            regulatory_notice=REGULATORY_NOTICE,
        )

    if not raw_results:
        return FarmlandClassificationResponse(
            query_type="mukey",
            input_query={"mukey": mukey},
            map_units=[],
            coverage_status="unmapped",
            source=QuerySource(
                service="USDA NRCS Soil Data Access",
                endpoint=client.base_url,
                timestamp_utc=timestamp,
            ),
            limitations=[
                *REGULATORY_LIMITATIONS,
                f"No map unit found for mukey '{mukey}' in USDA Soil Data Access",
            ],
            regulatory_notice=REGULATORY_NOTICE,
        )

    map_units = [SoilMapUnit.model_validate(row) for row in raw_results]

    return FarmlandClassificationResponse(
        query_type="mukey",
        input_query={"mukey": mukey},
        map_units=map_units,
        coverage_status="covered",
        source=QuerySource(
            service="USDA NRCS Soil Data Access",
            endpoint=client.base_url,
            timestamp_utc=timestamp,
        ),
        limitations=REGULATORY_LIMITATIONS,
        regulatory_notice=REGULATORY_NOTICE,
    )


def get_soil_interpretations(
    mukeys: Annotated[list[str | int], Field(min_length=1, max_length=1000)],
    rule_name: Literal["NCCPI - National Commodity Crop Productivity Index (Ver 3.0)"] = (
        "NCCPI - National Commodity Crop Productivity Index (Ver 3.0)"
    ),
) -> dict[str, Any]:
    """Retrieve component-weighted soil interpretations (such as NCCPI v3) for a list of mukeys.

    Args:
        mukeys: List of positive integer SSURGO map unit keys (up to 1000).
        rule_name: SDA interpretation rule name. Defaults to NCCPI (Ver 3.0), the name in the SDA cointerp table.

    Returns:
        Dictionary mapping mukey to interpretation rating result, plus query metadata.
    """
    client = SDAClient()
    try:
        return client.get_interpretations(mukeys=mukeys, rule_name=rule_name)
    except SDAClientError as exc:
        return {
            "status": "error",
            "source": {
                "service": "USDA NRCS Soil Data Access (SDA)",
                "endpoint": client.base_url,
            },
            "error": ToolError(
                code="validation_error"
                if isinstance(exc, SDAValidationError)
                else "upstream_error",
                message=str(exc),
                source="USDA NRCS Soil Data Access (SDA)",
            ).model_dump(),
        }


def _soil_map_fields(
    include_map: bool,
    geom: Polygon | MultiPolygon | None,
    rows: list[dict[str, Any]],
    clip: bool,
) -> dict[str, Any]:
    """ADR 0017 additive keys; layer geometry only when ``include_map`` is true.

    Uses the SDA rows already fetched, so no extra upstream call. As in
    ``PolygonAnalyzer._polygon_map``, the size cap drops layers from the end, so
    the AOI outline goes last.
    """
    include = include_map and geom is not None
    title = "Farmland classification" if clip else "Farmland classification (full survey polygons)"
    layers = [
        build_layer(
            layer_id="aoi",
            title="Area of interest",
            kind="polygon",
            authority="user_input",
            source="User-supplied area of interest",
            features=[(geom, {})] if include else None,
            include_map=include,
            legend=single_legend("aoi", "Area of interest", NEUTRAL_OUTLINE_COLOR),
        ),
        build_layer(
            layer_id="farmland_classes",
            title=title,
            kind="polygon",
            authority="machine_estimate",
            source="USDA NRCS Soil Data Access (SDA)",
            features=features_from_sda_rows(rows) if include else None,
            include_map=include,
            style_key="farmland_class",
            legend=farmland_legend(),
            simplify_tolerance_m=settings.map_simplify_tolerance_m,
        ),
    ]
    block = build_map_block(layers, settings.map_max_geojson_bytes)
    return {
        "schema_version": MAP_SCHEMA_VERSION,
        "data_mode": "live",
        "authority": ResultAuthority().model_dump(),
        "map": block.model_dump(),
    }


def get_soil_polygons_by_geometry(
    geojson: dict | str,
    clip: bool = True,
    include_map: IncludeMap = False,
) -> dict:
    """Retrieve intersecting SSURGO soil map unit polygons as a GeoJSON FeatureCollection.

    Queries USDA NRCS Soil Data Access (SDA) for spatial intersection with a GeoJSON Polygon
    or MultiPolygon. When `clip=True`, returns exact clipped map unit polygon fragments with
    geodesic acreage; when `clip=False`, returns full overlapping SSURGO survey polygons.

    Args:
        geojson: GeoJSON geometry dict or string (Polygon or MultiPolygon).
        clip: Whether to clip map units to AOI boundary (default True).
        include_map: Leave false. True embeds display GeoJSON in ``map.layers``
            (ADR 0017); by default the layers are descriptors without geometry.

    Returns:
        GeoJSON FeatureCollection dict with map unit attributes (mukey, musym, muname,
        farmlndcl, areasymbol, area_ac) and polygon geometries, plus the ADR 0017
        ``schema_version``, ``data_mode``, ``authority`` and ``map`` keys.
    """
    timestamp = datetime.now(UTC).isoformat()
    client = SDAClient()

    try:
        geom = parse_geojson_geometry(geojson)
        wkt_str = geometry_to_wkt(geom)
        aoi_acres = calculate_acreage(geom)
    except GeometryValidationError as exc:
        return {
            "type": "FeatureCollection",
            "features": [],
            "error": str(exc),
            "status": "error",
            "error_details": ToolError(
                code="validation_error",
                message=str(exc),
                source="GeoJSON geometry validation",
            ).model_dump(),
            "source": {
                "service": "USDA NRCS Soil Data Access",
                "timestamp_utc": timestamp,
            },
            "limitations": [*REGULATORY_LIMITATIONS, f"Geometry validation error: {exc}"],
            "regulatory_notice": REGULATORY_NOTICE,
            **_soil_map_fields(False, None, [], clip),
        }

    try:
        raw_rows = client.get_spatial_intersection(
            wkt_str,
            clip=clip,
            geom_acres=True,
            return_geom=True,
        )
    except SDAClientError as exc:
        logger.error("SDA spatial geometry query failed: %s", exc)
        return {
            "type": "FeatureCollection",
            "features": [],
            "error": str(exc),
            "status": "error",
            "error_details": ToolError(
                code="upstream_error",
                message=str(exc),
                source="USDA NRCS Soil Data Access (SDA)",
            ).model_dump(),
            "source": {
                "service": "USDA NRCS Soil Data Access",
                "timestamp_utc": timestamp,
            },
            "limitations": [*REGULATORY_LIMITATIONS, f"SDA spatial query error: {exc}"],
            "regulatory_notice": REGULATORY_NOTICE,
            **_soil_map_fields(False, None, [], clip),
        }

    features: list[dict] = []
    for row in raw_rows:
        geom_wkt = row.get("geom")
        if not geom_wkt:
            continue
        try:
            poly_shape = shapely_wkt.loads(geom_wkt)
            geom_dict = mapping(poly_shape)
        except (GEOSException, ShapelyError, ValueError, TypeError) as exc:
            logger.warning("Could not parse returned WKT geometry: %s", exc)
            continue

        try:
            area_val = float(row.get("area_ac") or 0.0)
        except (ValueError, TypeError):
            area_val = 0.0

        features.append(
            {
                "type": "Feature",
                "geometry": geom_dict,
                "properties": {
                    "mukey": str(row.get("mukey", "")),
                    "musym": row.get("musym"),
                    "muname": row.get("muname"),
                    "farmlndcl": row.get("farmlndcl"),
                    "areasymbol": row.get("areasymbol"),
                    "area_ac": round(area_val, 2),
                },
            }
        )

    return {
        "type": "FeatureCollection",
        "features": features,
        "properties": {
            "total_aoi_acres": aoi_acres,
            "feature_count": len(features),
            "clipped": clip,
        },
        "source": {
            "service": "USDA NRCS Soil Data Access",
            "endpoint": client.base_url,
            "timestamp_utc": timestamp,
        },
        "limitations": REGULATORY_LIMITATIONS,
        "regulatory_notice": REGULATORY_NOTICE,
        **_soil_map_fields(include_map, geom, raw_rows, clip),
    }
