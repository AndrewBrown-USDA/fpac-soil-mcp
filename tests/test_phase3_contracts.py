"""End-to-end integration and contract tests for Phase 3 Multi-County Corridor Analysis & FPPA Form NRCS-CPA-106 Rules."""

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

import httpx
import pytest
from fastmcp import FastMCP

from fpac_soil_mcp.authority import Provenance
from fpac_soil_mcp.config import settings
from fpac_soil_mcp.corridor_analysis import CorridorAnalyzer
from fpac_soil_mcp.corridor_scoring import (
    evaluate_corridor_lesa,
    evaluate_corridor_site_assessment,
)
from fpac_soil_mcp.geometry import (
    buffer_centerline,
    calculate_acreage,
    erase_geometries,
    parse_geojson_geometry,
)
from fpac_soil_mcp.integration_models import (
    CountyAgProfile,
    IntegrationStatus,
    UrbanExemptionRecord,
)
from fpac_soil_mcp.lesa import evaluate_site_assessment
from fpac_soil_mcp.models import (
    CorridorCountySegment,
    CorridorFarmlandAnalysisResponse,
)
from fpac_soil_mcp.nass_client import NassClient
from fpac_soil_mcp.sda_client import SDAClient
from fpac_soil_mcp.tigerweb_client import TigerwebClient
from fpac_soil_mcp.tools import register_tools
from fpac_soil_mcp.tools.spatial_analysis_tools import analyze_corridor_fppa

FIXTURES_PATH = Path(__file__).parent / "fixtures" / "corridor" / "multi_county_corridors.json"


def test_corridor_geometry_and_area_reconciliation_contract():
    """Verify geodesic buffering, indirect erasing, and area sum reconciliation."""
    centerline = {
        "type": "LineString",
        "coordinates": [[-93.65, 42.0], [-93.60, 42.0], [-93.55, 42.0]],
    }
    direct_geom = buffer_centerline(centerline, buffer_distance=100.0, distance_unit="feet")
    direct_acres = calculate_acreage(direct_geom)
    assert direct_acres > 0.0

    indirect_poly = {
        "type": "Polygon",
        "coordinates": [
            [
                [-93.62, 41.999],
                [-93.58, 41.999],
                [-93.58, 42.001],
                [-93.62, 42.001],
                [-93.62, 41.999],
            ]
        ],
    }
    indirect_geom = parse_geojson_geometry(indirect_poly)
    indirect_erased = erase_geometries(indirect_geom, direct_geom)
    indirect_acres = calculate_acreage(indirect_erased)
    assert indirect_acres >= 0.0

    total_footprint_acres = direct_acres + indirect_acres
    assert total_footprint_acres >= direct_acres


