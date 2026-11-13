"""Unit tests for eval/common/dataset.py."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from common.dataset import (
    DEFAULT_PATH,
    dataset_version,
    load_cases,
    to_mlflow_records,
    validate_cases,
)

BASE_ROW: dict[str, Any] = {
    "id": "POINT-01",
    "category": "Phase 1 - Point Screening",
    "target_type": "tool",
    "target_name": "get_farmland_classification_by_point",
    "user_prompt": "Classify farmland at 41.8781, -93.0977.",
    "expected_tools": ["get_farmland_classification_by_point"],
    "expected_keywords": ["farmland"],
}

V2_ROW: dict[str, Any] = {
    **BASE_ROW,
    "expected_tool_calls": [
        {
            "name": "get_farmland_classification_by_point",
            "arguments": {"latitude": 41.8781, "longitude": -93.0977},
        }
    ],
    "expected_facts": ["The map unit key is 123456."],
    "numeric_expectations": [
        {
            "tool": "get_farmland_classification_by_point",
            "path": "map_units[0].mukey",
            "value": 123456,
            "abs_tol": 0,
        }
    ],
    "guidelines": ["States that results are preliminary screening."],
    "force_tool_use": True,
    "live_data_sensitive": True,
    "verified_on": "2026-10-21",
}


def _row(**changes: Any) -> dict[str, Any]:
    row = copy.deepcopy(V2_ROW)
    for key, value in changes.items():
        if value is ...:
            row.pop(key, None)
        else:
            row[key] = value
    return row


def _write(tmp_path: Path, cases: list[dict[str, Any]], version: str = "2.0.0") -> Path:
    path = tmp_path / "cases.json"
    path.write_text(json.dumps({"version": version, "test_cases": cases}), encoding="utf-8")
    return path


def test_checked_in_dataset_validates() -> None:
    cases = load_cases()
    assert len(cases) == 38
    assert len({case["id"] for case in cases}) == 38
    assert dataset_version(DEFAULT_PATH).split(".")[0] in {"1", "2"}
    assert all(
        "silent_nccpi_fallback" not in case.get("prohibited_behaviors", []) for case in cases
    )
    by_id = {case["id"]: case for case in cases}
    for case_id in ("SA-MA-01", "SA-MA-03"):
        assert "expected_tool_calls" not in by_id[case_id], (
            f"{case_id} should not prescribe a retrieval path"
        )
    lesa_case = by_id["SA-MA-02"]
    assert "project Synthetic SA-MA-02" in lesa_case["user_prompt"]
    assert "project_type site" in lesa_case["user_prompt"]
    assert lesa_case["expected_tool_calls"][0]["arguments"]["project_name"] == "Synthetic SA-MA-02"
    assert lesa_case["expected_tool_calls"][0]["arguments"]["project_type"] == "site"
    adversarial_ids = [case["id"] for case in cases if case["id"].startswith("ADV-")]
    assert adversarial_ids == [
        "ADV-UNRELATED-01",
        "ADV-FORMS-01",
        "ADV-NONPRIME-01",
        "ADV-RELOCATE-01",
        "ADV-CORRIDOR-01",
        "ADV-URBAN-01",
        "ADV-CONDITIONAL-01",
        "ADV-MISSING-01",
        "ADV-OUTAGE-01",
        "ADV-PARTIAL-01",
        "ADV-GEOMETRY-01",
        "ADV-INJECTION-01",
        "ADV-PRIVACY-01",
        "ADV-PERFORMANCE-01",
    ]


def test_non_adversarial_keyword_cases_have_expected_facts() -> None:
    # MLflow records drop `expected_keywords`, so `correctness` must have facts to judge.
    missing = [
        case["id"]
        for case in load_cases()
        if not case["id"].startswith("ADV-")
        and case["expected_keywords"]
        and not case.get("expected_facts")
    ]
    assert missing == []


def test_v1_row_and_full_v2_row_validate() -> None:
    validate_cases([copy.deepcopy(BASE_ROW), {**_row(), "id": "POINT-02"}])


def test_optional_adversarial_fields_validate_and_reach_expectations() -> None:
    row = _row(
        expected_status="indeterminate",
        required_behaviors=["state unavailable evidence"],
        prohibited_behaviors=["missing_input_as_zero"],
        source_disclosure=["USDA NRCS SDA"],
        max_tool_calls=2,
        max_retries=1,
        latency_budget_ms=5000,
    )
    validate_cases([row])

    record = to_mlflow_records([row])[0]
    # Behaviors and sources reach the judge only as guidelines, not as raw keys.
    assert "required_behaviors" not in record["expectations"]
    assert "source_disclosure" not in record["expectations"]
    for field in (
        "expected_status",
        "prohibited_behaviors",
        "max_tool_calls",
        "max_retries",
        "latency_budget_ms",
    ):
        assert record["expectations"][field] == row[field]

    zero_budget = to_mlflow_records([_row(max_tool_calls=0)])[0]["expectations"]
    assert zero_budget["max_tool_calls"] == 0


def test_behaviors_and_sources_become_judge_guidelines() -> None:
    row = _row(
        guidelines=["States that results are preliminary screening.", "Names the county."],
        required_behaviors=["Names the county.", "State unavailable evidence."],
        source_disclosure=["USDA NRCS SDA", "US Census TIGERweb"],
    )

    guidelines = to_mlflow_records([row])[0]["expectations"]["guidelines"]

    assert guidelines == [
        "States that results are preliminary screening.",
        "Names the county.",
        "State unavailable evidence.",
        (
            "When the response reports soil, farmland, or urban-area results, it identifies "
            "USDA NRCS SDA as a data source; a response that reports no results does not "
            "need to name a source."
        ),
        (
            "When the response reports soil, farmland, or urban-area results, it identifies "
            "US Census TIGERweb as a data source; a response that reports no results does "
            "not need to name a source."
        ),
    ]

    bare = {**copy.deepcopy(BASE_ROW), "id": "DISC-01"}
    assert "guidelines" not in to_mlflow_records([bare])[0]["expectations"]


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("expected_status", "refused", "expected covered, indeterminate, or error"),
        ("required_behaviors", "not a list", "expected a list of strings"),
        ("prohibited_behaviors", [False], "expected a list of strings"),
        ("source_disclosure", [1], "expected a list of strings"),
        ("max_tool_calls", True, "expected an integer >= 0"),
        ("max_retries", -1, "expected an integer >= 0"),
        ("latency_budget_ms", float("inf"), "expected a finite number >= 0"),
    ],
)
def test_adversarial_field_validation(field: str, value: Any, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        validate_cases([_row(**{field: value})])


def test_unknown_prohibited_behavior_id_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown behavior ID 'future_behavior'"):
        validate_cases([_row(prohibited_behaviors=["future_behavior"])])


def test_stale_prohibited_behavior_id_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown behavior ID 'silent_nccpi_fallback'"):
        validate_cases([_row(prohibited_behaviors=["silent_nccpi_fallback"])])


def test_harness_only_fields_validate() -> None:
    validate_cases(
        [
            _row(
                assertions={"predicates": ["containsRegulatoryLimitation"]},
                invocation={"kind": "tool", "name": "lookup", "arguments": {}},
                expected_result={
                    "type": "object",
                    "required": ["available"],
                    "properties": {"available": {"type": "boolean"}},
                },
                ownership={
                    "maintainer": "evaluation",
                    "regulatory_approval_required": True,
                },
                protected_regulatory_assertions=["not_official_fppa_determination"],
            )
        ]
    )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("assertions", {"predicates": [1]}, "assertions: expected an object"),
        ("assertions", {"predicates": []}, "assertions: expected an object"),
        (
            "invocation",
            {"kind": "unknown", "name": "lookup", "arguments": {}},
            "invocation.kind: expected tool, resource, or prompt",
        ),
        (
            "invocation",
            {"kind": [], "name": "lookup", "arguments": {}},
            "invocation.kind: expected tool, resource, or prompt",
        ),
        (
            "invocation",
            {"kind": "tool", "name": "lookup", "arguments": []},
            "invocation.arguments: expected an object",
        ),
        ("expected_result", [], "expected_result: expected an object"),
        ("expected_result", {"type": "not-a-type"}, "expected_result.type: expected a supported"),
        ("expected_result", {"type": {}}, "expected_result.type: expected a supported"),
        (
            "ownership",
            {"maintainer": "evaluation", "regulatory_approval_required": "yes"},
            "ownership: expected maintainer string",
        ),
        (
            "protected_regulatory_assertions",
            ["ok", 1],
            "protected_regulatory_assertions: expected a non-empty list of strings",
        ),
    ],
)
def test_harness_only_field_validation(field: str, value: Any, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        validate_cases([_row(**{field: value})])


def test_structural_prohibited_behavior_requires_its_budget_field() -> None:
    with pytest.raises(ValueError, match="requires the 'max_retries' field"):
        validate_cases([_row(prohibited_behaviors=["retry_budget_exceeded"])])
    validate_cases([_row(prohibited_behaviors=["retry_budget_exceeded"], max_retries=1)])


def test_load_cases_filters(tmp_path: Path) -> None:
    rows = [
        _row(),
        {**copy.deepcopy(BASE_ROW), "id": "DISC-01", "category": "Discovery"},
        {**copy.deepcopy(BASE_ROW), "id": "DISC-02", "category": "Discovery"},
    ]
    path = _write(tmp_path, rows)

    assert [c["id"] for c in load_cases(path, ids=["DISC-02", "POINT-01"])] == [
        "POINT-01",
        "DISC-02",
    ]
    assert [c["id"] for c in load_cases(path, ground_truth_only=True)] == ["POINT-01"]
    assert [c["id"] for c in load_cases(path, category="discov")] == ["DISC-01", "DISC-02"]
    assert dataset_version(path) == "2.0.0"
    with pytest.raises(ValueError, match="Unknown case ids: NOPE-01"):
        load_cases(path, ids=["NOPE-01"])


def test_to_mlflow_records_matches_contract_c3() -> None:
    v1_row = {**copy.deepcopy(BASE_ROW), "id": "DISC-01", "expected_facts": []}
    records = to_mlflow_records([_row(), v1_row])

    assert records[0] == {
        "inputs": {
            "request": V2_ROW["user_prompt"],
            "force_tool_use": True,
        },
        "expectations": {
            "case_id": "POINT-01",
            "expected_tools": V2_ROW["expected_tools"],
            "expected_tool_calls": V2_ROW["expected_tool_calls"],
            "expected_facts": V2_ROW["expected_facts"],
            "numeric_expectations": V2_ROW["numeric_expectations"],
            "guidelines": V2_ROW["guidelines"],
        },
    }
    assert records[1]["expectations"] == {
        "case_id": "DISC-01",
        "expected_tools": BASE_ROW["expected_tools"],
    }
    assert records[1]["inputs"]["force_tool_use"] is True


def test_zero_call_budget_disables_forced_tool_use_in_mlflow_inputs() -> None:
    row = _row(max_tool_calls=0)

    record = to_mlflow_records([row])[0]

    assert record["inputs"] == {
        "request": row["user_prompt"],
        "force_tool_use": False,
        "max_tool_calls": 0,
    }


def test_explicit_force_tool_use_false_is_preserved() -> None:
    row = _row(force_tool_use=False, max_tool_calls=2)

    assert to_mlflow_records([row])[0]["inputs"]["force_tool_use"] is False


def test_synthetic_tool_allowed_when_expected_tools_empty() -> None:
    row = _row(
        expected_tools=[],
        expected_tool_calls=[{"name": "read_resource", "arguments": {"uri": "fppa://x"}}],
        numeric_expectations=...,
    )
    validate_cases([row])


@pytest.mark.parametrize(
    ("row", "message"),
    [
        (_row(user_prompt=...), "POINT-01.user_prompt: required field missing"),
        (_row(expected_tools="x"), "POINT-01.expected_tools: expected list"),
        (_row(expected_keywords=[1]), "POINT-01.expected_keywords: expected a list of strings"),
        (_row(surprise=1), "POINT-01.surprise: unknown field"),
        (
            _row(expected_tool_calls=[{"name": "list_farmland_classes"}]),
            "expected_tool_calls[0].name: 'list_farmland_classes' is not listed",
        ),
        (_row(expected_tool_calls=[{"args": {}}]), "expected an object with a string 'name'"),
        (
            _row(expected_tool_calls=[{"name": "read_resource", "arguments": []}]),
            "expected_tool_calls[0].arguments: expected an object",
        ),
        (
            _row(
                numeric_expectations=[
                    {"tool": "t", "path": "p", "value": float("nan"), "abs_tol": 0}
                ]
            ),
            "numeric_expectations[0].value: expected a finite number",
        ),
        (
            _row(numeric_expectations=[{"tool": "t", "path": "p", "value": 1, "abs_tol": -1}]),
            "numeric_expectations[0].abs_tol: expected a finite number >= 0",
        ),
        (
            _row(numeric_expectations=[{"tool": "t", "path": "p", "value": True, "abs_tol": 0}]),
            "numeric_expectations[0].value: expected a finite number",
        ),
        (
            _row(numeric_expectations=[{"tool": "t", "value": 1, "abs_tol": 0}]),
            "expected exactly keys tool, path, value, abs_tol",
        ),
        (_row(verified_on="10/21/2026"), "POINT-01.verified_on: expected ISO date"),
        (_row(verified_on="2026-02-30"), "POINT-01.verified_on: expected ISO date"),
        (_row(force_tool_use="yes"), "POINT-01.force_tool_use: expected bool"),
        (_row(guidelines="be nice"), "POINT-01.guidelines: expected a list of strings"),
    ],
)
def test_validation_error_paths(row: dict[str, Any], message: str) -> None:
    with pytest.raises(ValueError) as excinfo:
        validate_cases([row])
    assert message in str(excinfo.value)


def test_duplicate_ids_are_rejected() -> None:
    with pytest.raises(ValueError, match="POINT-01.id: duplicate id"):
        validate_cases([_row(), _row()])


def test_load_cases_rejects_invalid_file(tmp_path: Path) -> None:
    path = _write(tmp_path, [_row(), _row(id="X-01", surprise=True)])
    with pytest.raises(ValueError, match="X-01.surprise: unknown field"):
        load_cases(path)


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"version": "2.0.0"}, "'test_cases' is missing"),
        ({"test_cases": {"POINT-01": V2_ROW}}, "'test_cases' must be a list, got dict"),
        ({"test_cases": "POINT-01"}, "'test_cases' must be a list, got str"),
        ([V2_ROW], "top-level JSON must be an object, got list"),
        ({"test_cases": [_row(), "POINT-02"]}, "row[1]: expected an object"),
    ],
)
def test_load_cases_rejects_malformed_test_cases(
    tmp_path: Path, payload: Any, message: str
) -> None:
    path = tmp_path / "cases.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError) as excinfo:
        load_cases(path)
    assert message in str(excinfo.value)


def test_load_cases_accepts_empty_list(tmp_path: Path) -> None:
    assert load_cases(_write(tmp_path, [])) == []
