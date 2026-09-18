"""Tests for Census TIGERweb 2020 Urban Areas Client."""

import json
from urllib.parse import parse_qs

import httpx
import pytest
from shapely.geometry import LinearRing, MultiPolygon, Polygon

from fpac_soil_mcp.integration_models import IntegrationStatus
from fpac_soil_mcp.tigerweb_client import (
    TigerwebClient,
    _normalize_ring_winding,
    _polygon_to_esri_rings,
)


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


def test_ring_winding_normalization_helpers():
    # Counter-clockwise coordinates (standard GeoJSON exterior)
    ccw_coords = [
        [-86.16, 39.76],
        [-86.14, 39.76],
        [-86.14, 39.78],
        [-86.16, 39.78],
        [-86.16, 39.76],
    ]
    ring = LinearRing(ccw_coords)
    assert ring.is_ccw is True

    # Normalize to clockwise (exterior)
    cw_normalized = _normalize_ring_winding(ring, clockwise=True)
    assert LinearRing(cw_normalized).is_ccw is False

    # Normalize to counterclockwise (interior hole)
    ccw_normalized = _normalize_ring_winding(ring, clockwise=False)
    assert LinearRing(ccw_normalized).is_ccw is True

    # Clockwise coordinates
    cw_coords = [
        [-86.16, 39.76],
        [-86.16, 39.78],
        [-86.14, 39.78],
        [-86.14, 39.76],
        [-86.16, 39.76],
    ]
    ring_cw = LinearRing(cw_coords)
    assert ring_cw.is_ccw is False

    cw_normalized_from_cw = _normalize_ring_winding(ring_cw, clockwise=True)
    assert LinearRing(cw_normalized_from_cw).is_ccw is False

    ccw_normalized_from_cw = _normalize_ring_winding(ring_cw, clockwise=False)
    assert LinearRing(ccw_normalized_from_cw).is_ccw is True


def test_polygon_to_esri_rings_multipolygon_winding():
    # MultiPolygon with 2 polygons, one having an interior ring
    poly1 = Polygon(
        shell=[[-86.16, 39.76], [-86.14, 39.76], [-86.14, 39.78], [-86.16, 39.78], [-86.16, 39.76]],
        holes=[
            [
                [-86.155, 39.765],
                [-86.155, 39.775],
                [-86.145, 39.775],
                [-86.145, 39.765],
                [-86.155, 39.765],
            ]
        ],
    )
    poly2 = Polygon(
        shell=[[-86.10, 39.76], [-86.08, 39.76], [-86.08, 39.78], [-86.10, 39.78], [-86.10, 39.76]]
    )
    mp = MultiPolygon([poly1, poly2])

    rings = _polygon_to_esri_rings(mp)
    assert len(rings) == 3

    # Ring 0: exterior of poly1 (must be CW -> is_ccw is False)
    assert LinearRing(rings[0]).is_ccw is False
    # Ring 1: interior hole of poly1 (must be CCW -> is_ccw is True)
    assert LinearRing(rings[1]).is_ccw is True
    # Ring 2: exterior of poly2 (must be CW -> is_ccw is False)
    assert LinearRing(rings[2]).is_ccw is False


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


def test_tigerweb_point_geometry_success():
    point_geojson = {
        "type": "Point",
        "coordinates": [-86.1581, 39.7684],
    }
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
        assert b"esriGeometryPoint" in request.content
        assert b"-86.1581" in request.content
        return httpx.Response(200, json=mock_response)

    client = TigerwebClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))
    record = client.check_urban_exemption(point_geojson)

    assert record.status == IntegrationStatus.SUCCESS
    assert record.is_urban_intersected is True
    assert record.urban_area_names == ["Indianapolis, IN"]


def test_tigerweb_polygon_with_interior_rings():
    polygon_with_hole = {
        "type": "Polygon",
        "coordinates": [
            [
                [-86.16, 39.76],
                [-86.14, 39.76],
                [-86.14, 39.78],
                [-86.16, 39.78],
                [-86.16, 39.76],
            ],
            [
                [-86.155, 39.765],
                [-86.145, 39.765],
                [-86.145, 39.775],
                [-86.155, 39.775],
                [-86.155, 39.765],
            ],
        ],
    }
    mock_response = {"features": []}

    def handler(request: httpx.Request) -> httpx.Response:
        assert b"esriGeometryPolygon" in request.content
        # Verify rings are properly formatted and normalized in the posted data
        body = parse_qs(request.content.decode("utf-8"))
        geom_json = json.loads(body["geometry"][0])
        rings = geom_json["rings"]
        assert len(rings) == 2
        # Exterior ring should be CW (is_ccw is False)
        assert LinearRing(rings[0]).is_ccw is False
        # Interior hole ring should be CCW (is_ccw is True)
        assert LinearRing(rings[1]).is_ccw is True
        return httpx.Response(200, json=mock_response)

    client = TigerwebClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))
    record = client.check_urban_exemption(polygon_with_hole)

    assert record.status == IntegrationStatus.SUCCESS


def test_tigerweb_error_handling(sample_geojson):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Internal Server Error")

    client = TigerwebClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))
    record = client.check_urban_exemption(sample_geojson)

    assert record.status == IntegrationStatus.ERROR
    assert record.error_message is not None
    assert "Urban screening failed" in record.error_message


def test_tigerweb_get_intersecting_counties_and_partitioning():
    mock_county_response = {
        "features": [
            {
                "attributes": {
                    "GEOID": "19169",
                    "NAME": "Story County",
                    "BASENAME": "Story",
                    "STATE": "19",
                    "COUNTY": "169",
                },
                "geometry": {
                    "rings": [
                        [
                            [-93.70, 41.85],
                            [-93.35, 41.85],
                            [-93.35, 42.15],
                            [-93.70, 42.15],
                            [-93.70, 41.85],
                        ]
                    ]
                },
            },
            {
                "attributes": {
                    "GEOID": "19015",
                    "NAME": "Boone County",
                    "BASENAME": "Boone",
                    "STATE": "19",
                    "COUNTY": "015",
                },
                "geometry": {
                    "rings": [
                        [
                            [-94.05, 41.85],
                            [-93.70, 41.85],
                            [-93.70, 42.15],
                            [-94.05, 42.15],
                            [-94.05, 41.85],
                        ]
                    ]
                },
            },
        ]
    }

    def county_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=mock_county_response)

    client = TigerwebClient(http_client=httpx.Client(transport=httpx.MockTransport(county_handler)))

    # Line spanning both counties: from Boone (-93.8) to Story (-93.5)
    corridor_box = {
        "type": "Polygon",
        "coordinates": [
            [
                [-93.85, 42.00],
                [-93.45, 42.00],
                [-93.45, 42.02],
                [-93.85, 42.02],
                [-93.85, 42.00],
            ]
        ],
    }

    counties = client.get_intersecting_counties(corridor_box)
    assert len(counties) == 2
    assert {c["county_name"] for c in counties} == {"Story", "Boone"}

    segments = client.partition_geometry_by_counties(corridor_box, counties=counties)
    assert len(segments) == 2
    assert segments[0]["calculated_acres"] > 0
    assert segments[1]["calculated_acres"] > 0
