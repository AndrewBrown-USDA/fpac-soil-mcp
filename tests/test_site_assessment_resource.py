from __future__ import annotations

import json
from pathlib import Path

import pytest

from fpac_soil_mcp.mcp.app import create_mcp_server


@pytest.mark.asyncio
async def test_site_assessment_criteria_resource_is_discoverable_and_complete() -> None:
    server = create_mcp_server()
    resources = await server.list_resources()
    uris = {str(resource.uri) for resource in resources}
    assert "fppa://site-assessment-criteria" in uris

    result = await server.read_resource("fppa://site-assessment-criteria")
    payload = json.loads(result.contents[0].content)
    assert payload["schema_version"] == "1.0"
    assert len(payload["criteria"]) == 12
    assert all(item["citation"] for item in payload["criteria"])
    assert any(item["deferred_source"] for item in payload["criteria"])
    assert any(band["points"] is None for item in payload["criteria"] for band in item["bands"])
    assert "siting" not in json.dumps(payload).lower()


@pytest.mark.asyncio
async def test_resource_serves_only_registry_specified_band_fields() -> None:
    """The served bands must match the bundled registry file, with no null bounds.

    The agent app validates this payload strictly: null or default-filled bounds and
    inclusivity flags make it reject the criteria and disable the interview.
    """
    server = create_mcp_server()
    result = await server.read_resource("fppa://site-assessment-criteria")
    payload = json.loads(result.contents[0].content)
    registry_file = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "fpac_soil_mcp"
        / "data"
        / "site_assessment.v1.json"
    )
    for item in payload["criteria"]:
        for band in item["bands"]:
            assert "min" not in band or band["min"] is not None
            assert "max" not in band or band["max"] is not None
            assert ("min_inclusive" not in band) or ("min" in band)
            assert ("max_inclusive" not in band) or ("max" in band)
    served = {(c["criterion_number"], b["id"]): b for c in payload["criteria"] for b in c["bands"]}
    raw = json.loads(registry_file.read_text(encoding="utf-8"))
    for c in raw["criteria"]:
        for b in c["bands"]:
            assert served[(c["criterion_number"], b["id"])] == b
