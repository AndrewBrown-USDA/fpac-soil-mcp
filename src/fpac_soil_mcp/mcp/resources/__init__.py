"""FastMCP resources package."""

from fastmcp import FastMCP

from fpac_soil_mcp.mcp.resources.fppa_resources import register_fppa_resources


def register_resources(mcp: FastMCP) -> None:
    """Register all resources on the FastMCP server."""
    register_fppa_resources(mcp)
