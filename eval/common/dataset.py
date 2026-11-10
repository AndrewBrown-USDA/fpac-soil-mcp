"""Load, validate, and convert the shared eval dataset (`prompt_test_cases.json`, v2).

The v2 schema is additive over v1: every v1 field is unchanged and each v2 field is optional
per row. See `planning/EXECUTION_PLAN_33.md` contracts C2 (schema) and C3 (MLflow records).
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Iterable
from datetime import date
from pathlib import Path
from typing import Any

DEFAULT_PATH = Path(__file__).resolve().parents[1] / "prompt_test_cases.json"
GOLD_SET_PATH = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "phase4_gold_set.json"

REQUIRED_V1_FIELDS: dict[str, type] = {
    "id": str,
    "category": str,
    "target_type": str,
    "target_name": str,
    "user_prompt": str,
    "expected_tools": list,
    "expected_keywords": list,
}
OPTIONAL_V1_FIELDS = frozenset({"sample_geometry"})
V2_FIELDS = frozenset(
    {
        "expected_tool_calls",
        "expected_facts",
        "numeric_expectations",
        "guidelines",
        "force_tool_use",
        "live_data_sensitive",
        "evidence_tier",
        "verified_on",
    }
)
ADVERSARIAL_FIELDS = frozenset(
    {
        "expected_status",
        "required_behaviors",
        "prohibited_behaviors",
        "source_disclosure",
        "max_tool_calls",
        "max_retries",
        "latency_budget_ms",
    }
)
ALLOWED_FIELDS = frozenset(REQUIRED_V1_FIELDS) | OPTIONAL_V1_FIELDS | V2_FIELDS | ADVERSARIAL_FIELDS

# Agent-side tools that expose MCP resources and prompts (contract C4).
SYNTHETIC_TOOLS = frozenset({"read_resource", "get_prompt"})

# v2 fields copied into MLflow `expectations` when present and non-empty (contract C3).
EXPECTATION_FIELDS = (
    "expected_tool_calls",
    "expected_facts",
    "numeric_expectations",
    "guidelines",
    "evidence_tier",
    "expected_status",
    "required_behaviors",
    "prohibited_behaviors",
    "source_disclosure",
    "max_tool_calls",
    "max_retries",
    "latency_budget_ms",
)

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _read(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _validate_gold_case(case: Any, index: int) -> list[str]:
    errors: list[str] = []
    if not isinstance(case, dict):
        return [f"case[{index}]: expected an object"]
    case_id = case.get("id", f"case[{index}]")
    if not isinstance(case_id, str) or not case_id:
        errors.append(f"case[{index}].id: expected a non-empty string")
    for field in ("category", "description", "status"):
        if not isinstance(case.get(field), str):
            errors.append(f"{case_id}.{field}: expected a string")
    if case.get("status") not in {"covered", "indeterminate", "error"}:
        errors.append(f"{case_id}.status: expected covered, indeterminate, or error")
    expectations = case.get("expectations")
    if not isinstance(expectations, list) or not expectations:
        errors.append(f"{case_id}.expectations: expected a non-empty list")
    else:
        for item_index, expectation in enumerate(expectations):
            where = f"{case_id}.expectations[{item_index}]"
            if not isinstance(expectation, dict):
                errors.append(f"{where}: expected an object")
                continue
            if not isinstance(expectation.get("path"), str) or not expectation["path"]:
                errors.append(f"{where}.path: expected a non-empty string")
            modes = {"equals", "approx", "is_null"} & set(expectation)
            if len(modes) != 1:
                errors.append(f"{where}: expected exactly one matching mode")
    return errors


def validate_gold_set(data: Any) -> None:
    """Validate the versioned deterministic Phase 4 gold-set contract."""
    if not isinstance(data, dict):
        raise TypeError("Gold set: top-level JSON must be an object")
    if data.get("schema") != "phase4-gold-set":
        raise ValueError("Gold set: unsupported schema")
    if not isinstance(data.get("version"), str) or not data["version"]:
        raise ValueError("Gold set: version must be a non-empty string")
    cases = data.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("Gold set: cases must be a non-empty list")
    errors: list[str] = []
    seen: set[str] = set()
    for index, case in enumerate(cases):
        errors.extend(_validate_gold_case(case, index))
        if isinstance(case, dict) and isinstance(case.get("id"), str):
            if case["id"] in seen:
                errors.append(f"{case['id']}.id: duplicate id")
            seen.add(case["id"])
    if errors:
        raise ValueError("Invalid Phase 4 gold set:\n  " + "\n  ".join(errors))


def load_gold_set(path: Path | str = GOLD_SET_PATH) -> list[dict[str, Any]]:
    """Load the deterministic Phase 4 gold set in file order."""
    data = _read(Path(path))
    validate_gold_set(data)
    return list(data["cases"])


def _is_number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool) and math.isfinite(value)


def _is_str_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _row_errors(case: dict[str, Any], row_id: str) -> list[str]:
    errors: list[str] = []

    def err(field: str, message: str) -> None:
        errors.append(f"{row_id}.{field}: {message}")

    for field, kind in REQUIRED_V1_FIELDS.items():
        if field not in case:
            err(field, "required field missing")
        elif not isinstance(case[field], kind):
            err(field, f"expected {kind.__name__}")

    for field in sorted(set(case) - ALLOWED_FIELDS):
        err(field, "unknown field")

    for field in (
        "expected_tools",
        "expected_keywords",
        "expected_facts",
        "guidelines",
        "required_behaviors",
        "prohibited_behaviors",
        "source_disclosure",
    ):
        if field in case and not _is_str_list(case[field]):
            err(field, "expected a list of strings")

    if "expected_status" in case and (
        not isinstance(case["expected_status"], str)
        or case["expected_status"] not in {"covered", "indeterminate", "error"}
    ):
        err("expected_status", "expected covered, indeterminate, or error")

    for field in ("force_tool_use", "live_data_sensitive"):
        if field in case and not isinstance(case[field], bool):
            err(field, "expected bool")

    for field in ("max_tool_calls", "max_retries"):
        if field in case and (
            not isinstance(case[field], int) or isinstance(case[field], bool) or case[field] < 0
        ):
            err(field, "expected an integer >= 0")

    if "latency_budget_ms" in case and (
        not _is_number(case["latency_budget_ms"]) or case["latency_budget_ms"] < 0
    ):
        err("latency_budget_ms", "expected a finite number >= 0")

    if "evidence_tier" in case and (
        not isinstance(case["evidence_tier"], str)
        or case["evidence_tier"] not in {"deterministic_contract", "model_assisted"}
    ):
        err("evidence_tier", "expected deterministic_contract or model_assisted")

    if "verified_on" in case:
        value = case["verified_on"]
        try:
            if not (isinstance(value, str) and _ISO_DATE.match(value)):
                raise ValueError
            date.fromisoformat(value)
        except ValueError:
            err("verified_on", "expected ISO date YYYY-MM-DD")

    expected_tools = case.get("expected_tools")
    calls = case.get("expected_tool_calls")
    if calls is not None:
        if not isinstance(calls, list):
            err("expected_tool_calls", "expected a list")
            calls = []
        for index, call in enumerate(calls):
            where = f"expected_tool_calls[{index}]"
            if not isinstance(call, dict) or not isinstance(call.get("name"), str):
                err(where, "expected an object with a string 'name'")
                continue
            if set(call) - {"name", "arguments"}:
                err(where, f"unknown keys {sorted(set(call) - {'name', 'arguments'})}")
            if "arguments" in call and not isinstance(call["arguments"], dict):
                err(f"{where}.arguments", "expected an object")
            name = call["name"]
            if (
                _is_str_list(expected_tools)
                and expected_tools
                and name not in SYNTHETIC_TOOLS
                and name not in expected_tools
            ):
                err(f"{where}.name", f"'{name}' is not listed in expected_tools")

    numerics = case.get("numeric_expectations")
    if numerics is not None:
        if not isinstance(numerics, list):
            err("numeric_expectations", "expected a list")
            numerics = []
        for index, item in enumerate(numerics):
            where = f"numeric_expectations[{index}]"
            if not isinstance(item, dict):
                err(where, "expected an object")
                continue
            if set(item) != {"tool", "path", "value", "abs_tol"}:
                err(where, "expected exactly keys tool, path, value, abs_tol")
                continue
            if not isinstance(item["tool"], str) or not isinstance(item["path"], str):
                err(where, "tool and path must be strings")
            if not _is_number(item["value"]):
                err(f"{where}.value", "expected a finite number")
            if not _is_number(item["abs_tol"]) or item["abs_tol"] < 0:
                err(f"{where}.abs_tol", "expected a finite number >= 0")

    return errors


def validate_cases(cases: Iterable[dict[str, Any]]) -> None:
    """Validate rows against the v2 schema; raise ``ValueError`` listing every problem."""
    errors: list[str] = []
    seen: set[str] = set()
    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            errors.append(f"row[{index}]: expected an object")
            continue
        row_id = case.get("id") if isinstance(case.get("id"), str) else f"row[{index}]"
        if row_id in seen:
            errors.append(f"{row_id}.id: duplicate id")
        seen.add(row_id)
        errors.extend(_row_errors(case, row_id))
    if errors:
        raise ValueError("Invalid eval dataset:\n  " + "\n  ".join(errors))


def dataset_version(path: Path | str = DEFAULT_PATH) -> str:
    """Return the dataset file's top-level ``version`` string."""
    return str(_read(Path(path)).get("version", "unknown"))


