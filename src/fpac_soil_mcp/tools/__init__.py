"""FastMCP tool registrations for FPAC Soil MCP."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fpac_soil_mcp.tools.fppa_tools import (
    explain_fppa_screening_scope,
    list_farmland_classes,
    register_fppa_tools,
)
from fpac_soil_mcp.tools.soil_tools import (
    analyze_farmland_by_polygon,
    check_urban_area_exemption,
    get_farmland_classification_by_mukey,
    get_farmland_classification_by_point,
    get_soil_interpretations,
    get_soil_polygons_by_geometry,
    register_soil_tools,
)

if TYPE_CHECKING:
    from fastmcp import FastMCP

__all__ = [
    "analyze_farmland_by_polygon",
    "check_urban_area_exemption",
    "explain_fppa_screening_scope",
    "get_farmland_classification_by_mukey",
    "get_farmland_classification_by_point",
    "get_soil_interpretations",
    "get_soil_polygons_by_geometry",
    "list_farmland_classes",
    "register_fppa_tools",
    "register_soil_tools",
    "register_tools",
]


def register_tools(mcp: FastMCP) -> None:
    """Register all soil and FPPA tools with the provided FastMCP server.

    Args:
        mcp: FastMCP server instance.
    """
    register_soil_tools(mcp)
    register_fppa_tools(mcp)
