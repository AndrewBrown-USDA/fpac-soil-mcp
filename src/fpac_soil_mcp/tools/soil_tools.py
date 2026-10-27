"""Soil lookup tools for FastMCP server.

Provides tools for querying USDA NRCS Soil Data Access (SDA) by WGS84 geographic
coordinates and by SSURGO map unit key (mukey).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any


from fpac_soil_mcp.tools.exemption_tools import check_urban_area_exemption
from fpac_soil_mcp.tools.lesa_tools import calculate_preliminary_lesa
from fpac_soil_mcp.tools.spatial_analysis_tools import (
    analyze_corridor_fppa,
    analyze_farmland_by_polygon,
)
from fpac_soil_mcp.tools.soil_lookup_tools import (
    get_farmland_classification_by_mukey,
    get_farmland_classification_by_point,
    get_soil_interpretations,
    get_soil_polygons_by_geometry,
)

if TYPE_CHECKING:
    from fastmcp import FastMCP

logger = logging.getLogger(__name__)


def register_soil_tools(mcp: FastMCP) -> None:
    """Register soil query tools on the provided FastMCP instance.

    Args:
        mcp: FastMCP server instance.
    """
    mcp.tool(
        name="get_farmland_classification_by_point",
        description=(
            "Query USDA NRCS Soil Data Access (SDA) by WGS84 point coordinates (latitude, longitude) "
            "to retrieve SSURGO soil map unit information, official farmland classification (7 CFR 657), "
            "and FPPA regulatory notice."
        ),
    )(get_farmland_classification_by_point)

    mcp.tool(
        name="get_farmland_classification_by_mukey",
        description=(
            "Query USDA NRCS Soil Data Access (SDA) by Map Unit Key (mukey) to retrieve SSURGO "
            "soil map unit details, official farmland classification (7 CFR 657), and FPPA regulatory notice."
        ),
    )(get_farmland_classification_by_mukey)

    mcp.tool(
        name="analyze_farmland_by_polygon",
        description=(
            "Execute comprehensive FPPA preliminary screening on a GeoJSON Polygon or MultiPolygon AOI. "
            "Calculates total equal-area acreage, checks Census 2020 Urban Area statutory exemption status, "
            "queries intersecting SSURGO map units via SDA with exact spatial clipping, retrieves crop "
            "NCCPI productivity ratings, calculates candidate Land Evaluation (LE) scores, "
            "and generates acreage breakdowns by farmland classification."
        ),
    )(analyze_farmland_by_polygon)

    mcp.tool(
        name="calculate_preliminary_lesa",
        description=(
            "Calculate preliminary Land Evaluation and Site Assessment (LESA) scores and statutory threshold triggers. "
            "Performs spatial SSURGO soil clipping across the AOI geometry, computes area-weighted Land Evaluation (LE, 0-100), "
            "evaluates statutory Site Assessment (SA, 0-160) criteria for Form AD-1006 (site) or Form NRCS-CPA-106 (corridor), "
            "and enforces the statutory 160-point mandatory alternatives consideration threshold under 7 CFR § 658.4(c)(2)."
        ),
    )(calculate_preliminary_lesa)

    mcp.tool(
        name="get_soil_polygons_by_geometry",
        description=(
            "Retrieve intersecting SSURGO soil map unit polygon geometries and attributes as a GeoJSON "
            "FeatureCollection for a Polygon or MultiPolygon AOI, with support for server-side clipping and geodesic acreage."
        ),
    )(get_soil_polygons_by_geometry)

    mcp.tool(
        name="check_urban_area_exemption",
        description=(
            "Screen a project footprint against Census Bureau 2020 Urban Area boundaries (Layer 0) "
            "for preliminary statutory exemption analysis under 7 CFR § 658.2(a)."
        ),
    )(check_urban_area_exemption)

    mcp.tool(
        name="get_soil_interpretations",
        description=(
            "Retrieve component-weighted soil interpretations (such as NCCPI v3 crop productivity) "
            "from USDA NRCS Soil Data Access (SDA) for a list of map unit keys (mukeys)."
        ),
    )(get_soil_interpretations)

    mcp.tool(
        name="analyze_corridor_fppa",
        description=(
            "Execute multi-county linear corridor FPPA screening, topological erasure of indirect staging areas, "
            "Census TIGERweb county partitioning, USDA SDA soil intersection, NASS agricultural baseline queries, "
            "composite LE calculation, sum reconciliation, and optional 7 CFR § 658.5(c) Form NRCS-CPA-106 LESA scoring."
        ),
    )(analyze_corridor_fppa)
