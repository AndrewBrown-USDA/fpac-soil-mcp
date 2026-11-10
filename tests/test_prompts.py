from pathlib import Path

import pytest
from common.matching import load_policy_rules, policy_missing_requirements

from fpac_soil_mcp.app import create_mcp_server

REPO_ROOT = Path(__file__).resolve().parents[1]


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


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "prompt_name",
    [
        "fppa_screening_assistant",
        "fppa_corridor_screening_assistant",
        "fppa_urban_exemption_assistant",
        "fppa_site_assessment_assistant",
    ],
)
async def test_fastmcp_prompt_carries_shared_policy(prompt_name: str) -> None:
    server = create_mcp_server()
    text = (await server.render_prompt(prompt_name, {})).messages[0].content.text
    assert policy_missing_requirements(text) == []


@pytest.mark.parametrize(
    "prompt_path",
    [
        REPO_ROOT / "eval" / "databricks" / "prompts" / "system_prompt_v1.txt",
        REPO_ROOT / "eval" / "databricks" / "prompts" / "system_prompt_v2.txt",
    ],
)
def test_databricks_prompt_carries_shared_policy(prompt_path: Path) -> None:
    text = prompt_path.read_text(encoding="utf-8")
    policy = load_policy_rules()
    assert policy_missing_requirements(text, policy) == []
