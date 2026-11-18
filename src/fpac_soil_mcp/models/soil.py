"""Soil map units and farmland classification data models."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from fpac_soil_mcp.models.coverage import RatingCoverage, SoilMappingCoverage


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


class ToolError(BaseModel):
    """Source-aware description of an expected public tool failure."""

    code: Literal["validation_error", "upstream_error"]
    message: str
    source: str


class FarmlandClassificationResponse(BaseModel):
    """Response schema for farmland classification queries (point or mukey)."""

    query_type: str = Field(description="Query type performed, e.g. 'point' or 'mukey'")
    input_query: dict[str, Any] = Field(description="Parameters passed to the query")
    coverage_status: SoilMappingCoverage = Field(
        description=(
            "Soil mapping coverage: covered, partial, unmapped, or error (query failed); "
            "see fpac_soil_mcp.models.coverage"
        )
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
    error: ToolError | None = Field(
        default=None,
        description="Structured source-aware error details when the query fails",
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
    productivity_coverage_status: RatingCoverage = Field(
        default="unknown",
        description=(
            "Selected productivity rating coverage within this map unit: rated, partial, "
            "unrated, unmapped, unknown, or error (query failed); "
            "see fpac_soil_mcp.models.coverage"
        ),
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
    nccpi_baseline_rating: float | None = Field(
        default=None,
        description=(
            "Weighted-average NCCPI v3 rating (0-1), always included as national baseline "
            "context and never used for Land Evaluation scoring; null when unrated or not populated"
        ),
    )
    nccpi_baseline_rating_class: str | None = Field(
        default=None,
        description="NCCPI v3 rating class for the national baseline; null when unrated",
    )
    nccpi_baseline_rating_source: str | None = Field(
        default=None,
        description="SDA interpretation rule or catalog provenance of the NCCPI national baseline",
    )
    nccpi_baseline_coverage_status: RatingCoverage | None = Field(
        default=None,
        description=(
            "NCCPI baseline rating coverage: rated, partial, unrated, or error (query "
            "failed); null when SDA returned no NCCPI row for this map unit; "
            "see fpac_soil_mcp.models.coverage"
        ),
    )
    nccpi_baseline_rated_pct: float | None = Field(
        default=None,
        description="Percent of map-unit component area with an NCCPI rating, as returned by SDA",
    )
    nccpi_baseline_total_pct: float | None = Field(
        default=None,
        description="Percent of map-unit component area in the NCCPI coverage calculation",
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
