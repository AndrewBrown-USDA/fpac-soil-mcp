"""Offline tests for the out-of-band AOI screening route (ADR 0016).

The MCP client is replaced with a fake async context manager, so no network call is
made. Synthetic geometry only; the marker string stands in for anything that must
never reach ``chat_summary``, its text form, the error bodies or the logs.
"""

import asyncio
import importlib
import json
import logging
import re
from unittest.mock import AsyncMock

import httpx
import mlflow
import mlflow.genai.agent_server
import pytest
from agent_server import geo
from fastapi.testclient import TestClient
from mcp.types import CallToolResult, TextContent

MARKER = "R6-MARKER"
SQUARE = {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]}
GEOMETRY_KEYS = re.compile(r"coordinates|bbox|wkt|geom", re.IGNORECASE)


@pytest.fixture(scope="module")
def start_server():
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            mlflow.genai.agent_server,
            "setup_mlflow_git_based_version_tracking",
            lambda *args, **kwargs: None,
        )
        return importlib.import_module("agent_server.start_server")


def _analysis() -> dict:
    return {
        "query_type": "polygon",
        "geometry_hash": f"hash-{MARKER}",
        "total_aoi_acres": 123.456,
        "coverage_status": "covered",
        "urban_screening": {
            "status": "success",
            "geometry_hash": f"hash-{MARKER}",
            "is_urban_intersected": False,
            "urban_area_names": [MARKER],
            "limitations": [MARKER],
        },
        "farmland_summary": {
            "prime_farmland_acres": 100.04,
            "prime_farmland_pct": 81.06,
            "not_prime_acres": 23.42,
            "not_prime_pct": 18.94,
            "total_fppa_protected_acres": 100.04,
            "total_fppa_protected_pct": 81.06,
        },
        "map_units": [
            {
                "mukey": str(n),
                "musym": f"S{n}",
                "muname": f"Synthetic loam {n}",
                "farmlndcl": "All areas are prime farmland" if n % 2 else "Not prime farmland",
                "areasymbol": MARKER,
                "calculated_acres": float(n),
                "percentage_of_aoi": float(n) / 2,
            }
            for n in range(1, 13)
        ],
        "tabular_csv": f"mukey,wkt\n1,{MARKER}",
        "manifest": {"geometry": MARKER, "bbox": [MARKER]},
        "source": {
            "service_name": "USDA NRCS Soil Data Access",
            "endpoint": f"https://example.invalid/{MARKER}",
            "timestamp_utc": "2026-10-30T00:00:00Z",
        },
        "limitations": [f"Echo of input {MARKER}"],
        "regulatory_notice": "Preliminary screening only; not an official FPPA determination.",
    }


def _polygons() -> dict:
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": SQUARE["coordinates"],
                    "note": MARKER,
                },
                "properties": {"mukey": "1", "farmlndcl": "Not prime farmland", "note": MARKER},
            }
        ],
    }


def _structured(data: dict) -> CallToolResult:
    return CallToolResult(content=[], structuredContent=data, isError=False)


def _text(data: dict) -> CallToolResult:
    return CallToolResult(content=[TextContent(type="text", text=json.dumps(data))])


class FakeMcpServer:
    def __init__(self, results=None, error: Exception | None = None):
        self.results = results or {}
        self.error = error
        self.calls: list[tuple[str, dict]] = []
        self.entered = 0
        self.exited = 0

    async def __aenter__(self):
        self.entered += 1
        if self.error:
            raise self.error
        return self

    async def __aexit__(self, *exc):
        self.exited += 1
        return False

    async def call_tool(self, name, arguments, **kwargs):
        self.calls.append((name, arguments))
        return self.results[name]


@pytest.fixture
def fake_mcp(monkeypatch):
    def install(server: FakeMcpServer) -> FakeMcpServer:
        monkeypatch.setattr(geo, "WorkspaceClient", lambda: object())
        monkeypatch.setattr(geo, "init_fpac_mcp_server", lambda client: server)
        return server

    return install


def _happy_server() -> FakeMcpServer:
    return FakeMcpServer(
        {
            geo.ANALYSIS_TOOL: _structured(_analysis()),
            geo.POLYGONS_TOOL: _text(_polygons()),
        }
    )


def _post(start_server, body):
    client = TestClient(start_server.app)
    if isinstance(body, bytes | str):
        return client.post("/api/geo/screen", content=body)
    return client.post("/api/geo/screen", json=body)


