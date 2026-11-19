"""Preliminary LESA calculation tool."""

from __future__ import annotations

import math
from typing import Annotated, Any, Literal

from pydantic import Field
from shapely import wkt as shapely_wkt
from shapely.geometry import LineString, MultiLineString, mapping

from fpac_soil_mcp.clients.sda import PRODUCTIVITY_PROVENANCE
from fpac_soil_mcp.core.constants import CORRIDOR_CRITERIA_MAX_POINTS, SITE_CRITERIA_MAX_POINTS
from fpac_soil_mcp.domain.corridor_analyzer import CorridorAnalyzer
from fpac_soil_mcp.domain.lesa import (
    _normalize_productivity_index,
    evaluate_lesa,
)
from fpac_soil_mcp.domain.polygon_analyzer import PolygonAnalyzer
from fpac_soil_mcp.domain.site_assessment import SITE_ASSESSMENT_REGISTRY
from fpac_soil_mcp.models.coverage import (
    MAPPING_ERROR,
    MAPPING_UNMAPPED,
    RATING_ERROR,
    RATING_PARTIAL,
    RATING_RATED,
    RATING_UNKNOWN,
    RATING_UNMAPPED,
    RATING_UNRATED,
    RatingCoverage,
)
from fpac_soil_mcp.models.lesa import (
    SUPPORTED_INDEX_MSG,
    VALIDATED_PRODUCTIVITY_INDEXES,
    LandEvaluationSummary,
    PreliminaryLESAResponse,
    SiteAssessmentInputs,
    SiteAssessmentSummary,
)
from fpac_soil_mcp.spatial.geometry import (
    GeometryValidationError,
    parse_geojson_geometry,
    validate_and_sanitize_line_wkt,
    validate_and_sanitize_polygon_wkt,
)


