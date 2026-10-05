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

from run_evals import (
    _tool_matches,
    extract_advertised_tool_names,
    should_retry_missing_tools,
)

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


def test_advertised_tools_prefer_initialization_event() -> None:
    events = [
        {"type": "mcp_initialize", "capabilities": {"tools": [{"name": "init_tool"}]}},
        {"type": "tools_list", "tools": [{"name": "fallback_tool"}]},
    ]
    assert extract_advertised_tool_names(events) == ({"init_tool"}, "initialization")


def test_tool_list_fallback_and_unknown_configuration_diagnostics() -> None:
    assert extract_advertised_tool_names(
        [{"type": "tools_list", "result": {"tools": [{"name": "listed_tool"}]}}]
    ) == ({"listed_tool"}, "tool-list fallback")
    assert extract_advertised_tool_names([{"type": "message_end", "message": {}}]) == (
        None,
        "unknown",
    )


def test_advertised_and_unadvertised_tools_are_distinguished_exactly() -> None:
    advertised, source = extract_advertised_tool_names(
        [{"type": "initialize", "tools": [{"name": "fpac_tool"}]}]
    )
    assert source == "initialization"
    assert advertised == {"fpac_tool"}
    assert "fpac_tool" in advertised
    assert "other_tool" not in advertised
    assert _tool_matches("tool", {"server_tool"})
    assert not _tool_matches("tool", {"server_tool_extra"})


def test_missing_advertised_tool_can_be_retried_once_without_prose_substitution() -> None:
    events = [
        {"type": "initialize", "tools": [{"name": "expected_tool"}]},
        {"type": "message_end", "message": {"role": "assistant", "content": "expected_tool"}},
    ]
    advertised, _ = extract_advertised_tool_names(events)
    executed = set().union(*(extract_structured_tool_names(event) for event in events))
    assert advertised == {"expected_tool"}
    assert not _tool_matches("expected_tool", executed)
    assert should_retry_missing_tools(["expected_tool"], advertised, 0)
    assert not should_retry_missing_tools(["expected_tool"], advertised, 1)
    assert "expected_tool" not in executed


def event_text(event: dict[str, Any]) -> str:
    """Flatten an event to searchable text for compatibility across pi event versions."""
    return json.dumps(event, ensure_ascii=False).lower()


def extract_structured_tool_names(event: dict[str, Any]) -> set[str]:
    """Extract tool names specifically from dedicated name/function fields in an event."""
    names: set[str] = set()
    event_type = str(event.get("type", "")).lower()

    # Direct tool execution or tool call events
    if "tool" in event_type or event_type in {
        "call",
        "tool_use",
        "tool_call",
        "tool_execution",
    }:
        for key in ("tool_name", "tool", "name", "function_name", "toolName"):
            val = event.get(key)
            if isinstance(val, str) and val:
                names.add(val)

        args_obj = event.get("args")
        if isinstance(args_obj, dict):
            sub_tool = args_obj.get("tool") or args_obj.get("name")
            if isinstance(sub_tool, str) and sub_tool:
                names.add(sub_tool)

        tool_call_obj = event.get("tool_call") or event.get("call") or event.get("function")
        if isinstance(tool_call_obj, dict):
            for key in ("name", "tool_name", "tool", "toolName"):
                val = tool_call_obj.get(key)
                if isinstance(val, str) and val:
                    names.add(val)
            sub_args = tool_call_obj.get("args") or tool_call_obj.get("arguments")
            if isinstance(sub_args, dict):
                sub_tool = sub_args.get("tool") or sub_args.get("name")
                if isinstance(sub_tool, str) and sub_tool:
                    names.add(sub_tool)

    # Tool calls embedded inside message objects
    message = event.get("message")
    if isinstance(message, dict):
        tool_calls = message.get("tool_calls") or message.get("toolCalls")
        if isinstance(tool_calls, list):
            for tc in tool_calls:
                if isinstance(tc, dict):
                    fn = tc.get("function")
                    if isinstance(fn, dict) and isinstance(fn.get("name"), str):
                        names.add(fn["name"])
                    elif isinstance(tc.get("name"), str):
                        names.add(tc["name"])
                    sub_args = tc.get("args") or tc.get("arguments")
                    if isinstance(sub_args, dict):
                        sub_tool = sub_args.get("tool") or sub_args.get("name")
                        if isinstance(sub_tool, str) and sub_tool:
                            names.add(sub_tool)

        # Content blocks inside message (e.g. toolCall, tool_use)
        msg_content = message.get("content")
        if isinstance(msg_content, list):
            for block in msg_content:
                if isinstance(block, dict):
                    btype = block.get("type", "")
                    if btype in {"tool_use", "tool_call", "toolCall"}:
                        val = block.get("name") or block.get("tool") or block.get("toolName")
                        if isinstance(val, str) and val:
                            names.add(val)
                        b_args = block.get("arguments") or block.get("args")
                        if isinstance(b_args, dict):
                            sub_tool = b_args.get("tool") or b_args.get("name")
                            if isinstance(sub_tool, str) and sub_tool:
                                names.add(sub_tool)

    # Nested content blocks (e.g. Claude/Pi tool_use content blocks)
    content = event.get("content")
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") in {
                "tool_use",
                "tool_call",
                "toolCall",
            }:
                val = block.get("name") or block.get("tool") or block.get("toolName")
                if isinstance(val, str) and val:
                    names.add(val)
                b_args = block.get("arguments") or block.get("args")
                if isinstance(b_args, dict):
                    sub_tool = b_args.get("tool") or b_args.get("name")
                    if isinstance(sub_tool, str) and sub_tool:
                        names.add(sub_tool)

    return names


