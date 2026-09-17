"""Pydantic models and response schemas for FPAC Soil MCP.

Defines data models for Soil Map Units, Query Sources, Farmland Classification responses,
FPPA Scope responses, and Farmland Class listings.
"""

from typing import Any

from pydantic import BaseModel, Field


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
    nccpi_rating: float | None = Field(
        default=None, description="Weighted NCCPI v3 rating (0.0 - 1.0)"
    )
    nccpi_class: str | None = Field(default=None, description="Qualitative rating class")


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
