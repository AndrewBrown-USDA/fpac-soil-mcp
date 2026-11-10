"""Offline tests for eval/databricks/run_mlflow_eval.py.

The ``--dry-run`` path builds records and scorers without making any model or
network calls, so these tests run in the default offline suite when the
``eval-databricks`` dependency group is installed.
"""

from __future__ import annotations

import os
from types import SimpleNamespace

import pytest

mlflow = pytest.importorskip("mlflow")

from run_mlflow_eval import _git_branch, _git_sha, run, summarize_traces
from scorers import DETERMINISTIC_SCORER_NAMES


@pytest.fixture(scope="module", autouse=True)
def local_mlflow(tmp_path_factory: pytest.TempPathFactory):
    previous = os.environ.get("MLFLOW_ENABLE_ASYNC_TRACE_LOGGING")
    os.environ["MLFLOW_ENABLE_ASYNC_TRACE_LOGGING"] = "false"
    db = tmp_path_factory.mktemp("mlflow") / "mlflow.db"
    mlflow.set_tracking_uri(f"sqlite:///{db}")
    mlflow.set_experiment("t1-runner-tests")
    yield
    mlflow.set_tracking_uri(None)
    if previous is None:
        os.environ.pop("MLFLOW_ENABLE_ASYNC_TRACE_LOGGING", None)
    else:
        os.environ["MLFLOW_ENABLE_ASYNC_TRACE_LOGGING"] = previous


def test_dry_run_returns_ground_truth_records_and_scorer_names() -> None:
    result = run(["--dry-run"])

    records = result["records"]
    assert len(records) == 5
    for rec in records:
        assert "inputs" in rec
        assert "request" in rec["inputs"]
        assert "expectations" in rec
        assert "case_id" in rec["expectations"]

    scorer_names = result["scorer_names"]
    assert scorer_names[:4] == list(DETERMINISTIC_SCORER_NAMES)
    assert "correctness" in scorer_names
    assert "safety" in scorer_names


def test_dry_run_with_specific_cases() -> None:
    result = run(["--dry-run", "--cases", "POINT-01,DISC-01"])
    assert len(result["records"]) == 2
    ids = [rec["expectations"]["case_id"] for rec in result["records"]]
    assert set(ids) == {"POINT-01", "DISC-01"}


def test_dry_run_all_cases() -> None:
    result = run(["--dry-run", "--all"])
    assert len(result["records"]) == 24


def _assessment(name: str, value: object, error: object = None) -> SimpleNamespace:
    return SimpleNamespace(name=name, value=value, error=error, feedback=object())


def _trace(*assessments: SimpleNamespace) -> SimpleNamespace:
    return SimpleNamespace(info=SimpleNamespace(assessments=list(assessments)))


def test_summarize_traces_counts_pass_fail_and_null() -> None:
    traces = [
        _trace(_assessment("a", True), _assessment("b", "yes"), _assessment("c", "no")),
        _trace(_assessment("a", False), _assessment("b", None, error="boom")),
        _trace(SimpleNamespace(name="a", value="x", error=None, feedback=None)),
    ]
    summary = summarize_traces(traces, ["a", "b", "c"])
    assert summary["a"] == {"pass": 1, "fail": 1, "null": 1}
    assert summary["b"] == {"pass": 1, "fail": 0, "null": 2}
    assert summary["c"] == {"pass": 0, "fail": 1, "null": 2}


def test_git_tags_are_non_empty_strings() -> None:
    for value in (_git_sha(), _git_branch()):
        assert isinstance(value, str)
        assert value
