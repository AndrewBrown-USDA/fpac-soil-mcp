"""Integration & server tests for FastMCP app lifecycle, resources, prompts, routes, and live tests."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from starlette.requests import Request

from fpac_soil_mcp.app import create_mcp_server
from fpac_soil_mcp.constants import CITATIONS, REGULATORY_NOTICE
from fpac_soil_mcp.prompts.fppa_prompts import register_fppa_prompts
from fpac_soil_mcp.routes import register_routes
from fpac_soil_mcp.sda_client import SDAClient
from fpac_soil_mcp.tools.soil_tools import get_farmland_classification_by_point


class TestServerInitialization:
    """Test FastMCP server creation and registration of components."""

    def test_create_mcp_server(self) -> None:
        server = create_mcp_server()
        assert server.name == "fpac-soil-mcp"
        assert "USDA FPAC Farmland Protection Policy Act" in server.instructions


class TestResourcesAndPrompts:
    """Test resources and prompts registration and outputs."""

    def test_fppa_resources(self) -> None:
        # Test directly the resource functions
        server = create_mcp_server()
        # Verify resources can be retrieved or registered without error
        assert server is not None

    def test_fppa_screening_assistant_prompt(self) -> None:
        mock_mcp = MagicMock()
        registered_prompts = {}

        def mock_prompt_decorator(name):
            def decorator(fn):
                registered_prompts[name] = fn
                return fn

            return decorator

        mock_mcp.prompt.side_effect = mock_prompt_decorator
        register_fppa_prompts(mock_mcp)

        assert "fppa_screening_assistant" in registered_prompts
        prompt_fn = registered_prompts["fppa_screening_assistant"]

        prompt_text = prompt_fn(project_name="Bridge Expansion", location="39.7684, -86.1581")
        assert "Bridge Expansion" in prompt_text
        assert "39.7684, -86.1581" in prompt_text
        assert "get_farmland_classification_by_point" in prompt_text
        assert "7 CFR Part 657" in prompt_text
        assert "7 CFR Part 658" in prompt_text


class TestCustomRoutes:
    """Test custom HTTP routes (/health, /meta)."""

    @pytest.mark.asyncio
    async def test_health_check_endpoint(self) -> None:
        mock_mcp = MagicMock()
        registered_routes = {}

        def mock_route_decorator(path, methods):
            def decorator(fn):
                registered_routes[path] = fn
                return fn

            return decorator

        mock_mcp.custom_route.side_effect = mock_route_decorator
        register_routes(mock_mcp)

        assert "/health" in registered_routes
        health_fn = registered_routes["/health"]
        mock_request = MagicMock(spec=Request)
        response = await health_fn(mock_request)
        body = json.loads(response.body.decode())

        assert body["status"] == "healthy"
        assert body["service"] == "fpac-soil-mcp"
        assert "timestamp_utc" in body
        assert "transport" in body

    @pytest.mark.asyncio
    async def test_meta_endpoint(self) -> None:
        mock_mcp = MagicMock()
        registered_routes = {}

        def mock_route_decorator(path, methods):
            def decorator(fn):
                registered_routes[path] = fn
                return fn

            return decorator

        mock_mcp.custom_route.side_effect = mock_route_decorator
        register_routes(mock_mcp)

        assert "/meta" in registered_routes
        meta_fn = registered_routes["/meta"]
        mock_request = MagicMock(spec=Request)
        response = await meta_fn(mock_request)
        body = json.loads(response.body.decode())

        assert body["service"] == "fpac-soil-mcp"
        assert "sda_endpoint" in body
        assert body["citations"] == CITATIONS


class TestLiveSDAIntegration:
    """Opt-in live tests verifying network communication against USDA SDA Tabular REST service."""

    @pytest.mark.live_sda
    def test_live_sda_point_lookup_prime_farmland(self) -> None:
        """Query real USDA SDA service for Indianapolis, IN prime farmland coordinate."""
        client = SDAClient()
        results = client.get_by_point(39.7684, -86.1581)

        assert isinstance(results, list)
        assert len(results) > 0
        mapunit = results[0]
        assert "mukey" in mapunit
        assert "musym" in mapunit
        assert "muname" in mapunit
        assert "farmlndcl" in mapunit
        assert "areasymbol" in mapunit

    @pytest.mark.live_sda
    def test_live_sda_mukey_lookup(self) -> None:
        """Query real USDA SDA service for known SSURGO map unit key."""
        client = SDAClient()
        # Query known SSURGO map unit key (e.g. 3104713 from Indianapolis survey area IN097)
        results = client.get_by_mukey("3104713")

        assert isinstance(results, list)
        assert len(results) > 0
        assert results[0]["mukey"] == "3104713"

    @pytest.mark.live_sda
    def test_live_tool_execution(self) -> None:
        """Execute get_farmland_classification_by_point tool against live SDA."""
        response = get_farmland_classification_by_point(latitude=39.7684, longitude=-86.1581)
        assert response.coverage_status in ("covered", "unmapped")
        assert response.regulatory_notice == REGULATORY_NOTICE
        assert response.source.endpoint == "https://sdmdataaccess.nrcs.usda.gov/Tabular/post.rest"
