import json
from pathlib import Path

import pytest
from criterion2_benchmark import (
    SCHEMA_VERSION,
    _memory_method,
    _percentile,
    load_manifest,
    run_benchmark,
)

MANIFEST = Path("tests/fixtures/criterion2_benchmark.v1.json")


def _args(**overrides):
    values = {
        "fixture_manifest": str(MANIFEST),
        "runs": 1,
        "max_workers": 1,
        "transport": "dry-run",
        "mcp_url": None,
        "timeout": 180.0,
        "retries": 0,
        "model": None,
        "output": None,
    }
    values.update(overrides)
    return type("Args", (), values)()


def test_canonical_manifest_has_required_fixture_records():
    manifest = load_manifest(MANIFEST)

    assert manifest["version"] == "criterion2-benchmark-fixtures.v1"
    assert [case["id"] for case in manifest["fixtures"]] == [
        "CORR-MULTI-2COUNTY",
        "CORR-MULTI-3COUNTY",
        "POLY-PARTIAL",
        "URBAN-PARTIAL",
    ]
    for case in manifest["fixtures"]:
        assert case["geometry"]
        assert case["county_count"] == len(case["county_fips"])
        assert case["expected_coverage_class"]
        assert case["expected_status"]


def test_dry_run_emits_full_schema_and_manifest_counties():
    result = run_benchmark(_args())

    assert result["schema_version"] == SCHEMA_VERSION
    assert result["execution_mode"] == "manifest_dry_run"
    assert len(result["cases"]) == 4
    assert result["environment"]["memory_method"]
    assert result["environment"]["max_workers"] == 1
    assert all(case["response_status"] == "not_executed" for case in result["cases"])
    assert all(case["latency_ms"] is None for case in result["cases"])
    assert all(case["failure"] is None for case in result["cases"])
    assert all(case["retry_count"] is None for case in result["cases"])

    manifest_by_id = {case["id"]: case for case in load_manifest(MANIFEST)["fixtures"]}
    for case in result["cases"]:
        assert case["input"]["arguments"] == manifest_by_id[case["case_id"]]["arguments"]

    for aggregate in result["aggregates"]:
        assert aggregate["manifest_version"] == result["manifest"]["version"]
        assert "county_fips" in aggregate
        assert "county_identifiers" in aggregate
        assert "county_count" in aggregate
        assert "p50_latency_ms" in aggregate
        assert "p95_latency_ms" in aggregate
        assert "p99_latency_ms" in aggregate
        assert "failure_count" in aggregate
        assert "retry_count" in aggregate

    all_cases = result["aggregates"][-1]
    assert all_cases["failure_count"] is None
    assert all_cases["retry_count"] is None
    assert all_cases["county_count"] == 6
    assert {"19015", "19169", "17037", "17043", "17089"} <= set(all_cases["county_identifiers"])
    assert {case["case_id"] for case in result["cases"]} == {
        "CORR-MULTI-2COUNTY",
        "CORR-MULTI-3COUNTY",
        "POLY-PARTIAL",
        "URBAN-PARTIAL",
    }
    json.dumps(result)


def test_repeat_mode_preserves_case_and_county_aggregate_metadata():
    result = run_benchmark(_args(runs=2, max_workers=2))

    assert result["run_settings"]["runs_per_case"] == 2
    assert len(result["cases"]) == 8
    assert result["environment"]["max_workers"] == 2
    for aggregate in result["aggregates"]:
        assert aggregate["manifest_version"] == result["manifest"]["version"]
        assert aggregate["sample_count"] == (8 if aggregate.get("scope") == "all_cases" else 2)
        if aggregate.get("scope") == "all_cases":
            assert aggregate["county_count"] == 6


@pytest.mark.parametrize(
    ("percentile", "expected"),
    [(50, 2.0), (95, 2.9), (99, 2.98)],
)
def test_percentiles_interpolate(percentile, expected):
    assert _percentile([1.0, 3.0], percentile) == pytest.approx(expected)


def test_memory_method_discloses_when_concurrency_prevents_measurement():
    assert _memory_method("http", 1) == "tracemalloc_peak_python_bytes"
    assert _memory_method("http", 2) == ("not_measured_concurrent_tracemalloc_is_process_global")
    assert _memory_method("dry-run", 2) == "not_measured_dry_run"
