"""Offline tests for direct, stateless corridor screening."""

import importlib
import json
import logging
from contextlib import asynccontextmanager

import mlflow.genai.agent_server
import pytest
from agent_server import geo
from fastapi.testclient import TestClient
from mcp.types import CallToolResult

MARKER = "CORRIDOR-SECRET-MARKER"
LINE = {"type": "LineString", "coordinates": [[-100, 40], [-99.9, 40.1]]}
CONTEXT = {
    "corridor_ref": "corridor-0123abcd",
    "centerline": LINE,
    "buffer_distance": 50,
    "buffer_units": "feet",
    "alternatives": [LINE],
    "indirect_geometry": {
        "type": "Polygon",
        "coordinates": [[[-100, 40], [-99.9, 40], [-99.9, 40.1], [-100, 40.1], [-100, 40]]],
    },
}
MAP = {"layers": [{"id": "corridor", "feature_collection": {"secret": MARKER}}]}
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


@pytest.fixture
def install_mcp(monkeypatch):
    calls = []
    outcome = CallToolResult(
        content=[],
        structuredContent={
            "impact_breakdown": {
                "direct_acres": 12.3,
                "indirect_acres": 2.0,
                "total_project_acres": 14.3,
            },
            "buffer_distance": 50,
            "buffer_units": "feet",
            "composite_relative_rating": 72.2,
            "county_segments": [
                {
                    "county_name": "Example",
                    "state_name": "XY",
                    "direct_acres": 12.3,
                    "indirect_acres": 2,
                    "total_segment_acres": 14.3,
                    "coverage_status": "covered",
                    "geometry": MARKER,
                }
            ],
            "alternatives": [
                {
                    "alternative_id": "Alt 1",
                    "total_project_acres": 20,
                    "direct_acres": 19,
                    "indirect_acres": 1,
                    "total_fppa_protected_acres": 10,
                    "total_fppa_protected_pct": 50,
                    "centerline": MARKER,
                }
            ],
            "regulatory_notice": NOTICE,
            "map": MAP,
            "tabular_csv": MARKER,
            "manifest": {"geometry": MARKER},
            "lesa_evaluation": {"marker": MARKER},
        },
        isError=False,
    )

    monkeypatch.setattr(geo, "local_dev_enabled", lambda: True)

    async def call_untraced(_server, name, arguments):
        calls.append((name, arguments))
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    @asynccontextmanager
    async def local_server_context(_client):
        yield object()

    monkeypatch.setattr(geo, "_call_tool_untraced", call_untraced)
    monkeypatch.setattr(geo, "init_fpac_mcp_server", local_server_context)

    def _set_outcome(value):
        nonlocal outcome
        outcome = value

    return calls, _set_outcome


def _post(start_server, body):
    client = TestClient(start_server.app)
    if isinstance(body, bytes | str):
        return client.post("/api/geo/corridor", content=body)
    return client.post("/api/geo/corridor", json=body)


def test_missing_mcp_notice_is_returned_as_none(start_server, install_mcp):
    _, set_outcome = install_mcp
    structured = {"map": MAP, "impact_breakdown": {}, "county_segments": [], "alternatives": []}
    set_outcome(CallToolResult(content=[], structuredContent=structured, isError=False))

    body = _post(start_server, CONTEXT).json()

    # ADR 0016: no MCP notice means no notice; the limitation never stands in.
    assert body["regulatory_notice"] is None
    assert body["display"]["regulatory_notice"] is None
    assert body["status"] == "preliminary_screening"


def test_corridor_route_is_registered(start_server):
    assert "/api/geo/corridor" in [route.path for route in start_server.app.routes]


def test_corridor_route_calls_only_expected_tool_with_map_and_no_site_assessment(
    start_server, install_mcp
):
    calls, _ = install_mcp
    response = _post(start_server, CONTEXT)

    assert response.status_code == 200
    assert calls == [
        (
            geo.CORRIDOR_TOOL,
            {
                "centerline": LINE,
                "buffer_distance": 50.0,
                "buffer_units": "feet",
                "alternatives": [{"alternative_id": "Alternative 1", "centerline": LINE}],
                "include_map": True,
                "indirect_geometry": CONTEXT["indirect_geometry"],
            },
        )
    ]
    assert not {"site_assessment_inputs", "project_farm_acres", "criteria_inputs"} & set(
        calls[0][1]
    )


