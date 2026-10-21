"""T1 MLflow evaluation runner (contract C5).

Loads the shared dataset, builds the in-process agent and scorers, and calls
``mlflow.genai.evaluate``.  ``mlflow`` is imported lazily so the module imports
without the ``eval-databricks`` dependency group (``--dry-run`` still works).

Usage::

    uv run --group eval-databricks python eval/databricks/run_mlflow_eval.py --ground-truth
    uv run --group eval-databricks python eval/databricks/run_mlflow_eval.py --dry-run
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from collections import Counter
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parents[1]
for _path in (_HERE.parent, _HERE):  # eval/ (common) and eval/databricks/ (agent, scorers)
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from agent import available_prompt_versions, build_agent
from common.dataset import dataset_version, load_cases, to_mlflow_records
from scorers import build_scorers

DEFAULT_MODEL = "databricks-gpt-5-6-luna"
DEFAULT_JUDGE = "databricks-claude-sonnet-4-5"
_PASS_VALUES = {"yes", "true", "pass"}
_FAIL_VALUES = {"no", "false", "fail"}


def _default_experiment() -> str:
    """``/Users/<current user>/fpac-soil-mcp-eval``; falls back to ``$USER``."""
    user = None
    try:
        from databricks.sdk import WorkspaceClient

        user = WorkspaceClient().current_user.me().user_name
    except Exception:  # noqa: BLE001 -- best-effort lookup
        user = None
    return f"/Users/{user or os.environ.get('USER', 'unknown')}/fpac-soil-mcp-eval"


def _git(*args: str) -> str:
    try:
        out = subprocess.run(
            ["git", *args],
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
        return out.stdout.strip() or "unknown"
    except Exception:  # noqa: BLE001 -- intentional fallback
        return "unknown"


def _git_sha() -> str:
    return _git("rev-parse", "HEAD")


def _git_branch() -> str:
    return _git("rev-parse", "--abbrev-ref", "HEAD")


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the T1 MLflow evaluation for fpac-soil-mcp.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--cases", help="Comma-separated case IDs to run")
    group.add_argument("--ground-truth", action="store_true", help="Run only verified rows")
    group.add_argument("--all", action="store_true", help="Run all rows")
    parser.add_argument(
        "--model", default=DEFAULT_MODEL, help=f"Agent model (default {DEFAULT_MODEL})"
    )
    parser.add_argument(
        "--judge-model", default=DEFAULT_JUDGE, help=f"Judge model (default {DEFAULT_JUDGE})"
    )
    parser.add_argument("--experiment", default=None, help="MLflow experiment path")
    parser.add_argument("--max-workers", type=int, default=1, help="Max parallel eval workers")
    parser.add_argument("--max-turns", type=int, default=8, help="Max agent turns per case")
    parser.add_argument(
        "--system-prompt-version",
        default="v1",
        choices=available_prompt_versions(),
        help="System prompt version (default v1)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Build records and scorers only")
    return parser.parse_args(argv)


def _select_cases(args: argparse.Namespace) -> list[dict[str, Any]]:
    if args.cases:
        ids = [s.strip() for s in args.cases.split(",") if s.strip()]
        return load_cases(ids=ids)
    if args.all:
        return load_cases()
    return load_cases(ground_truth_only=True)


def _classify(assessment: Any) -> str:
    """Map one feedback assessment to ``pass`` / ``fail`` / ``null``."""
    if getattr(assessment, "error", None) is not None:
        return "null"
    value = getattr(assessment, "value", None)
    if isinstance(value, bool):
        return "pass" if value else "fail"
    text = str(getattr(value, "value", value)).strip().lower() if value is not None else ""
    if text in _PASS_VALUES:
        return "pass"
    if text in _FAIL_VALUES:
        return "fail"
    return "null"


def summarize_traces(
    traces: Iterable[Any], scorer_names: Sequence[str]
) -> dict[str, dict[str, int]]:
    """Per-scorer pass/fail/null counts over evaluated traces.

    A scorer with no feedback assessment on a trace (it returned ``None`` or was
    not applicable) counts as ``null`` for that row.
    """
    counts = {name: Counter(**{"pass": 0, "fail": 0, "null": 0}) for name in scorer_names}
    for trace in traces:
        seen: dict[str, str] = {}
        for assessment in getattr(trace.info, "assessments", None) or []:
            name = getattr(assessment, "name", None)
            if name in counts and getattr(assessment, "feedback", None) is not None:
                seen[name] = _classify(assessment)
        for name in scorer_names:
            counts[name][seen.get(name, "null")] += 1
    return {name: dict(c) for name, c in counts.items()}


def run(argv: Sequence[str] | None = None) -> dict[str, Any]:
    """Execute the T1 evaluation.  Returns a dict with run info (or dry-run info)."""
    args = _parse_args(argv)
    cases = _select_cases(args)
    records = to_mlflow_records(cases)
    scorers = build_scorers(args.judge_model)
    scorer_names = [s.name for s in scorers]

    if args.dry_run:
        print(f"Dry run: {len(records)} records, scorers: {scorer_names}")
        return {"records": records, "scorer_names": scorer_names}

    import mlflow

    os.environ["MLFLOW_GENAI_EVAL_MAX_WORKERS"] = str(args.max_workers)

    experiment = args.experiment or _default_experiment()
    mlflow.set_experiment(experiment)

    ds_ver = dataset_version()
    tags = {
        "git_sha": _git_sha(),
        "git_branch": _git_branch(),
        "agent_model": args.model,
        "judge_model": args.judge_model,
        "dataset_version": ds_ver,
        "system_prompt_version": args.system_prompt_version,
    }

    predict = build_agent(
        args.model,
        max_turns=args.max_turns,
        system_prompt_version=args.system_prompt_version,
    )

    with mlflow.start_run(tags=tags) as active_run:
        mlflow.genai.evaluate(data=records, predict_fn=predict, scorers=scorers)
        run_id = active_run.info.run_id

    traces = mlflow.search_traces(run_id=run_id, return_type="list")
    summary = summarize_traces(traces, scorer_names)

    print(f"Run ID: {run_id}")
    print(f"Experiment: {experiment}")
    print(f"Dataset version: {ds_ver}")
    print(f"Records: {len(records)}")
    for name, counts in summary.items():
        print(f"  {name}: pass={counts['pass']} fail={counts['fail']} null={counts['null']}")

    return {"run_id": run_id, "experiment": experiment, "summary": summary, "records": records}


def main() -> None:
    run()


if __name__ == "__main__":
    main()
