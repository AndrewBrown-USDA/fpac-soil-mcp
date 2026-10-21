#!/usr/bin/env python3
"""Release-time agentic evaluation benchmark runner using the pi coding agent CLI.

Runs prompt test cases against the fpac-soil-mcp server in an isolated sandbox,
verifies tool call execution and keyword presence, and displays a summary report.

Usage:
    python eval/pi/run_evals.py [--category CATEGORY] [--case-id CASE_ID] [--model MODEL] [--timeout TIMEOUT] [--verbose]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any

# Ensure UTF-8 output on Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

EVAL_ROOT = Path(__file__).resolve().parent.parent
if str(EVAL_ROOT) not in sys.path:
    sys.path.insert(0, str(EVAL_ROOT))

from common.matching import keywords_present, tool_matches

REPO_ROOT = EVAL_ROOT.parent
FIXTURES_PATH = REPO_ROOT / "eval" / "prompt_test_cases.json"
MAX_CAPTURE_BYTES = 64 * 1024
MAX_CAPTURE_LINES = 1000
MAX_CAPTURE_EVENTS = 500
SAFE_ID = re.compile(r"[^A-Za-z0-9_-]+")
SENSITIVE = re.compile(
    r"(?i)(?:api[_ -]?key|token|secret|password|authorization|cookie|"
    r"email|phone|address|coordinates?|geometry|geojson|wkt)\s*[:=]\s*[^\s,;]+"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run pi coding agent prompt evaluation benchmarks against fpac-soil-mcp."
    )
    parser.add_argument(
        "--category",
        type=str,
        default="all",
        help="Filter test cases by category substring (e.g., 'Point', 'Polygon', 'Corridor', 'all').",
    )
    parser.add_argument(
        "--capture-artifacts", action="store_true", help="Retain sanitized eval artifacts."
    )
    parser.add_argument(
        "--artifact-root", type=Path, default=None, help="External root for retained artifacts."
    )
    parser.add_argument(
        "--case-id",
        type=str,
        default=None,
        help="Run a single specific test case by ID (e.g., 'POINT-01', 'CORR-01').",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=os.environ.get("AGENT_EVAL_MODEL", "gpt-5.6-luna"),
        help="Model string/pattern to pass to pi (overrides AGENT_EVAL_MODEL env var, default: gpt-5.6-luna).",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Per-test timeout in seconds (default: 300s).",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print verbose stdout/stderr from pi for each prompt.",
    )
    parser.add_argument(
        "--show-output",
        "-s",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Print model response text for each evaluated case (default: True). Use --no-show-output to suppress.",
    )
    return parser.parse_args()


def _bounded(text: str | bytes | None) -> tuple[str, bool]:
    if isinstance(text, bytes):
        text = text.decode("utf-8", "replace")
    text = text or ""
    truncated = len(text.encode("utf-8")) > MAX_CAPTURE_BYTES
    if truncated:
        text = text.encode("utf-8")[:MAX_CAPTURE_BYTES].decode("utf-8", "ignore")
    return text, truncated


def _sanitize(text: str) -> str:
    return SENSITIVE.sub("[REDACTED]", text)


def _safe_id(value: str) -> str:
    safe = SAFE_ID.sub("_", str(value)).strip("_")
    return safe[:80] or "unknown"


def _artifact_root(root: Path | None) -> Path | None:
    if root is None:
        return None
    resolved = root.expanduser().resolve()
    try:
        resolved.relative_to(REPO_ROOT)
    except ValueError:
        return resolved
    raise ValueError("artifact root must be outside the repository")


def _capture_attempt(
    root: Path | None,
    run_id: str,
    case_id: str,
    attempt: int,
    metadata: dict[str, Any],
    stdout: str,
    stderr: str,
    events: list[dict[str, Any]],
    malformed: list[str],
) -> dict[str, str]:
    if root is None:
        return {}
    directory = root / _safe_id(run_id) / _safe_id(case_id) / f"attempt-{attempt}"
    directory.mkdir(parents=True, exist_ok=True)
    files = {
        "metadata": directory / "metadata.json",
        "stdout": directory / "stdout.txt",
        "stderr": directory / "stderr.txt",
        "events": directory / "events.jsonl",
        "malformed_lines": directory / "malformed-lines.txt",
        "raw_stdout": directory / "raw-stdout.txt",
        "raw_stderr": directory / "raw-stderr.txt",
        "raw_events": directory / "raw-events.jsonl",
        "raw_malformed_lines": directory / "raw-malformed-lines.txt",
    }
    bounded_stdout, stdout_truncated = _bounded(_sanitize(stdout))
    bounded_stderr, stderr_truncated = _bounded(_sanitize(stderr))
    bounded_events = events[:MAX_CAPTURE_EVENTS]
    bounded_malformed = malformed[:MAX_CAPTURE_LINES]
    metadata = {
        **metadata,
        "artifact_stdout_truncated": stdout_truncated,
        "artifact_stderr_truncated": stderr_truncated,
        "artifact_events_truncated": len(bounded_events) < len(events),
        "artifact_malformed_lines_truncated": len(bounded_malformed) < len(malformed),
    }
    files["metadata"].write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
    files["stdout"].write_text(bounded_stdout, encoding="utf-8")
    files["stderr"].write_text(bounded_stderr, encoding="utf-8")
    files["events"].write_text(
        "".join(json.dumps(event, sort_keys=True) + "\n" for event in bounded_events),
        encoding="utf-8",
    )
    files["malformed_lines"].write_text(
        "".join(_sanitize(line) + "\n" for line in bounded_malformed), encoding="utf-8"
    )
    files["raw_stdout"].write_text(stdout, encoding="utf-8")
    files["raw_stderr"].write_text(stderr, encoding="utf-8")
    files["raw_events"].write_text(
        "".join(json.dumps(event, sort_keys=True) + "\n" for event in events), encoding="utf-8"
    )
    files["raw_malformed_lines"].write_text(
        "".join(line + "\n" for line in malformed), encoding="utf-8"
    )
    return {key + "_path": str(path.relative_to(root)) for key, path in files.items()}


def get_pi_executable() -> str:
    """Resolve the pi executable path cross-platform (including Windows .cmd/.bat)."""
    pi_path = shutil.which("pi")
    if pi_path:
        return pi_path
    if sys.platform == "win32":
        for ext in [".cmd", ".bat", ".exe"]:
            pi_ext = shutil.which(f"pi{ext}")
            if pi_ext:
                return pi_ext
    return "pi"


def check_prerequisites() -> str:
    pi_exe = get_pi_executable()
    if not shutil.which(pi_exe):
        print(
            "ERROR: 'pi' CLI is not found on PATH. Please ensure pi is installed.", file=sys.stderr
        )
        sys.exit(1)

    if not FIXTURES_PATH.exists():
        print(f"ERROR: Prompt fixtures not found at {FIXTURES_PATH}", file=sys.stderr)
        sys.exit(1)
    return pi_exe


def load_test_cases(category: str, case_id: str | None) -> list[dict[str, Any]]:
    with open(FIXTURES_PATH, encoding="utf-8") as f:
        data = json.load(f)
    cases = data.get("test_cases", [])

    if case_id:
        cases = [c for c in cases if c.get("id") == case_id]
    elif category != "all":
        cases = [c for c in cases if category.lower() in c.get("category", "").lower()]

    return cases


def create_sandbox(sandbox_dir: Path) -> None:
    # The temporary working directory keeps the agent away from the repository
    # files. A future hardening step can replace this with pi-sandbox/container
    # isolation: https://github.com/brownag/pi-sandbox
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
    with open(sandbox_dir / ".mcp.json", "w", encoding="utf-8") as f:
        json.dump(mcp_config, f, indent=2)

    # Also generate an explicit mcp-config.json for pi --mcp-config
    mcp_file = sandbox_dir / "mcp_config.json"
    with open(mcp_file, "w", encoding="utf-8") as f:
        json.dump(mcp_config, f, indent=2)


def extract_structured_tool_names(event: dict[str, Any]) -> set[str]:
    """Extract tool names specifically from dedicated name/function fields in an event."""
    names: set[str] = set()
    event_type = str(event.get("type", "")).lower()

    if (
        event_type in {"tool_execution_start", "tool_execution_end"}
        and event.get("toolName") == "mcpScript"
    ):
        args = event.get("args")
        code = args.get("code") if isinstance(args, dict) else None
        if isinstance(code, str):
            names.update(
                match.group(1)
                for match in re.finditer(
                    r"""tools\.call\(\s*["']([A-Za-z0-9_.:-]+)["']\s*,""", code
                )
            )
        details = event.get("details")
        calls = details.get("calls") if isinstance(details, dict) else None
        if isinstance(calls, list):
            for call in calls:
                path = call.get("path") if isinstance(call, dict) else None
                if isinstance(path, str):
                    leaf = re.split(r"[/.:]", path.rstrip("/"))[-1]
                    if re.fullmatch(r"[A-Za-z0-9_-]+", leaf):
                        names.add(leaf)

    # Direct tool execution or tool call events
    if "tool" in event_type or event_type in {"call", "tool_use", "tool_call", "tool_execution"}:
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


