"""T0 contract tests: the in-memory MCP surface matches manifest.yaml and keeps notices.

These tests run offline against ``fastmcp.Client(create_mcp_server())``. SDA access is
replaced with an ``httpx.MockTransport``; no test here contacts an external service.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import fastmcp
import httpx
import pytest
from common.dataset import load_gold_set
from common.matching import match_expected

from fpac_soil_mcp.app import create_mcp_server
from fpac_soil_mcp.authority import Provenance
from fpac_soil_mcp.constants import REGULATORY_NOTICE
from fpac_soil_mcp.integration_models import IntegrationStatus, UrbanExemptionRecord
from fpac_soil_mcp.lesa import evaluate_land_evaluation, evaluate_lesa
from fpac_soil_mcp.models import MapUnitProductivityRating
from fpac_soil_mcp.polygon_analysis import PolygonAnalyzer
from fpac_soil_mcp.sda_client import SDAClient, SDAQueryError
from fpac_soil_mcp.tigerweb_client import TigerwebClient

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


_SDV_RECORDS: dict[str, dict[str, Any]] = {
    r["attributename"]: r
    for r in json.loads(
        (
            Path(__file__).resolve().parents[2]
            / "tests"
            / "fixtures"
            / "sdv_attribute_records.json"
        ).read_text(encoding="utf-8")
    )["records"]
}


def _attribute_rating_result(
    attribute_name: str,
    mukey: str,
    numeric_rating: float,
    constraints: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run a gold-set scenario through the attribute_meta path (chorizon, cocropyld)."""
    client = SDAClient(max_retries=1)
    with patch.object(
        client,
        "_execute_query",
        return_value=[
            {
                "mukey": mukey,
                "areasymbol": "IL019",
                "numeric_rating": numeric_rating,
                "rated_pct": 100.0,
                "total_pct": 100.0,
            }
        ],
    ):
        return client.get_productivity_ratings(
            [mukey],
            attribute_meta=_SDV_RECORDS[attribute_name],
            constraints=constraints,
        )[0]


def _rating_result(index_type: str, mukey: str, numeric_rating: float) -> dict[str, Any]:
    client = SDAClient(max_retries=1)
    with patch.object(
        client,
        "_execute_query",
        return_value=[
            {
                "mukey": mukey,
                "areasymbol": "IL019",
                "numeric_rating": numeric_rating,
                "rated_pct": 100.0,
                "total_pct": 100.0,
            }
        ],
    ):
        return client.get_productivity_ratings([mukey], index_type=index_type)[0]


def _partial_land_evaluation() -> dict[str, Any]:
    summary = evaluate_land_evaluation(
        [
            MapUnitProductivityRating(
                mukey="rated",
                raw_rating=0.8,
                normalized_relative_rating=0.8,
                is_rated=True,
            ),
            MapUnitProductivityRating(
                mukey="unrated",
                raw_rating=None,
                normalized_relative_rating=None,
                is_rated=False,
            ),
        ],
        acreages={"rated": 60.0, "unrated": 40.0},
    )
    return summary.model_dump(mode="json")


