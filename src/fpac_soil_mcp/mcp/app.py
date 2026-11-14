"""FastMCP application instance and factory for fpac-soil-mcp."""

import logging

from fastmcp import FastMCP

from fpac_soil_mcp.core.config import settings
from fpac_soil_mcp.mcp.prompts import register_prompts
from fpac_soil_mcp.mcp.resources import register_resources
from fpac_soil_mcp.mcp.routes import register_routes
from fpac_soil_mcp.mcp.tools import register_tools

logger = logging.getLogger(__name__)


def create_mcp_server() -> FastMCP:
    """Create and configure the FastMCP server instance with tools, resources, prompts, and routes.

    Returns:
        Configured FastMCP instance.
    """
    server = FastMCP(
        name="fpac-soil-mcp",
        instructions=(
            "USDA FPAC Farmland Protection Policy Act (FPPA) Soil Screening MCP Server. "
            "Provides SSURGO soil map unit and farmland classification queries via USDA NRCS Soil Data Access (SDA). "
            "Outputs preliminary soil inventory data (7 CFR Part 657) with strict regulatory disclaimers."
        ),
    )

    # Register components
    register_tools(server)
    register_resources(server)
    register_prompts(server)
    register_routes(server)

    return server


# Default server instance for module-level import
mcp = create_mcp_server()


def main() -> None:
    """Entry point for running the FastMCP server."""
    logging.basicConfig(level=logging.INFO)
    logger.info("Starting fpac-soil-mcp server (transport=%s)...", settings.mcp_transport)

    if settings.mcp_transport.lower() == "sse":
        mcp.run(transport="sse", host=settings.mcp_host, port=settings.mcp_port)
    elif settings.mcp_transport.lower() in ("http", "streamable-http"):
        mcp.run(transport="http", host=settings.mcp_host, port=settings.mcp_port)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
