"""Tests for geometry parsing, validation, acreage computation, WKT conversion, and hashing."""

import pytest
from shapely.geometry import MultiPolygon, Polygon

from fpac_soil_mcp.geometry import (
    GeometryValidationError,
    calculate_acreage,
    compute_geometry_hash,
    geometry_to_wkt,
    parse_geojson_geometry,
    validate_wkt_string,
)


def test_validate_wkt_string_valid():
    wkt = "POLYGON((-93.5 42.0, -93.4 42.0, -93.4 42.1, -93.5 42.1, -93.5 42.0))"
    assert validate_wkt_string(wkt) == wkt


def test_validate_wkt_string_invalid():
    with pytest.raises(GeometryValidationError, match="cannot be empty"):
        validate_wkt_string("   ")

    with pytest.raises(GeometryValidationError, match="Must begin with a recognized"):
        validate_wkt_string("SELECT * FROM table; DROP TABLE;")


def test_parse_geojson_polygon():
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
    geom = parse_geojson_geometry(geojson)
    assert isinstance(geom, Polygon)
    assert geom.is_valid


def test_parse_geojson_multipolygon():
    geojson = {
        "type": "MultiPolygon",
        "coordinates": [
            [
                [
                    [-93.5, 42.0],
                    [-93.4, 42.0],
                    [-93.4, 42.1],
                    [-93.5, 42.1],
                    [-93.5, 42.0],
                ]
            ],
            [
                [
                    [-93.3, 42.0],
                    [-93.2, 42.0],
                    [-93.2, 42.1],
                    [-93.3, 42.1],
                    [-93.3, 42.0],
                ]
            ],
        ],
    }
    geom = parse_geojson_geometry(geojson)
    assert isinstance(geom, MultiPolygon)
    assert len(geom.geoms) == 2


def test_parse_geojson_feature_wrapper():
    feature = {
        "type": "Feature",
        "properties": {"name": "Test Site"},
        "geometry": {
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
        },
    }
    geom = parse_geojson_geometry(feature)
    assert isinstance(geom, Polygon)


def test_parse_geojson_invalid_type():
    with pytest.raises(GeometryValidationError, match="Unsupported geometry type"):
        parse_geojson_geometry({"type": "Point", "coordinates": [-93.5, 42.0]})


def test_parse_geojson_invalid_coordinates():
    with pytest.raises(GeometryValidationError, match="Longitude coordinates outside valid range"):
        parse_geojson_geometry(
            {
                "type": "Polygon",
                "coordinates": [
                    [
                        [-200.0, 42.0],
                        [-190.0, 42.0],
                        [-190.0, 42.1],
                        [-200.0, 42.1],
                        [-200.0, 42.0],
                    ]
                ],
            }
        )


def test_calculate_acreage_accuracy():
    # Roughly 1 square mile in Iowa: 1 section ~ 640 acres
    # 1 deg lon at 42 deg N ~ 82.6 km, 1 deg lat ~ 111.0 km
    # A small 0.01 x 0.01 deg box (~826m x 1110m = 916,860 m2 = ~226.56 acres)
    geojson = {
        "type": "Polygon",
        "coordinates": [
            [
                [-93.51, 42.00],
                [-93.50, 42.00],
                [-93.50, 42.01],
                [-93.51, 42.01],
                [-93.51, 42.00],
            ]
        ],
    }
    geom = parse_geojson_geometry(geojson)
    acres = calculate_acreage(geom)
    assert 220.0 <= acres <= 235.0


def test_geometry_to_wkt_and_hash():
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
    geom = parse_geojson_geometry(geojson)
    wkt = geometry_to_wkt(geom)
    assert wkt.startswith("POLYGON")

    geom_hash = compute_geometry_hash(geom)
    assert geom_hash.startswith("sha256:")
    assert len(geom_hash) == 71  # "sha256:" + 64 hex characters

    # Reproducibility
    assert compute_geometry_hash(geojson) == geom_hash
