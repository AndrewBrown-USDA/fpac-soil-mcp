"""Reproducible Criterion 2 MCP benchmark runner.

The default transport is a manifest-only dry run. Use ``--transport http`` with
``--mcp-url`` to invoke a deployed Streamable HTTP MCP server.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import platform
import subprocess
import sys
import time
import tracemalloc
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "criterion2-benchmark.v1"
DEFAULT_MANIFEST = Path("tests/fixtures/criterion2_benchmark.v1.json")


def _git_commit() -> str | None:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=2,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None


def load_manifest(path: Path) -> dict[str, Any]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(manifest.get("version"), str) or not manifest["version"]:
        raise ValueError("fixture manifest must define a non-empty version")
    fixtures = manifest.get("fixtures")
    if not isinstance(fixtures, list) or not fixtures:
        raise ValueError("fixture manifest must contain a non-empty fixtures list")
    seen: set[str] = set()
    for fixture in fixtures:
        required = {
            "id",
            "geometry",
            "county_fips",
            "county_count",
            "expected_coverage_class",
            "expected_status",
            "tool",
            "arguments",
        }
        missing = required.difference(fixture)
        if missing:
            raise ValueError(f"fixture missing required fields: {sorted(missing)}")
        if fixture["id"] in seen:
            raise ValueError(f"duplicate fixture id: {fixture['id']}")
        seen.add(fixture["id"])
        if fixture["county_count"] != len(fixture["county_fips"]):
            raise ValueError(f"{fixture['id']}: county_count does not match county_fips")
    return manifest


def _percentile(samples: list[float], percentile: int) -> float | None:
    if not samples:
        return None
    ordered = sorted(samples)
    if len(ordered) == 1:
        return round(ordered[0], 3)
    position = (len(ordered) - 1) * percentile / 100
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return round(ordered[lower] + (ordered[upper] - ordered[lower]) * fraction, 3)


def _memory_method(transport: str, max_workers: int) -> str:
    if transport == "dry-run":
        return "not_measured_dry_run"
    if max_workers > 1:
        return "not_measured_concurrent_tracemalloc_is_process_global"
    return "tracemalloc_peak_python_bytes"


def _summary(case_runs: list[dict[str, Any]], manifest_version: str) -> dict[str, Any]:
    observed = [row for row in case_runs if row["latency_ms"] is not None]
    latencies = [row["latency_ms"] for row in observed]
    county_fips = sorted({fips for row in case_runs for fips in row["county_fips"]})
    outcomes_measured = all(row["outcomes_measured"] for row in case_runs)
    return {
        "manifest_version": manifest_version,
        "case_ids": sorted({row["case_id"] for row in case_runs}),
        "county_fips": county_fips,
        "county_identifiers": county_fips,
        "county_count": len(county_fips),
        "sample_count": len(case_runs),
        "p50_latency_ms": _percentile(latencies, 50),
        "p95_latency_ms": _percentile(latencies, 95),
        "p99_latency_ms": _percentile(latencies, 99),
        "failure_count": (sum(row["failure"] for row in case_runs) if outcomes_measured else None),
        "retry_count": (
            sum(row["retry_count"] for row in case_runs) if outcomes_measured else None
        ),
        "tool_call_count": sum(row["tool_call_count"] for row in case_runs),
        "latency_method": ("wall_clock_mcp_call" if observed else "not_measured_manifest_dry_run"),
    }


async def _call_http(url: str, fixture: dict[str, Any], timeout: float) -> Any:
    from fastmcp import Client

    async with Client(url, timeout=timeout) as client:
        return await client.call_tool(fixture["tool"], fixture["arguments"])


def _result_text(result: Any) -> str:
    if hasattr(result, "model_dump"):
        return json.dumps(result.model_dump(mode="json"), default=str)
    if hasattr(result, "content"):
        return json.dumps(
            [
                item.model_dump(mode="json") if hasattr(item, "model_dump") else str(item)
                for item in result.content
            ],
            default=str,
        )
    return json.dumps(result, default=str)


async def _run_http_case(
    fixture: dict[str, Any],
    url: str,
    timeout: float,
    retries: int,
    measure_memory: bool,
) -> dict[str, Any]:
    started = time.perf_counter()
    retry_count = 0
    response_status = "error"
    response_size = 0
    error: str | None = None
    if measure_memory:
        tracemalloc.start()
    try:
        while True:
            try:
                result = await asyncio.wait_for(_call_http(url, fixture, timeout), timeout=timeout)
                text = _result_text(result)
                response_size = len(text.encode("utf-8"))
                response_status = "error" if getattr(result, "isError", False) else "ok"
                if response_status == "error":
                    error = "MCP tool returned an error result"
                break
            except Exception as exc:  # noqa: BLE001 - MCP client exceptions vary by transport.
                if retry_count >= retries:
                    error = f"{type(exc).__name__}: {exc}"
                    response_status = "timeout" if isinstance(exc, TimeoutError) else "error"
                    break
                retry_count += 1
    finally:
        if measure_memory:
            _, peak_memory = tracemalloc.get_traced_memory()
            tracemalloc.stop()
        else:
            peak_memory = None
    elapsed_ms = (time.perf_counter() - started) * 1000
    return {
        "latency_ms": round(elapsed_ms, 3),
        "response_status": response_status,
        "response_size_bytes": response_size,
        "tool_call_count": retry_count + 1,
        "retry_count": retry_count,
        "failure": response_status != "ok",
        "outcomes_measured": True,
        "error": error,
        "peak_memory_bytes": peak_memory,
    }


def run_benchmark(args: argparse.Namespace) -> dict[str, Any]:
    manifest_path = Path(args.fixture_manifest)
    manifest = load_manifest(manifest_path)
    if args.runs < 1:
        raise ValueError("--runs must be at least 1")
    if args.max_workers < 1:
        raise ValueError("--max-workers must be at least 1")
    if args.timeout <= 0 or args.retries < 0:
        raise ValueError("--timeout must be positive and --retries non-negative")
    if args.transport == "http" and not args.mcp_url:
        raise ValueError("--mcp-url is required with --transport http")

    cases = manifest["fixtures"]
    tasks: list[tuple[int, dict[str, Any]]] = [
        (run_number, fixture) for run_number in range(1, args.runs + 1) for fixture in cases
    ]

    def execute(task: tuple[int, dict[str, Any]]) -> dict[str, Any]:
        run_number, fixture = task
        if args.transport == "dry-run":
            measurements = {
                "latency_ms": None,
                "response_status": "not_executed",
                "response_size_bytes": None,
                "tool_call_count": 0,
                "retry_count": None,
                "failure": None,
                "outcomes_measured": False,
                "error": None,
                "peak_memory_bytes": None,
            }
        else:
            measurements = asyncio.run(
                _run_http_case(
                    fixture,
                    args.mcp_url,
                    args.timeout,
                    args.retries,
                    measure_memory=args.max_workers == 1,
                )
            )
        return {
            "case_id": fixture["id"],
            "run_number": run_number,
            "tool": fixture["tool"],
            "input": {
                "geometry": fixture["geometry"],
                "county_fips": fixture["county_fips"],
                "county_count": fixture["county_count"],
                "arguments": fixture["arguments"],
            },
            "county_fips": fixture["county_fips"],
            "county_count": fixture["county_count"],
            "expected_coverage_class": fixture["expected_coverage_class"],
            "expected_status": fixture["expected_status"],
            **measurements,
        }

    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=args.max_workers) as pool:
        case_runs = list(pool.map(execute, tasks))
    duration_ms = round((time.perf_counter() - started) * 1000, 3)
    aggregates = [
        {
            "case_id": fixture["id"],
            **_summary(
                [row for row in case_runs if row["case_id"] == fixture["id"]],
                manifest["version"],
            ),
        }
        for fixture in cases
    ]
    aggregates.append({"scope": "all_cases", **_summary(case_runs, manifest["version"])})

    result = {
        "schema_version": SCHEMA_VERSION,
        "run_id": datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ"),
        "execution_mode": "manifest_dry_run" if args.transport == "dry-run" else "mcp",
        "manifest": {"path": str(manifest_path), "version": manifest["version"]},
        "environment": {
            "commit": _git_commit(),
            "prompt_version": os.getenv("FPAC_PROMPT_VERSION", "unknown"),
            "case_version": manifest["version"],
            "model": args.model or os.getenv("MODEL", "not_applicable"),
            "transport": args.transport,
            "mcp_url": args.mcp_url if args.transport == "http" else None,
            "timeout_seconds": args.timeout,
            "max_retries": args.retries,
            "max_workers": args.max_workers,
            "memory_method": _memory_method(args.transport, args.max_workers),
            "python_version": platform.python_version(),
            "platform": platform.platform(),
        },
        "run_settings": {"runs_per_case": args.runs, "case_count": len(cases)},
        "duration_ms": duration_ms,
        "cases": case_runs,
        "aggregates": aggregates,
    }
    return result


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture-manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--max-workers", type=int, default=1)
    parser.add_argument("--transport", choices=("dry-run", "http"), default="dry-run")
    parser.add_argument("--mcp-url")
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--retries", type=int, default=0)
    parser.add_argument("--model")
    parser.add_argument("--output")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    result = run_benchmark(args)
    serialized = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        Path(args.output).write_text(serialized + "\n", encoding="utf-8")
    print(serialized)
    return 0


if __name__ == "__main__":
    sys.exit(main())
