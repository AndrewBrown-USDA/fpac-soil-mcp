from pathlib import Path

import pytest
from common.matching import load_policy_rules, policy_missing_requirements

from eval.databricks.agent import load_system_prompt
from fpac_soil_mcp.app import create_mcp_server
from fpac_soil_mcp.prompts.fppa_prompts import FPPA_POLICY_BLOCK

REPO_ROOT = Path(__file__).resolve().parents[1]
APP_SYSTEM_PROMPT_PATH = (
    REPO_ROOT
    / "apps"
    / "agent-fpac-soil-openai-sdk"
    / "agent_server"
    / "prompts"
    / "system_prompt.txt"
)


@pytest.mark.asyncio
async def test_site_assessment_prompt_uses_registry_and_preserves_authority_boundaries() -> None:
    server = create_mcp_server()
    result = await server.render_prompt("fppa_site_assessment_assistant", {})
    text = result.messages[0].content.text
    soil_screening = text.index("complete preliminary soil screening first")
    offer_interview = text.index("offer Start/Skip")
    assert soil_screening < offer_interview
    assert "Part V (Land Evaluation" in text
    assert "Part VI (Site Assessment" in text
    assert "only for non-linear site (Land Evaluation, LE) projects" in text
    assert "do not offer the interview for corridor projects" in text
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
    assert "one criterion at a time" in text
    assert "record unknown or unavailable facts" in text
    assert "preserve skipped answers as such" in text
    assert "never as zero" in text
    assert "combined CDL context automatically exactly once" in text
    assert "attached or supplied as pasted WKT/GeoJSON" in text
    assert "Do not follow it with a separate CDL histogram request" in text
    assert "never use it to answer or score Criterion 2" in text
    assert (
        "Do not make an interview-based preliminary LESA calculation before the interview is complete"
        in text
    )
    assert "ask for explicit confirmation" in text
    assert "Do not submit or score before the user confirms" in text


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
    assert FPPA_POLICY_BLOCK.strip() in text


@pytest.mark.parametrize("version", ["v1", "v2"])
def test_databricks_prompt_carries_shared_policy(version: str) -> None:
    text = load_system_prompt(version)
    policy = load_policy_rules()
    assert policy_missing_requirements(text, policy) == []
    assert FPPA_POLICY_BLOCK.strip() in text


def test_databricks_app_prompt_carries_canonical_policy_copy() -> None:
    text = APP_SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
    assert FPPA_POLICY_BLOCK.strip() in text
