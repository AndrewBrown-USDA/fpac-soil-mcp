"""LESA scoring and Site Assessment data models."""

from __future__ import annotations

import math
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class CriterionPointInput(BaseModel):
    """Analyst-proposed point input for one Site Assessment criterion."""

    model_config = ConfigDict(extra="forbid")

    awarded_points: float = Field(ge=0, le=160, description="Proposed points for this criterion")
    justification: str = Field(default="", description="Rationale for proposed points")
    is_verified: bool = False
    is_automated: bool = False
    input_authority: str | None = None
    evidence_status: str | None = None
    source_provenance: list[str] = Field(default_factory=list)


class CriterionFactInput(BaseModel):
    """Registry-based evidence input for one Site Assessment criterion."""

    model_config = ConfigDict(extra="forbid")

    value: str | float | None = None
    answer: str | float | None = None
    percentage: float | str | None = None
    distance_miles: float | str | None = None
    category: str | None = None
    is_verified: bool = False
    source_provenance: list[str] = Field(default_factory=list)
    justification: str | None = None

    @model_validator(mode="after")
    def validate_single_value(self) -> CriterionFactInput:
        supplied = [
            field
            for field in ("value", "answer", "percentage", "distance_miles", "category")
            if getattr(self, field) is not None
        ]
        if len(supplied) > 1:
            raise ValueError("Provide only one criterion fact value.")
        return self


class SiteAssessmentInputs(BaseModel):
    """Validated inputs for optional Site Assessment scoring."""

    model_config = ConfigDict(extra="forbid")

    criteria_inputs: dict[int, CriterionPointInput] = Field(default_factory=dict)
    criteria_facts: dict[int, CriterionFactInput] = Field(default_factory=dict)
    project_farm_acres: float | None = Field(default=None, ge=0)
    county_average_farm_acres: float | None = Field(default=None, gt=0)

    @field_validator("criteria_inputs", "criteria_facts")
    @classmethod
    def validate_criterion_numbers(cls, value: dict[int, Any]) -> dict[int, Any]:
        if any(number < 1 or number > 12 for number in value):
            raise ValueError("Site Assessment criterion numbers must be from 1 through 12.")
        return value

    @model_validator(mode="after")
    def reject_conflicting_criteria(self) -> SiteAssessmentInputs:
        overlap = set(self.criteria_inputs) & set(self.criteria_facts)
        if overlap:
            raise ValueError(
                f"Conflicting fact and point override for criterion(s): {sorted(overlap)}."
            )
        return self


class ProductivityIndexType(str, Enum):
    """Supported Soil Productivity Index types for Land Evaluation (LE)."""

    NCCPI = "NCCPI"
    CSR2 = "CSR2"
    CPI = "CPI"
    STORIE = "STORIE"


VALIDATED_PRODUCTIVITY_INDEXES: frozenset[ProductivityIndexType] = frozenset(ProductivityIndexType)
"""All currently validated productivity index types for FPPA guard checks."""

SUPPORTED_INDEX_MSG: str = (
    "Supported fixed selectors: "
    + ", ".join(f"'{v.value.lower()}'" for v in ProductivityIndexType)
    + "."
)
"""Human-readable error message listing all valid productivity index selectors."""


class MapUnitProductivityRating(BaseModel):
    """Productivity rating and normalization metrics for a single soil map unit."""

    mukey: str = Field(description="SSURGO Map Unit Key")
    musym: str | None = Field(default=None, description="Map unit symbol")
    muname: str | None = Field(default=None, description="Map unit name")
    raw_rating: float | None = Field(
        default=None, description="Raw productivity index rating value"
    )
    normalized_relative_rating: float | None = Field(
        default=None,
        description="Normalized relative rating scaled to county maximum (0.0 - 1.0)",
    )
    county_max_rating: float | None = Field(
        default=None,
        description="Maximum productivity index rating benchmark for the county",
    )
    is_rated: bool = Field(
        default=True,
        description="Whether this map unit has an authoritative productivity rating",
    )
    unrated_reason: str | None = Field(
        default=None,
        description="Reason if unrated (e.g. water, urban land, pits, unmapped)",
    )

    @field_validator("normalized_relative_rating")
    @classmethod
    def validate_normalized_rating(cls, v: float | None) -> float | None:
        if v is not None and (v < 0.0 or v > 1.0):
            raise ValueError(f"normalized_relative_rating must be between 0.0 and 1.0, got {v}")
        return v


