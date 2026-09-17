"""Tests for Census TIGERweb 2020 Urban Areas Client."""

import httpx
import pytest

from fpac_soil_mcp.integration_models import IntegrationStatus
from fpac_soil_mcp.tigerweb_client import TigerwebClient


@pytest.fixture
def sample_geojson():
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [-86.16, 39.76],
                [-86.15, 39.76],
                [-86.15, 39.77],
                [-86.16, 39.77],
                [-86.16, 39.76],
            ]
        ],
    }


def test_tigerweb_intersected_success(sample_geojson):
    mock_response = {
        "features": [
            {
                "attributes": {
                    "GEOID": "40996",
                    "NAME": "Indianapolis, IN",
                    "POP100": 887642,
                    "HU100": 395800,
                }
            }
        ]
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert b"esriGeometryPolygon" in request.content
        return httpx.Response(200, json=mock_response)

    client = TigerwebClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))
    record = client.check_urban_exemption(sample_geojson)

    assert record.status == IntegrationStatus.SUCCESS
    assert record.is_urban_intersected is True
    assert record.urban_area_names == ["Indianapolis, IN"]
    assert record.geometry_hash.startswith("sha256:")


def test_tigerweb_non_intersected_rural(sample_geojson):
    mock_response = {"features": []}

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=mock_response)

    client = TigerwebClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))
    record = client.check_urban_exemption(sample_geojson)

    assert record.status == IntegrationStatus.SUCCESS
    assert record.is_urban_intersected is False
    assert record.urban_area_names == []


def test_tigerweb_error_handling(sample_geojson):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Internal Server Error")

    client = TigerwebClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))
    record = client.check_urban_exemption(sample_geojson)

    assert record.status == IntegrationStatus.ERROR
    assert record.error_message is not None
    assert "Urban screening failed" in record.error_message