def _gold_scenario(case_id: str) -> dict[str, Any]:
    if case_id == "strategy-cointerp":
        return _rating_result("nccpi", "1", 0.8)
    if case_id == "strategy-mapunit":
        return _rating_result("csr2", "2", 96.0)
    if case_id == "strategy-component":
        return _rating_result("cpi", "3", 71.004)
    if case_id == "strategy-chorizon":
        return _attribute_rating_result(
            "Available Water Storage",
            "4",
            15.5,
        )
    if case_id == "strategy-cocropyld":
        return _attribute_rating_result(
            "Yields of Non-Irrigated Crops (Component)",
            "5",
            145.0,
            constraints={"cropname": "Corn"},
        )
    if case_id == "multi-county-selected-property":
        client = SDAClient(max_retries=1)
        with patch.object(
            client,
            "_execute_query",
            side_effect=[
                [
                    {
                        "mukey": "4",
                        "areasymbol": "IL019",
                        "numeric_rating": 0.8,
                        "rated_pct": 100.0,
                        "total_pct": 100.0,
                    }
                ],
                [
                    {
                        "mukey": "5",
                        "areasymbol": "IN097",
                        "numeric_rating": 0.7,
                        "rated_pct": 100.0,
                        "total_pct": 100.0,
                    }
                ],
                [{"max_county_rating": 0.933}],
                [{"max_county_rating": 0.812}],
            ],
        ):
            ratings = [
                client.get_productivity_ratings(["4"], index_type="nccpi")[0],
                client.get_productivity_ratings(["5"], index_type="nccpi")[0],
            ]
            maxima = {
                "IL019": client.get_county_max_productivity_rating("IL019", "nccpi"),
                "IN097": client.get_county_max_productivity_rating("IN097", "nccpi"),
            }
        return {"ratings": ratings, "county_maxima": maxima}
    if case_id == "partial-rated-coverage":
        return _partial_land_evaluation()
    if case_id == "urban-partial-overlap":
        from fpac_soil_mcp.geometry import calculate_acreage, parse_geojson_geometry

        geometry = parse_geojson_geometry(
            {
                "type": "Polygon",
                "coordinates": [
                    [
                        [-93.65, 42.02],
                        [-93.63, 42.02],
                        [-93.63, 42.04],
                        [-93.65, 42.04],
                        [-93.65, 42.02],
                    ]
                ],
            }
        )
        total_acres = calculate_acreage(geometry)
        urban = UrbanExemptionRecord(
            status=IntegrationStatus.SUCCESS,
            geometry_hash="sha256:" + "a" * 64,
            provenance=Provenance(
                source_name="US Census Bureau TIGERweb",
                source_reference="https://tigerweb.geo.census.gov/",
                timestamp_utc=datetime.now(UTC),
                method_version="1.0.0",
                configuration_version="1.0.0",
            ),
            is_urban_intersected=True,
            screened_acreage=25.0,
        )
        sda = MagicMock(spec=SDAClient)
        sda.base_url = "https://sdmdataaccess.nrcs.usda.gov/Tabular/post.rest"
        sda.get_spatial_intersection.return_value = [
            {
                "mukey": "rated",
                "areasymbol": "IL019",
                "area_ac": total_acres * 0.6,
                "farmlndcl": "All areas are prime farmland",
            },
            {
                "mukey": "unrated",
                "areasymbol": "IL019",
                "area_ac": total_acres * 0.4,
                "farmlndcl": "Not prime farmland",
            },
        ]
        sda.get_interpretations.return_value = [
            {"mukey": "rated", "numeric_rating": 0.8, "rating_class": "High"}
        ]
        sda.get_county_max_productivity_rating.return_value = 1.0
        tigerweb = MagicMock(spec=TigerwebClient)
        tigerweb.check_urban_exemption_with_geometries.return_value = (urban, [])
        tigerweb.get_perimeter_evidence.return_value = {"evidence_status": "unavailable"}
        response = PolygonAnalyzer(sda, tigerweb).analyze_polygon(geometry)
        return response.model_dump(mode="json")
    if case_id == "missing-subjective-inputs":
        return evaluate_lesa(
            project_name="Gold-set missing inputs",
            land_evaluation=90.0,
            site_assessment=None,
        ).model_dump(mode="json")
    if case_id == "upstream-failure":
        with httpx.Client(
            transport=httpx.MockTransport(
                lambda _request: httpx.Response(503, text="Service Unavailable")
            )
        ) as http_client:
            client = SDAClient(max_retries=1, http_client=http_client)
            try:
                client.get_productivity_ratings(["6"], index_type="nccpi")
            except SDAQueryError as exc:
                return {
                    "error": {"type": type(exc).__name__},
                    "rating": None,
                }
        raise AssertionError("The mocked SDA failure did not raise SDAQueryError.")
    raise AssertionError(f"Unknown gold-set case: {case_id}")


def test_manifest_parser_reads_expected_counts(manifest: dict[str, set[str]]) -> None:
    assert len(manifest["tools"]) == 11
    assert len(manifest["resources"]) == 4
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


def test_phase4_gold_set_is_registered_as_deterministic_contract() -> None:
    cases = load_gold_set()
    assert len(cases) >= 8
    assert {case["status"] for case in cases} == {"covered", "indeterminate", "error"}
    assert all(case["deterministic"] is True for case in cases)


def test_phase4_gold_set_expectations_match_production_scenarios() -> None:
    for case in load_gold_set():
        actual = _gold_scenario(case["id"])
        for expected in case["expectations"]:
            matched, detail = match_expected(actual, expected)
            assert matched, f"{case['id']}: {detail}"