class LandEvaluationSummary(BaseModel):
    """Summary of Land Evaluation (LE) scoring across an Area of Interest."""

    productivity_index: ProductivityIndexType = Field(
        default=ProductivityIndexType.NCCPI,
        description="Productivity index used for relative scoring",
    )
    aoi_relative_rating: float | None = Field(
        default=0.0,
        description="Area-weighted relative rating across AOI (0.0 - 1.0), or None if unavailable",
    )
    candidate_le_score: float | None = Field(
        default=0.0,
        description="Candidate Land Evaluation score on standard 0-100 point scale, or None if unavailable",
    )
    county_farmland_percentile_higher: float | None = Field(
        default=None,
        description="Percentile ranking of AOI productivity compared to county farmland",
    )
    rated_acreage: float = Field(
        default=0.0,
        description="Total acres with valid productivity ratings",
    )
    unrated_acreage: float = Field(
        default=0.0,
        description="Total acres lacking productivity ratings",
    )
    total_acreage: float = Field(
        default=0.0,
        description="Total evaluated acreage in AOI",
    )
    coverage_percent: float = Field(
        default=0.0,
        description="Percentage of AOI footprint with rated soil productivity",
    )
    coverage_status: Literal["covered", "partial", "unrated", "unmapped", "unknown"] = Field(
        default="unknown",
        description=(
            "Reconciled productivity coverage state: covered, partial, unrated, "
            "unmapped, or unknown (source states are normalized to this vocabulary)"
        ),
    )
    rating_source_provenance: list[str] = Field(
        default_factory=list,
        description="Registry provenance identifiers for the selected productivity rating source",
    )
    reconciliation: dict[str, Any] = Field(
        default_factory=dict,
        description="Acreage reconciliation details and explicit coverage states",
    )
    notices: list[str] = Field(
        default_factory=list,
        description="Land evaluation computation notes and coverage advisories",
    )

    @field_validator("aoi_relative_rating")
    @classmethod
    def validate_aoi_relative_rating(cls, v: float | None) -> float | None:
        if v is None:
            return None
        if v < 0.0 or v > 1.0:
            raise ValueError(f"aoi_relative_rating must be between 0.0 and 1.0, got {v}")
        return v

    @field_validator("candidate_le_score")
    @classmethod
    def validate_candidate_le_score(cls, v: float | None) -> float | None:
        if v is None:
            return None
        if v < 0.0 or v > 100.0:
            raise ValueError(f"candidate_le_score must be between 0.0 and 100.0, got {v}")
        return v

    @field_validator("county_farmland_percentile_higher")
    @classmethod
    def validate_county_percentile(cls, v: float | None) -> float | None:
        if v is not None and (v < 0.0 or v > 100.0):
            raise ValueError(
                f"county_farmland_percentile_higher must be between 0.0 and 100.0, got {v}"
            )
        return v


