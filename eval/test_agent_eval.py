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


def parse_pi_events(output: str) -> list[dict[str, Any]]:
    """Parse pi's JSONL event stream, ignoring non-JSON diagnostic lines."""
    events: list[dict[str, Any]] = []
    for line in output.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict):
            events.append(event)
    return events


def event_text(event: dict[str, Any]) -> str:
    """Flatten an event to searchable text for compatibility across pi event versions."""
    return json.dumps(event, ensure_ascii=False).lower()


def extract_structured_tool_names(event: dict[str, Any]) -> set[str]:
    """Extract tool names specifically from dedicated name/function fields in an event."""
    names: set[str] = set()
    event_type = str(event.get("type", "")).lower()

    if "tool" in event_type or event_type in {"call", "tool_use", "tool_call", "tool_execution"}:
        for key in ("tool_name", "tool", "name", "function_name"):
            val = event.get(key)
            if isinstance(val, str) and val:
                names.add(val)

        tool_call_obj = event.get("tool_call") or event.get("call") or event.get("function")
        if isinstance(tool_call_obj, dict):
            for key in ("name", "tool_name", "tool"):
                val = tool_call_obj.get(key)
                if isinstance(val, str) and val:
                    names.add(val)

    message = event.get("message")
    if isinstance(message, dict):
        tool_calls = message.get("tool_calls")
        if isinstance(tool_calls, list):
            for tc in tool_calls:
                if isinstance(tc, dict):
                    fn = tc.get("function")
                    if isinstance(fn, dict) and isinstance(fn.get("name"), str):
                        names.add(fn["name"])
                    elif isinstance(tc.get("name"), str):
                        names.add(tc["name"])

    content = event.get("content")
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") in {"tool_use", "tool_call"}:
                val = block.get("name") or block.get("tool")
                if isinstance(val, str) and val:
                    names.add(val)

    return names


def extract_assistant_content(event: dict[str, Any]) -> str:
    """Extract assistant response text or tool output from an event."""
    event_type = str(event.get("type", "")).lower()
    role = str(event.get("role", "")).lower()
    text_parts: list[str] = []

    if role in {"assistant", "model", "tool"} or event_type in {
        "assistant",
        "message",
        "text",
        "response",
        "tool_result",
        "tool_output",
    }:
        content = (
            event.get("content") or event.get("text") or event.get("result") or event.get("output")
        )
        if isinstance(content, str):
            text_parts.append(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, str):
                    text_parts.append(block)
                elif (
                    isinstance(block, dict)
                    and block.get("type") in {"text", "output", "result"}
                    and isinstance(block.get("text") or block.get("content"), str)
                ):
                    text_parts.append(block.get("text") or block.get("content") or "")

    message = event.get("message")
    if isinstance(message, dict) and str(message.get("role", "")).lower() in {"assistant", "model"}:
        msg_content = message.get("content")
        if isinstance(msg_content, str):
            text_parts.append(msg_content)
        elif isinstance(msg_content, list):
            for block in msg_content:
                if isinstance(block, str):
                    text_parts.append(block)
                elif isinstance(block, dict) and isinstance(block.get("text"), str):
                    text_parts.append(block["text"])

    return " ".join(text_parts)


def extract_tool_calls(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return events representing MCP/tool invocations from pi's JSON stream."""
    calls: list[dict[str, Any]] = []
    for event in events:
        if extract_structured_tool_names(event):
            calls.append(event)
    return calls


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
        "--mode",
        "json",
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
    events = parse_pi_events(result.stdout or "")
    assert events, f"pi returned no JSON events: {result.stdout}"

    event_stream = "\n".join(event_text(event) for event in events)
    assert "initialize" in event_stream, (
        f"MCP initialization event not found in pi event stream: {result.stdout}"
    )

    tool_calls = extract_tool_calls(events)
    target_tool = case["target_name"]
    matching_calls = [event for event in tool_calls if target_tool.lower() in event_text(event)]
    assert matching_calls, (
        f"Expected MCP tool call '{target_tool}' not found in pi event stream: {result.stdout}"
    )

    for expected_value in ("41.8781", "-93.0977"):
        assert any(expected_value in event_text(event) for event in matching_calls), (
            f"Expected parameter '{expected_value}' not found in call to {target_tool}: "
            f"{result.stdout}"
        )

    assistant_texts = [
        extract_assistant_content(ev) for ev in events if extract_assistant_content(ev)
    ]
    combined_content = " ".join(assistant_texts) if assistant_texts else (result.stdout or "")
    norm_content = normalize_text(combined_content).lower()

    # Verify key expected content or keywords
    for kw in case.get("expected_keywords", []):
        norm_kw = normalize_text(kw).lower()
        assert norm_kw in norm_content, (
            f"Expected keyword '{kw}' not found in normalized assistant output: {result.stdout}"
        )
