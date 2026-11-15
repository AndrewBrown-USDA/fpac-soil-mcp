"""Opt-in local stand-in for the dev-app Site Assessment trial (headless).

Starts its own fpac-soil-mcp server over Streamable HTTP on a free port (or uses
``--mcp-url``), then drives the agent app's real MCP client class, criteria-resource
validation, interview tools, and confirmed-summary gate with a scripted (stub) model.
It does not call any LLM, Databricks workspace, or remote app. USDA SDA is contacted
by the local MCP server for the soil screening and LESA success path.

Run from the repository root with ``make trial-local``. See ``planning/STATE_52.md``.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from types import SimpleNamespace
from typing import Any

# Dummy credentials: the app's McpServer builds a WorkspaceClient; the local server
# ignores the bearer header. No workspace is contacted.
os.environ.setdefault("DATABRICKS_HOST", "https://example.cloud.databricks.com")
os.environ.setdefault("DATABRICKS_TOKEN", "dummy")
os.environ.setdefault("DATABRICKS_CONFIG_FILE", "/dev/null")
os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")

APP_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = APP_DIR.parents[1]
sys.path.insert(0, str(APP_DIR))

from agent_server.agent import (  # noqa: E402
    SITE_ASSESSMENT_CRITERIA_URI,
    _site_assessment_criteria_context,
    _site_assessment_payload_from_context,
)
from agent_server.site_assessment_gate import bind_site_assessment_gate  # noqa: E402
from agent_server.site_assessment_tools import create_site_assessment_tools  # noqa: E402
from agents.tool import ToolContext  # noqa: E402
from databricks_openai.agents import McpServer  # noqa: E402

# Synthetic AOI (about 40 acres in central Iowa). Not a real project location.
AOI = {
    "type": "Polygon",
    "coordinates": [
        [
            [-93.6300, 42.0300],
            [-93.6240, 42.0300],
            [-93.6240, 42.0345],
            [-93.6300, 42.0345],
            [-93.6300, 42.0300],
        ]
    ],
}
WANTED_TOOLS = {
    "analyze_farmland_by_polygon",
    "calculate_preliminary_lesa",
}


def _offline_workspace_client() -> Any:
    """Stub with a dummy bearer token (ignored by the local server); a real WorkspaceClient would contact a Databricks host."""
    return SimpleNamespace(
        config=SimpleNamespace(
            authenticate=lambda: {"Authorization": "Bearer local-trial"},
            host="http://127.0.0.1",
            token=None,
            auth_type="none",
        ),
        current_user=SimpleNamespace(me=lambda: None),
    )


VERIFIED = {
    "is_verified": True,
    "source_provenance": ["user statement (synthetic trial)"],
    "justification": "Synthetic trial input.",
}


class Trial:
    def __init__(self) -> None:
        self.failures: list[str] = []
        self.mcp_calls: list[str] = []

    def check(self, label: str, ok: bool, detail: str = "") -> None:
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}" + (f" - {detail}" if detail else ""))
        if not ok:
            self.failures.append(label)


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def start_server(port: int) -> subprocess.Popen:
    env = {**os.environ, "MCP_TRANSPORT": "http", "MCP_HOST": "127.0.0.1", "MCP_PORT": str(port)}
    proc = subprocess.Popen(
        ["uv", "run", "fpac-soil-mcp"],
        cwd=REPO_ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    deadline = time.time() + 90
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError("Local MCP server exited during startup.")
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2) as r:
                if r.status == 200:
                    return proc
        except OSError:
            time.sleep(0.5)
    proc.terminate()
    raise RuntimeError("Local MCP server did not become healthy.")


async def invoke_tool(tool: Any, arguments: dict[str, Any]) -> str:
    serialized = json.dumps(arguments)
    ctx = ToolContext({}, tool_name=tool.name, tool_call_id="trial", tool_arguments=serialized)
    return await tool.on_invoke_tool(ctx, serialized)


def result_text(result: Any) -> str:
    return "".join(getattr(c, "text", "") for c in result.content)


def confirmed_history(answers: list[dict[str, Any]], confirmed: bool = True) -> list[dict]:
    summary = {
        "type": "site_assessment_confirmed_summary",
        "confirmed": confirmed,
        "answers": answers,
    }
    return [{"role": "user", "content": json.dumps(summary)}]


def ui_answers(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Shape records as the question cards do: the answer field holds the band id."""
    return [
        {**r, "answer": r["selected_band"]["id"] if r["answer_state"] == "answered" else None}
        for r in records
    ]


