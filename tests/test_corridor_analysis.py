"""Tests for Multi-County Corridor Analysis and Sum Reconciliation Engine."""

import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

from fpac_soil_mcp.authority import Provenance
from fpac_soil_mcp.corridor_analysis import CorridorAnalyzer
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


def mock_nass_profile(county_name: str, state_fips: str = "19", county_fips: str = "169"):
    return CountyAgProfile(
        status=IntegrationStatus.SUCCESS,
        state_fips=state_fips,
        county_fips=county_fips,
        county_name=county_name,
        census_year=2022,
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
    mock_sda.get_interpretations.return_value = [
        {"mukey": "1001", "numeric_rating": "0.85", "rating_class": "High"},
        {"mukey": "1002", "numeric_rating": "0.90", "rating_class": "High"},
    ]

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
    mock_nass.get_county_ag_profile.side_effect = lambda state_fips, county_fips, county_name: (
        mock_nass_profile(county_name, state_fips, county_fips)
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
    assert response.impact_breakdown.direct_acres > 0
    assert response.impact_breakdown.indirect_acres == 0.0
    assert response.reconciliation_summary["reconciliation_passed"] is True
    assert response.reconciliation_summary["variance_pct"] <= 0.1
    assert response.composite_relative_rating is not None
    assert response.tabular_csv != ""
    assert "Story" in response.tabular_csv
    assert "Boone" in response.tabular_csv


def test_corridor_analysis_with_indirect_staging_and_alternatives():
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
    mock_sda.get_interpretations.return_value = [
        {"mukey": "2001", "numeric_rating": "0.75", "rating_class": "Moderate"}
    ]

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
    mock_nass.get_county_ag_profile.side_effect = lambda state_fips, county_fips, county_name: (
        mock_nass_profile(county_name, state_fips, county_fips)
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
    )

    assert len(response.county_segments) == 3
    assert response.impact_breakdown.direct_acres > 0
    assert response.impact_breakdown.indirect_acres > 0
    assert len(response.alternatives) == 1
    assert response.alternatives[0].alternative_id == "Alternative B (South Alignment)"
    assert response.alternatives[0].direct_acres > 0
    assert response.reconciliation_summary["reconciliation_passed"] is True


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
    mock_nass.get_county_ag_profile.side_effect = lambda state_fips, county_fips, county_name: (
        mock_nass_profile(county_name, state_fips, county_fips)
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
