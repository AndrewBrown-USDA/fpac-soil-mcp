"""Tests for the bounded custom route beside the Agent Server chat proxy."""

from agent_server.start_server import app
from fastapi.testclient import TestClient


def test_geo_health_route_is_registered_after_chat_proxy():
    paths = [route.path for route in app.routes]

    assert "/api/geo/health" in paths
    assert paths.index("/api/geo/health") > paths.index("/invocations")


def test_geo_health_route_returns_probe_status():
    response = TestClient(app).get("/api/geo/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_probe_does_not_forward_unknown_geo_routes():
    response = TestClient(app).get("/api/geo/not-a-route")

    assert response.status_code != 200
    assert response.text != '{"status":"ok"}'
