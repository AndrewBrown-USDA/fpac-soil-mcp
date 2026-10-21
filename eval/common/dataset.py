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
        "verified_on",
    }
)
ALLOWED_FIELDS = frozenset(REQUIRED_V1_FIELDS) | OPTIONAL_V1_FIELDS | V2_FIELDS

# Agent-side tools that expose MCP resources and prompts (contract C4).
SYNTHETIC_TOOLS = frozenset({"read_resource", "get_prompt"})

# v2 fields copied into MLflow `expectations` when present and non-empty (contract C3).
EXPECTATION_FIELDS = ("expected_tool_calls", "expected_facts", "numeric_expectations", "guidelines")

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _read(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


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

    for field in ("expected_tools", "expected_keywords", "expected_facts", "guidelines"):
        if field in case and not _is_str_list(case[field]):
            err(field, "expected a list of strings")

    for field in ("force_tool_use", "live_data_sensitive"):
        if field in case and not isinstance(case[field], bool):
            err(field, "expected bool")

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

    ``ids`` keeps rows in dataset order and raises ``ValueError`` for unknown ids.
    ``ground_truth_only`` keeps rows that carry ``verified_on``. ``category`` is a
    case-insensitive substring match, as in the Pi runner.
    """
    cases = _read(Path(path)).get("test_cases", [])
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
        expectations: dict[str, Any] = {
            "case_id": case["id"],
            "expected_tools": list(case["expected_tools"]),
            "expected_keywords": list(case["expected_keywords"]),
        }
        for field in EXPECTATION_FIELDS:
            if case.get(field):
                expectations[field] = case[field]
        records.append({"inputs": {"request": case["user_prompt"]}, "expectations": expectations})
    return records
