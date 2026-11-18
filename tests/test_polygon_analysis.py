"""Tests for PolygonFarmlandAnalysis and polygon screening engine."""

import csv
import io
from unittest.mock import MagicMock

import httpx
import pytest

from fpac_soil_mcp.clients.sda import (
    PRODUCTIVITY_PROVENANCE,
    SDAClient,
    SDAClientError,
    SDAQueryError,
)
from fpac_soil_mcp.clients.tigerweb import TigerwebClient
from fpac_soil_mcp.domain.nccpi_baseline import NCCPI_BASELINE_FIELDS, NCCPI_BASELINE_RULE
from fpac_soil_mcp.domain.polygon_analyzer import PolygonAnalyzer, categorize_farmland_class

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
    assert categorize_farmland_class("Some unrecognized SSURGO label") == "unknown"
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

    assert res.coverage_status == "partial"
    assert res.total_aoi_acres > 0
    assert len(res.map_units) == 2
    assert res.farmland_summary.prime_farmland_acres == 120.5
    assert res.farmland_summary.conditional_prime_acres == 80.2
    assert res.farmland_summary.total_fppa_protected_pct > 0
    assert "mukey,musym,muname" in res.tabular_csv
    assert res.geometry_hash.startswith("sha256:")
    assert res.urban_screening.get("status") == "success"
    assert res.manifest["spatial_clipping_engine"] == "USDA NRCS SDA STIntersection / STArea"
    assert res.manifest["criterion_2_perimeter_evidence"]["evidence_status"] == "measured"
    assert res.manifest["criterion_2_perimeter_evidence"]["is_verified"] is True


@pytest.mark.parametrize(
    ("evidence_status", "is_verified"),
    [("measured", True), ("unavailable", False), ("error", False)],
)
def test_analyze_polygon_preserves_perimeter_evidence_status(evidence_status, is_verified):
    spatial = {
        "Table": [
            ["mukey", "musym", "muname", "farmlndcl", "areasymbol", "area_ac"],
            ["412915", "138B", "Clarion loam", "All areas are prime farmland", "IA169", 10.0],
        ]
    }
    sda = SDAClient(
        http_client=httpx.Client(
            transport=httpx.MockTransport(lambda req: httpx.Response(200, json=spatial))
        )
    )
    analyzer = _analyzer(sda)
    analyzer.tigerweb_client.get_perimeter_evidence = lambda geometry: {
        "evidence_status": evidence_status,
        "is_verified": is_verified,
        "normalized_ratio": 1.0 if evidence_status == "measured" else None,
    }

    result = analyzer.analyze_polygon(GEOJSON)

    evidence = result.manifest["criterion_2_perimeter_evidence"]
    assert evidence["evidence_status"] == evidence_status
    assert evidence["is_verified"] is is_verified


@pytest.mark.parametrize("method", ["analyze_polygon", "analyze_polygon_sync"])
def test_analyze_polygon_rejects_removed_include_nccpi_argument(method):
    analyzer = PolygonAnalyzer(sda_client=MagicMock(), tigerweb_client=MagicMock())
    with pytest.raises(TypeError, match="include_nccpi"):
        getattr(analyzer, method)(GEOJSON, include_nccpi=True)


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


@pytest.mark.parametrize("index", ["custom", "unsupported", ""])
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
    assert result.manifest["candidate_le_score"] is None
    assert result.manifest["land_evaluation"]["aoi_relative_rating"] is None


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
    from fpac_soil_mcp.spatial.geometry import calculate_acreage, parse_geojson_geometry

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
    assert res.manifest["land_evaluation"]["coverage_status"] == "rated"
    assert [u.productivity_coverage_status for u in res.map_units] == ["rated"]


@pytest.mark.parametrize("index", ["nccpi", "csr2", "cpi", "storie"])
def test_all_validated_selectors_accepted(index):
    """All validated productivity index selectors pass the guard without ValueError."""
    mock_sda = MagicMock(spec=SDAClient)
    mock_sda.base_url = "https://sdmdataaccess.nrcs.usda.gov/Tabular/post.rest"
    mock_sda.get_spatial_intersection.return_value = []
    mock_sda.get_productivity_ratings.return_value = []
    mock_sda.get_county_max_productivity_rating.return_value = None
    mock_sda.get_interpretations.return_value = []
    analyzer = _analyzer(mock_sda)
    # Should NOT raise ValueError — downstream calls can return empty/mock data
    result = analyzer.analyze_polygon(GEOJSON, productivity_index=index)
    assert result.query_type == "polygon"


