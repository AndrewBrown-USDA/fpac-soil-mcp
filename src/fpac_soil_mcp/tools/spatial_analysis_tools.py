"""Spatial analysis tools for FPPA screening."""

from __future__ import annotations

from typing import Any

from fpac_soil_mcp.corridor_analysis import CorridorAnalyzer
from fpac_soil_mcp.corridor_scoring import (
    evaluate_corridor_lesa,
    evaluate_corridor_site_assessment,
)
from fpac_soil_mcp.lesa import _normalize_productivity_index
from fpac_soil_mcp.models import (
    SUPPORTED_INDEX_MSG,
    VALIDATED_PRODUCTIVITY_INDEXES,
    PolygonFarmlandAnalysisResponse,
)
from fpac_soil_mcp.polygon_analysis import PolygonAnalyzer


def analyze_farmland_by_polygon(
    geojson: dict | str,
    include_nccpi: bool = True,
    productivity_index: str = "nccpi",
    max_county_rating_override: float | None = None,
) -> PolygonFarmlandAnalysisResponse:
    """Execute comprehensive FPPA preliminary screening on a GeoJSON Polygon or MultiPolygon AOI.

    Calculates geodesic surface acreage, checks Census 2020 Urban Area boundaries,
    queries intersecting SSURGO soil map units from USDA NRCS SDA, fetches NCCPI
    crop productivity ratings, computes candidate Land
    Evaluation scores, and summarizes acreage across statutory farmland categories.

    Args:
        geojson: GeoJSON geometry dict or string (Polygon or MultiPolygon).
        include_nccpi: Whether to retrieve crop productivity ratings.
        productivity_index: Soil productivity index type ('nccpi'). Default is 'nccpi'.
        max_county_rating_override: Optional user-supplied maximum county rating benchmark.

    Returns:
        PolygonFarmlandAnalysisResponse with farmland acreage summaries, urban screening, and provenance.
    """
    normalized_productivity_index = _normalize_productivity_index(productivity_index)
    if normalized_productivity_index not in VALIDATED_PRODUCTIVITY_INDEXES:
        raise ValueError(
            f"Unsupported productivity index type '{productivity_index}'. {SUPPORTED_INDEX_MSG}"
        )
    analyzer = PolygonAnalyzer()
    return analyzer.analyze_polygon(
        geojson,
        include_nccpi=include_nccpi,
        productivity_index=normalized_productivity_index,
        max_county_rating_override=max_county_rating_override,
    )


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
        productivity_index: Requested soil productivity index ('nccpi').
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
    if normalized_productivity_index not in VALIDATED_PRODUCTIVITY_INDEXES:
        raise ValueError(
            f"Unsupported productivity index type '{productivity_index}'. {SUPPORTED_INDEX_MSG}"
        )
    analyzer = CorridorAnalyzer()
    corridor_kwargs: dict[str, Any] = {
        "centerline_input": centerline,
        "buffer_distance": buffer_distance,
        "buffer_units": buffer_units,
        "indirect_geometry_input": indirect_geometry,
        "alternatives": alternatives,
        "include_nccpi": include_nccpi,
        "productivity_index": normalized_productivity_index,
    }
    if max_county_rating_override is not None:
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
        perimeter_evidence = corridor_response.manifest.get("criterion_2_perimeter_evidence")
        if perimeter_evidence:
            criterion_two = dict(parsed_crit_inputs.get(2, {}) or {})
            criterion_two["perimeter_evidence"] = perimeter_evidence
            parsed_crit_inputs[2] = criterion_two

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
