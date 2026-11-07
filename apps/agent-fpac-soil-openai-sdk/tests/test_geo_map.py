"""Offline tests for ``POST /api/geo/map`` (ADR 0017).

Same approach as ``test_geo_screen.py``: the real ``McpServer`` class with only its
transport faked. Synthetic geometry only; the marker stands in for anything that must
never reach an error body or the logs.
"""

import importlib
import json
import logging
from unittest.mock import MagicMock

import mlflow.genai.agent_server
import pytest
from agent_server import geo
from agent_server.agent import init_fpac_mcp_server
from databricks_openai.agents import McpServer
from fastapi.testclient import TestClient
from mcp.types import CallToolResult, TextContent

MARKER = "R6-MARKER"
SQUARE = {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]}
LINE = {"type": "LineString", "coordinates": [[0, 0.5], [1, 0.5]]}
AOI_REF = "aoi-0123abcd"
MAP = {
    "display_crs": "EPSG:4326",
    "bounds": [0, 0, 1, 1],
    "warnings": [],
    "layers": [{"id": "aoi", "delivery": "inline_geojson", "feature_collection": {}}],
}
AUTHORITY = {"level": "preliminary_screening", "official_filing": False}
NOTICE = "Preliminary screening only; not an official FPPA determination."


@pytest.fixture(scope="module")
def start_server():
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            mlflow.genai.agent_server,
            "setup_mlflow_git_based_version_tracking",
            lambda *args, **kwargs: None,
        )
        return importlib.import_module("agent_server.start_server")


class FakeMcp:
    def __init__(self, results=None, error: Exception | None = None):
        self.results = results or {}
        self.error = error
        self.calls: list[tuple[str, dict]] = []


class FakeSession:
    def __init__(self, fake: FakeMcp):
        self.fake = fake

    async def call_tool(self, name, arguments=None, *args, **kwargs):
        self.fake.calls.append((name, arguments))
        return self.fake.results[name]


def _real_server(fake: FakeMcp) -> McpServer:
    server = init_fpac_mcp_server(MagicMock(name="WorkspaceClient"))

    async def connect():
        if fake.error:
            raise fake.error
        server.session = FakeSession(fake)

    async def cleanup():
        server.session = None

    server.connect = connect
    server.cleanup = cleanup
    return server


@pytest.fixture
def fake_mcp(monkeypatch):
    def install(fake: FakeMcp) -> FakeMcp:
        monkeypatch.setattr(geo, "WorkspaceClient", lambda: object())
        monkeypatch.setattr(geo, "init_fpac_mcp_server", lambda client: _real_server(fake))
        return fake

    return install


def _result(extra: dict | None = None) -> CallToolResult:
    data = {
        "query_type": "polygon",
        "tabular_csv": f"mukey\n{MARKER}",
        "map": MAP,
        "authority": AUTHORITY,
        "regulatory_notice": NOTICE,
        **(extra or {}),
    }
    return CallToolResult(content=[], structuredContent=data, isError=False)


def _happy() -> FakeMcp:
    return FakeMcp({tool: _result() for tool in geo.MAP_TOOLS})


def _post(start_server, body):
    client = TestClient(start_server.app)
    if isinstance(body, bytes | str):
        return client.post("/api/geo/map", content=body)
    return client.post("/api/geo/map", json=body)


def test_route_is_registered(start_server):
    assert "/api/geo/map" in [route.path for route in start_server.app.routes]


def test_polygon_call_returns_map_only(start_server, fake_mcp):
    fake = fake_mcp(_happy())

    response = _post(start_server, {"tool": geo.ANALYSIS_TOOL, "arguments": {"geojson": SQUARE}})

    assert response.status_code == 200
    assert response.json() == {
        "tool": geo.ANALYSIS_TOOL,
        "map": MAP,
        "regulatory_notice": NOTICE,
        "authority": AUTHORITY,
    }
    assert MARKER not in response.text  # nothing beyond the map, notice and authority
    assert fake.calls == [(geo.ANALYSIS_TOOL, {"geojson": SQUARE, "include_map": True})]


def test_corridor_call_and_wrapped_result(start_server, fake_mcp):
    wrapped = CallToolResult(
        content=[],
        structuredContent={"result": {"map": MAP, "authority": AUTHORITY, "lesa_evaluation": {}}},
        isError=False,
    )
    fake = fake_mcp(FakeMcp({geo.CORRIDOR_TOOL: wrapped}))
    arguments = {"centerline": LINE, "buffer_distance": 50.0, "alternatives": []}

    body = _post(start_server, {"tool": geo.CORRIDOR_TOOL, "arguments": arguments}).json()

    assert body["map"] == MAP
    assert body["regulatory_notice"] is None
    assert fake.calls == [(geo.CORRIDOR_TOOL, {**arguments, "include_map": True})]


@pytest.mark.parametrize("supplied", [False, "false", None, 0])
def test_include_map_is_forced_on(start_server, fake_mcp, supplied):
    fake = fake_mcp(_happy())
    _post(
        start_server,
        {"tool": geo.ANALYSIS_TOOL, "arguments": {"geojson": SQUARE, "include_map": supplied}},
    )
    assert fake.calls[0][1]["include_map"] is True


