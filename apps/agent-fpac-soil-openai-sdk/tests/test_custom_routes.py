"""Tests for the bounded custom route beside the Agent Server chat proxy.

The MLflow chat proxy serves any registered route first, whatever the registration
order, and forwards other allowlisted paths (including unknown ``/api/*``) to the
chat app on ``CHAT_APP_PORT``. Importing ``start_server`` normally calls
``setup_mlflow_git_based_version_tracking()`` against the configured tracking server,
so the import runs with that call patched to a no-op to keep these tests offline.
"""

import importlib
from unittest.mock import AsyncMock

import httpx
import mlflow.genai.agent_server
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def start_server():
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            mlflow.genai.agent_server,
            "setup_mlflow_git_based_version_tracking",
            lambda *args, **kwargs: None,
        )
        return importlib.import_module("agent_server.start_server")


def test_geo_health_route_is_registered(start_server):
    paths = [route.path for route in start_server.app.routes]

    assert "/api/geo/health" in paths


def test_geo_health_route_returns_probe_status(start_server):
    response = TestClient(start_server.app).get("/api/geo/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_unknown_geo_route_is_forwarded_to_chat_app(start_server, monkeypatch):
    server = start_server.agent_server
    send = AsyncMock(return_value=httpx.Response(200, text="proxied"))
    monkeypatch.setattr(server.proxy_client, "send", send)

    response = TestClient(start_server.app).get("/api/geo/not-a-route")

    assert response.text == "proxied"
    send.assert_awaited_once()
    forwarded = send.await_args.args[0]
    assert str(forwarded.url) == f"http://localhost:{server.chat_app_port}/api/geo/not-a-route"
