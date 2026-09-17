"""Soil lookup tools for FastMCP server.

Provides tools for querying USDA NRCS Soil Data Access (SDA) by WGS84 geographic
coordinates and by SSURGO map unit key (mukey).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from shapely import wkt as shapely_wkt
from shapely.errors import GEOSException, ShapelyError
from shapely.geometry import mapping

from fpac_soil_mcp.constants import REGULATORY_LIMITATIONS, REGULATORY_NOTICE
from fpac_soil_mcp.geometry import (
    GeometryValidationError,
    calculate_acreage,
    geometry_to_wkt,
    parse_geojson_geometry,
)
from fpac_soil_mcp.integration_models import UrbanExemptionRecord
from fpac_soil_mcp.models import (
    FarmlandClassificationResponse,
    PolygonFarmlandAnalysisResponse,
    QuerySource,
    SoilMapUnit,
)
from fpac_soil_mcp.polygon_analysis import PolygonAnalyzer
from fpac_soil_mcp.sda_client import SDAClient, SDAClientError
from fpac_soil_mcp.tigerweb_client import TigerwebClient

if TYPE_CHECKING:
    from fastmcp import FastMCP

logger = logging.getLogger(__name__)


def get_farmland_classification_by_point(
    latitude: float,
    longitude: float,
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
            coverage_status="no_data",
            map_units=[],
            source=QuerySource(
                endpoint=client.base_url,
                timestamp_utc=timestamp,
            ),
            limitations=[*REGULATORY_LIMITATIONS, f"Query error: {exc}"],
            regulatory_notice=REGULATORY_NOTICE,
        )

    map_units = [
        SoilMapUnit(
            mukey=str(row.get("mukey", "")),
            musym=row.get("musym"),
            muname=row.get("muname"),
            farmlndcl=row.get("farmlndcl"),
            areasymbol=row.get("areasymbol"),
        )
        for row in raw_results
        if row.get("mukey") is not None
    ]

    coverage_status = "covered" if map_units else "unmapped"

    return FarmlandClassificationResponse(
        query_type="point",
        input_query={"latitude": latitude, "longitude": longitude},
        coverage_status=coverage_status,
        map_units=map_units,
        source=QuerySource(
            endpoint=client.base_url,
            timestamp_utc=timestamp,
        ),
        limitations=REGULATORY_LIMITATIONS,
        regulatory_notice=REGULATORY_NOTICE,
    )


def get_farmland_classification_by_mukey(
    mukey: str,
) -> FarmlandClassificationResponse:
    """Query USDA NRCS Soil Data Access for soil map unit and farmland classification by mukey.

    Retrieves SSURGO map unit attributes (mukey, musym, muname, farmlndcl, areasymbol)
    for a specific SSURGO Map Unit Key (mukey).

    Args:
        mukey: SSURGO Map Unit Key (positive numeric string or integer).

    Returns:
        FarmlandClassificationResponse containing soil map unit details, coverage status,
        source metadata, and FPPA regulatory notices.
    """
    timestamp = datetime.now(UTC).isoformat()
    client = SDAClient()

    try:
        raw_results = client.get_by_mukey(mukey=mukey)
    except SDAClientError as exc:
        logger.error("Error querying SDA by mukey '%s': %s", mukey, exc)
        return FarmlandClassificationResponse(
            query_type="mukey",
            input_query={"mukey": mukey},
            coverage_status="no_data",
            map_units=[],
            source=QuerySource(
                endpoint=client.base_url,
                timestamp_utc=timestamp,
            ),
            limitations=[*REGULATORY_LIMITATIONS, f"Query error: {exc}"],
            regulatory_notice=REGULATORY_NOTICE,
        )

    map_units = [
        SoilMapUnit(
            mukey=str(row.get("mukey", "")),
            musym=row.get("musym"),
            muname=row.get("muname"),
            farmlndcl=row.get("farmlndcl"),
            areasymbol=row.get("areasymbol"),
        )
        for row in raw_results
        if row.get("mukey") is not None
    ]

    coverage_status = "covered" if map_units else "unmapped"

    return FarmlandClassificationResponse(
        query_type="mukey",
        input_query={"mukey": mukey},
        coverage_status=coverage_status,
        map_units=map_units,
        source=QuerySource(
            endpoint=client.base_url,
            timestamp_utc=timestamp,
        ),
        limitations=REGULATORY_LIMITATIONS,
        regulatory_notice=REGULATORY_NOTICE,
    )


def analyze_farmland_by_polygon(
    geojson: dict | str,
    include_nccpi: bool = True,
) -> PolygonFarmlandAnalysisResponse:
    """Execute comprehensive FPPA preliminary screening on a GeoJSON Polygon or MultiPolygon AOI.

    Calculates geodesic surface acreage, checks Census 2020 Urban Area boundaries,
    queries intersecting SSURGO soil map units from USDA NRCS SDA, fetches NCCPI crop
    productivity ratings, and summarizes acreage across statutory farmland categories.

    Args:
        geojson: GeoJSON geometry dict or string (Polygon or MultiPolygon).
        include_nccpi: Whether to retrieve NCCPI v3 crop productivity ratings.

    Returns:
        PolygonFarmlandAnalysisResponse with farmland acreage summaries, urban screening, and provenance.
    """
    analyzer = PolygonAnalyzer()
    return analyzer.analyze_polygon(geojson, include_nccpi=include_nccpi)


def check_urban_area_exemption(
    geojson: dict | str,
) -> UrbanExemptionRecord:
    """Screen a project footprint against Census Bureau 2020 Urban Area boundaries (Layer 6).

    Provides automated spatial screening under 7 CFR § 658.2(a) without issuing a binding legal determination.

    Args:
        geojson: GeoJSON geometry dict or string (Polygon, MultiPolygon, or Point).

    Returns:
        UrbanExemptionRecord with screening outcome and intersected urban areas.
    """
    client = TigerwebClient()
    return client.check_urban_exemption(geojson)


def get_soil_interpretations(
    mukeys: list[str],
    rule_name: str = "NCCPI - National Commodity Crop Productivity Index (v3)",
    aggregation_method: str = "Weighted Average",
) -> list[dict]:
    """Retrieve component-level soil interpretations from USDA NRCS SDA for a list of map unit keys.

    Args:
        mukeys: List of SSURGO Map Unit Keys.
        rule_name: Soil interpretation rule name.
        aggregation_method: Component aggregation method ('Weighted Average' or 'Dominant Component').

    Returns:
        List of interpretation rating dictionaries per map unit key.
    """
    client = SDAClient()
    return client.get_interpretations(
        mukeys=mukeys,
        rule_name=rule_name,
        aggregation_method=aggregation_method,
    )


def get_soil_polygons_by_geometry(
    geojson: dict | str,
    clip: bool = True,
) -> dict:
    """Retrieve intersecting SSURGO soil map unit polygons as a GeoJSON FeatureCollection.

    Queries USDA NRCS Soil Data Access (SDA) for spatial intersection with a GeoJSON Polygon
    or MultiPolygon. When `clip=True`, returns exact clipped map unit polygon fragments with
    geodesic acreage; when `clip=False`, returns full overlapping SSURGO survey polygons.

    Args:
        geojson: GeoJSON geometry dict or string (Polygon or MultiPolygon).
        clip: Whether to clip map units to AOI boundary (default True).

    Returns:
        GeoJSON FeatureCollection dict with map unit attributes (mukey, musym, muname,
        farmlndcl, areasymbol, area_ac) and polygon geometries.
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
            "source": {
                "service": "USDA NRCS Soil Data Access",
                "timestamp_utc": timestamp,
            },
            "limitations": [*REGULATORY_LIMITATIONS, f"Geometry validation error: {exc}"],
            "regulatory_notice": REGULATORY_NOTICE,
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
            "source": {
                "service": "USDA NRCS Soil Data Access",
                "timestamp_utc": timestamp,
            },
            "limitations": [*REGULATORY_LIMITATIONS, f"SDA spatial query error: {exc}"],
            "regulatory_notice": REGULATORY_NOTICE,
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
    }


