"""Map result contract (ADR 0017) through the MCP tool layer.

Calls ``analyze_farmland_by_polygon`` and ``analyze_corridor_fppa`` through a
``FastMCP`` server built with ``register_tools``; the analyzers run for real on
synthetic SDA, TIGERweb and NASS clients. Synthetic geometry only.

The Phase 8 M3 "soil" exit item is met by the ``farmland_classes`` layer on
these two tools; the soil lookup tools, including
``get_soil_polygons_by_geometry``, are unchanged (EXECUTION_PLAN_44 D3).
"""

from __future__ import annotations

import asyncio
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastmcp import FastMCP
from shapely.geometry import box

from fpac_soil_mcp.authority import Provenance
from fpac_soil_mcp.corridor_analysis import CorridorAnalyzer
from fpac_soil_mcp.geometry import calculate_acreage
from fpac_soil_mcp.integration_models import (
    CountyAgProfile,
    IntegrationStatus,
    UrbanExemptionRecord,
)
from fpac_soil_mcp.polygon_analysis import PolygonAnalyzer
from fpac_soil_mcp.sda_client import SDAClient
from fpac_soil_mcp.tigerweb_client import TigerwebClient
from fpac_soil_mcp.tools import register_tools

MARKER = "R6-MARKER"
ADR_PATH = Path(__file__).resolve().parents[1] / "docs/decisions/0017-server-map-result-contract.md"
MAP_TOOLS = ("analyze_farmland_by_polygon", "analyze_corridor_fppa")
UNCHANGED_TOOLS = (
    "get_farmland_classification_by_point",
    "get_farmland_classification_by_mukey",
    "get_soil_polygons_by_geometry",
    "calculate_preliminary_lesa",
)
ADDITIVE_KEYS = ("schema_version", "data_mode", "authority", "map")
# Fixed allowance for the additive keys in a default (descriptor-only) response.
# A percentage does not work on small fixtures: the additive keys measured
# 2,163 bytes (polygon, +43%) and 2,657 bytes (corridor, +47%) here, mostly the
# seven-item farmland legend. Real responses are larger, so the share is lower.
DEFAULT_SIZE_MARGIN_BYTES = 4_000

POLYGON = {
    "type": "Polygon",
    "coordinates": [[[0.0, 0.0], [0.01, 0.0], [0.01, 0.01], [0.0, 0.01], [0.0, 0.0]]],
}
CENTERLINE = {"type": "LineString", "coordinates": [[0.0, 0.005], [0.01, 0.005]]}
PROVENANCE = Provenance(
    source_name="synthetic",
    source_reference="synthetic",
    timestamp_utc=datetime(2026, 1, 1, tzinfo=UTC),
    method_version="1.0.0",
    configuration_version="1.0.0",
)


def _sda() -> MagicMock:
    sda = MagicMock(spec=SDAClient)
    sda.base_url = "https://sdmdataaccess.nrcs.usda.gov/Tabular/post.rest"

    def spatial(wkt, clip=True, geom_acres=True, return_geom=False):
        rows = [
            {
                "mukey": "3001",
                "musym": f"{MARKER}A",
                "muname": f"{MARKER} prime unit",
                "farmlndcl": "All areas are prime farmland",
                "areasymbol": "ZZ001",
                "area_ac": "6.0",
                "geom": box(0.0, 0.0, 0.005, 0.01).wkt,
            },
            {
                "mukey": "3002",
                "musym": f"{MARKER}B",
                "muname": f"{MARKER} local unit",
                "farmlndcl": "Farmland of local importance",
                "areasymbol": "ZZ001",
                "area_ac": "6.0",
                "geom": box(0.005, 0.0, 0.01, 0.01).wkt,
            },
        ]
        if not return_geom:
            for row in rows:
                row.pop("geom")
        return rows

    sda.get_spatial_intersection.side_effect = spatial
    sda.get_interpretations.return_value = [
        {"mukey": "3001", "numeric_rating": "0.8", "rating_class": "High"},
        {"mukey": "3002", "numeric_rating": "0.4", "rating_class": "Low"},
    ]
    sda.get_productivity_ratings.return_value = []
    sda.get_county_max_productivity_rating.return_value = 1.0
    return sda