def test_phase3_multi_county_corridor_analyzer_contract():
    """End-to-end contract for CorridorAnalyzer with county partitioning, SDA queries, and NASS baselines."""
    with open(FIXTURES_PATH, encoding="utf-8") as f:
        data = json.load(f)
        fixtures_map = {fix["fixture_id"]: fix for fix in data.get("fixtures", [])}

    sc2 = fixtures_map["corridor_2county_ia_transmission"]

    mock_sda = MagicMock(spec=SDAClient)
    mock_sda.base_url = "https://sdmdataaccess.nrcs.usda.gov/Tabular/post.rest"
    mock_sda.get_spatial_intersection.return_value = [
        {
            "mukey": "1001",
            "musym": "138B",
            "muname": "Clarion loam",
            "farmlndcl": "All areas are prime farmland",
            "areasymbol": "IA169",
            "area_ac": "12.5",
        },
        {
            "mukey": "1002",
            "musym": "507",
            "muname": "Canisteo clay loam",
            "farmlndcl": "Prime farmland if drained",
            "areasymbol": "IA169",
            "area_ac": "7.5",
        },
    ]
    mock_sda.get_interpretations.return_value = [
        {"mukey": "1001", "numeric_rating": "0.88", "rating_class": "High"},
        {"mukey": "1002", "numeric_rating": "0.82", "rating_class": "High"},
    ]
    mock_sda.get_county_max_productivity_rating.return_value = 1.0

    mock_tiger = MagicMock(spec=TigerwebClient)
    urban_record = UrbanExemptionRecord(
        status=IntegrationStatus.SUCCESS,
        geometry_hash="sha256:test1234",
        provenance=Provenance(
            source_name="US Census Bureau TIGERweb",
            source_reference="https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Urban/MapServer/0/query",
            timestamp_utc=datetime.now(UTC),
            method_version="1.0.0",
            configuration_version="1.0.0",
        ),
        is_urban_intersected=False,
        urban_area_names=[],
        screened_acreage=0.0,
    )
    mock_tiger.check_urban_exemption_with_geometries.return_value = (urban_record, [])

    buf = buffer_centerline(sc2["centerline"], sc2["buffer_distance"], sc2["buffer_units"])
    tot_ac = calculate_acreage(buf)
    half_ac = round(tot_ac / 2.0, 2)

    mock_tiger.partition_geometry_by_counties.return_value = [
        {
            "state_fips": "19",
            "county_fips": "169",
            "county_name": "Story",
            "state_name": "IA",
            "geometry": buf,
            "calculated_acres": half_ac,
        },
        {
            "state_fips": "19",
            "county_fips": "015",
            "county_name": "Boone",
            "state_name": "IA",
            "geometry": buf,
            "calculated_acres": half_ac,
        },
    ]

    mock_nass = MagicMock(spec=NassClient)
    mock_nass.get_county_ag_profile.side_effect = (
        lambda county=None, state_fips=None, county_fips=None, county_name=None, **kwargs: (
            CountyAgProfile(
                status=IntegrationStatus.SUCCESS,
                state_fips=county.state_fips if county else (state_fips or "19"),
                county_fips=county.county_fips if county else (county_fips or "169"),
                county_name=county.county_name if county else (county_name or "Story"),
                census_year=2022,
                provenance=Provenance(
                    source_name="USDA NASS QuickStats",
                    source_reference="https://quickstats.nass.usda.gov/api/api_GET/",
                    timestamp_utc=datetime.now(UTC),
                    method_version="1.0.0",
                    configuration_version="1.0.0",
                ),
                land_in_farms_acres=320000.0,
                total_cropland_acres=250000.0,
                farm_count=1100,
                average_farm_size_acres=263.0,
            )
        )
    )

    analyzer = CorridorAnalyzer(
        sda_client=mock_sda,
        tigerweb_client=mock_tiger,
        nass_client=mock_nass,
    )

    result = analyzer.analyze_corridor(
        centerline_input=sc2["centerline"],
        buffer_distance=sc2["buffer_distance"],
        buffer_units=sc2["buffer_units"],
        include_nccpi=True,
    )

    assert isinstance(result, CorridorFarmlandAnalysisResponse)
    assert result.query_type == "corridor"
    assert result.geometry_hash.startswith("sha256:")
    assert len(result.county_segments) == 2
    assert result.composite_relative_rating is not None
    assert result.composite_relative_rating > 0.0
    assert result.reconciliation_summary["reconciliation_passed"] is True
    assert result.reconciliation_summary["variance_pct"] <= 0.1
    assert result.impact_breakdown.direct_acres > 0.0

    for seg in result.county_segments:
        assert isinstance(seg, CorridorCountySegment)
        assert seg.county_fips != ""
        assert seg.relative_rating_le is not None
        assert seg.total_segment_acres > 0.0
        assert seg.farmland_summary.total_fppa_protected_acres > 0.0
        assert seg.nass_profile["status"] == "success"
        assert seg.nass_profile["land_in_farms_acres"] == 320000.0


