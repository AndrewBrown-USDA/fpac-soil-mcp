"""Tests for the server map result contract (ADR 0017). Synthetic geometry only."""

from __future__ import annotations

import json

import pytest
from pydantic import BaseModel, ValidationError
from shapely.geometry import Point, Polygon, shape

from fpac_soil_mcp.core.config import Settings
from fpac_soil_mcp.models import (
    CorridorFarmlandAnalysisResponse,
    CorridorImpactBreakdown,
    FarmlandCategoryBreakdown,
    PolygonFarmlandAnalysisResponse,
    QuerySource,
)
from fpac_soil_mcp.spatial.map_builder import (
    FARMLAND_CLASS_VALUES,
    MAP_META_KEY,
    MAP_SCHEMA_VERSION,
    MapBlock,
    MapDisplay,
    MapLayer,
    MapLayerDisplay,
    MapLegendItem,
    ResultAuthority,
    bounds_of,
    build_layer,
    build_map_block,
    categorize_farmland_class,
    enforce_size_cap,
    farmland_legend,
    features_from_sda_rows,
    simplify_for_display,
)

MARKER = "R6-MARKER"
MOVED_FIELDS = (
    "feature_collection",
    "bounds",
    "display_crs",
    "warnings",
    "feature_count",
    "simplified",
    "simplify_tolerance_m",
    "truncated",
)
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


def _schema_text(model: type[BaseModel]) -> str:
    return json.dumps(model.model_json_schema())


def test_body_schemas_have_no_display_fields():
    assert MAP_META_KEY == "gov.usda.fpac-soil/map"
    assert set(MapLayer.model_fields).isdisjoint(MOVED_FIELDS)
    assert set(MapBlock.model_fields) == {"layers"}
    for model in (MapBlock, MapLayer):
        schema = _schema_text(model)
        for name in MOVED_FIELDS:
            assert f'"{name}"' not in schema, (model.__name__, name)
        assert "_display" not in schema
        assert "inline_geojson" not in schema


def test_layer_omitted_by_default_has_no_geometry():
    build = _layer("aoi", include_map=False)
    assert build.layer.delivery == "omitted"
    assert build.display is None
    block = build_map_block([build], max_bytes=2_000_000)
    assert block.display is None
    dumped = json.dumps(block.model_dump())
    assert "coordinates" not in dumped


def test_layer_geometry_only_in_display_when_requested():
    build = _layer("aoi", include_map=True)
    assert build.layer.delivery == "meta_geojson"
    assert build.display.feature_count == 1
    feature = build.display.feature_collection["features"][0]
    assert feature["properties"] == {"name": MARKER}
    assert shape(feature["geometry"]).equals(SQUARE)
    block = build_map_block([build], max_bytes=2_000_000)
    assert "coordinates" not in json.dumps(block.model_dump())
    assert block.display.bounds == [0.0, 0.0, 0.01, 0.01]
    assert block.display.display_crs == "EPSG:4326"
    assert "coordinates" in json.dumps(block.display.model_dump())


def test_body_dump_identical_for_both_flags_except_delivery():
    def body(include_map: bool) -> dict:
        builds = [
            _layer("aoi", include_map=include_map),
            _layer("farmland_classes", include_map=include_map, tolerance=1.0),
        ]
        dumped = build_map_block(builds, max_bytes=2_000_000).model_dump()
        for layer in dumped["layers"]:
            layer.pop("delivery")
        return dumped

    assert body(True) == body(False)


def test_display_survives_revalidation_into_a_parent_model():
    class Holder(BaseModel):
        map: MapBlock = MapBlock()

    block = build_map_block([_layer("aoi", include_map=True)], max_bytes=2_000_000)
    held = Holder(map=block)
    assert held.map.display is not None
    assert held.map.display == block.display
    assert "coordinates" not in json.dumps(held.model_dump())

    response = PolygonFarmlandAnalysisResponse(
        geometry_hash="sha256:" + "0" * 64,
        total_aoi_acres=1.0,
        coverage_status="covered",
        urban_screening={},
        farmland_summary=FarmlandCategoryBreakdown(),
        tabular_csv="",
        source=_source(),
        regulatory_notice=MARKER,
        map=block,
    )
    assert response.map.display == block.display
    assert "coordinates" not in json.dumps(response.model_dump())


