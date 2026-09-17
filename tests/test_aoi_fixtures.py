"""Tests verifying 50 benchmark AOI fixtures match acreage within 0.1% tolerance."""

import json
from pathlib import Path

from fpac_soil_mcp.geometry import calculate_acreage, parse_geojson_geometry

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "aoi" / "benchmark_50_aois.json"


def test_50_benchmark_aois_acreage_tolerance():
    with open(FIXTURE_PATH, encoding="utf-8") as f:
        data = json.load(f)

    fixtures = data.get("fixtures", [])
    assert len(fixtures) == 50

    for item in fixtures:
        aoi_id = item["id"]
        geom_json = item["geometry"]
        expected_acreage = item["expected_acreage"]

        parsed_geom = parse_geojson_geometry(geom_json)
        calculated_acreage = calculate_acreage(parsed_geom)

        # Verify acreage within 0.1% tolerance or 0.05 acre absolute precision
        diff = abs(calculated_acreage - expected_acreage)
        rel_diff = diff / expected_acreage if expected_acreage > 0 else 0.0

        assert rel_diff <= 0.001 or diff <= 0.05, (
            f"Fixture {aoi_id} failed acreage tolerance: "
            f"calculated={calculated_acreage}, expected={expected_acreage}, diff={diff}"
        )