def test_contract_corridor_wkt_indirect_geometry_hashing_and_partial_coverage():
    """Verify WKT indirect geometry parsing, centerline invariant hashing, and partial coverage status in end-to-end corridor screening."""
    mock_sda = MagicMock(spec=SDAClient)
    mock_sda.base_url = "https://sdmdataaccess.nrcs.usda.gov/Tabular/post.rest"
    # Return 15.0 acres mapped out of 20.0 acres segment -> partial coverage
    mock_sda.get_spatial_intersection.return_value = [
        {
            "mukey": "2001",
            "musym": "101",
            "muname": "Clarion loam",
            "farmlndcl": "All areas are prime farmland",
            "areasymbol": "IA169",
            "area_ac": "15.0",
        }
    ]
    mock_sda.get_interpretations.return_value = [
        {"mukey": "2001", "numeric_rating": "0.90", "rating_class": "High"}
    ]
    mock_sda.get_county_max_productivity_rating.return_value = 1.0

    mock_tiger = MagicMock(spec=TigerwebClient)
    urban_record = UrbanExemptionRecord(
        status=IntegrationStatus.SUCCESS,
        geometry_hash="sha256:wkt123",
        provenance=Provenance(
            source_name="US Census Bureau TIGERweb",
            source_reference="https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Urban/MapServer/0/query",
            timestamp_utc=datetime.now(UTC),
            method_version="1.0.0",
            configuration_version="1.0.0",
        ),
        is_urban_intersected=False,
        urban_area_names=[],
        screened_acreage=0.0,
    )
    mock_tiger.check_urban_exemption_with_geometries.return_value = (urban_record, [])
    mock_tiger.get_intersecting_counties.return_value = [
        {"state_fips": "19", "county_fips": "169", "county_name": "Story", "state_name": "IA"}
    ]

    from shapely import wkt as shapely_wkt

    from fpac_soil_mcp.geometry import (
        buffer_centerline,
        calculate_acreage,
        erase_geometries,
        validate_and_sanitize_line_wkt,
        validate_and_sanitize_polygon_wkt,
    )

    line_wkt = "LINESTRING(-93.65 42.0, -93.55 42.0)"
    indirect_wkt = "POLYGON((-93.62 41.99, -93.58 41.99, -93.58 42.01, -93.62 42.01, -93.62 41.99))"

    clean_line = validate_and_sanitize_line_wkt(line_wkt)
    clean_poly = validate_and_sanitize_polygon_wkt(indirect_wkt)
    direct_geom = buffer_centerline(shapely_wkt.loads(clean_line), 50.0, "feet")
    indirect_geom = shapely_wkt.loads(clean_poly)
    indirect_erased = erase_geometries(indirect_geom, direct_geom)

    direct_acres = calculate_acreage(direct_geom)
    indirect_acres = calculate_acreage(indirect_erased)
    total_acres = round(direct_acres + indirect_acres, 2)
    footprint = direct_geom.union(indirect_erased)

    mock_tiger.partition_geometry_by_counties.return_value = [
        {
            "state_fips": "19",
            "county_fips": "169",
            "county_name": "Story",
            "state_name": "IA",
            "geometry": footprint,
            "calculated_acres": total_acres,
        }
    ]

    mock_nass = MagicMock(spec=NassClient)
    mock_nass.get_county_ag_profile.return_value = CountyAgProfile(
        status=IntegrationStatus.SUCCESS,
        state_fips="19",
        county_fips="169",
        county_name="Story",
        census_year=2022,
        provenance=Provenance(
            source_name="USDA NASS",
            source_reference="https://quickstats.nass.usda.gov/api/api_GET/",
            timestamp_utc=datetime.now(UTC),
            method_version="1.0.0",
            configuration_version="1.0.0",
        ),
        land_in_farms_acres=300000.0,
        total_cropland_acres=250000.0,
        farm_count=1000,
        average_farm_size_acres=300.0,
    )

    analyzer = CorridorAnalyzer(
        sda_client=mock_sda,
        tigerweb_client=mock_tiger,
        nass_client=mock_nass,
    )

    # 1. Run with 50ft buffer
    res_50 = analyzer.analyze_corridor(
        centerline_input=line_wkt,
        buffer_distance=50.0,
        buffer_units="feet",
        indirect_geometry_input=indirect_wkt,
        include_nccpi=True,
    )

    # 2. Run with 100ft buffer to verify centerline hash invariance
    res_100 = analyzer.analyze_corridor(
        centerline_input=line_wkt,
        buffer_distance=100.0,
        buffer_units="feet",
        indirect_geometry_input=indirect_wkt,
        include_nccpi=True,
    )

    # Centerline hash invariance
    assert res_50.geometry_hash.startswith("sha256:")
    assert res_50.geometry_hash == res_100.geometry_hash

    # WKT indirect geometry parsed and incorporated into footprint
    assert res_50.impact_breakdown.direct_acres > 0.0
    assert res_50.impact_breakdown.indirect_acres > 0.0
    assert res_50.impact_breakdown.total_project_acres == total_acres

    # Partial coverage status detection when mapped acreage < total segment acreage
    assert len(res_50.county_segments) == 1
    segment = res_50.county_segments[0]
    assert segment.coverage_status == "partially_covered"
    assert segment.farmland_summary.prime_farmland_acres == 15.0
    assert segment.farmland_summary.unmapped_acres > 0.0