def _score_registry_facts(
    facts: dict[str, Any] | None,
    project_type: str = "site",
    excluded_criteria: set[int] | None = None,
) -> dict[int, dict[str, Any]]:
    scored: dict[int, dict[str, Any]] = {}
    if facts is None:
        facts = {}
    if not isinstance(facts, dict):
        raise TypeError("criteria_facts must be a mapping of criterion numbers to fact inputs.")
    point_limits = (
        CORRIDOR_CRITERIA_MAX_POINTS if project_type == "corridor" else SITE_CRITERIA_MAX_POINTS
    )

    def assumed_input(number: int, raw_input: dict[str, Any] | None = None) -> dict[str, Any]:
        maximum = float(point_limits[number])
        assumption_provenance = (
            f"Registry maximum ({maximum:g} points) assumed under ADR 0018; "
            "no criterion evidence was supplied."
        )
        return {
            **(raw_input or {}),
            "assumed_points": maximum,
            "assumption_provenance": assumption_provenance,
            "is_automated": False,
            "is_verified": False,
            "input_authority": "unavailable",
            "evidence_status": "assumed (no evidence)",
            "justification": (
                f"No evidence supplied for criterion {number}; {maximum:g} registry-maximum "
                "points are shown only as a conservative assumption."
            ),
        }

    excluded_criteria = set(excluded_criteria or set())
    if project_type == "corridor":
        excluded_criteria.update({5, 6})

    for raw_number, raw_input in facts.items():
        try:
            number = int(raw_number)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid Site Assessment criterion number: {raw_number!r}.") from exc
        if not 1 <= number <= 12 or str(number) != str(raw_number):
            raise ValueError(f"Invalid Site Assessment criterion number: {raw_number!r}.")
        if number in scored:
            raise ValueError(f"Duplicate Site Assessment criterion input: {number}.")
        if not isinstance(raw_input, dict):
            raise TypeError(f"Criterion {number} fact input must be a mapping.")
        if project_type == "corridor" and number in {5, 6}:
            continue
        definition = SITE_ASSESSMENT_REGISTRY.criterion(number)
        value = raw_input.get("value", raw_input.get("answer"))
        if value is None:
            value = raw_input.get(
                "percentage"
                if definition.answer_type == "percentage"
                else "distance_miles"
                if definition.answer_type == "distance_miles"
                else "category"
            )
        numeric_value: float | None = None
        if definition.answer_type != "qualitative" and value is not None:
            if isinstance(value, bool):
                raise ValueError(f"Criterion {number} fact value must be numeric, not boolean.")
            try:
                numeric_value = float(value)
            except (TypeError, ValueError):
                if str(value).strip().lower() not in {
                    "unknown",
                    "unavailable",
                    "not available",
                    "not provided",
                    "skipped",
                    "skip",
                }:
                    raise ValueError(
                        f"Criterion {number} fact value is not valid for its registry."
                    )
        if numeric_value is not None and not math.isfinite(numeric_value):
            raise ValueError(f"Criterion {number} fact value must be finite.")
        if (
            numeric_value is not None
            and definition.answer_type != "qualitative"
            and not any(
                band.minimum is not None
                and numeric_value >= band.minimum
                and (band.maximum is None or numeric_value <= band.maximum)
                for band in definition.bands
            )
        ):
            raise ValueError(
                f"Criterion {number} fact value is outside the registry's valid range."
            )
        selected = next(
            (
                band
                for band in definition.bands
                if (
                    (
                        definition.answer_type == "qualitative"
                        and value is not None
                        and str(value).strip().lower() in {band.band_id.lower(), band.label.lower()}
                    )
                    or (
                        definition.answer_type != "qualitative"
                        and numeric_value is not None
                        and band.contains(numeric_value)
                    )
                )
            ),
            None,
        )
        if selected is None or selected.points is None:
            scored[number] = assumed_input(number, raw_input)
            continue
        is_verified = raw_input.get("is_verified") is True
        source_provenance = raw_input.get("source_provenance", [])
        if isinstance(source_provenance, str):
            source_provenance = [source_provenance]
        if not isinstance(source_provenance, list) or not all(
            isinstance(source, str) and source.strip() for source in source_provenance
        ):
            raise ValueError(
                f"Criterion {number} source_provenance must contain non-empty strings."
            )
        if definition.requires_verification and not is_verified:
            raise ValueError(f"Criterion {number} fact requires verification.")
        if definition.requires_rationale and not str(raw_input.get("justification", "")).strip():
            raise ValueError(f"Criterion {number} fact requires a rationale.")
        if number == 2 and not source_provenance:
            raise ValueError("Criterion 2 analyst-provided percentages require source provenance.")
        maximum = (
            CORRIDOR_CRITERIA_MAX_POINTS[number]
            if project_type == "corridor"
            else SITE_CRITERIA_MAX_POINTS[number]
        )
        selected_points = selected.points
        if selected.point_range is not None and numeric_value is not None:
            lower = selected.minimum if selected.minimum is not None else numeric_value
            upper = selected.maximum if selected.maximum is not None else numeric_value
            width = upper - lower
            if width > 0:
                ratio = (numeric_value - lower) / width
                selected_points = round(
                    selected.point_range[0]
                    + ratio * (selected.point_range[1] - selected.point_range[0])
                )
        points = selected_points * maximum / definition.max_points if definition.max_points else 0.0
        scored[number] = {
            **raw_input,
            "awarded_points": points,
            "is_automated": False,
            "input_authority": "analyst_proposed",
            "evidence_status": "provided",
            "is_verified": is_verified,
            "source_provenance": source_provenance,
            "justification": (
                str(raw_input.get("justification") or "").strip()
                or f"User-provided fact scored by registry rule {definition.citation}: {selected.label} -> "
                f"{points:g}/{maximum:g} points."
            ),
        }
    for number in range(1, 13):
        if number not in scored and number not in excluded_criteria:
            scored[number] = assumed_input(number)
    return scored


