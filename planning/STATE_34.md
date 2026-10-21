# State 34 — PR Review Remediation for the Databricks Eval Tier

Plan: `planning/EXECUTION_PLAN_34.md` · Template: `planning/PROMPT_TEMPLATE_34.md` · Branch: `feat/databricks-eval1`

## Baseline (record before wave 1)

- [x] Branch is `feat/databricks-eval1`, tree clean apart from Plan 34 artifacts (HEAD `3db89a4`); artifacts committed as `94af9dc` (`docs(planning):`).
- [x] Offline suite with group: `UV_PROJECT_ENVIRONMENT=/tmp/fpac-venv PYTHONDONTWRITEBYTECODE=1 uv run --group eval-databricks pytest -p no:cacheprovider -q` → 463 passed, 0 skipped, 24 deselected
- [x] Exact no-group suite: `UV_PROJECT_ENVIRONMENT=/tmp/fpac-venv-nogroup PYTHONDONTWRITEBYTECODE=1 uv run --exact pytest -p no:cacheprovider -q` → 443 passed, 3 skipped, 24 deselected
- [x] `uv run ruff check . --extend-ignore EXE002` → All checks passed
- [x] `uv run ruff format --check .` → 412 files already formatted
- [x] Reference live run for comparison: v2 default run `bc2e4bee` (from STATE_33 D12 results)

## Wave board

| Wave | Task | Title | Status | Worker | Result |
|---|---|---|---|---|---|
| 1 | 34.1.1 | Digit-boundary keyword matching | done | orchestrator (inline) | `c52dfc7` |
| 1 | 34.1.2 | Reject malformed `test_cases` | done | orchestrator (inline) | `97d8aee` |
| 2 | 34.2.1 | Strict list scoring + `scorer_names` | done | orchestrator (inline) | `2d1b66b` |
| 2 | 34.2.2 | AGENT span documentation and pinning test | done | orchestrator (inline) | `4d2b8f4` |
| 3 | 34.3.1 | Dry run without MLflow | done | orchestrator (inline) | `c187279` |
| 3 | 34.3.2 | README corrections | done | orchestrator (inline) | `50d8a39` |
| 4 | 34.4.1 | Full gates + 5-case live run (LIVE) | done | orchestrator (inline) | run `203e58f3` |

## Wave gates

| Wave | Offline pytest (group) | No-group (exact) | ruff check | ruff format | Notes |
|---|---|---|---|---|---|
| 1 | 488 passed, 24 desel | 468 passed, 3 skipped | clean | 414 formatted | +25 tests |
| 2 | 494 passed, 24 desel | 468 passed, 3 skipped | clean | 416 formatted | +6 tests (group only) |
| 3 | 496 passed, 24 desel | 470 passed, 3 skipped | clean | 419 formatted | +2 dry-run tests, pass in both envs |
| 4 | 496 passed, 24 desel | 470 passed, 3 skipped | clean | 419 formatted | live run id: `203e58f3a38a4770a0123d34e1e9193c` |

## Task reports

<!-- Workers append `## <task-id>` sections here (<=15 lines each). -->

All tasks ran inline (no sub-agent spawning on this surface); each micro-TODO in `planning/tasks/34.*.todo.md` was written and reviewed before code.

## 34.1.1

Status: done (`c52dfc7`)
Changes: `eval/common/matching.py` new `_keyword_pattern` (digit lookbehind/lookahead at digit edges), `keywords_present` uses it, docstring states the rule; `test_common_matching.py` +5 negatives, +4 positives, +1 dataset-count check, +parametrized digit-edged dataset keywords (`f"See {kw} here."`).
Tests: `uv run pytest -p no:cacheprovider eval/common -q` -> 79 passed; ruff clean.
Deviations: none.
Gotchas: affects Pi and Databricks harnesses through `keywords_present`; live run shows keywords_present 5/0 (no regression).

## 34.1.2

