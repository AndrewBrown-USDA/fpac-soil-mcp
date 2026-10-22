# Orchestration 36 State

## Baseline

- **Repository:** `D:\workspace\fpac-soil-mcp`
- **Baseline source:** rebased and cleaned branch after reconciliation with latest `main`; preserve unrelated changes.
- **Required baseline commands:** `uv run pytest -m "not live_network"`, `uv run ruff check .`, `uv run ruff format --check .`, harness `node --check` commands.
- **Conditional gates:** `uv run pytest -m live_network` and model/agent evaluations remain opt-in.
- **Worker policy:** maximum two concurrent workers; targeted tests only; full verification serially at wave end.
- **Known pre-existing/unrelated files:** `TODO.md`, `planning/RESEARCH_FEATURE_EVAL_HARNESS_DATABRICKS.md`.
- **Baseline capture:** required in task 36.1.4 before implementation; record exact counts and post-rebase compatibility findings here.

## Wave board

| Wave | Task | Status |
|---|---|---|
| 1 | 36.1.1 | pending |
| 1 | 36.1.2 | pending |
| 1 | 36.1.3 | pending |
| 1 | 36.1.4 | pending |
| 2 | 36.2.1 | blocked on Wave 1 |
| 2 | 36.2.2 | blocked on Wave 1 |
| 2 | 36.2.3 | pending |
| 3 | 36.3.1 | blocked on Wave 2 |
| 3 | 36.3.2 | blocked on Wave 3.1 and 2.2 |
| 4 | 36.4.1 | blocked on Wave 3 |

## Task reports

<!-- Append one concise report under each task heading. Include status, changed files/line ranges, exact validation commands and counts, deviations, and dependent-task gotchas. -->

## 36.1.1

- **Status:** pending
- **Changes:** —
- **Validation:** —
- **Scope:** —
- **Deviations:** —
- **Gotchas:** —

## 36.1.2

- **Status:** pending
- **Changes:** —
- **Validation:** —
- **Scope:** —
- **Deviations:** —
- **Gotchas:** —

## 36.1.3

- **Status:** pending
- **Changes:** —
- **Validation:** —
- **Scope:** —
- **Deviations:** —
- **Gotchas:** —

## 36.1.4

- **Status:** pending
- **Changes:** —
- **Validation:** —
- **Scope:** —
- **Deviations:** —
- **Gotchas:** —

## 36.2.1

- **Status:** pending
- **Changes:** —
- **Validation:** —
- **Scope:** —
- **Deviations:** —
- **Gotchas:** —

## 36.2.2

- **Status:** pending
- **Changes:** —
- **Validation:** —
- **Scope:** —
- **Deviations:** —
- **Gotchas:** —

## 36.2.3

- **Status:** pending
- **Changes:** —
- **Validation:** —
- **Scope:** —
- **Deviations:** —
- **Gotchas:** —

## 36.3.1

- **Status:** pending
- **Changes:** —
- **Validation:** —
- **Scope:** —
- **Deviations:** —
- **Gotchas:** —

## 36.3.2

- **Status:** pending
- **Changes:** —
- **Validation:** —
- **Scope:** —
- **Deviations:** —
- **Gotchas:** —

## 36.4.1

- **Status:** pending
- **Changes:** —
- **Validation:** —
- **Scope:** —
- **Deviations:** —
- **Gotchas:** —
