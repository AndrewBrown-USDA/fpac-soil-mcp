"""FastMCP prompts package."""

from fastmcp import FastMCP

from fpac_soil_mcp.mcp.prompts.fppa_prompts import register_fppa_prompts


def register_prompts(mcp: FastMCP) -> None:
    """Register all prompts on the FastMCP server."""
    register_fppa_prompts(mcp)
