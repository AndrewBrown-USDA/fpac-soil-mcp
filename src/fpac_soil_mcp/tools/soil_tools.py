"""Soil lookup tools for FastMCP server.

Provides tools for querying USDA NRCS Soil Data Access (SDA) by WGS84 geographic
coordinates and by SSURGO map unit key (mukey).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from shapely import wkt as shapely_wkt
from shapely.errors import GEOSException, ShapelyError
from shapely.geometry import LineString, MultiLineString, mapping

from fpac_soil_mcp.constants import REGULATORY_LIMITATIONS, REGULATORY_NOTICE
from fpac_soil_mcp.corridor_analysis import CorridorAnalyzer
from fpac_soil_mcp.corridor_scoring import (
    evaluate_corridor_lesa,
    evaluate_corridor_site_assessment,
)
from fpac_soil_mcp.geometry import (
    GeometryValidationError,
    calculate_acreage,
    geometry_to_wkt,
    parse_geojson_geometry,
    validate_and_sanitize_line_wkt,
    validate_and_sanitize_polygon_wkt,
)
from fpac_soil_mcp.integration_models import UrbanExemptionRecord
from fpac_soil_mcp.lesa import _normalize_productivity_index, evaluate_lesa
from fpac_soil_mcp.models import (
    FarmlandClassificationResponse,
    LandEvaluationSummary,
    PolygonFarmlandAnalysisResponse,
    PreliminaryLESAResponse,
    ProductivityIndexType,
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
    productivity_index: str = "nccpi",
    max_county_rating_override: float | None = None,
) -> PolygonFarmlandAnalysisResponse:
    """Execute comprehensive FPPA preliminary screening on a GeoJSON Polygon or MultiPolygon AOI.

    Calculates geodesic surface acreage, checks Census 2020 Urban Area boundaries,
    queries intersecting SSURGO soil map units from USDA NRCS SDA, fetches crop
    productivity ratings (NCCPI, CSR2, CPI, Storie, or custom), computes candidate Land
    Evaluation scores, and summarizes acreage across statutory farmland categories.

    Args:
        geojson: GeoJSON geometry dict or string (Polygon or MultiPolygon).
        include_nccpi: Whether to retrieve crop productivity ratings.
        productivity_index: Soil productivity index type ('nccpi', 'csr2', 'cpi', 'storie'). Default is 'nccpi'.
        max_county_rating_override: Optional user-supplied maximum county rating benchmark.

    Returns:
        PolygonFarmlandAnalysisResponse with farmland acreage summaries, urban screening, and provenance.
    """
    analyzer = PolygonAnalyzer()
    return analyzer.analyze_polygon(
        geojson,
        include_nccpi=include_nccpi,
        productivity_index=productivity_index,
        max_county_rating_override=max_county_rating_override,
    )


def check_urban_area_exemption(
    geojson: dict | str,
) -> UrbanExemptionRecord:
    """Screen a project footprint against Census Bureau 2020 Urban Area boundaries (Layer 0).

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
    rule_name: str = "NCCPI - National Commodity Crop Productivity Index (Ver 3.0)",
    aggregation_method: str = "Weighted Average",
) -> list[dict]:
    """Retrieve component-level soil interpretations from USDA NRCS SDA for a list of map unit keys.

    Args:
        mukeys: List of SSURGO Map Unit Keys.
        rule_name: Soil interpretation rule name (default 'NCCPI - National Commodity Crop Productivity Index (Ver 3.0)').
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


def analyze_corridor_fppa(
    centerline: dict | str,
    buffer_distance: float,
    buffer_units: str = "feet",
    indirect_geometry: dict | str | None = None,
    alternatives: list[dict] | None = None,
    include_nccpi: bool = True,
    site_assessment_inputs: dict[str, Any] | None = None,
    productivity_index: str = "nccpi",
    max_county_rating_override: float | None = None,
) -> dict[str, Any]:
    """Execute multi-county linear corridor FPPA screening and statutory CPA-106 analysis.

    Buffers the direct corridor centerline, erases indirect staging overlap, partitions the project
    footprint across Census TIGERweb county boundaries, queries clipped SSURGO soil map units from USDA SDA,
    retrieves NASS agricultural baselines, calculates composite Land Evaluation (LE) ratings, and enforces
    strict sum reconciliation. If site assessment inputs are provided, evaluates statutory 7 CFR § 658.5(c)
    Site Assessment criteria and computes combined LESA threshold determinations.

    Args:
        centerline: GeoJSON LineString dict/string or WKT of the corridor centerline.
        buffer_distance: Width to buffer on each side of the centerline.
        buffer_units: Buffer distance units ('feet', 'meters', 'miles'). Default is 'feet'.
        indirect_geometry: Optional GeoJSON Polygon/MultiPolygon or WKT for staging/access areas.
        alternatives: Optional list of alternative alignment dicts [{'alternative_id': 'Alt B', 'centerline': ...}].
        include_nccpi: Whether to retrieve component-weighted NCCPI v3 crop productivity ratings.
        productivity_index: Requested soil productivity index. Supported values include
            NCCPI, CSR2, CPI, STORIE, and CUSTOM selectors.
        max_county_rating_override: Optional positive county benchmark override used
            for corridor normalization and Land Evaluation scoring.
        site_assessment_inputs: Optional dictionary of Part VI Site Assessment inputs for CPA-106 scoring:
            - 'criteria_inputs': dict mapping criterion numbers (1-12) to {'awarded_points': float, 'justification': str}
            - 'project_farm_acres': float (size of affected farm holding)
            - 'county_average_farm_acres': float (optional override for NASS average farm size)

    Returns:
        Dictionary containing CorridorFarmlandAnalysisResponse fields, plus optional 'lesa_evaluation' result.
    """
    normalized_productivity_index = _normalize_productivity_index(productivity_index)
    analyzer = CorridorAnalyzer()
    corridor_kwargs: dict[str, Any] = {
        "centerline_input": centerline,
        "buffer_distance": buffer_distance,
        "buffer_units": buffer_units,
        "indirect_geometry_input": indirect_geometry,
        "alternatives": alternatives,
        "include_nccpi": include_nccpi,
    }
    if (
        normalized_productivity_index is not ProductivityIndexType.NCCPI
        or max_county_rating_override is not None
    ):
        corridor_kwargs["productivity_index"] = productivity_index
        corridor_kwargs["max_county_rating_override"] = max_county_rating_override
    corridor_response = analyzer.analyze_corridor(
        **corridor_kwargs,
    )

    result = corridor_response.model_dump()

    if site_assessment_inputs:
        crit_inputs_raw = site_assessment_inputs.get("criteria_inputs", {})
        # Convert string criterion keys if passed as json strings
        parsed_crit_inputs = {}
        for k, v in crit_inputs_raw.items():
            try:
                parsed_crit_inputs[int(k)] = v
            except (ValueError, TypeError):
                continue

        project_farm_acres = site_assessment_inputs.get("project_farm_acres")
        county_avg_acres = site_assessment_inputs.get("county_average_farm_acres")

        # If county_avg_acres not explicitly given, compute area-weighted average from county segments
        if county_avg_acres is None and corridor_response.county_segments:
            weighted_sum = 0.0
            total_acres = 0.0
            for seg in corridor_response.county_segments:
                seg_profile = getattr(seg, "nass_profile", None)
                if isinstance(seg, dict):
                    seg_profile = seg.get("nass_profile")
                    seg_acres = seg.get("total_segment_acres", 0.0)
                else:
                    seg_acres = getattr(seg, "total_segment_acres", 0.0)

                avg_size = (
                    seg_profile.get("average_farm_size_acres")
                    if isinstance(seg_profile, dict)
                    and seg_profile.get("average_farm_size_acres") is not None
                    else seg_profile.get("farm_size_acres_avg")
                    if isinstance(seg_profile, dict)
                    else None
                )
                if avg_size is not None and seg_acres is not None and seg_acres > 0:
                    weighted_sum += float(avg_size) * float(seg_acres)
                    total_acres += float(seg_acres)

            if total_acres > 0:
                county_avg_acres = weighted_sum / total_acres
            elif corridor_response.county_segments[0].nass_profile:
                first_prof = corridor_response.county_segments[0].nass_profile
                if isinstance(first_prof, dict):
                    county_avg_acres = first_prof.get("average_farm_size_acres") or first_prof.get(
                        "farm_size_acres_avg"
                    )

        sa_summary = evaluate_corridor_site_assessment(
            criteria_inputs=parsed_crit_inputs,
            project_farm_acres=project_farm_acres,
            county_average_farm_acres=county_avg_acres,
        )

        le_score = corridor_response.composite_relative_rating
        lesa_result = evaluate_corridor_lesa(
            land_evaluation_score=le_score,
            site_assessment=sa_summary,
        )
        result["lesa_evaluation"] = lesa_result.model_dump()

    return result


def calculate_preliminary_lesa(
    project_name: str,
    geometry: dict[str, Any] | str,
    project_type: str = "site",
    productivity_index: str = "nccpi",
    max_county_rating_override: float | None = None,
    site_assessment_inputs: dict[str, Any] | None = None,
    corridor_buffer_distance: float = 100.0,
    corridor_buffer_units: str = "feet",
) -> PreliminaryLESAResponse:
    """Calculate preliminary Land Evaluation and Site Assessment (LESA) scores and statutory threshold triggers.

    Performs spatial SSURGO soil clipping across the AOI geometry, computes area-weighted Land Evaluation (LE, 0-100),
    evaluates statutory Site Assessment (SA, 0-160) criteria for Form AD-1006 (site) or Form NRCS-CPA-106 (corridor),
    and enforces the statutory 160-point mandatory alternatives consideration threshold under 7 CFR § 658.4(c)(2).

    Args:
        project_name: Project name or tracking identifier.
        geometry: GeoJSON geometry dict or string (Polygon or MultiPolygon for site;
            LineString or MultiLineString for corridor).
        project_type: Project geometry type ('site' for Form AD-1006 or 'corridor' for Form NRCS-CPA-106).
        productivity_index: Soil productivity index type ('nccpi', 'csr2', 'cpi', 'storie'). Default is 'nccpi'.
        max_county_rating_override: Optional user-supplied maximum county rating benchmark.
        site_assessment_inputs: Optional dictionary of Part V/VI Site Assessment parameters:
            - 'criteria_inputs': dict mapping criterion numbers (1-12) to {'awarded_points': float, 'justification': str}
            - 'project_farm_acres': float (size of affected farm holding)
            - 'county_average_farm_acres': float (county average farm holding size)
        corridor_buffer_distance: Buffer distance for corridor centerlines. Defaults to 100 feet.
        corridor_buffer_units: Buffer units for corridor centerlines. Defaults to feet.

    Returns:
        PreliminaryLESAResponse containing Land Evaluation summary, Site Assessment criteria breakdown,
        total LESA score (0-260), mandatory alternatives threshold flag, and regulatory citations.
    """
    analysis_geometry: dict[str, Any] | str = geometry
    norm_project_type = "corridor" if project_type.strip().lower() == "corridor" else "site"
    normalized_productivity_index = _normalize_productivity_index(productivity_index)
    if isinstance(geometry, (LineString, MultiLineString)):
        parsed_geometry = geometry
    elif isinstance(geometry, str) and geometry.strip().upper().startswith(
        ("LINESTRING", "MULTILINESTRING")
    ):
        parsed_geometry = shapely_wkt.loads(validate_and_sanitize_line_wkt(geometry))
    elif isinstance(geometry, str) and geometry.strip().upper().startswith(
        ("POLYGON", "MULTIPOLYGON")
    ):
        parsed_geometry = shapely_wkt.loads(validate_and_sanitize_polygon_wkt(geometry))
        analysis_geometry = mapping(parsed_geometry)
    else:
        parsed_geometry = parse_geojson_geometry(geometry, allow_line=True)

    if isinstance(parsed_geometry, (LineString, MultiLineString)):
        corridor_kwargs: dict[str, Any] = {
            "centerline": geometry,
            "buffer_distance": corridor_buffer_distance,
            "buffer_units": corridor_buffer_units,
            "include_nccpi": normalized_productivity_index is ProductivityIndexType.NCCPI,
        }
        if (
            normalized_productivity_index is not ProductivityIndexType.NCCPI
            or max_county_rating_override is not None
        ):
            corridor_kwargs["productivity_index"] = productivity_index
            corridor_kwargs["max_county_rating_override"] = max_county_rating_override
        corridor_result = analyze_corridor_fppa(**corridor_kwargs)
        le_score = float(corridor_result.get("composite_relative_rating") or 0.0)
        reconciliation = corridor_result.get("reconciliation_summary") or {}
        le_summary = LandEvaluationSummary(
            productivity_index=normalized_productivity_index,
            candidate_le_score=le_score,
            aoi_relative_rating=round(le_score / 100.0, 4),
            total_acreage=float(reconciliation.get("buffered_footprint_acres") or 0.0),
        )
        polygon_response = None
    elif norm_project_type == "corridor":
        raise GeometryValidationError(
            "Explicit corridor projects require a representable LineString or MultiLineString "
            "centerline for buffered corridor analysis; polygon geometry cannot be routed through "
            "the corridor centerline API."
        )
    else:
        analyzer = PolygonAnalyzer()
        polygon_response = analyzer.analyze_polygon(
            geojson_input=analysis_geometry,
            include_nccpi=productivity_index.strip().lower() == "nccpi",
            productivity_index=normalized_productivity_index,
            max_county_rating_override=max_county_rating_override,
        )

        manifest = polygon_response.manifest or {}
        le_raw = manifest.get("land_evaluation")
        if isinstance(le_raw, dict):
            try:
                le_summary = LandEvaluationSummary(**le_raw)
            except (ValueError, TypeError, KeyError):
                le_summary = LandEvaluationSummary(
                    productivity_index=normalized_productivity_index,
                    candidate_le_score=float(manifest.get("candidate_le_score", 0.0) or 0.0),
                    aoi_relative_rating=round(
                        float(manifest.get("candidate_le_score", 0.0) or 0.0) / 100.0, 4
                    ),
                    total_acreage=polygon_response.total_aoi_acres,
                )
        else:
            le_summary = LandEvaluationSummary(
                productivity_index=normalized_productivity_index,
                candidate_le_score=float(manifest.get("candidate_le_score", 0.0) or 0.0),
                aoi_relative_rating=round(
                    float(manifest.get("candidate_le_score", 0.0) or 0.0) / 100.0, 4
                ),
                total_acreage=polygon_response.total_aoi_acres,
            )

    # Extract farm acres and criteria inputs if present
    sa_inputs = site_assessment_inputs or {}
    criteria_inputs = sa_inputs.get("criteria_inputs", sa_inputs)
    project_farm_acres = sa_inputs.get("project_farm_acres")
    county_average_farm_acres = sa_inputs.get("county_average_farm_acres")

    lesa_response = evaluate_lesa(
        project_name=project_name,
        land_evaluation=le_summary,
        site_assessment=criteria_inputs,
        project_type=norm_project_type,
        project_farm_acres=project_farm_acres,
        county_average_farm_acres=county_average_farm_acres,
        productivity_index=normalized_productivity_index,
    )

    # Append any polygon limitations or warnings
    if polygon_response is not None and polygon_response.limitations:
        for lim in polygon_response.limitations:
            if lim not in lesa_response.limitations:
                lesa_response.limitations.append(lim)

    return lesa_response


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
            "queries intersecting SSURGO map units via SDA with exact spatial clipping, retrieves crop "
            "productivity ratings (NCCPI, CSR2, CPI, Storie), calculates candidate Land Evaluation (LE) scores, "
            "and generates acreage breakdowns by farmland classification."
        ),
    )(analyze_farmland_by_polygon)

    mcp.tool(
        name="calculate_preliminary_lesa",
        description=(
            "Calculate preliminary Land Evaluation and Site Assessment (LESA) scores and statutory threshold triggers. "
            "Performs spatial SSURGO soil clipping across the AOI geometry, computes area-weighted Land Evaluation (LE, 0-100), "
            "evaluates statutory Site Assessment (SA, 0-160) criteria for Form AD-1006 (site) or Form NRCS-CPA-106 (corridor), "
            "and enforces the statutory 160-point mandatory alternatives consideration threshold under 7 CFR § 658.4(c)(2)."
        ),
    )(calculate_preliminary_lesa)

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
            "Screen a project footprint against Census Bureau 2020 Urban Area boundaries (Layer 0) "
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

    mcp.tool(
        name="analyze_corridor_fppa",
        description=(
            "Execute multi-county linear corridor FPPA screening, topological erasure of indirect staging areas, "
            "Census TIGERweb county partitioning, USDA SDA soil intersection, NASS agricultural baseline queries, "
            "composite LE calculation, sum reconciliation, and optional 7 CFR § 658.5(c) Form NRCS-CPA-106 LESA scoring."
        ),
    )(analyze_corridor_fppa)
