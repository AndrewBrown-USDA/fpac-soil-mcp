"""Tests for PolygonFarmlandAnalysis and polygon screening engine."""

from unittest.mock import MagicMock

import httpx
import pytest

from fpac_soil_mcp.polygon_analysis import PolygonAnalyzer, categorize_farmland_class
from fpac_soil_mcp.sda_client import SDAClient
from fpac_soil_mcp.tigerweb_client import TigerwebClient

GEOJSON = {
    "type": "Polygon",
    "coordinates": [[[-93.5, 42.0], [-93.4, 42.0], [-93.4, 42.1], [-93.5, 42.1], [-93.5, 42.0]]],
}


def _spatial(*rows):
    return {
        "Table": [
            ["mukey", "musym", "muname", "farmlndcl", "areasymbol", "area_ac"],
            *rows,
        ]
    }


def _analyzer(sda):
    tiger = TigerwebClient(
        http_client=httpx.Client(
            transport=httpx.MockTransport(lambda req: httpx.Response(200, json={"features": []}))
        )
    )
    return PolygonAnalyzer(sda_client=sda, tigerweb_client=tiger)


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

    assert res.coverage_status == "partially_covered"
    assert res.total_aoi_acres > 0
    assert len(res.map_units) == 2
    assert res.farmland_summary.prime_farmland_acres == 120.5
    assert res.farmland_summary.conditional_prime_acres == 80.2
    assert res.farmland_summary.total_fppa_protected_pct > 0
    assert "mukey,musym,muname" in res.tabular_csv
    assert res.geometry_hash.startswith("sha256:")
    assert res.urban_screening.get("status") == "success"
    assert res.manifest["spatial_clipping_engine"] == "USDA NRCS SDA STIntersection / STArea"


def test_analyze_polygon_include_nccpi_false_skips_rating_query():
    geojson = {
        "type": "Polygon",
        "coordinates": [
            [[-93.5, 42.0], [-93.4, 42.0], [-93.4, 42.1], [-93.5, 42.1], [-93.5, 42.0]]
        ],
    }
    spatial = {
        "Table": [
            ["mukey", "musym", "muname", "farmlndcl", "areasymbol", "area_ac"],
            ["412915", "138B", "Clarion loam", "All areas are prime farmland", "IA169", 10.0],
        ]
    }

    def sda_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=spatial)

    class NoNccpiClient(SDAClient):
        def get_interpretations(self, *args, **kwargs):
            raise AssertionError("NCCPI query should be skipped")

        def get_county_max_productivity_rating(self, *args, **kwargs):
            raise AssertionError("County benchmark query should be skipped")

    sda_client = NoNccpiClient(http_client=httpx.Client(transport=httpx.MockTransport(sda_handler)))
    tiger_client = TigerwebClient(
        http_client=httpx.Client(
            transport=httpx.MockTransport(lambda req: httpx.Response(200, json={"features": []}))
        )
    )
    result = PolygonAnalyzer(sda_client=sda_client, tigerweb_client=tiger_client).analyze_polygon(
        geojson, include_nccpi=False
    )
    assert result.map_units[0].productivity_rating is None


def test_analyze_polygon_treats_decimal_99_as_unrated_nccpi():
    geojson = {
        "type": "Polygon",
        "coordinates": [
            [[-93.5, 42.0], [-93.4, 42.0], [-93.4, 42.1], [-93.5, 42.1], [-93.5, 42.0]]
        ],
    }
    spatial = {
        "Table": [
            ["mukey", "musym", "muname", "farmlndcl", "areasymbol", "area_ac"],
            ["412915", "138B", "Clarion", "All areas are prime farmland", "IA169", 10.0],
        ]
    }
    interp = {"Table": [["mukey", "numeric_rating"], ["412915", 99.0]]}

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=interp if b"comp_interp" in request.content else spatial)

    sda = SDAClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))
    tiger = TigerwebClient(
        http_client=httpx.Client(
            transport=httpx.MockTransport(lambda req: httpx.Response(200, json={"features": []}))
        )
    )
    result = PolygonAnalyzer(sda_client=sda, tigerweb_client=tiger).analyze_polygon(geojson)
    assert result.map_units[0].productivity_rating is None


