"""Tests for the server map result contract (ADR 0017). Synthetic geometry only."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError
from shapely.geometry import Point, Polygon, shape

from fpac_soil_mcp.config import Settings
from fpac_soil_mcp.map_contract import (
    FARMLAND_CLASS_VALUES,
    MAP_SCHEMA_VERSION,
    MapBlock,
    MapLegendItem,
    ResultAuthority,
    bounds_of,
    build_layer,
    build_map_block,
    enforce_size_cap,
    farmland_legend,
    features_from_sda_rows,
    simplify_for_display,
)
from fpac_soil_mcp.models import (
    CorridorFarmlandAnalysisResponse,
    CorridorImpactBreakdown,
    FarmlandCategoryBreakdown,
    PolygonFarmlandAnalysisResponse,
    QuerySource,
)
from fpac_soil_mcp.polygon_analysis import categorize_farmland_class

MARKER = "R6-MARKER"
SQUARE = Polygon([(0, 0), (0.01, 0), (0.01, 0.01), (0, 0.01), (0, 0)])


def _dense_square(points_per_side: int = 200) -> Polygon:
    """Square with many collinear-ish vertices and sub-metre jitter on each edge."""
    step = 0.01 / points_per_side
    coords = []
    for i in range(points_per_side):
        coords.append((i * step, 1e-7 if i % 2 else 0.0))
    for i in range(points_per_side):
        coords.append((0.01, i * step))
    for i in range(points_per_side):
        coords.append((0.01 - i * step, 0.01))
    for i in range(points_per_side):
        coords.append((0.0, 0.01 - i * step))
    coords.append(coords[0])
    return Polygon(coords)


def _layer(layer_id: str, include_map: bool, geom=SQUARE, tolerance=None):
    return build_layer(
        layer_id=layer_id,
        title=f"{MARKER} {layer_id}",
        kind="polygon",
        authority="machine_estimate",
        source="synthetic",
        features=[(geom, {"name": MARKER})],
        include_map=include_map,
        simplify_tolerance_m=tolerance,
    )


def test_layer_omitted_by_default_has_no_geometry():
    layer = _layer("aoi", include_map=False)
    assert layer.delivery == "omitted"
    assert layer.feature_collection is None
    assert layer.feature_count is None
    assert layer.simplified is False
    block = build_map_block([layer], max_bytes=2_000_000)
    assert block.bounds is None
    dumped = json.dumps(block.model_dump())
    assert "coordinates" not in dumped


def test_layer_inline_when_requested():
    layer = _layer("aoi", include_map=True)
    assert layer.delivery == "inline_geojson"
    assert layer.feature_count == 1
    feature = layer.feature_collection["features"][0]
    assert feature["properties"] == {"name": MARKER}
    assert shape(feature["geometry"]).equals(SQUARE)
    block = build_map_block([layer], max_bytes=2_000_000)
    assert block.bounds == [0.0, 0.0, 0.01, 0.01]
    assert block.display_crs == "EPSG:4326"


def test_simplification_flags_and_reduces_vertices():
    dense = _dense_square()
    layer = _layer("farmland_classes", include_map=True, geom=dense, tolerance=1.0)
    assert layer.simplified is True
    assert layer.simplify_tolerance_m == 1.0
    simplified = shape(layer.feature_collection["features"][0]["geometry"])
    assert len(simplified.exterior.coords) < len(dense.exterior.coords)
    assert simplified.is_valid
    # Display copy stays within about a metre of the exact shape (area check).
    assert simplified.area == pytest.approx(dense.area, rel=1e-3)


def test_simplify_zero_tolerance_keeps_geometry():
    assert simplify_for_display([SQUARE], 0.0)[0] is SQUARE
    layer = _layer("aoi", include_map=True, tolerance=0.0)
    assert layer.simplified is False
    assert layer.simplify_tolerance_m is None


def test_size_cap_drops_whole_layers_from_the_end():
    first = _layer("aoi", include_map=True)
    second = _layer("farmland_classes", include_map=True, geom=_dense_square())
    first_bytes = len(json.dumps(first.feature_collection, separators=(",", ":")))
    block = build_map_block([first, second], max_bytes=first_bytes + 10)

    assert block.layers[0].delivery == "inline_geojson"
    assert block.layers[0].truncated is False
    assert block.layers[1].delivery == "omitted"
    assert block.layers[1].truncated is True
    assert block.layers[1].feature_collection is None
    assert len(block.warnings) == 1
    assert f"{MARKER} farmland_classes" in block.warnings[0]
    assert block.bounds == [0.0, 0.0, 0.01, 0.01]


def test_size_cap_can_drop_every_layer():
    block = enforce_size_cap(MapBlock(layers=[_layer("aoi", include_map=True)]), max_bytes=1)
    assert block.layers[0].truncated is True
    assert block.bounds is None


def test_size_cap_leaves_small_block_untouched():
    block = build_map_block([_layer("aoi", include_map=True)], max_bytes=2_000_000)
    assert block.warnings == []
    assert block.layers[0].truncated is False


def test_farmland_legend_matches_classifier_values():
    legend = farmland_legend()
    assert [item.value for item in legend] == list(FARMLAND_CLASS_VALUES)
    samples = [
        "All areas are prime farmland",
        "Prime farmland if drained",
        "Farmland of statewide importance",
        "Farmland of unique importance",
        "Farmland of local importance",
        "Not prime farmland",
        "Some unrecognized SSURGO label",
        None,
    ]
    assert {categorize_farmland_class(s) for s in samples} == set(FARMLAND_CLASS_VALUES)
    by_value = {item.value: item for item in legend}
    assert by_value["prime"].color == "#2E7D32" and by_value["prime"].code == "P"
    assert by_value["statewide"].color == "#F9A825"
    assert by_value["unique"].color == "#6A1B9A"
    assert by_value["local"].color == "#0288D1"
    assert by_value["not_prime"].color == "#9E9E9E"
    assert all(item.code for item in legend)


def test_legend_rejects_bad_colour():
    with pytest.raises(ValidationError):
        MapLegendItem(value="x", label="x", color="green")


def test_features_from_sda_rows_converts_and_skips_bad_rows():
    rows = [
        {
            "mukey": 123,
            "musym": f"{MARKER}A",
            "muname": f"{MARKER} unit",
            "farmlndcl": "All areas are prime farmland",
            "area_ac": "12.345",
            "geom": SQUARE.wkt,
        },
        {"mukey": 456, "geom": None},
        {"mukey": 789, "geom": "NOT WKT"},
        {"mukey": 1011, "farmlndcl": None, "area_ac": "bad", "geom": SQUARE.wkt},
    ]
    features = features_from_sda_rows(rows)
    assert len(features) == 2
    geom, props = features[0]
    assert geom.equals(SQUARE)
    assert props == {
        "mukey": "123",
        "musym": f"{MARKER}A",
        "muname": f"{MARKER} unit",
        "farmlndcl": "All areas are prime farmland",
        "farmland_class": "prime",
        "area_ac": 12.35,
    }
    assert features[1][1]["farmland_class"] == "unmapped"
    assert features[1][1]["area_ac"] == 0.0


def test_bounds_ignore_omitted_layers():
    inline = _layer("aoi", include_map=True)
    omitted = _layer("urban_context", include_map=False, geom=Point(5, 5).buffer(1))
    assert bounds_of([inline, omitted]) == [0.0, 0.0, 0.01, 0.01]


def test_result_authority_is_never_official():
    authority = ResultAuthority()
    assert authority.model_dump() == {
        "level": "machine_estimate",
        "label": "Preliminary Machine Estimate",
        "official_filing": False,
    }
    with pytest.raises(ValidationError):
        ResultAuthority(official_filing=True)


def _source() -> QuerySource:
    return QuerySource(timestamp_utc="2026-01-01T00:00:00Z")


def test_existing_polygon_constructor_validates_without_new_fields():
    response = PolygonFarmlandAnalysisResponse(
        geometry_hash="sha256:" + "0" * 64,
        total_aoi_acres=1.0,
        coverage_status="covered",
        urban_screening={},
        farmland_summary=FarmlandCategoryBreakdown(),
        tabular_csv="",
        source=_source(),
        regulatory_notice=MARKER,
    )
    assert response.schema_version == MAP_SCHEMA_VERSION
    assert response.data_mode == "live"
    assert response.authority.official_filing is False
    assert response.map.layers == []
    assert response.map.bounds is None


def test_existing_corridor_constructor_validates_without_new_fields():
    response = CorridorFarmlandAnalysisResponse(
        geometry_hash="sha256:" + "0" * 64,
        buffer_distance=100.0,
        buffer_units="feet",
        impact_breakdown=CorridorImpactBreakdown(),
        source=_source(),
        regulatory_notice=MARKER,
    )
    dumped = response.model_dump()
    assert dumped["schema_version"] == "1.0"
    assert dumped["map"] == {
        "display_crs": "EPSG:4326",
        "bounds": None,
        "layers": [],
        "warnings": [],
    }


def test_map_settings_defaults_and_validation():
    defaults = Settings(_env_file=None)
    assert defaults.map_simplify_tolerance_m == 1.0
    assert defaults.map_max_geojson_bytes == 2_000_000
    assert Settings(_env_file=None, map_simplify_tolerance_m=0.0).map_simplify_tolerance_m == 0.0
    with pytest.raises(ValidationError):
        Settings(_env_file=None, map_simplify_tolerance_m=-1.0)
    with pytest.raises(ValidationError):
        Settings(_env_file=None, map_max_geojson_bytes=0)
