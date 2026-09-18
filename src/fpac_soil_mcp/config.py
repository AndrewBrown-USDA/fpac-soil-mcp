"""Configuration settings for fpac-soil-mcp."""

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings for FPAC Soil MCP server."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # SDA API Configuration
    sda_tabular_url: str = Field(
        default="https://sdmdataaccess.nrcs.usda.gov/Tabular/post.rest",
        description="USDA NRCS Soil Data Access Tabular Query endpoint",
    )
    request_timeout_seconds: float = Field(
        default=30.0,
        description="HTTP request timeout in seconds for SDA queries",
    )
    max_retries: int = Field(
        default=3,
        description="Maximum retry attempts for transient SDA HTTP/connection errors",
    )

    # USDA NASS Quick Stats Configuration
    nass_api_key: str | None = Field(
        default=None,
        description="Optional API key for USDA NASS Quick Stats API",
    )
    nass_base_url: str = Field(
        default="https://quickstats.nass.usda.gov/api/api_GET/",
        description="Base URL for USDA NASS Quick Stats API",
    )
    nass_enabled: bool = Field(
        default=False,
        description="Whether USDA NASS integration is actively enabled",
    )
    nass_census_year: int = Field(
        default=2022,
        description="Default baseline Census of Agriculture year",
    )

    # Census TIGERweb Configuration
    tigerweb_rest_url: str = Field(
        default="https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_Census2020/MapServer/6",
        description="Census TIGERweb 2020 Urban Areas Layer endpoint",
    )
    tigerweb_urban_layer_id: int = Field(
        default=6,
        description="Layer index for 2020 Census Urban Areas",
    )
    tigerweb_timeout_seconds: float = Field(
        default=15.0,
        description="HTTP request timeout for TIGERweb spatial queries",
    )

    # SDA Interpretation Rules & NCCPI Allowlist
    sda_interpretation_rules_allowed: list[str] = Field(
        default_factory=lambda: [
            "NCCPI - National Commodity Crop Productivity Index (Ver 3.0)",
            "NCCPI - Corn and Soybeans Crop Productivity Index",
            "NCCPI - Small Grains Crop Productivity Index",
            "NCCPI - Cotton Crop Productivity Index",
            "Farmland Classification",
        ],
        description="Allowlist of supported SDA interpretation rule names",
    )
    sda_aggregation_methods_allowed: list[str] = Field(
        default_factory=lambda: [
            "Weighted Average",
            "Dominant Component",
        ],
        description="Allowlist of supported component aggregation methods",
    )

    # MCP Server Configuration
    mcp_transport: str = Field(
        default="stdio",
        description="Transport type for FastMCP (stdio or sse)",
    )
    mcp_host: str = Field(
        default="127.0.0.1",
        description="Host to bind when using SSE transport",
    )
    mcp_port: int = Field(
        default=8000,
        description="Port to bind when using SSE transport",
    )

    @field_validator("sda_tabular_url", "nass_base_url", "tigerweb_rest_url")
    @classmethod
    def _validate_urls(cls, v: str, info) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError(f"{info.field_name} must be a valid HTTP/HTTPS URL.")
        return v

    @field_validator("request_timeout_seconds", "tigerweb_timeout_seconds")
    @classmethod
    def _validate_timeouts(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Timeout must be a positive number of seconds.")
        return v

    @field_validator("max_retries")
    @classmethod
    def _validate_retries(cls, v: int) -> int:
        if v < 0:
            raise ValueError("max_retries cannot be negative.")
        return v

    @field_validator("nass_census_year")
    @classmethod
    def _validate_year(cls, v: int) -> int:
        if v < 1900 or v > 2100:
            raise ValueError(f"nass_census_year '{v}' is outside valid range [1900, 2100].")
        return v

    @model_validator(mode="after")
    def _validate_capabilities(self) -> "Settings":
        if self.nass_enabled and not (self.nass_api_key and self.nass_api_key.strip()):
            raise ValueError("nass_api_key is required when nass_enabled is set to True.")
        return self

    def validate_nass_capability(self) -> None:
        """Explicit capability check for callers attempting to execute NASS queries."""
        if not (self.nass_api_key and self.nass_api_key.strip()):
            raise ValueError("USDA NASS integration requires 'nass_api_key' to be configured.")


settings = Settings()