@pytest.mark.parametrize("index", ["csr2", "cpi", "storie"])
def test_polygon_forwards_selected_productivity_index(index):
    mock_sda = MagicMock(spec=SDAClient)
    mock_sda.base_url = "https://sdmdataaccess.nrcs.usda.gov/Tabular/post.rest"
    mock_sda.get_spatial_intersection.return_value = [
        {
            "mukey": "1",
            "musym": "A",
            "muname": "Test soil",
            "farmlndcl": "Prime farmland",
            "areasymbol": "IA169",
            "area_ac": 10.0,
        }
    ]
    mock_sda.get_productivity_ratings.return_value = [
        {"mukey": "1", "numeric_rating": 0.8, "is_rated": True}
    ]
    mock_sda.get_county_max_productivity_rating.return_value = 1.0

    result = _analyzer(mock_sda).analyze_polygon(GEOJSON, productivity_index=index)

    mock_sda.get_productivity_ratings.assert_called_once_with(mukeys=["1"], index_type=index)
    mock_sda.get_county_max_productivity_rating.assert_called_once_with(
        areasymbol="IA169", index_type=index
    )
    assert result.map_units[0].productivity_rating_source
    assert result.manifest["land_evaluation"]["rating_source_provenance"] == [
        PRODUCTIVITY_PROVENANCE[index]
    ]


BASELINE_UNITS = [
    {
        "mukey": "1",
        "musym": "A",
        "muname": "Clarion loam",
        "farmlndcl": "All areas are prime farmland",
        "areasymbol": "IA169",
        "area_ac": 10.0,
    },
    {
        "mukey": "2",
        "musym": "W",
        "muname": "Water",
        "farmlndcl": "Not prime farmland",
        "areasymbol": "IA169",
        "area_ac": 2.0,
    },
]
BASELINE_NCCPI_ROWS = [
    {
        "mukey": "1",
        "numeric_rating": 0.72,
        "rating_class": "High",
        "rated_pct": 85,
        "total_pct": 85,
    },
    {
        "mukey": "2",
        "numeric_rating": None,
        "rating_class": None,
        "rated_pct": 0,
        "total_pct": 100,
    },
]


def _baseline_sda(nccpi_rows=None, nccpi_error=None):
    sda = MagicMock(spec=SDAClient)
    sda.base_url = "https://sdmdataaccess.nrcs.usda.gov/Tabular/post.rest"
    sda.get_spatial_intersection.return_value = [dict(u) for u in BASELINE_UNITS]
    sda.get_productivity_ratings.return_value = [
        {"mukey": "1", "numeric_rating": 80.0, "rating_class": "80", "is_rated": True}
    ]
    sda.get_county_max_productivity_rating.return_value = 100.0
    if nccpi_error is not None:
        sda.get_interpretations.side_effect = nccpi_error
    else:
        sda.get_interpretations.return_value = [dict(r) for r in (nccpi_rows or [])]
    return sda


def _primary_view(result):
    units = [u.model_dump(exclude=set(NCCPI_BASELINE_FIELDS)) for u in result.map_units]
    return units, result.manifest["land_evaluation"], result.farmland_summary.model_dump()


@pytest.mark.parametrize("index", ["csr2", "cpi", "storie"])
def test_polygon_nccpi_baseline_populated_without_changing_primary(index):
    sda = _baseline_sda(BASELINE_NCCPI_ROWS)
    result = _analyzer(sda).analyze_polygon(GEOJSON, productivity_index=index)
    without = _analyzer(_baseline_sda([])).analyze_polygon(GEOJSON, productivity_index=index)

    sda.get_interpretations.assert_called_once()
    assert sda.get_interpretations.call_args.kwargs["rule_name"] == NCCPI_BASELINE_RULE
    unit = next(u for u in result.map_units if u.mukey == "1")
    assert unit.productivity_rating == 80.0
    assert unit.nccpi_baseline_rating == 0.72
    assert unit.nccpi_baseline_rating_class == "High"
    assert unit.nccpi_baseline_coverage_status == "rated"
    assert unit.nccpi_baseline_rated_pct == 85.0
    assert _primary_view(result) == _primary_view(without)


def test_polygon_nccpi_primary_baseline_reuses_primary_rows():
    sda = _baseline_sda(BASELINE_NCCPI_ROWS)
    result = _analyzer(sda).analyze_polygon(GEOJSON, productivity_index="nccpi")

    sda.get_interpretations.assert_called_once()
    for unit in result.map_units:
        assert unit.nccpi_baseline_rating == unit.productivity_rating
        assert unit.nccpi_baseline_rating_class == unit.productivity_rating_class
    assert next(u for u in result.map_units if u.mukey == "1").nccpi_baseline_rating == 0.72


