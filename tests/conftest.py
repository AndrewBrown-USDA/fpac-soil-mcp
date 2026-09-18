"""Pytest configuration, shared fixtures, and SDA response mocks."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from fpac_soil_mcp.app import create_mcp_server
from fpac_soil_mcp.sda_client import SDAClient

# ---------------------------------------------------------------------------
# SDA Mock Response Payloads (JSON+COLUMNNAME format)
# ---------------------------------------------------------------------------

MOCK_SDA_PRIME_FARMLAND_RESPONSE: dict[str, Any] = {
    "Table": [
        ["mukey", "musym", "muname", "farmlndcl", "areasymbol"],
        [
            "412915",
            "MmA",
            "Miami silt loam, 0 to 2 percent slopes",
            "All areas are prime farmland",
            "IN097",
        ],
    ]
}

MOCK_SDA_PRIME_IF_DRAINED_RESPONSE: dict[str, Any] = {
    "Table": [
        ["mukey", "musym", "muname", "farmlndcl", "areasymbol"],
        [
            "412920",
            "CkB",
            "Crosby silt loam, 0 to 2 percent slopes",
            "Prime farmland if drained",
            "IN097",
        ],
    ]
}

MOCK_SDA_NOT_PRIME_RESPONSE: dict[str, Any] = {
    "Table": [
        ["mukey", "musym", "muname", "farmlndcl", "areasymbol"],
        [
            "412930",
            "Ur",
            "Urban land",
            "Not prime farmland",
            "IN097",
        ],
    ]
}

MOCK_SDA_EMPTY_RESPONSE: dict[str, Any] = {"Table": []}

MOCK_SDA_HEADERS_ONLY_RESPONSE: dict[str, Any] = {
    "Table": [["mukey", "musym", "muname", "farmlndcl", "areasymbol"]]
}

MOCK_SDA_ERROR_RESPONSE: dict[str, Any] = {
    "ErrorMessage": "Syntax error converting the varchar value 'invalid' to a column of data type int."
}


@pytest.fixture(autouse=True)
def reset_settings_for_tests(monkeypatch):
    """Ensure tests run in a pristine default environment without local .env bleeding into test assertions."""
    monkeypatch.delenv("NASS_API_KEY", raising=False)
    monkeypatch.delenv("NASS_ENABLED", raising=False)


@pytest.fixture
def mock_sda_prime_response() -> dict[str, Any]:
    """Return mock SDA response with prime farmland map unit."""
    return MOCK_SDA_PRIME_FARMLAND_RESPONSE


@pytest.fixture
def mock_sda_prime_if_drained_response() -> dict[str, Any]:
    """Return mock SDA response with 'Prime farmland if drained'."""
    return MOCK_SDA_PRIME_IF_DRAINED_RESPONSE


@pytest.fixture
def mock_sda_empty_response() -> dict[str, Any]:
    """Return mock SDA response representing no intersecting map units."""
    return MOCK_SDA_EMPTY_RESPONSE


@pytest.fixture
def mock_sda_error_response() -> dict[str, Any]:
    """Return mock SDA response representing an API-level error."""
    return MOCK_SDA_ERROR_RESPONSE


@pytest.fixture
def mock_httpx_client_prime() -> httpx.Client:
    """Return an httpx.Client configured with MockTransport for prime farmland."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=MOCK_SDA_PRIME_FARMLAND_RESPONSE)

    transport = httpx.MockTransport(handler)
    return httpx.Client(transport=transport)


@pytest.fixture
def mock_httpx_client_empty() -> httpx.Client:
    """Return an httpx.Client configured with MockTransport returning empty results."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=MOCK_SDA_EMPTY_RESPONSE)

    transport = httpx.MockTransport(handler)
    return httpx.Client(transport=transport)


@pytest.fixture
def mock_sda_client(mock_httpx_client_prime: httpx.Client) -> SDAClient:
    """Return an SDAClient injected with mock prime farmland HTTP transport."""
    return SDAClient(http_client=mock_httpx_client_prime)


@pytest.fixture
def mcp_server():
    """Return a configured FastMCP server instance for testing."""
    return create_mcp_server()
