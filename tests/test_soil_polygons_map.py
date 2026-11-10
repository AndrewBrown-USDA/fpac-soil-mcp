"""Map result (ADR 0017) on ``get_soil_polygons_by_geometry`` (EXECUTION_PLAN_44 A6).

Calls the tool through a ``FastMCP`` server built with ``register_tools`` on a
synthetic SDA client. Synthetic geometry only.
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastmcp import FastMCP
from shapely.geometry import box

from fpac_soil_mcp.config import settings
from fpac_soil_mcp.sda_client import SDAClient, SDAClientError
from fpac_soil_mcp.tools import register_tools

TOOL = "get_soil_polygons_by_geometry"
POLYGON = {
    "type": "Polygon",
    "coordinates": [[[0.0, 0.0], [0.01, 0.0], [0.01, 0.01], [0.0, 0.01], [0.0, 0.0]]],
}
ROWS = [
    {
        "mukey": "3001",
        "musym": "ZA",
        "muname": "Synthetic prime unit",
        "farmlndcl": "All areas are prime farmland",
        "areasymbol": "ZZ001",
        "area_ac": "6.0",
        "geom": box(0.0, 0.0, 0.005, 0.01).wkt,
    },
    {
        "mukey": "3002",
        "musym": "ZB",
        "muname": "Synthetic local unit",
        "farmlndcl": "Farmland of local importance",
        "areasymbol": "ZZ001",
        "area_ac": "6.0",
        "geom": box(0.005, 0.0, 0.01, 0.01).wkt,
    },
]
ADDITIVE_KEYS = ("schema_version", "data_mode", "authority", "map")


@pytest.fixture
def mcp() -> FastMCP:
    server = FastMCP("soil-polygons-map-test")
    register_tools(server)
    return server


@pytest.fixture
def sda():
    client = MagicMock(spec=SDAClient)
    client.base_url = "https://sdmdataaccess.nrcs.usda.gov/Tabular/post.rest"
    client.get_spatial_intersection.side_effect = lambda *a, **kw: [dict(r) for r in ROWS]
    with patch("fpac_soil_mcp.tools.soil_lookup_tools.SDAClient", return_value=client):
        yield client


def _call(mcp: FastMCP, **arguments: Any) -> dict[str, Any]:
    result = asyncio.run(mcp.call_tool(TOOL, arguments))
    assert isinstance(result.structured_content, dict)
    return result.structured_content


def _layers(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {layer["id"]: layer for layer in payload["map"]["layers"]}


def _without_map(payload: dict[str, Any]) -> dict[str, Any]:
    rest = {k: v for k, v in payload.items() if k not in ADDITIVE_KEYS}
    rest["source"] = {k: v for k, v in rest["source"].items() if k != "timestamp_utc"}
    return rest


def test_default_call_returns_descriptors_only(mcp, sda):
    payload = _call(mcp, geojson=POLYGON)
    assert payload["type"] == "FeatureCollection"
    assert len(payload["features"]) == 2
    assert payload["schema_version"] == "1.0"
    assert payload["data_mode"] == "live"
    assert payload["authority"]["official_filing"] is False
    layers = _layers(payload)
    assert list(layers) == ["aoi", "farmland_classes"]
    assert all(layer["delivery"] == "omitted" for layer in layers.values())
    assert all(layer["feature_collection"] is None for layer in layers.values())
    assert payload["map"]["bounds"] is None


def test_include_map_returns_inline_layers(mcp, sda):
    payload = _call(mcp, geojson=POLYGON, include_map=True)
    layers = _layers(payload)
    assert all(layer["delivery"] == "inline_geojson" for layer in layers.values())
    farmland = layers["farmland_classes"]
    assert farmland["style_key"] == "farmland_class"
    assert farmland["legend"]
    classes = {
        f["properties"]["farmland_class"] for f in farmland["feature_collection"]["features"]
    }
    assert len(farmland["feature_collection"]["features"]) == 2
    assert len(classes) == 2
    assert len(layers["aoi"]["feature_collection"]["features"]) == 1
    assert payload["map"]["bounds"] is not None


def test_include_map_keeps_existing_keys_and_one_sda_call(mcp, sda):
    default = _call(mcp, geojson=POLYGON)
    with_map = _call(mcp, geojson=POLYGON, include_map=True)
    assert _without_map(default) == _without_map(with_map)
    assert sda.get_spatial_intersection.call_count == 2  # one per call
    for call in sda.get_spatial_intersection.call_args_list:
        assert call.kwargs["return_geom"] is True


def test_unclipped_title_says_full_survey_polygons(mcp, sda):
    payload = _call(mcp, geojson=POLYGON, clip=False, include_map=True)
    assert "full survey polygons" in _layers(payload)["farmland_classes"]["title"]
    assert payload["properties"]["clipped"] is False


def test_invalid_geometry_returns_descriptor_map(mcp, sda):
    payload = _call(mcp, geojson={"type": "Point", "coordinates": [0.0, 0.0]}, include_map=True)
    assert payload["error"]
    assert payload["features"] == []
    assert all(layer["delivery"] == "omitted" for layer in payload["map"]["layers"])
    sda.get_spatial_intersection.assert_not_called()


def test_sda_error_returns_descriptor_map(mcp, sda):
    sda.get_spatial_intersection.side_effect = SDAClientError("synthetic failure")
    payload = _call(mcp, geojson=POLYGON, include_map=True)
    assert payload["error"]
    assert all(layer["delivery"] == "omitted" for layer in payload["map"]["layers"])


def test_size_cap_drops_farmland_before_aoi(mcp, sda, monkeypatch):
    monkeypatch.setattr(settings, "map_max_geojson_bytes", 400)
    payload = _call(mcp, geojson=POLYGON, include_map=True)
    layers = _layers(payload)
    assert layers["farmland_classes"]["truncated"] is True
    assert layers["farmland_classes"]["delivery"] == "omitted"
    assert layers["aoi"]["delivery"] == "inline_geojson"
    assert payload["map"]["warnings"]
    assert len(payload["features"]) == 2  # the FeatureCollection itself is not capped