def register_soil_tools(mcp: FastMCP) -> None:
    """Register soil query tools on the provided FastMCP instance.

    Args:
        mcp: FastMCP server instance.
    """
    mcp.tool(
        name="get_farmland_classification_by_point",
        description=(
            "Query USDA NRCS Soil Data Access (SDA) by WGS84 point coordinates (latitude, longitude) "
            "to retrieve SSURGO soil map unit information, official farmland classification (7 CFR 657), "
            "and FPPA regulatory notice."
        ),
    )(get_farmland_classification_by_point)

    mcp.tool(
        name="get_farmland_classification_by_mukey",
        description=(
            "Query USDA NRCS Soil Data Access (SDA) by Map Unit Key (mukey) to retrieve SSURGO "
            "soil map unit details, official farmland classification (7 CFR 657), and FPPA regulatory notice."
        ),
    )(get_farmland_classification_by_mukey)

    mcp.tool(
        name="analyze_farmland_by_polygon",
        description=(
            "Execute comprehensive FPPA preliminary screening on a GeoJSON Polygon or MultiPolygon AOI. "
            "Calculates total equal-area acreage, checks Census 2020 Urban Area statutory exemption status, "
            "queries intersecting SSURGO map units via SDA with exact spatial clipping, retrieves NCCPI crop "
            "productivity ratings, and generates acreage breakdowns by farmland classification."
        ),
    )(analyze_farmland_by_polygon)

    mcp.tool(
        name="get_soil_polygons_by_geometry",
        description=(
            "Retrieve intersecting SSURGO soil map unit polygon geometries and attributes as a GeoJSON "
            "FeatureCollection for a Polygon or MultiPolygon AOI, with support for server-side clipping and geodesic acreage."
        ),
    )(get_soil_polygons_by_geometry)

    mcp.tool(
        name="check_urban_area_exemption",
        description=(
            "Screen a project footprint against Census Bureau 2020 Urban Area boundaries (Layer 6) "
            "for preliminary statutory exemption analysis under 7 CFR § 658.2(a)."
        ),
    )(check_urban_area_exemption)

    mcp.tool(
        name="get_soil_interpretations",
        description=(
            "Retrieve component-weighted soil interpretations (such as NCCPI v3 crop productivity) "
            "from USDA NRCS Soil Data Access (SDA) for a list of map unit keys (mukeys)."
        ),
    )(get_soil_interpretations)