Status: done (`97d8aee`)
Changes: `eval/common/dataset.py` `load_cases` raises `ValueError("<path>: ...")` for non-object top level, missing `test_cases`, or non-list `test_cases`; docstring updated. `test_common_dataset.py` +5 parametrized malformed-file cases, +1 empty-list case.
Tests: eval/common 79 passed; ruff clean.
Deviations: `validate_cases` already reported non-dict rows as `row[<i>]: expected an object`; kept that message (spec wording was `row <i>: must be an object`) and pinned it via `load_cases`. Single `raise` after collecting `problem` to satisfy ruff TRY004 while keeping `ValueError`.

## 34.2.1

Status: done (`2d1b66b`)
Changes: `scorers.py` string-list branch requires all actual items be `str`; new `JUDGE_SCORER_NAMES` and pure `scorer_names(judge_model=None)`. Tests +1 names-equal-built, +4 parametrized strict/order cases.
Tests: `uv run --group eval-databricks pytest -p no:cacheprovider eval/databricks/test_databricks_scorers.py eval/databricks/test_databricks_agent.py -q` -> 21 passed; ruff clean.
Deviations: none. Judge names taken from the existing MLflow 3.12 assertion in `test_build_scorers_names_and_judge_settings`.
Gotchas: H4 did not trigger live (tool_arguments_within_tolerance 4/0/1).

## 34.2.2

Status: done (`4d2b8f4`)
Changes: `agent.py` module docstring documents AGENT plain-text vs TOOL sanitized and the synthetic-only rule; `test_agent_span_shape_is_pinned` (two tool calls; root name/type, request in inputs, answer in outputs, TOOL parents = root). No code change to `@mlflow.trace`/`predict`.
Tests: same command as 34.2.1 -> 21 passed; ruff format fix (wrapped list) applied.
Deviations: none.

## 34.3.1

Status: done (`c187279`)
Changes: `run_mlflow_eval.py` imports `scorer_names`; dry-run returns before `build_scorers`; live path builds scorers after `import mlflow`; local renamed `names`; docstring/usage/help updated. New `test_databricks_dry_run.py` (no importorskip): ground-truth ids match `load_cases(ground_truth_only=True)` (5), `--all` matches `len(load_cases())`.
Tests: with group runner + dry-run -> 7 passed; exact no-group `pytest eval/databricks/test_databricks_dry_run.py -v` -> 2 PASSED (not skipped); no-group CLI `--dry-run` prints 5 records + 10 scorer names. Ruff I001 fixed.
Deviations: `--all` count from `load_cases()` instead of hard-coded 20.

## 34.3.2

Status: done (`50d8a39`)
Changes: README prompt note -> scope-aware prompt deferred, will be `v3`; Privacy section: synthetic/public-only rule first, TOOL sanitized, AGENT plain text not sanitized and why; dry-run comment and flag row say no group/MLflow needed; Components lists the new test file.
Acceptance: `grep "planned as"` empty; `v3` at L90; `synthetic` at L94, L99, L104.
Deviations: Components line added (doc accuracy for the new test file).

## 34.4.1

Status: done
Gates (serial): group 496 passed, 24 deselected; exact no-group 470 passed, 3 skipped, 24 deselected; `ruff check . --extend-ignore EXE002` clean; `ruff format --check .` 419 formatted. No regressions vs baseline (+33 / +27 tests).
Live: `uv run --group eval-databricks python eval/databricks/run_mlflow_eval.py --ground-truth` (v2, gpt-5-6-luna, claude-sonnet-4-5, dataset 2.0.1, 79s) -> run `203e58f3a38a4770a0123d34e1e9193c`.
Scores (pass/fail/null): required_tools_called 4/0/1, keywords_present 5/0/0, numeric_within_tolerance 1/0/4, tool_arguments_within_tolerance 4/0/1, correctness 5/0/0, fppa_compliance 5/0/0, expectations_guidelines 5/0/0, tool_call_correctness 5/0/0, safety 5/0/0, tool_call_efficiency 5/0/0.
vs `bc2e4bee`: identical on every scorer recorded in STATE_33 D12; judges non-null on all 5 rows (pass bar met).
Trace check (all 5 traces): root `fpac_soil_agent`/AGENT, inputs `{"request": ...}`, outputs contain the answer, every TOOL span parented to the root; no spurious `read_resource`.
