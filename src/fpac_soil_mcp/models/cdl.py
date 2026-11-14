"""Evidence models for USDA NASS Cropland Data Layer screening."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from fpac_soil_mcp.core.authority import Provenance, _validate_non_empty_str


class CDLAnalysisStatus(str, Enum):
    """Outcome status for a CDL ImageServer analysis."""

    SUCCESS = "success"
    UNAVAILABLE = "unavailable"
    INVALID = "invalid"
    AMBIGUOUS = "ambiguous"
    ERROR = "error"


class CDLHistogramBin(BaseModel):
    """Pixel count for one categorical CDL class value."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    class_value: int = Field(description="Raw categorical CDL class value")
    pixel_count: int = Field(description="Number of AOI pixels assigned to the class")
    class_name: str | None = Field(default=None, description="Optional CDL class label")
    is_qualifying_agricultural: bool = Field(
        default=False,
        description="Whether the configured evidence policy treats this class as agricultural",
    )

    @field_validator("class_value")
    @classmethod
    def _validate_class_value(cls, value: int) -> int:
        if value < 0:
            raise ValueError("class_value must be non-negative.")
        return value

    @field_validator("pixel_count")
    @classmethod
    def _validate_pixel_count(cls, value: int) -> int:
        if value < 0:
            raise ValueError("pixel_count must be non-negative.")
        return value

    @field_validator("class_name")
    @classmethod
    def _validate_class_name(cls, value: str | None) -> str | None:
        return None if value is None else _validate_non_empty_str(value, "class_name")


class CDLServiceMetadata(BaseModel):
    """Validated metadata used to interpret one ImageServer request."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    endpoint: str = Field(description="NASS CDL ImageServer endpoint")
    capabilities: list[str] = Field(default_factory=list)
    spatial_reference: str | None = None
    pixel_type: str | None = None
    band_count: int | None = Field(default=None, ge=1)
    pixel_size_x: float | None = Field(default=None, gt=0)
    pixel_size_y: float | None = Field(default=None, gt=0)
    full_extent: dict[str, float] | None = None
    object_id_field: str | None = None
    time_field: str | None = None
    retrieved_at_utc: datetime = Field(description="Metadata retrieval timestamp")
    response_hash: str = Field(description="SHA-256 hash of the metadata response")

    @field_validator("endpoint", "response_hash")
    @classmethod
    def _validate_strings(cls, value: str, info) -> str:
        return _validate_non_empty_str(value, info.field_name or "field")

    @field_validator("retrieved_at_utc")
    @classmethod
    def _validate_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            raise ValueError("retrieved_at_utc must be timezone-aware.")
        return value


class CDLHistogramResponse(BaseModel):
    """Preliminary mapped land-cover evidence for a polygon AOI."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    status: CDLAnalysisStatus = Field(description="Analysis outcome status")
    geometry_hash: str = Field(description="Deterministic hash of the AOI geometry")
    histogram: list[CDLHistogramBin] = Field(default_factory=list)
    total_pixel_count: int | None = Field(default=None, ge=0)
    nodata_pixel_count: int | None = Field(default=None, ge=0)
    coverage_pct: float | None = Field(default=None, ge=0, le=100)
    product_vintage: str | None = Field(default=None)
    vintage_verified: bool = Field(
        default=False,
        description="Whether the requested product vintage was matched to one catalog raster",
    )
    coverage_verified: bool = Field(
        default=False,
        description="Whether complete AOI coverage was established from service extent metadata",
    )
    qualifying_agricultural_pixel_pct: float | None = Field(default=None, ge=0, le=100)
    service_metadata: CDLServiceMetadata | None = None
    provenance: Provenance | None = None
    error_message: str | None = None
    limitations: list[str] = Field(
        default_factory=lambda: [
            "Recent mapped agricultural land-cover evidence from USDA NASS CDL only.",
            "CDL does not establish active farming, ownership, legal agricultural status, or FPPA farmland status.",
            "This result does not constitute an official FPPA or LESA determination.",
        ]
    )

    @field_validator("geometry_hash")
    @classmethod
    def _validate_geometry_hash(cls, value: str) -> str:
        return _validate_non_empty_str(value, "geometry_hash")

    @field_validator("product_vintage", "error_message")
    @classmethod
    def _validate_optional_strings(cls, value: str | None, info) -> str | None:
        return None if value is None else _validate_non_empty_str(value, info.field_name or "field")

    @model_validator(mode="after")
    def _validate_status_fields(self) -> CDLHistogramResponse:
        if self.status == CDLAnalysisStatus.SUCCESS:
            if self.provenance is None:
                raise ValueError("provenance is required when status is 'success'.")
            if self.total_pixel_count is None or self.coverage_pct is None:
                raise ValueError(
                    "total_pixel_count and coverage_pct are required when status is 'success'."
                )
            if not self.vintage_verified or not self.coverage_verified:
                raise ValueError(
                    "vintage_verified and coverage_verified are required when status is 'success'."
                )
        elif (
            self.status
            in {
                CDLAnalysisStatus.INVALID,
                CDLAnalysisStatus.AMBIGUOUS,
                CDLAnalysisStatus.ERROR,
            }
            and not self.error_message
        ):
            raise ValueError(f"error_message is required when status is '{self.status.value}'.")
        return self
