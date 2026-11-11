from __future__ import annotations

import json

import pytest

from fpac_soil_mcp.app import create_mcp_server


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