def _keys(value):
    if isinstance(value, dict):
        for key, inner in value.items():
            yield key
            yield from _keys(inner)
    elif isinstance(value, list):
        for inner in value:
            yield from _keys(inner)


def test_screen_route_is_registered_and_served_before_proxy(start_server, fake_mcp, monkeypatch):
    assert "/api/geo/screen" in [route.path for route in start_server.app.routes]
    send = AsyncMock(return_value=httpx.Response(200, text="proxied"))
    monkeypatch.setattr(start_server.agent_server.proxy_client, "send", send)
    fake_mcp(_happy_server())

    response = _post(start_server, {"geometry": SQUARE})

    assert response.status_code == 200
    send.assert_not_awaited()


def test_happy_path_returns_display_and_summary(start_server, fake_mcp):
    server = fake_mcp(_happy_server())

    response = _post(start_server, {"geometry": SQUARE, "name": "My field"})
    body = response.json()

    assert response.status_code == 200
    assert set(body) == {"aoi_ref", "display", "chat_summary", "chat_summary_text"}
    assert re.fullmatch(r"aoi-[0-9a-f]{8}", body["aoi_ref"])
    assert body["chat_summary"]["aoi_ref"] == body["aoi_ref"]
    assert body["display"]["soil_polygons"]["type"] == "FeatureCollection"
    assert len(body["display"]["soil_polygons"]["features"]) == 1
    assert body["display"]["regulatory_notice"].startswith("Preliminary screening")
    summary = body["chat_summary"]
    assert summary["total_aoi_acres"] == 123.5
    assert summary["farmland_classes"]["prime_farmland"] == {"acres": 100.0, "pct": 81.1}
    assert summary["urban_screening"] == {"urban_intersected": False}
    assert len(summary["map_units"]) == 10
    assert summary["map_units"][0]["acres"] == 12.0
    assert "My field" not in json.dumps(summary) + body["chat_summary_text"]
    assert body["chat_summary_text"].startswith("Map screening result (preliminary)")
    assert len(body["chat_summary_text"]) <= 2000
    assert [name for name, _ in server.calls] == [geo.ANALYSIS_TOOL, geo.POLYGONS_TOOL]
    assert server.calls[0][1] == {"geojson": SQUARE, "include_nccpi": True}
    assert server.calls[1][1] == {"geojson": SQUARE, "clip": True}
    assert server.entered == server.exited == 1


def test_aoi_ref_is_random_per_request(start_server, fake_mcp):
    fake_mcp(_happy_server())
    first = _post(start_server, {"geometry": SQUARE}).json()["aoi_ref"]
    second = _post(start_server, {"geometry": SQUARE}).json()["aoi_ref"]
    assert first != second


def test_marker_never_reaches_chat_summary(start_server, fake_mcp):
    fake_mcp(_happy_server())
    marked = {
        "type": "MultiPolygon",
        "coordinates": [SQUARE["coordinates"]],
    }

    body = _post(start_server, {"geometry": marked, "name": MARKER}).json()

    assert MARKER not in json.dumps(body["chat_summary"])
    assert MARKER not in body["chat_summary_text"]
    assert not [k for k in _keys(body["chat_summary"]) if GEOMETRY_KEYS.search(k)]