class SiteAssessmentCriterion(BaseModel):
    """Scoring evaluation for an individual Site Assessment (SA) criterion (Part V / VI)."""

    criterion_number: int = Field(
        description="Criterion number (1 to 12 as defined in 7 CFR 658.5)",
    )
    name: str = Field(description="Name or title of the site assessment criterion")
    max_points: float = Field(description="Maximum allowable points for this criterion")
    awarded_points: float = Field(
        default=0.0,
        description="Points awarded for this site under the criterion evaluation",
    )
    assumed_points: float | None = Field(
        default=None,
        description="Registry-maximum points used only to calculate a conservative upper bound",
    )
    justification: str = Field(
        default="",
        description="Explanation, facts, and statutory basis for awarded points",
    )
    is_automated: bool = Field(
        default=False,
        description="Whether points were derived automatically from spatial / census data",
    )
    is_statutorily_zeroed: bool = Field(
        default=False,
        description="Whether points are zeroed due to corridor/linear project statutory rules",
    )
    normalized_ratio: float | None = Field(
        default=None,
        description="Normalized evidence ratio in the inclusive range 0.0 to 1.0",
    )
    evidence_status: str = Field(
        default="not_provided",
        description="Evidence state: measured, unavailable, or not_provided",
    )
    rule_reference: str | None = Field(
        default=None,
        description="Regulatory or scoring rule reference used for this criterion",
    )
    rule_version: str | None = Field(
        default=None,
        description="Version identifier for the scoring rule",
    )
    source_provenance: list[str] = Field(
        default_factory=list,
        description="Sources supporting the criterion evidence",
    )
    assumption_provenance: str | None = Field(
        default=None,
        description="Policy basis for any conservative points assumed without evidence",
    )
    is_verified: bool = Field(
        default=False,
        description="Whether the evidence and point mapping were verified",
    )
    input_authority: Literal[
        "machine_estimate", "analyst_proposed", "unavailable", "verified", "statutory"
    ] = Field(
        default="unavailable",
        description="Authority/state of the input supporting this criterion",
    )

    @field_validator("criterion_number")
    @classmethod
    def validate_criterion_number(cls, v: int) -> int:
        if v < 1 or v > 12:
            raise ValueError(f"criterion_number must be between 1 and 12, got {v}")
        return v

    @field_validator("max_points")
    @classmethod
    def validate_max_points(cls, v: float) -> float:
        if v < 0.0:
            raise ValueError(f"max_points cannot be negative, got {v}")
        if not math.isfinite(v):
            raise ValueError(f"max_points must be finite, got {v}")
        return v

    @field_validator("awarded_points")
    @classmethod
    def validate_awarded_points(cls, v: float) -> float:
        if v < 0.0:
            raise ValueError(f"awarded_points cannot be negative, got {v}")
        if not math.isfinite(v):
            raise ValueError(f"awarded_points must be finite, got {v}")
        return v

    @field_validator("assumed_points")
    @classmethod
    def validate_assumed_points(cls, v: float | None) -> float | None:
        if v is not None and (v < 0.0 or not math.isfinite(v)):
            raise ValueError(f"assumed_points must be finite and non-negative, got {v}")
        return v

    @field_validator("normalized_ratio")
    @classmethod
    def validate_normalized_ratio(cls, v: float | None) -> float | None:
        if v is not None and (v < 0.0 or v > 1.0):
            raise ValueError(f"normalized_ratio must be between 0.0 and 1.0, got {v}")
        return v

    @model_validator(mode="after")
    def validate_awarded_not_exceed_max(self) -> SiteAssessmentCriterion:
        if self.awarded_points > self.max_points:
            raise ValueError(
                f"awarded_points ({self.awarded_points}) cannot exceed max_points ({self.max_points}) for criterion {self.criterion_number}"
            )
        if self.assumed_points is not None and (
            self.assumed_points < 0.0 or self.assumed_points > self.max_points
        ):
            raise ValueError(
                f"assumed_points ({self.assumed_points}) must be between 0 and max_points "
                f"({self.max_points}) for criterion {self.criterion_number}"
            )
        if self.evidence_status == "assumed (no evidence)":
            if self.assumed_points is None or self.input_authority != "unavailable":
                raise ValueError(
                    "Assumed Site Assessment points require unavailable authority and "
                    "a separate assumed_points value."
                )
            if not self.assumption_provenance:
                raise ValueError("Assumed Site Assessment points require assumption provenance.")
            if self.is_verified or self.is_automated:
                raise ValueError("Assumed Site Assessment points cannot be verified or automated.")
        if self.is_statutorily_zeroed:
            if self.awarded_points != 0:
                raise ValueError("Statutorily zeroed criteria cannot receive points.")
            self.input_authority = "statutory"
            self.is_automated = False
        return self

    @model_validator(mode="after")
    def validate_analyst_rationale(self) -> SiteAssessmentCriterion:
        if self.input_authority == "analyst_proposed" and not self.justification.strip():
            raise ValueError("Analyst-proposed criterion points require a rationale.")
        return self


