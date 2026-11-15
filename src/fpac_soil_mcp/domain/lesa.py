"""Unified Land Evaluation and Site Assessment (LESA) Calculation Engine.

Consolidates statutory and technical scoring rules under the Farmland Protection Policy Act (FPPA)
and 7 CFR Part 658 for both:
- Standard Site Projects (Form AD-1006, 12 criteria, max 160 SA points)
- Linear Corridor Projects (Form NRCS-CPA-106, Criteria 5 & 6 zeroed, 8 & 11 adjusted to 25 pts)
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Any, Literal, overload

from pydantic import BaseModel, Field

from fpac_soil_mcp.core.constants import (
    CORRIDOR_CRITERIA_MAX_POINTS,
    CORRIDOR_CRITERIA_NAMES,
    CRITERION_2_HIGH_RATIO,
    CRITERION_2_LOW_RATIO,
    CRITERION_2_RULE_REFERENCE,
    CRITERION_2_RULE_VERSION,
    LESA_ACTION_AVOID_MINIMIZE_CONVERSION,
    LESA_ACTION_REDUCE_FOOTPRINT,
    LESA_THRESHOLD_SCORE,
    MAX_LAND_EVALUATION_SCORE,
    MAX_SITE_ASSESSMENT_SCORE,
    MAX_TOTAL_LESA_SCORE,
    REGULATORY_LIMITATIONS,
    REGULATORY_NOTICE,
    SITE_CRITERIA_MAX_POINTS,
    SITE_CRITERIA_NAMES,
    STATUTORY_DETERMINATIONS,
)
from fpac_soil_mcp.models.lesa import (
    SUPPORTED_INDEX_MSG,
    LandEvaluationSummary,
    MapUnitProductivityRating,
    PreliminaryLESAResponse,
    ProductivityIndexType,
    SiteAssessmentCriterion,
    SiteAssessmentSummary,
)

try:
    from fpac_soil_mcp.domain.site_assessment import SITE_ASSESSMENT_REGISTRY
except ImportError:
    from fpac_soil_mcp.site_assessment import SITE_ASSESSMENT_REGISTRY

__all__ = [
    "CORRIDOR_CRITERIA_MAX_POINTS",
    "CORRIDOR_CRITERIA_NAMES",
    "CRITERION_EVALUATORS",
    "LESA_THRESHOLD_SCORE",
    "MAX_LAND_EVALUATION_SCORE",
    "MAX_SITE_ASSESSMENT_SCORE",
    "MAX_TOTAL_LESA_SCORE",
    "SITE_CRITERIA_MAX_POINTS",
    "SITE_CRITERIA_NAMES",
    "BaseCriterionEvaluator",
    "CorridorSiteAssessmentSummary",
    "CriterionEvaluation",
    "CriterionEvaluator",
    "FarmSizeCriterionEvaluator",
    "FarmSizeCriterionStrategy",
    "LESAEvaluationResult",
    "PerimeterCriterionEvaluator",
    "PerimeterCriterionStrategy",
    "StandardCriterionEvaluator",
    "StandardCriterionStrategy",
    "ZeroedCriterionEvaluator",
    "ZeroedCriterionStrategy",
    "calculate_area_weighted_le",
    "calculate_composite_le",
    "calculate_county_farmland_percentile",
    "calculate_criterion_2_score",
    "calculate_criterion_7_score",
    "calculate_relative_ratings",
    "evaluate_corridor_lesa",
    "evaluate_corridor_site_assessment",
    "evaluate_land_evaluation",
    "evaluate_lesa",
    "evaluate_lesa_threshold",
    "evaluate_site_assessment",
    "get_criterion_evaluators",
]


# --- Response Models for Corridor Scoring ---


class CriterionEvaluation(SiteAssessmentCriterion):
    """Detailed evaluation of an individual Site Assessment criterion."""


class CorridorSiteAssessmentSummary(BaseModel):
    """Aggregated Site Assessment (Part VI) evaluation under 7 CFR § 658.5(c)."""

    criteria: list[CriterionEvaluation] = Field(
        description="List of all 12 evaluated site assessment criteria"
    )
    total_sa_points: float = Field(
        ge=0.0, le=160.0, description="Sum of awarded site assessment points (Max 160)"
    )
    max_sa_points: int = Field(
        default=MAX_SITE_ASSESSMENT_SCORE, description="Statutory maximum SA points (160)"
    )
    all_criteria_justified: bool = Field(
        default=True, description="True if all manual/subjective criteria have justifications"
    )


class LESAEvaluationResult(BaseModel):
    """Complete Land Evaluation and Site Assessment (LESA) evaluation for Form NRCS-CPA-106."""

    land_evaluation_score: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Relative Land Evaluation (LE) score derived from SSURGO/NCCPI (0-100), or None if unmapped",
    )
    site_assessment: CorridorSiteAssessmentSummary = Field(
        description="Evaluated CPA-106 Site Assessment criteria and summary"
    )
    total_lesa_score: float | None = Field(
        default=None,
        ge=0.0,
        le=260.0,
        description="Combined total LESA score (LE + SA) on 0-260 point scale, or None if LE unavailable",
    )
    threshold_score: int = Field(
        default=LESA_THRESHOLD_SCORE,
        description="160-point threshold described in 7 CFR § 658.4(c)(2)-(4)",
    )
    threshold_exceeded: bool | None = Field(
        default=None,
        description=(
            "True if the score is 160 or more, False if below 160, None if LE is unavailable; "
            "this indicates consideration guidance, not a requirement to select an alternative"
        ),
    )
    statutory_determination: str = Field(
        description="Statutory recommendation under 7 CFR § 658.4(c)",
    )
    recommended_actions: list[str] = Field(
        default_factory=list,
        description="Recommended or regulatory consideration guidance based on the LESA score",
    )
    regulatory_notice: str = Field(
        default=REGULATORY_NOTICE,
        description="Preliminary screening disclaimer",
    )


# --- Core Land Evaluation Normalization & Scoring ---


def _normalize_productivity_index(
    productivity_index: ProductivityIndexType | str,
) -> ProductivityIndexType:
    """Normalize public productivity-index inputs for summary construction."""
    if isinstance(productivity_index, str):
        try:
            return ProductivityIndexType(productivity_index.upper())
        except ValueError:
            raise ValueError(
                f"Unsupported productivity index type '{productivity_index}'. {SUPPORTED_INDEX_MSG}"
            ) from None
    return productivity_index


def calculate_relative_ratings(
    ratings: list[dict[str, Any]],
    county_max: float,
) -> list[MapUnitProductivityRating]:
    """Calculate relative productivity ratings for a collection of soil map units.

    Normalizes each raw productivity rating against the county maximum baseline:
        RR_i = min(1.0, max(0.0, raw_rating / county_max))

    Handles unrated, null, or invalid ratings (e.g. 99, 999, negative, None, '')
    by marking is_rated=False and providing unrated_reason.

    Args:
        ratings: List of map unit rating dictionaries containing 'mukey', and optionally
                 'musym', 'muname', 'raw_rating'/'rating', 'is_rated', 'unrated_reason'.
        county_max: Maximum baseline productivity rating for the county / survey area.

    Returns:
        List of MapUnitProductivityRating instances.
    """
    result: list[MapUnitProductivityRating] = []

    for item in ratings:
        mukey = str(item.get("mukey", ""))
        musym = item.get("musym")
        muname = item.get("muname")

        raw_val = item.get("raw_rating")
        if raw_val is None:
            raw_val = item.get("rating")

        # Explicit unrated status passed in input
        explicit_is_rated = item.get("is_rated")
        unrated_reason = item.get("unrated_reason")

        if explicit_is_rated is False:
            result.append(
                MapUnitProductivityRating(
                    mukey=mukey,
                    musym=musym,
                    muname=muname,
                    raw_rating=None if raw_val is None else float(raw_val),
                    normalized_relative_rating=None,
                    county_max_rating=county_max if county_max > 0 else None,
                    is_rated=False,
                    unrated_reason=unrated_reason or "Map unit explicitly marked unrated",
                )
            )
            continue

        # Check for invalid or null raw rating
        if raw_val is None or raw_val == "":
            result.append(
                MapUnitProductivityRating(
                    mukey=mukey,
                    musym=musym,
                    muname=muname,
                    raw_rating=None,
                    normalized_relative_rating=None,
                    county_max_rating=county_max if county_max > 0 else None,
                    is_rated=False,
                    unrated_reason=unrated_reason
                    or "Missing or unavailable productivity index rating",
                )
            )
            continue

        try:
            num_raw = float(raw_val)
        except (ValueError, TypeError):
            result.append(
                MapUnitProductivityRating(
                    mukey=mukey,
                    musym=musym,
                    muname=muname,
                    raw_rating=None,
                    normalized_relative_rating=None,
                    county_max_rating=county_max if county_max > 0 else None,
                    is_rated=False,
                    unrated_reason=unrated_reason or f"Non-numeric rating value: {raw_val}",
                )
            )
            continue

        # Null-sentinel check: unrated indicators are screened consistently across
        # productivity index scales, regardless of county_max.
        is_sentinel = (
            explicit_is_rated is False
            or num_raw in (99.0, 999.0, -99.0, -999.0)
            or num_raw < 0
            or (county_max <= 1.0 and num_raw > 1.0)
        )

        if is_sentinel:
            result.append(
                MapUnitProductivityRating(
                    mukey=mukey,
                    musym=musym,
                    muname=muname,
                    raw_rating=num_raw,
                    normalized_relative_rating=None,
                    county_max_rating=county_max if county_max > 0 else None,
                    is_rated=False,
                    unrated_reason=unrated_reason
                    or f"Rating sentinel value ({num_raw}) indicates unrated/water/urban land",
                )
            )
            continue

        if county_max <= 0:
            result.append(
                MapUnitProductivityRating(
                    mukey=mukey,
                    musym=musym,
                    muname=muname,
                    raw_rating=num_raw,
                    normalized_relative_rating=None,
                    county_max_rating=None,
                    is_rated=False,
                    unrated_reason="Invalid county maximum rating (<= 0)",
                )
            )
            continue

        normalized = round(min(1.0, max(0.0, num_raw / county_max)), 4)
        result.append(
            MapUnitProductivityRating(
                mukey=mukey,
                musym=musym,
                muname=muname,
                raw_rating=num_raw,
                normalized_relative_rating=normalized,
                county_max_rating=county_max,
                is_rated=True,
                unrated_reason=None,
            )
        )

    return result


def calculate_area_weighted_le(
    mapunit_ratings: list[tuple[float, float]],
) -> tuple[float, int]:
    """Calculate area-weighted relative rating and integer candidate LE score.

    Args:
        mapunit_ratings: List of (relative_rating, acres) tuples for rated map units.

    Returns:
        Tuple of (area_weighted_relative_rating, integer_candidate_le_score).
        Example: (0.7655, 77)
    """
    if not mapunit_ratings:
        return 0.0, 0

    total_acres = 0.0
    weighted_sum = 0.0
    for rating, acres in mapunit_ratings:
        r = float(rating)
        a = float(acres)
        if a > 0:
            weighted_sum += r * a
            total_acres += a

    if total_acres <= 0:
        return 0.0, 0

    aoi_rr = round(weighted_sum / total_acres, 4)
    candidate_le = round(aoi_rr * 100)
    return aoi_rr, max(0, min(100, candidate_le))


@overload
def calculate_composite_le(
    weighted_scores: Iterable[tuple[float, float]],
) -> float | None: ...


@overload
def calculate_composite_le(weighted_scores: float, total_weight: float) -> float | None: ...


def calculate_composite_le(
    weighted_scores: Iterable[tuple[float, float]] | float,
    total_weight: float | None = None,
) -> float | None:
    """Calculate a rounded area-weighted composite Land Evaluation score.

    Supports both iterable calling form and scalar (weighted_sum, total_weight) form.
    """
    if total_weight is None:
        if not isinstance(weighted_scores, Iterable):
            raise TypeError("The iterable calling form requires an iterable of score/weight pairs")
        weighted_sum = 0.0
        weight = 0.0
        for score, acres in weighted_scores:
            weighted_sum += float(score) * float(acres)
            weight += float(acres)
    else:
        if isinstance(weighted_scores, Iterable):
            raise TypeError("The scalar calling form requires a weighted sum and total weight")
        weighted_sum = float(weighted_scores)
        weight = float(total_weight)
    return round(weighted_sum / weight, 1) if weight > 0 else None


def calculate_county_farmland_percentile(
    aoi_relative_rating: float,
    county_farmland_distribution: list[dict[str, Any]] | None,
) -> float | None:
    """Calculate county farmland comparison percentile higher.

    Calculates the percentage of qualifying rated county farmland acreage with a relative
    rating greater than or equal to the AOI's relative rating. Unrated acres or negative/sentinel
    ratings are excluded from the denominator.

    Args:
        aoi_relative_rating: Area-weighted relative rating across AOI (0.0 - 1.0).
        county_farmland_distribution: List of dicts representing county soil rating bins/distribution,
                                      each having 'acres' and 'relative_rating' / 'rating'.

    Returns:
        Percentile higher (0.0 - 100.0) rounded to 1 decimal place, or None if unavailable.
    """
    if not county_farmland_distribution:
        return None

    total_rated_county_acres = 0.0
    qualifying_acres = 0.0

    for item in county_farmland_distribution:
        acres = float(item.get("acres", 0.0))
        if acres <= 0:
            continue

        rating = item.get("relative_rating")
        if rating is None:
            rating = item.get("rating")

        if rating is None:
            continue

        try:
            rating_val = float(rating)
        except (ValueError, TypeError):
            continue

        if rating_val < 0.0 or rating_val in (99.0, 999.0):
            continue

        total_rated_county_acres += acres
        if rating_val >= aoi_relative_rating:
            qualifying_acres += acres

    if total_rated_county_acres <= 0:
        return None

    return round((qualifying_acres / total_rated_county_acres) * 100.0, 1)


def evaluate_land_evaluation(
    mapunit_ratings: list[MapUnitProductivityRating | dict[str, Any]],
    acreages: dict[str, float] | list[tuple[str, float]] | None = None,
    productivity_index: ProductivityIndexType | str = ProductivityIndexType.NCCPI,
    county_farmland_distribution: list[dict[str, Any]] | None = None,
) -> LandEvaluationSummary:
    """Aggregate map unit productivity ratings and acreages into a LandEvaluationSummary.

    Args:
        mapunit_ratings: List of MapUnitProductivityRating instances or rating dicts.
        acreages: Mapping or list of tuples of (mukey, acres).
        productivity_index: Supported soil productivity index (NCCPI).
        county_farmland_distribution: Optional county farmland rating distribution.

    Returns:
        LandEvaluationSummary instance.
    """
    prod_enum = _normalize_productivity_index(productivity_index)

    # Acreage lookup map
    acre_map: dict[str, float] = {}
    if acreages is not None:
        if isinstance(acreages, dict):
            acre_map = {str(k): float(v) for k, v in acreages.items()}
        elif isinstance(acreages, list):
            acre_map = {str(k): float(v) for k, v in acreages}

    rated_pairs: list[tuple[float, float]] = []
    rated_acres = 0.0
    unrated_acres = 0.0
    notices: list[str] = []

    for item in mapunit_ratings:
        if isinstance(item, MapUnitProductivityRating):
            mukey = item.mukey
            is_rated = item.is_rated
            rr = item.normalized_relative_rating
            unrated_reason = item.unrated_reason
            item_caveats: list[str] = []
        else:
            mukey = str(item.get("mukey", ""))
            is_rated = item.get("is_rated", True)
            rr = item.get("normalized_relative_rating")
            unrated_reason = item.get("unrated_reason")
            item_caveats = [str(c) for c in item.get("caveats", []) if c]
            source = item.get("productivity_rating_source")
            if source:
                item_caveats.append(f"Productivity rating provenance: {source}")

        for caveat in item_caveats:
            if caveat not in notices:
                notices.append(caveat)

        acres = acre_map.get(mukey)
        if acres is None and isinstance(item, dict):
            acres = item.get("acres")
        acres_val = float(acres) if acres is not None else 0.0

        if is_rated and rr is not None:
            rated_acres += acres_val
            rated_pairs.append((rr, acres_val))
        else:
            unrated_acres += acres_val
            reason = unrated_reason or "Unrated soil map unit"
            notices.append(f"Map unit {mukey} ({acres_val:.1f} ac) unrated: {reason}")

    total_acres = rated_acres + unrated_acres
    coverage_pct = round((rated_acres / total_acres * 100.0), 1) if total_acres > 0 else 0.0
    coverage_status = (
        "unknown"
        if total_acres <= 0
        else "unrated"
        if rated_acres <= 0
        else "covered"
        if rated_acres >= total_acres
        else "partial"
    )

    if rated_acres > 0:
        aoi_rr, candidate_le_int = calculate_area_weighted_le(rated_pairs)
        candidate_le_float = (
            round(aoi_rr * 100.0, 2)
            if round(aoi_rr * 100.0, 2) != candidate_le_int
            else float(candidate_le_int)
        )
    else:
        aoi_rr = None
        candidate_le_float = None
        notices.append("No rated soil map units found in AOI footprint.")

    percentile = None
    if county_farmland_distribution and rated_acres > 0:
        percentile = calculate_county_farmland_percentile(aoi_rr, county_farmland_distribution)

    return LandEvaluationSummary(
        productivity_index=prod_enum,
        aoi_relative_rating=aoi_rr,
        candidate_le_score=candidate_le_float,
        county_farmland_percentile_higher=percentile,
        rated_acreage=round(rated_acres, 2),
        unrated_acreage=round(unrated_acres, 2),
        total_acreage=round(total_acres, 2),
        coverage_percent=coverage_pct,
        coverage_status=coverage_status,
        notices=notices,
    )


# --- Helper Scoring Functions ---


def _validate_farm_size_inputs(
    project_farm_acres: float | None,
    county_average_farm_acres: float | None,
) -> None:
    for name, value in (
        ("project_farm_acres", project_farm_acres),
        ("county_average_farm_acres", county_average_farm_acres),
    ):
        if value is not None:
            try:
                is_finite = math.isfinite(value) and not isinstance(value, bool)
            except TypeError:
                is_finite = False
            if not is_finite:
                raise ValueError(f"{name} must be a finite number.")
    if project_farm_acres is not None and project_farm_acres < 0:
        raise ValueError("project_farm_acres must not be negative.")
    if county_average_farm_acres is not None and county_average_farm_acres <= 0:
        raise ValueError("county_average_farm_acres must be positive.")


def calculate_criterion_7_score(
    project_farm_acres: float,
    county_average_farm_acres: float,
) -> tuple[float, str]:
    """Calculate Criterion 7 (farm size compared to county average) score under 7 CFR § 658.5(b)(7).

    The farm unit receives 10 points when it is at least the county average.
    Deduct one point for each complete 5 percent below average, to a floor of
    zero when it is 50 percent or more below average.
    """
    _validate_farm_size_inputs(project_farm_acres, county_average_farm_acres)

    ratio = project_farm_acres / county_average_farm_acres
    pct = ratio * 100.0
    band = SITE_ASSESSMENT_REGISTRY.criterion(7).band_for(pct)
    if band is None or band.points is None:
        return 0.0, "Invalid or unavailable farm size; awarded 0 points."
    desc = (
        f"Affected farm size ({project_farm_acres:.1f} ac) is {pct:.1f}% of "
        f"county average ({county_average_farm_acres:.1f} ac); {band.label}: "
        f"{band.points:g} points awarded."
    )
    return band.points, desc


def calculate_criterion_2_score(normalized_ratio: float | None) -> tuple[float, str]:
    """Map a measured non-urban perimeter ratio to Criterion 2 points."""
    if normalized_ratio is None:
        return 0.0, "Criterion 2 evidence is unavailable; no points awarded."
    if not 0.0 <= normalized_ratio <= 1.0:
        raise ValueError(f"normalized_ratio must be between 0.0 and 1.0, got {normalized_ratio}")
    if normalized_ratio < CRITERION_2_LOW_RATIO:
        return 0.0, "Less than 20% of the perimeter borders non-urban land: 0 points."
    if normalized_ratio > CRITERION_2_HIGH_RATIO:
        return 10.0, "More than 90% of the perimeter borders non-urban land: 10 points."
    points = round(1.0 + ((normalized_ratio - 0.2) / 0.7) * 8.0)
    return float(max(1, min(9, points))), "Intermediate 20%-90% perimeter band: 1-9 points."


# --- Unified Criterion Evaluators ---


class CriterionEvaluator(ABC):
    """Abstract base strategy evaluator for Site Assessment criteria under 7 CFR § 658.5."""

    def __init__(
        self,
        criterion_number: int,
        max_points: int | None = None,
        name: str | None = None,
    ) -> None:
        self.criterion_number = criterion_number
        self.max_points = (
            max_points if max_points is not None else CORRIDOR_CRITERIA_MAX_POINTS[criterion_number]
        )
        self.name = name if name is not None else CORRIDOR_CRITERIA_NAMES[criterion_number]

    @abstractmethod
    def evaluate(
        self,
        crit_input: dict[str, Any] | None = None,
        project_farm_acres: float | None = None,
        county_average_farm_acres: float | None = None,
    ) -> CriterionEvaluation:
        """Evaluate criterion score and return CriterionEvaluation."""
        ...


class ZeroedCriterionEvaluator(CriterionEvaluator):
    """Evaluator for statutorily zeroed criteria in corridor projects (Criteria 5 and 6)."""

    def evaluate(
        self,
        crit_input: dict[str, Any] | None = None,
        project_farm_acres: float | None = None,
        county_average_farm_acres: float | None = None,
    ) -> CriterionEvaluation:
        return CriterionEvaluation(
            criterion_number=self.criterion_number,
            name=self.name,
            max_points=0,
            awarded_points=0.0,
            is_statutorily_zeroed=True,
            is_automated=True,
            input_authority="machine_estimate",
            justification="Statutorily set to 0 points for corridor projects under 7 CFR § 658.5(c).",
        )


class PerimeterCriterionEvaluator(CriterionEvaluator):
    """Evaluator for Criterion 2 using TIGERweb perimeter evidence."""

    def evaluate(
        self,
        crit_input: dict[str, Any] | None = None,
        project_farm_acres: float | None = None,
        county_average_farm_acres: float | None = None,
    ) -> CriterionEvaluation:
        input_data = crit_input or {}
        evidence = input_data.get("perimeter_evidence")
        if not isinstance(evidence, dict):
            evidence = input_data
        status = evidence.get("evidence_status", "not_provided")

        explicit_override = "awarded_points" in input_data and not isinstance(
            input_data.get("awarded_points"), dict
        )
        if explicit_override:
            justification = input_data.get("justification", "")
            if not isinstance(justification, str) or not justification.strip():
                raise ValueError("Analyst-proposed criterion points require a rationale.")
            try:
                awarded = max(0.0, min(float(self.max_points), float(input_data["awarded_points"])))
            except (TypeError, ValueError):
                awarded = 0.0
            is_automated = bool(input_data.get("is_automated", False))
            input_authority = (
                input_data.get("input_authority")
                if input_data.get("input_authority") == "unavailable"
                else "analyst_proposed"
            )
        else:
            ratio = evidence.get("normalized_ratio")
            has_agricultural_source = evidence.get("is_agricultural", False) is True
            is_verified = evidence.get("is_verified", False) is True
            if status == "measured" and ratio is None:
                status = "unavailable"
                awarded = 0.0
                justification = (
                    "Criterion 2 measured evidence is unavailable for scoring because "
                    "the normalized perimeter ratio is missing."
                )
            elif status == "measured" and (not has_agricultural_source or not is_verified):
                status = "unavailable"
                awarded = 0.0
                justification = (
                    "Criterion 2 requires verified agricultural adjacency evidence; "
                    "unverified or non-agricultural screening evidence is unavailable for scoring."
                )
            else:
                awarded, justification = calculate_criterion_2_score(ratio)
            if status != "measured":
                awarded = 0.0
                justification = evidence.get("error_message") or justification
            is_automated = status == "measured"
            input_authority = (
                "verified"
                if status == "measured" and is_verified
                else "machine_estimate"
                if status == "measured"
                else "unavailable"
            )

        return CriterionEvaluation(
            criterion_number=self.criterion_number,
            name=self.name,
            max_points=self.max_points,
            awarded_points=awarded,
            normalized_ratio=evidence.get("normalized_ratio"),
            evidence_status=status,
            rule_reference=evidence.get("rule_reference", CRITERION_2_RULE_REFERENCE),
            rule_version=evidence.get("rule_version", CRITERION_2_RULE_VERSION),
            source_provenance=evidence.get("source_provenance", []),
            is_verified=(
                evidence.get("is_verified", False) is True
                and (status == "measured" or (explicit_override and status == "provided"))
            ),
            input_authority=input_authority,
            is_statutorily_zeroed=False,
            is_automated=is_automated,
            justification=justification,
        )


class FarmSizeCriterionEvaluator(CriterionEvaluator):
    """Evaluator for Criterion 7 (farm size compared to county average)."""

    def evaluate(
        self,
        crit_input: dict[str, Any] | None = None,
        project_farm_acres: float | None = None,
        county_average_farm_acres: float | None = None,
    ) -> CriterionEvaluation:
        input_data = crit_input or {}
        if project_farm_acres is not None and county_average_farm_acres is not None:
            awarded, justification = calculate_criterion_7_score(
                project_farm_acres, county_average_farm_acres
            )
            is_automated = True
            input_authority = "machine_estimate"
        else:
            raw_pts = input_data.get("awarded_points", 0.0)
            try:
                awarded = float(raw_pts)
            except (ValueError, TypeError):
                awarded = 0.0

            awarded = max(0.0, min(float(self.max_points), awarded))
            justification = input_data.get("justification", "")
            explicit_override = "awarded_points" in input_data
            is_automated = (
                bool(input_data.get("is_automated", False)) if explicit_override else False
            )
            input_authority = "analyst_proposed" if explicit_override else "unavailable"

            if not str(justification).strip() and not is_automated and explicit_override:
                raise ValueError("Analyst-proposed criterion points require a rationale.")

        return CriterionEvaluation(
            criterion_number=self.criterion_number,
            name=self.name,
            max_points=self.max_points,
            awarded_points=awarded,
            is_statutorily_zeroed=False,
            is_automated=is_automated,
            input_authority=input_authority,
            justification=justification,
            evidence_status=input_data.get(
                "evidence_status", "provided" if "awarded_points" in input_data else "not_provided"
            ),
            is_verified=(
                input_data.get("is_verified") is True
                and input_data.get("evidence_status") == "provided"
            ),
            source_provenance=input_data.get("source_provenance", []),
        )


class StandardCriterionEvaluator(CriterionEvaluator):
    """Evaluator for standard or custom-weighted criteria."""

    def evaluate(
        self,
        crit_input: dict[str, Any] | None = None,
        project_farm_acres: float | None = None,
        county_average_farm_acres: float | None = None,
    ) -> CriterionEvaluation:
        input_data = crit_input or {}
        raw_pts = input_data.get("awarded_points", 0.0)
        try:
            awarded = float(raw_pts)
        except (ValueError, TypeError):
            awarded = 0.0

        awarded = max(0.0, min(float(self.max_points), awarded))
        justification = input_data.get("justification", "")
        explicit_override = "awarded_points" in input_data
        is_automated = bool(input_data.get("is_automated", False)) if explicit_override else False
        input_authority = "analyst_proposed" if explicit_override else "unavailable"

        if not justification and not is_automated and explicit_override:
            justification = f"Points ({awarded}/{self.max_points}) entered without explicit justification rationale."

        return CriterionEvaluation(
            criterion_number=self.criterion_number,
            name=self.name,
            max_points=self.max_points,
            awarded_points=awarded,
            is_statutorily_zeroed=False,
            is_automated=is_automated,
            input_authority=input_authority,
            justification=justification,
            evidence_status=input_data.get(
                "evidence_status", "provided" if explicit_override else "not_provided"
            ),
            is_verified=(
                input_data.get("is_verified") is True
                and explicit_override
                and input_data.get("evidence_status") == "provided"
            ),
            source_provenance=input_data.get("source_provenance", []),
        )


# Strategy aliases for backwards compatibility
BaseCriterionEvaluator = CriterionEvaluator
ZeroedCriterionStrategy = ZeroedCriterionEvaluator
PerimeterCriterionStrategy = PerimeterCriterionEvaluator
FarmSizeCriterionStrategy = FarmSizeCriterionEvaluator
StandardCriterionStrategy = StandardCriterionEvaluator


def get_criterion_evaluators(
    project_type: Literal["site", "corridor"] = "site",
) -> dict[int, CriterionEvaluator]:
    """Retrieve the dictionary of criterion evaluators for site or corridor project type."""
    is_corridor = project_type.lower() == "corridor"
    max_pts = CORRIDOR_CRITERIA_MAX_POINTS if is_corridor else SITE_CRITERIA_MAX_POINTS
    names = CORRIDOR_CRITERIA_NAMES if is_corridor else SITE_CRITERIA_NAMES

    evaluators: dict[int, CriterionEvaluator] = {}
    for crit_num in range(1, 13):
        limit = max_pts[crit_num]
        name = names[crit_num]

        if is_corridor and crit_num in (5, 6):
            evaluators[crit_num] = ZeroedCriterionEvaluator(crit_num, limit, name)
        elif crit_num == 2:
            evaluators[crit_num] = PerimeterCriterionEvaluator(crit_num, limit, name)
        elif crit_num == 7:
            evaluators[crit_num] = FarmSizeCriterionEvaluator(crit_num, limit, name)
        else:
            evaluators[crit_num] = StandardCriterionEvaluator(crit_num, limit, name)

    return evaluators


CRITERION_EVALUATORS: dict[int, CriterionEvaluator] = get_criterion_evaluators("corridor")


# --- Site Assessment Evaluation Functions ---


def evaluate_site_assessment(
    criteria_inputs: dict[int | str, dict[str, Any]] | None = None,
    project_type: Literal["site", "corridor"] = "site",
    project_farm_acres: float | None = None,
    county_average_farm_acres: float | None = None,
) -> SiteAssessmentSummary:
    """Evaluate Site Assessment criteria under 7 CFR § 658.5 for Site or Corridor projects.

    Args:
        criteria_inputs: Dict mapping criterion number (1-12) to dict containing 'awarded_points',
                         'justification', 'is_automated', etc.
        project_type: 'site' (Form AD-1006 rules) or 'corridor' (Form NRCS-CPA-106 rules).
        project_farm_acres: Optional farm size in acres for Criterion 7.
        county_average_farm_acres: Optional NASS county average farm size.

    Returns:
        SiteAssessmentSummary with evaluated criteria list and total points (0-160).
    """
    normalized_inputs: dict[int, dict[str, Any]] = {}
    if criteria_inputs:
        for k, v in criteria_inputs.items():
            try:
                normalized_inputs[int(k)] = v if isinstance(v, dict) else {}
            except (ValueError, TypeError):
                continue

    _validate_farm_size_inputs(project_farm_acres, county_average_farm_acres)
    if (
        project_farm_acres is not None
        and county_average_farm_acres is not None
        and normalized_inputs.get(7)
    ):
        raise ValueError(
            "Criterion 7 cannot combine farm-acreage inputs with an explicit fact or point override."
        )

    evaluators = get_criterion_evaluators(project_type)
    criteria: list[SiteAssessmentCriterion] = []
    total_pts = 0.0

    for crit_num in range(1, 13):
        evaluator = evaluators[crit_num]
        crit_input = normalized_inputs.get(crit_num)
        item = evaluator.evaluate(
            crit_input=crit_input,
            project_farm_acres=project_farm_acres,
            county_average_farm_acres=county_average_farm_acres,
        )
        criteria.append(item)
        total_pts += item.awarded_points

    total_sa = min(160.0, round(total_pts, 2))
    evaluation_status = (
        "complete"
        if criteria and all(c.input_authority != "unavailable" for c in criteria)
        else "incomplete"
    )
    return SiteAssessmentSummary(
        total_points=total_sa,
        criteria=criteria,
        evaluation_status=evaluation_status,
    )


class _SiteAssessmentAggregator:
    """Encapsulate criterion evaluation and statutory total reconciliation."""

    def __init__(
        self,
        inputs: dict[int, dict[str, Any]],
        project_farm_acres: float | None,
        county_average_farm_acres: float | None,
    ) -> None:
        self.inputs = inputs
        self.project_farm_acres = project_farm_acres
        self.county_average_farm_acres = county_average_farm_acres

    def evaluate(self) -> CorridorSiteAssessmentSummary:
        criteria: list[CriterionEvaluation] = []
        total = 0.0
        all_justified = True
        for crit_num in range(1, 13):
            evaluator = CRITERION_EVALUATORS.get(crit_num) or StandardCriterionEvaluator(crit_num)
            crit_input = self.inputs.get(crit_num)
            item = evaluator.evaluate(
                crit_input=crit_input,
                project_farm_acres=self.project_farm_acres,
                county_average_farm_acres=self.county_average_farm_acres,
            )
            if (
                item.awarded_points > 0
                and not item.is_automated
                and (
                    not crit_input
                    or not crit_input.get("justification")
                    or not str(crit_input.get("justification")).strip()
                )
            ):
                all_justified = False
            criteria.append(item)
            total += item.awarded_points
        return CorridorSiteAssessmentSummary(
            criteria=criteria,
            total_sa_points=min(160.0, round(total, 2)),
            max_sa_points=MAX_SITE_ASSESSMENT_SCORE,
            all_criteria_justified=all_justified,
        )


def evaluate_corridor_site_assessment(
    criteria_inputs: dict[int, dict[str, Any]] | None = None,
    project_farm_acres: float | None = None,
    county_average_farm_acres: float | None = None,
) -> CorridorSiteAssessmentSummary:
    """Evaluate all 12 Site Assessment criteria under 7 CFR § 658.5(c) for corridor projects.

    Enforces:
    - Zeroed criteria 5 & 6 (0 pts max).
    - Adjusted criteria 8 & 11 (25 pts max each).
    - Automated NASS comparison for criterion 7 if farm sizes provided.
    - Max 160 points total SA.

    Args:
        criteria_inputs: Dict mapping criterion number (1-12) to dict containing
                         'awarded_points' (float) and optional 'justification' (str).
        project_farm_acres: Optional project parcel farm size in acres.
        county_average_farm_acres: Optional NASS county average farm size.

    Returns:
        CorridorSiteAssessmentSummary object.
    """
    return _SiteAssessmentAggregator(
        criteria_inputs or {}, project_farm_acres, county_average_farm_acres
    ).evaluate()


# --- Threshold Evaluator & Top-Level Routers ---


def evaluate_lesa_threshold(
    total_lesa_score: float,
    project_type: str = "site",
) -> tuple[bool, str, list[str]]:
    """Evaluate the 160-point protection-consideration threshold under 7 CFR § 658.4(c).

    Threshold rule:
    - Score >= 160: USDA recommends increasing levels of consideration for protection; agencies
      consider alternatives and other factors when deciding on a proposed action.
    - Score < 160: No further consideration for protection or additional site evaluation is needed.

    Args:
        total_lesa_score: Combined LE + SA score (0 - 260 scale).
        project_type: Project geometry type ('site' or 'corridor').

    Returns:
        Tuple of (mandatory_alternatives_required, statutory_determination_text, recommended_actions).
    """
    threshold_exceeded = total_lesa_score >= LESA_THRESHOLD_SCORE
    is_corridor = project_type.lower() == "corridor"
    form_ref = "Form NRCS-CPA-106" if is_corridor else "Form AD-1006"

    if threshold_exceeded:
        determination = STATUTORY_DETERMINATIONS["THRESHOLD_EXCEEDED"].format(
            total_lesa=total_lesa_score
        )
        actions = [
            LESA_ACTION_AVOID_MINIMIZE_CONVERSION,
            LESA_ACTION_REDUCE_FOOTPRINT,
            "Consult with USDA NRCS State/Local Conservationist to review Site Assessment criteria scores and mitigation options.",
            f"Complete official USDA {form_ref} prior to final federal project approval.",
        ]
    else:
        determination = STATUTORY_DETERMINATIONS["THRESHOLD_NOT_EXCEEDED"].format(
            total_lesa=total_lesa_score
        )
        actions = [
            "Retain this preliminary screening score and documentation in the project administrative record.",
            f"Complete {form_ref} Parts I, II, III, and VI for federal agency reporting.",
        ]

    return threshold_exceeded, determination, actions


def evaluate_lesa(
    project_name: str,
    land_evaluation: LandEvaluationSummary | float | None,
    site_assessment: SiteAssessmentSummary | dict[int | str, dict[str, Any]] | float | None = None,
    project_type: Literal["site", "corridor"] = "site",
    project_farm_acres: float | None = None,
    county_average_farm_acres: float | None = None,
    productivity_index: ProductivityIndexType | str = ProductivityIndexType.NCCPI,
) -> PreliminaryLESAResponse:
    """Unified LESA evaluation router combining Land Evaluation and Site Assessment.

    Computes total combined LESA score, statutory threshold trigger, and returns
    a fully validated PreliminaryLESAResponse.

    Args:
        project_name: Project name or identifier.
        land_evaluation: LandEvaluationSummary or candidate LE float score (0-100), or None.
        site_assessment: SiteAssessmentSummary or criteria input dict or float total points.
        project_type: 'site' for Form AD-1006 or 'corridor' for Form NRCS-CPA-106.
        project_farm_acres: Affected farm parcel size in acres.
        county_average_farm_acres: County average farm size in acres.
        productivity_index: Supported soil productivity index (NCCPI).

    Returns:
        PreliminaryLESAResponse object.
    """
    # Normalize once so fallback summaries preserve the requested index type.
    normalized_productivity_index = _normalize_productivity_index(productivity_index)

    def fallback_land_evaluation(
        score: float | None = None,
        *,
        available: bool = False,
    ) -> LandEvaluationSummary:
        bounded_score = max(0.0, min(100.0, float(score))) if score is not None else None
        return LandEvaluationSummary(
            productivity_index=normalized_productivity_index,
            aoi_relative_rating=(
                round(bounded_score / 100.0, 4) if bounded_score is not None else None
            ),
            candidate_le_score=bounded_score,
            rated_acreage=0.0,
            unrated_acreage=0.0,
            total_acreage=0.0,
            coverage_percent=100.0 if available else 0.0,
            notices=[] if available else ["Land Evaluation score unavailable."],
        )

    # 1. Resolve Land Evaluation Summary
    if isinstance(land_evaluation, LandEvaluationSummary):
        if land_evaluation.productivity_index != normalized_productivity_index:
            le_summary = land_evaluation.model_copy(
                update={"productivity_index": normalized_productivity_index}
            )
        else:
            le_summary = land_evaluation
    elif isinstance(land_evaluation, (int, float)):
        le_summary = fallback_land_evaluation(land_evaluation, available=True)
    else:
        le_summary = fallback_land_evaluation()

    # 2. Resolve Site Assessment Summary
    if isinstance(site_assessment, SiteAssessmentSummary):
        sa_summary = site_assessment
    elif isinstance(site_assessment, dict):
        sa_summary = evaluate_site_assessment(
            criteria_inputs=site_assessment,
            project_type=project_type,
            project_farm_acres=project_farm_acres,
            county_average_farm_acres=county_average_farm_acres,
        )
    elif isinstance(site_assessment, (int, float)):
        sa_score = max(0.0, min(160.0, float(site_assessment)))
        sa_summary = SiteAssessmentSummary(
            total_points=sa_score,
            criteria=[],
            evaluation_status="indeterminate",
        )
    else:
        sa_summary = evaluate_site_assessment(
            criteria_inputs=None,
            project_type=project_type,
            project_farm_acres=project_farm_acres,
            county_average_farm_acres=county_average_farm_acres,
        )

    # 3. Calculate Total LESA Score and Threshold
    if le_summary.candidate_le_score is None or sa_summary.evaluation_status != "complete":
        limitations = list(REGULATORY_LIMITATIONS)
        if le_summary.candidate_le_score is None:
            limitations.append(
                "Land Evaluation score unavailable; total LESA score is indeterminate."
            )
        else:
            limitations.append(
                "Site Assessment inputs incomplete; threshold evaluation is not evaluated."
            )
        return PreliminaryLESAResponse(
            project_name=project_name,
            project_type=project_type,
            land_evaluation=le_summary,
            site_assessment=sa_summary,
            total_lesa_score=None,
            mandatory_alternatives_required=None,
            threshold_status="not_evaluated",
            regulatory_notice=REGULATORY_NOTICE,
            limitations=limitations,
        )

    total_lesa = round(min(260.0, le_summary.candidate_le_score + sa_summary.total_points), 2)
    mandatory_alt, determination, _actions = evaluate_lesa_threshold(
        total_lesa, project_type=project_type
    )

    limitations = list(REGULATORY_LIMITATIONS)
    limitations.append(determination)

    return PreliminaryLESAResponse(
        project_name=project_name,
        project_type=project_type,
        land_evaluation=le_summary,
        site_assessment=sa_summary,
        total_lesa_score=total_lesa,
        mandatory_alternatives_required=mandatory_alt,
        regulatory_notice=REGULATORY_NOTICE,
        limitations=limitations,
    )


def evaluate_corridor_lesa(
    land_evaluation_score: float | None,
    site_assessment: CorridorSiteAssessmentSummary,
) -> LESAEvaluationResult:
    """Combine Land Evaluation and Site Assessment into a complete LESA determination.

    Evaluates the 160-point guidance in § 658.4(c)(2)-(4):
    - If Total < 160 points: Further consideration for protection and additional site evaluation
      are not needed.
    - If Total >= 160 points: USDA recommends increasing levels of consideration for protection;
      agency personnel consider alternatives and other factors when deciding on an action.
    - If LE is None: Returns partial evaluation without false below-threshold determination.

    Args:
        land_evaluation_score: Composite LE score (0-100), or None if unavailable/unmapped.
        site_assessment: Evaluated CorridorSiteAssessmentSummary (0-160).

    Returns:
        LESAEvaluationResult with scoring totals, statutory findings, and actions.
    """
    sa = site_assessment.total_sa_points

    if land_evaluation_score is None:
        determination = STATUTORY_DETERMINATIONS["LE_UNAVAILABLE"].format(total_sa=sa)
        actions = [
            "Obtain official Land Evaluation (LE) score from USDA NRCS State/Local Conservationist (7 CFR § 658.4(a)).",
            f"Combine NRCS LE score with this Site Assessment ({sa:.1f}/160) to determine total LESA score.",
            "Complete official USDA Form NRCS-CPA-106 Parts IV and V prior to final federal project approval.",
        ]
        return LESAEvaluationResult(
            land_evaluation_score=None,
            site_assessment=site_assessment,
            total_lesa_score=None,
            threshold_score=LESA_THRESHOLD_SCORE,
            threshold_exceeded=None,
            statutory_determination=determination,
            recommended_actions=actions,
            regulatory_notice=REGULATORY_NOTICE,
        )

    le = max(0.0, min(100.0, round(float(land_evaluation_score), 2)))
    total_lesa = round(le + sa, 2)
    threshold_exceeded = total_lesa >= LESA_THRESHOLD_SCORE

    if threshold_exceeded:
        determination = STATUTORY_DETERMINATIONS["THRESHOLD_EXCEEDED"].format(total_lesa=total_lesa)
        actions = [
            "For scores of 160 or more, USDA recommends increasing levels of consideration for protection; when deciding on an action, agency personnel consider corridor alternatives and designs that convert fewer acres or lower-value farmland (7 CFR § 658.4(c)(3)-(4)).",
            "Consult with USDA NRCS State/Local Conservationist to review Site Assessment criteria scores and mitigation options.",
            "Complete official USDA Form NRCS-CPA-106 prior to final federal project approval.",
        ]
    else:
        determination = STATUTORY_DETERMINATIONS["THRESHOLD_NOT_EXCEEDED"].format(
            total_lesa=total_lesa
        )
        actions = [
            "Retain this preliminary screening score and documentation in the project administrative record.",
            "Complete Form NRCS-CPA-106 Parts I, II, III, and VI for federal agency reporting.",
        ]

    return LESAEvaluationResult(
        land_evaluation_score=le,
        site_assessment=site_assessment,
        total_lesa_score=total_lesa,
        threshold_score=LESA_THRESHOLD_SCORE,
        threshold_exceeded=threshold_exceeded,
        statutory_determination=determination,
        recommended_actions=actions,
        regulatory_notice=REGULATORY_NOTICE,
    )