def extract_assistant_content(event: dict[str, Any]) -> str:
    """Extract assistant response text or tool output from an event."""
    event_type = str(event.get("type", "")).lower()
    text_parts: list[str] = []

    # Handle pi structured events (message_end is emitted per assistant message turn)
    if event_type == "message_end":
        msg = event.get("message")
        if isinstance(msg, dict):
            msg_role = str(msg.get("role", "")).lower()
            if msg_role in {"assistant", "model"}:
                content = msg.get("content")
                if isinstance(content, str):
                    text_parts.append(content)
                elif isinstance(content, list):
                    for block in content:
                        if isinstance(block, str):
                            text_parts.append(block)
                        elif isinstance(block, dict) and block.get("type") == "text":
                            text_parts.append(block.get("text") or "")
                return " ".join(text_parts)

    return ""


def extract_tool_calls(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Extract structured MCP/tool invocations from pi's JSON stream."""
    calls: list[dict[str, Any]] = []

    def add_call(name: Any, arguments: Any) -> None:
        if isinstance(name, str) and name:
            if isinstance(arguments, str):
                try:
                    parsed_arguments = json.loads(arguments)
                except json.JSONDecodeError:
                    parsed_arguments = {}
            else:
                parsed_arguments = arguments
            calls.append(
                {
                    "name": name,
                    "arguments": parsed_arguments if isinstance(parsed_arguments, dict) else {},
                }
            )

    for event in events:
        event_type = str(event.get("type", "")).lower()
        direct_args = event.get("args")
        if isinstance(direct_args, dict):
            direct_name = direct_args.get("tool") or direct_args.get("name")
            if isinstance(direct_name, str):
                add_call(
                    direct_name,
                    direct_args.get("arguments") or direct_args.get("args"),
                )

        if "tool" in event_type or event_type in {
            "call",
            "tool_use",
            "tool_call",
            "tool_execution",
        }:
            for key in ("tool_name", "tool", "name", "function_name", "toolName"):
                if isinstance(event.get(key), str):
                    add_call(event[key], event.get("arguments") or event.get("args"))

            for key in ("tool_call", "call", "function"):
                nested = event.get(key)
                if isinstance(nested, dict):
                    for name_key in ("name", "tool_name", "tool", "toolName"):
                        if isinstance(nested.get(name_key), str):
                            add_call(
                                nested[name_key],
                                nested.get("arguments") or nested.get("args"),
                            )
                            break

        message = event.get("message")
        if isinstance(message, dict):
            tool_calls = message.get("tool_calls") or message.get("toolCalls")
            if isinstance(tool_calls, list):
                for tool_call in tool_calls:
                    if not isinstance(tool_call, dict):
                        continue
                    function = tool_call.get("function")
                    if isinstance(function, dict):
                        add_call(
                            function.get("name"),
                            function.get("arguments") or function.get("args"),
                        )
                    else:
                        add_call(
                            tool_call.get("name"),
                            tool_call.get("arguments") or tool_call.get("args"),
                        )

            content_blocks = message.get("content")
            if isinstance(content_blocks, list):
                for block in content_blocks:
                    if isinstance(block, dict) and block.get("type") in {
                        "tool_use",
                        "tool_call",
                        "toolCall",
                    }:
                        add_call(
                            block.get("name") or block.get("tool") or block.get("toolName"),
                            block.get("arguments") or block.get("args"),
                        )

        content = event.get("content")
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") in {
                    "tool_use",
                    "tool_call",
                    "toolCall",
                }:
                    add_call(
                        block.get("name") or block.get("tool") or block.get("toolName"),
                        block.get("arguments") or block.get("args"),
                    )

    return calls


