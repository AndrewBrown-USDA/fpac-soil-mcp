"""FastMCP tool registrations for FPAC Soil MCP."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fpac_soil_mcp.tools.fppa_tools import (
    explain_fppa_screening_scope,
    list_farmland_classes,
    register_fppa_tools,
)
from fpac_soil_mcp.tools.soil_tools import (
    get_farmland_classification_by_mukey,
    get_farmland_classification_by_point,
    register_soil_tools,
)

if TYPE_CHECKING:
    from fastmcp import FastMCP

__all__ = [
    "explain_fppa_screening_scope",
    "get_farmland_classification_by_mukey",
    "get_farmland_classification_by_point",
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