def test_analyze_polygon_partitions_county_benchmarks_and_weights_by_acreage():
    geojson = {
        "type": "Polygon",
        "coordinates": [
            [[-93.5, 42.0], [-93.4, 42.0], [-93.4, 42.1], [-93.5, 42.1], [-93.5, 42.0]]
        ],
    }
    spatial = {
        "Table": [
            ["mukey", "musym", "muname", "farmlndcl", "areasymbol", "area_ac"],
            ["412915", "138B", "Clarion", "All areas are prime farmland", "IA169", 10.0],
            ["512915", "138B", "Clarion", "All areas are prime farmland", "IA170", 90.0],
        ]
    }

    class PartitionedSDAClient(SDAClient):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.interpretation_mukeys = []
            self.benchmark_areasymbols = []

        def get_interpretations(self, mukeys, *args, **kwargs):
            self.interpretation_mukeys.append(set(mukeys))
            return [
                {"mukey": "412915", "numeric_rating": 0.8},
                {"mukey": "512915", "numeric_rating": 0.25},
            ]

        def get_county_max_productivity_rating(self, areasymbol, *args, **kwargs):
            self.benchmark_areasymbols.append(areasymbol)
            return {"IA169": 1.0, "IA170": 0.5}[areasymbol]

    sda = PartitionedSDAClient(
        http_client=httpx.Client(
            transport=httpx.MockTransport(lambda req: httpx.Response(200, json=spatial))
        )
    )
    tiger = TigerwebClient(
        http_client=httpx.Client(
            transport=httpx.MockTransport(lambda req: httpx.Response(200, json={"features": []}))
        )
    )
    result = PolygonAnalyzer(sda_client=sda, tigerweb_client=tiger).analyze_polygon(geojson)

    assert sda.interpretation_mukeys == [{"412915", "512915"}]
    assert set(sda.benchmark_areasymbols) == {"IA169", "IA170"}
    assert len(sda.benchmark_areasymbols) == 2
    assert result.manifest["candidate_le_score"] == pytest.approx(53.0)


@pytest.mark.parametrize("index", ["storie", "custom"])
def test_unsupported_selector_rejected_before_sda(index):
    sda = MagicMock(spec=SDAClient)
    with pytest.raises(ValueError, match="Unsupported productivity index type"):
        _analyzer(sda).analyze_polygon(GEOJSON, productivity_index=index)
    sda.get_spatial_intersection.assert_not_called()
    sda.get_productivity_ratings.assert_not_called()
    sda.get_interpretations.assert_not_called()


@pytest.mark.parametrize("index", ["nccpi"])
@pytest.mark.parametrize("sentinel", [99.0, 999.0, -99.0, -999.0])
def test_requested_index_sentinels_are_unrated(index, sentinel):
    class SentinelSDA(SDAClient):
        def get_interpretations(self, *args, **kwargs):
            return [{"mukey": "1", "numeric_rating": sentinel}]

        def get_productivity_ratings(self, *args, **kwargs):
            return [{"mukey": "1", "numeric_rating": sentinel, "is_rated": False}]

        def get_county_max_productivity_rating(self, *args, **kwargs):
            return 100.0 if index != "nccpi" else 1.0

    sda = SentinelSDA(
        http_client=httpx.Client(
            transport=httpx.MockTransport(
                lambda req: httpx.Response(
                    200,
                    json=_spatial(
                        ["1", "A", "Soil", "All areas are prime farmland", "AA001", 10.0]
                    ),
                )
            )
        )
    )
    result = _analyzer(sda).analyze_polygon(GEOJSON, productivity_index=index)
    assert result.map_units[0].productivity_rating is None
    assert result.manifest["land_evaluation"]["rated_acreage"] == 0
    assert result.manifest["candidate_le_score"] == 0.0


