"""Pydantic models and response schemas for FPAC Soil MCP.

Defines data models for Soil Map Units, Query Sources, Farmland Classification responses,
FPPA Scope responses, and Farmland Class listings.
"""

from __future__ import annotations

import math
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from fpac_soil_mcp.map_contract import MAP_SCHEMA_VERSION, MapBlock, ResultAuthority


class SoilMapUnit(BaseModel):
    """SSURGO Soil Map Unit data structure."""

    mukey: str = Field(description="Map Unit Key (unique identifier in SSURGO)")
    musym: str | None = Field(default=None, description="Map unit symbol")
    muname: str | None = Field(default=None, description="Map unit name")
    farmlndcl: str | None = Field(
        default=None, description="Farmland classification string from SSURGO"
    )
    areasymbol: str | None = Field(default=None, description="Soil survey area symbol")


class QuerySource(BaseModel):
    """Metadata describing the data source and query context."""

    service_name: str = Field(
        default="USDA NRCS Soil Data Access (SDA)",
        description="Name of the soil data service",
    )
    endpoint: str = Field(
        default="https://sdmdataaccess.nrcs.usda.gov/Tabular/post.rest",
        description="REST endpoint URL queried",
    )
    timestamp_utc: str = Field(description="ISO 8601 UTC timestamp of query execution")
    documentation_urls: list[str] = Field(
        default_factory=lambda: [
            "https://sdmdataaccess.nrcs.usda.gov/",
            "https://websoilsurvey.sc.egov.usda.gov/",
        ],
        description="Official documentation URLs",
    )


class FarmlandClassificationResponse(BaseModel):
    """Response schema for farmland classification queries (point or mukey)."""

    query_type: str = Field(description="Query type performed, e.g. 'point' or 'mukey'")
    input_query: dict[str, Any] = Field(description="Parameters passed to the query")
    coverage_status: str = Field(
        description="Data coverage status: 'covered', 'no_data', or 'unmapped'"
    )
    map_units: list[SoilMapUnit] = Field(
        default_factory=list, description="Soil map units identified in the query area"
    )
    source: QuerySource = Field(description="Query source metadata")
    limitations: list[str] = Field(
        default_factory=list, description="Regulatory and technical limitations"
    )
    regulatory_notice: str = Field(
        description="Official regulatory disclaimer regarding FPPA screening"
    )


class FppaScopeResponse(BaseModel):
    """Response schema explaining FPPA screening vs full determination."""

    title: str = Field(description="Scope document title")
    summary: str = Field(description="Executive summary of FPPA screening vs LESA")
    sda_screening_scope: dict[str, Any] = Field(
        description="Details on what SDA preliminary screening provides"
    )
    lesa_determination_scope: dict[str, Any] = Field(
        description="Details on full LESA determination and Form AD-1006 requirements"
    )
    regulatory_notice: str = Field(description="Official regulatory notice")
    limitations: list[str] = Field(default_factory=list, description="Regulatory limitations")
    citations: dict[str, str] = Field(
        default_factory=dict, description="Legal and regulatory citations"
    )


class FarmlandClassItem(BaseModel):
    """Detailed definition of a single farmland classification category."""

    description: str = Field(description="Description of the farmland classification category")
    fppa_status: str = Field(description="Status under 7 CFR Part 657 / FPPA")
    regulatory_category: str = Field(description="Regulatory category designation")


class FarmlandClassListResponse(BaseModel):
    """Response schema for listing standard SSURGO farmland classifications."""

    source: str = Field(description="Source of farmland classification definitions")
    authority: str = Field(description="Authoritative regulatory/handbook citation")
    classes: dict[str, dict[str, str]] = Field(
        description="Dictionary mapping farmland class names to their details"
    )


