"""Tool response models for the map tools' explicit output schemas. Synthetic data only."""

from __future__ import annotations

import json
from typing import get_args

import pytest
from shapely.geometry import Polygon

from fpac_soil_mcp.models import (
    CorridorImpactBreakdown,
    QuerySource,
    ToolError,
)
from fpac_soil_mcp.models.coverage import RatingCoverage, SoilMappingCoverage
from fpac_soil_mcp.models.map import ResultAuthority
from fpac_soil_mcp.models.spatial import (
    CorridorToolResponse,
    SoilPolygonsResponse,
)
from fpac_soil_mcp.spatial.map_builder import MAP_SCHEMA_VERSION, build_layer, build_map_block

MARKER = "R6-MARKER"
SQUARE = Polygon([(0, 0), (0.01, 0), (0.01, 0.01), (0, 0.01), (0, 0)])
SOURCE = {"service": "USDA NRCS Soil Data Access", "timestamp_utc": "2026-01-01T00:00:00Z"}


def _map_fields(include_map: bool) -> dict:
    """Same keys as ``soil_lookup_tools._soil_map_fields``."""
    block = build_map_block(
        [
            build_layer(
                layer_id="aoi",
                title="Area of interest",
                kind="polygon",
                authority="user_input",
                source="User-supplied area of interest",
                features=[(SQUARE, {})] if include_map else None,
                include_map=include_map,
            )
        ],
        2_000_000,
    )
    return {
        "schema_version": MAP_SCHEMA_VERSION,
        "data_mode": "live",
        "authority": ResultAuthority().model_dump(),
        "map": block.model_dump(),
    }


def _error_body(code: str, source: str) -> dict:
    return {
        "type": "FeatureCollection",
        "features": [],
        "error": MARKER,
        "status": "error",
        "error_details": ToolError(code=code, message=MARKER, source=source).model_dump(),
        "source": dict(SOURCE),
        "limitations": [MARKER, f"error: {MARKER}"],
        "regulatory_notice": MARKER,
        **_map_fields(False),
    }


def _success_body(include_map: bool) -> dict:
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[0, 0], [0.01, 0], [0.01, 0.01], [0, 0]]],
                },
                "properties": {
                    "mukey": "123",
                    "musym": "A",
                    "muname": MARKER,
                    "farmlndcl": "All areas are prime farmland",
                    "areasymbol": "XX001",
                    "area_ac": 1.0,
                },
            }
        ],
        "properties": {"total_aoi_acres": 2.5, "feature_count": 1, "clipped": True},
        "source": {**SOURCE, "endpoint": "https://example.invalid/sda"},
        "limitations": [MARKER],
        "regulatory_notice": MARKER,
        **_map_fields(include_map),
    }


@pytest.mark.parametrize("include_map", [False, True])
def test_soil_polygons_success_body_validates(include_map):
    response = SoilPolygonsResponse.model_validate(_success_body(include_map))
    assert response.properties.feature_count == 1
    assert response.properties.clipped is True
    assert response.status is None
    assert response.error is None
    assert response.error_details is None
    assert response.features[0]["properties"]["mukey"] == "123"


@pytest.mark.parametrize(
    ("code", "source"),
    [
        ("validation_error", "GeoJSON geometry validation"),
        ("upstream_error", "USDA NRCS Soil Data Access (SDA)"),
    ],
)
def test_soil_polygons_error_bodies_validate(code, source):
    response = SoilPolygonsResponse.model_validate(_error_body(code, source))
    assert response.properties is None
    assert response.status == "error"
    assert response.error_details.code == code
    assert response.features == []


def test_soil_polygons_rejects_unknown_status():
    body = _error_body("upstream_error", "USDA NRCS Soil Data Access (SDA)")
    body["status"] = "ok"
    with pytest.raises(ValueError):
        SoilPolygonsResponse.model_validate(body)


def _resolve(schema: dict, node: dict) -> dict:
    while "$ref" in node:
        node = schema["$defs"][node["$ref"].rsplit("/", 1)[-1]]
    return node


def _field(schema: dict, path: list[str]) -> dict:
    node = schema
    for key in path:
        node = _resolve(schema, node)
        node = node["items"] if key == "[]" else node["properties"][key]
    return _resolve(schema, node)


def _enum(schema: dict, node: dict) -> tuple[list[str], bool]:
    if "anyOf" in node:
        options = [_resolve(schema, option) for option in node["anyOf"]]
        enums = [option for option in options if "enum" in option]
        nullable = any(option.get("type") == "null" for option in options)
        assert len(enums) == 1
        return enums[0]["enum"], nullable
    return node["enum"], False


@pytest.mark.parametrize(
    ("field", "expected"),
    [
        ("coverage_status", list(get_args(SoilMappingCoverage))),
        ("productivity_coverage_status", list(get_args(RatingCoverage))),
    ],
)
def test_corridor_tool_schema_lists_coverage_enums(field, expected):
    schema = CorridorToolResponse.model_json_schema()
    values, _ = _enum(schema, _field(schema, ["county_segments", "[]", field]))
    assert values == expected


def test_corridor_tool_schema_has_nullable_lesa_evaluation():
    schema = CorridorToolResponse.model_json_schema()
    node = schema["properties"]["lesa_evaluation"]
    options = [_resolve(schema, option) for option in node["anyOf"]]
    assert any(option.get("type") == "null" for option in options)
    assert any("land_evaluation_score" in option.get("properties", {}) for option in options)


def test_corridor_tool_response_without_lesa_validates():
    response = CorridorToolResponse(
        geometry_hash="sha256:" + "0" * 64,
        buffer_distance=100.0,
        buffer_units="feet",
        impact_breakdown=CorridorImpactBreakdown(),
        source=QuerySource(timestamp_utc="2026-01-01T00:00:00Z"),
        regulatory_notice=MARKER,
    )
    assert response.lesa_evaluation is None
    assert response.schema_version == MAP_SCHEMA_VERSION


@pytest.mark.parametrize("model", [CorridorToolResponse, SoilPolygonsResponse])
def test_new_schemas_have_no_display_data(model):
    text = json.dumps(model.model_json_schema())
    for name in ("_display", "feature_collection", "inline_geojson", "display_crs"):
        assert name not in text, name
    assert "gov.usda.fpac-soil/map" in text
