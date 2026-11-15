"""Spatial and linear corridor analysis response and input models."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from fpac_soil_mcp.models.map import MAP_SCHEMA_VERSION, MapBlock, ResultAuthority
from fpac_soil_mcp.models.soil import (
    FarmlandCategoryBreakdown,
    QuerySource,
    SoilMapUnitAcreage,
)


class CorridorAlternativeInput(BaseModel):
    """Validated alternative centerline accepted by corridor screening."""

    model_config = ConfigDict(extra="forbid")

    alternative_id: str = Field(min_length=1, max_length=100)
    centerline: dict[str, Any] | str
    buffer_distance: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    buffer_units: Literal["feet", "meters", "miles"] | None = None


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
