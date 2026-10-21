# State 33 — Databricks-Native Eval Tier (T0 + T1)

Plan: `planning/EXECUTION_PLAN_33.md` · Template: `planning/PROMPT_TEMPLATE_33.md` · Branch: `feat/databricks-eval1`

## Baseline (record before wave 1)

- [x] Branch is `feat/databricks-eval1` (HEAD 7b281cb); staged research note, office-hours questions, and Plan 33 artifacts committed (`docs(planning):`).
- [x] Offline suite (2026-10-21, serverless, `UV_PROJECT_ENVIRONMENT=/tmp/fpac-venv`): **376 passed, 1 skipped, 22 deselected**. The repo `.venv` on `/Workspace` is not used; set `UV_PROJECT_ENVIRONMENT=/tmp/fpac-venv PYTHONDONTWRITEBYTECODE=1` and pass `-p no:cacheprovider`.
- [x] `uv run ruff check .` → 59 × EXE002 only (Workspace FS reports every file as executable; not a code defect). `uv run ruff check . --extend-ignore EXE002` → All checks passed. Wave gates use `--extend-ignore EXE002` on Workspace.
- [x] `uv run ruff format --check .` → 385 files already formatted
- [ ] Pi live baseline (laptop, optional): `make test-eval` → ___ / 20 PASS
- [x] Serverless facts re-confirmed: MLflow 3.12.0 installed; endpoints `databricks-gpt-5-6-luna`, `databricks-claude-sonnet-4-5` READY

## Wave board

| Wave | Task | Title | Status | Worker | Result |
|---|---|---|---|---|---|
| 1 | 33.1.1 | Common matching, pytest path, eval-databricks group | pending | | |
| 1 | 33.1.2 | Dataset encoding repair, manifest wording | pending | | |
| 2 | 33.2.1 | Pi harness alignment | pending | | |
| 2 | 33.2.2 | T0 contract tests | pending | | |
| 3 | 33.3.1 | Dataset v2 schema and loader | pending | | |
| 4 | 33.4.1 | Ground truth for five rows (LIVE, user sign-off) | pending | | |
| 5 | 33.5.1 | T1 agent loop with tracing | pending | | |
| 5 | 33.5.2 | T1 scorers | pending | | |
| 6 | 33.6.1 | T1 runner, notebook, 5-case serverless check (LIVE step) | pending | | |
| 6 | 33.6.2 | Documentation and Make target | pending | | |

## Wave gates

| Wave | Offline pytest | ruff check | ruff format | eval-databricks tests | Notes |
|---|---|---|---|---|---|
| 1 | | | | n/a | |
| 2 | | | | n/a | |
| 3 | | | | n/a | |
| 4 | | | | n/a | user sign-off: |
| 5 | | | | | |
| 6 | | | | | T1 run ID / experiment / per-scorer counts: |

Pre-merge manual: Pi live `make test-eval` on laptop → ___

## Task reports

<!-- Workers append `## <task-id>` sections here (<=15 lines each). -->
