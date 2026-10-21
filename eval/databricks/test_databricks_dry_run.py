"""Dry-run tests for eval/databricks/run_mlflow_eval.py that need no MLflow.

These tests deliberately do not ``importorskip("mlflow")``: they must pass both with and
without the ``eval-databricks`` dependency group.
"""

from __future__ import annotations

from common.dataset import load_cases
from run_mlflow_eval import run
from scorers import scorer_names


def test_dry_run_ground_truth_needs_no_mlflow() -> None:
    result = run(["--dry-run"])

    ids = [record["expectations"]["case_id"] for record in result["records"]]
    assert len(ids) == 5
    assert ids == [case["id"] for case in load_cases(ground_truth_only=True)]
    assert result["scorer_names"] == scorer_names()


def test_dry_run_all_rows_needs_no_mlflow() -> None:
    result = run(["--dry-run", "--all"])

    assert len(result["records"]) == len(load_cases())
    assert result["scorer_names"] == scorer_names()
