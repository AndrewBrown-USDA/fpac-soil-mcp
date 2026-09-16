"""FPPA scope explanation and farmland class listing tools for FastMCP server."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fpac_soil_mcp.fppa import get_farmland_class_list, get_fppa_scope_explanation
from fpac_soil_mcp.models import FarmlandClassListResponse, FppaScopeResponse

if TYPE_CHECKING:
    from fastmcp import FastMCP


def explain_fppa_screening_scope() -> FppaScopeResponse:
    """Explain FPPA screening scope vs. full Land Evaluation and Site Assessment (LESA) determination.

    Returns:
        FppaScopeResponse breaking down SDA preliminary screening capabilities vs. official
        FPPA Form AD-1006 / NRCS-CPA-106 requirements, with citations to 7 CFR Parts 657 & 658.
    """
    data = get_fppa_scope_explanation()
    return FppaScopeResponse(**data)


def list_farmland_classes() -> FarmlandClassListResponse:
    """List standard USDA NRCS SSURGO farmland classification categories and FPPA statuses.

    Returns:
        FarmlandClassListResponse containing definitions and regulatory categories for all
        standard mapunit.farmlndcl values.
    """
    data = get_farmland_class_list()
    return FarmlandClassListResponse(**data)


def register_fppa_tools(mcp: FastMCP) -> None:
    """Register FPPA scope and classification listing tools on the FastMCP instance.

    Args:
        mcp: FastMCP server instance.
    """
    mcp.tool(
        name="explain_fppa_screening_scope",
        description=(
            "Provides an authoritative regulatory breakdown distinguishing preliminary SDA soil "
            "screening (7 CFR 657) from formal FPPA Land Evaluation & Site Assessment (LESA) scoring "
            "and Form AD-1006 determinations (7 CFR 658)."
        ),
    )(explain_fppa_screening_scope)

    mcp.tool(
        name="list_farmland_classes",
        description=(
            "List documented standard USDA NRCS SSURGO Farmland Classification categories "
            "(mapunit.farmlndcl) with definitions, FPPA statuses, and regulatory references."
        ),
    )(list_farmland_classes)