def test_extract_tool_calls_preserves_structured_point_arguments() -> None:
    """Structured extraction retains coordinates and does not inspect flattened text."""
    events = [
        {
            "type": "message_end",
            "message": {
                "role": "assistant",
                "tool_calls": [
                    {
                        "function": {
                            "name": "get_farmland_classification_by_point",
                            "arguments": '{"latitude": 41.8781, "longitude": -93.0977}',
                        }
                    }
                ],
            },
        },
        {
            "type": "assistant_message",
            "content": "latitude 0 longitude 0 get_farmland_classification_by_point",
        },
    ]

    calls = extract_tool_calls(events)

    assert calls == [
        {
            "name": "get_farmland_classification_by_point",
            "arguments": {"latitude": 41.8781, "longitude": -93.0977},
        }
    ]


def test_point_01_structured_arguments_match_exact_coordinates() -> None:
    """Validate POINT-01 coordinates without invoking pi or a network."""
    events = [
        {
            "type": "message_end",
            "message": {
                "role": "assistant",
                "tool_calls": [
                    {
                        "function": {
                            "name": "get_farmland_classification_by_point",
                            "arguments": '{"latitude": 41.8781, "longitude": -93.0977}',
                        }
                    }
                ],
            },
        }
    ]

    point_call = extract_tool_calls(events)[0]
    assert point_call["name"] == "get_farmland_classification_by_point"
    assert float(point_call["arguments"]["latitude"]) == pytest.approx(41.8781, abs=1e-5)
    assert float(point_call["arguments"]["longitude"]) == pytest.approx(-93.0977, abs=1e-5)


def test_extract_tool_calls_supports_direct_args_objects() -> None:
    events = [
        {
            "type": "tool_execution",
            "args": {
                "tool": "get_farmland_classification_by_point",
                "arguments": {"latitude": 41.8781, "longitude": -93.0977},
            },
        },
        {
            "type": "tool_execution",
            "args": {
                "name": "get_farmland_classification_by_mukey",
                "args": {"mukey": "12345"},
            },
        },
    ]

    assert extract_tool_calls(events) == [
        {
            "name": "get_farmland_classification_by_point",
            "arguments": {"latitude": 41.8781, "longitude": -93.0977},
        },
        {"name": "get_farmland_classification_by_mukey", "arguments": {"mukey": "12345"}},
    ]


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

    model_override = os.environ.get("AGENT_EVAL_MODEL", "gpt-5.6-luna")
    cmd = [
        pi_exe,
        "--no-session",
        "--mode",
        "json",
        "--mcp-config",
        str(sandbox_env / "mcp_config.json"),
        "--append-system-prompt",
        "You are an automated evaluation agent connected to the fpac-soil-mcp MCP server. You MUST execute the appropriate fpac-soil MCP tool or read the MCP resource to fulfill the user request before generating the final response. Do not answer purely from memory if an MCP tool or resource is available.",
        "-p",
        f"Call the appropriate fpac-soil MCP tool/resource and {case['user_prompt']}",
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

    executed_tool_names: set[str] = set()
    for event in events:
        executed_tool_names.update(extract_structured_tool_names(event))

    target_tool = case["target_name"]
    is_tool_called = target_tool in executed_tool_names or any(
        executed.endswith((f"_{target_tool}", f":{target_tool}"))
        for executed in executed_tool_names
    )
    assert is_tool_called, (
        f"Expected MCP tool call '{target_tool}' not found in executed tools: {executed_tool_names}"
    )

    target_calls = [
        call
        for call in extract_tool_calls(events)
        if call["name"] == target_tool
        or call["name"].endswith((f"_{target_tool}", f":{target_tool}"))
    ]
    assert target_calls, f"Structured call for '{target_tool}' not found"
    point_arguments = target_calls[0]["arguments"]
    assert float(point_arguments["latitude"]) == pytest.approx(41.8781, abs=1e-5)
    assert float(point_arguments["longitude"]) == pytest.approx(-93.0977, abs=1e-5)

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
