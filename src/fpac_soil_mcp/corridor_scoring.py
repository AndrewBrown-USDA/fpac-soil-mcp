"""7 CFR § 658.5(c) Corridor Site Assessment & LESA Scoring Rules Engine.

Implements statutory scoring rules for USDA Form NRCS-CPA-106 (Farmland Conversion Impact
Rating for Corridor Type Projects) under the Farmland Protection Policy Act (FPPA).

Key statutory rules under 7 CFR § 658.5(c):
- Criteria 1-4: Standard parameters (Max: 15, 10, 20, 20 pts).
- Criteria 5 & 6: Statutorily ZEROED OUT (0 pts max) for linear corridor projects.
- Criterion 7: Farm size comparison against NASS county average farm size (Max: 10 pts).
- Criteria 8 & 11: Statutorily adjusted to 25 points maximum each (from standard 10/15).
- Criteria 9, 10, 12: Standard parameters (Max: 5, 20, 10 pts).
- Total Site Assessment (SA) maximum: 160 points.
- Combined LESA score (LE + SA) maximum: 260 points.
- Threshold Rule (§ 658.4(c)(2)): Total score >= 160 points requires consideration of
  alternatives to avoid or minimize farmland conversion. Total score < 160 requires no
  further farmland protection consideration.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field, field_validator

from fpac_soil_mcp.constants import (
    CORRIDOR_CRITERIA_MAX_POINTS,
    CORRIDOR_CRITERIA_NAMES,
    LESA_THRESHOLD_SCORE,
    MAX_LAND_EVALUATION_SCORE,
    MAX_SITE_ASSESSMENT_SCORE,
    MAX_TOTAL_LESA_SCORE,
    REGULATORY_NOTICE,
    STATUTORY_DETERMINATIONS,
)

# Re-export constants for backwards compatibility
__all__ = [
    "CORRIDOR_CRITERIA_MAX_POINTS",
    "CORRIDOR_CRITERIA_NAMES",
    "CRITERION_EVALUATORS",
    "LESA_THRESHOLD_SCORE",
    "MAX_LAND_EVALUATION_SCORE",
    "MAX_SITE_ASSESSMENT_SCORE",
    "MAX_TOTAL_LESA_SCORE",
    "CorridorSiteAssessmentSummary",
    "CriterionEvaluation",
    "CriterionEvaluator",
    "FarmSizeCriterionEvaluator",
    "LESAEvaluationResult",
    "StandardCriterionEvaluator",
    "ZeroedCriterionEvaluator",
    "calculate_criterion_7_score",
    "evaluate_corridor_lesa",
    "evaluate_corridor_site_assessment",
]


class CriterionEvaluation(BaseModel):
    """Detailed evaluation of an individual Site Assessment criterion."""

    criterion_number: int = Field(ge=1, le=12, description="Criterion number (1-12)")
    name: str = Field(description="Name and statutory description of the criterion")
    max_points: int = Field(ge=0, le=25, description="Statutory maximum point limit")
    awarded_points: float = Field(ge=0.0, description="Points awarded for this criterion")
    is_statutorily_zeroed: bool = Field(
        default=False,
        description="True if criterion is statutorily zeroed out for corridor projects",
    )
    is_automated: bool = Field(
        default=False,
        description="True if score was derived from automated spatial/statistical data",
    )
    justification: str = Field(
        default="", description="Detailed factual or legal justification for awarded score"
    )

    @field_validator("awarded_points")
    @classmethod
    def validate_points(cls, v: float, info: Any) -> float:
        crit_num = info.data.get("criterion_number")
        if crit_num in CORRIDOR_CRITERIA_MAX_POINTS:
            max_allowed = float(CORRIDOR_CRITERIA_MAX_POINTS[crit_num])
            if v < 0 or v > max_allowed:
                raise ValueError(
                    f"Criterion {crit_num} points ({v}) must be between 0 and {max_allowed}"
                )
        return v


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

    land_evaluation_score: float = Field(
        ge=0.0,
        le=100.0,
        description="Relative Land Evaluation (LE) score derived from SSURGO/NCCPI (0-100)",
    )
    site_assessment: CorridorSiteAssessmentSummary = Field(
        description="Evaluated CPA-106 Site Assessment criteria and summary"
    )
    total_lesa_score: float = Field(
        ge=0.0,
        le=260.0,
        description="Combined total LESA score (LE + SA) on 0-260 point scale",
    )
    threshold_score: int = Field(
        default=LESA_THRESHOLD_SCORE,
        description="Statutory threshold under 7 CFR § 658.4(c)(2) (160 points)",
    )
    threshold_exceeded: bool = Field(
        description="True if total LESA score >= 160, triggering mandatory alternatives evaluation",
    )
    statutory_determination: str = Field(
        description="Statutory recommendation under 7 CFR § 658.4(c)",
    )
    recommended_actions: list[str] = Field(
        default_factory=list,
        description="Required or recommended agency actions based on LESA score",
    )
    regulatory_notice: str = Field(
        default=REGULATORY_NOTICE,
        description="Preliminary screening disclaimer",
    )


# --- Strategy Evaluator Pattern for Corridor Criteria ---


class CriterionEvaluator(ABC):
    """Abstract base strategy evaluator for corridor Site Assessment criteria under 7 CFR § 658.5(c)."""

    def __init__(self, criterion_number: int) -> None:
        self.criterion_number = criterion_number
        self.name = CORRIDOR_CRITERIA_NAMES[criterion_number]
        self.max_points = CORRIDOR_CRITERIA_MAX_POINTS[criterion_number]

    @abstractmethod
    def evaluate(
        self,
        crit_input: dict[str, Any] | None = None,
        project_farm_acres: float | None = None,
        county_average_farm_acres: float | None = None,
    ) -> CriterionEvaluation:
        """Evaluate the criterion and return a CriterionEvaluation instance."""
        ...


class ZeroedCriterionEvaluator(CriterionEvaluator):
    """Evaluator for statutorily zeroed criteria (e.g. Criteria 5 and 6)."""

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
            justification="Statutorily set to 0 points for corridor projects under 7 CFR § 658.5(c).",
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
        else:
            raw_pts = input_data.get("awarded_points", 0.0)
            try:
                awarded = float(raw_pts)
            except (ValueError, TypeError):
                awarded = 0.0

            awarded = max(0.0, min(float(self.max_points), awarded))
            justification = input_data.get("justification", "")
            is_automated = bool(input_data.get("is_automated", False))

            if awarded > 0 and not justification and not is_automated:
                justification = f"Points ({awarded}/{self.max_points}) entered without explicit justification rationale."

        return CriterionEvaluation(
            criterion_number=self.criterion_number,
            name=self.name,
            max_points=self.max_points,
            awarded_points=awarded,
            is_statutorily_zeroed=False,
            is_automated=is_automated,
            justification=justification,
        )


class StandardCriterionEvaluator(CriterionEvaluator):
    """Evaluator for standard or statutory-adjusted criteria (Criteria 1-4, 8-12)."""

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
        is_automated = bool(input_data.get("is_automated", False))

        if awarded > 0 and not justification and not is_automated:
            justification = f"Points ({awarded}/{self.max_points}) entered without explicit justification rationale."

        return CriterionEvaluation(
            criterion_number=self.criterion_number,
            name=self.name,
            max_points=self.max_points,
            awarded_points=awarded,
            is_statutorily_zeroed=False,
            is_automated=is_automated,
            justification=justification,
        )


# Strategy registry mapping criterion numbers 1-12 to evaluators
CRITERION_EVALUATORS: dict[int, CriterionEvaluator] = {
    1: StandardCriterionEvaluator(1),
    2: StandardCriterionEvaluator(2),
    3: StandardCriterionEvaluator(3),
    4: StandardCriterionEvaluator(4),
    5: ZeroedCriterionEvaluator(5),
    6: ZeroedCriterionEvaluator(6),
    7: FarmSizeCriterionEvaluator(7),
    8: StandardCriterionEvaluator(8),
    9: StandardCriterionEvaluator(9),
    10: StandardCriterionEvaluator(10),
    11: StandardCriterionEvaluator(11),
    12: StandardCriterionEvaluator(12),
}


def calculate_criterion_7_score(
    project_farm_acres: float,
    county_average_farm_acres: float,
) -> tuple[float, str]:
    """Calculate Criterion 7 (farm size compared to county average) score under 7 CFR § 658.5(b)(7).

    Statutory scale (Max 10 points):
    - Farm size is > 100% of county average: 10 points
    - Farm size is 50% - 100% of county average: 5 points
    - Farm size is < 50% of county average: 0 points

    Args:
        project_farm_acres: Size of affected agricultural holding/parcel in acres.
        county_average_farm_acres: NASS county average farm size in acres.

    Returns:
        Tuple of (awarded_points, justification_string).
    """
    if county_average_farm_acres <= 0 or project_farm_acres < 0:
        return 0.0, "Invalid or unavailable county average farm size; awarded 0 points."

    ratio = project_farm_acres / county_average_farm_acres
    pct = ratio * 100.0

    if ratio >= 1.0:
        points = 10.0
        desc = f"Affected farm size ({project_farm_acres:.1f} ac) is {pct:.1f}% of county average ({county_average_farm_acres:.1f} ac) (>=100%): 10 points awarded."
    elif ratio >= 0.5:
        points = 5.0
        desc = f"Affected farm size ({project_farm_acres:.1f} ac) is {pct:.1f}% of county average ({county_average_farm_acres:.1f} ac) (50%-99%): 5 points awarded."
    else:
        points = 0.0
        desc = f"Affected farm size ({project_farm_acres:.1f} ac) is {pct:.1f}% of county average ({county_average_farm_acres:.1f} ac) (<50%): 0 points awarded."

    return points, desc


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
    inputs = criteria_inputs or {}
    criteria_list: list[CriterionEvaluation] = []
    total_sa = 0.0
    all_justified = True

    for crit_num in range(1, 13):
        evaluator = CRITERION_EVALUATORS.get(crit_num) or StandardCriterionEvaluator(crit_num)
        crit_input = inputs.get(crit_num)
        eval_item = evaluator.evaluate(
            crit_input=crit_input,
            project_farm_acres=project_farm_acres,
            county_average_farm_acres=county_average_farm_acres,
        )

        if (
            eval_item.awarded_points > 0
            and not eval_item.is_automated
            and (
                not crit_input
                or not crit_input.get("justification")
                or not crit_input.get("justification").strip()
            )
        ):
            all_justified = False

        criteria_list.append(eval_item)
        total_sa += eval_item.awarded_points

    total_sa = min(160.0, round(total_sa, 2))

    return CorridorSiteAssessmentSummary(
        criteria=criteria_list,
        total_sa_points=total_sa,
        max_sa_points=MAX_SITE_ASSESSMENT_SCORE,
        all_criteria_justified=all_justified,
    )


def evaluate_corridor_lesa(
    land_evaluation_score: float,
    site_assessment: CorridorSiteAssessmentSummary,
) -> LESAEvaluationResult:
    """Combine Land Evaluation and Site Assessment into a complete LESA determination.

    Evaluates the 160-point threshold rule (§ 658.4(c)(2)):
    - If Total < 160 points: Site requires no further farmland protection review.
    - If Total >= 160 points: Agency must consider alternatives to avoid farmland conversion,
      alternative designs, and measures to minimize corridor impact (§ 658.4(c)(3)-(4)).

    Args:
        land_evaluation_score: Composite LE score (0-100).
        site_assessment: Evaluated CorridorSiteAssessmentSummary (0-160).

    Returns:
        LESAEvaluationResult with scoring totals, statutory findings, and actions.
    """
    le = max(0.0, min(100.0, round(float(land_evaluation_score), 2)))
    sa = site_assessment.total_sa_points
    total_lesa = round(le + sa, 2)
    threshold_exceeded = total_lesa >= LESA_THRESHOLD_SCORE

    if threshold_exceeded:
        determination = STATUTORY_DETERMINATIONS["THRESHOLD_EXCEEDED"].format(total_lesa=total_lesa)
        actions = [
            "Assess alternative corridor alignments that avoid or minimize conversion of farmland (7 CFR § 658.4(c)(3)).",
            "Evaluate corridor designs with reduced right-of-way widths or alternative construction access to minimize acreage taken (7 CFR § 658.4(c)(4)).",
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
