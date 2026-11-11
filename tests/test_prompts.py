import pytest

from fpac_soil_mcp.app import create_mcp_server


@pytest.mark.asyncio
async def test_site_assessment_prompt_uses_registry_and_preserves_authority_boundaries() -> None:
    server = create_mcp_server()
    result = await server.render_prompt("fppa_site_assessment_assistant", {})
    text = result.messages[0].content.text
    assert "Part V (Land Evaluation" in text
    assert "Part VI (Site Assessment" in text
    assert "fppa://site-assessment-criteria" in text
    assert "unknown or unavailable" in text.lower()
    assert "never guess facts or invent points" in text
    assert "Never propose a site, footprint, alignment, project design" in text
    assert "not an official FPPA determination" in text
    assert "USDA recommends increasingly higher levels of consideration" in text
    assert "§ 658.4(c)(3)" in text
    assert "agency personnel consider" in text
    assert "must provide in-depth consideration" not in text
    assert "Consider alternative sites if available" not in text