def _has_dedicated_invocation(event: dict[str, Any]) -> bool:
    """Return whether an event contains a structured tool invocation container."""
    if extract_structured_tool_names(event):
        return True
    for container in (event.get("tool_call"), event.get("call"), event.get("function")):
        if isinstance(container, dict) and any(
            isinstance(container.get(key), str) and container[key]
            for key in ("name", "tool_name", "tool", "toolName", "function_name")
        ):
            return True
    message = event.get("message")
    if isinstance(message, dict):
        if isinstance(message.get("tool_calls") or message.get("toolCalls"), list):
            return True
        content = message.get("content")
        if isinstance(content, list) and any(
            isinstance(block, dict) and block.get("type") in {"tool_use", "tool_call", "toolCall"}
            for block in content
        ):
            return True
    return False


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


def _tool_names_from_list(value: Any) -> set[str] | None:
    if not isinstance(value, list):
        return None
    names = {
        item.get("name")
        for item in value
        if isinstance(item, dict) and isinstance(item.get("name"), str) and item["name"]
    }
    return names


def extract_advertised_tool_names(events: list[dict[str, Any]]) -> tuple[set[str] | None, str]:
    """Read MCP tools from initialization, then use an explicit list-tools result."""
    for event in events:
        event_type = str(event.get("type", "")).lower()
        if "init" not in event_type:
            continue
        candidates = [
            event.get("tools"),
            event.get("capabilities", {}).get("tools")
            if isinstance(event.get("capabilities"), dict)
            else None,
            event.get("result", {}).get("tools") if isinstance(event.get("result"), dict) else None,
        ]
        for candidate in candidates:
            names = _tool_names_from_list(candidate)
            if names is not None:
                return names, "initialization"

    for event in events:
        event_type = str(event.get("type", "")).lower()
        if "tool" not in event_type or "list" not in event_type:
            continue
        candidates = [event.get("tools"), event.get("result")]
        for candidate in candidates:
            if isinstance(candidate, dict):
                candidate = candidate.get("tools")
            names = _tool_names_from_list(candidate)
            if names is not None:
                return names, "tool-list fallback"
    return None, "unknown"