def test_polygon_nccpi_baseline_null_for_misc_unit_and_empty_in_csv():
    result = _analyzer(_baseline_sda(BASELINE_NCCPI_ROWS)).analyze_polygon(
        GEOJSON, productivity_index="csr2"
    )
    water = next(u for u in result.map_units if u.mukey == "2")
    assert water.nccpi_baseline_rating is None
    assert water.nccpi_baseline_rating_class is None
    assert water.nccpi_baseline_coverage_status == "unrated"

    rows = {r["mukey"]: r for r in csv.DictReader(io.StringIO(result.tabular_csv))}
    assert rows["2"]["nccpi_baseline_rating"] == ""
    assert rows["2"]["nccpi_baseline_rating_class"] == ""
    assert rows["1"]["nccpi_baseline_rating"] == "0.72"
    assert rows["1"]["nccpi_baseline_rating_class"] == "High"


def test_polygon_nccpi_baseline_failure_adds_one_limitation_only():
    failed = _analyzer(_baseline_sda(nccpi_error=SDAClientError("SDA down"))).analyze_polygon(
        GEOJSON, productivity_index="csr2"
    )
    without = _analyzer(_baseline_sda([])).analyze_polygon(GEOJSON, productivity_index="csr2")

    baseline_lines = [m for m in failed.limitations if "NCCPI national baseline" in m]
    assert baseline_lines == ["NCCPI national baseline unavailable: SDA down"]
    assert [m for m in failed.limitations if m not in baseline_lines] == without.limitations
    assert all(u.nccpi_baseline_rating is None for u in failed.map_units)
    assert all(u.nccpi_baseline_coverage_status == "error" for u in failed.map_units)
    assert _primary_view(failed) == _primary_view(without)


def test_polygon_spatial_failure_reports_error_not_unmapped():
    sda = _baseline_sda(BASELINE_NCCPI_ROWS)
    sda.get_spatial_intersection.side_effect = SDAQueryError("SDA unavailable")
    result = _analyzer(sda).analyze_polygon(GEOJSON, productivity_index="csr2")

    assert result.coverage_status == "error"
    assert result.manifest["land_evaluation"]["coverage_status"] == "error"
    assert result.map_units == []
    assert any("SDA spatial query error: SDA unavailable" in m for m in result.limitations)


def test_polygon_rating_failure_keeps_mapping_and_reports_rating_error():
    ok = _analyzer(_baseline_sda(BASELINE_NCCPI_ROWS)).analyze_polygon(
        GEOJSON, productivity_index="csr2"
    )
    sda = _baseline_sda(BASELINE_NCCPI_ROWS)
    sda.get_productivity_ratings.side_effect = SDAQueryError("SDA unavailable")
    failed = _analyzer(sda).analyze_polygon(GEOJSON, productivity_index="csr2")

    assert failed.coverage_status == ok.coverage_status
    assert failed.coverage_status in {"covered", "partial"}
    assert failed.manifest["land_evaluation"]["coverage_status"] == "error"
    assert all(u.productivity_coverage_status == "error" for u in failed.map_units)
    assert any("Productivity rating warning (csr2)" in m for m in failed.limitations)


def test_polygon_nccpi_primary_failure_marks_baseline_error():
    sda = _baseline_sda(nccpi_error=SDAQueryError("SDA unavailable"))
    result = _analyzer(sda).analyze_polygon(GEOJSON, productivity_index="nccpi")

    assert result.manifest["land_evaluation"]["coverage_status"] == "error"
    assert result.map_units
    assert all(u.productivity_coverage_status == "error" for u in result.map_units)
    assert all(u.nccpi_baseline_coverage_status == "error" for u in result.map_units)


def test_polygon_unit_productivity_coverage_from_rating_row():
    result = _analyzer(_baseline_sda(BASELINE_NCCPI_ROWS)).analyze_polygon(
        GEOJSON, productivity_index="csr2"
    )
    statuses = {u.mukey: u.productivity_coverage_status for u in result.map_units}
    assert statuses["1"] == "rated"
    assert statuses["2"] == "unknown"


def test_polygon_invalid_geometry_reports_error():
    result = _analyzer(_baseline_sda()).analyze_polygon(
        {"type": "Polygon", "coordinates": [[[0, 0], [1, 1], [0, 0]]]}
    )
    assert result.coverage_status == "error"
    assert any(m.startswith("Geometry validation error:") for m in result.limitations)
