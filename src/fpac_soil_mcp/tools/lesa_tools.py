"""Preliminary LESA calculation tool."""

from __future__ import annotations

from typing import Any

from shapely import wkt as shapely_wkt
from shapely.geometry import LineString, MultiLineString, mapping

from fpac_soil_mcp.geometry import (
    GeometryValidationError,
    parse_geojson_geometry,
    validate_and_sanitize_line_wkt,
    validate_and_sanitize_polygon_wkt,
)
from fpac_soil_mcp.lesa import _normalize_productivity_index, evaluate_lesa
from fpac_soil_mcp.models import (
    SUPPORTED_INDEX_MSG,
    VALIDATED_PRODUCTIVITY_INDEXES,
    LandEvaluationSummary,
    PreliminaryLESAResponse,
    ProductivityIndexType,
)
from fpac_soil_mcp.polygon_analysis import PolygonAnalyzer
from fpac_soil_mcp.tools.spatial_analysis_tools import analyze_corridor_fppa


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
        productivity_index: Soil productivity index type ('nccpi'). Default is 'nccpi'.
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
    if normalized_productivity_index not in VALIDATED_PRODUCTIVITY_INDEXES:
        raise ValueError(
            f"Unsupported productivity index type '{productivity_index}'. {SUPPORTED_INDEX_MSG}"
        )
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
            "productivity_index": normalized_productivity_index,
        }
        if max_county_rating_override is not None:
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
    perimeter_evidence = (
        polygon_response.manifest.get("criterion_2_perimeter_evidence")
        if polygon_response is not None
        else None
    )
    if perimeter_evidence:
        criteria_inputs = dict(criteria_inputs) if isinstance(criteria_inputs, dict) else {}
        criterion_two = dict(criteria_inputs.get(2, criteria_inputs.get("2", {})) or {})
        criterion_two["perimeter_evidence"] = perimeter_evidence
        criteria_inputs[2] = criterion_two
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
