"""T0 contract tests: the in-memory MCP surface matches manifest.yaml and keeps notices.

These tests run offline against ``fastmcp.Client(create_mcp_server())``. SDA access is
replaced with an ``httpx.MockTransport``; no test here contacts an external service.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any
from unittest.mock import patch

import fastmcp
import httpx
import pytest

from fpac_soil_mcp.app import create_mcp_server
from fpac_soil_mcp.constants import REGULATORY_NOTICE
from fpac_soil_mcp.sda_client import SDAClient

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = REPO_ROOT / "manifest.yaml"

PRIME_FARMLAND_PAYLOAD: dict[str, Any] = {
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


def parse_manifest(text: str) -> dict[str, set[str]]:
    """Return tool names, resource URIs, and prompt names declared in manifest.yaml."""
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in text.splitlines():
        top = re.match(r"^([a-z_]+):\s*$", line)
        if top:
            current = top.group(1)
            sections.setdefault(current, [])
        elif re.match(r"^\S", line):
            current = None
        elif current is not None:
            sections[current].append(line)

    def collect(section: str, key: str) -> set[str]:
        pattern = re.compile(rf"^  - {key}: (\S+)")
        return {m.group(1) for line in sections.get(section, []) if (m := pattern.match(line))}

    return {
        "tools": collect("tools", "name"),
        "resources": collect("resources", "uri"),
        "prompts": collect("prompts", "name"),
    }


@pytest.fixture(scope="module")
def manifest() -> dict[str, set[str]]:
    return parse_manifest(MANIFEST_PATH.read_text(encoding="utf-8"))


def _sda_factory(handler: Callable[[httpx.Request], httpx.Response]) -> Callable[[], SDAClient]:
    def factory() -> SDAClient:
        return SDAClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))

    return factory


def _prime_handler(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json=PRIME_FARMLAND_PAYLOAD)


def _payload(result: Any) -> dict[str, Any]:
    if result.structured_content:
        return result.structured_content
    return json.loads(result.content[0].text)


def test_manifest_parser_reads_expected_counts(manifest: dict[str, set[str]]) -> None:
    assert len(manifest["tools"]) == 10
    assert len(manifest["resources"]) == 3
    assert len(manifest["prompts"]) == 4


def test_manifest_parser_detects_a_missing_tool(manifest: dict[str, set[str]]) -> None:
    trimmed = "\n".join(
        line
        for line in MANIFEST_PATH.read_text(encoding="utf-8").splitlines()
        if line != "  - name: list_farmland_classes"
    )
    assert parse_manifest(trimmed)["tools"] != manifest["tools"]


async def test_server_surface_matches_manifest(manifest: dict[str, set[str]]) -> None:
    async with fastmcp.Client(create_mcp_server()) as client:
        tools = {tool.name for tool in await client.list_tools()}
        resources = {str(resource.uri) for resource in await client.list_resources()}
        prompts = {prompt.name for prompt in await client.list_prompts()}

    assert tools == manifest["tools"]
    assert resources == manifest["resources"]
    assert prompts == manifest["prompts"]


async def test_every_tool_exposes_an_input_schema() -> None:
    async with fastmcp.Client(create_mcp_server()) as client:
        tools = await client.list_tools()

    for tool in tools:
        assert isinstance(tool.input_schema, dict) and tool.input_schema, tool.name


async def test_scope_tool_carries_regulatory_notice() -> None:
    async with fastmcp.Client(create_mcp_server()) as client:
        result = await client.call_tool("explain_fppa_screening_scope", {})

    assert not result.is_error
    assert _payload(result)["regulatory_notice"] == REGULATORY_NOTICE


async def test_farmland_class_listing_cites_its_authority() -> None:
    # Reference listing (not a soil query): FarmlandClassListResponse has no notice field.
    async with fastmcp.Client(create_mcp_server()) as client:
        result = await client.call_tool("list_farmland_classes", {})

    payload = _payload(result)
    assert not result.is_error
    assert payload["authority"]
    assert payload["classes"]


@pytest.mark.parametrize(
    ("tool_name", "arguments"),
    [
        ("get_farmland_classification_by_point", {"latitude": 39.7684, "longitude": -86.1581}),
        ("get_farmland_classification_by_mukey", {"mukey": "412915"}),
    ],
)
async def test_soil_queries_carry_regulatory_notice(
    tool_name: str, arguments: dict[str, Any]
) -> None:
    with patch("fpac_soil_mcp.tools.soil_lookup_tools.SDAClient", _sda_factory(_prime_handler)):
        async with fastmcp.Client(create_mcp_server()) as client:
            result = await client.call_tool(tool_name, arguments)

    payload = _payload(result)
    assert not result.is_error
    assert payload["coverage_status"] == "covered"
    assert payload["map_units"][0]["mukey"] == "412915"
    assert payload["regulatory_notice"] == REGULATORY_NOTICE


@pytest.mark.parametrize(
    ("tool_name", "arguments"),
    [
        ("get_farmland_classification_by_point", {"latitude": 999, "longitude": -93.0}),
        ("get_farmland_classification_by_mukey", {"mukey": "-5"}),
        ("get_farmland_classification_by_mukey", {"mukey": "abc"}),
    ],
)
async def test_invalid_inputs_return_structured_errors(
    tool_name: str, arguments: dict[str, Any]
) -> None:
    requests: list[httpx.Request] = []

    def record(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(500)

    with patch("fpac_soil_mcp.tools.soil_lookup_tools.SDAClient", _sda_factory(record)):
        async with fastmcp.Client(create_mcp_server()) as client:
            result = await client.call_tool(tool_name, arguments, raise_on_error=False)

    assert requests == [], "invalid input must be rejected before any SDA request"
    if result.is_error:
        return
    payload = _payload(result)
    assert payload["coverage_status"] == "no_data"
    assert payload["map_units"] == []
    assert any(item.startswith("Query error:") for item in payload["limitations"])
    assert payload["regulatory_notice"] == REGULATORY_NOTICE


async def test_regulatory_notice_resource_cites_parts_657_and_658() -> None:
    async with fastmcp.Client(create_mcp_server()) as client:
        contents = await client.read_resource("fppa://regulatory-notice")

    text = "\n".join(getattr(item, "text", "") for item in contents)
    assert "7 CFR Part 657" in text
    assert "7 CFR Part 658" in text
