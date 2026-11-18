"""End-to-end integration and contract tests for Phase 2 Polygon AOI Screening & Farmland Analysis."""

import json
from pathlib import Path

import httpx
from fastmcp import FastMCP

from fpac_soil_mcp.clients.sda import SDAClient
from fpac_soil_mcp.clients.tigerweb import TigerwebClient
from fpac_soil_mcp.domain.polygon_analyzer import PolygonAnalyzer
from fpac_soil_mcp.mcp.tools import register_tools

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "aoi" / "benchmark_50_aois.json"


def test_phase2_end_to_end_screening_with_fixtures():
    with open(FIXTURE_PATH, encoding="utf-8") as f:
        data = json.load(f)

    fixture = data["fixtures"][0]
    geojson = fixture["geometry"]

    mock_sda_spatial = {
        "Table": [
            ["mukey", "musym", "muname", "farmlndcl", "areasymbol", "area_ac"],
            [
                "412915",
                "138B",
                "Clarion loam, 2 to 5 percent slopes",
                "All areas are prime farmland",
                "IA169",
                25.0,
            ],
            [
                "412916",
                "507",
                "Canisteo clay loam, 0 to 2 percent slopes",
                "Prime farmland if drained",
                "IA169",
                15.0,
            ],
            [
                "412917",
                "138C2",
                "Clarion loam, 6 to 10 percent slopes",
                "Farmland of statewide importance",
                "IA169",
                9.42,
            ],
        ]
    }

    mock_sda_interp = {
        "Table": [
            [
                "mukey",
                "areasymbol",
                "musym",
                "muname",
                "numeric_rating",
                "rating_class",
                "rated_pct",
                "total_pct",
            ],
            ["412915", "IA169", "138B", "Clarion loam", 0.88, "High", 100, 100],
            ["412916", "IA169", "507", "Canisteo clay loam", 0.82, "High", 95, 100],
            ["412917", "IA169", "138C2", "Clarion loam", 0.71, "Moderate", 90, 100],
        ]
    }

    def sda_handler(request: httpx.Request) -> httpx.Response:
        if b"comp_interp" in request.content:
            return httpx.Response(200, json=mock_sda_interp)
        return httpx.Response(200, json=mock_sda_spatial)

    mock_tiger_resp = {
        "features": [
            {
                "attributes": {
                    "GEOID": "12345",
                    "NAME": "Ames, IA Urban Area",
                    "POP100": 66427,
                    "HU100": 26800,
                }
            }
        ]
    }

    def tiger_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=mock_tiger_resp)

    sda_client = SDAClient(http_client=httpx.Client(transport=httpx.MockTransport(sda_handler)))
    tiger_client = TigerwebClient(
        http_client=httpx.Client(transport=httpx.MockTransport(tiger_handler))
    )

    analyzer = PolygonAnalyzer(sda_client=sda_client, tigerweb_client=tiger_client)
    res = analyzer.analyze_polygon(geojson)

    # 1. Total acreage matches within tolerance
    assert abs(res.total_aoi_acres - fixture["expected_acreage"]) <= 0.05

    # 2. Map units and interpretations populated
    assert len(res.map_units) == 3
    assert [unit.productivity_rating for unit in res.map_units] == [0.88, 0.82, 0.71]
    assert [unit.productivity_rating_class for unit in res.map_units] == [
        "High",
        "High",
        "Moderate",
    ]
    assert all(
        unit.productivity_rating_source
        == "NCCPI - National Commodity Crop Productivity Index (Ver 3.0)"
        for unit in res.map_units
    )

    # 3. Farmland breakdown sums correctly
    summary = res.farmland_summary
    assert summary.prime_farmland_acres > 0
    assert summary.conditional_prime_acres > 0
    assert summary.statewide_importance_acres > 0
    assert summary.total_fppa_protected_pct > 0

    # 4. Urban screening captured
    assert res.urban_screening["status"] == "success"
    assert res.urban_screening["is_urban_intersected"] is True
    assert "Ames, IA Urban Area" in res.urban_screening["urban_area_names"]

    # 5. Provenance, hash, and disclaimers
    assert res.geometry_hash.startswith("sha256:")
    assert "PRELIMINARY SCREENING ONLY" in res.regulatory_notice
    assert len(res.limitations) >= 5


def test_mcp_tool_registration_surface():
    import asyncio

    mcp = FastMCP("test-server")
    register_tools(mcp)
    assert mcp.name == "test-server"

    tools = asyncio.run(mcp.list_tools())
    tool_names = [t.name for t in tools]

    expected_tools = [
        "get_farmland_classification_by_point",
        "get_farmland_classification_by_mukey",
        "analyze_farmland_by_polygon",
        "calculate_preliminary_lesa",
        "get_soil_polygons_by_geometry",
        "check_urban_area_exemption",
        "get_soil_interpretations",
        "explain_fppa_screening_scope",
        "list_farmland_classes",
        "analyze_corridor_fppa",
        "analyze_cdl_histogram",
        "analyze_cdl_context",
    ]

    for expected in expected_tools:
        assert expected in tool_names
    assert len(tool_names) == 12
    assert set(tool_names) == set(expected_tools)
