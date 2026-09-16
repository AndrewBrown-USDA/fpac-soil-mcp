"""Configuration settings for fpac-soil-mcp."""

from pydantic import Field
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


settings = Settings()