def test_statutory_7_cfr_658_5_c_rules_enforcement():
    """Verify CPA-106 site assessment rules under 7 CFR § 658.5(c)."""
    # 1. Rules check: criteria 5 and 6 must be 0, 8 and 11 max 25
    sa_res = evaluate_corridor_site_assessment(
        criteria_inputs={
            1: {"awarded_points": 15, "justification": "Rural area"},
            2: {"awarded_points": 10, "justification": "Surrounded by ag"},
            3: {"awarded_points": 20, "justification": "Substantial farm investments"},
            4: {"awarded_points": 10, "justification": "Ag infrastructure available"},
            5: {"awarded_points": 20, "justification": "Should be zeroed"},
            6: {"awarded_points": 15, "justification": "Should be zeroed"},
            7: {"awarded_points": 10, "justification": "Farm size ratio"},
            8: {"awarded_points": 25, "justification": "Severance impact"},
            9: {"awarded_points": 5, "justification": "Urban services not needed"},
            10: {"awarded_points": 10, "justification": "Alternative sites available"},
            11: {"awarded_points": 25, "justification": "Compatible with ag"},
            12: {"awarded_points": 10, "justification": "Consistent with local plan"},
        }
    )
    crit5 = next(c for c in sa_res.criteria if c.criterion_number == 5)
    assert crit5.awarded_points == 0.0
    assert crit5.is_statutorily_zeroed is True

    crit6 = next(c for c in sa_res.criteria if c.criterion_number == 6)
    assert crit6.awarded_points == 0.0
    assert crit6.is_statutorily_zeroed is True

    crit8 = next(c for c in sa_res.criteria if c.criterion_number == 8)
    assert crit8.awarded_points == 25.0
    assert crit8.max_points == 25

    crit11 = next(c for c in sa_res.criteria if c.criterion_number == 11)
    assert crit11.awarded_points == 25.0
    assert crit11.max_points == 25

    assert sa_res.total_sa_points <= 160.0

    # 2. Combined LESA evaluation with statutory threshold check
    lesa_res = evaluate_corridor_lesa(
        land_evaluation_score=85.0,
        site_assessment=sa_res,
    )
    assert lesa_res.land_evaluation_score == 85.0
    assert lesa_res.total_lesa_score == 85.0 + lesa_res.site_assessment.total_sa_points
    assert lesa_res.total_lesa_score <= 260.0
    assert lesa_res.threshold_exceeded == (lesa_res.total_lesa_score >= 160.0)


@pytest.mark.parametrize("project_type", ["site", "corridor"])
def test_criterion_2_contract_surface_for_site_and_corridor(project_type: str) -> None:
    """Verify Criterion 2 fields and threshold-adjacent point mapping."""
    measured = {
        "normalized_ratio": 0.9,
        "evidence_status": "measured",
        "rule_reference": "7 CFR § 658.5(b)/(c)",
        "rule_version": "criterion-2-v1",
        "source_provenance": ["USDA agricultural land-use survey"],
        "is_agricultural": True,
        "is_verified": True,
    }
    summary = evaluate_site_assessment(
        {2: {"perimeter_evidence": measured}},
        project_type=project_type,
    )
    criterion = next(item for item in summary.criteria if item.criterion_number == 2)
    assert criterion.awarded_points == 9.0
    assert criterion.normalized_ratio == 0.9
    assert criterion.evidence_status == "measured"
    assert criterion.rule_version == "criterion-2-v1"
    assert criterion.source_provenance == ["USDA agricultural land-use survey"]
    assert criterion.is_verified is True


