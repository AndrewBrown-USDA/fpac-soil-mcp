"""Custom HTTP routes for FPAC Soil MCP server."""

import datetime

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from fpac_soil_mcp.core.config import settings
from fpac_soil_mcp.core.constants import CITATIONS


def register_routes(mcp: FastMCP) -> None:
    """Register custom HTTP endpoints on FastMCP server (e.g. /health, /meta)."""

    @mcp.custom_route("/health", methods=["GET"])
    async def health_check(request: Request) -> Response:
        """Health check endpoint returning server status."""
        return JSONResponse(
            {
                "status": "healthy",
                "service": "fpac-soil-mcp",
                "timestamp_utc": datetime.datetime.now(datetime.UTC).isoformat(),
                "transport": settings.mcp_transport,
            }
        )

    @mcp.custom_route("/meta", methods=["GET"])
    async def meta_endpoint(request: Request) -> Response:
        """Server metadata and capabilities endpoint."""
        return JSONResponse(
            {
                "service": "fpac-soil-mcp",
                "description": "USDA FPAC Farmland Protection Policy Act (FPPA) Soil Screening MCP Server",
                "sda_endpoint": settings.sda_tabular_url,
                "citations": CITATIONS,
            }
        )