def test_simplification_flags_and_reduces_vertices():
    dense = _dense_square()
    display = _layer("farmland_classes", include_map=True, geom=dense, tolerance=1.0).display
    assert display.simplified is True
    assert display.simplify_tolerance_m == 1.0
    simplified = shape(display.feature_collection["features"][0]["geometry"])
    assert len(simplified.exterior.coords) < len(dense.exterior.coords)
    assert simplified.is_valid
    # Display copy stays within about a metre of the exact shape (area check).
    assert simplified.area == pytest.approx(dense.area, rel=1e-3)


def test_simplify_zero_tolerance_keeps_geometry():
    assert simplify_for_display([SQUARE], 0.0)[0] is SQUARE
    display = _layer("aoi", include_map=True, tolerance=0.0).display
    assert display.simplified is False
    assert display.simplify_tolerance_m is None


def test_size_cap_drops_whole_layers_from_the_end():
    first = _layer("aoi", include_map=True)
    second = _layer("farmland_classes", include_map=True, geom=_dense_square())
    first_bytes = len(json.dumps(first.display.feature_collection, separators=(",", ":")))
    block = build_map_block([first, second], max_bytes=first_bytes + 10)
    display = block.display

    assert block.layers[0].delivery == "meta_geojson"
    assert display.layers["aoi"].truncated is False
    assert display.layers["aoi"].feature_count == 1
    assert block.layers[1].delivery == "omitted"
    assert display.layers["farmland_classes"] == MapLayerDisplay(truncated=True)
    assert display.layers["farmland_classes"].feature_collection is None
    assert display.layers["farmland_classes"].feature_count is None
    assert len(display.warnings) == 1
    assert f"{MARKER} farmland_classes" in display.warnings[0]
    assert display.bounds == [0.0, 0.0, 0.01, 0.01]
    assert "coordinates" not in json.dumps(block.model_dump())


def test_size_cap_can_drop_every_layer():
    block = build_map_block([_layer("aoi", include_map=True)], max_bytes=1)
    assert block.layers[0].delivery == "omitted"
    assert block.display.layers["aoi"].truncated is True
    assert block.display.bounds is None


def test_size_cap_leaves_small_block_untouched():
    block = build_map_block([_layer("aoi", include_map=True)], max_bytes=2_000_000)
    assert block.display.warnings == []
    assert block.display.layers["aoi"].truncated is False


def test_size_cap_without_display_is_a_no_op():
    block = build_map_block([_layer("aoi", include_map=False)], max_bytes=1)
    assert enforce_size_cap(block, max_bytes=1) is block
    assert block.display is None
    assert block.layers[0].delivery == "omitted"


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
    shown = _layer("aoi", include_map=True)
    omitted = _layer("urban_context", include_map=False, geom=Point(5, 5).buffer(1))
    block = build_map_block([shown, omitted], max_bytes=2_000_000)
    assert set(block.display.layers) == {"aoi"}
    assert bounds_of(block.display) == [0.0, 0.0, 0.01, 0.01]
    capped = MapDisplay(layers={"aoi": MapLayerDisplay(truncated=True)})
    assert bounds_of(capped) is None


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
    assert response.map.display is None


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
    assert dumped["schema_version"] == "2.0"
    assert dumped["map"] == {"layers": []}


def test_map_settings_defaults_and_validation():
    defaults = Settings(_env_file=None)
    assert defaults.map_simplify_tolerance_m == 1.0
    assert defaults.map_max_geojson_bytes == 2_000_000
    assert Settings(_env_file=None, map_simplify_tolerance_m=0.0).map_simplify_tolerance_m == 0.0
    with pytest.raises(ValidationError):
        Settings(_env_file=None, map_simplify_tolerance_m=-1.0)
    with pytest.raises(ValidationError):
        Settings(_env_file=None, map_max_geojson_bytes=0)