def test_criterion_2_contract_preserves_zero_unavailable_and_override() -> None:
    """Measured zero, unavailable evidence, and overrides remain distinct."""
    measured_zero = evaluate_site_assessment(
        {
            2: {
                "perimeter_evidence": {
                    "normalized_ratio": 0.0,
                    "evidence_status": "measured",
                    "is_agricultural": True,
                    "is_verified": True,
                }
            }
        }
    )
    zero = next(item for item in measured_zero.criteria if item.criterion_number == 2)
    assert zero.awarded_points == 0.0
    assert zero.evidence_status == "measured"

    unavailable = evaluate_site_assessment(
        {2: {"perimeter_evidence": {"evidence_status": "unavailable"}}}
    )
    missing = next(item for item in unavailable.criteria if item.criterion_number == 2)
    assert missing.awarded_points == 0.0
    assert missing.normalized_ratio is None
    assert missing.evidence_status == "unavailable"
    assert missing.is_verified is False

    overridden = evaluate_site_assessment(
        {
            2: {
                "awarded_points": 4.0,
                "justification": "Documented project-specific override.",
                "perimeter_evidence": {
                    "normalized_ratio": 0.0,
                    "evidence_status": "measured",
                },
            }
        }
    )
    override = next(item for item in overridden.criteria if item.criterion_number == 2)
    assert override.awarded_points == 4.0
    assert override.normalized_ratio == 0.0


def test_criterion_2_contract_boundary_point_mapping() -> None:
    """Verify lower/upper ratio boundaries and threshold-adjacent values."""
    from fpac_soil_mcp.lesa import calculate_criterion_2_score

    assert calculate_criterion_2_score(0.0)[0] == 0.0
    assert calculate_criterion_2_score(0.2)[0] == 1.0
    assert calculate_criterion_2_score(0.9)[0] == 9.0
    assert calculate_criterion_2_score(0.9001)[0] == 10.0
    assert calculate_criterion_2_score(1.0)[0] == 10.0


def test_nass_graceful_fallback_contract(monkeypatch: pytest.MonkeyPatch):
    """Verify NASS client graceful degradation when disabled or unavailable."""
    monkeypatch.setattr(settings, "nass_enabled", True)

    # 1. When API key is empty / not configured
    client_unconfigured = NassClient(api_key="")
    profile_unconfigured = client_unconfigured.get_county_ag_profile(
        state_fips="19", county_fips="169", county_name="Story"
    )
    assert profile_unconfigured.status == IntegrationStatus.UNAVAILABLE
    assert profile_unconfigured.land_in_farms_acres is None

    # 2. When server returns error
    def error_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "NASS internal server error"})

    nass_client = NassClient(
        api_key="TEST_KEY",
        http_client=httpx.Client(transport=httpx.MockTransport(error_handler)),
    )
    profile_err = nass_client.get_county_ag_profile(
        state_fips="19", county_fips="169", county_name="Story"
    )
    assert profile_err.status == IntegrationStatus.ERROR
    assert profile_err.land_in_farms_acres is None


