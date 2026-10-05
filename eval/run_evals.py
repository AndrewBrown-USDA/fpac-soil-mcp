#!/usr/bin/env python3
"""Release-time agentic evaluation benchmark runner using the pi coding agent CLI.

Runs prompt test cases against the fpac-soil-mcp server in an isolated sandbox,
verifies tool call execution and keyword presence, and displays a summary report.

Usage:
    python eval/run_evals.py [--category CATEGORY] [--case-id CASE_ID] [--model MODEL] [--timeout TIMEOUT] [--verbose]
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
import unicodedata
from pathlib import Path
from typing import Any

# Ensure UTF-8 output on Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_PATH = REPO_ROOT / "eval" / "prompt_test_cases.json"


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


def normalize_text(text: str) -> str:
    """Normalize text by standardizing unicode characters (e.g. non-breaking hyphens, special spaces)."""
    # NFKD normalizes compatibility characters
    normalized = unicodedata.normalize("NFKD", text)
    # Replace non-breaking hyphen (U+2011), figure dash (U+2012), en dash (U+2013), em dash (U+2014) with ASCII hyphen
    normalized = re.sub(r"[\u2010\u2011\u2012\u2013\u2014\u2015\u2212]", "-", normalized)
    # Replace non-breaking space (U+00A0) and other unicode whitespace with standard space
    normalized = re.sub(r"[\u00a0\u2000-\u200b\u202f\u205f\u3000]", " ", normalized)
    return normalized


def extract_structured_tool_names(event: dict[str, Any]) -> set[str]:
    """Extract tool names specifically from dedicated name/function fields in an event."""
    names: set[str] = set()
    event_type = str(event.get("type", "")).lower()

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
            event.get("result", {}).get("tools")
            if isinstance(event.get("result"), dict)
            else None,
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


def _tool_matches(expected: str, executed: set[str]) -> bool:
    return expected in executed or any(
        name.endswith((f"_{expected}", f":{expected}")) for name in executed
    )


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
) -> dict[str, Any]:
    case_id = case["id"]
    prompt = case["user_prompt"]
    expected_keywords = case.get("expected_keywords", [])
    expected_tools = case.get("expected_tools", [])

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
        f"Call the appropriate fpac-soil MCP tool/resource and {prompt}",
    ]
    if model:
        cmd.extend(["--model", model])

    start_time = time.perf_counter()
    status = "PASS"
    error_msg = ""
    output = ""

    try:
        retry_count = 0
        diagnostics: list[str] = []
        while True:
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
            output = proc.stdout or ""
            events: list[dict[str, Any]] = []
            for line in output.splitlines():
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(event, dict):
                    events.append(event)
            if proc.returncode != 0:
                status = "FAIL"
                error_msg = f"Non-zero exit code ({proc.returncode}): {(proc.stderr or '').strip()}"
                break

            executed_tools = set().union(
                *(extract_structured_tool_names(event) for event in events)
            )
            advertised_tools, advertisement_source = extract_advertised_tool_names(events)
            missing_tools = [
                tool for tool in expected_tools if not _tool_matches(tool, executed_tools)
            ]
            if missing_tools and advertised_tools is not None:
                unadvertised = [tool for tool in missing_tools if tool not in advertised_tools]
                retryable = [tool for tool in missing_tools if tool in advertised_tools]
                if retryable and not unadvertised and should_retry_missing_tools(
                    missing_tools, advertised_tools, retry_count
                ):
                    retry_count += 1
                    cmd[-1] = (
                        f"Call the appropriate fpac-soil MCP tool/resource and {prompt} "
                        f"Execute the advertised tool(s) {', '.join(retryable)} now; "
                        "do not substitute prose for a tool call."
                    )
                    continue
                if unadvertised:
                    diagnostics.append(
                        f"unadvertised expected tool(s): {', '.join(unadvertised)}"
                    )
            elif missing_tools:
                diagnostics.append("configuration diagnostic: MCP tool list unavailable")

            assistant_texts = [
                extract_assistant_content(event) for event in events if extract_assistant_content(event)
            ]
            combined_assistant_text = " ".join(assistant_texts) if assistant_texts else output
            norm_content = normalize_text(combined_assistant_text).lower()
            missing_keywords = [
                kw for kw in expected_keywords if normalize_text(kw).lower() not in norm_content
            ]
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

    except subprocess.TimeoutExpired:
        elapsed = time.perf_counter() - start_time
        status = "TIMEOUT"
        error_msg = f"Exceeded {timeout}s timeout"
    except (subprocess.SubprocessError, OSError) as e:
        elapsed = time.perf_counter() - start_time
        status = "ERROR"
        error_msg = f"{type(e).__name__}: {e}"

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
    }


def main() -> None:
    args = parse_args()
    pi_exe = check_prerequisites()
    cases = load_test_cases(args.category, args.case_id)

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
                case, sandbox_path, args.model, args.timeout, args.verbose, pi_exe=pi_exe
            )
            print(f"{res['status']} ({res['elapsed_sec']}s)")
            if res["error"]:
                print(f"     -> {res['error']}")
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
    warned = sum(1 for r in results if r["status"] == "WARN")
    failed = sum(1 for r in results if r["status"] in ("FAIL", "ERROR", "TIMEOUT", "WARN"))

    print(
        f"\nSummary: {passed} Passed, {warned} Warnings, {failed} Failed out of {len(results)} total cases.\n"
    )

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
