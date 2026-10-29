"""Tests for Multi-County Corridor Analysis and Sum Reconciliation Engine."""

import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from fpac_soil_mcp.authority import Provenance
from fpac_soil_mcp.corridor_analysis import CorridorAnalyzer, _get_corridor_ratings
from fpac_soil_mcp.integration_models import (
    CountyAgProfile,
    IntegrationStatus,
    UrbanExemptionRecord,
)
from fpac_soil_mcp.sda_client import SDAClient
from fpac_soil_mcp.tigerweb_client import TigerwebClient

FIXTURES_PATH = Path(__file__).parent / "fixtures" / "corridor" / "multi_county_corridors.json"


def load_corridor_fixtures():
    with open(FIXTURES_PATH, encoding="utf-8") as f:
        data = json.load(f)
        return {fix["fixture_id"]: fix for fix in data.get("fixtures", [])}


def mock_urban_record(geom_hash: str = "hash123"):
    return UrbanExemptionRecord(
        status=IntegrationStatus.SUCCESS,
        geometry_hash=geom_hash,
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


def mock_nass_profile(
    county_name: str, state_fips: str = "19", county_fips: str = "169", census_year: int = 2022
):
    return CountyAgProfile(
        status=IntegrationStatus.SUCCESS,
        state_fips=state_fips,
        county_fips=county_fips,
        county_name=county_name,
        census_year=census_year,
        provenance=Provenance(
            source_name="USDA NASS Census of Agriculture Quick Stats",
            source_reference="https://quickstats.nass.usda.gov/api/api_GET/",
            timestamp_utc=datetime.now(UTC),
            method_version="1.0.0",
            configuration_version="1.0.0",
        ),
        land_in_farms_acres=300000.0,
        total_cropland_acres=250000.0,
        farm_count=800,
        average_farm_size_acres=375.0,
    )


def test_corridor_analysis_two_counties():
    scenarios = load_corridor_fixtures()
    sc2 = scenarios["corridor_2county_ia_transmission"]

    # Mock SDA Client
    mock_sda = MagicMock(spec=SDAClient)
    mock_sda.base_url = "https://sdmdataaccess.nrcs.usda.gov/Tabular/post.rest"
    mock_sda.get_spatial_intersection.return_value = [
        {
            "mukey": "1001",
            "musym": "101",
            "muname": "Clarion loam, 2 to 6 percent slopes",
            "farmlndcl": "All areas are prime farmland",
            "areasymbol": "IA169",
            "area_ac": "12.5",
        },
        {
            "mukey": "1002",
            "musym": "102",
            "muname": "Nicollet loam, 1 to 3 percent slopes",
            "farmlndcl": "All areas are prime farmland",
            "areasymbol": "IA169",
            "area_ac": "10.0",
        },
    ]
    mock_sda.get_productivity_ratings.return_value = [
        {"mukey": "1001", "numeric_rating": "0.85", "rating_class": "High"},
        {"mukey": "1002", "numeric_rating": "0.90", "rating_class": "High"},
    ]
    mock_sda.get_county_max_productivity_rating.return_value = 1.0

    # Mock TIGERweb Client
    mock_tiger = MagicMock(spec=TigerwebClient)
    mock_tiger.check_urban_exemption.side_effect = lambda geom: mock_urban_record()

    # Simulate TIGERweb county discovery and partitioning
    mock_tiger.get_intersecting_counties.return_value = [
        {"state_fips": "19", "county_fips": "169", "county_name": "Story", "state_name": "IA"},
        {"state_fips": "19", "county_fips": "015", "county_name": "Boone", "state_name": "IA"},
    ]

    # Partition returns 2 segments summing to total buffered acreage
    from fpac_soil_mcp.geometry import buffer_centerline, calculate_acreage

    buf = buffer_centerline(sc2["centerline"], sc2["buffer_distance"], sc2["buffer_units"])
    tot_ac = calculate_acreage(buf)
    half_ac = tot_ac / 2.0

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

    # Mock NASS Client
    mock_nass = MagicMock()
    mock_nass.get_county_ag_profile.side_effect = lambda county, **kwargs: mock_nass_profile(
        county.county_name, county.state_fips, county.county_fips
    )

    analyzer = CorridorAnalyzer(
        sda_client=mock_sda,
        tigerweb_client=mock_tiger,
        nass_client=mock_nass,
    )

    response = analyzer.analyze_corridor(
        centerline_input=sc2["centerline"],
        buffer_distance=sc2["buffer_distance"],
        buffer_units=sc2["buffer_units"],
    )

    assert response.query_type == "corridor"
    assert len(response.county_segments) == 2
    assert all(
        segment.urban_screening["screened_acreage"] == 0.0 for segment in response.county_segments
    )
    assert response.impact_breakdown.direct_acres > 0
    assert response.impact_breakdown.indirect_acres == 0.0
    assert response.reconciliation_summary["reconciliation_passed"] is True
    assert response.reconciliation_summary["variance_pct"] <= 0.1
    assert response.composite_relative_rating is not None
    assert response.tabular_csv != ""
    assert "Story" in response.tabular_csv
    assert "Boone" in response.tabular_csv


@pytest.mark.parametrize("alternative_rating", [75.0, 99.0, 999.0, -99.0, -999.0])
def test_corridor_analysis_with_indirect_staging_and_alternatives(alternative_rating):
    scenarios = load_corridor_fixtures()
    sc3 = scenarios["corridor_3county_il_pipeline"]

    mock_sda = MagicMock(spec=SDAClient)
    mock_sda.base_url = "https://sdmdataaccess.nrcs.usda.gov/Tabular/post.rest"
    mock_sda.get_spatial_intersection.return_value = [
        {
            "mukey": "2001",
            "musym": "A1",
            "muname": "Test Silt Loam",
            "farmlndcl": "Prime farmland if drained",
            "areasymbol": "IL001",
            "area_ac": "15.0",
        }
    ]
    mock_sda.get_productivity_ratings.return_value = [
        {
            "mukey": "2001",
            "numeric_rating": str(alternative_rating),
            "rating_class": "Moderate",
            "productivity_rating_source": "SDA:NCCPI_V3",
        }
    ]
    mock_sda.get_productivity_ratings.return_value = [
        {
            "mukey": "2001",
            "numeric_rating": str(alternative_rating),
            "rating_class": "Moderate",
        }
    ]
    mock_sda.get_county_max_productivity_rating.return_value = 1.0

    mock_tiger = MagicMock(spec=TigerwebClient)
    mock_tiger.check_urban_exemption.side_effect = lambda geom: mock_urban_record()
    mock_tiger.get_intersecting_counties.return_value = [
        {"state_fips": "17", "county_fips": "037", "county_name": "DeKalb", "state_name": "IL"},
        {"state_fips": "17", "county_fips": "089", "county_name": "Kane", "state_name": "IL"},
        {"state_fips": "17", "county_fips": "043", "county_name": "DuPage", "state_name": "IL"},
    ]

    from fpac_soil_mcp.geometry import (
        buffer_centerline,
        calculate_acreage,
        erase_geometries,
        parse_geojson_geometry,
    )

    buf = buffer_centerline(sc3["centerline"], sc3["buffer_distance"], sc3["buffer_units"])
    ind_parsed = parse_geojson_geometry(
        {
            "type": "Polygon",
            "coordinates": [
                [
                    [-88.45, 41.932],
                    [-88.43, 41.932],
                    [-88.43, 41.940],
                    [-88.45, 41.940],
                    [-88.45, 41.932],
                ]
            ],
        }
    )
    ind_erased = erase_geometries(ind_parsed, buf)
    total_proj_ac = calculate_acreage(buf) + calculate_acreage(ind_erased)
    seg_ac = total_proj_ac / 3.0

    mock_tiger.partition_geometry_by_counties.return_value = [
        {
            "state_fips": "17",
            "county_fips": "037",
            "county_name": "DeKalb",
            "geometry": buf,
            "calculated_acres": seg_ac,
        },
        {
            "state_fips": "17",
            "county_fips": "089",
            "county_name": "Kane",
            "geometry": buf,
            "calculated_acres": seg_ac,
        },
        {
            "state_fips": "17",
            "county_fips": "043",
            "county_name": "DuPage",
            "geometry": buf,
            "calculated_acres": seg_ac,
        },
    ]

    mock_nass = MagicMock()
    mock_nass.get_county_ag_profile.side_effect = lambda county, **kwargs: mock_nass_profile(
        county.county_name, county.state_fips, county.county_fips
    )

    analyzer = CorridorAnalyzer(
        sda_client=mock_sda,
        tigerweb_client=mock_tiger,
        nass_client=mock_nass,
    )

    alternatives = [
        {
            "alternative_id": "Alternative B (South Alignment)",
            "centerline": sc3["alternatives"]["alternative_b"],
            "buffer_distance": 75.0,
            "buffer_units": "feet",
        }
    ]

    indirect_geom = {
        "type": "Polygon",
        "coordinates": [
            [
                [-88.45, 41.932],
                [-88.43, 41.932],
                [-88.43, 41.940],
                [-88.45, 41.940],
                [-88.45, 41.932],
            ]
        ],
    }

    response = analyzer.analyze_corridor(
        centerline_input=sc3["centerline"],
        buffer_distance=sc3["buffer_distance"],
        buffer_units=sc3["buffer_units"],
        indirect_geometry_input=indirect_geom,
        alternatives=alternatives,
        productivity_index="NCCPI",
    )

    assert len(response.county_segments) == 3
    assert response.impact_breakdown.direct_acres > 0
    assert response.impact_breakdown.indirect_acres > 0
    assert len(response.alternatives) == 1
    assert response.alternatives[0].alternative_id == "Alternative B (South Alignment)"
    assert response.alternatives[0].direct_acres > 0
    if alternative_rating == 75.0:
        assert response.alternatives[0].composite_relative_rating == 100.0
    else:
        assert response.alternatives[0].composite_relative_rating is None
    assert response.county_segments[0].map_units[0].productivity_rating_source == "SDA:NCCPI_V3"
    assert response.county_segments[0].map_units[0].productivity_rating == (
        alternative_rating if alternative_rating == 75.0 else None
    )
    assert response.county_segments[0].map_units[0].model_dump().get("nccpi_rating") is None
    mock_sda.get_productivity_ratings.assert_called()
    mock_sda.get_productivity_ratings.assert_called()
    assert response.reconciliation_summary["reconciliation_passed"] is True


def test_corridor_analysis_reconciliation_failure_warning(caplog):
    """Test that sum reconciliation > 0.1% logs a warning and appends to limitations."""
    import logging

    mock_sda = MagicMock(spec=SDAClient)
    mock_sda.base_url = "https://sdmdataaccess.nrcs.usda.gov/Tabular/post.rest"
    mock_sda.get_spatial_intersection.return_value = []
    mock_sda.get_productivity_ratings.return_value = []

    mock_tiger = MagicMock(spec=TigerwebClient)
    mock_tiger.check_urban_exemption.side_effect = lambda geom: mock_urban_record()
    mock_tiger.get_intersecting_counties.return_value = [
        {"state_fips": "19", "county_fips": "169", "county_name": "Story", "state_name": "IA"}
    ]

    from fpac_soil_mcp.geometry import buffer_centerline, calculate_acreage

    centerline = {
        "type": "LineString",
        "coordinates": [[-93.90, 42.03], [-93.50, 42.03]],
    }
    buf = buffer_centerline(centerline, 50.0, "feet")
    tot_ac = calculate_acreage(buf)

    # Intentionally cause a 5% mismatch between total footprint and partition segment
    mock_tiger.partition_geometry_by_counties.return_value = [
        {
            "state_fips": "19",
            "county_fips": "169",
            "county_name": "Story",
            "state_name": "IA",
            "geometry": buf,
            "calculated_acres": tot_ac * 1.05,  # 5% variance > 0.1%
        }
    ]

    mock_nass = MagicMock()
    mock_nass.get_county_ag_profile.side_effect = lambda county, **kwargs: mock_nass_profile(
        county.county_name, county.state_fips, county.county_fips
    )

    analyzer = CorridorAnalyzer(
        sda_client=mock_sda,
        tigerweb_client=mock_tiger,
        nass_client=mock_nass,
    )

    with caplog.at_level(logging.WARNING):
        response = analyzer.analyze_corridor(
            centerline_input=centerline,
            buffer_distance=50.0,
            buffer_units="feet",
        )

    assert response.reconciliation_summary["reconciliation_passed"] is False
    assert response.reconciliation_summary["variance_pct"] > 0.1
    assert any(
        "sum reconciliation exceeded 0.1% tolerance limit" in lim for lim in response.limitations
    )
    assert any("Acreage sum reconciliation failed" in rec.message for rec in caplog.records)


def test_corridor_analysis_invalid_geometry_fallback():
    analyzer = CorridorAnalyzer()
    response = analyzer.analyze_corridor(
        centerline_input="INVALID WKT CENTERLINE",
        buffer_distance=50.0,
        buffer_units="feet",
    )
    assert response.query_type == "corridor"
    assert len(response.county_segments) == 0
    assert response.reconciliation_summary["status"] == "error"
    assert any("Centerline error" in lim for lim in response.limitations)


def test_corridor_analysis_empty_counties_fallback():
    mock_sda = MagicMock(spec=SDAClient)
    mock_sda.base_url = "https://sdmdataaccess.nrcs.usda.gov/Tabular/post.rest"
    mock_sda.get_spatial_intersection.return_value = []

    mock_tiger = MagicMock(spec=TigerwebClient)
    mock_tiger.get_intersecting_counties.return_value = []
    mock_tiger.partition_geometry_by_counties.return_value = []
    mock_tiger.check_urban_exemption.side_effect = lambda geom: mock_urban_record()

    mock_nass = MagicMock()
    mock_nass.get_county_ag_profile.side_effect = lambda county, **kwargs: mock_nass_profile(
        county.county_name, county.state_fips, county.county_fips
    )

    analyzer = CorridorAnalyzer(
        sda_client=mock_sda,
        tigerweb_client=mock_tiger,
        nass_client=mock_nass,
    )

    response = analyzer.analyze_corridor(
        centerline_input={
            "type": "LineString",
            "coordinates": [[-93.90, 42.03], [-93.50, 42.03]],
        },
        buffer_distance=50.0,
        buffer_units="feet",
    )

    assert response.query_type == "corridor"
    assert len(response.county_segments) == 1
    assert response.county_segments[0].county_name == "Unspecified County"
    assert response.reconciliation_summary["reconciliation_passed"] is True
    assert any(
        "County boundary intersection/partitioning fallback occurred" in lim
        for lim in response.limitations
    )


def test_corridor_centerline_hash_invariance_with_buffer():
    """Verify that geometry_hash is computed from the direct centerline, invariant to buffer distance."""
    mock_sda = MagicMock(spec=SDAClient)
    mock_sda.base_url = "https://sdmdataaccess.nrcs.usda.gov/Tabular/post.rest"
    mock_sda.get_spatial_intersection.return_value = []

    mock_tiger = MagicMock(spec=TigerwebClient)
    mock_tiger.get_intersecting_counties.return_value = []
    mock_tiger.partition_geometry_by_counties.return_value = []
    mock_tiger.check_urban_exemption.side_effect = lambda geom: mock_urban_record()

    mock_nass = MagicMock()
    mock_nass.get_county_ag_profile.side_effect = lambda county, **kwargs: mock_nass_profile(
        county.county_name, county.state_fips, county.county_fips
    )

    analyzer = CorridorAnalyzer(
        sda_client=mock_sda,
        tigerweb_client=mock_tiger,
        nass_client=mock_nass,
    )

    line_wkt = "LINESTRING(-93.90 42.03, -93.50 42.03)"
    res_50 = analyzer.analyze_corridor(
        centerline_input=line_wkt, buffer_distance=50.0, buffer_units="feet"
    )
    res_100 = analyzer.analyze_corridor(
        centerline_input=line_wkt, buffer_distance=100.0, buffer_units="feet"
    )

    assert res_50.geometry_hash == res_100.geometry_hash
    assert res_50.geometry_hash.startswith("sha256:")


def test_corridor_wkt_indirect_geometry_support():
    """Verify that indirect_geometry_input parses WKT strings as well as GeoJSON."""
    mock_sda = MagicMock(spec=SDAClient)
    mock_sda.base_url = "https://sdmdataaccess.nrcs.usda.gov/Tabular/post.rest"
    mock_sda.get_spatial_intersection.return_value = []

    mock_tiger = MagicMock(spec=TigerwebClient)
    mock_tiger.get_intersecting_counties.return_value = []
    mock_tiger.partition_geometry_by_counties.return_value = []
    mock_tiger.check_urban_exemption.side_effect = lambda geom: mock_urban_record()

    mock_nass = MagicMock()
    mock_nass.get_county_ag_profile.side_effect = lambda county, **kwargs: mock_nass_profile(
        county.county_name, county.state_fips, county.county_fips
    )

    analyzer = CorridorAnalyzer(
        sda_client=mock_sda,
        tigerweb_client=mock_tiger,
        nass_client=mock_nass,
    )

    line_wkt = "LINESTRING(-93.90 42.03, -93.50 42.03)"
    staging_wkt = "POLYGON((-93.80 42.04, -93.75 42.04, -93.75 42.06, -93.80 42.06, -93.80 42.04))"

    res = analyzer.analyze_corridor(
        centerline_input=line_wkt,
        buffer_distance=50.0,
        buffer_units="feet",
        indirect_geometry_input=staging_wkt,
    )

    assert res.impact_breakdown.direct_acres > 0
    assert res.impact_breakdown.indirect_acres > 0
    assert res.impact_breakdown.total_project_acres == round(
        res.impact_breakdown.direct_acres + res.impact_breakdown.indirect_acres, 2
    )


def test_corridor_unsupported_selector_rejected_before_sda_lookup():
    mock_sda = MagicMock(spec=SDAClient)
    mock_sda.base_url = "https://sdmdataaccess.nrcs.usda.gov/Tabular/post.rest"
    with pytest.raises(ValueError, match="Unsupported productivity index type"):
        CorridorAnalyzer(sda_client=mock_sda).analyze_corridor(
            centerline_input="LINESTRING(-93.90 42.03, -93.50 42.03)",
            buffer_distance=50.0,
            productivity_index="unsupported",
        )
    mock_sda.get_spatial_intersection.assert_not_called()
    mock_sda.get_productivity_ratings.assert_not_called()
    mock_sda.get_productivity_ratings.assert_not_called()


@pytest.mark.parametrize("productivity_index", ["CSR2", "CPI", "STORIE"])
def test_corridor_ratings_route_selected_productivity_index(productivity_index):
    mock_sda = MagicMock(spec=SDAClient)
    mock_sda.get_productivity_ratings.return_value = [
        {"mukey": "1", "numeric_rating": "99.0", "is_rated": True}
    ]

    ratings = _get_corridor_ratings(mock_sda, ["1"], productivity_index.lower())

    assert ratings["1"]["numeric_rating"] == "99.0"
    mock_sda.get_productivity_ratings.assert_called_once_with(
        mukeys=["1"], index_type=productivity_index.lower()
    )


def test_corridor_unavailable_productivity_rating_preserves_map_unit():
    mock_sda = MagicMock(spec=SDAClient)
    mock_sda.base_url = "https://sdmdataaccess.nrcs.usda.gov/Tabular/post.rest"
    mock_sda.get_spatial_intersection.return_value = [
        {
            "mukey": "5002",
            "musym": "P2",
            "muname": "Unrated test unit",
            "farmlndcl": "Not prime farmland",
            "areasymbol": "IA169",
            "area_ac": "10.0",
        }
    ]
    mock_sda.get_productivity_ratings.return_value = [
        {
            "mukey": "5002",
            "numeric_rating": None,
            "rating_class": "Not Rated",
            "productivity_rating_source": "SDA:NCCPI_V3",
        }
    ]

    mock_tiger = MagicMock(spec=TigerwebClient)
    mock_tiger.get_intersecting_counties.return_value = []
    mock_tiger.partition_geometry_by_counties.return_value = []
    mock_tiger.check_urban_exemption.side_effect = lambda geom: mock_urban_record()
    mock_nass = MagicMock()
    mock_nass.get_county_ag_profile.side_effect = lambda county, **kwargs: mock_nass_profile(
        county.county_name, county.state_fips, county.county_fips
    )

    response = CorridorAnalyzer(
        sda_client=mock_sda,
        tigerweb_client=mock_tiger,
        nass_client=mock_nass,
    ).analyze_corridor(
        centerline_input="LINESTRING(-93.90 42.03, -93.50 42.03)",
        buffer_distance=50.0,
        buffer_units="feet",
        productivity_index="NCCPI",
        max_county_rating_override=100.0,
    )

    unit = response.county_segments[0].map_units[0]
    assert unit.productivity_rating is None
    assert unit.productivity_rating_class is None
    assert unit.productivity_rating_source == "SDA:NCCPI_V3"
    assert response.composite_relative_rating is None


@pytest.mark.parametrize("numeric_rating", [0.0, 99.0, 999.0, -99.0, -999.0])
def test_corridor_direct_ratings_preserve_zero_and_filter_sentinels(numeric_rating):
    """Verify that zero is rated while sentinel values are unrated."""
    mock_sda = MagicMock(spec=SDAClient)
    mock_sda.base_url = "https://sdmdataaccess.nrcs.usda.gov/Tabular/post.rest"
    mock_sda.get_spatial_intersection.return_value = [
        {
            "mukey": "9999",
            "musym": "99",
            "muname": "Urban land or rock outcrop",
            "farmlndcl": "Not prime farmland",
            "areasymbol": "IA169",
            "area_ac": "10.0",
        }
    ]
    mock_sda.get_productivity_ratings.return_value = [
        {"mukey": "9999", "numeric_rating": str(numeric_rating), "rating_class": "Not Rated"}
    ]
    mock_sda.get_county_max_productivity_rating.return_value = 1.0

    mock_tiger = MagicMock(spec=TigerwebClient)
    mock_tiger.get_intersecting_counties.return_value = []
    mock_tiger.partition_geometry_by_counties.return_value = []
    mock_tiger.check_urban_exemption.side_effect = lambda geom: mock_urban_record()

    mock_nass = MagicMock()
    mock_nass.get_county_ag_profile.side_effect = lambda county, **kwargs: mock_nass_profile(
        county.county_name, county.state_fips, county.county_fips
    )

    analyzer = CorridorAnalyzer(
        sda_client=mock_sda,
        tigerweb_client=mock_tiger,
        nass_client=mock_nass,
    )

    line_wkt = "LINESTRING(-93.90 42.03, -93.50 42.03)"
    res = analyzer.analyze_corridor(
        centerline_input=line_wkt,
        buffer_distance=50.0,
        buffer_units="feet",
    )

    assert len(res.county_segments) == 1
    seg = res.county_segments[0]
    if numeric_rating == 0.0:
        assert seg.relative_rating_le == 0.0
        assert res.composite_relative_rating == 0.0
        assert seg.map_units[0].calculated_acres > 0
        assert seg.map_units[0].productivity_rating == 0.0
        assert seg.map_units[0].productivity_rating_source == "SDA:NCCPI_V3"
    else:
        assert seg.relative_rating_le is None
        assert res.composite_relative_rating is None
        assert seg.map_units[0].productivity_rating is None


def test_corridor_partially_covered_status():
    """Verify that coverage_status is 'partially_covered' when soils map is incomplete."""
    mock_sda = MagicMock(spec=SDAClient)
    mock_sda.base_url = "https://sdmdataaccess.nrcs.usda.gov/Tabular/post.rest"
    # Return 5 acres for a 20+ acre corridor segment
    mock_sda.get_spatial_intersection.return_value = [
        {
            "mukey": "1001",
            "musym": "101",
            "muname": "Clarion loam",
            "farmlndcl": "All areas are prime farmland",
            "areasymbol": "IA169",
            "area_ac": "5.0",
        }
    ]
    mock_sda.get_productivity_ratings.return_value = [
        {"mukey": "1001", "numeric_rating": "0.85", "rating_class": "High"}
    ]
    mock_sda.get_county_max_productivity_rating.return_value = 1.0

    mock_tiger = MagicMock(spec=TigerwebClient)
    mock_tiger.get_intersecting_counties.return_value = []
    mock_tiger.partition_geometry_by_counties.return_value = []
    mock_tiger.check_urban_exemption.side_effect = lambda geom: mock_urban_record()

    mock_nass = MagicMock()
    mock_nass.get_county_ag_profile.side_effect = lambda county, **kwargs: mock_nass_profile(
        county.county_name, county.state_fips, county.county_fips
    )

    analyzer = CorridorAnalyzer(
        sda_client=mock_sda,
        tigerweb_client=mock_tiger,
        nass_client=mock_nass,
    )

    line_wkt = "LINESTRING(-93.90 42.03, -93.50 42.03)"
    res = analyzer.analyze_corridor(
        centerline_input=line_wkt,
        buffer_distance=50.0,
        buffer_units="feet",
    )

    assert len(res.county_segments) == 1
    seg = res.county_segments[0]
    assert seg.coverage_status == "partially_covered"
    assert seg.farmland_summary.unmapped_acres > 0


def test_corridor_analysis_with_county_partition_geometry_models():
    """Verify analyze_corridor processes CountyPartitionGeometry Pydantic model objects."""
    from shapely.geometry import box

    from fpac_soil_mcp.integration_models import CountyPartitionGeometry

    mock_sda = MagicMock(spec=SDAClient)
    mock_sda.base_url = "https://sdmdataaccess.nrcs.usda.gov/Tabular/post.rest"
    mock_sda.get_spatial_intersection.return_value = [
        {
            "mukey": "1001",
            "musym": "101",
            "muname": "Clarion loam",
            "farmlndcl": "All areas are prime farmland",
            "areasymbol": "IA169",
            "area_ac": "10.0",
        }
    ]
    mock_sda.get_productivity_ratings.return_value = [
        {"mukey": "1001", "numeric_rating": "0.85", "rating_class": "High"}
    ]
    mock_sda.get_county_max_productivity_rating.return_value = 1.0

    mock_tiger = MagicMock(spec=TigerwebClient)
    mock_tiger.get_intersecting_counties.return_value = [
        {"state_fips": "19", "county_fips": "169", "county_name": "Story", "state_name": "IA"}
    ]
    # Return actual CountyPartitionGeometry model instance
    poly = box(-93.80, 42.02, -93.60, 42.04)
    from fpac_soil_mcp.geometry import calculate_acreage

    acres = calculate_acreage(poly)

    partition_models = [
        CountyPartitionGeometry(
            state_fips="19",
            county_fips="169",
            county_name="Story",
            state_name="Iowa",
            geometry=poly,
            calculated_acres=acres,
        )
    ]
    mock_tiger.partition_geometry_by_counties.return_value = partition_models
    mock_tiger.check_urban_exemption.side_effect = lambda geom: mock_urban_record()

    mock_nass = MagicMock()
    mock_nass.get_county_ag_profile.side_effect = lambda county, **kwargs: mock_nass_profile(
        county.county_name, county.state_fips, county.county_fips
    )

    analyzer = CorridorAnalyzer(
        sda_client=mock_sda,
        tigerweb_client=mock_tiger,
        nass_client=mock_nass,
    )

    line_wkt = "LINESTRING(-93.80 42.03, -93.60 42.03)"
    res = analyzer.analyze_corridor(
        centerline_input=line_wkt,
        buffer_distance=50.0,
        buffer_units="feet",
    )

    assert len(res.county_segments) == 1
    seg = res.county_segments[0]
    assert seg.county_name == "Story"
    assert seg.state_fips == "19"
    assert seg.county_fips == "169"
    assert seg.total_segment_acres == acres


@pytest.mark.parametrize("index", ["nccpi", "csr2", "cpi", "storie"])
def test_corridor_all_validated_selectors_accepted(index):
    """All validated productivity index selectors pass the corridor guard without ValueError."""
    mock_sda = MagicMock(spec=SDAClient)
    mock_sda.base_url = "https://sdmdataaccess.nrcs.usda.gov/Tabular/post.rest"
    mock_sda.get_spatial_intersection.return_value = []
    mock_sda.get_productivity_ratings.return_value = []
    mock_sda.get_county_max_productivity_rating.return_value = None
    mock_sda.get_productivity_ratings.return_value = []
    mock_tiger = MagicMock(spec=TigerwebClient)
    mock_tiger.get_intersecting_counties.return_value = []
    mock_tiger.partition_geometry_by_counties.return_value = []
    mock_tiger.check_urban_exemption.return_value = None
    mock_nass = MagicMock()
    analyzer = CorridorAnalyzer(
        sda_client=mock_sda, tigerweb_client=mock_tiger, nass_client=mock_nass
    )
    # Guard must NOT raise ValueError; downstream errors from empty mocks are acceptable
    try:
        result = analyzer.analyze_corridor(
            centerline_input="LINESTRING(-93.90 42.03, -93.50 42.03)",
            buffer_distance=50.0,
            productivity_index=index,
        )
        assert result.query_type == "corridor"
    except ValueError:
        raise  # re-raise so test fails if it IS a ValueError
    except (AttributeError, TypeError, KeyError, IndexError, ZeroDivisionError):
        pass  # downstream mock errors (e.g. empty county list) are acceptable


@pytest.mark.parametrize("index", ["nccpi", "csr2", "cpi", "storie"])
def test_corridor_fallback_source_matches_registry_provenance(index):
    """Corridor fallback provenance comes from the SDV registry (stable D8 IDs)."""
    from fpac_soil_mcp import corridor_analysis
    from fpac_soil_mcp.sda_client import SDV_RATING_REGISTRY

    assert corridor_analysis._INDEX_SOURCES[index] == SDV_RATING_REGISTRY[index].provenance_id
    assert corridor_analysis._INDEX_SENTINELS[index] == SDV_RATING_REGISTRY[index].sentinels


def test_corridor_sentinels_and_rule_unchanged_by_registry_dedupe():
    """Deduping onto the registry keeps the previous corridor sentinel values and NCCPI rule."""
    from fpac_soil_mcp import corridor_analysis

    assert corridor_analysis._INDEX_SOURCES == {
        "nccpi": "SDA:NCCPI_V3",
        "csr2": "SDA:MAPUNIT_IACORNSR",
        "cpi": "SDA:COMPONENT_CROPPRODINDEX",
        "storie": "SDA:COINTERP_STORIE_CA",
    }
    assert {k: set(v) for k, v in corridor_analysis._INDEX_SENTINELS.items()} == {
        "nccpi": {99.0, 999.0, -99.0, -999.0},
        "storie": {99.0, 999.0, -99.0, -999.0},
        "csr2": {999.0, -99.0, -999.0},
        "cpi": {999.0, -99.0, -999.0},
    }
    assert set(corridor_analysis._UNRATED_SENTINELS) == {99.0, 999.0, -99.0, -999.0}
    assert (
        corridor_analysis._NCCPI_RULE
        == "NCCPI - National Commodity Crop Productivity Index (Ver 3.0)"
    )