class SiteAssessmentSummary(BaseModel):
    """Breakdown of Site Assessment (SA) scores across criteria."""

    total_points: float = Field(
        default=0.0,
        description="Total Site Assessment points awarded (0 - 160 point scale)",
    )
    criteria: list[SiteAssessmentCriterion] = Field(
        default_factory=list,
        description="Detailed breakdown of individual site assessment criteria",
    )
    evaluation_status: Literal["complete", "incomplete", "indeterminate"] = Field(
        default="incomplete",
        description="Whether required Site Assessment inputs support evaluation",
    )

    @field_validator("total_points")
    @classmethod
    def validate_total_points(cls, v: float) -> float:
        if v < 0.0 or v > 160.0:
            raise ValueError(f"total_points must be between 0.0 and 160.0, got {v}")
        return v


class PreliminaryLESAResponse(BaseModel):
    """Response schema for preliminary Land Evaluation and Site Assessment (LESA) evaluation."""

    project_name: str = Field(description="Name or identifier of proposed project")
    project_type: Literal["site", "corridor"] = Field(
        default="site",
        description="Project geometry type ('site' for polygon or 'corridor' for linear)",
    )
    land_evaluation: LandEvaluationSummary = Field(
        description="Land Evaluation (LE) score and productivity summary (Part IV/LE max 100)"
    )
    site_assessment: SiteAssessmentSummary = Field(
        description="Site Assessment (SA) criteria breakdown and score (Part V/VI max 160)"
    )
    total_lesa_score: float | None = Field(
        default=0.0,
        description="Total combined LESA score on standard 0-260 point scale (LE + SA), or None if LE unavailable",
    )
    conservative_total_lesa_upper_bound: float | None = Field(
        default=None,
        description=(
            "Conservative upper bound using registry-maximum assumptions for missing Site "
            "Assessment inputs; not an evaluated LESA score or threshold result"
        ),
    )
    mandatory_alternatives_required: bool | None = Field(
        default=False,
        description=(
            "True when the score is 160 or more, indicating the increased-protection "
            "consideration guidance in 7 CFR § 658.4(c)(3)-(4); this does not require selecting "
            "an alternative."
        ),
    )
    threshold_status: Literal["evaluated", "not_evaluated"] = Field(
        default="evaluated",
        description="Whether the statutory threshold was evaluated",
    )
    regulatory_notice: str = Field(
        description="Official regulatory disclaimer regarding FPPA screening and LESA"
    )
    limitations: list[str] = Field(
        default_factory=list,
        description="Regulatory and technical limitations of preliminary scoring",
    )

    @field_validator("total_lesa_score")
    @classmethod
    def validate_total_lesa_score(cls, v: float | None) -> float | None:
        if v is None:
            return None
        if v < 0.0 or v > 260.0:
            raise ValueError(f"total_lesa_score must be between 0.0 and 260.0, got {v}")
        return v

    @field_validator("conservative_total_lesa_upper_bound")
    @classmethod
    def validate_conservative_total_lesa_upper_bound(cls, v: float | None) -> float | None:
        if v is not None and (not math.isfinite(v) or v < 0.0 or v > 260.0):
            raise ValueError("conservative_total_lesa_upper_bound must be between 0.0 and 260.0")
        return v

    @model_validator(mode="after")
    def validate_mandatory_alternatives_required(self) -> PreliminaryLESAResponse:
        if (
            self.threshold_status == "not_evaluated"
            and self.mandatory_alternatives_required is not None
        ):
            raise ValueError(
                "mandatory_alternatives_required must be None when threshold_status is not_evaluated"
            )
        if self.total_lesa_score is None:
            if self.mandatory_alternatives_required is not None:
                raise ValueError(
                    "mandatory_alternatives_required must be None when total_lesa_score is unavailable"
                )
            return self
        expected = self.total_lesa_score >= 160.0
        if self.mandatory_alternatives_required != expected:
            raise ValueError(
                "mandatory_alternatives_required must equal "
                f"(total_lesa_score >= 160.0), expected {expected}"
            )
        return self
