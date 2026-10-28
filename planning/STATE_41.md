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
| 1 | Databricks | 41.1.1 | done (7a0c0c1) |
| 1 | Databricks | 41.1.2 | done (69814cc) |
| 2 | User | 41.2.1 | pending |
| 3 | Local agent | 41.3.1 | pending |
| 3 | Local agent | 41.3.2 | pending (STOP after) |
| 3 | Local agent | 41.3.3 | pending |
| 4 | Databricks / user | 41.4.1 | pending |

## Task reports

<!-- Append one concise report (<=15 lines) under each task heading: status, changed files/line ranges, exact commands and results, deviations, gotchas. -->

## 41.1.1

- **Status:** done, commit 7a0c0c1 `fix(agent-app): restore conversation-based trace session id`.
- **Changed:**
  - `agent_server/agent.py` L33-34 (imports), L142, L157 (`get_session_id(request)`).
  - `agent_server/history.py`: removed `sanitize_custom_inputs` and `typing.Any`; now identical to origin/main (`git diff origin/main` empty).
  - `tests/test_aoi_handoff.py`: rewritten. Local `patched` fixture; invoke and stream no-`custom_inputs` tests; `test_conversation_id_sets_trace_session[invoke|stream]`.
  - `planning/evidence/40.2.1-aoi.md`: request path, output path and validation sections corrected (exact adapter loss at 0e57297).
- **Checks:**
  - `pytest tests/test_aoi_handoff.py tests/test_agent_mcp_wiring.py` (/tmp copy, default env): 13 passed.
  - `grep -rn sanitize_custom_inputs apps/`: no matches.
  - Ruff check and format check: clean.
- **Deviations:** none. A planned scratch mutation check (re-applying the old `custom_inputs` session lookup in /tmp) was blocked by tooling. The session test still fails on the old code by construction: with only `context` set, the old lookup never calls `update_current_trace`.
- **Gotchas:** `get_session_id` still falls back to the raw `custom_inputs.session_id` value (upstream behaviour, D4).

## 41.1.2

- **Status:** done, commit 69814cc `test(agent-app): isolate custom route tests from live MLflow`.
- **Changed:**
  - `tests/test_custom_routes.py`: rewritten. A module-scoped `start_server` fixture imports with `setup_mlflow_git_based_version_tracking` patched to a no-op. Tests: registration, 200 probe, and unknown `/api/geo/not-a-route` forwarded via a stubbed `proxy_client.send` to `http://localhost:<chat_app_port>/api/geo/not-a-route`.
  - `planning/evidence/40.2.2-routes.md`: route-first matching rule (MLflow 3.17.1 `server.py` L167-168), deployed probe pending in 41.4.1.
- **Checks:**
  - Full app pytest (/tmp copy): 61 passed with `MLFLOW_TRACKING_URI=databricks`, and 61 passed with it unset.
  - Count: 60 baseline - 2 sanitizer tests + 3 new in 41.1.1 (stream, session invoke, session stream) + 0 net in routes = 61.
  - Ruff check and format check on the app lint paths: clean.
- **Deviations:** none.
- **Gotchas:** only `test_custom_routes.py` imports `agent_server.start_server`. A future test that imports it at module level would bypass the patch.

**Wave 1 complete.** Next: 41.2.1, where you push `feature/agent-app-map1`.

## 41.2.1

## 41.3.1

## 41.3.2

## 41.3.3

## 41.4.1