def _apply_conservative_site_assessment_bound(
    response: PreliminaryLESAResponse,
    assumptions: dict[int, dict[str, Any]],
) -> PreliminaryLESAResponse:
    assumed_criteria = {
        number: input_data
        for number, input_data in assumptions.items()
        if input_data.get("evidence_status") == "assumed (no evidence)"
    }
    if not assumed_criteria:
        return response

    criteria = []
    applied_assumptions = False
    for criterion in response.site_assessment.criteria:
        assumption = assumed_criteria.get(criterion.criterion_number)
        has_scored_evidence = (
            criterion.evidence_status == "measured"
            and criterion.input_authority in {"verified", "machine_estimate"}
        )
        if assumption is not None and not has_scored_evidence:
            applied_assumptions = True
            criterion = type(criterion).model_validate(
                {
                    **criterion.model_dump(),
                    "assumed_points": float(assumption["assumed_points"]),
                    "assumption_provenance": assumption["assumption_provenance"],
                    "evidence_status": "assumed (no evidence)",
                    "input_authority": "unavailable",
                    "is_verified": False,
                    "is_automated": False,
                }
            )
        criteria.append(criterion)

    if not applied_assumptions:
        return response

    site_assessment = SiteAssessmentSummary.model_validate(
        {
            **response.site_assessment.model_dump(),
            "criteria": criteria,
            "evaluation_status": "incomplete",
        }
    )
    le_score = response.land_evaluation.candidate_le_score
    upper_bound = None
    if le_score is not None:
        assumed_sa = sum(
            criterion.awarded_points + (criterion.assumed_points or 0.0) for criterion in criteria
        )
        upper_bound = round(min(260.0, le_score + assumed_sa), 2)
    return response.model_copy(
        update={
            "site_assessment": site_assessment,
            "conservative_total_lesa_upper_bound": upper_bound,
        }
    )


