"""Tests for USDA NASS QuickStats REST API client."""

import httpx
import pytest

from fpac_soil_mcp.config import settings
from fpac_soil_mcp.integration_models import IntegrationStatus
from fpac_soil_mcp.nass_client import NassClient


def test_nass_client_disabled_setting(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "nass_enabled", False)
    client = NassClient(api_key="VALID_KEY")
    profile = client.get_county_ag_profile(
        state_fips="19",
        county_fips="169",
        county_name="Story",
    )
    assert profile.status == IntegrationStatus.UNAVAILABLE
    assert "disabled" in (profile.error_message or "")
    assert profile.census_year == settings.nass_census_year


def test_nass_client_no_key_fallback(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "nass_enabled", True)
    client = NassClient(api_key="")
    profile = client.get_county_ag_profile(
        state_fips="19",
        county_fips="169",
        county_name="Story",
        census_year=2022,
    )
    assert profile.status == IntegrationStatus.UNAVAILABLE
    assert "not configured" in (profile.error_message or "")
    assert profile.provenance.source_name == "USDA NASS Census of Agriculture Quick Stats"


def test_nass_client_default_census_year_propagation(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "nass_enabled", True)
    monkeypatch.setattr(settings, "nass_census_year", 2017)

    requested_urls: list[str] = []

    def nass_handler(request: httpx.Request) -> httpx.Response:
        requested_urls.append(str(request.url))
        return httpx.Response(200, json={"data": []})

    mock_transport = httpx.MockTransport(nass_handler)
    mock_http = httpx.Client(transport=mock_transport)

    client = NassClient(api_key="MOCK_KEY_123", http_client=mock_http)
    profile = client.get_county_ag_profile(
        state_fips="19",
        county_fips="169",
        county_name="Story",
    )

    assert len(requested_urls) == 1
    assert "year=2017" in requested_urls[0]
    assert profile.census_year == 2017
    assert profile.provenance.configuration_version == "census_2017"


def test_nass_client_success_mock(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "nass_enabled", True)
    mock_response_data = {
        "data": [
            {
                "short_desc": "AG LAND - ACRES",
                "Value": "335,120",
            },
            {
                "short_desc": "AG LAND, CROPLAND, HARVESTED - ACRES",
                "Value": "295,450",
            },
            {
                "short_desc": "FARM OPERATIONS - NUMBER OF OPERATIONS",
                "Value": "812",
            },
            {
                "short_desc": "FARM OPERATIONS - ACRES / OPERATION",
                "Value": "413",
            },
        ]
    }

    def nass_handler(request: httpx.Request) -> httpx.Response:
        assert "key=MOCK_KEY_123" in str(request.url)
        assert "state_fips_code=19" in str(request.url)
        assert "county_code=169" in str(request.url)
        return httpx.Response(200, json=mock_response_data)

    mock_transport = httpx.MockTransport(nass_handler)
    mock_http = httpx.Client(transport=mock_transport)

    client = NassClient(api_key="MOCK_KEY_123", http_client=mock_http)
    profile = client.get_county_ag_profile(
        state_fips="19",
        county_fips="169",
        county_name="Story",
        census_year=2022,
    )

    assert profile.status == IntegrationStatus.SUCCESS
    assert profile.land_in_farms_acres == 335120.0
    assert profile.total_cropland_acres == 295450.0
    assert profile.farm_count == 812
    assert profile.average_farm_size_acres == 413.0
    assert len(profile.unavailable_fields) == 0


def test_nass_client_withheld_data_and_404(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "nass_enabled", True)
    mock_response_data = {
        "data": [
            {
                "short_desc": "AG LAND - ACRES",
                "Value": "(D)",
            },
            {
                "short_desc": "FARM OPERATIONS - NUMBER OF OPERATIONS",
                "Value": "15",
            },
        ]
    }

    def nass_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=mock_response_data)

    mock_transport = httpx.MockTransport(nass_handler)
    mock_http = httpx.Client(transport=mock_transport)

    client = NassClient(api_key="MOCK_KEY_123", http_client=mock_http)
    profile = client.get_county_ag_profile(
        state_fips="19",
        county_fips="169",
        county_name="Story",
        census_year=2022,
    )

    assert profile.status == IntegrationStatus.SUCCESS
    assert profile.land_in_farms_acres is None
    assert profile.farm_count == 15
    assert "AG LAND - ACRES" in profile.unavailable_fields


def test_nass_client_http_error(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "nass_enabled", True)

    def nass_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Internal Server Error")

    mock_transport = httpx.MockTransport(nass_handler)
    mock_http = httpx.Client(transport=mock_transport)

    client = NassClient(api_key="MOCK_KEY_123", http_client=mock_http)
    profile = client.get_county_ag_profile(
        state_fips="19",
        county_fips="169",
        county_name="Story",
        census_year=2022,
    )

    assert profile.status == IntegrationStatus.ERROR
    assert "USDA NASS query error" in (profile.error_message or "")
