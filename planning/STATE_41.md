# Orchestration 41 State

## Baseline

- **Repository:** personal clone `/Workspace/Users/andrew.g.brown@usda.gov/fpac-soil-mcp` (Databricks), plus the local agent's clone for wave 3.
- **Branch:** `feature/agent-app-map1`; 1 commit ahead of origin at plan time (7c1f2b8, research note).
- **Plan:** fix the Plan 40 review findings F1-F11 in the order from `planning/RESEARCH_AGENT_APP_FRONTEND_VENDORING_FIXES.md`.
- **Baseline date:** 2026-10-28.
- **App tests (Databricks /tmp copy):** 60 passed with `env -u MLFLOW_TRACKING_URI`. With the serverless default `MLFLOW_TRACKING_URI=databricks`, collection of `tests/test_custom_routes.py` fails (`experiment_ids must be a list of strings`). 41.1.2 fixes this.
- **Ruff (app lint paths, `--extend-ignore EXE002`):** passed.
- **Frontend checks:** not runnable on Databricks (no npm). Plan 40 STATE reports `npm ci`/lint/typecheck/build passing locally for the client-only layout; this must be re-baselined locally before 41.3.1.
- **Root `make check`:** not re-run at plan time; the local agent runs it at the end of wave 3.
- **Deployed app:** `agent-fpac-soil-openai-sdk` deploys from git source branch `main`.
- **Working-tree status:** capture with `git status -sb` immediately before each wave.

## Wave board

| Wave | Executor | Task | Status |
|---|---|---|---|
| 1 | Databricks | 41.1.1 | pending |
| 1 | Databricks | 41.1.2 | pending |
| 2 | User | 41.2.1 | pending |
| 3 | Local agent | 41.3.1 | pending |
| 3 | Local agent | 41.3.2 | pending (STOP after) |
| 3 | Local agent | 41.3.3 | pending |
| 4 | Databricks / user | 41.4.1 | pending |

## Task reports

<!-- Append one concise report (<=15 lines) under each task heading: status, changed files/line ranges, exact commands and results, deviations, gotchas. -->

## 41.1.1

## 41.1.2

## 41.2.1

## 41.3.1

## 41.3.2

## 41.3.3

## 41.4.1