def calculate_preliminary_lesa(
    project_name: Annotated[str, Field(min_length=1, max_length=200)],
    geometry: dict[str, Any] | str,
    project_type: Literal["site", "corridor"] = "site",
    productivity_index: str = "nccpi",
    max_county_rating_override: Annotated[float | None, Field(gt=0, allow_inf_nan=False)] = None,
    site_assessment_inputs: SiteAssessmentInputs | None = None,
    corridor_buffer_distance: Annotated[float, Field(gt=0, allow_inf_nan=False)] = 100.0,
    corridor_buffer_units: Literal["feet", "meters", "miles"] = "feet",
) -> PreliminaryLESAResponse:
    """Calculate preliminary Land Evaluation and Site Assessment (LESA) scores and statutory threshold states.

    Accepts validated fact-based Site Assessment inputs or rationale-required analyst-proposed overrides,
    preserves unavailable and indeterminate criteria, and reports authority/provenance. Performs spatial SSURGO
    soil clipping across the AOI geometry, computes area-weighted Land Evaluation (LE, 0-100), evaluates Site
    Assessment (SA, 0-160) criteria for Form AD-1006 (site) or Form NRCS-CPA-106 (corridor), and applies the
    preliminary 160-point consideration guidance under 7 CFR § 658.4(c)(2)-(4) without issuing an
    official determination.

    Args:
        project_name: Project name or tracking identifier.
        geometry: GeoJSON geometry dict or string (Polygon or MultiPolygon for site;
            LineString or MultiLineString for corridor).
        project_type: Project geometry type ('site' requires polygon geometry for Form AD-1006;
            'corridor' requires LineString or MultiLineString geometry for Form NRCS-CPA-106).
        productivity_index: Soil productivity index type ('nccpi'). Default is 'nccpi'.
        max_county_rating_override: Optional user-supplied maximum county rating benchmark.
        site_assessment_inputs: Optional dictionary of Part VI Site Assessment parameters:
            - 'criteria_facts': dict mapping criterion numbers to registry-defined values
            - 'criteria_inputs': dict mapping criterion numbers (1-12) to {'awarded_points': float, 'justification': str}
            - 'project_farm_acres': float (size of affected farm holding)
            - 'county_average_farm_acres': float (county average farm holding size)
        corridor_buffer_distance: Buffer distance for corridor centerlines. Defaults to 100 feet.
        corridor_buffer_units: Buffer units for corridor centerlines. Defaults to feet.

    Returns:
        PreliminaryLESAResponse containing Land Evaluation summary, Site Assessment criteria breakdown,
        total LESA score (0-260) when evaluable, threshold indicator, and regulatory citations.
    """
    analysis_geometry: dict[str, Any] | str = geometry
    validated_sa_inputs = (
        SiteAssessmentInputs.model_validate(site_assessment_inputs)
        if site_assessment_inputs is not None
        else SiteAssessmentInputs()
    )
    sa_inputs = validated_sa_inputs.model_dump(mode="python", exclude_none=True)
    norm_project_type = project_type
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

    if (
        isinstance(parsed_geometry, (LineString, MultiLineString))
        and norm_project_type != "corridor"
    ):
        raise GeometryValidationError(
            "LineString or MultiLineString geometry requires project_type='corridor'; "
            "site projects require Polygon or MultiPolygon geometry."
        )

    if isinstance(parsed_geometry, (LineString, MultiLineString)):
        corridor_analyzer = CorridorAnalyzer()
        corridor_response = corridor_analyzer.analyze_corridor(
            centerline_input=geometry,
            buffer_distance=corridor_buffer_distance,
            buffer_units=corridor_buffer_units,
            productivity_index=normalized_productivity_index.value,
            max_county_rating_override=max_county_rating_override,
        )
        corridor_result = corridor_response.model_dump()
        reconciliation = corridor_result.get("reconciliation_summary") or {}
        total_acreage = float(reconciliation.get("buffered_footprint_acres") or 0.0)
        county_segments = corridor_result.get("county_segments") or []
        rated_acreage = 0.0
        mapped_acreage = 0.0
        source_coverage = []
        for segment in county_segments:
            if not isinstance(segment, dict):
                continue
            source_coverage.append(segment.get("coverage_status"))
            source_coverage.append(segment.get("productivity_coverage_status"))
            for unit in segment.get("map_units") or []:
                if not isinstance(unit, dict):
                    continue
                acres = float(unit.get("calculated_acres") or 0.0)
                mapped_acreage += acres
                if unit.get("productivity_rating") is not None:
                    rated_acreage += acres
        rated_acreage = float(
            reconciliation.get(
                "component_rated_productivity_acres",
                reconciliation.get("rated_productivity_acres", round(rated_acreage, 2)),
            )
        )
        unrated_acreage = float(
            reconciliation.get(
                "component_unrated_productivity_acres",
                reconciliation.get(
                    "unrated_productivity_acres",
                    round(max(0.0, total_acreage - rated_acreage), 2),
                ),
            )
        )
        coverage_percent = (
            float(
                reconciliation.get(
                    "productivity_coverage_percent",
                    min(100.0, round(rated_acreage / total_acreage * 100.0, 2)),
                )
            )
            if total_acreage > 0
            else 0.0
        )
        coverage_status = reconciliation.get(
            "productivity_coverage_status",
            _lesa_coverage_status(rated_acreage, total_acreage, source_coverage, mapped_acreage),
        )
        nested_evaluation = corridor_result.get("lesa_evaluation") or {}
        le_raw = nested_evaluation.get("land_evaluation") or {}
        le_score = corridor_result.get("composite_relative_rating")
        if le_score is None:
            le_score = le_raw.get("candidate_le_score")
        le_score = float(le_score) if le_score is not None else None
        rating_provenance = [PRODUCTIVITY_PROVENANCE[normalized_productivity_index.value.lower()]]
        le_notices = list(le_raw.get("notices") or [])
        le_notices.append(
            "Productivity rating source provenance: " + ", ".join(rating_provenance) + "."
        )
        le_summary = LandEvaluationSummary(
            productivity_index=normalized_productivity_index,
            candidate_le_score=le_score,
            aoi_relative_rating=round(le_score / 100.0, 4) if le_score is not None else None,
            rated_acreage=rated_acreage,
            unrated_acreage=unrated_acreage,
            total_acreage=total_acreage,
            coverage_percent=coverage_percent,
            coverage_status=coverage_status,
            rating_source_provenance=rating_provenance,
            reconciliation=reconciliation,
            notices=le_notices,
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
            productivity_index=normalized_productivity_index,
            max_county_rating_override=max_county_rating_override,
        )

        manifest = polygon_response.manifest or {}
        le_raw = manifest.get("land_evaluation")
        manifest_le_score = manifest.get("candidate_le_score")
        fallback_le_score = float(manifest_le_score) if manifest_le_score is not None else None
        if isinstance(le_raw, dict):
            try:
                le_summary = LandEvaluationSummary(**le_raw)
            except (ValueError, TypeError, KeyError):
                le_summary = LandEvaluationSummary(
                    productivity_index=normalized_productivity_index,
                    candidate_le_score=fallback_le_score,
                    aoi_relative_rating=(
                        round(fallback_le_score / 100.0, 4)
                        if fallback_le_score is not None
                        else None
                    ),
                    total_acreage=polygon_response.total_aoi_acres,
                )
        else:
            le_summary = LandEvaluationSummary(
                productivity_index=normalized_productivity_index,
                candidate_le_score=fallback_le_score,
                aoi_relative_rating=(
                    round(fallback_le_score / 100.0, 4) if fallback_le_score is not None else None
                ),
                total_acreage=polygon_response.total_aoi_acres,
            )
        if le_summary.rated_acreage == 0:
            le_summary.rated_acreage = round(
                sum(
                    unit.calculated_acres
                    for unit in polygon_response.map_units
                    if unit.productivity_rating is not None
                ),
                2,
            )
            le_summary.unrated_acreage = round(
                max(0.0, le_summary.total_acreage - le_summary.rated_acreage), 2
            )
            le_summary.coverage_percent = (
                round(le_summary.rated_acreage / le_summary.total_acreage * 100.0, 2)
                if le_summary.total_acreage > 0
                else 0.0
            )
        le_summary.coverage_status = _lesa_coverage_status(
            le_summary.rated_acreage,
            le_summary.total_acreage,
            [
                polygon_response.coverage_status,
                le_raw.get("coverage_status") if isinstance(le_raw, dict) else None,
            ],
            sum(unit.calculated_acres for unit in polygon_response.map_units),
        )
        le_summary.rating_source_provenance = [
            PRODUCTIVITY_PROVENANCE[normalized_productivity_index.value.lower()]
        ]
        provenance_notice = (
            "Productivity rating source provenance: "
            + ", ".join(le_summary.rating_source_provenance)
            + "."
        )
        if provenance_notice not in le_summary.notices:
            le_summary.notices.append(provenance_notice)

    # Extract farm acres and criteria inputs if present
    raw_criteria_inputs = sa_inputs.get("criteria_inputs", {})
    if not isinstance(raw_criteria_inputs, dict):
        raise TypeError(
            "criteria_inputs must be a mapping of criterion numbers to point overrides."
        )
    criteria_inputs = dict(raw_criteria_inputs)
    override_numbers: set[int] = set()
    if "criteria_inputs" in sa_inputs:
        for raw_number in criteria_inputs:
            try:
                number = int(raw_number)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"Invalid Site Assessment criterion number: {raw_number!r}."
                ) from exc
            if not 1 <= number <= 12:
                raise ValueError(f"Invalid Site Assessment criterion number: {raw_number!r}.")
            if number in override_numbers:
                raise ValueError(f"Duplicate Site Assessment criterion input: {number}.")
            override_numbers.add(number)
    fact_inputs = sa_inputs.get("criteria_facts")
    if isinstance(fact_inputs, dict):
        fact_numbers = {int(number) for number in fact_inputs if str(number).isdigit()}
        overlap = fact_numbers & override_numbers
        if overlap:
            raise ValueError(
                f"Conflicting fact and point override for criterion(s): {sorted(overlap)}."
            )
    project_farm_acres = sa_inputs.get("project_farm_acres")
    county_average_farm_acres = sa_inputs.get("county_average_farm_acres")
    excluded_assumption_criteria = set(override_numbers)
    if project_farm_acres is not None and county_average_farm_acres is not None:
        excluded_assumption_criteria.add(7)
    scored_registry_facts = _score_registry_facts(
        fact_inputs,
        norm_project_type,
        excluded_criteria=excluded_assumption_criteria,
    )
    criteria_inputs.update(scored_registry_facts)
    if not criteria_inputs and not any(
        key in sa_inputs for key in ("criteria_inputs", "criteria_facts")
    ):
        criteria_inputs = sa_inputs
    for number, fact_input in scored_registry_facts.items():
        if fact_input.get("evidence_status") == "assumed (no evidence)":
            criteria_inputs[number] = {
                **criteria_inputs.get(number, criteria_inputs.get(str(number), {})),
                "evidence_status": "unavailable",
            }
    if isinstance(criteria_inputs, dict):
        point_limits = (
            CORRIDOR_CRITERIA_MAX_POINTS
            if norm_project_type == "corridor"
            else SITE_CRITERIA_MAX_POINTS
        )
        for raw_number, raw_input in criteria_inputs.items():
            try:
                number = int(raw_number)
            except (TypeError, ValueError):
                continue
            if not isinstance(raw_input, dict) or "awarded_points" not in raw_input:
                continue
            try:
                points = float(raw_input["awarded_points"])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Criterion {number} points must be numeric.") from exc
            if not math.isfinite(points):
                raise ValueError(f"Criterion {number} points must be finite.")
            if not 1 <= number <= 12:
                raise ValueError(f"Invalid Site Assessment criterion number: {raw_number!r}.")
            if norm_project_type == "corridor" and number in (5, 6) and points != 0:
                raise ValueError(
                    f"Criterion {number} cannot have analyst points for corridor projects; "
                    "it is statutorily zeroed."
                )
            if points < 0 or points > point_limits[number]:
                raise ValueError(
                    f"Criterion {number} points must be between 0 and {point_limits[number]}."
                )
    result_manifest = (
        polygon_response.manifest
        if polygon_response is not None
        else corridor_result.get("manifest", {})
    )
    perimeter_evidence = result_manifest.get("criterion_2_perimeter_evidence")
    if perimeter_evidence:
        criteria_inputs = dict(criteria_inputs) if isinstance(criteria_inputs, dict) else {}
        criterion_two = dict(criteria_inputs.get(2, criteria_inputs.get("2", {})) or {})
        criterion_two["perimeter_evidence"] = perimeter_evidence
        criteria_inputs[2] = criterion_two
    lesa_response = evaluate_lesa(
        project_name=project_name,
        land_evaluation=le_summary,
        site_assessment=criteria_inputs,
        project_type=norm_project_type,
        project_farm_acres=project_farm_acres,
        county_average_farm_acres=county_average_farm_acres,
        productivity_index=normalized_productivity_index,
    )
    lesa_response = _apply_conservative_site_assessment_bound(
        lesa_response,
        scored_registry_facts,
    )

    for criterion in lesa_response.site_assessment.criteria:
        definition = SITE_ASSESSMENT_REGISTRY.criterion(criterion.criterion_number)
        criterion.rule_reference = definition.citation
        criterion.rule_version = SITE_ASSESSMENT_REGISTRY.schema_version

    # Append any polygon limitations or warnings
    if polygon_response is not None and polygon_response.limitations:
        for lim in polygon_response.limitations:
            if lim not in lesa_response.limitations:
                lesa_response.limitations.append(lim)

    return lesa_response


def _lesa_coverage_status(
    rated_acreage: float,
    total_acreage: float,
    source_statuses: list[Any],
    mapped_acreage: float,
) -> RatingCoverage:
    """Normalize analysis-specific coverage outcomes to the shared rating vocabulary.

    Any failed source query (status ``error``) makes the result ``error``.
    """
    if MAPPING_ERROR in source_statuses or RATING_ERROR in source_statuses:
        return RATING_ERROR
    if total_acreage <= 0:
        return RATING_UNKNOWN
    if rated_acreage <= 0:
        if MAPPING_UNMAPPED in source_statuses or mapped_acreage <= 0:
            return RATING_UNMAPPED
        return RATING_UNRATED
    if rated_acreage >= total_acreage:
        return RATING_RATED
    return RATING_PARTIAL