class SoilMapUnitAcreage(BaseModel):
    """Acreage and interpretation metrics for a specific soil map unit in an AOI."""

    mukey: str = Field(description="SSURGO Map Unit Key")
    musym: str | None = Field(default=None, description="Map unit symbol")
    muname: str | None = Field(default=None, description="Map unit name")
    farmlndcl: str | None = Field(default=None, description="SSURGO farmland classification")
    areasymbol: str | None = Field(default=None, description="Soil survey area symbol")
    calculated_acres: float = Field(default=0.0, description="Estimated acres of this map unit")
    percentage_of_aoi: float = Field(default=0.0, description="Percentage of total AOI footprint")
    productivity_rating: float | None = Field(
        default=None, description="Weighted productivity rating for the selected interpretation"
    )
    productivity_rating_class: str | None = Field(
        default=None, description="Qualitative class for the selected productivity interpretation"
    )
    productivity_rating_source: str | None = Field(
        default=None,
        description="SDA interpretation rule or catalog provenance used for the productivity rating",
    )
    productivity_coverage_status: str = Field(
        default="unknown",
        description="Selected productivity interpretation coverage status within this map unit",
    )
    productivity_rated_pct: float | None = Field(
        default=None,
        description="Percent of map-unit component area supporting the selected productivity rating",
    )
    productivity_total_pct: float | None = Field(
        default=None,
        description="Percent of map-unit component area included in the coverage calculation",
    )
    productivity_coverage_caveats: list[str] = Field(
        default_factory=list,
        description="Selected productivity interpretation coverage caveats for this map unit",
    )


class FarmlandCategoryBreakdown(BaseModel):
    """Acreage summary grouped by statutory FPPA / SSURGO farmland category."""

    prime_farmland_acres: float = Field(
        default=0.0, description="Acres of all areas prime farmland"
    )
    prime_farmland_pct: float = Field(default=0.0, description="Percentage prime farmland")
    conditional_prime_acres: float = Field(
        default=0.0, description="Acres of prime farmland if drained/protected/irrigated"
    )
    conditional_prime_pct: float = Field(default=0.0, description="Percentage conditional prime")
    statewide_importance_acres: float = Field(
        default=0.0, description="Acres of farmland of statewide importance"
    )
    statewide_importance_pct: float = Field(
        default=0.0, description="Percentage statewide importance"
    )
    local_importance_acres: float = Field(
        default=0.0, description="Acres of farmland of local importance"
    )
    local_importance_pct: float = Field(default=0.0, description="Percentage local importance")
    unique_farmland_acres: float = Field(default=0.0, description="Acres of unique farmland")
    unique_farmland_pct: float = Field(default=0.0, description="Percentage unique farmland")
    not_prime_acres: float = Field(default=0.0, description="Acres of not prime farmland")
    not_prime_pct: float = Field(default=0.0, description="Percentage not prime")
    unmapped_acres: float = Field(default=0.0, description="Acres of unmapped / water area")
    unmapped_pct: float = Field(default=0.0, description="Percentage unmapped")
    total_fppa_protected_acres: float = Field(
        default=0.0,
        description="Total acres subject to FPPA review (prime + conditional + statewide + local + unique)",
    )
    total_fppa_protected_pct: float = Field(
        default=0.0, description="Total percentage of AOI subject to FPPA review"
    )


