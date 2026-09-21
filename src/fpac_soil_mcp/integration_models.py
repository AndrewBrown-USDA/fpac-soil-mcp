"""Provenance-bearing integration domain models for external public data services.

Defines UrbanExemptionRecord (Census TIGERweb), CountyAgProfile (USDA NASS),
SoilInterpretationRecord (USDA NRCS SDA), and CountyPartitionGeometry (Census TIGERweb).
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from fpac_soil_mcp.authority import Provenance, _validate_non_empty_str


class IntegrationStatus(str, Enum):
    """Execution status of an external data retrieval or integration."""

    SUCCESS = "success"
    UNAVAILABLE = "unavailable"
    ERROR = "error"


class CountyIdentifier(BaseModel):
    """Validated identifier and display metadata for a county."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    state_fips: str = Field(description="2-digit state FIPS code")
    county_fips: str = Field(description="3-digit county FIPS code")
    county_name: str = Field(description="County or parish name")
    state_name: str | None = Field(default=None, description="Optional state name")
    state_alpha: str | None = Field(default=None, description="Optional state abbreviation")

    @field_validator("state_fips")
    @classmethod
    def _validate_state_fips(cls, value: str) -> str:
        if len(value) != 2 or not value.isdigit():
            raise ValueError("state_fips must be a two-digit numeric FIPS code.")
        return value

    @field_validator("county_fips")
    @classmethod
    def _validate_county_fips(cls, value: str) -> str:
        if len(value) != 3 or not value.isdigit():
            raise ValueError("county_fips must be a three-digit numeric FIPS code.")
        return value

    @field_validator("county_name")
    @classmethod
    def _validate_county_name(cls, value: str) -> str:
        return _validate_non_empty_str(value, "county_name")

    @property
    def full_fips(self) -> str:
        return f"{self.state_fips}{self.county_fips}"


class UrbanExemptionRecord(BaseModel):
    """Screening result against Census TIGERweb Urban Areas (7 CFR 658.2(a)).

    This record represents preliminary screening only and does NOT constitute
    an official or binding legal exemption determination.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    status: IntegrationStatus = Field(description="Integration outcome status")
    geometry_hash: str = Field(description="Deterministic hash of the screened project geometry")
    provenance: Provenance = Field(description="Authoritative source provenance (Census TIGERweb)")
    source_layer: str | None = Field(
        default="Urban Areas 2020 (Layer 0)",
        description="Name or identifier of urban boundary layer",
    )
    layer_version: str | None = Field(default="2020", description="Census urban layer vintage")
    is_urban_intersected: bool | None = Field(
        default=None, description="Whether footprint intersects urbanized area boundaries"
    )
    urban_area_names: list[str] = Field(
        default_factory=list, description="Intersected Census urban area names"
    )
    screened_acreage: float | None = Field(
        default=None, description="Optional calculated acreage within urban boundary"
    )
    limitations: list[str] = Field(
        default_factory=lambda: [
            "Preliminary automated screening only under 7 CFR 658.2(a).",
            "Does not constitute an official agency determination or NRCS exemption finding.",
            "Local zoning, commit-to-urban development status, and field conditions must be verified.",
        ],
        description="Statutory and technical limitations",
    )
    error_message: str | None = Field(default=None, description="Error details if status is error")

    @field_validator("geometry_hash")
    @classmethod
    def _validate_hash(cls, v: str) -> str:
        return _validate_non_empty_str(v, "geometry_hash")

    @field_validator("screened_acreage")
    @classmethod
    def _validate_acreage(cls, v: float | None) -> float | None:
        if v is not None and v < 0:
            raise ValueError("screened_acreage must be non-negative.")
        return v

    @model_validator(mode="after")
    def _validate_status_fields(self) -> "UrbanExemptionRecord":
        if self.status == IntegrationStatus.SUCCESS:
            if self.is_urban_intersected is None:
                raise ValueError("is_urban_intersected must be set when status is 'success'.")
        elif self.status == IntegrationStatus.ERROR and not self.error_message:
            raise ValueError("error_message must be provided when status is 'error'.")
        return self


class CountyAgProfile(BaseModel):
    """County-level agricultural baseline data from USDA NASS Quick Stats."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    status: IntegrationStatus = Field(description="Integration outcome status")
    state_fips: str = Field(description="2-digit state FIPS code")
    county_fips: str = Field(description="3-digit county FIPS code")
    county_name: str = Field(description="County or parish name")
    census_year: int = Field(description="Census of Agriculture year (e.g. 2017, 2022)")
    provenance: Provenance = Field(description="Authoritative source provenance (USDA NASS)")
    land_in_farms_acres: float | None = Field(
        default=None, description="Total land in farms (acres) in county"
    )
    total_cropland_acres: float | None = Field(
        default=None, description="Total cropland (acres) in county"
    )
    farm_count: int | None = Field(
        default=None, description="Total number of operations/farms in county"
    )
    average_farm_size_acres: float | None = Field(
        default=None, description="Average farm size in acres"
    )
    unavailable_fields: list[str] = Field(
        default_factory=list, description="Fields withheld or not disclosed (e.g. (D))"
    )
    error_message: str | None = Field(default=None, description="Error details if status is error")

    @field_validator("state_fips", "county_fips", "county_name")
    @classmethod
    def _validate_strings(cls, v: str, info) -> str:
        return _validate_non_empty_str(v, info.field_name or "field")

    @field_validator("land_in_farms_acres", "total_cropland_acres", "average_farm_size_acres")
    @classmethod
    def _validate_acres(cls, v: float | None) -> float | None:
        if v is not None and v < 0:
            raise ValueError("Acreage values must be non-negative.")
        return v

    @field_validator("farm_count")
    @classmethod
    def _validate_count(cls, v: int | None) -> int | None:
        if v is not None and v < 0:
            raise ValueError("farm_count must be non-negative.")
        return v

    @field_validator("census_year")
    @classmethod
    def _validate_year(cls, v: int) -> int:
        if v < 1900 or v > 2100:
            raise ValueError(f"census_year '{v}' is outside valid historical range.")
        return v

    @model_validator(mode="after")
    def _validate_status_fields(self) -> "CountyAgProfile":
        if self.status == IntegrationStatus.ERROR and not self.error_message:
            raise ValueError("error_message must be provided when status is 'error'.")
        return self


