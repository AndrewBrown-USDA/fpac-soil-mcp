"""Unit tests for FastMCP tools: soil_tools and fppa_tools."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from fpac_soil_mcp.constants import (
    FARMLAND_CLASS_DEFINITIONS,
    REGULATORY_LIMITATIONS,
    REGULATORY_NOTICE,
)
from fpac_soil_mcp.models import (
    FarmlandClassificationResponse,
    FarmlandClassListResponse,
    FppaScopeResponse,
)
from fpac_soil_mcp.sda_client import SDAQueryError, SDAValidationError
from fpac_soil_mcp.tools.fppa_tools import (
    explain_fppa_screening_scope,
    list_farmland_classes,
)
from fpac_soil_mcp.tools.soil_tools import (
    get_farmland_classification_by_mukey,
    get_farmland_classification_by_point,
)


class TestSoilTools:
    """Tests for get_farmland_classification_by_point and get_farmland_classification_by_mukey."""

    @patch("fpac_soil_mcp.tools.soil_tools.SDAClient")
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

    @patch("fpac_soil_mcp.tools.soil_tools.SDAClient")
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

    @patch("fpac_soil_mcp.tools.soil_tools.SDAClient")
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

    @patch("fpac_soil_mcp.tools.soil_tools.SDAClient")
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

    @patch("fpac_soil_mcp.tools.soil_tools.SDAClient")
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

    @patch("fpac_soil_mcp.tools.soil_tools.SDAClient")
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

    @patch("fpac_soil_mcp.tools.soil_tools.SDAClient")
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