def test_response_is_allowlisted_bounded_and_preliminary(start_server, install_mcp):
    _, _ = install_mcp
    response = _post(start_server, CONTEXT)
    body = response.json()

    assert set(body) == {"display", "map", "regulatory_notice", "status"}
    assert body["status"] == "preliminary_screening"
    assert body["map"] == MAP
    assert body["regulatory_notice"].startswith(NOTICE)
    assert body["regulatory_notice"].endswith(geo.NON_PRIME_LIMITATION)
    assert body["display"] == {
        "corridor_ref": CONTEXT["corridor_ref"],
        "status": "preliminary_screening",
        "buffer_distance": 50.0,
        "buffer_units": "feet",
        "impact_breakdown": {
            "direct_acres": 12.3,
            "indirect_acres": 2.0,
            "total_project_acres": 14.3,
        },
        "composite_relative_rating": 72.2,
        "county_segments": [
            {
                "county_name": "Example",
                "state_name": "XY",
                "direct_acres": 12.3,
                "indirect_acres": 2.0,
                "total_segment_acres": 14.3,
                "coverage_status": "covered",
            }
        ],
        "alternatives": [
            {
                "alternative_id": "Alt 1",
                "total_project_acres": 20.0,
                "direct_acres": 19.0,
                "indirect_acres": 1.0,
                "total_fppa_protected_acres": 10.0,
                "total_fppa_protected_pct": 50.0,
            }
        ],
        "regulatory_notice": body["regulatory_notice"],
    }
    assert body["display"]["county_segments"][0].get("geometry") is None
    assert "tabular_csv" not in response.text and "lesa_evaluation" not in response.text


@pytest.mark.parametrize(
    "body",
    [
        "not json " + MARKER,
        [],
        {**CONTEXT, "unexpected": MARKER},
        json.dumps({**CONTEXT, "buffer_distance": float("nan")}),
        {**CONTEXT, "corridor_ref": MARKER},
        {**CONTEXT, "site_assessment_inputs": {"marker": MARKER}},
        {**CONTEXT, "centerline": {"type": "LineString", "coordinates": [[0, 0]]}},
    ],
)
def test_malformed_requests_are_bounded_and_do_not_call_mcp(start_server, install_mcp, body):
    calls, _ = install_mcp
    response = _post(start_server, body)
    assert response.status_code == 400
    assert MARKER not in response.text
    assert calls == []


def test_mcp_failure_is_bounded_and_never_logs_geometry(start_server, install_mcp, caplog):
    calls, set_outcome = install_mcp
    set_outcome(RuntimeError(f"failed for {MARKER}"))
    caplog.set_level(logging.DEBUG)

    response = _post(start_server, CONTEXT)

    assert response.status_code == 502
    assert response.json() == {"error": "corridor_screening_unavailable"}
    assert MARKER not in response.text
    assert MARKER not in caplog.text
    assert len(calls) == 1


def test_tool_error_is_bounded(start_server, install_mcp):
    _, set_outcome = install_mcp
    set_outcome(CallToolResult(content=[], structuredContent={"error": MARKER}, isError=False))

    response = _post(start_server, CONTEXT)

    assert response.status_code == 502
    assert response.json() == {"error": "corridor_screening_unavailable"}
    assert MARKER not in response.text


def test_request_geometry_and_unallowlisted_tool_payload_never_reach_logs_or_display(
    start_server, install_mcp, caplog
):
    _, _ = install_mcp
    caplog.set_level(logging.DEBUG)
    marked = {**CONTEXT, "centerline": {"type": "LineString", "coordinates": [[1, 2], [3, 4]]}}
    response = _post(start_server, marked)
    body = response.json()

    assert response.status_code == 200
    assert MARKER not in json.dumps(body["display"])
    assert "manifest" not in response.text and "tabular_csv" not in response.text
    assert MARKER not in caplog.text
