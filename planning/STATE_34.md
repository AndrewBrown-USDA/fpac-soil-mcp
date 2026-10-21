# State 34 — PR Review Remediation for the Databricks Eval Tier

Plan: `planning/EXECUTION_PLAN_34.md` · Template: `planning/PROMPT_TEMPLATE_34.md` · Branch: `feat/databricks-eval1`

## Baseline (record before wave 1)

- [ ] Branch is `feat/databricks-eval1`, tree clean (planning HEAD `3db89a4`); Plan 34 artifacts committed (`docs(planning):`).
- [ ] Offline suite with group: `UV_PROJECT_ENVIRONMENT=/tmp/fpac-venv PYTHONDONTWRITEBYTECODE=1 uv run --group eval-databricks pytest -p no:cacheprovider -q` → ___ passed, ___ skipped, ___ deselected
- [ ] Exact no-group suite: `UV_PROJECT_ENVIRONMENT=/tmp/fpac-venv-nogroup PYTHONDONTWRITEBYTECODE=1 uv run --exact pytest -p no:cacheprovider -q` → ___ passed, ___ skipped
- [ ] `uv run ruff check . --extend-ignore EXE002` → ___
- [ ] `uv run ruff format --check .` → ___ files already formatted
- [ ] Reference live run for comparison: v2 default run `bc2e4bee` (from STATE_33 D12 results)

## Wave board

| Wave | Task | Title | Status | Worker | Result |
|---|---|---|---|---|---|
| 1 | 34.1.1 | Digit-boundary keyword matching | pending | | |
| 1 | 34.1.2 | Reject malformed `test_cases` | pending | | |
| 2 | 34.2.1 | Strict list scoring + `scorer_names` | pending | | |
| 2 | 34.2.2 | Sanitized AGENT span | pending | | |
| 3 | 34.3.1 | Dry run without MLflow | pending | | |
| 3 | 34.3.2 | README corrections | pending | | |
| 4 | 34.4.1 | Full gates + 5-case live run (LIVE) | pending | | |

## Wave gates

| Wave | Offline pytest (group) | No-group (exact) | ruff check | ruff format | Notes |
|---|---|---|---|---|---|
| 1 | | | | | |
| 2 | | | | | |
| 3 | | | | | |
| 4 | | | | | live run id: |

## Task reports

<!-- Workers append `## <task-id>` sections here (<=15 lines each). -->