def test_fastmcp_analyze_corridor_fppa_tool_contract():
    """Verify FastMCP server tool registration and execution contract for analyze_corridor_fppa."""
    mcp = FastMCP("corridor-contract-test")
    register_tools(mcp)

    tools = asyncio.run(mcp.list_tools())
    tool_map = {t.name: t for t in tools}

    assert "analyze_corridor_fppa" in tool_map
    corridor_tool = tool_map["analyze_corridor_fppa"]
    params = corridor_tool.parameters["properties"]
    assert "centerline" in params
    assert "buffer_distance" in params
    assert "buffer_units" in params
    assert "indirect_geometry" in params
    assert "alternatives" in params
    assert "site_assessment_inputs" in params

    # Direct invocation of tool function with mock analyzer
    from unittest.mock import patch

    mock_resp = MagicMock()
    mock_resp.model_dump.return_value = {
        "query_type": "corridor",
        "geometry_hash": "sha256:123456",
        "buffer_distance": 50.0,
        "buffer_units": "feet",
        "composite_relative_rating": 82.5,
        "county_segments": [],
        "reconciliation_summary": {"reconciliation_passed": True},
    }
    mock_resp.composite_relative_rating = 82.5
    mock_resp.county_segments = []

    with patch("fpac_soil_mcp.tools.spatial_analysis_tools.CorridorAnalyzer") as mock_cls:
        mock_instance = MagicMock()
        mock_instance.analyze_corridor.return_value = mock_resp
        mock_cls.return_value = mock_instance

        centerline = {
            "type": "LineString",
            "coordinates": [[-93.65, 42.0], [-93.60, 42.0]],
        }
        result = analyze_corridor_fppa(
            centerline=centerline,
            buffer_distance=50.0,
            buffer_units="feet",
            site_assessment_inputs={
                "criteria_inputs": {"1": {"awarded_points": 10}},
            },
        )
        assert isinstance(result, dict)
        assert result["query_type"] == "corridor"
        assert "composite_relative_rating" in result
        assert "lesa_evaluation" in result
        assert result["lesa_evaluation"]["total_lesa_score"] >= 0


def test_contract_alternative_composite_le_scoring():
    """Verify alternative corridor alignments calculate composite LE scores across intersected county segments."""
    mock_sda = MagicMock(spec=SDAClient)
    mock_sda.base_url = "https://sdmdataaccess.nrcs.usda.gov/Tabular/post.rest"
    mock_sda.get_spatial_intersection.return_value = [
        {
            "mukey": "3001",
            "musym": "B1",
            "muname": "Highland Silt",
            "farmlndcl": "All areas are prime farmland",
            "areasymbol": "IA169",
            "area_ac": "10.0",
        }
    ]
    # Return 0.90 NCCPI rating -> LE score = 90.0
    mock_sda.get_interpretations.return_value = [
        {"mukey": "3001", "numeric_rating": "0.90", "rating_class": "High"}
    ]
    mock_sda.get_county_max_productivity_rating.return_value = 1.0

    mock_tiger = MagicMock(spec=TigerwebClient)
    urban_record = UrbanExemptionRecord(
        status=IntegrationStatus.SUCCESS,
        geometry_hash="sha256:alt123",
        provenance=Provenance(
            source_name="US Census Bureau TIGERweb",
            source_reference="https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Urban/MapServer/0/query",
            timestamp_utc=datetime.now(UTC),
            method_version="1.0.0",
            configuration_version="1.0.0",
        ),
        is_urban_intersected=False,
        urban_area_names=[],
        screened_acreage=0.0,
    )
    mock_tiger.check_urban_exemption_with_geometries.return_value = (urban_record, [])
    mock_tiger.get_intersecting_counties.return_value = [
        {"state_fips": "19", "county_fips": "169", "county_name": "Story", "state_name": "IA"}
    ]

    from fpac_soil_mcp.geometry import buffer_centerline, calculate_acreage

    alt_centerline = {
        "type": "LineString",
        "coordinates": [[-93.65, 42.0], [-93.55, 42.0]],
    }
    buf = buffer_centerline(alt_centerline, 60.0, "feet")
    tot_ac = calculate_acreage(buf)

    mock_tiger.partition_geometry_by_counties.return_value = [
        {
            "state_fips": "19",
            "county_fips": "169",
            "county_name": "Story",
            "state_name": "IA",
            "geometry": buf,
            "calculated_acres": tot_ac,
        }
    ]

    mock_nass = MagicMock(spec=NassClient)
    mock_nass.get_county_ag_profile.return_value = CountyAgProfile(
        status=IntegrationStatus.SUCCESS,
        state_fips="19",
        county_fips="169",
        county_name="Story",
        census_year=2022,
        provenance=Provenance(
            source_name="USDA NASS",
            source_reference="https://quickstats.nass.usda.gov/api/api_GET/",
            timestamp_utc=datetime.now(UTC),
            method_version="1.0.0",
            configuration_version="1.0.0",
        ),
        land_in_farms_acres=300000.0,
        total_cropland_acres=250000.0,
        farm_count=1000,
        average_farm_size_acres=300.0,
    )

    analyzer = CorridorAnalyzer(
        sda_client=mock_sda,
        tigerweb_client=mock_tiger,
        nass_client=mock_nass,
    )

    primary_centerline = {
        "type": "LineString",
        "coordinates": [[-93.70, 42.0], [-93.60, 42.0]],
    }

    alternatives = [
        {
            "alternative_id": "Alignment Option B",
            "centerline": alt_centerline,
            "buffer_distance": 60.0,
            "buffer_units": "feet",
        }
    ]

    res = analyzer.analyze_corridor(
        centerline_input=primary_centerline,
        buffer_distance=60.0,
        buffer_units="feet",
        alternatives=alternatives,
        include_nccpi=True,
    )

    assert len(res.alternatives) == 1
    alt = res.alternatives[0]
    assert alt.alternative_id == "Alignment Option B"
    assert alt.direct_acres > 0.0
    assert alt.composite_relative_rating == 90.0


