"""Tests for PolygonFarmlandAnalysis and polygon screening engine."""

import httpx

from fpac_soil_mcp.polygon_analysis import PolygonAnalyzer, categorize_farmland_class
from fpac_soil_mcp.sda_client import SDAClient
from fpac_soil_mcp.tigerweb_client import TigerwebClient


def test_categorize_farmland_class():
    assert categorize_farmland_class("All areas are prime farmland") == "prime"
    assert categorize_farmland_class("Prime farmland if drained") == "conditional_prime"
    assert categorize_farmland_class("Farmland of statewide importance") == "statewide"
    assert categorize_farmland_class("Farmland of local importance") == "local"
    assert categorize_farmland_class("Farmland of unique importance") == "unique"
    assert categorize_farmland_class("Not prime farmland") == "not_prime"
    assert categorize_farmland_class(None) == "unmapped"


def test_analyze_polygon_success():
    geojson = {
        "type": "Polygon",
        "coordinates": [
            [
                [-93.5, 42.0],
                [-93.4, 42.0],
                [-93.4, 42.1],
                [-93.5, 42.1],
                [-93.5, 42.0],
            ]
        ],
    }

    mock_sda_spatial = {
        "Table": [
            ["mukey", "musym", "muname", "farmlndcl", "areasymbol", "area_ac"],
            ["412915", "138B", "Clarion loam", "All areas are prime farmland", "IA169", 120.5],
            ["412916", "507", "Canisteo clay loam", "Prime farmland if drained", "IA169", 80.2],
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
        ]
    }

    def sda_handler(request: httpx.Request) -> httpx.Response:
        if b"comp_interp" in request.content:
            return httpx.Response(200, json=mock_sda_interp)
        return httpx.Response(200, json=mock_sda_spatial)

    mock_tiger_resp = {"features": []}

    def tiger_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=mock_tiger_resp)

    sda_client = SDAClient(http_client=httpx.Client(transport=httpx.MockTransport(sda_handler)))
    tiger_client = TigerwebClient(
        http_client=httpx.Client(transport=httpx.MockTransport(tiger_handler))
    )

    analyzer = PolygonAnalyzer(sda_client=sda_client, tigerweb_client=tiger_client)
    res = analyzer.analyze_polygon(geojson)

    assert res.coverage_status == "covered"
    assert res.total_aoi_acres > 0
    assert len(res.map_units) == 2
    assert res.farmland_summary.prime_farmland_acres == 120.5
    assert res.farmland_summary.conditional_prime_acres == 80.2
    assert res.farmland_summary.total_fppa_protected_pct > 0
    assert "mukey,musym,muname" in res.tabular_csv
    assert res.geometry_hash.startswith("sha256:")
    assert res.urban_screening.get("status") == "success"
    assert res.manifest["spatial_clipping_engine"] == "USDA NRCS SDA STIntersection / STArea"
