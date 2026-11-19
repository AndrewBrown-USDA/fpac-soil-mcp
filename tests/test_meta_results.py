"""Issue #117 guard: map display geometry travels in result ``_meta``, never in the body.

Every call goes through ``fastmcp.Client(create_mcp_server())``, so the client
validates ``structuredContent`` against each tool's explicit output schema.
SDA, TIGERweb and NASS are synthetic (the fakes in ``test_map_tool_contracts``).
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable, Iterator
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastmcp import Client

from fpac_soil_mcp.clients.sda import SDAClientError
from fpac_soil_mcp.domain.corridor_analyzer import CorridorAnalyzer
from fpac_soil_mcp.domain.polygon_analyzer import PolygonAnalyzer
from fpac_soil_mcp.mcp.app import create_mcp_server
from fpac_soil_mcp.models.map import MAP_META_KEY
from tests.test_map_tool_contracts import CENTERLINE, POLYGON, _nass, _sda, _tiger

DISPLAY_KEYS = {"coordinates", "feature_collection", "bounds"}
# Per-call clock values (e.g. source.timestamp_utc, manifest.generated_at_utc).
CLOCK_KEY_PARTS = ("timestamp", "generated_at")
OUR_META_PREFIX = "gov.usda.fpac-soil/"


def _failing_sda() -> MagicMock:
    sda = _sda()
    sda.get_spatial_intersection.side_effect = SDAClientError("synthetic failure")
    return sda


# (case id, tool, arguments, SDA factory)
CASES: list[tuple[str, str, dict[str, Any], Callable[[], MagicMock]]] = [
    ("polygon", "analyze_farmland_by_polygon", {"geojson": POLYGON}, _sda),
    ("polygon_sda_error", "analyze_farmland_by_polygon", {"geojson": POLYGON}, _failing_sda),
    (
        "corridor",
        "analyze_corridor_fppa",
        {"centerline": CENTERLINE, "buffer_distance": 50.0, "buffer_units": "meters"},
        _sda,
    ),
    (
        "corridor_county_sda_error",
        "analyze_corridor_fppa",
        {"centerline": CENTERLINE, "buffer_distance": 50.0, "buffer_units": "meters"},
        _failing_sda,
    ),
    ("soil_polygons", "get_soil_polygons_by_geometry", {"geojson": POLYGON}, _sda),
    (
        "soil_polygons_validation_error",
        "get_soil_polygons_by_geometry",
        {"geojson": {"type": "Point", "coordinates": [0.0, 0.0]}},
        _sda,
    ),
    (
        "soil_polygons_sda_error",
        "get_soil_polygons_by_geometry",
        {"geojson": POLYGON},
        _failing_sda,
    ),
]


@pytest.fixture(params=CASES, ids=[case[0] for case in CASES])
def case(request: pytest.FixtureRequest) -> Iterator[tuple[str, str, dict[str, Any]]]:
    case_id, tool, arguments, sda = request.param
    with (
        patch(
            "fpac_soil_mcp.mcp.tools.spatial_analysis_tools.PolygonAnalyzer",
            side_effect=lambda: PolygonAnalyzer(sda_client=sda(), tigerweb_client=_tiger()),
        ),
        patch(
            "fpac_soil_mcp.mcp.tools.spatial_analysis_tools.CorridorAnalyzer",
            side_effect=lambda: CorridorAnalyzer(
                sda_client=sda(), tigerweb_client=_tiger(), nass_client=_nass()
            ),
        ),
        patch("fpac_soil_mcp.mcp.tools.soil_lookup_tools.SDAClient", side_effect=sda),
    ):
        yield case_id, tool, arguments


def _call_both(tool: str, arguments: dict[str, Any]) -> dict[bool, Any]:
    async def run() -> dict[bool, Any]:
        async with Client(create_mcp_server()) as client:
            # 1. The client validates structuredContent against the output schema.
            return {
                flag: await client.call_tool(tool, {**arguments, "include_map": flag})
                for flag in (False, True)
            }

    return asyncio.run(run())


def _keys(node: Any) -> Iterator[str]:
    if isinstance(node, dict):
        for key, value in node.items():
            yield key
            yield from _keys(value)
    elif isinstance(node, list):
        for item in node:
            yield from _keys(item)


def _without_features(tool: str, body: dict[str, Any]) -> dict[str, Any]:
    # D2: get_soil_polygons_by_geometry keeps its top-level features in the body.
    if tool == "get_soil_polygons_by_geometry":
        return {key: value for key, value in body.items() if key != "features"}
    return body


def _normalized(body: dict[str, Any]) -> dict[str, Any]:
    """Drop per-call timestamps and the one field that differs by flag."""

    def strip(node: Any) -> Any:
        if isinstance(node, dict):
            return {
                key: strip(value)
                for key, value in node.items()
                if not any(part in key for part in CLOCK_KEY_PARTS) and key != "delivery"
            }
        if isinstance(node, list):
            return [strip(item) for item in node]
        return node

    return strip(body)


def test_display_geometry_only_in_meta(case) -> None:
    case_id, tool, arguments = case
    results = _call_both(tool, arguments)

    for flag, result in results.items():
        body = result.structured_content
        assert isinstance(body, dict)
        assert len(result.content) == 1
        text = json.loads(result.content[0].text)
        assert text == body
        # 2. No display data in the model-visible body or text.
        for payload in (body, text):
            leaked = DISPLAY_KEYS & set(_keys(_without_features(tool, payload)))
            assert not leaked, (case_id, flag, leaked)
        delivery = {layer["delivery"] for layer in body["map"]["layers"]}
        assert delivery <= {"meta_geojson", "omitted"}
        if not flag:
            assert delivery == {"omitted"}

        # 4. Our _meta key only with include_map=true; other keys are not ours.
        meta = result.meta or {}
        assert (MAP_META_KEY in meta) is (flag and "meta_geojson" in delivery)
        assert not [k for k in meta if k.startswith(OUR_META_PREFIX) and k != MAP_META_KEY]

    # The happy paths must actually deliver a display when asked.
    if not case_id.endswith("_error"):
        assert MAP_META_KEY in (results[True].meta or {})
        display = results[True].meta[MAP_META_KEY]
        assert "coordinates" in json.dumps(display)

    # 3. The body is the same across flags except map.layers[].delivery.
    off, on = (results[flag].structured_content for flag in (False, True))
    assert _normalized(off) == _normalized(on)

    # 5. Numbers and hashes are equal across flags.
    for key in (
        "geometry_hash",
        "total_aoi_acres",
        "total_acres",
        "tabular_csv",
        "farmland_summary",
        "impact_breakdown",
        "reconciliation_summary",
        "properties",
        "coverage_status",
    ):
        assert off.get(key) == on.get(key), key