def test_contract_multi_county_criterion_7_weighting():
    """Verify multi-county corridor Criterion 7 area-weighted farm size calculation across multiple county segments."""
    from unittest.mock import patch

    # County 1: 100 acres, avg farm size 200 acres
    seg1 = MagicMock(spec=CorridorCountySegment)
    seg1.total_segment_acres = 100.0
    seg1.nass_profile = {"average_farm_size_acres": 200.0}

    # County 2: 300 acres, avg farm size 400 acres
    seg2 = MagicMock(spec=CorridorCountySegment)
    seg2.total_segment_acres = 300.0
    seg2.nass_profile = {"average_farm_size_acres": 400.0}

    # Area-weighted average: (100*200 + 300*400) / (100+300) = (20000 + 120000) / 400 = 140000 / 400 = 350.0 acres
    mock_resp = MagicMock()
    mock_resp.model_dump.return_value = {
        "query_type": "corridor",
        "geometry_hash": "sha256:testmulti",
        "composite_relative_rating": 85.0,
        "county_segments": [seg1, seg2],
    }
    mock_resp.composite_relative_rating = 85.0
    mock_resp.county_segments = [seg1, seg2]

    with patch("fpac_soil_mcp.tools.spatial_analysis_tools.CorridorAnalyzer") as mock_cls:
        mock_instance = MagicMock()
        mock_instance.analyze_corridor.return_value = mock_resp
        mock_cls.return_value = mock_instance

        # Test with project farm size = 350.0 acres (100% of weighted average -> 10 points)
        res_full = analyze_corridor_fppa(
            centerline="LINESTRING(-93.65 42.0, -93.55 42.0)",
            buffer_distance=50.0,
            site_assessment_inputs={"project_farm_acres": 350.0},
        )
        lesa_full = res_full["lesa_evaluation"]
        crit7_full = next(
            c for c in lesa_full["site_assessment"]["criteria"] if c["criterion_number"] == 7
        )
        assert crit7_full["awarded_points"] == 10
        assert "350.0" in crit7_full["justification"]
        assert "100.0%" in crit7_full["justification"]

        # Test with project farm size = 175.0 acres (50% below weighted average -> 0 points)
        res_half = analyze_corridor_fppa(
            centerline="LINESTRING(-93.65 42.0, -93.55 42.0)",
            buffer_distance=50.0,
            site_assessment_inputs={"project_farm_acres": 175.0},
        )
        lesa_half = res_half["lesa_evaluation"]
        crit7_half = next(
            c for c in lesa_half["site_assessment"]["criteria"] if c["criterion_number"] == 7
        )
        assert crit7_half["awarded_points"] == 0.0
        assert "50.0%" in crit7_half["justification"]

        # Test with project farm size = 70.0 acres (20% of weighted average -> 0 points)
        res_small = analyze_corridor_fppa(
            centerline="LINESTRING(-93.65 42.0, -93.55 42.0)",
            buffer_distance=50.0,
            site_assessment_inputs={"project_farm_acres": 70.0},
        )
        lesa_small = res_small["lesa_evaluation"]
        crit7_small = next(
            c for c in lesa_small["site_assessment"]["criteria"] if c["criterion_number"] == 7
        )
        assert crit7_small["awarded_points"] == 0.0
        assert "20.0%" in crit7_small["justification"]