class PolygonFarmlandAnalysisResponse(BaseModel):
    """Complete response schema for polygon AOI screening and farmland analysis."""

    query_type: str = Field(default="polygon", description="Query type performed")
    geometry_hash: str = Field(description="Deterministic SHA-256 hash of the screened geometry")
    total_aoi_acres: float = Field(description="Total geodesic surface area of the AOI in acres")
    coverage_status: str = Field(
        description="Coverage status: 'covered', 'partially_covered', or 'unmapped'"
    )
    urban_screening: dict[str, Any] = Field(
        description="Census 2020 Urban Area preliminary screening result"
    )
    farmland_summary: FarmlandCategoryBreakdown = Field(
        description="Acreage summary by farmland classification category"
    )
    map_units: list[SoilMapUnitAcreage] = Field(
        default_factory=list, description="List of intersecting soil map units with acreage"
    )
    tabular_csv: str = Field(description="CSV-formatted table of soil map units and acreage")
    manifest: dict[str, Any] = Field(
        default_factory=dict,
        description="Execution manifest, geometry hash, and runtime parameters",
    )
    source: QuerySource = Field(description="Query source metadata")
    limitations: list[str] = Field(
        default_factory=list, description="Regulatory and technical limitations"
    )
    regulatory_notice: str = Field(
        description="Official regulatory disclaimer regarding FPPA screening"
    )
    schema_version: str = Field(
        default=MAP_SCHEMA_VERSION, description="Map result contract version (ADR 0017)"
    )
    data_mode: Literal["live"] = Field(
        default="live", description="Data mode: live upstream services"
    )
    authority: ResultAuthority = Field(
        default_factory=ResultAuthority,
        description="Result authority: preliminary machine estimate, not an official filing",
    )
    map: MapBlock = Field(
        default_factory=MapBlock,
        description="Map layers; geometry only when include_map is true (ADR 0017)",
    )


class CorridorImpactBreakdown(BaseModel):
    """Acreage breakdown for direct right-of-way and indirect staging areas."""

    direct_acres: float = Field(default=0.0, description="Direct right-of-way footprint in acres")
    indirect_acres: float = Field(
        default=0.0,
        description="Indirect staging/access footprint in acres (erased of direct overlap)",
    )
    total_project_acres: float = Field(
        default=0.0, description="Total project footprint (direct + indirect) in acres"
    )


class CorridorCountySegment(BaseModel):
    """Analysis summary for a single county partition along a multi-county corridor."""

    state_fips: str = Field(description="2-digit State FIPS code")
    county_fips: str = Field(description="3-digit County FIPS code")
    county_name: str = Field(description="County name")
    state_name: str | None = Field(default=None, description="State name or abbreviation")
    direct_acres: float = Field(default=0.0, description="Direct corridor acreage in this county")
    indirect_acres: float = Field(
        default=0.0, description="Indirect staging acreage in this county"
    )
    total_segment_acres: float = Field(
        default=0.0, description="Total project acreage in this county"
    )
    segment_weight_pct: float = Field(
        default=0.0, description="Segment acreage as percentage of total corridor footprint"
    )
    coverage_status: str = Field(
        default="covered",
        description="Soil coverage status: 'covered', 'partially_covered', or 'unmapped'",
    )
    productivity_coverage_status: str = Field(
        default="unknown",
        description="Selected productivity rating coverage, independent of mapped-soil coverage",
    )
    component_rated_acres: float = Field(
        default=0.0,
        description="Map-unit acreage weighted by the share of components supporting the rating",
    )
    component_coverage_percent: float = Field(
        default=0.0,
        description="Percent of the county segment with rated productivity-component coverage",
    )
    productivity_coverage_caveats: list[str] = Field(
        default_factory=list,
        description="Selected productivity rating coverage caveats for this county segment",
    )
    urban_screening: dict[str, Any] = Field(
        default_factory=dict,
        description="Census 2020 Urban Area screening result for this segment",
    )
    farmland_summary: FarmlandCategoryBreakdown = Field(
        default_factory=FarmlandCategoryBreakdown,
        description="Farmland classification acreage breakdown within this county segment",
    )
    map_units: list[SoilMapUnitAcreage] = Field(
        default_factory=list,
        description="Soil map units intersecting this county segment",
    )
    nass_profile: dict[str, Any] = Field(
        default_factory=dict,
        description="USDA NASS Census of Agriculture profile for this county",
    )
    relative_rating_le: float | None = Field(
        default=None,
        description="Weighted relative Land Evaluation (LE) score (0-100) for this county segment",
    )


