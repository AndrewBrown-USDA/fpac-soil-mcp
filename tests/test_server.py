"""Integration & server tests for FastMCP app lifecycle, resources, prompts, routes, and live tests."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import ClassVar
from unittest.mock import MagicMock

import pytest
from starlette.requests import Request

from fpac_soil_mcp.clients.sda import SDAClient
from fpac_soil_mcp.core.constants import CITATIONS, REGULATORY_NOTICE
from fpac_soil_mcp.mcp.app import create_mcp_server
from fpac_soil_mcp.mcp.routes import register_routes
from fpac_soil_mcp.mcp.tools.soil_lookup_tools import get_farmland_classification_by_point


class TestServerInitialization:
    """Test FastMCP server creation and registration of components."""

    EXPECTED_TOOLS: ClassVar[set[str]] = {
        "get_farmland_classification_by_point",
        "get_farmland_classification_by_mukey",
        "analyze_farmland_by_polygon",
        "analyze_cdl_histogram",
        "analyze_cdl_context",
        "calculate_preliminary_lesa",
        "get_soil_polygons_by_geometry",
        "check_urban_area_exemption",
        "get_soil_interpretations",
        "analyze_corridor_fppa",
        "explain_fppa_screening_scope",
        "list_farmland_classes",
    }
    EXPECTED_RESOURCES: ClassVar[set[str]] = {
        "fppa://regulatory-notice",
        "fppa://screening-guidance",
        "fppa://farmland-classes",
        "fppa://site-assessment-criteria",
    }
    EXPECTED_PROMPTS: ClassVar[set[str]] = {
        "fppa_screening_assistant",
        "fppa_corridor_screening_assistant",
        "fppa_urban_exemption_assistant",
        "fppa_site_assessment_assistant",
    }

    def test_create_mcp_server(self) -> None:
        server = create_mcp_server()
        assert server.name == "fpac-soil-mcp"
        assert "USDA FPAC Farmland Protection Policy Act" in server.instructions

    @pytest.mark.asyncio
    async def test_corridor_tool_registered(self) -> None:
        server = create_mcp_server()
        tools = await server.list_tools()
        tool_names = [t.name for t in tools]
        assert set(tool_names) == self.EXPECTED_TOOLS
        assert len(tool_names) == 12

    @pytest.mark.asyncio
    async def test_spatial_tools_do_not_publish_include_nccpi(self) -> None:
        server = create_mcp_server()
        tools = {tool.name: tool for tool in await server.list_tools()}
        for name in ("analyze_farmland_by_polygon", "analyze_corridor_fppa"):
            properties = tools[name].parameters["properties"]
            assert "include_nccpi" not in properties
            assert "productivity_index" in properties
            assert "national baseline" in tools[name].description

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("name", "arguments"),
        [
            (
                "analyze_farmland_by_polygon",
                {
                    "geojson": {
                        "type": "Polygon",
                        "coordinates": [
                            [[-93.5, 42.0], [-93.4, 42.0], [-93.4, 42.1], [-93.5, 42.0]]
                        ],
                    }
                },
            ),
            (
                "analyze_corridor_fppa",
                {"centerline": "LINESTRING(-93.5 42.0, -93.4 42.1)", "buffer_distance": 50.0},
            ),
        ],
    )
    async def test_spatial_tools_reject_removed_include_nccpi(
        self, name: str, arguments: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from fastmcp import Client
        from fastmcp.exceptions import ToolError

        from fpac_soil_mcp.mcp.tools import spatial_analysis_tools

        def _no_network(*args: object, **kwargs: object) -> None:
            raise AssertionError("analyzer must not run for rejected arguments")

        monkeypatch.setattr(spatial_analysis_tools, "PolygonAnalyzer", _no_network)
        monkeypatch.setattr(spatial_analysis_tools, "CorridorAnalyzer", _no_network)
        async with Client(create_mcp_server()) as client:
            with pytest.raises(ToolError, match="include_nccpi"):
                await client.call_tool(name, {**arguments, "include_nccpi": True})

    def test_published_server_metadata_exposes_lesa_capabilities(self) -> None:
        with open("server.json", encoding="utf-8") as metadata_file:
            metadata = json.load(metadata_file)

        published_tools = {tool["name"]: tool["description"] for tool in metadata["tools"]}
        assert "calculate_preliminary_lesa" in published_tools
        assert "analyze_corridor_fppa" in published_tools
        assert "LESA" in published_tools["calculate_preliminary_lesa"]
        assert "corridor" in published_tools["analyze_corridor_fppa"].lower()

    @pytest.mark.asyncio
    async def test_runtime_tool_metadata_matches_published_metadata(self) -> None:
        server = create_mcp_server()
        runtime_tools = {tool.name: tool.description for tool in await server.list_tools()}
        metadata = json.loads(Path("server.json").read_text(encoding="utf-8"))
        published_tools = {tool["name"]: tool["description"] for tool in metadata["tools"]}

        assert runtime_tools == published_tools

    def test_published_tool_metadata_matches_manifest(self) -> None:
        metadata = json.loads(Path("server.json").read_text(encoding="utf-8"))
        manifest = Path("manifest.yaml").read_text(encoding="utf-8")
        manifest_tools = dict(
            re.findall(
                r"^  - name: ([^\r\n]+)\r?\n    description: ([^\r\n]+)$",
                manifest.split("\nresources:", 1)[0],
                re.MULTILINE,
            )
        )
        published_tools = {tool["name"]: tool["description"] for tool in metadata["tools"]}

        assert len(manifest_tools) == 12
        assert len(published_tools) == 12
        assert set(published_tools) == set(manifest_tools)
        assert published_tools == manifest_tools

    def test_published_resource_and_prompt_metadata_matches_public_surface(self) -> None:
        manifest = Path("manifest.yaml").read_text(encoding="utf-8")
        resource_entries = re.findall(
            r"^  - uri: ([^\r\n]+)\r?\n    name: ([^\r\n]+)\r?\n    description: ([^\r\n]+)$",
            manifest.split("\nprompts:", 1)[0].split("\nresources:", 1)[1],
            re.MULTILINE,
        )
        prompt_entries = dict(
            re.findall(
                r"^  - name: ([^\r\n]+)\r?\n    description: ([^\r\n]+)$",
                manifest.split("\nprompts:", 1)[1],
                re.MULTILINE,
            )
        )

        resource_uris = {uri for uri, _, _ in resource_entries}
        assert resource_uris == TestServerInitialization.EXPECTED_RESOURCES
        assert len(resource_entries) == 4
        assert all(name and description for _, name, description in resource_entries)
        assert set(prompt_entries) == TestServerInitialization.EXPECTED_PROMPTS
        assert len(prompt_entries) == 4
        assert all(prompt_entries.values())

    @pytest.mark.asyncio
    async def test_server_initialization_includes_all_tools_and_prompts(self) -> None:
        server = create_mcp_server()
        prompts = await server.list_prompts()
        prompt_names = [p.name for p in prompts]
        assert set(prompt_names) == self.EXPECTED_PROMPTS
        assert len(prompt_names) == 4


class TestResourcesAndPrompts:
    """Test resources and prompts registration and outputs."""

    @pytest.mark.asyncio
    async def test_fppa_resources(self) -> None:
        server = create_mcp_server()
        resources = await server.list_resources()
        resource_uris = {str(r.uri) for r in resources}

        assert resource_uris == TestServerInitialization.EXPECTED_RESOURCES
        assert len(resource_uris) == 4

        # Validate regulatory notice resource schema and keys
        reg_res = await server.read_resource("fppa://regulatory-notice")
        reg_data = json.loads(reg_res.contents[0].content)
        assert "regulatory_notice" in reg_data
        assert "limitations" in reg_data
        assert "citations" in reg_data
        assert isinstance(reg_data["limitations"], list)
        assert isinstance(reg_data["citations"], dict)
        assert reg_data["regulatory_notice"] == REGULATORY_NOTICE

        # Validate screening guidance resource schema and keys
        guidance_res = await server.read_resource("fppa://screening-guidance")
        guidance_data = json.loads(guidance_res.contents[0].content)
        assert "sda_screening_scope" in guidance_data
        assert "lesa_determination_scope" in guidance_data
        assert "regulatory_notice" in guidance_data
        assert "limitations" in guidance_data

        # Validate farmland classes resource schema and keys
        classes_res = await server.read_resource("fppa://farmland-classes")
        classes_data = json.loads(classes_res.contents[0].content)
        assert "classes" in classes_data
        assert "authority" in classes_data
        assert "All areas are prime farmland" in classes_data["classes"]
        assert "Not prime farmland" in classes_data["classes"]

    @pytest.mark.parametrize(
        ("kwargs", "expected_snippets"),
        [
            (
                {},
                [
                    "get_farmland_classification_by_point",
                    "get_farmland_classification_by_mukey",
                    "analyze_farmland_by_polygon",
                    "analyze_corridor_fppa",
                    "check_urban_area_exemption",
                    "get_soil_interpretations",
                    "get_soil_polygons_by_geometry",
                    "list_farmland_classes",
                    "explain_fppa_screening_scope",
                    "7 CFR Part 657",
                    "7 CFR Part 658",
                    "preliminary soil inventory information",
                    "DOES NOT constitute an official FPPA determination",
                    "Form AD-1006",
                    "NRCS-CPA-106",
                    "fppa://regulatory-notice",
                    "fppa://screening-guidance",
                    "fppa://farmland-classes",
                ],
            ),
            (
                {
                    "project_name": "Bridge Expansion",
                    "location": "39.7684, -86.1581",
                    "geometry_type": "polygon",
                },
                [
                    "Bridge Expansion",
                    "39.7684, -86.1581",
                    "polygon",
                    "get_farmland_classification_by_point",
                    "analyze_farmland_by_polygon",
                    "7 CFR Part 657",
                    "7 CFR Part 658",
                    "preliminary soil inventory information",
                    "DOES NOT constitute an official FPPA determination",
                    "fppa://regulatory-notice",
                ],
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_fppa_screening_assistant_prompt(
        self, kwargs: dict[str, str], expected_snippets: list[str]
    ) -> None:
        server = create_mcp_server()
        result = await server.render_prompt("fppa_screening_assistant", kwargs)
        prompt_text = result.messages[0].content.text
        for snippet in expected_snippets:
            assert snippet in prompt_text

    @pytest.mark.parametrize(
        ("kwargs", "expected_snippets"),
        [
            (
                {},
                [
                    "analyze_corridor_fppa",
                    "7 CFR § 658.5(c)",
                    "160 points",
                    "Form NRCS-CPA-106",
                    "preliminary estimates",
                    "do not constitute an official Form NRCS-CPA-106 determination",
                    "fppa://regulatory-notice",
                    "fppa://screening-guidance",
                    "fppa://farmland-classes",
                ],
            ),
            (
                {
                    "project_name": "Interstate Highway 69 Expansion",
                    "corridor_length_miles": "14.5",
                },
                [
                    "Interstate Highway 69 Expansion",
                    "14.5",
                    "analyze_corridor_fppa",
                    "7 CFR § 658.5(c)",
                    "160 points",
                    "Form NRCS-CPA-106",
                    "preliminary estimates",
                    "do not constitute an official Form NRCS-CPA-106 determination",
                    "fppa://regulatory-notice",
                ],
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_fppa_corridor_screening_assistant_prompt(
        self, kwargs: dict[str, str], expected_snippets: list[str]
    ) -> None:
        server = create_mcp_server()
        result = await server.render_prompt("fppa_corridor_screening_assistant", kwargs)
        prompt_text = result.messages[0].content.text
        for snippet in expected_snippets:
            assert snippet in prompt_text

    @pytest.mark.parametrize(
        ("kwargs", "expected_snippets"),
        [
            (
                {},
                [
                    "check_urban_area_exemption",
                    "7 CFR § 658.2(a)",
                    "fppa://regulatory-notice",
                    "fppa://screening-guidance",
                    "fppa://farmland-classes",
                ],
            ),
            (
                {
                    "project_name": "Metro Transit Hub",
                    "jurisdiction": "City of Indianapolis, Marion County",
                },
                [
                    "Metro Transit Hub",
                    "City of Indianapolis, Marion County",
                    "check_urban_area_exemption",
                    "7 CFR § 658.2(a)",
                    "fppa://regulatory-notice",
                ],
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_fppa_urban_exemption_assistant_prompt(
        self, kwargs: dict[str, str], expected_snippets: list[str]
    ) -> None:
        server = create_mcp_server()
        result = await server.render_prompt("fppa_urban_exemption_assistant", kwargs)
        prompt_text = result.messages[0].content.text
        for snippet in expected_snippets:
            assert snippet in prompt_text

    @pytest.mark.parametrize(
        ("kwargs", "expected_snippets"),
        [
            (
                {},
                [
                    "Form AD-1006",
                    "NRCS-CPA-106",
                    "160 points",
                    "7 CFR § 658.4",
                    "7 CFR § 658.5",
                    "fppa://regulatory-notice",
                    "fppa://screening-guidance",
                    "fppa://farmland-classes",
                    "fppa://site-assessment-criteria",
                ],
            ),
            (
                {
                    "project_name": "Federal Research Facility",
                    "evaluation_type": "site",
                },
                [
                    "Federal Research Facility",
                    "site",
                    "Form AD-1006",
                    "NRCS-CPA-106",
                    "160 points",
                    "7 CFR § 658.4",
                    "fppa://regulatory-notice",
                    "fppa://site-assessment-criteria",
                ],
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_fppa_site_assessment_assistant_prompt(
        self, kwargs: dict[str, str], expected_snippets: list[str]
    ) -> None:
        server = create_mcp_server()
        result = await server.render_prompt("fppa_site_assessment_assistant", kwargs)
        prompt_text = result.messages[0].content.text
        for snippet in expected_snippets:
            assert snippet in prompt_text


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


class TestLiveNetworkIntegration:
    """Opt-in live tests verifying network communication against USDA SDA Tabular REST service."""

    @pytest.mark.live_network
    def test_live_network_sda_point_lookup_prime_farmland(self) -> None:
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

    @pytest.mark.live_network
    def test_live_network_sda_mukey_lookup(self) -> None:
        """Query real USDA SDA service for known SSURGO map unit key."""
        client = SDAClient()
        # Query known SSURGO map unit key (e.g. 3104713 from Indianapolis survey area IN097)
        results = client.get_by_mukey("3104713")

        assert isinstance(results, list)
        assert len(results) > 0
        assert results[0]["mukey"] == "3104713"

    @pytest.mark.live_network
    def test_live_network_tool_execution(self) -> None:
        """Execute get_farmland_classification_by_point tool against live SDA."""
        response = get_farmland_classification_by_point(latitude=39.7684, longitude=-86.1581)
        assert response.coverage_status in ("covered", "unmapped")
        assert response.regulatory_notice == REGULATORY_NOTICE
        assert response.source.endpoint == "https://sdmdataaccess.nrcs.usda.gov/Tabular/post.rest"


MAPPING_ENUM = ["covered", "partial", "unmapped", "error"]
RATING_ENUM = ["rated", "partial", "unrated", "unmapped", "unknown", "error"]


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


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("tool", "path", "expected", "nullable"),
    [
        ("get_farmland_classification_by_point", ["coverage_status"], MAPPING_ENUM, False),
        ("get_farmland_classification_by_mukey", ["coverage_status"], MAPPING_ENUM, False),
        ("analyze_farmland_by_polygon", ["coverage_status"], MAPPING_ENUM, False),
        (
            "analyze_farmland_by_polygon",
            ["map_units", "[]", "productivity_coverage_status"],
            RATING_ENUM,
            False,
        ),
        (
            "analyze_farmland_by_polygon",
            ["map_units", "[]", "nccpi_baseline_coverage_status"],
            RATING_ENUM,
            True,
        ),
        (
            "calculate_preliminary_lesa",
            ["land_evaluation", "coverage_status"],
            RATING_ENUM,
            False,
        ),
        (
            "analyze_corridor_fppa",
            ["county_segments", "[]", "coverage_status"],
            MAPPING_ENUM,
            False,
        ),
        (
            "analyze_corridor_fppa",
            ["county_segments", "[]", "productivity_coverage_status"],
            RATING_ENUM,
            False,
        ),
    ],
)
async def test_tool_output_schemas_list_coverage_enums(tool, path, expected, nullable) -> None:
    server = create_mcp_server()
    schema = {t.name: t for t in await server.list_tools()}[tool].output_schema
    values, is_nullable = _enum(schema, _field(schema, path))
    assert values == expected
    assert is_nullable is nullable