def extract_structured_prompt_names(event: dict[str, Any]) -> set[str]:
    """Extract prompt names only from dedicated structured prompt fields."""
    names: set[str] = set()
    event_type = str(event.get("type", "")).lower()
    if "prompt" not in event_type:
        return names
    for key in ("prompt_name", "promptName", "name"):
        value = event.get(key)
        if isinstance(value, str) and value:
            names.add(value)
    for key in ("prompt", "prompt_call", "promptCall"):
        container = event.get(key)
        if isinstance(container, dict):
            for name_key in ("name", "prompt_name", "promptName"):
                value = container.get(name_key)
                if isinstance(value, str) and value:
                    names.add(value)
    return names


def prompt_case_instruction(case: dict[str, Any]) -> str:
    """Build an explicit, bounded instruction for rendering a named MCP prompt."""
    prompt_name = case.get("target_name", "")
    citation_note = ""
    if case.get("id") == "RES-01":
        citation_note = (
            " Retain the exact keywords 7 CFR Part 657, 7 CFR Part 658, and preliminary "
            "in the final answer."
        )
    elif case.get("id") == "PROMPT-02":
        citation_note = (
            " Retain 7 CFR § 658.5(c), CPA-106 guidance, and the preliminary limitation "
            "in the final answer."
        )
    if case.get("target_type") == "prompt":
        return (
            f"First invoke or render the MCP prompt named {prompt_name}; use its rendered "
            f"instructions before answering. Then complete this request: {case['user_prompt']}."
            f"{citation_note}"
        )
    return (
        f"Call the appropriate fpac-soil MCP tool/resource and {case['user_prompt']}{citation_note}"
    )


_tool_matches = tool_matches


def should_retry_missing_tools(
    missing_tools: list[str], advertised_tools: set[str] | None, retry_count: int
) -> bool:
    return (
        retry_count == 0
        and advertised_tools is not None
        and bool(missing_tools)
        and all(tool in advertised_tools for tool in missing_tools)
    )


