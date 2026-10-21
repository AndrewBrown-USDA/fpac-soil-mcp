"""T1 scorers: deterministic checks over C4 agent traces plus MLflow judges.

Deterministic scorers read TOOL span inputs/outputs (contract C4) and the MLflow
`expectations` built from the shared dataset (contract C3). Each returns ``None`` when its
expectation key is absent for a row, so it is skipped rather than failed.

`mlflow` is imported lazily so this module imports without the `eval-databricks` group.
"""

from __future__ import annotations

import math
import re
from typing import Any

from common.matching import keywords_present as _keywords_present
from common.matching import tool_matches

ARG_ABS_TOL = 1e-4

FPPA_COMPLIANCE_GUIDELINE = (
    "The response states that results are preliminary screening and are not an official "
    "FPPA determination, LESA score, Form AD-1006, or Form NRCS-CPA-106."
)

DETERMINISTIC_SCORER_NAMES = (
    "required_tools_called",
    "keywords_present",
    "numeric_within_tolerance",
    "tool_arguments_within_tolerance",
)

_PATH_TOKEN = re.compile(r"([^.\[\]]+)|\[(\d+)\]")


def _feedback(value: bool, rationale: str) -> Any:
    from mlflow.entities import Feedback

    return Feedback(value=value, rationale=rationale)


def _tool_spans(trace: Any) -> list[Any]:
    return [span for span in trace.data.spans if span.span_type == "TOOL"]


def resolve_path(obj: Any, path: str) -> Any:
    """Resolve a dot/bracket path such as ``result[0].numeric_rating``; raise on a miss."""
    current = obj
    for key, index in _PATH_TOKEN.findall(path):
        if index:
            current = current[int(index)]
        elif isinstance(current, dict):
            current = current[key]
        else:
            raise KeyError(key)
    return current


def _as_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _matches_expected(expected: Any, actual: Any) -> bool:
    if isinstance(expected, bool) or expected is None:
        return actual == expected
    if isinstance(expected, int | float):
        number = _as_number(actual)
        return number is not None and abs(number - expected) <= ARG_ABS_TOL
    if isinstance(expected, str):
        return isinstance(actual, str) and actual == expected
    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(
            key in actual and _matches_expected(value, actual[key])
            for key, value in expected.items()
        )
    if isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            return False
        if all(isinstance(item, str) for item in expected):
            return sorted(expected) == sorted(str(item) for item in actual)
        return all(_matches_expected(e, a) for e, a in zip(expected, actual, strict=True))
    return actual == expected


def required_tools_called(trace: Any, expectations: dict[str, Any]) -> Any:
    expected = expectations.get("expected_tools") or []
    if not expected:
        return None
    called = [span.name for span in _tool_spans(trace)]
    missing = [tool for tool in expected if not tool_matches(tool, called)]
    if missing:
        return _feedback(False, f"Missing tool calls: {missing}; called: {called}")
    return _feedback(True, f"All expected tools called: {expected}")


def keywords_present(outputs: Any, expectations: dict[str, Any]) -> Any:
    expected = expectations.get("expected_keywords") or []
    if not expected:
        return None
    ok, missing = _keywords_present("" if outputs is None else str(outputs), expected)
    if ok:
        return _feedback(True, f"All keywords present: {expected}")
    return _feedback(False, f"Missing keywords: {missing}")


def numeric_within_tolerance(trace: Any, expectations: dict[str, Any]) -> Any:
    checks = expectations.get("numeric_expectations") or []
    if not checks:
        return None
    spans = _tool_spans(trace)
    failures: list[str] = []
    for check in checks:
        observed: list[float] = []
        for span in spans:
            if not tool_matches(check["tool"], [span.name]):
                continue
            try:
                value = resolve_path((span.outputs or {}).get("result"), check["path"])
            except (KeyError, IndexError, TypeError):
                continue
            number = _as_number(value)
            if number is not None:
                observed.append(number)
        if not any(abs(n - check["value"]) <= check["abs_tol"] for n in observed):
            failures.append(
                f"{check['tool']}:{check['path']} expected {check['value']} "
                f"+/- {check['abs_tol']}, observed {observed or 'nothing'}"
            )
    if failures:
        return _feedback(False, "; ".join(failures))
    return _feedback(True, f"{len(checks)} numeric expectation(s) within tolerance")


def tool_arguments_within_tolerance(trace: Any, expectations: dict[str, Any]) -> Any:
    calls = [c for c in expectations.get("expected_tool_calls") or [] if "arguments" in c]
    if not calls:
        return None
    spans = _tool_spans(trace)
    failures: list[str] = []
    for call in calls:
        candidates = [span for span in spans if tool_matches(call["name"], [span.name])]
        if not any(_matches_expected(call["arguments"], span.inputs or {}) for span in candidates):
            seen = [span.inputs for span in candidates] or "no matching call"
            failures.append(f"{call['name']} expected {call['arguments']}, saw {seen}")
    if failures:
        return _feedback(False, "; ".join(failures))
    return _feedback(True, f"{len(calls)} tool call(s) matched expected arguments")


def deterministic_scorers() -> list[Any]:
    """Wrap the deterministic checks as MLflow scorers."""
    from mlflow.genai.scorers import scorer

    functions = (
        required_tools_called,
        keywords_present,
        numeric_within_tolerance,
        tool_arguments_within_tolerance,
    )
    return [scorer(name=fn.__name__)(fn) for fn in functions]


def judge_scorers(judge_model: str) -> list[Any]:
    """MLflow judges on a Databricks foundation model endpoint, with ``temperature=0``."""
    from mlflow.genai.scorers import (
        Correctness,
        ExpectationsGuidelines,
        Guidelines,
        Safety,
        ToolCallCorrectness,
        ToolCallEfficiency,
    )

    common = {"model": f"databricks:/{judge_model}", "inference_params": {"temperature": 0}}
    return [
        Correctness(**common),
        Guidelines(name="fppa_compliance", guidelines=FPPA_COMPLIANCE_GUIDELINE, **common),
        ExpectationsGuidelines(**common),
        ToolCallCorrectness(should_exact_match=False, **common),
        Safety(**common),
        ToolCallEfficiency(**common),
    ]


def build_scorers(judge_model: str) -> list[Any]:
    """Deterministic scorers followed by judges (D9)."""
    return deterministic_scorers() + judge_scorers(judge_model)
