"""Tests for multi-county linear corridor fixtures and benchmark parameters."""

import json
from pathlib import Path

from shapely.geometry import MultiPolygon, Polygon

from fpac_soil_mcp.spatial.geometry import (
    buffer_centerline,
    calculate_acreage,
    erase_geometries,
    parse_geojson_geometry,
)


def test_corridor_fixtures_corpus():
    fixture_path = Path(__file__).parent / "fixtures" / "corridor" / "multi_county_corridors.json"
    assert fixture_path.exists()

    data = json.loads(fixture_path.read_text(encoding="utf-8"))
    fixtures = data.get("fixtures", [])
    assert len(fixtures) >= 3

    for f in fixtures:
        centerline = f["centerline"]
        dist = f["buffer_distance"]
        unit = f["buffer_units"]

        # 1. Centerline parsing
        line_geom = parse_geojson_geometry(centerline, allow_line=True)
        assert line_geom.geom_type in ("LineString", "MultiLineString")

        # 2. Buffering
        buffered = buffer_centerline(centerline, buffer_distance=dist, distance_unit=unit)
        assert isinstance(buffered, (Polygon, MultiPolygon))
        assert buffered.is_valid

        # 3. Acreage calculation within benchmark envelope
        acres = calculate_acreage(buffered)
        assert f["expected_direct_acres_min"] <= acres <= f["expected_direct_acres_max"]

        # 4. Indirect geometry separation (if provided)
        if "indirect_geometry" in f:
            indirect = parse_geojson_geometry(f["indirect_geometry"])
            erased_indirect = erase_geometries(indirect, buffered)
            assert isinstance(erased_indirect, (Polygon, MultiPolygon))
            # Direct footprint and erased indirect footprint should have disjoint interiors
            assert buffered.intersection(erased_indirect).area < 1e-9