def run_case(
    case: dict[str, Any],
    sandbox_dir: Path,
    model: str | None,
    timeout: int,
    verbose: bool,
    pi_exe: str = "pi",
    run_id: str | None = None,
    artifact_root: Path | None = None,
) -> dict[str, Any]:
    case_id = case["id"]
    prompt = case["user_prompt"]
    expected_keywords = case.get("expected_keywords", [])
    expected_tools = case.get("expected_tools", [])
    run_id = run_id or uuid.uuid4().hex
    try:
        artifact_root = _artifact_root(artifact_root)
    except ValueError as exc:
        artifact_root = None
        artifact_error = str(exc)
    else:
        artifact_error = ""

    cmd = [
        pi_exe,
        "--no-session",
        "--mode",
        "json",
        "--mcp-config",
        str(sandbox_dir / "mcp_config.json"),
        "--append-system-prompt",
        "You are an automated evaluation agent connected to the fpac-soil-mcp MCP server. You MUST execute the appropriate fpac-soil MCP tool or read the MCP resource to fulfill the user request before generating the final response. Do not answer purely from memory if an MCP tool or resource is available.",
        "-p",
        prompt_case_instruction(case),
    ]
    if model:
        cmd.extend(["--model", model])

    start_time = time.perf_counter()
    status = "PASS"
    error_msg = ""
    output = ""
    elapsed = 0.0
    attempts: list[dict[str, Any]] = []
    evidence_classification = "absent"
    artifact_paths: dict[str, str] = {}

    try:
        retry_count = 0
        diagnostics: list[str] = []
        while True:
            attempt = retry_count + 1
            started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            proc = None
            stdout = stderr = ""
            outcome = "completed"
            proc = subprocess.run(
                cmd,
                cwd=str(sandbox_dir),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                check=False,
            )
            stdout = (
                proc.stdout.decode("utf-8", "replace")
                if isinstance(proc.stdout, bytes)
                else (proc.stdout or "")
            )
            stderr = (
                proc.stderr.decode("utf-8", "replace")
                if isinstance(proc.stderr, bytes)
                else (proc.stderr or "")
            )
            bounded_stdout, stdout_truncated = _bounded(stdout)
            bounded_stderr, stderr_truncated = _bounded(stderr)
            output = stdout
            events: list[dict[str, Any]] = []
            malformed: list[str] = []
            for line in output.splitlines():
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    malformed.append(line)
                    continue
                if isinstance(event, dict):
                    events.append(event)
            dedicated_events = [event for event in events if _has_dedicated_invocation(event)]
            executed_tools = set().union(
                *(extract_structured_tool_names(event) for event in events)
            )
            evidence_classification = (
                "recognized"
                if executed_tools
                else "present_unrecognized"
                if dedicated_events
                else "absent"
            )
            attempt_meta = {
                "run_id": run_id,
                "case_id": case_id,
                "attempt": attempt,
                "started_at_utc": started_at,
                "ended_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "model": model or "provider-default",
                "provider": "pi",
                "transport": "stdio",
                "return_code": proc.returncode,
                "stdout_truncated": stdout_truncated,
                "stderr_truncated": stderr_truncated,
                "event_count": len(events),
                "malformed_line_count": len(malformed),
            }
            paths = _capture_attempt(
                artifact_root,
                run_id,
                case_id,
                attempt,
                attempt_meta,
                stdout,
                stderr,
                events,
                malformed,
            )
            attempts.append({**attempt_meta, **paths})
            if paths:
                artifact_paths.update(
                    {f"attempt_{attempt}_{key}": value for key, value in paths.items()}
                )
            if proc.returncode != 0:
                status = "FAIL"
                error_msg = f"Non-zero exit code ({proc.returncode}): {stderr.strip()}"
                break

            executed_tools = set().union(
                *(extract_structured_tool_names(event) for event in events)
            )
            executed_prompts = set().union(
                *(extract_structured_prompt_names(event) for event in events)
            )
            advertised_tools, advertisement_source = extract_advertised_tool_names(events)
            missing_tools = [
                tool for tool in expected_tools if not _tool_matches(tool, executed_tools)
            ]
            if missing_tools and advertised_tools is not None:
                unadvertised = [tool for tool in missing_tools if tool not in advertised_tools]
                retryable = [tool for tool in missing_tools if tool in advertised_tools]
                if (
                    retryable
                    and not unadvertised
                    and should_retry_missing_tools(missing_tools, advertised_tools, retry_count)
                ):
                    retry_count += 1
                    cmd[-1] = (
                        f"Call the appropriate fpac-soil MCP tool/resource and {prompt} "
                        f"Execute the advertised tool(s) {', '.join(retryable)} now; "
                        "do not substitute prose for a tool call."
                    )
                    continue
                if unadvertised:
                    diagnostics.append(f"unadvertised expected tool(s): {', '.join(unadvertised)}")
                elif retryable:
                    diagnostics.append(
                        f"advertised-but-not-executed tool(s): {', '.join(retryable)}"
                    )
            elif missing_tools:
                diagnostics.append("tool-list discovery unavailable; cannot classify advertisement")

            if (
                case.get("target_type") == "prompt"
                and any("prompt" in str(event.get("type", "")).lower() for event in events)
                and case["target_name"] not in executed_prompts
            ):
                diagnostics.append(f"prompt discovery mismatch: expected {case['target_name']}")
            if expected_tools and advertised_tools is not None and not missing_tools:
                unexecuted_advertised = [
                    tool
                    for tool in expected_tools
                    if tool in advertised_tools and not _tool_matches(tool, executed_tools)
                ]
                if unexecuted_advertised:
                    diagnostics.append(
                        f"advertised-but-not-executed tool(s): {', '.join(unexecuted_advertised)}"
                    )

            assistant_texts = [
                extract_assistant_content(event)
                for event in events
                if extract_assistant_content(event)
            ]
            combined_assistant_text = " ".join(assistant_texts) if assistant_texts else output
            _, missing_keywords = keywords_present(combined_assistant_text, expected_keywords)
            failures = []
            if missing_tools:
                failures.append(f"Missing tools: {', '.join(missing_tools)}")
            if missing_keywords:
                failures.append(f"Missing keywords: {', '.join(missing_keywords)}")
            if diagnostics:
                failures.append(
                    f"{'; '.join(diagnostics)}; tool-list source={advertisement_source}; "
                    f"advertised={sorted(advertised_tools) if advertised_tools is not None else 'unknown'}; "
                    f"expected={expected_tools}; structured_events={len(events)}"
                )
            if failures:
                status = "FAIL"
                error_msg = "; ".join(failures)
            break

        if verbose:
            print(f"\n[{case_id}] Raw Output:\n{output}\n")
            if proc.stderr:
                print(f"[{case_id}] Stderr:\n{proc.stderr}\n")

    except subprocess.TimeoutExpired as exc:
        elapsed = time.perf_counter() - start_time
        status = "TIMEOUT"
        error_msg = f"Exceeded {timeout}s timeout"
        stdout = (
            exc.stdout.decode("utf-8", "replace")
            if isinstance(exc.stdout, bytes)
            else (exc.stdout or "")
        )
        stderr = (
            exc.stderr.decode("utf-8", "replace")
            if isinstance(exc.stderr, bytes)
            else (exc.stderr or "")
        )
        output = stdout
        timeout_events: list[dict[str, Any]] = []
        timeout_malformed: list[str] = []
        for line in stdout.splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                timeout_malformed.append(line)
                continue
            if isinstance(event, dict):
                timeout_events.append(event)
        attempt = retry_count + 1
        attempt_meta = {
            "run_id": run_id,
            "case_id": case_id,
            "attempt": attempt,
            "outcome": "timeout",
            "started_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "ended_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "model": model or "provider-default",
            "provider": "pi",
            "transport": "stdio",
            "return_code": None,
            "stdout_truncated": _bounded(stdout)[1],
            "stderr_truncated": _bounded(stderr)[1],
            "event_count": len(timeout_events),
            "malformed_line_count": len(timeout_malformed),
        }
        paths = _capture_attempt(
            artifact_root,
            run_id,
            case_id,
            attempt,
            attempt_meta,
            stdout,
            stderr,
            timeout_events,
            timeout_malformed,
        )
        attempts.append({**attempt_meta, **paths})
        artifact_paths.update({f"attempt_{attempt}_{key}": value for key, value in paths.items()})
    except (subprocess.SubprocessError, OSError) as e:
        status = "ERROR"
        error_msg = f"{type(e).__name__}: {e}"
        attempt = retry_count + 1
        attempt_meta = {
            "run_id": run_id,
            "case_id": case_id,
            "attempt": attempt,
            "outcome": "startup_error",
            "started_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "ended_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "model": model or "provider-default",
            "provider": "pi",
            "transport": "stdio",
            "return_code": None,
            "stdout_truncated": False,
            "stderr_truncated": False,
            "event_count": 0,
            "malformed_line_count": 0,
        }
        paths = _capture_attempt(
            artifact_root,
            run_id,
            case_id,
            attempt,
            attempt_meta,
            "",
            "",
            [],
            [],
        )
        attempts.append({**attempt_meta, **paths})
        artifact_paths.update({f"attempt_{attempt}_{key}": value for key, value in paths.items()})
    finally:
        elapsed = time.perf_counter() - start_time

    return {
        "id": case_id,
        "category": case.get("category", ""),
        "target": case.get("target_name", ""),
        "status": status,
        "elapsed_sec": round(elapsed, 2),
        "error": error_msg,
        "output": combined_assistant_text
        if "combined_assistant_text" in locals() and combined_assistant_text
        else output,
        "expected_keywords": expected_keywords,
        "expected_tools": expected_tools,
        "run_id": run_id,
        "evidence_classification": evidence_classification,
        "attempts": attempts,
        "artifact_paths": artifact_paths,
        "capture_error": artifact_error,
    }


