"""Map layers on the polygon farmland analysis (ADR 0017). Synthetic geometry only."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from shapely.geometry import box, shape

from fpac_soil_mcp.clients.sda import SDAClient
from fpac_soil_mcp.clients.tigerweb import TigerwebClient
from fpac_soil_mcp.core.authority import Provenance
from fpac_soil_mcp.domain.polygon_analyzer import PolygonAnalyzer
from fpac_soil_mcp.models.integration import IntegrationStatus, UrbanExemptionRecord
from fpac_soil_mcp.spatial.map_builder import FARMLAND_CLASS_VALUES, MAP_SCHEMA_VERSION

MARKER = "R6-MARKER"
AOI = box(0.0, 0.0, 0.01, 0.01)
AOI_GEOJSON = {
    "type": "Polygon",
    "coordinates": [[[0.0, 0.0], [0.01, 0.0], [0.01, 0.01], [0.0, 0.01], [0.0, 0.0]]],
}
LEFT = box(0.0, 0.0, 0.005, 0.01)
RIGHT = box(0.005, 0.0, 0.01, 0.01)
URBAN = box(0.008, 0.008, 0.02, 0.02)
# Display-only keys that must never appear in the body (D3).
MOVED_KEYS = {
    "coordinates",
    "feature_collection",
    "feature_count",
    "simplified",
    "simplify_tolerance_m",
    "truncated",
    "bounds",
    "display_crs",
    "warnings",
}

ROWS = [
    {
        "mukey": "1001",
        "musym": f"{MARKER}A",
        "muname": f"{MARKER} prime unit",
        "farmlndcl": "All areas are prime farmland",
        "areasymbol": "ZZ001",
        "area_ac": "15.3",
        "geom": LEFT.wkt,
    },
    {
        "mukey": "1002",
        "musym": f"{MARKER}B",
        "muname": f"{MARKER} drained unit",
        "farmlndcl": "Prime farmland if drained",
        "areasymbol": "ZZ001",
        "area_ac": "15.3",
        "geom": RIGHT.wkt,
    },
]


def _sda() -> MagicMock:
    sda = MagicMock(spec=SDAClient)
    sda.base_url = "https://sdmdataaccess.nrcs.usda.gov/Tabular/post.rest"

    def spatial(wkt, clip=True, geom_acres=True, return_geom=False):
        if return_geom:
            return [dict(row) for row in ROWS]
        return [{k: v for k, v in row.items() if k != "geom"} for row in ROWS]

    sda.get_spatial_intersection.side_effect = spatial
    sda.get_interpretations.return_value = [
        {"mukey": "1001", "numeric_rating": "0.8", "rating_class": "High"},
        {"mukey": "1002", "numeric_rating": "0.6", "rating_class": "Moderate"},
    ]
    sda.get_county_max_productivity_rating.return_value = 1.0
    return sda


def _tiger(urban: list | None = None) -> MagicMock:
    tiger = MagicMock(spec=TigerwebClient)
    record = UrbanExemptionRecord(
        status=IntegrationStatus.SUCCESS,
        geometry_hash="sha256:" + "1" * 64,
        provenance=Provenance(
            source_name="synthetic",
            source_reference="synthetic",
            timestamp_utc=datetime(2026, 1, 1, tzinfo=UTC),
            method_version="1.0.0",
            configuration_version="1.0.0",
        ),
        is_urban_intersected=bool(urban),
        urban_area_names=[name for name, _ in (urban or [])],
        screened_acreage=0.0,
    )
    tiger.check_urban_exemption_with_geometries.return_value = (record, list(urban or []))
    tiger.get_perimeter_evidence.return_value = {"status": "synthetic"}
    return tiger


def _run(include_map: bool, urban: list | None = None):
    sda, tiger = _sda(), _tiger(urban if urban is not None else [(f"{MARKER} Urban", URBAN)])
    result = PolygonAnalyzer(sda_client=sda, tigerweb_client=tiger).analyze_polygon(
        AOI_GEOJSON, include_map=include_map
    )
    return result, sda, tiger


def _layers(result) -> dict:
    return {layer.id: layer for layer in result.map.layers}


def _keys(node) -> set[str]:
    if isinstance(node, dict):
        return set(node) | {key for value in node.values() for key in _keys(value)}
    if isinstance(node, list):
        return {key for item in node for key in _keys(item)}
    return set()


def test_numbers_identical_with_and_without_map():
    plain, _, _ = _run(False)
    mapped, _, _ = _run(True)
    assert plain.total_aoi_acres == mapped.total_aoi_acres
    assert plain.geometry_hash == mapped.geometry_hash
    assert plain.tabular_csv == mapped.tabular_csv
    assert plain.farmland_summary == mapped.farmland_summary
    assert plain.map_units == mapped.map_units
    assert plain.coverage_status == mapped.coverage_status
    assert plain.urban_screening == mapped.urban_screening
    assert plain.manifest["land_evaluation"] == mapped.manifest["land_evaluation"]


@pytest.mark.parametrize("include_map", [False, True])
def test_one_spatial_and_one_urban_call(include_map):
    _, sda, tiger = _run(include_map)
    assert sda.get_spatial_intersection.call_count == 1
    assert sda.get_spatial_intersection.call_args.kwargs["return_geom"] is include_map
    assert tiger.check_urban_exemption_with_geometries.call_count == 1
    tiger.check_urban_exemption.assert_not_called()


def test_default_map_is_descriptor_only():
    result, _, _ = _run(False)
    assert result.schema_version == MAP_SCHEMA_VERSION
    assert result.data_mode == "live"
    assert result.authority.official_filing is False
    assert [layer.id for layer in result.map.layers] == ["aoi", "farmland_classes", "urban_context"]
    for layer in result.map.layers:
        assert layer.delivery == "omitted"
    assert result.map.display is None
    dumped = json.dumps(result.map.model_dump())
    assert "coordinates" not in dumped
    assert [item.value for item in _layers(result)["farmland_classes"].legend] == list(
        FARMLAND_CLASS_VALUES
    )


def test_inline_layers_when_requested():
    result, _, _ = _run(True)
    layers = _layers(result)
    assert all(layer.delivery == "meta_geojson" for layer in layers.values())
    display = result.map.display
    assert display is not None
    assert set(display.layers) == set(layers)

    assert layers["aoi"].authority == "user_input"
    aoi = display.layers["aoi"]
    assert aoi.simplified is False
    assert shape(aoi.feature_collection["features"][0]["geometry"]).equals(AOI)

    assert layers["farmland_classes"].style_key == "farmland_class"
    farmland = display.layers["farmland_classes"]
    assert farmland.feature_count == 2
    assert farmland.simplified is True and farmland.simplify_tolerance_m == 1.0
    props = [f["properties"] for f in farmland.feature_collection["features"]]
    assert [p["farmland_class"] for p in props] == ["prime", "conditional_prime"]
    assert props[0]["mukey"] == "1001" and props[0]["muname"] == f"{MARKER} prime unit"

    assert layers["urban_context"].authority == "reference_data"
    assert layers["urban_context"].data_vintage == "Census 2020 Urban Areas"
    urban = display.layers["urban_context"]
    assert urban.feature_collection["features"][0]["properties"] == {"name": f"{MARKER} Urban"}

    assert display.bounds == [0.0, 0.0, 0.02, 0.02]
    assert display.warnings == []


def test_inline_without_urban_areas_has_empty_urban_layer():
    result, _, _ = _run(True, urban=[])
    assert _layers(result)["urban_context"].delivery == "meta_geojson"
    assert result.map.display.layers["urban_context"].feature_count == 0
    assert result.map.display.bounds == [0.0, 0.0, 0.01, 0.01]


def test_size_cap_drops_urban_layer_first(monkeypatch):
    from fpac_soil_mcp.domain import polygon_analyzer as polygon_analysis

    plain, _, _ = _run(True)
    sizes = {
        layer_id: len(json.dumps(layer.feature_collection, separators=(",", ":")))
        for layer_id, layer in plain.map.display.layers.items()
    }
    monkeypatch.setattr(
        polygon_analysis.settings,
        "map_max_geojson_bytes",
        sizes["aoi"] + sizes["farmland_classes"] + 1,
    )
    capped, _, _ = _run(True)
    layers = _layers(capped)
    assert capped.map.display.layers["urban_context"].truncated is True
    assert capped.map.display.layers["urban_context"].feature_collection is None
    assert layers["urban_context"].delivery == "omitted"
    assert layers["farmland_classes"].delivery == "meta_geojson"
    assert len(capped.map.display.warnings) == 1
    assert capped.tabular_csv == plain.tabular_csv


def test_invalid_geometry_returns_descriptor_map():
    sda, tiger = _sda(), _tiger()
    result = PolygonAnalyzer(sda_client=sda, tigerweb_client=tiger).analyze_polygon(
        {"type": "Polygon", "coordinates": [[[0, 0], [1, 1]]]}, include_map=True
    )
    assert result.coverage_status == "error"
    assert [layer.id for layer in result.map.layers] == ["aoi", "farmland_classes", "urban_context"]
    assert all(layer.delivery == "omitted" for layer in result.map.layers)
    sda.get_spatial_intersection.assert_not_called()


def test_wrappers_pass_include_map():
    sda, tiger = _sda(), _tiger()
    analyzer = PolygonAnalyzer(sda_client=sda, tigerweb_client=tiger)
    result = analyzer.analyze_polygon_sync(AOI_GEOJSON, include_map=True)
    assert _layers(result)["aoi"].delivery == "meta_geojson"
    assert result.map.display is not None


@pytest.mark.parametrize("include_map", [False, True])
def test_body_dump_has_no_moved_keys(include_map):
    result, _, _ = _run(include_map)
    leaked = MOVED_KEYS & _keys(result.model_dump(mode="json"))
    assert not leaked
