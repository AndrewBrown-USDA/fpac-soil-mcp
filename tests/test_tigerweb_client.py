"""Tests for Census TIGERweb 2020 Urban Areas Client."""

import json
from urllib.parse import parse_qs

import httpx
import pytest
from shapely.geometry import LinearRing, MultiPolygon, Polygon

from fpac_soil_mcp.integration_models import CountyPartitionGeometry, IntegrationStatus
from fpac_soil_mcp.tigerweb_client import (
    TigerwebClient,
    _esri_rings_to_geometry,
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
    assert all(isinstance(s, CountyPartitionGeometry) for s in segments)
    assert segments[0].calculated_acres > 0
    assert segments[1].calculated_acres > 0
    assert {s.county_name for s in segments} == {"Story", "Boone"}

    # Validate backward compatibility with dictionary access and .get()
    assert segments[0]["state_fips"] == "19"
    assert segments[0].get("county_fips") in {"169", "015"}
    assert segments[0]["calculated_acres"] > 0
    assert segments[0].get("state_name") is None
    assert segments[0].get("non_existent_key", "default_val") == "default_val"

    # Fallback on empty counties
    fallback_segments = client.partition_geometry_by_counties(corridor_box, counties=[])
    assert len(fallback_segments) == 1
    assert isinstance(fallback_segments[0], CountyPartitionGeometry)
    assert fallback_segments[0].county_name == "Unsegmented Area"
    assert fallback_segments[0]["state_fips"] == "00"
    assert fallback_segments[0]["calculated_acres"] > 0


def test_esri_rings_to_geometry_single_ring():
    # CW ring
    cw_ring = [
        [-86.16, 39.76],
        [-86.16, 39.78],
        [-86.14, 39.78],
        [-86.14, 39.76],
        [-86.16, 39.76],
    ]
    geom = _esri_rings_to_geometry([cw_ring])
    assert isinstance(geom, Polygon)
    assert geom.is_valid
    assert len(geom.interiors) == 0
    assert pytest.approx(geom.area, 1e-6) == 0.0004


def test_esri_rings_to_geometry_with_hole():
    # Outer ring: CW box [0,0] to [10,10] (area 100)
    outer = [
        [0.0, 0.0],
        [0.0, 10.0],
        [10.0, 10.0],
        [10.0, 0.0],
        [0.0, 0.0],
    ]
    # Hole ring: CCW box [2,2] to [4,4] (area 4)
    hole = [
        [2.0, 2.0],
        [4.0, 2.0],
        [4.0, 4.0],
        [2.0, 4.0],
        [2.0, 2.0],
    ]
    assert LinearRing(outer).is_ccw is False
    assert LinearRing(hole).is_ccw is True

    geom = _esri_rings_to_geometry([outer, hole])
    assert isinstance(geom, Polygon)
    assert geom.is_valid
    assert len(geom.interiors) == 1
    # Area should be 100 - 4 = 96
    assert pytest.approx(geom.area, 1e-6) == 96.0


def test_esri_rings_to_geometry_multipart_with_hole():
    # Poly1 Outer: CW [0,0] to [10,10] (area 100)
    outer1 = [
        [0.0, 0.0],
        [0.0, 10.0],
        [10.0, 10.0],
        [10.0, 0.0],
        [0.0, 0.0],
    ]
    # Poly1 Hole: CCW [2,2] to [4,4] (area 4)
    hole1 = [
        [2.0, 2.0],
        [4.0, 2.0],
        [4.0, 4.0],
        [2.0, 4.0],
        [2.0, 2.0],
    ]
    # Poly2 Outer: CW [20,20] to [30,30] (area 100)
    outer2 = [
        [20.0, 20.0],
        [20.0, 30.0],
        [30.0, 30.0],
        [30.0, 20.0],
        [20.0, 20.0],
    ]

    geom = _esri_rings_to_geometry([outer1, hole1, outer2])
    assert isinstance(geom, MultiPolygon)
    assert geom.is_valid
    assert len(geom.geoms) == 2
    # Total area: (100 - 4) + 100 = 196
    assert pytest.approx(geom.area, 1e-6) == 196.0

    poly1 = next(p for p in geom.geoms if p.bounds[0] < 15)
    poly2 = next(p for p in geom.geoms if p.bounds[0] > 15)
    assert len(poly1.interiors) == 1
    assert len(poly2.interiors) == 0


def test_esri_rings_to_geometry_non_standard_winding_fallback():
    # All CCW rings: outer [0,0] to [10,10], hole [2,2] to [4,4]
    outer_ccw = [
        [0.0, 0.0],
        [10.0, 0.0],
        [10.0, 10.0],
        [0.0, 10.0],
        [0.0, 0.0],
    ]
    hole_ccw = [
        [2.0, 2.0],
        [4.0, 2.0],
        [4.0, 4.0],
        [2.0, 4.0],
        [2.0, 2.0],
    ]
    assert LinearRing(outer_ccw).is_ccw is True
    assert LinearRing(hole_ccw).is_ccw is True

    geom = _esri_rings_to_geometry([outer_ccw, hole_ccw])
    assert isinstance(geom, Polygon)
    assert geom.is_valid
    assert len(geom.interiors) == 1
    assert pytest.approx(geom.area, 1e-6) == 96.0


def test_esri_rings_to_geometry_edge_cases():
    assert _esri_rings_to_geometry([]) is None
    assert _esri_rings_to_geometry([[]]) is None
    # Ring with less than 4 points
    assert _esri_rings_to_geometry([[[0.0, 0.0], [1.0, 1.0], [0.0, 0.0]]]) is None


def test_tigerweb_county_query_donut_county():
    # Mock county with an enclave hole (e.g. independent city or water body hole)
    outer_ring = [
        [-94.0, 42.0],
        [-94.0, 43.0],
        [-93.0, 43.0],
        [-93.0, 42.0],
        [-94.0, 42.0],
    ]
    hole_ring = [
        [-93.6, 42.4],
        [-93.4, 42.4],
        [-93.4, 42.6],
        [-93.6, 42.6],
        [-93.6, 42.4],
    ]
    mock_county_response = {
        "features": [
            {
                "attributes": {
                    "GEOID": "19999",
                    "NAME": "Donut County",
                    "BASENAME": "Donut",
                    "STATE": "19",
                    "COUNTY": "999",
                },
                "geometry": {
                    "rings": [outer_ring, hole_ring],
                },
            }
        ]
    }

    def county_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=mock_county_response)

    client = TigerwebClient(http_client=httpx.Client(transport=httpx.MockTransport(county_handler)))
    counties = client.get_intersecting_counties(
        Polygon([[-94.0, 42.0], [-94.0, 43.0], [-93.0, 43.0], [-93.0, 42.0], [-94.0, 42.0]])
    )

    assert len(counties) == 1
    county_geom = counties[0]["geometry"]
    assert isinstance(county_geom, Polygon)
    assert len(county_geom.interiors) == 1
    # Outer box area is 1.0, hole is 0.2*0.2 = 0.04 -> county area is 0.96
    assert pytest.approx(county_geom.area, 1e-6) == 0.96


def test_esri_rings_to_geometry_non_standard_all_cw_winding_fallback():
    # All CW rings: outer [0,0] to [10,10], hole [2,2] to [4,4]
    outer_cw = [
        [0.0, 0.0],
        [0.0, 10.0],
        [10.0, 10.0],
        [10.0, 0.0],
        [0.0, 0.0],
    ]
    hole_cw = [
        [2.0, 2.0],
        [2.0, 4.0],
        [4.0, 4.0],
        [4.0, 2.0],
        [2.0, 2.0],
    ]
    assert LinearRing(outer_cw).is_ccw is False
    assert LinearRing(hole_cw).is_ccw is False

    geom = _esri_rings_to_geometry([outer_cw, hole_cw])
    assert isinstance(geom, Polygon)
    assert geom.is_valid
    assert len(geom.interiors) == 1
    assert pytest.approx(geom.area, 1e-6) == 96.0