@pytest.mark.parametrize(
    "body",
    [
        {"geometry": {"type": "Point", "coordinates": [0, 0], "marker": MARKER}},
        {"geometry": {"type": "LineString", "coordinates": [[0, 0], [1, 1]], "m": MARKER}},
        {"geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [0, 0]]]}, "x": MARKER},
        {"geometry": {"type": "Polygon", "coordinates": MARKER}},
        {"geometry": SQUARE, "name": MARKER * 20},
        {"geometry": MARKER},
        f"not json {MARKER}",
    ],
)
def test_invalid_requests_return_bounded_422(start_server, fake_mcp, body):
    server = fake_mcp(_happy_server())

    response = _post(start_server, body)

    assert response.status_code == 422
    assert MARKER not in response.text
    assert server.calls == []


def test_vertex_limit_returns_422(start_server, fake_mcp, monkeypatch):
    server = fake_mcp(_happy_server())
    monkeypatch.setenv("GEO_MAX_VERTICES", "10")
    ring = [[i, 0] for i in range(10)] + [[0, 0]]

    response = _post(start_server, {"geometry": {"type": "Polygon", "coordinates": [ring]}})

    assert response.status_code == 422
    assert "10 vertices" in response.text
    assert server.calls == []


def test_default_vertex_limit_is_2000(start_server, fake_mcp):
    fake_mcp(_happy_server())
    ring = [[i, 0] for i in range(2000)] + [[0, 0]]

    response = _post(start_server, {"geometry": {"type": "Polygon", "coordinates": [ring]}})

    assert response.status_code == 422
    assert "2000 vertices" in response.text


def test_oversize_body_returns_422(start_server, fake_mcp):
    server = fake_mcp(_happy_server())
    body = json.dumps({"geometry": SQUARE, "pad": MARKER * 30000})
    assert len(body) > geo.MAX_BODY_BYTES

    response = _post(start_server, body)

    assert response.status_code == 422
    assert MARKER not in response.text
    assert server.calls == []


def test_oversize_stream_stops_before_later_chunks(start_server, fake_mcp):
    server = fake_mcp(_happy_server())
    consumed: list[str] = []

    class ChunkedRequest:
        async def stream(self):
            yield b"x" * (geo.MAX_BODY_BYTES + 1)
            consumed.append("later")
            yield MARKER.encode()

    response = asyncio.run(start_server.geo_screen(ChunkedRequest()))

    assert response.status_code == 422
    assert json.loads(response.body) == {"detail": "Request body exceeds 256 KB."}
    assert consumed == []
    assert server.calls == []


def test_mcp_exception_returns_502_without_marker(start_server, fake_mcp, caplog):
    fake_mcp(FakeMcpServer(error=RuntimeError(f"connect failed for {MARKER}")))
    caplog.set_level(logging.DEBUG)

    response = _post(start_server, {"geometry": SQUARE})

    assert response.status_code == 502
    assert response.json() == {"error": "screening_unavailable"}
    assert MARKER not in caplog.text


def test_call_tool_exception_returns_502(start_server, fake_mcp):
    server = FakeMcpServer({})  # KeyError from call_tool
    fake_mcp(server)

    response = _post(start_server, {"geometry": SQUARE})

    assert response.status_code == 502
    assert MARKER not in response.text
    assert server.exited == 1


@pytest.mark.parametrize(
    "failing",
    [
        CallToolResult(content=[TextContent(type="text", text=MARKER)], isError=True),
        _structured({"error": f"bad input {MARKER}", "regulatory_notice": "n"}),
    ],
)
def test_tool_error_returns_display_error(start_server, fake_mcp, failing):
    fake_mcp(
        FakeMcpServer({geo.ANALYSIS_TOOL: _structured(_analysis()), geo.POLYGONS_TOOL: failing})
    )

    response = _post(start_server, {"geometry": SQUARE})
    body = response.json()

    assert response.status_code == 200
    assert body["display"]["error"] == "screening_failed"
    assert body["chat_summary"]["status"] == "screening_failed"
    assert "screening failed" in body["chat_summary_text"]
    assert MARKER not in response.text


def test_screening_creates_no_traces(start_server, fake_mcp, tmp_path):
    fake_mcp(_happy_server())
    previous = mlflow.get_tracking_uri()
    mlflow.set_tracking_uri(f"sqlite:///{tmp_path / 'mlflow.db'}")
    try:
        experiment_id = mlflow.create_experiment("geo-screen-no-trace")
        mlflow.set_experiment(experiment_id=experiment_id)

        response = _post(start_server, {"geometry": SQUARE})
        if hasattr(mlflow, "flush_trace_async_logging"):
            mlflow.flush_trace_async_logging()
        traces = mlflow.MlflowClient().search_traces(locations=[experiment_id])
    finally:
        mlflow.set_tracking_uri(previous)

    assert response.status_code == 200
    assert len(traces) == 0


def test_debug_logs_contain_no_marker(start_server, fake_mcp, caplog):
    caplog.set_level(logging.DEBUG)
    fake_mcp(_happy_server())
    marked = {"type": "Polygon", "coordinates": SQUARE["coordinates"]}

    _post(start_server, {"geometry": marked, "name": MARKER})
    fake_mcp(
        FakeMcpServer(
            {geo.ANALYSIS_TOOL: _structured({"error": MARKER}), geo.POLYGONS_TOOL: _text({})}
        )
    )
    _post(start_server, {"geometry": marked})

    assert MARKER not in caplog.text


def test_summary_text_is_capped():
    analysis = _analysis()
    analysis["regulatory_notice"] = "N" * 5000
    summary = geo.build_chat_summary(analysis, "aoi-00000000")

    assert len(geo.render_chat_summary_text(summary)) <= 2000
