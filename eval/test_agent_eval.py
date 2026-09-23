"""Agentic integration test harness invoking the pi coding agent CLI against fpac-soil-mcp.

Tests in this module run pi in an isolated temporary sandbox directory outside
the repository root, with an ephemeral .mcp.json pointing to fpac-soil-mcp.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PROMPT_FIXTURES_PATH = REPO_ROOT / "eval" / "prompt_test_cases.json"


def normalize_text(text: str) -> str:
    """Normalize text by standardizing unicode characters (e.g. non-breaking hyphens, special spaces)."""
    normalized = unicodedata.normalize("NFKD", text)
    normalized = re.sub(r"[\u2010\u2011\u2012\u2013\u2014\u2015\u2212]", "-", normalized)
    normalized = re.sub(r"[\u00a0\u2000-\u200b\u202f\u205f\u3000]", " ", normalized)
    return normalized


def get_pi_executable() -> str | None:
    """Resolve the pi executable path cross-platform (including Windows .cmd/.bat)."""
    pi_path = shutil.which("pi")
    if pi_path:
        return pi_path
    if sys.platform == "win32":
        for ext in [".cmd", ".bat", ".exe"]:
            pi_ext = shutil.which(f"pi{ext}")
            if pi_ext:
                return pi_ext
    return None


def is_pi_available() -> bool:
    """Check if the pi coding agent CLI is available on the system PATH."""
    return get_pi_executable() is not None


@pytest.fixture(scope="module")
def prompt_dataset() -> list[dict[str, Any]]:
    """Load prompt test cases from the eval dataset."""
    assert PROMPT_FIXTURES_PATH.exists(), f"Missing fixtures at {PROMPT_FIXTURES_PATH}"
    with open(PROMPT_FIXTURES_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("test_cases", [])


@pytest.fixture
def sandbox_env() -> Generator[Path, None, None]:
    """Create an isolated temporary sandbox directory with ephemeral .mcp.json."""
    with tempfile.TemporaryDirectory(prefix="pi_mcp_eval_") as tmp_dir:
        sandbox_path = Path(tmp_dir)

        # Create ephemeral .mcp.json pointing back to repository using uv run
        mcp_config = {
            "mcpServers": {
                "fpac-soil": {
                    "command": "uv",
                    "args": [
                        "--directory",
                        str(REPO_ROOT),
                        "run",
                        "fpac-soil-mcp",
                    ],
                    "env": {
                        "MCP_TRANSPORT": "stdio",
                    },
                }
            }
        }

        mcp_config_path = sandbox_path / ".mcp.json"
        with open(mcp_config_path, "w", encoding="utf-8") as f:
            json.dump(mcp_config, f, indent=2)

        mcp_custom_path = sandbox_path / "mcp_config.json"
        with open(mcp_custom_path, "w", encoding="utf-8") as f:
            json.dump(mcp_config, f, indent=2)

        yield sandbox_path


@pytest.mark.agent_eval
def test_prompt_dataset_schema_and_completeness(prompt_dataset: list[dict[str, Any]]) -> None:
    """Verify that prompt test cases cover all required tools, resources, and prompts."""
    assert len(prompt_dataset) >= 16, f"Expected >= 16 test cases, got {len(prompt_dataset)}"

    tools_covered = {tc["target_name"] for tc in prompt_dataset if tc.get("target_type") == "tool"}
    resources_covered = {
        tc["target_name"] for tc in prompt_dataset if tc.get("target_type") == "resource"
    }
    prompts_covered = {
        tc["target_name"] for tc in prompt_dataset if tc.get("target_type") == "prompt"
    }

    expected_tools = {
        "get_farmland_classification_by_point",
        "get_farmland_classification_by_mukey",
        "explain_fppa_screening_scope",
        "list_farmland_classes",
        "analyze_farmland_by_polygon",
        "get_soil_polygons_by_geometry",
        "check_urban_area_exemption",
        "get_soil_interpretations",
        "analyze_corridor_fppa",
    }
    expected_resources = {
        "fppa://regulatory-notice",
        "fppa://screening-guidance",
        "fppa://farmland-classes",
    }
    expected_prompts = {
        "fppa_screening_assistant",
        "fppa_corridor_screening_assistant",
        "fppa_urban_exemption_assistant",
        "fppa_site_assessment_assistant",
    }

    assert expected_tools.issubset(tools_covered)
    assert expected_resources.issubset(resources_covered)
    assert expected_prompts.issubset(prompts_covered)


@pytest.mark.agent_eval
def test_pi_point_screening_evaluation(
    sandbox_env: Path, prompt_dataset: list[dict[str, Any]]
) -> None:
    """Test running a representative point screening prompt via pi CLI in the sandbox."""
    pi_exe = get_pi_executable()
    if not pi_exe:
        pytest.skip("pi CLI is not installed or available on PATH")

    # Find POINT-01 test case
    case = next((tc for tc in prompt_dataset if tc["id"] == "POINT-01"), None)
    assert case is not None, "POINT-01 test case not found"

    model_override = os.environ.get("AGENT_EVAL_MODEL")
    cmd = [
        pi_exe,
        "--no-session",
        "--mcp-config",
        str(sandbox_env / "mcp_config.json"),
        "--append-system-prompt",
        "You are an automated evaluation agent connected to the fpac-soil-mcp MCP server. Always inspect and call the available fpac-soil MCP tools, MCP resources, and MCP prompts immediately to answer the user query. Do not ask for confirmation, do not request external files, and do not look for local files when an MCP tool or resource is available.",
        "-p",
        case["user_prompt"],
    ]
    if model_override:
        cmd.extend(["--model", model_override])

    # Run in the isolated sandbox cwd
    result = subprocess.run(
        cmd,
        cwd=str(sandbox_env),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        check=False,
    )

    assert result.returncode == 0, f"pi invocation failed: {result.stderr}"
    norm_stdout = normalize_text(result.stdout or "").lower()

    # Verify key expected content or keywords
    for kw in case.get("expected_keywords", []):
        norm_kw = normalize_text(kw).lower()
        assert norm_kw in norm_stdout, (
            f"Expected keyword '{kw}' not found in normalized output: {result.stdout}"
        )