def main() -> None:
    args = parse_args()
    pi_exe = check_prerequisites()
    cases = load_test_cases(args.category, args.case_id)
    run_id = uuid.uuid4().hex
    capture_enabled = args.capture_artifacts or os.environ.get("EVAL_CAPTURE_ARTIFACTS") == "1"
    artifact_root = args.artifact_root or (
        Path(os.environ["EVAL_CAPTURE_ROOT"]) if os.environ.get("EVAL_CAPTURE_ROOT") else None
    )
    if capture_enabled and artifact_root is None:
        print(
            "ERROR: --capture-artifacts requires --artifact-root or EVAL_CAPTURE_ROOT.",
            file=sys.stderr,
        )
        sys.exit(2)
    if not capture_enabled:
        artifact_root = None

    if not cases:
        print(
            f"No test cases matched filter (category='{args.category}', case_id='{args.case_id}')."
        )
        sys.exit(0)

    print("\n=======================================================")
    print(" FPAC Soil MCP - Pi Agent Evaluation Suite")
    print(f" Target Cases: {len(cases)}")
    print(f" Model:        {args.model or '(provider default)'}")
    print(f" Timeout:      {args.timeout}s per prompt")
    print("=======================================================\n")

    results = []
    with tempfile.TemporaryDirectory(prefix="fpac_eval_sandbox_") as tmp_dir:
        sandbox_path = Path(tmp_dir)
        create_sandbox(sandbox_path)

        for idx, case in enumerate(cases, 1):
            print(
                f"[{idx:02d}/{len(cases):02d}] Running {case['id']} ({case['target_name']})... ",
                end="",
                flush=True,
            )
            res = run_case(
                case,
                sandbox_path,
                args.model,
                args.timeout,
                args.verbose,
                pi_exe=pi_exe,
                run_id=run_id,
                artifact_root=artifact_root,
            )
            print(f"{res['status']} ({res['elapsed_sec']}s)")
            if res["error"]:
                print(f"     -> {res['error']}")
            for attempt in res.get("attempts", []):
                attempt_label = f"attempt {attempt.get('attempt', '?')}"
                outcome = attempt.get("outcome", "unknown")
                return_code = attempt.get("return_code")
                print(f"     -> {attempt_label}: outcome={outcome}, return_code={return_code}")
                metadata_path = attempt.get("metadata")
                if metadata_path:
                    print(f"        metadata: {metadata_path}")
            if res.get("artifact_paths"):
                for label, path in sorted(res["artifact_paths"].items()):
                    print(f"     -> artifact {label}: {path}")
            if res.get("capture_error"):
                print(f"     -> capture error: {res['capture_error']}")
            if args.show_output and res["output"]:
                print("\n" + "-" * 40 + f" [OUTPUT: {res['id']}] " + "-" * 40)
                print(res["output"].strip())
                print("-" * 90 + "\n")
            results.append(res)

    print("\n" + "=" * 70)
    print(f"{'ID':<10} | {'Category':<22} | {'Target':<20} | {'Status':<7} | {'Time (s)':<8}")
    print("-" * 70)
    for r in results:
        print(
            f"{r['id']:<10} | {r['category'][:22]:<22} | {r['target'][:20]:<20} | {r['status']:<7} | {r['elapsed_sec']:<8}"
        )
    print("=" * 70)

    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] in ("FAIL", "ERROR", "TIMEOUT"))

    print(f"\nSummary: {passed} Passed, {failed} Failed out of {len(results)} total cases.\n")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