def load_cases(
    path: Path | str = DEFAULT_PATH,
    *,
    ids: Iterable[str] | None = None,
    ground_truth_only: bool = False,
    category: str | None = None,
) -> list[dict[str, Any]]:
    """Load and validate the dataset, then filter rows.

    Raises ``ValueError`` when the file is not an object with a ``test_cases`` list
    or when any row fails validation.

    ``ids`` keeps rows in dataset order and raises ``ValueError`` for unknown ids.
    ``ground_truth_only`` keeps rows that carry ``verified_on``. ``category`` is a
    case-insensitive substring match, as in the Pi runner.
    """
    data = _read(Path(path))
    problem = None
    if not isinstance(data, dict):
        problem = f"top-level JSON must be an object, got {type(data).__name__}"
    elif "test_cases" not in data:
        problem = "'test_cases' is missing"
    elif not isinstance(data["test_cases"], list):
        problem = f"'test_cases' must be a list, got {type(data['test_cases']).__name__}"
    if problem:
        raise ValueError(f"{path}: {problem}")
    cases = data["test_cases"]
    validate_cases(cases)

    if ids is not None:
        wanted = list(ids)
        unknown = sorted(set(wanted) - {case["id"] for case in cases})
        if unknown:
            raise ValueError(f"Unknown case ids: {', '.join(unknown)}")
        cases = [case for case in cases if case["id"] in set(wanted)]
    if ground_truth_only:
        cases = [case for case in cases if "verified_on" in case]
    if category:
        needle = category.lower()
        cases = [case for case in cases if needle in case["category"].lower()]
    return cases


def to_mlflow_records(cases: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert rows to ``mlflow.genai.evaluate`` records (contract C3)."""
    records: list[dict[str, Any]] = []
    for case in cases:
        inputs: dict[str, Any] = {
            "request": case["user_prompt"],
            "force_tool_use": case_forces_tool_use(case),
        }
        if "max_tool_calls" in case:
            inputs["max_tool_calls"] = case["max_tool_calls"]
        expectations: dict[str, Any] = {
            "case_id": case["id"],
            "expected_tools": list(case["expected_tools"]),
            "expected_keywords": list(case["expected_keywords"]),
        }
        for field in EXPECTATION_FIELDS:
            if field in case and (
                field in {"max_tool_calls", "max_retries", "latency_budget_ms"} or case[field]
            ):
                expectations[field] = case[field]
        records.append({"inputs": inputs, "expectations": expectations})
    return records


def case_forces_tool_use(case: dict[str, Any]) -> bool:
    """Keep the default tool-use contract unless the case explicitly disables it or has no budget."""
    return case.get("force_tool_use", True) and case.get("max_tool_calls") != 0
