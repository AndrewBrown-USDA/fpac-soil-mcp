"""Offline tests for eval/databricks/scorers.py. No judge or network calls."""

from __future__ import annotations

import os
from typing import Any

import pytest

mlflow = pytest.importorskip("mlflow")

from scorers import (
    DETERMINISTIC_SCORER_NAMES,
    build_scorers,
    deterministic_scorers,
    resolve_path,
)


@pytest.fixture(scope="module", autouse=True)
def local_mlflow(tmp_path_factory: pytest.TempPathFactory):
    previous = os.environ.get("MLFLOW_ENABLE_ASYNC_TRACE_LOGGING")
    os.environ["MLFLOW_ENABLE_ASYNC_TRACE_LOGGING"] = "false"
    db = tmp_path_factory.mktemp("mlflow") / "mlflow.db"
    mlflow.set_tracking_uri(f"sqlite:///{db}")
    mlflow.set_experiment("t1-scorer-tests")
    yield
    mlflow.set_tracking_uri(None)
    if previous is None:
        os.environ.pop("MLFLOW_ENABLE_ASYNC_TRACE_LOGGING", None)
    else:
        os.environ["MLFLOW_ENABLE_ASYNC_TRACE_LOGGING"] = previous


@pytest.fixture(scope="module")
def scorers() -> dict[str, Any]:
    return {s.name: s for s in deterministic_scorers()}


def make_trace(calls: list[tuple[str, dict[str, Any], Any]], answer: str = "answer"):
    """Build a C4-shaped trace: AGENT root with one TOOL child span per call."""

    @mlflow.trace(name="fpac_soil_agent", span_type="AGENT")
    def agent(request: str) -> str:
        for name, inputs, result in calls:
            with mlflow.start_span(name=name, span_type="TOOL") as span:
                span.set_inputs(inputs)
                span.set_outputs({"result": result, "is_error": False})
        return answer

    agent("request")
    return mlflow.get_trace(mlflow.get_last_active_trace_id())


INTERP_RESULT = {
    "result": [
        {"mukey": "412850", "numeric_rating": "0.72"},
        {"mukey": "412851", "numeric_rating": "0.592"},
    ]
}
INTERP_ARGS = {"mukeys": ["412850", "412851", "413100"]}
POINT_ARGS = {"latitude": 41.8781, "longitude": -93.0977}


def test_resolve_path() -> None:
    assert resolve_path(INTERP_RESULT, "result[1].numeric_rating") == "0.592"
    assert resolve_path({"a": {"b": [1, {"c": 2}]}}, "a.b[1].c") == 2
    with pytest.raises(IndexError):
        resolve_path(INTERP_RESULT, "result[5].numeric_rating")


def test_required_tools_called(scorers: dict[str, Any]) -> None:
    trace = make_trace([("get_soil_interpretations", INTERP_ARGS, INTERP_RESULT)])
    score = scorers["required_tools_called"]

    assert score(trace=trace, expectations={"expected_tools": ["get_soil_interpretations"]}).value
    miss = score(trace=trace, expectations={"expected_tools": ["list_farmland_classes"]})
    assert miss.value is False
    assert "list_farmland_classes" in miss.rationale
    assert score(trace=trace, expectations={"expected_tools": []}) is None


def test_keywords_present(scorers: dict[str, Any]) -> None:
    score = scorers["keywords_present"]
    expectations = {"expected_keywords": ["Prime farmland", "AD-1006"]}

    assert score(outputs="prime farmland; see Form AD\u20111006", expectations=expectations).value
    miss = score(outputs="prime farmland", expectations=expectations)
    assert miss.value is False
    assert "AD-1006" in miss.rationale
    assert score(outputs="x", expectations={}) is None


def test_numeric_within_tolerance_reads_tool_output(scorers: dict[str, Any]) -> None:
    trace = make_trace([("get_soil_interpretations", INTERP_ARGS, INTERP_RESULT)])
    score = scorers["numeric_within_tolerance"]

    def check(value: float, path: str = "result[0].numeric_rating") -> dict[str, Any]:
        return {
            "numeric_expectations": [
                {"tool": "get_soil_interpretations", "path": path, "value": value, "abs_tol": 0.01}
            ]
        }

    assert score(trace=trace, expectations=check(0.725)).value is True
    assert score(trace=trace, expectations=check(0.80)).value is False
    assert score(trace=trace, expectations=check(0.72, "result[9].numeric_rating")).value is False
    assert score(trace=trace, expectations={}) is None


def test_tool_arguments_within_tolerance(scorers: dict[str, Any]) -> None:
    trace = make_trace(
        [
            ("get_farmland_classification_by_point", {**POINT_ARGS, "latitude": 41.87812}, {}),
            ("get_soil_interpretations", {"mukeys": ["413100", "412850", "412851"]}, {}),
        ]
    )
    score = scorers["tool_arguments_within_tolerance"]

    def expect(*calls: dict[str, Any]) -> dict[str, Any]:
        return {"expected_tool_calls": list(calls)}

    point = {"name": "get_farmland_classification_by_point", "arguments": POINT_ARGS}
    interp = {"name": "get_soil_interpretations", "arguments": INTERP_ARGS}
    assert score(trace=trace, expectations=expect(point, interp)).value is True

    far = {**point, "arguments": {**POINT_ARGS, "latitude": 41.88}}
    assert score(trace=trace, expectations=expect(far)).value is False
    wrong_string = {"name": "get_soil_interpretations", "arguments": {"mukeys": ["1", "2", "3"]}}
    assert score(trace=trace, expectations=expect(wrong_string)).value is False
    absent = {"name": "get_farmland_classification_by_mukey", "arguments": {"mukey": "412850"}}
    assert score(trace=trace, expectations=expect(absent)).value is False

    assert score(trace=trace, expectations=expect({"name": "read_resource"})) is None
    assert score(trace=trace, expectations={}) is None


def test_build_scorers_names_and_judge_settings() -> None:
    built = build_scorers("databricks-claude-sonnet-4-5")
    names = [s.name for s in built]

    assert names[:4] == list(DETERMINISTIC_SCORER_NAMES)
    assert names[4:] == [
        "correctness",
        "fppa_compliance",
        "expectations_guidelines",
        "tool_call_correctness",
        "safety",
        "tool_call_efficiency",
    ]
    for judge in built[4:]:
        assert judge.model == "databricks:/databricks-claude-sonnet-4-5"
        assert judge.inference_params == {"temperature": 0}
