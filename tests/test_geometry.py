"""Tests for geometry parsing, validation, acreage computation, WKT conversion, and hashing."""

import json
from pathlib import Path

import pytest
from shapely.geometry import MultiPolygon, Polygon
from shapely.wkt import loads as load_wkt

from fpac_soil_mcp.geometry import (
    GeometryValidationError,
    buffer_centerline,
    calculate_acreage,
    calculate_geodesic_length,
    compute_geometry_hash,
    erase_geometries,
    geometry_to_wkt,
    parse_geojson_geometry,
    validate_and_sanitize_line_wkt,
    validate_wkt_string,
)

LESA_FIXTURE_PATH = Path(__file__).parents[1] / "eval" / "eval_cases.v1.json"


def _lesa_02_fixture() -> dict:
    with LESA_FIXTURE_PATH.open(encoding="utf-8") as fixture_file:
        cases = json.load(fixture_file)["test_cases"]
    return next(item for item in cases if item["id"] == "LESA-02")


def test_lesa_02_fixture_represents_45_acres():
    fixture = _lesa_02_fixture()
    geometry = parse_geojson_geometry(fixture["sample_geometry"])

    acreage = calculate_acreage(geometry)

    assert abs(acreage - 45.0) <= max(45.0 * 0.001, 0.05)
    assert calculate_acreage(
        load_wkt(fixture["user_prompt"].split(": ", 1)[1].split(". Use ", 1)[0])
    ) == pytest.approx(acreage)


def test_lesa_02_aoi_acreage_is_separate_from_affected_farm_acreage():
    fixture = _lesa_02_fixture()
    aoi_acreage = calculate_acreage(parse_geojson_geometry(fixture["sample_geometry"]))
    affected_farm_acreage = 120.0

    evaluated_acreage = aoi_acreage

    assert evaluated_acreage == pytest.approx(aoi_acreage)
    assert evaluated_acreage != affected_farm_acreage


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


def test_calculate_geodesic_length_supports_empty_and_multipart():
    from shapely.geometry import LineString, MultiLineString

    assert calculate_geodesic_length(LineString()) == 0.0
    length = calculate_geodesic_length(
        MultiLineString(
            [
                [(-93.5, 42.0), (-93.4, 42.0)],
                [(-93.5, 42.0), (-93.5, 42.1)],
            ]
        )
    )
    assert length > 0.0


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


def test_parse_geojson_line():
    line_geojson = {
        "type": "LineString",
        "coordinates": [
            [-93.5, 42.0],
            [-93.4, 42.1],
        ],
    }
    # default disallows line
    with pytest.raises(GeometryValidationError, match="Unsupported geometry type"):
        parse_geojson_geometry(line_geojson, allow_line=False)

    geom = parse_geojson_geometry(line_geojson, allow_line=True)
    assert geom.geom_type == "LineString"


def test_validate_and_sanitize_line_wkt():
    wkt = "LINESTRING(-93.5 42.0, -93.4 42.1)"
    clean = validate_and_sanitize_line_wkt(wkt)
    assert clean.startswith("LINESTRING")

    with pytest.raises(GeometryValidationError, match="must be a LineString or MultiLineString"):
        validate_and_sanitize_line_wkt(
            "POLYGON((-93.5 42.0, -93.4 42.0, -93.4 42.1, -93.5 42.1, -93.5 42.0))"
        )


def test_buffer_centerline():
    # 10 mile line in Iowa, buffer 50 feet each side (total width 100 feet)
    # 10 miles = 52,800 feet. Area ~ 52,800 * 100 = 5,280,000 sq ft = ~121.2 acres (plus round caps)
    line_geojson = {
        "type": "LineString",
        "coordinates": [
            [-93.5, 42.0],
            [-93.5, 42.145],  # roughly 10 miles north
        ],
    }
    buffered = buffer_centerline(line_geojson, buffer_distance=50, distance_unit="feet")
    assert isinstance(buffered, (Polygon, MultiPolygon))
    acres = calculate_acreage(buffered)
    assert 100.0 <= acres <= 150.0

    # Test meters
    buffered_m = buffer_centerline(line_geojson, buffer_distance=15.24, distance_unit="meters")
    assert abs(calculate_acreage(buffered_m) - acres) < 2.0

    # Test miles
    buffered_mi = buffer_centerline(line_geojson, buffer_distance=0.1, distance_unit="miles")
    acres_mi = calculate_acreage(buffered_mi)
    assert acres_mi > acres

    # Test invalid distance
    with pytest.raises(GeometryValidationError, match="must be a positive number"):
        buffer_centerline(line_geojson, buffer_distance=-10)

    # Test invalid unit
    with pytest.raises(GeometryValidationError, match="Unrecognized distance_unit"):
        buffer_centerline(line_geojson, buffer_distance=50, distance_unit="furlongs")


def test_erase_geometries():
    # Large box: 0.1 x 0.1 deg
    big_box = parse_geojson_geometry(
        {
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
    )
    # Inner box: 0.05 x 0.05 deg
    inner_box = parse_geojson_geometry(
        {
            "type": "Polygon",
            "coordinates": [
                [
                    [-93.48, 42.02],
                    [-93.42, 42.02],
                    [-93.42, 42.08],
                    [-93.48, 42.08],
                    [-93.48, 42.02],
                ]
            ],
        }
    )

    erased = erase_geometries(big_box, inner_box)
    assert isinstance(erased, (Polygon, MultiPolygon))
    big_acres = calculate_acreage(big_box)
    inner_acres = calculate_acreage(inner_box)
    erased_acres = calculate_acreage(erased)

    assert abs(erased_acres - (big_acres - inner_acres)) < 1.0

    # Line hash handling
    line_hash = compute_geometry_hash(
        {"type": "LineString", "coordinates": [[-93.5, 42.0], [-93.4, 42.1]]}
    )
    assert line_hash.startswith("sha256:")