def test_requested_index_calls_are_partitioned_for_nccpi():
    class CallsSDA(SDAClient):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.calls = []

        def get_interpretations(self, *args, **kwargs):
            self.calls.append(("interpretations",))
            return [
                {"mukey": key, "numeric_rating": 0.5, "rating_class": "High"} for key in ("1", "2")
            ]

    sda = CallsSDA(
        http_client=httpx.Client(
            transport=httpx.MockTransport(
                lambda req: httpx.Response(
                    200,
                    json=_spatial(
                        ["1", "A", "Soil", "All areas are prime farmland", "AA001", 10.0],
                        ["2", "B", "Soil", "All areas are prime farmland", "AA002", 10.0],
                    ),
                )
            )
        )
    )
    result = _analyzer(sda).analyze_polygon(GEOJSON, productivity_index="nccpi")
    assert ("interpretations",) in sda.calls
    assert result.manifest["candidate_le_score"] == pytest.approx(50.0)


@pytest.mark.parametrize("sentinel", [99.0, 999.0, -99.0, -999.0])
def test_analyze_polygon_treats_all_nccpi_sentinels_as_unrated(sentinel):
    geojson = {
        "type": "Polygon",
        "coordinates": [
            [[-93.5, 42.0], [-93.4, 42.0], [-93.4, 42.1], [-93.5, 42.1], [-93.5, 42.0]]
        ],
    }
    spatial = {
        "Table": [
            ["mukey", "musym", "muname", "farmlndcl", "areasymbol", "area_ac"],
            ["412915", "138B", "Clarion", "All areas are prime farmland", "IA169", 10.0],
        ]
    }

    class SentinelSDAClient(SDAClient):
        def get_interpretations(self, *args, **kwargs):
            return [{"mukey": "412915", "numeric_rating": sentinel}]

        def get_county_max_productivity_rating(self, *args, **kwargs):
            return 1.0

    sda = SentinelSDAClient(
        http_client=httpx.Client(
            transport=httpx.MockTransport(lambda req: httpx.Response(200, json=spatial))
        )
    )
    tiger = TigerwebClient(
        http_client=httpx.Client(
            transport=httpx.MockTransport(lambda req: httpx.Response(200, json={"features": []}))
        )
    )
    result = PolygonAnalyzer(sda_client=sda, tigerweb_client=tiger).analyze_polygon(geojson)

    assert result.map_units[0].productivity_rating is None


def test_analyze_polygon_fully_covered():
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

    # Geodesic area for this box in Iowa is approx 21744.4 acres or similar calculated value
    # Let's mock spatial table to match total_aoi_acres exactly
    from fpac_soil_mcp.geometry import calculate_acreage, parse_geojson_geometry

    geom = parse_geojson_geometry(geojson)
    total_aoi = calculate_acreage(geom)

    mock_sda_spatial = {
        "Table": [
            ["mukey", "musym", "muname", "farmlndcl", "areasymbol", "area_ac"],
            ["412915", "138B", "Clarion loam", "All areas are prime farmland", "IA169", total_aoi],
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
        ]
    }

    def sda_handler(request: httpx.Request) -> httpx.Response:
        if b"comp_interp" in request.content:
            return httpx.Response(200, json=mock_sda_interp)
        return httpx.Response(200, json=mock_sda_spatial)

    def tiger_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"features": []})

    sda_client = SDAClient(http_client=httpx.Client(transport=httpx.MockTransport(sda_handler)))
    tiger_client = TigerwebClient(
        http_client=httpx.Client(transport=httpx.MockTransport(tiger_handler))
    )

    analyzer = PolygonAnalyzer(sda_client=sda_client, tigerweb_client=tiger_client)
    res = analyzer.analyze_polygon(geojson)

    assert res.coverage_status == "covered"
    assert res.farmland_summary.unmapped_acres == 0.0
