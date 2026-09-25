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
        default=os.environ.get("AGENT_EVAL_MODEL"),
        help="Model string/pattern to pass to pi (overrides AGENT_EVAL_MODEL env var).",
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

    cmd = [
        pi_exe,
        "--no-session",
        "--mcp-config",
        str(sandbox_dir / "mcp_config.json"),
        "--append-system-prompt",
        "You are an automated evaluation agent connected to the fpac-soil-mcp MCP server. Always inspect and call the available fpac-soil MCP tools, MCP resources, and MCP prompts immediately to answer the user query. Do not ask for confirmation, do not request external files, and do not look for local files when an MCP tool or resource is available.",
        "-p",
        prompt,
    ]
    if model:
        cmd.extend(["--model", model])

    start_time = time.perf_counter()
    status = "PASS"
    error_msg = ""
    output = ""

    try:
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
        elapsed = time.perf_counter() - start_time
        output = proc.stdout or ""

        if proc.returncode != 0:
            status = "FAIL"
            error_msg = f"Non-zero exit code ({proc.returncode}): {(proc.stderr or '').strip()}"
        else:
            norm_output = normalize_text(output).lower()
            missing_keywords = [
                kw for kw in expected_keywords if normalize_text(kw).lower() not in norm_output
            ]
            if missing_keywords:
                status = "WARN"
                error_msg = f"Missing keywords: {', '.join(missing_keywords)}"

        if verbose:
            print(f"\n[{case_id}] Output:\n{output}\n")
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
        "output": output,
        "expected_keywords": expected_keywords,
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
    failed = sum(1 for r in results if r["status"] in ("FAIL", "ERROR", "TIMEOUT"))

    print(
        f"\nSummary: {passed} Passed, {warned} Warnings, {failed} Failed out of {len(results)} total cases.\n"
    )

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
