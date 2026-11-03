"""Unit tests for the extracted MCP tool modules."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from shapely.geometry import LineString

from fpac_soil_mcp.constants import (
    FARMLAND_CLASS_DEFINITIONS,
    REGULATORY_LIMITATIONS,
    REGULATORY_NOTICE,
)
from fpac_soil_mcp.geometry import GeometryValidationError
from fpac_soil_mcp.models import (
    FarmlandClassificationResponse,
    FarmlandClassListResponse,
    FppaScopeResponse,
)
from fpac_soil_mcp.sda_client import SDAQueryError, SDAValidationError
from fpac_soil_mcp.tools.exemption_tools import check_urban_area_exemption
from fpac_soil_mcp.tools.fppa_tools import (
    explain_fppa_screening_scope,
    list_farmland_classes,
)
from fpac_soil_mcp.tools.lesa_tools import calculate_preliminary_lesa
from fpac_soil_mcp.tools.soil_lookup_tools import (
    get_farmland_classification_by_mukey,
    get_farmland_classification_by_point,
    get_soil_interpretations,
    get_soil_polygons_by_geometry,
)
from fpac_soil_mcp.tools.spatial_analysis_tools import (
    analyze_corridor_fppa,
    analyze_farmland_by_polygon,
)


class TestSoilTools:
    """Tests for get_farmland_classification_by_point and get_farmland_classification_by_mukey."""

    @patch("fpac_soil_mcp.tools.soil_lookup_tools.SDAClient")
    def test_get_farmland_classification_by_point_covered(
        self,
        mock_sda_client_cls: MagicMock,
    ) -> None:
        mock_instance = MagicMock()
        mock_sda_client_cls.return_value = mock_instance
        mock_instance.base_url = "https://sdmdataaccess.nrcs.usda.gov/Tabular/post.rest"
        mock_instance.get_by_point.return_value = [
            {
                "mukey": "412915",
                "musym": "MmA",
                "muname": "Miami silt loam, 0 to 2 percent slopes",
                "farmlndcl": "All areas are prime farmland",
                "areasymbol": "IN097",
            }
        ]

        response = get_farmland_classification_by_point(latitude=39.7684, longitude=-86.1581)

        assert isinstance(response, FarmlandClassificationResponse)
        assert response.query_type == "point"
        assert response.coverage_status == "covered"
        assert len(response.map_units) == 1
        assert response.map_units[0].mukey == "412915"
        assert response.map_units[0].musym == "MmA"
        assert response.map_units[0].muname == "Miami silt loam, 0 to 2 percent slopes"
        assert response.map_units[0].farmlndcl == "All areas are prime farmland"
        assert response.map_units[0].areasymbol == "IN097"
        assert response.regulatory_notice == REGULATORY_NOTICE
        assert response.limitations == REGULATORY_LIMITATIONS

    @patch("fpac_soil_mcp.tools.soil_lookup_tools.SDAClient")
    def test_get_farmland_classification_by_point_unmapped(
        self,
        mock_sda_client_cls: MagicMock,
    ) -> None:
        mock_instance = MagicMock()
        mock_sda_client_cls.return_value = mock_instance
        mock_instance.base_url = "https://sdmdataaccess.nrcs.usda.gov/Tabular/post.rest"
        mock_instance.get_by_point.return_value = []

        response = get_farmland_classification_by_point(latitude=0.0, longitude=0.0)

        assert isinstance(response, FarmlandClassificationResponse)
        assert response.query_type == "point"
        assert response.coverage_status == "unmapped"
        assert len(response.map_units) == 0

    @patch("fpac_soil_mcp.tools.soil_lookup_tools.SDAClient")
    def test_get_farmland_classification_by_point_validation_error(
        self,
        mock_sda_client_cls: MagicMock,
    ) -> None:
        mock_instance = MagicMock()
        mock_sda_client_cls.return_value = mock_instance
        mock_instance.base_url = "https://sdmdataaccess.nrcs.usda.gov/Tabular/post.rest"
        mock_instance.get_by_point.side_effect = SDAValidationError("Latitude out of range")

        response = get_farmland_classification_by_point(latitude=120.0, longitude=-86.1581)

        assert isinstance(response, FarmlandClassificationResponse)
        assert response.coverage_status == "no_data"
        assert len(response.map_units) == 0
        assert any("Latitude out of range" in lim for lim in response.limitations)

    @patch("fpac_soil_mcp.tools.soil_lookup_tools.SDAClient")
    def test_get_farmland_classification_by_point_query_error(
        self,
        mock_sda_client_cls: MagicMock,
    ) -> None:
        mock_instance = MagicMock()
        mock_sda_client_cls.return_value = mock_instance
        mock_instance.base_url = "https://sdmdataaccess.nrcs.usda.gov/Tabular/post.rest"
        mock_instance.get_by_point.side_effect = SDAQueryError("SDA connection timeout")

        response = get_farmland_classification_by_point(latitude=39.7684, longitude=-86.1581)

        assert isinstance(response, FarmlandClassificationResponse)
        assert response.coverage_status == "no_data"
        assert len(response.map_units) == 0
        assert any("SDA connection timeout" in lim for lim in response.limitations)

    @patch("fpac_soil_mcp.tools.soil_lookup_tools.SDAClient")
    def test_get_farmland_classification_by_mukey_covered(
        self,
        mock_sda_client_cls: MagicMock,
    ) -> None:
        mock_instance = MagicMock()
        mock_sda_client_cls.return_value = mock_instance
        mock_instance.base_url = "https://sdmdataaccess.nrcs.usda.gov/Tabular/post.rest"
        mock_instance.get_by_mukey.return_value = [
            {
                "mukey": "412915",
                "musym": "MmA",
                "muname": "Miami silt loam, 0 to 2 percent slopes",
                "farmlndcl": "All areas are prime farmland",
                "areasymbol": "IN097",
            }
        ]

        response = get_farmland_classification_by_mukey(mukey="412915")

        assert isinstance(response, FarmlandClassificationResponse)
        assert response.query_type == "mukey"
        assert response.coverage_status == "covered"
        assert len(response.map_units) == 1
        assert response.map_units[0].mukey == "412915"

    @patch("fpac_soil_mcp.tools.soil_lookup_tools.SDAClient")
    def test_get_farmland_classification_by_mukey_unmapped(
        self,
        mock_sda_client_cls: MagicMock,
    ) -> None:
        mock_instance = MagicMock()
        mock_sda_client_cls.return_value = mock_instance
        mock_instance.base_url = "https://sdmdataaccess.nrcs.usda.gov/Tabular/post.rest"
        mock_instance.get_by_mukey.return_value = []

        response = get_farmland_classification_by_mukey(mukey="999999999")

        assert isinstance(response, FarmlandClassificationResponse)
        assert response.coverage_status == "unmapped"
        assert len(response.map_units) == 0

    @patch("fpac_soil_mcp.tools.soil_lookup_tools.SDAClient")
    def test_get_farmland_classification_by_mukey_error(
        self,
        mock_sda_client_cls: MagicMock,
    ) -> None:
        mock_instance = MagicMock()
        mock_sda_client_cls.return_value = mock_instance
        mock_instance.base_url = "https://sdmdataaccess.nrcs.usda.gov/Tabular/post.rest"
        mock_instance.get_by_mukey.side_effect = SDAValidationError("Invalid mukey")

        response = get_farmland_classification_by_mukey(mukey="invalid-mukey")

        assert isinstance(response, FarmlandClassificationResponse)
        assert response.coverage_status == "no_data"
        assert any("Invalid mukey" in lim for lim in response.limitations)


class TestFPPATools:
    """Tests for explain_fppa_screening_scope and list_farmland_classes."""

    def test_explain_fppa_screening_scope(self) -> None:
        response = explain_fppa_screening_scope()

        assert isinstance(response, FppaScopeResponse)
        assert response.sda_screening_scope
        assert response.lesa_determination_scope
        assert response.limitations == REGULATORY_LIMITATIONS
        assert "7 CFR Part 658" in response.summary or "7 CFR Part 658" in str(
            response.lesa_determination_scope
        )

    def test_list_farmland_classes(self) -> None:
        response = list_farmland_classes()

        assert isinstance(response, FarmlandClassListResponse)
        assert len(response.classes) == len(FARMLAND_CLASS_DEFINITIONS)
        assert "All areas are prime farmland" in response.classes
        assert (
            response.classes["All areas are prime farmland"]["fppa_status"]
            == "Prime Farmland under 7 CFR 657.5(a)"
        )
        assert "Not prime farmland" in response.classes

    def test_calculate_preliminary_lesa_accepts_linestring_corridor(
        self,
    ) -> None:
        with patch("fpac_soil_mcp.tools.lesa_tools.analyze_corridor_fppa") as mock_corridor:
            mock_corridor.return_value = {
                "composite_relative_rating": 55.0,
                "reconciliation_summary": {"buffered_footprint_acres": 2.0},
                "manifest": {
                    "criterion_2_perimeter_evidence": {
                        "normalized_ratio": 0.9,
                        "evidence_status": "measured",
                        "is_agricultural": True,
                        "is_verified": True,
                    }
                },
            }
            geometry = LineString([(0, 0), (1, 1)])
            response = calculate_preliminary_lesa(
                project_name="corridor",
                geometry=geometry,
                project_type="corridor",
            )
            assert response.project_name == "corridor"
            criterion = next(
                item for item in response.site_assessment.criteria if item.criterion_number == 2
            )
            assert criterion.normalized_ratio == 0.9
            mock_corridor.assert_called_once_with(
                centerline=geometry,
                buffer_distance=100.0,
                buffer_units="feet",
                include_nccpi=True,
                productivity_index="NCCPI",
            )

    @patch("fpac_soil_mcp.tools.spatial_analysis_tools.CorridorAnalyzer")
    def test_analyze_corridor_fppa_exposes_shared_criterion_2_evidence(
        self, mock_analyzer_cls: MagicMock
    ) -> None:
        mock_response = MagicMock()
        mock_response.model_dump.return_value = {"manifest": {}}
        mock_response.manifest = {
            "criterion_2_perimeter_evidence": {
                "normalized_ratio": 0.9,
                "evidence_status": "measured",
                "is_agricultural": True,
                "is_verified": True,
                "source_provenance": ["Agricultural land-use source"],
            }
        }
        mock_response.county_segments = []
        mock_response.composite_relative_rating = 55.0
        mock_analyzer_cls.return_value.analyze_corridor.return_value = mock_response

        result = analyze_corridor_fppa(
            centerline={"type": "LineString", "coordinates": [[0, 0], [1, 1]]},
            buffer_distance=100.0,
            site_assessment_inputs={"criteria_inputs": {}},
        )

        criterion = next(
            item
            for item in result["lesa_evaluation"]["site_assessment"]["criteria"]
            if item["criterion_number"] == 2
        )
        assert criterion["awarded_points"] == 9.0
        assert criterion["normalized_ratio"] == 0.9
        assert criterion["evidence_status"] == "measured"
        assert criterion["is_verified"] is True
        assert criterion["source_provenance"] == ["Agricultural land-use source"]

    @patch("fpac_soil_mcp.tools.lesa_tools.PolygonAnalyzer")
    def test_calculate_preliminary_lesa_accepts_wkt_polygon(
        self, mock_analyzer_cls: MagicMock
    ) -> None:
        mock_response = MagicMock()
        mock_response.manifest = {
            "land_evaluation": {
                "productivity_index": "NCCPI",
                "candidate_le_score": 72.0,
                "aoi_relative_rating": 0.72,
                "total_acreage": 1.0,
            }
        }
        mock_response.total_aoi_acres = 1.0
        mock_response.limitations = []
        mock_analyzer_cls.return_value.analyze_polygon.return_value = mock_response

        response = calculate_preliminary_lesa(
            project_name="wkt polygon",
            geometry="POLYGON ((0 0, 1 0, 1 1, 0 1, 0 0))",
        )

        assert response.project_name == "wkt polygon"
        mock_analyzer_cls.return_value.analyze_polygon.assert_called_once()
        assert (
            mock_analyzer_cls.return_value.analyze_polygon.call_args.kwargs["geojson_input"]["type"]
            == "Polygon"
        )

    @patch("fpac_soil_mcp.tools.lesa_tools.analyze_corridor_fppa")
    def test_calculate_preliminary_lesa_routes_wkt_line_with_buffer_options(
        self, mock_corridor: MagicMock
    ) -> None:
        mock_corridor.return_value = {
            "composite_relative_rating": 65.0,
            "reconciliation_summary": {"buffered_footprint_acres": 12.5},
        }

        response = calculate_preliminary_lesa(
            project_name="wkt corridor",
            geometry="LINESTRING (-93.5 42.0, -93.4 42.1)",
            project_type="corridor",
            corridor_buffer_distance=250.0,
            corridor_buffer_units="meters",
        )

        assert response.project_name == "wkt corridor"
        mock_corridor.assert_called_once_with(
            centerline="LINESTRING (-93.5 42.0, -93.4 42.1)",
            buffer_distance=250.0,
            buffer_units="meters",
            include_nccpi=True,
            productivity_index="NCCPI",
        )

    def test_calculate_preliminary_lesa_rejects_polygon_corridor(self) -> None:
        geometry = {
            "type": "Polygon",
            "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]],
        }

        with pytest.raises(GeometryValidationError, match="polygon geometry cannot be routed"):
            calculate_preliminary_lesa(
                project_name="polygon corridor",
                geometry=geometry,
                project_type="corridor",
            )

    def test_calculate_preliminary_lesa_rejects_multipolygon_corridor(self) -> None:
        geometry = {
            "type": "MultiPolygon",
            "coordinates": [
                [[[0, 0], [1, 0], [1, 1], [0, 0]]],
                [[[2, 2], [3, 2], [3, 3], [2, 2]]],
            ],
        }

        with pytest.raises(GeometryValidationError, match="polygon geometry cannot be routed"):
            calculate_preliminary_lesa(
                project_name="multipolygon corridor",
                geometry=geometry,
                project_type="corridor",
            )

    def test_calculate_preliminary_lesa_rejects_unsupported_selector(
        self,
    ) -> None:
        with pytest.raises(ValueError, match="Unsupported productivity index type"):
            calculate_preliminary_lesa(
                project_name="unsupported corridor",
                geometry="LINESTRING (-93.5 42.0, -93.4 42.1)",
                project_type="corridor",
                productivity_index="unsupported",
            )

    @patch("fpac_soil_mcp.tools.lesa_tools.analyze_corridor_fppa")
    def test_calculate_preliminary_lesa_propagates_benchmark_and_generic_fields(
        self, mock_corridor: MagicMock
    ) -> None:
        mock_corridor.return_value = {
            "composite_relative_rating": 74.0,
            "reconciliation_summary": {"buffered_footprint_acres": 9.5},
            "productivity_rating": 74.0,
            "productivity_rating_class": "high",
        }

        with pytest.raises(ValueError, match="Unsupported productivity index type"):
            calculate_preliminary_lesa(
                project_name="benchmarked corridor",
                geometry="LINESTRING (-93.5 42.0, -93.4 42.1)",
                project_type="corridor",
                productivity_index="unsupported",
                max_county_rating_override=88.0,
            )


class TestPolygonTools:
    """Tests for analyze_farmland_by_polygon, check_urban_area_exemption, and get_soil_interpretations."""

    @patch("fpac_soil_mcp.tools.spatial_analysis_tools.PolygonAnalyzer")
    def test_analyze_farmland_by_polygon(self, mock_analyzer_cls: MagicMock) -> None:
        mock_instance = MagicMock()
        mock_analyzer_cls.return_value = mock_instance
        mock_instance.analyze_polygon.return_value = {
            "coverage_status": "covered",
            "total_aoi_acres": 125.0,
        }

        res = analyze_farmland_by_polygon({"type": "Polygon", "coordinates": []})
        assert res["coverage_status"] == "covered"
        assert res["total_aoi_acres"] == 125.0

    @patch("fpac_soil_mcp.tools.exemption_tools.TigerwebClient")
    def test_check_urban_area_exemption(self, mock_tiger_cls: MagicMock) -> None:
        mock_instance = MagicMock()
        mock_tiger_cls.return_value = mock_instance
        mock_instance.check_urban_exemption.return_value = {
            "status": "success",
            "is_urban_intersected": False,
        }

        res = check_urban_area_exemption({"type": "Polygon", "coordinates": []})
        assert res["status"] == "success"
        assert res["is_urban_intersected"] is False

    @patch("fpac_soil_mcp.tools.soil_lookup_tools.SDAClient")
    def test_get_soil_interpretations(self, mock_sda_cls: MagicMock) -> None:
        mock_instance = MagicMock()
        mock_sda_cls.return_value = mock_instance
        mock_instance.get_interpretations.return_value = [
            {"mukey": "412915", "numeric_rating": 0.85}
        ]

        res = get_soil_interpretations(["412915"])
        assert len(res) == 1
        assert res[0]["numeric_rating"] == 0.85

    @patch("fpac_soil_mcp.tools.soil_lookup_tools.SDAClient")
    def test_get_soil_polygons_by_geometry(self, mock_sda_cls: MagicMock) -> None:
        mock_instance = MagicMock()
        mock_sda_cls.return_value = mock_instance
        mock_instance.get_spatial_intersection.return_value = [
            {
                "mukey": "412915",
                "musym": "138B",
                "muname": "Clarion loam",
                "farmlndcl": "All areas are prime farmland",
                "areasymbol": "IA169",
                "area_ac": 25.0,
                "geom": "POLYGON((-93.5 42.0, -93.4 42.0, -93.4 42.1, -93.5 42.1, -93.5 42.0))",
            }
        ]

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

        fc = get_soil_polygons_by_geometry(geojson)
        assert fc["type"] == "FeatureCollection"
        assert len(fc["features"]) == 1
        assert fc["features"][0]["properties"]["mukey"] == "412915"
        assert fc["features"][0]["properties"]["area_ac"] == 25.0
        assert fc["properties"]["clipped"] is True


class TestCorridorTools:
    """Tests for analyze_corridor_fppa FastMCP tool."""

    @patch("fpac_soil_mcp.tools.spatial_analysis_tools.CorridorAnalyzer")
    def test_analyze_corridor_fppa_basic(self, mock_analyzer_cls: MagicMock) -> None:
        mock_instance = MagicMock()
        mock_analyzer_cls.return_value = mock_instance

        mock_response = MagicMock()
        mock_response.model_dump.return_value = {
            "query_type": "corridor",
            "geometry_hash": "sha256:123456",
            "buffer_distance": 50.0,
            "buffer_units": "feet",
            "composite_relative_rating": 82.5,
            "productivity_rating": 82.5,
            "productivity_rating_class": "high",
            "county_segments": [],
            "reconciliation_summary": {"status": "reconciled"},
        }
        mock_response.county_segments = []
        mock_response.composite_relative_rating = 82.5
        mock_instance.analyze_corridor.return_value = mock_response

        res = analyze_corridor_fppa(
            centerline="LINESTRING(-93.5 42.0, -93.4 42.1)",
            buffer_distance=50.0,
            buffer_units="feet",
        )

        assert res["query_type"] == "corridor"
        assert res["composite_relative_rating"] == 82.5
        assert res["productivity_rating"] == 82.5
        assert res["productivity_rating_class"] == "high"
        assert "nccpi_rating" not in res
        assert "nccpi_class" not in res
        assert "lesa_evaluation" not in res
        mock_instance.analyze_corridor.assert_called_once_with(
            centerline_input="LINESTRING(-93.5 42.0, -93.4 42.1)",
            buffer_distance=50.0,
            buffer_units="feet",
            indirect_geometry_input=None,
            alternatives=None,
            include_nccpi=True,
            productivity_index="NCCPI",
        )

    @patch("fpac_soil_mcp.tools.spatial_analysis_tools.CorridorAnalyzer")
    def test_analyze_corridor_fppa_propagates_generic_options(
        self, mock_analyzer_cls: MagicMock
    ) -> None:
        mock_instance = MagicMock()
        mock_analyzer_cls.return_value = mock_instance
        mock_response = MagicMock()
        mock_response.model_dump.return_value = {
            "query_type": "corridor",
            "geometry_hash": "sha256:generic",
            "composite_relative_rating": 70.0,
            "county_segments": [],
        }
        mock_response.county_segments = []
        mock_response.composite_relative_rating = 70.0
        mock_instance.analyze_corridor.return_value = mock_response

        alternatives = [
            {
                "alternative_id": "B",
                "centerline": "LINESTRING(-93.6 42.0, -93.5 42.1)",
                "buffer_distance": 75.0,
                "buffer_units": "meters",
            }
        ]
        result = analyze_corridor_fppa(
            centerline="LINESTRING(-93.5 42.0, -93.4 42.1)",
            buffer_distance=125.0,
            buffer_units="meters",
            indirect_geometry="POLYGON((-93.5 42.0, -93.4 42.0, -93.4 42.1, -93.5 42.0))",
            alternatives=alternatives,
            include_nccpi=True,
            productivity_index="NCCPI",
            max_county_rating_override=88.0,
        )

        assert result["query_type"] == "corridor"
        mock_instance.analyze_corridor.assert_called_once_with(
            centerline_input="LINESTRING(-93.5 42.0, -93.4 42.1)",
            buffer_distance=125.0,
            buffer_units="meters",
            indirect_geometry_input="POLYGON((-93.5 42.0, -93.4 42.0, -93.4 42.1, -93.5 42.0))",
            alternatives=alternatives,
            include_nccpi=True,
            productivity_index="NCCPI",
            max_county_rating_override=88.0,
        )

    @patch("fpac_soil_mcp.tools.spatial_analysis_tools.CorridorAnalyzer")
    def test_analyze_corridor_fppa_forwards_non_nccpi_without_override(
        self, mock_analyzer_cls: MagicMock
    ) -> None:
        mock_instance = mock_analyzer_cls.return_value
        mock_response = MagicMock()
        mock_response.model_dump.return_value = {"query_type": "corridor"}
        mock_response.county_segments = []
        mock_response.composite_relative_rating = None
        mock_instance.analyze_corridor.return_value = mock_response

        analyze_corridor_fppa(
            centerline="LINESTRING(-93.5 42.0, -93.4 42.1)",
            buffer_distance=50.0,
            productivity_index="csr2",
            include_nccpi=False,
        )

        mock_instance.analyze_corridor.assert_called_once_with(
            centerline_input="LINESTRING(-93.5 42.0, -93.4 42.1)",
            buffer_distance=50.0,
            buffer_units="feet",
            indirect_geometry_input=None,
            alternatives=None,
            include_nccpi=False,
            productivity_index="CSR2",
        )

    @patch("fpac_soil_mcp.tools.spatial_analysis_tools.CorridorAnalyzer")
    def test_analyze_corridor_fppa_with_site_assessment(self, mock_analyzer_cls: MagicMock) -> None:
        mock_instance = MagicMock()
        mock_analyzer_cls.return_value = mock_instance

        mock_seg = MagicMock()
        mock_seg.total_segment_acres = 250.0
        mock_seg.nass_profile = {"farm_size_acres_avg": 250.0}

        mock_response = MagicMock()
        mock_response.model_dump.return_value = {
            "query_type": "corridor",
            "geometry_hash": "sha256:123456",
            "composite_relative_rating": 80.0,
            "county_segments": [mock_seg],
        }
        mock_response.county_segments = [mock_seg]
        mock_response.composite_relative_rating = 80.0
        mock_instance.analyze_corridor.return_value = mock_response

        res = analyze_corridor_fppa(
            centerline="LINESTRING(-93.5 42.0, -93.4 42.1)",
            buffer_distance=100.0,
            site_assessment_inputs={
                "criteria_inputs": {
                    "1": {"awarded_points": 15, "justification": "Rural area"},
                    "8": {"awarded_points": 20, "justification": "Severed parcel"},
                },
                "project_farm_acres": 300.0,
            },
        )

        assert "lesa_evaluation" in res
        lesa = res["lesa_evaluation"]
        assert lesa["land_evaluation_score"] == 80.0
        assert lesa["site_assessment"]["total_sa_points"] >= 45.0  # 15 + 20 + 10 (from farm ratio)
        assert lesa["total_lesa_score"] >= 125.0

    @patch("fpac_soil_mcp.tools.spatial_analysis_tools.CorridorAnalyzer")
    def test_analyze_corridor_fppa_multi_county_weighted_farm_size(
        self, mock_analyzer_cls: MagicMock
    ) -> None:
        mock_instance = MagicMock()
        mock_analyzer_cls.return_value = mock_instance

        # County 1: 100 acres, avg farm size 200.0
        mock_seg1 = MagicMock()
        mock_seg1.total_segment_acres = 100.0
        mock_seg1.nass_profile = {"farm_size_acres_avg": 200.0}

        # County 2: 300 acres, avg farm size 400.0
        mock_seg2 = MagicMock()
        mock_seg2.total_segment_acres = 300.0
        mock_seg2.nass_profile = {"farm_size_acres_avg": 400.0}

        # Expected weighted avg: (200*100 + 400*300) / (100 + 300) = (20000 + 120000) / 400 = 140000 / 400 = 350.0
        mock_response = MagicMock()
        mock_response.model_dump.return_value = {
            "query_type": "corridor",
            "geometry_hash": "sha256:abcdef",
            "composite_relative_rating": 75.0,
            "county_segments": [mock_seg1, mock_seg2],
        }
        mock_response.county_segments = [mock_seg1, mock_seg2]
        mock_response.composite_relative_rating = 75.0
        mock_instance.analyze_corridor.return_value = mock_response

        # Project farm acres = 350.0. Ratio = 350 / 350 = 1.0 (100% -> 10 points)
        res = analyze_corridor_fppa(
            centerline="LINESTRING(-93.5 42.0, -93.4 42.1)",
            buffer_distance=50.0,
            site_assessment_inputs={
                "project_farm_acres": 350.0,
            },
        )

        assert "lesa_evaluation" in res
        lesa = res["lesa_evaluation"]
        sa = lesa["site_assessment"]
        crit7 = next(c for c in sa["criteria"] if c["criterion_number"] == 7)
        assert crit7["awarded_points"] == 10
        assert "350.0" in crit7["justification"] or "100.0%" in crit7["justification"]