def test_aoi_ref_is_substituted_from_active_aoi(start_server, fake_mcp):
    fake = fake_mcp(_happy())

    response = _post(
        start_server,
        {
            "tool": geo.ANALYSIS_TOOL,
            "arguments": {"geojson": AOI_REF},
            "active_aoi": {"aoi_ref": AOI_REF, "geometry": SQUARE},
        },
    )

    assert response.status_code == 200
    assert fake.calls == [(geo.ANALYSIS_TOOL, {"geojson": SQUARE, "include_map": True})]


def test_other_argument_left_alone_when_ref_differs(start_server, fake_mcp):
    fake = fake_mcp(_happy())
    _post(
        start_server,
        {
            "tool": geo.ANALYSIS_TOOL,
            "arguments": {"geojson": "aoi-ffffffff"},
            "active_aoi": {"aoi_ref": AOI_REF, "geometry": SQUARE},
        },
    )
    assert fake.calls[0][1]["geojson"] == "aoi-ffffffff"


def test_soil_polygons_tool_is_accepted_with_substitution(start_server, fake_mcp):
    fake = fake_mcp(_happy())

    response = _post(
        start_server,
        {
            "tool": geo.SOIL_POLYGONS_TOOL,
            "arguments": {"geojson": AOI_REF, "clip": True, "include_map": False},
            "active_aoi": {"aoi_ref": AOI_REF, "geometry": SQUARE},
        },
    )

    assert response.status_code == 200
    assert response.json()["tool"] == geo.SOIL_POLYGONS_TOOL
    assert fake.calls == [
        (geo.SOIL_POLYGONS_TOOL, {"geojson": SQUARE, "clip": True, "include_map": True})
    ]


@pytest.mark.parametrize(
    "tool",
    [
        "calculate_preliminary_lesa",
        "get_farmland_classification_by_point",
        MARKER,
        None,
    ],
)
def test_tool_allowlist_rejects_with_400(start_server, fake_mcp, tool):
    fake = fake_mcp(_happy())
    response = _post(start_server, {"tool": tool, "arguments": {"geojson": SQUARE, "x": MARKER}})
    assert response.status_code == 400
    assert response.json() == {"detail": "Tool is not available for maps."}
    assert fake.calls == []


@pytest.mark.parametrize(
    "body",
    [
        f"not json {MARKER}",
        json.dumps([MARKER]),
        {"tool": geo.ANALYSIS_TOOL},
        {"tool": geo.ANALYSIS_TOOL, "arguments": MARKER},
        {"tool": geo.ANALYSIS_TOOL, "arguments": {"geojson": SQUARE}, "active_aoi": MARKER},
        {
            "tool": geo.ANALYSIS_TOOL,
            "arguments": {"geojson": AOI_REF},
            "active_aoi": {"aoi_ref": MARKER, "geometry": SQUARE},
        },
        {
            "tool": geo.ANALYSIS_TOOL,
            "arguments": {"geojson": AOI_REF},
            "active_aoi": {"aoi_ref": AOI_REF, "geometry": {"type": "Point", "c": MARKER}},
        },
    ],
)
def test_invalid_requests_return_bounded_400(start_server, fake_mcp, body):
    fake = fake_mcp(_happy())
    response = _post(start_server, body)
    assert response.status_code == 400
    assert set(response.json()) == {"detail"}
    assert MARKER not in response.text
    assert fake.calls == []


def test_oversize_body_returns_413(start_server, fake_mcp):
    fake = fake_mcp(_happy())
    body = json.dumps(
        {"tool": geo.ANALYSIS_TOOL, "arguments": {"geojson": SQUARE, "pad": MARKER * 30000}}
    )
    assert len(body) > geo.MAX_BODY_BYTES

    response = _post(start_server, body)

    assert response.status_code == 413
    assert MARKER not in response.text
    assert fake.calls == []


@pytest.mark.parametrize(
    "fake",
    [
        FakeMcp(error=RuntimeError(f"connect failed for {MARKER}")),
        FakeMcp({}),  # KeyError from call_tool
        FakeMcp(
            {
                geo.ANALYSIS_TOOL: CallToolResult(
                    content=[TextContent(type="text", text=MARKER)], isError=True
                )
            }
        ),
        FakeMcp({geo.ANALYSIS_TOOL: _result({"error": f"bad input {MARKER}"})}),
    ],
)
def test_mcp_failures_return_bounded_502(start_server, fake_mcp, caplog, fake):
    caplog.set_level(logging.DEBUG)
    fake_mcp(fake)

    response = _post(
        start_server, {"tool": geo.ANALYSIS_TOOL, "arguments": {"geojson": SQUARE, "n": MARKER}}
    )

    assert response.status_code == 502
    assert response.json() == {"error": "map_unavailable"}
    assert MARKER not in caplog.text


def test_missing_map_block_returns_null_map(start_server, fake_mcp):
    fake_mcp(FakeMcp({geo.ANALYSIS_TOOL: _result({"map": "not a block", "authority": []})}))
    body = _post(start_server, {"tool": geo.ANALYSIS_TOOL, "arguments": {"geojson": SQUARE}}).json()
    assert body["map"] is None
    assert body["authority"] is None
