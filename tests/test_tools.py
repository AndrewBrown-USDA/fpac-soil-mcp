"""Unit tests for the extracted MCP tool modules."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from shapely.geometry import LineString

from fpac_soil_mcp.clients.sda import SDAQueryError, SDAValidationError
from fpac_soil_mcp.core.constants import (
    FARMLAND_CLASS_DEFINITIONS,
    REGULATORY_LIMITATIONS,
    REGULATORY_NOTICE,
)
from fpac_soil_mcp.domain.lesa import calculate_criterion_7_score
from fpac_soil_mcp.domain.site_assessment import SITE_ASSESSMENT_REGISTRY
from fpac_soil_mcp.mcp.tools.exemption_tools import check_urban_area_exemption
from fpac_soil_mcp.mcp.tools.fppa_tools import (
    explain_fppa_screening_scope,
    list_farmland_classes,
)
from fpac_soil_mcp.mcp.tools.lesa_tools import _score_registry_facts, calculate_preliminary_lesa
from fpac_soil_mcp.mcp.tools.soil_lookup_tools import (
    get_farmland_classification_by_mukey,
    get_farmland_classification_by_point,
    get_soil_interpretations,
    get_soil_polygons_by_geometry,
)
from fpac_soil_mcp.mcp.tools.spatial_analysis_tools import (
    analyze_corridor_fppa,
    analyze_farmland_by_polygon,
)
from fpac_soil_mcp.models import (
    FarmlandClassificationResponse,
    FarmlandClassListResponse,
    FppaScopeResponse,
    SiteAssessmentInputs,
)
from fpac_soil_mcp.spatial.geometry import GeometryValidationError


def _polygon_geometry() -> dict[str, Any]:
    return {
        "type": "Polygon",
        "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
    }


def _mock_lesa_polygon(mock_analyzer_cls: MagicMock, score: float, acreage: float) -> None:
    response = MagicMock()
    response.manifest = {
        "land_evaluation": {
            "candidate_le_score": score,
            "aoi_relative_rating": score / 100,
            "rated_acreage": acreage,
            "unrated_acreage": 0.0,
            "total_acreage": acreage,
            "coverage_percent": 100.0,
        }
    }
    response.total_aoi_acres = acreage
    response.limitations = []
    response.coverage_status = "covered"
    response.map_units = [MagicMock(calculated_acres=acreage, productivity_rating=score / 100)]
    mock_analyzer_cls.return_value.analyze_polygon.return_value = response


def _mock_lesa_corridor(mock_analyzer_cls: MagicMock, data: dict[str, Any]) -> MagicMock:
    instance = MagicMock()
    response = MagicMock()
    response.model_dump.return_value = data
    instance.analyze_corridor.return_value = response
    mock_analyzer_cls.return_value = instance
    return instance


class TestSoilTools:
    """Tests for get_farmland_classification_by_point and get_farmland_classification_by_mukey."""

    @patch("fpac_soil_mcp.mcp.tools.soil_lookup_tools.SDAClient")
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

    @patch("fpac_soil_mcp.mcp.tools.soil_lookup_tools.SDAClient")
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

    @patch("fpac_soil_mcp.mcp.tools.soil_lookup_tools.SDAClient")
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
        assert response.coverage_status == "error"
        assert len(response.map_units) == 0
        assert any("Latitude out of range" in lim for lim in response.limitations)
        assert response.error is not None
        assert response.error.code == "validation_error"
        assert response.error.source == "USDA NRCS Soil Data Access (SDA)"

    @patch("fpac_soil_mcp.mcp.tools.soil_lookup_tools.SDAClient")
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
        assert response.coverage_status == "error"
        assert len(response.map_units) == 0
        assert any("SDA connection timeout" in lim for lim in response.limitations)
        assert response.error is not None
        assert response.error.code == "upstream_error"
        assert response.error.source == "USDA NRCS Soil Data Access (SDA)"

    @patch("fpac_soil_mcp.mcp.tools.soil_lookup_tools.SDAClient")
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

    @patch("fpac_soil_mcp.mcp.tools.soil_lookup_tools.SDAClient")
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

    @patch("fpac_soil_mcp.mcp.tools.soil_lookup_tools.SDAClient")
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
        assert response.coverage_status == "error"
        assert any("Invalid mukey" in lim for lim in response.limitations)
        assert response.error is not None
        assert response.error.code == "validation_error"

    @patch("fpac_soil_mcp.mcp.tools.soil_lookup_tools.SDAClient")
    def test_get_farmland_classification_by_mukey_upstream_error_is_not_unmapped(
        self,
        mock_sda_client_cls: MagicMock,
    ) -> None:
        mock_instance = MagicMock()
        mock_sda_client_cls.return_value = mock_instance
        mock_instance.base_url = "https://sdmdataaccess.nrcs.usda.gov/Tabular/post.rest"
        mock_instance.get_by_mukey.side_effect = SDAQueryError("SDA unavailable")

        response = get_farmland_classification_by_mukey(mukey="402001")

        assert response.coverage_status == "error"
        assert response.map_units == []
        assert response.error is not None
        assert response.error.code == "upstream_error"
        assert any("SDA unavailable" in lim for lim in response.limitations)


class TestFPPATools:
    def test_missing_criterion_10_category_is_assumed_at_registry_maximum(self) -> None:
        scored = _score_registry_facts(
            {"10": {"is_verified": True, "justification": "No category provided."}}
        )[10]
        criterion_max = SITE_ASSESSMENT_REGISTRY.criterion(10).max_points

        assert scored["input_authority"] == "unavailable"
        assert scored["evidence_status"] == "assumed (no evidence)"
        assert scored["assumed_points"] == criterion_max
        assert scored["is_verified"] is False
        assert f"Registry maximum ({criterion_max:g} points)" in scored["assumption_provenance"]
        assert "ADR 0018" in scored["assumption_provenance"]
        assert "no criterion evidence" in scored["assumption_provenance"]
        assert "awarded_points" not in scored

    @patch("fpac_soil_mcp.mcp.tools.lesa_tools.PolygonAnalyzer")
    def test_preliminary_lesa_keeps_scored_registry_fact_metadata(
        self, mock_analyzer_cls: MagicMock
    ) -> None:
        _mock_lesa_polygon(mock_analyzer_cls, 70.0, 10.0)
        facts = {
            "1": {
                "value": None,
                "percentage": 50,
                "is_verified": True,
                "source_provenance": ["Verified field survey"],
            }
        }

        response = calculate_preliminary_lesa(
            project_name="registry-fact-metadata",
            geometry=_polygon_geometry(),
            site_assessment_inputs={"criteria_facts": facts},
        )
        criterion = next(c for c in response.site_assessment.criteria if c.criterion_number == 1)
        scored_fact = _score_registry_facts(facts)[1]

        assert criterion.awarded_points == scored_fact["awarded_points"]
        assert criterion.input_authority == scored_fact["input_authority"] == "analyst_proposed"
        assert criterion.is_verified is scored_fact["is_verified"] is True
        assert criterion.source_provenance == scored_fact["source_provenance"]
        assert criterion.justification == scored_fact["justification"]

    @pytest.mark.parametrize("percentage", [50, 50.1, 60, 65, 70, 75, 80, 85, 90, 92, 95, 100, 110])
    def test_criterion_7_acreage_and_registry_fact_scores_match(self, percentage: float) -> None:
        county_average = 200.0
        project_acres = county_average * percentage / 100.0
        acreage_points, acreage_description = calculate_criterion_7_score(
            project_farm_acres=project_acres,
            county_average_farm_acres=county_average,
        )
        fact = _score_registry_facts({"7": {"percentage": percentage, "is_verified": True}})[7]
        band = SITE_ASSESSMENT_REGISTRY.criterion(7).band_for(percentage)

        assert band is not None
        assert acreage_points == fact["awarded_points"] == band.points
        assert band.label in acreage_description
        assert band.label in fact["justification"]

    @pytest.mark.parametrize(
        "criterion_input",
        [
            {"criteria_facts": {"7": {"percentage": 92, "is_verified": True}}},
            {
                "criteria_inputs": {
                    "7": {"awarded_points": 8, "justification": "Verified farm size."}
                }
            },
        ],
    )
    @patch("fpac_soil_mcp.mcp.tools.lesa_tools.PolygonAnalyzer")
    def test_preliminary_lesa_rejects_competing_criterion_7_inputs(
        self, mock_analyzer_cls: MagicMock, criterion_input: dict[str, Any]
    ) -> None:
        _mock_lesa_polygon(mock_analyzer_cls, 70.0, 10.0)
        site_assessment_inputs = {
            **criterion_input,
            "project_farm_acres": 184.0,
            "county_average_farm_acres": 200.0,
        }

        with pytest.raises(ValueError, match="cannot combine farm-acreage"):
            calculate_preliminary_lesa(
                project_name="conflicting-criterion-seven",
                geometry=_polygon_geometry(),
                site_assessment_inputs=site_assessment_inputs,
            )

    @patch("fpac_soil_mcp.mcp.tools.lesa_tools.PolygonAnalyzer")
    def test_preliminary_lesa_scores_registry_facts_deterministically(
        self, mock_analyzer_cls: MagicMock
    ) -> None:
        _mock_lesa_polygon(mock_analyzer_cls, 70.0, 10.0)

        response = calculate_preliminary_lesa(
            project_name="facts",
            geometry=_polygon_geometry(),
            site_assessment_inputs={
                "criteria_facts": {
                    "1": {"percentage": 95, "is_verified": True},
                    "8": {
                        "percentage": 15,
                        "is_verified": True,
                        "justification": "The project creates a minor remnant.",
                    },
                }
            },
        )

        criteria = {item.criterion_number: item for item in response.site_assessment.criteria}
        assert criteria[1].awarded_points == 15
        assert criteria[1].rule_reference == "7 CFR § 658.5(b)(1)"
        assert criteria[8].awarded_points == 5
        assert criteria[1].input_authority == "analyst_proposed"
        assert criteria[1].is_automated is False
        assert criteria[8].justification == "The project creates a minor remnant."
        assert response.site_assessment.evaluation_status == "incomplete"
        assert all("siting" not in item.lower() for item in response.limitations)

    @pytest.mark.parametrize(
        ("inputs", "message"),
        [
            (
                {
                    "criteria_facts": {"1": {"percentage": 95, "is_verified": True}},
                    "criteria_inputs": {"1": {"awarded_points": 15, "justification": "Override."}},
                },
                "Conflicting fact and point override",
            ),
            (
                {"criteria_facts": {"1": {"percentage": 101, "is_verified": True}}},
                "outside the registry",
            ),
            (
                {"criteria_facts": {"8": {"percentage": 15, "is_verified": True}}},
                "requires a rationale",
            ),
            (
                {"criteria_facts": {"1": {"percentage": 95}}},
                "requires verification",
            ),
            (
                {
                    "criteria_inputs": {
                        "8": {"awarded_points": 11, "justification": "Above the site maximum."}
                    }
                },
                "must be between 0 and 10",
            ),
        ],
    )
    @patch("fpac_soil_mcp.mcp.tools.lesa_tools.PolygonAnalyzer")
    def test_preliminary_lesa_rejects_invalid_facts_and_overrides(
        self, mock_analyzer_cls: MagicMock, inputs: dict[str, Any], message: str
    ) -> None:
        _mock_lesa_polygon(mock_analyzer_cls, 70.0, 10.0)
        with pytest.raises(ValueError, match=message):
            calculate_preliminary_lesa(
                project_name="invalid-input",
                geometry=_polygon_geometry(),
                site_assessment_inputs=inputs,
            )

    @patch("fpac_soil_mcp.mcp.tools.lesa_tools.CorridorAnalyzer")
    def test_preliminary_lesa_preserves_fact_provenance_and_corridor_maxima(
        self, mock_analyzer_cls: MagicMock
    ) -> None:
        _mock_lesa_corridor(
            mock_analyzer_cls,
            {
                "composite_relative_rating": 70.0,
                "reconciliation_summary": {
                    "buffered_footprint_acres": 10.0,
                    "rated_productivity_acres": 8.0,
                    "unrated_productivity_acres": 2.0,
                    "productivity_coverage_percent": 80.0,
                    "productivity_coverage_status": "partial",
                },
                "manifest": {},
            },
        )
        response = calculate_preliminary_lesa(
            project_name="corridor-facts",
            geometry="LINESTRING (-93.5 42.0, -93.4 42.1)",
            project_type="corridor",
            site_assessment_inputs={
                "criteria_facts": {
                    "2": {
                        "percentage": 95,
                        "is_verified": True,
                        "source_provenance": ["Analyst field survey"],
                    },
                    "8": {
                        "percentage": 15,
                        "is_verified": True,
                        "justification": "A minor remnant is expected.",
                    },
                    "11": {
                        "category": "substantial_reduction",
                        "is_verified": True,
                        "justification": "Substantial demand reduction is expected.",
                    },
                }
            },
        )
        criteria = {item.criterion_number: item for item in response.site_assessment.criteria}
        assert criteria[2].source_provenance == ["Analyst field survey"]
        assert criteria[2].input_authority == "analyst_proposed"
        assert criteria[8].max_points == 25
        assert criteria[8].awarded_points == 12.5
        assert criteria[11].max_points == 25
        assert criteria[11].awarded_points == 25
        assert response.land_evaluation.coverage_status == "partial"
        assert response.land_evaluation.coverage_percent == 80.0
        assert response.land_evaluation.rated_acreage == 8.0
        assert response.land_evaluation.unrated_acreage == 2.0
        assert response.land_evaluation.rating_source_provenance == ["SDA:NCCPI_V3"]
        assert any("SDA:NCCPI_V3" in notice for notice in response.land_evaluation.notices)
        for number in (5, 6):
            assert criteria[number].awarded_points == 0
            assert criteria[number].is_statutorily_zeroed is True
            assert criteria[number].input_authority == "statutory"
            assert criteria[number].is_automated is False

    @patch("fpac_soil_mcp.mcp.tools.lesa_tools.CorridorAnalyzer")
    def test_preliminary_lesa_rejects_points_for_statutorily_zeroed_corridor_criterion(
        self, mock_analyzer_cls: MagicMock
    ) -> None:
        _mock_lesa_corridor(
            mock_analyzer_cls,
            {
                "composite_relative_rating": 70.0,
                "reconciliation_summary": {"buffered_footprint_acres": 10.0},
                "manifest": {},
            },
        )
        with pytest.raises(ValueError, match="statutorily zeroed"):
            calculate_preliminary_lesa(
                project_name="corridor-zeroed",
                geometry="LINESTRING (-93.5 42.0, -93.4 42.1)",
                project_type="corridor",
                site_assessment_inputs={
                    "criteria_inputs": {
                        "5": {"awarded_points": 1, "justification": "Should not be scored."}
                    }
                },
            )

    @patch("fpac_soil_mcp.mcp.tools.lesa_tools.PolygonAnalyzer")
    def test_preliminary_lesa_preserves_analyst_override_rationale_requirement(
        self, mock_analyzer_cls: MagicMock
    ) -> None:
        _mock_lesa_polygon(mock_analyzer_cls, 70.0, 10.0)

        with pytest.raises(ValueError, match="rationale"):
            calculate_preliminary_lesa(
                project_name="override",
                geometry=_polygon_geometry(),
                site_assessment_inputs={"criteria_inputs": {"1": {"awarded_points": 15}}},
            )

    @patch("fpac_soil_mcp.mcp.tools.lesa_tools.PolygonAnalyzer")
    def test_preliminary_lesa_keeps_unknown_registry_fact_unavailable(
        self, mock_analyzer_cls: MagicMock
    ) -> None:
        _mock_lesa_polygon(mock_analyzer_cls, 70.0, 10.0)

        response = calculate_preliminary_lesa(
            project_name="unknown-fact",
            geometry=_polygon_geometry(),
            site_assessment_inputs={"criteria_facts": {"1": {"percentage": "unknown"}}},
        )

        criterion = next(
            item for item in response.site_assessment.criteria if item.criterion_number == 1
        )
        assert criterion.awarded_points == 0.0
        assert criterion.input_authority == "unavailable"
        assert criterion.is_automated is False
        assert response.site_assessment.evaluation_status == "incomplete"
        assert response.threshold_status == "not_evaluated"

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
        with patch("fpac_soil_mcp.mcp.tools.lesa_tools.CorridorAnalyzer") as mock_analyzer_cls:
            mock_analyzer = _mock_lesa_corridor(
                mock_analyzer_cls,
                {
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
                },
            )
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
            mock_analyzer.analyze_corridor.assert_called_once_with(
                centerline_input=geometry,
                buffer_distance=100.0,
                buffer_units="feet",
                productivity_index="NCCPI",
                max_county_rating_override=None,
            )

    @patch("fpac_soil_mcp.mcp.tools.spatial_analysis_tools.CorridorAnalyzer")
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

    @patch("fpac_soil_mcp.mcp.tools.lesa_tools.PolygonAnalyzer")
    def test_calculate_preliminary_lesa_accepts_wkt_polygon(
        self, mock_analyzer_cls: MagicMock
    ) -> None:
        mock_response = MagicMock()
        mock_response.manifest = {
            "land_evaluation": {
                "productivity_index": "NCCPI",
                "candidate_le_score": 72.0,
                "aoi_relative_rating": 0.72,
                "rated_acreage": 1.0,
                "unrated_acreage": 0.0,
                "total_acreage": 1.0,
                "coverage_percent": 100.0,
            }
        }
        mock_response.total_aoi_acres = 1.0
        mock_response.limitations = []
        mock_response.coverage_status = "covered"
        mock_response.map_units = [MagicMock(calculated_acres=1.0, productivity_rating=0.8)]
        mock_analyzer_cls.return_value.analyze_polygon.return_value = mock_response

        response = calculate_preliminary_lesa(
            project_name="wkt polygon",
            geometry="POLYGON ((0 0, 1 0, 1 1, 0 1, 0 0))",
        )

        assert response.project_name == "wkt polygon"
        assert response.land_evaluation.coverage_status == "covered"
        assert response.land_evaluation.rating_source_provenance == ["SDA:NCCPI_V3"]
        assert any("SDA:NCCPI_V3" in notice for notice in response.land_evaluation.notices)
        mock_analyzer_cls.return_value.analyze_polygon.assert_called_once()
        assert (
            mock_analyzer_cls.return_value.analyze_polygon.call_args.kwargs["geojson_input"]["type"]
            == "Polygon"
        )

    @patch("fpac_soil_mcp.mcp.tools.lesa_tools.PolygonAnalyzer")
    def test_calculate_preliminary_lesa_keeps_unavailable_le_unavailable(
        self, mock_analyzer_cls: MagicMock
    ) -> None:
        mock_response = MagicMock()
        mock_response.manifest = {
            "land_evaluation": {
                "candidate_le_score": None,
                "aoi_relative_rating": None,
                "rated_acreage": 0.0,
                "unrated_acreage": 5.0,
                "total_acreage": 5.0,
                "coverage_percent": 0.0,
            }
        }
        mock_response.total_aoi_acres = 5.0
        mock_response.limitations = []
        mock_response.coverage_status = "unmapped"
        mock_response.map_units = []
        mock_analyzer_cls.return_value.analyze_polygon.return_value = mock_response

        response = calculate_preliminary_lesa(
            project_name="unavailable LE",
            geometry=_polygon_geometry(),
        )

        assert response.land_evaluation.candidate_le_score is None
        assert response.land_evaluation.aoi_relative_rating is None
        assert response.land_evaluation.coverage_status == "unmapped"
        assert response.threshold_status == "not_evaluated"
        assert response.total_lesa_score is None

    @patch("fpac_soil_mcp.mcp.tools.lesa_tools.CorridorAnalyzer")
    def test_calculate_preliminary_lesa_routes_wkt_line_with_buffer_options(
        self, mock_analyzer_cls: MagicMock
    ) -> None:
        mock_analyzer = _mock_lesa_corridor(
            mock_analyzer_cls,
            {
                "composite_relative_rating": 65.0,
                "reconciliation_summary": {"buffered_footprint_acres": 12.5},
            },
        )

        response = calculate_preliminary_lesa(
            project_name="wkt corridor",
            geometry="LINESTRING (-93.5 42.0, -93.4 42.1)",
            project_type="corridor",
            corridor_buffer_distance=250.0,
            corridor_buffer_units="meters",
        )

        assert response.project_name == "wkt corridor"
        mock_analyzer.analyze_corridor.assert_called_once_with(
            centerline_input="LINESTRING (-93.5 42.0, -93.4 42.1)",
            buffer_distance=250.0,
            buffer_units="meters",
            productivity_index="NCCPI",
            max_county_rating_override=None,
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

    def test_calculate_preliminary_lesa_rejects_linestring_site(self) -> None:
        with pytest.raises(GeometryValidationError, match="requires project_type='corridor'"):
            calculate_preliminary_lesa(
                project_name="line site",
                geometry="LINESTRING (-93.5 42.0, -93.4 42.1)",
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

    @patch("fpac_soil_mcp.mcp.tools.lesa_tools.CorridorAnalyzer")
    def test_calculate_preliminary_lesa_propagates_benchmark_and_generic_fields(
        self, mock_analyzer_cls: MagicMock
    ) -> None:
        _mock_lesa_corridor(
            mock_analyzer_cls,
            {
                "composite_relative_rating": 74.0,
                "reconciliation_summary": {"buffered_footprint_acres": 9.5},
                "productivity_rating": 74.0,
                "productivity_rating_class": "high",
            },
        )

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

    @patch("fpac_soil_mcp.mcp.tools.spatial_analysis_tools.PolygonAnalyzer")
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

    @patch("fpac_soil_mcp.mcp.tools.exemption_tools.TigerwebClient")
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

    @patch("fpac_soil_mcp.mcp.tools.soil_lookup_tools.SDAClient")
    def test_get_soil_interpretations(self, mock_sda_cls: MagicMock) -> None:
        mock_instance = MagicMock()
        mock_sda_cls.return_value = mock_instance
        mock_instance.get_interpretations.return_value = [
            {"mukey": "412915", "numeric_rating": 0.85}
        ]

        res = get_soil_interpretations(["412915"])
        assert len(res) == 1
        assert res[0]["numeric_rating"] == 0.85

    @patch("fpac_soil_mcp.mcp.tools.soil_lookup_tools.SDAClient")
    def test_get_soil_interpretations_returns_source_aware_upstream_error(
        self, mock_sda_cls: MagicMock
    ) -> None:
        mock_instance = mock_sda_cls.return_value
        mock_instance.base_url = "https://sda.example.test/query"
        mock_instance.get_interpretations.side_effect = SDAQueryError("service unavailable")

        result = get_soil_interpretations(["412915"])

        assert result["status"] == "error"
        assert result["source"]["endpoint"] == "https://sda.example.test/query"
        assert result["error"] == {
            "code": "upstream_error",
            "message": "service unavailable",
            "source": "USDA NRCS Soil Data Access (SDA)",
        }

    def test_site_assessment_input_rejects_unknown_nested_fields_and_bad_criteria(self) -> None:
        with pytest.raises(ValueError):
            SiteAssessmentInputs.model_validate(
                {"criteria_inputs": {"1": {"awarded_points": 2, "unexpected": True}}}
            )
        with pytest.raises(ValueError):
            SiteAssessmentInputs.model_validate({"criteria_inputs": {"13": {"awarded_points": 2}}})
        with pytest.raises(ValueError):
            SiteAssessmentInputs.model_validate(
                {
                    "criteria_inputs": {"1": {"awarded_points": 2}},
                    "criteria_facts": {"1": {"percentage": 10}},
                }
            )

    @patch("fpac_soil_mcp.mcp.tools.soil_lookup_tools.SDAClient")
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

    @patch("fpac_soil_mcp.mcp.tools.spatial_analysis_tools.CorridorAnalyzer")
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
            productivity_index="NCCPI",
            include_map=False,
        )

    @patch("fpac_soil_mcp.mcp.tools.spatial_analysis_tools.CorridorAnalyzer")
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
            productivity_index="NCCPI",
            max_county_rating_override=88.0,
            include_map=False,
        )

    @patch("fpac_soil_mcp.mcp.tools.spatial_analysis_tools.CorridorAnalyzer")
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
        )

        mock_instance.analyze_corridor.assert_called_once_with(
            centerline_input="LINESTRING(-93.5 42.0, -93.4 42.1)",
            buffer_distance=50.0,
            buffer_units="feet",
            indirect_geometry_input=None,
            alternatives=None,
            productivity_index="CSR2",
            include_map=False,
        )

    @patch("fpac_soil_mcp.mcp.tools.spatial_analysis_tools.CorridorAnalyzer")
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

    @patch("fpac_soil_mcp.mcp.tools.spatial_analysis_tools.CorridorAnalyzer")
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


@pytest.mark.parametrize("include_map", [False, True])
@patch("fpac_soil_mcp.mcp.tools.spatial_analysis_tools.PolygonAnalyzer")
def test_analyze_farmland_by_polygon_forwards_include_map(
    mock_analyzer_cls: MagicMock, include_map: bool
) -> None:
    analyze_farmland_by_polygon({"type": "Polygon", "coordinates": []}, include_map=include_map)
    kwargs = mock_analyzer_cls.return_value.analyze_polygon.call_args.kwargs
    assert kwargs["include_map"] is include_map


@pytest.mark.parametrize("include_map", [False, True])
@patch("fpac_soil_mcp.mcp.tools.spatial_analysis_tools.CorridorAnalyzer")
def test_analyze_corridor_fppa_forwards_include_map(
    mock_analyzer_cls: MagicMock, include_map: bool
) -> None:
    mock_response = MagicMock()
    mock_response.model_dump.return_value = {"query_type": "corridor"}
    mock_analyzer_cls.return_value.analyze_corridor.return_value = mock_response
    analyze_corridor_fppa(
        centerline="LINESTRING(-93.5 42.0, -93.4 42.1)",
        buffer_distance=50.0,
        include_map=include_map,
    )
    kwargs = mock_analyzer_cls.return_value.analyze_corridor.call_args.kwargs
    assert kwargs["include_map"] is include_map