def _tiger() -> MagicMock:
    tiger = MagicMock(spec=TigerwebClient)
    record = UrbanExemptionRecord(
        status=IntegrationStatus.SUCCESS,
        geometry_hash="sha256:" + "3" * 64,
        provenance=PROVENANCE,
        is_urban_intersected=True,
        urban_area_names=[f"{MARKER} Urban"],
        screened_acreage=0.0,
    )
    tiger.check_urban_exemption_with_geometries.side_effect = lambda geom: (
        record,
        [(f"{MARKER} Urban", box(0.008, 0.008, 0.02, 0.02))],
    )
    tiger.get_perimeter_evidence.return_value = {"evidence_status": "synthetic"}
    tiger.get_intersecting_counties.return_value = [
        {"state_fips": "99", "county_fips": "001", "county_name": f"{MARKER} County"}
    ]
    tiger.partition_geometry_by_counties.side_effect = lambda geometry_input, counties=None, **kw: [
        {
            "state_fips": "99",
            "county_fips": "001",
            "county_name": f"{MARKER} County",
            "state_name": "ZZ",
            "geometry": geometry_input,
            "calculated_acres": calculate_acreage(geometry_input),
        }
    ]
    return tiger


def _nass() -> MagicMock:
    nass = MagicMock()
    nass.get_county_ag_profile.side_effect = lambda county, **kw: CountyAgProfile(
        status=IntegrationStatus.SUCCESS,
        state_fips=county.state_fips,
        county_fips=county.county_fips,
        county_name=county.county_name,
        census_year=2022,
        provenance=PROVENANCE,
        average_farm_size_acres=300.0,
    )
    return nass


@pytest.fixture
def mcp() -> FastMCP:
    server = FastMCP("map-tool-contract-test")
    register_tools(server)
    return server


@pytest.fixture(autouse=True)
def synthetic_analyzers():
    """Make the tool layer build analyzers on synthetic clients."""
    with (
        patch(
            "fpac_soil_mcp.tools.spatial_analysis_tools.PolygonAnalyzer",
            side_effect=lambda: PolygonAnalyzer(sda_client=_sda(), tigerweb_client=_tiger()),
        ),
        patch(
            "fpac_soil_mcp.tools.spatial_analysis_tools.CorridorAnalyzer",
            side_effect=lambda: CorridorAnalyzer(
                sda_client=_sda(), tigerweb_client=_tiger(), nass_client=_nass()
            ),
        ),
    ):
        yield


def _call(mcp: FastMCP, name: str, **arguments: Any) -> dict[str, Any]:
    result = asyncio.run(mcp.call_tool(name, arguments))
    assert isinstance(result.structured_content, dict)
    return result.structured_content


def _polygon(mcp: FastMCP, **kw: Any) -> dict[str, Any]:
    return _call(mcp, "analyze_farmland_by_polygon", geojson=POLYGON, **kw)


def _corridor(mcp: FastMCP, **kw: Any) -> dict[str, Any]:
    return _call(
        mcp,
        "analyze_corridor_fppa",
        centerline=CENTERLINE,
        buffer_distance=50.0,
        buffer_units="meters",
        **kw,
    )


def _size(payload: dict[str, Any]) -> int:
    return len(json.dumps(payload, separators=(",", ":"), default=str))


# --- tool schema --------------------------------------------------------------


def test_include_map_only_on_the_two_analyze_tools(mcp):
    tools = {t.name: t for t in asyncio.run(mcp.list_tools())}
    for name in MAP_TOOLS:
        prop = tools[name].parameters["properties"]["include_map"]
        assert prop["type"] == "boolean"
        assert prop["default"] is False
        assert prop["description"].startswith("Leave false.")
        assert "include_map" not in tools[name].parameters.get("required", [])
    for name in UNCHANGED_TOOLS:
        assert "include_map" not in tools[name].parameters["properties"]


# --- delivery -------------------------------------------------------------------


@pytest.mark.parametrize("call", [_polygon, _corridor])
def test_default_call_returns_descriptors_only(mcp, call):
    payload = call(mcp)
    layers = payload["map"]["layers"]
    assert layers
    assert all(layer["delivery"] == "omitted" for layer in layers)
    assert all(layer["feature_collection"] is None for layer in layers)
    assert payload["map"]["bounds"] is None
    assert '"coordinates"' not in json.dumps(payload["map"])