class SoilInterpretationRecord(BaseModel):
    """SSURGO Soil Interpretation or NCCPI rating from USDA NRCS SDA."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    status: IntegrationStatus = Field(description="Integration outcome status")
    mukey: str = Field(description="SSURGO Map Unit Key")
    rule_name: str = Field(
        description="Name of interpretation rule, e.g. NCCPI - National Commodity Crop Productivity Index (Ver 3.0)"
    )
    rule_version: str = Field(description="Version of interpretation rule")
    provenance: Provenance = Field(description="Authoritative source provenance (USDA NRCS SDA)")
    aggregation_method: str | None = Field(
        default=None,
        description="Component aggregation method (e.g. 'Dominant Component', 'Weighted Average')",
    )
    rating_class: str | None = Field(
        default=None,
        description="Qualitative rating class, e.g. 'Not prime farmland', 'Prime farmland'",
    )
    numeric_rating: float | None = Field(
        default=None, description="Normalized rating score between 0.0 and 1.0"
    )
    rated_component_pct: float | None = Field(
        default=None, description="Percentage of mapunit components rated (0-100)"
    )
    total_component_pct: float | None = Field(
        default=None, description="Total percentage of mapunit components present (0-100)"
    )
    limiting_reasons: list[str] = Field(
        default_factory=list, description="Specific soil properties or limiting factors"
    )
    error_message: str | None = Field(default=None, description="Error details if status is error")

    @field_validator("mukey", "rule_name", "rule_version")
    @classmethod
    def _validate_strings(cls, v: str, info) -> str:
        return _validate_non_empty_str(v, info.field_name or "field")

    @field_validator("numeric_rating")
    @classmethod
    def _validate_numeric_rating(cls, v: float | None) -> float | None:
        if v is not None and not (0.0 <= v <= 1.0):
            raise ValueError(f"numeric_rating '{v}' must be between 0.0 and 1.0.")
        return v

    @field_validator("rated_component_pct", "total_component_pct")
    @classmethod
    def _validate_percentages(cls, v: float | None, info) -> float | None:
        if v is not None and not (0.0 <= v <= 100.0):
            raise ValueError(f"'{info.field_name}' must be between 0.0 and 100.0 percent.")
        return v

    @model_validator(mode="after")
    def _validate_status_fields(self) -> "SoilInterpretationRecord":
        if self.status == IntegrationStatus.SUCCESS:
            if self.rating_class is None and self.numeric_rating is None:
                raise ValueError(
                    "At least one of rating_class or numeric_rating must be present on success."
                )
        elif self.status == IntegrationStatus.ERROR and not self.error_message:
            raise ValueError("error_message must be provided when status is 'error'.")
        return self


class CountyPartitionGeometry(BaseModel):
    """Spatially partitioned geometry segment intersecting a specific county.

    Represents an intersection segment of a project footprint or corridor
    aligned within a single county boundary for multi-county LESA analysis.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    state_fips: str = Field(description="2-digit state FIPS code")
    county_fips: str = Field(description="3-digit county FIPS code")
    county_name: str = Field(description="County or parish name")
    state_name: str | None = Field(default=None, description="Optional state name")
    geometry: Any = Field(
        description="Shapely geometry (Polygon or MultiPolygon) or GeoJSON structure"
    )
    calculated_acres: float = Field(description="Geodesic calculated acreage of this segment")

    @field_validator("state_fips", "county_fips", "county_name")
    @classmethod
    def _validate_strings(cls, v: str, info) -> str:
        return _validate_non_empty_str(v, info.field_name or "field")

    @field_validator("calculated_acres")
    @classmethod
    def _validate_acres(cls, v: float) -> float:
        if v < 0:
            raise ValueError("calculated_acres must be non-negative.")
        return v

    @field_validator("geometry")
    @classmethod
    def _validate_geometry(cls, v: Any) -> Any:
        if v is None:
            raise ValueError("geometry must be provided.")
        return v

    def __getitem__(self, item: str) -> Any:
        """Allow dictionary-style key access for backward compatibility."""
        if hasattr(self, item):
            return getattr(self, item)
        raise KeyError(f"'{item}' is not a valid field on CountyPartitionGeometry")

    def get(self, item: str, default: Any = None) -> Any:
        """Allow dictionary-style .get() access for backward compatibility."""
        if hasattr(self, item):
            val = getattr(self, item)
            return val if val is not None else default
        return default