def lesa_args(facts: dict[str, Any], **extra: Any) -> dict[str, Any]:
    inputs: dict[str, Any] = {"criteria_facts": facts, **extra}
    return {
        "project_name": "Synthetic local trial",
        "geometry": AOI,
        "project_type": "site",
        "site_assessment_inputs": inputs,
    }


async def run(mcp_url: str, trial: Trial) -> None:
    server = McpServer(
        url=mcp_url, name="fpac-local", workspace_client=_offline_workspace_client(), timeout=120.0
    )
    original_call = server.call_tool

    async def logged_call(name: str, arguments: Any, **kwargs: Any) -> Any:
        trial.mcp_calls.append(name)
        return await original_call(name, arguments, **kwargs)

    server.call_tool = logged_call  # type: ignore[method-assign]

    async with server:
        print("1. MCP surface")
        tools = {t.name for t in await server.list_tools()}
        trial.check("/mcp lists screening and LESA tools", WANTED_TOOLS <= tools)

        resource = await server.read_resource(SITE_ASSESSMENT_CRITERIA_URI)
        context = _site_assessment_criteria_context(resource)
        payload = _site_assessment_payload_from_context(context)
        trial.check("criteria resource validates (12 criteria)", bool(payload))
        assert payload is not None
        question_tool, answer_tool = create_site_assessment_tools(payload)

        print("2. Soil-first screening (live SDA through the local server)")
        screen = await server.call_tool("analyze_farmland_by_polygon", {"geojson": AOI})
        trial.check("screening call succeeded", not screen.isError, result_text(screen)[:120])

        print("3. Interview: question from tool, answers with comment and provenance")
        question = json.loads(await invoke_tool(question_tool, {"criterion_number": 1}))
        registry = {c["criterion_number"]: c for c in payload["criteria"]}
        trial.check(
            "question has registry choices, citation, and points",
            question["choices"] == registry[1]["bands"]
            and bool(question["citation"])
            and question["max_points"] == registry[1]["max_points"],
        )
        records = [
            json.loads(
                await invoke_tool(
                    answer_tool,
                    {
                        "criterion_number": 1,
                        "answer_state": "answered",
                        "answer": 22,
                        "evidence": "user estimate",
                        "comment": "about 22 percent",
                        "provenance": "user",
                    },
                )
            ),
            json.loads(
                await invoke_tool(
                    answer_tool,
                    {
                        "criterion_number": 2,
                        "answer_state": "skipped",
                        "answer": None,
                        "evidence": "",
                        "comment": "user skipped",
                        "provenance": "user",
                    },
                )
            ),
            json.loads(
                await invoke_tool(
                    answer_tool,
                    {
                        "criterion_number": 3,
                        "answer_state": "unknown",
                        "answer": None,
                        "evidence": "",
                        "comment": "no data",
                        "provenance": "user",
                    },
                )
            ),
            json.loads(
                await invoke_tool(
                    answer_tool,
                    {
                        "criterion_number": 4,
                        "answer_state": "answered",
                        "answer": "protected",
                        "evidence": "easement letter",
                        "comment": "",
                        "provenance": "agent",
                    },
                )
            ),
        ]
        trial.check(
            "records keep type, comment, provenance, derived points",
            all(r["type"] == "site_assessment_answer" for r in records)
            and records[0]["comment"] == "about 22 percent"
            and records[0]["points"] == 1
            and records[3]["provenance"] == "agent"
            and records[3]["points"] == 20,
        )
        trial.check(
            "numeric percentage answer maps to band",
            records[0]["selected_band"]["id"] == "range_20_90_1",
        )
        summary_answers = ui_answers(records)
        facts = {
            "1": {**VERIFIED, "percentage": 22},
            "2": {"value": "skipped"},
            "3": {"value": "unknown"},
            "4": {**VERIFIED, "category": "protected"},
        }

        def gated(history: list[dict]) -> McpServer:
            return bind_site_assessment_gate(server, history, payload)

        print("4. Negative cases (refused before any MCP call)")
        negatives = {
            "no confirmation": (
                confirmed_history(summary_answers, confirmed=False),
                lesa_args(facts),
            ),
            "no summary in history": ([], lesa_args(facts)),
            "mismatched answers": (
                confirmed_history(summary_answers),
                lesa_args({**facts, "1": {**VERIFIED, "percentage": 60}}),
            ),
            "missing answer set member": (
                confirmed_history(summary_answers),
                lesa_args({k: v for k, v in facts.items() if k != "4"}),
            ),
            "criterion 7 fact plus farm acres": (
                confirmed_history(summary_answers),
                lesa_args(
                    {"7": {"percentage": 50}},
                    project_farm_acres=100,
                    county_average_farm_acres=200,
                ),
            ),
        }
        for label, (history, args) in negatives.items():
            # Bind on a fresh wrapper chain each time: restore the logging call first.
            server.call_tool = logged_call  # type: ignore[method-assign]
            before = len(trial.mcp_calls)
            refused = await gated(history).call_tool("calculate_preliminary_lesa", args)
            trial.check(
                f"refused: {label}",
                bool(refused.isError) and len(trial.mcp_calls) == before,
                result_text(refused)[:90],
            )

        print("5. Matching confirmation reaches LESA")
        server.call_tool = logged_call  # type: ignore[method-assign]
        before = len(trial.mcp_calls)
        ok = await gated(confirmed_history(summary_answers)).call_tool(
            "calculate_preliminary_lesa", lesa_args(facts)
        )
        text = result_text(ok)
        trial.check("LESA call reached MCP", len(trial.mcp_calls) == before + 1)
        trial.check("LESA call succeeded", not ok.isError, text[:160])
        data = json.loads(text) if not ok.isError else {}
        criteria = {
            c["criterion_number"]: c for c in data.get("site_assessment", {}).get("criteria", [])
        }
        provided = {n for n, c in criteria.items() if c.get("evidence_status") == "provided"}
        assumed = {
            n: c
            for n, c in criteria.items()
            if str(c.get("evidence_status", "")).startswith("assumed")
        }
        trial.check("answered criteria 1 and 4 scored as provided", provided == {1, 4})
        trial.check(
            "skipped, unknown, and unasked criteria are conservative maximums labeled assumed",
            set(assumed) == set(range(1, 13)) - {1, 4}
            and all(c["assumed_points"] == registry[n]["max_points"] for n, c in assumed.items()),
        )
        trial.check(
            "result undetermined: no total, threshold not evaluated, bound separate",
            data.get("total_lesa_score") is None
            and data.get("threshold_status") == "not_evaluated"
            and isinstance(data.get("conservative_total_lesa_upper_bound"), (int, float)),
        )
        trial.check(
            "preliminary notice present",
            "PRELIMINARY SCREENING ONLY" in str(data.get("regulatory_notice", "")),
        )
        out = (
            Path(os.environ.get("TRIAL_LOCAL_OUT", ""))
            if os.environ.get("TRIAL_LOCAL_OUT")
            else None
        )
        if out:
            out.write_text(text, encoding="utf-8")

    print("6. MCP call log:", trial.mcp_calls)
    trial.check(
        "call log is screening then LESA only",
        trial.mcp_calls == ["analyze_farmland_by_polygon", "calculate_preliminary_lesa"],
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mcp-url", help="Use an already running server's /mcp URL.")
    args = parser.parse_args()
    trial = Trial()
    proc = None
    try:
        url = args.mcp_url
        if not url:
            port = free_port()
            proc = start_server(port)
            url = f"http://127.0.0.1:{port}/mcp"
        print(f"MCP server: {url}")
        asyncio.run(run(url, trial))
    finally:
        if proc is not None:
            proc.terminate()
            proc.wait(timeout=15)
    print("FAILED: " + ", ".join(trial.failures) if trial.failures else "ALL CHECKS PASSED")
    return 1 if trial.failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