def test_contract_sum_reconciliation_warning_appended_to_limitations():
    """Verify sum reconciliation discrepancy warning is appended to limitations when acreage drifts >0.1%."""
    mock_sda = MagicMock(spec=SDAClient)
    mock_sda.base_url = "https://sdmdataaccess.nrcs.usda.gov/Tabular/post.rest"
    mock_sda.get_spatial_intersection.return_value = []
    mock_sda.get_interpretations.return_value = []

    mock_tiger = MagicMock(spec=TigerwebClient)
    urban_record = UrbanExemptionRecord(
        status=IntegrationStatus.SUCCESS,
        geometry_hash="sha256:recon123",
        provenance=Provenance(
            source_name="US Census Bureau TIGERweb",
            source_reference="https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Urban/MapServer/0/query",
            timestamp_utc=datetime.now(UTC),
            method_version="1.0.0",
            configuration_version="1.0.0",
        ),
        is_urban_intersected=False,
        urban_area_names=[],
        screened_acreage=0.0,
    )
    mock_tiger.check_urban_exemption_with_geometries.return_value = (urban_record, [])
    mock_tiger.get_intersecting_counties.return_value = [
        {"state_fips": "19", "county_fips": "169", "county_name": "Story", "state_name": "IA"}
    ]

    from fpac_soil_mcp.geometry import buffer_centerline, calculate_acreage

    centerline = {
        "type": "LineString",
        "coordinates": [[-93.65, 42.0], [-93.55, 42.0]],
    }
    buf = buffer_centerline(centerline, 50.0, "feet")
    tot_ac = calculate_acreage(buf)

    # Inject 2.5% acreage drift (> 0.1% tolerance) in partitioned county segment
    mock_tiger.partition_geometry_by_counties.return_value = [
        {
            "state_fips": "19",
            "county_fips": "169",
            "county_name": "Story",
            "state_name": "IA",
            "geometry": buf,
            "calculated_acres": tot_ac * 1.025,
        }
    ]

    mock_nass = MagicMock(spec=NassClient)
    mock_nass.get_county_ag_profile.return_value = CountyAgProfile(
        status=IntegrationStatus.SUCCESS,
        state_fips="19",
        county_fips="169",
        county_name="Story",
        census_year=2022,
        provenance=Provenance(
            source_name="USDA NASS",
            source_reference="https://quickstats.nass.usda.gov/api/api_GET/",
            timestamp_utc=datetime.now(UTC),
            method_version="1.0.0",
            configuration_version="1.0.0",
        ),
        land_in_farms_acres=300000.0,
        total_cropland_acres=250000.0,
        farm_count=1000,
        average_farm_size_acres=300.0,
    )

    analyzer = CorridorAnalyzer(
        sda_client=mock_sda,
        tigerweb_client=mock_tiger,
        nass_client=mock_nass,
    )

    response = analyzer.analyze_corridor(
        centerline_input=centerline,
        buffer_distance=50.0,
        buffer_units="feet",
    )

    assert response.reconciliation_summary["reconciliation_passed"] is False
    assert response.reconciliation_summary["variance_pct"] > 0.1
    assert any(
        "Acreage sum reconciliation exceeded 0.1% tolerance limit" in lim
        for lim in response.limitations
    )