@pytest.mark.parametrize("call", [_polygon, _corridor])
def test_include_map_returns_inline_layers(mcp, call):
    payload = call(mcp, include_map=True)
    layers = {layer["id"]: layer for layer in payload["map"]["layers"]}
    assert all(layer["delivery"] == "inline_geojson" for layer in layers.values())
    farmland = layers["farmland_classes"]["feature_collection"]
    assert farmland["type"] == "FeatureCollection"
    assert {f["properties"]["farmland_class"] for f in farmland["features"]} == {"prime", "local"}
    assert payload["map"]["bounds"] is not None


def test_corridor_lesa_evaluation_survives_include_map(mcp):
    payload = _corridor(
        mcp,
        include_map=True,
        site_assessment_inputs={"criteria_inputs": {"1": {"awarded_points": 10}}},
    )
    assert "lesa_evaluation" in payload
    assert payload["lesa_evaluation"]["total_lesa_score"] >= 0
    assert any(layer["delivery"] == "inline_geojson" for layer in payload["map"]["layers"])


@pytest.mark.parametrize("call", [_polygon, _corridor])
def test_include_map_does_not_change_numbers(mcp, call):
    plain, mapped = call(mcp), call(mcp, include_map=True)
    for key in ("geometry_hash", "tabular_csv", "limitations", "regulatory_notice"):
        assert plain[key] == mapped[key]
    for key in (
        "farmland_summary",
        "map_units",
        "impact_breakdown",
        "county_segments",
        "alternatives",
    ):
        if key in plain:
            assert plain[key] == mapped[key]


@pytest.mark.parametrize("call", [_polygon, _corridor])
def test_default_response_size_within_fixed_margin(mcp, call):
    payload = call(mcp)
    pre_change = {k: v for k, v in payload.items() if k not in ADDITIVE_KEYS}
    added = _size(payload) - _size(pre_change)
    assert 0 < added <= DEFAULT_SIZE_MARGIN_BYTES, added


# --- ADR 0017 strategy section 4 parity ---------------------------------------

# section 4 field -> (polygon keys, corridor keys) that must be present, or None when
# the contract says "not provided" (the section 4 name must then be absent).
SECTION_4: dict[str, tuple[tuple[str, ...], tuple[str, ...]] | None] = {
    "schema_version": (("schema_version",), ("schema_version",)),
    "analysis_id": None,
    "analysis_type": (("query_type",), ("query_type",)),
    "status": None,
    "data_mode": (("data_mode",), ("data_mode",)),
    "source_status": None,
    "authority": (("authority",), ("authority",)),
    "summary": (("farmland_summary",), ("impact_breakdown", "reconciliation_summary")),
    "metrics": (("map_units",), ("county_segments", "alternatives")),
    "map": (("map",), ("map",)),
    "provenance.analysis_timestamp": (("source",), ("source",)),
    "provenance.rule_version": (("manifest",), ("manifest",)),
    "provenance.sources": (("source", "manifest"), ("source", "manifest")),
    "provenance.calculation_crs": None,
    "privacy": None,
    "warnings": (("limitations",), ("limitations",)),
    "disclaimer": (("regulatory_notice",), ("regulatory_notice",)),
}


def _adr_section_4_fields() -> list[str]:
    text = ADR_PATH.read_text(encoding="utf-8")
    section = text.split("### Mapping to strategy section 4", 1)[1].split("\n### ", 1)[0]
    return re.findall(r"^\| `([^`]+)` \|", section, flags=re.MULTILINE)


def test_section_4_table_matches_adr():
    assert _adr_section_4_fields() == list(SECTION_4)


@pytest.mark.parametrize(("call", "side"), [(_polygon, 0), (_corridor, 1)])
def test_section_4_parity_field_by_field(mcp, call, side):
    payload = call(mcp)
    for field, keys in SECTION_4.items():
        top = field.split(".", 1)[0]
        if keys is None:
            assert top not in payload, field
            continue
        for key in keys[side]:
            assert key in payload, (field, key)

    # Details the table promises beyond key presence.
    assert payload["schema_version"] == "1.0"
    assert payload["data_mode"] == "live"
    assert payload["authority"]["official_filing"] is False
    assert payload["source"]["timestamp_utc"]
    assert payload["map"]["display_crs"] == "EPSG:4326"
    assert isinstance(payload["map"]["warnings"], list)
    for layer in payload["map"]["layers"]:
        assert layer["source"]
        assert "data_vintage" in layer
    if side == 0:
        assert payload["coverage_status"]
    else:
        assert all(seg["coverage_status"] for seg in payload["county_segments"])
