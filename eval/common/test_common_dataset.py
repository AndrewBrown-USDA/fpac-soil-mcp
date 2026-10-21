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
    assert len(cases) >= 20
    assert dataset_version(DEFAULT_PATH).split(".")[0] in {"1", "2"}


def test_v1_row_and_full_v2_row_validate() -> None:
    validate_cases([copy.deepcopy(BASE_ROW), {**_row(), "id": "POINT-02"}])


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
        "inputs": {"request": V2_ROW["user_prompt"]},
        "expectations": {
            "case_id": "POINT-01",
            "expected_tools": V2_ROW["expected_tools"],
            "expected_keywords": V2_ROW["expected_keywords"],
            "expected_tool_calls": V2_ROW["expected_tool_calls"],
            "expected_facts": V2_ROW["expected_facts"],
            "numeric_expectations": V2_ROW["numeric_expectations"],
            "guidelines": V2_ROW["guidelines"],
        },
    }
    assert records[1]["expectations"] == {
        "case_id": "DISC-01",
        "expected_tools": BASE_ROW["expected_tools"],
        "expected_keywords": BASE_ROW["expected_keywords"],
    }


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