class CorridorAlternativeComparison(BaseModel):
    """Side-by-side comparison summary for an alternative corridor alignment."""

    alternative_id: str = Field(description="Identifier or name for alternative alignment")
    geometry_hash: str = Field(description="Deterministic hash of alternative geometry")
    total_project_acres: float = Field(
        default=0.0, description="Total project acres for this alternative"
    )
    direct_acres: float = Field(default=0.0, description="Direct right-of-way acres")
    indirect_acres: float = Field(default=0.0, description="Indirect staging acres")
    total_fppa_protected_acres: float = Field(
        default=0.0, description="Total FPPA protected farmland acres"
    )
    total_fppa_protected_pct: float = Field(
        default=0.0, description="Percentage of alternative footprint in protected farmland"
    )
    prime_farmland_acres: float = Field(
        default=0.0, description="Acres of all areas prime farmland in this alternative"
    )
    conditional_prime_acres: float = Field(
        default=0.0,
        description="Acres of prime farmland if drained/protected/irrigated in this alternative",
    )
    statewide_importance_acres: float = Field(
        default=0.0, description="Acres of farmland of statewide importance in this alternative"
    )
    local_importance_acres: float = Field(
        default=0.0, description="Acres of farmland of local importance in this alternative"
    )
    unique_farmland_acres: float = Field(
        default=0.0, description="Acres of unique farmland in this alternative"
    )
    not_prime_acres: float = Field(
        default=0.0, description="Acres of not prime farmland in this alternative"
    )
    not_prime_pct: float = Field(
        default=0.0, description="Percentage of alternative footprint in not prime farmland"
    )
    unmapped_acres: float = Field(
        default=0.0, description="Acres of unmapped / water area in this alternative"
    )
    composite_relative_rating: float | None = Field(
        default=None,
        description="Area-weighted composite Land Evaluation score across all counties (0-100)",
    )
    counties_traversed: list[str] = Field(
        default_factory=list, description="List of counties traversed by this alternative"
    )


class CorridorFarmlandAnalysisResponse(BaseModel):
    """Complete response schema for multi-county corridor screening and farmland analysis."""

    query_type: str = Field(default="corridor", description="Query type performed")
    geometry_hash: str = Field(description="Deterministic SHA-256 hash of direct centerline")
    buffer_distance: float = Field(description="Corridor buffer distance applied")
    buffer_units: str = Field(description="Corridor buffer distance units (feet, meters, miles)")
    impact_breakdown: CorridorImpactBreakdown = Field(
        description="Direct, indirect, and total project acreage breakdown"
    )
    composite_relative_rating: float | None = Field(
        default=None,
        description="Reconciled area-weighted composite LE rating across all county segments (0-100)",
    )
    county_segments: list[CorridorCountySegment] = Field(
        default_factory=list,
        description="Partitioned corridor segment analyses for each traversed county",
    )
    reconciliation_summary: dict[str, Any] = Field(
        default_factory=dict,
        description="Mathematical sum reconciliation audit across county partitions",
    )
    alternatives: list[CorridorAlternativeComparison] = Field(
        default_factory=list,
        description="Side-by-side comparison of alternative corridor alignments (if provided)",
    )
    tabular_csv: str = Field(
        default="",
        description="CSV-formatted summary table of county segments and farmland categories",
    )
    manifest: dict[str, Any] = Field(
        default_factory=dict,
        description="Execution manifest, hashes, runtime parameters, and service versions",
    )
    source: QuerySource = Field(description="Query source metadata")
    limitations: list[str] = Field(
        default_factory=list, description="Regulatory and technical limitations"
    )
    regulatory_notice: str = Field(
        description="Official regulatory disclaimer regarding FPPA screening"
    )
    schema_version: str = Field(
        default=MAP_SCHEMA_VERSION, description="Map result contract version (ADR 0017)"
    )
    data_mode: Literal["live"] = Field(
        default="live", description="Data mode: live upstream services"
    )
    authority: ResultAuthority = Field(
        default_factory=ResultAuthority,
        description="Result authority: preliminary machine estimate, not an official filing",
    )
    map: MapBlock = Field(
        default_factory=MapBlock,
        description="Map layers; geometry only when include_map is true (ADR 0017)",
    )


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
