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
| 2 | User | 41.2.1 | done (pushed through 226f283) |
| 3 | Local agent | 41.3.1 | done (6e1d381); file-mode fix in 41.3.2 rework |
| 3 | Local agent -> Databricks | 41.3.2 | rework (45ed0be, 9c1567f; STOP review: corrections requested) |
| 3 | Local agent -> Databricks | 41.3.3 | pending (after 41.3.2 rework) |
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

- **Status:** done. The user pushed `feature/agent-app-map1` (7c1f2b8, e430767, 7a0c0c1, 69814cc, 226f283); the local agent pulled and resumed at wave 3.
- **Check:** wave 3 commits 6e1d381..9c1567f sit on top; Databricks clone and origin both at 9c1567f (`git status -sb` even).

## 41.3.1

- **Status:** done, commit 6e1d381 `feat(agent-app): vendor full pinned chat template` (local agent). Scope: `frontend/**` plus `planning/tasks/41.3.1.todo.md` only.
- **Parity (orchestrator review, `git ls-tree` vs upstream 0e57297 fetched to /tmp):**
  - Equal hashes: `client` c7e05c07, `server` c9374ad3, `packages` 1a741bc8, `package.json` 89d5baa6, `package-lock.json` 664a2674 (byte-for-byte), `knip.json` bd613a55 (upstream file, kept), `biome.jsonc`, `tsconfig.json`, `drizzle.config.ts`, `.gitignore`, `.env.example`, `README.md`.
  - `scripts/` tree fde463e2 != upstream d3160316: blobs identical, but 5 files lost +x (`cleanup-database.sh`, `get-pghost.sh`, `quickstart.sh`, `reset-database.ts`, `start-app.sh`). Fixed in the 41.3.2 rework.
  - Excluded files absent (`.claude/`, `CLAUDE.md`, `tests/`, `playwright.config.ts`, `app.yaml`, `databricks.yml`, `manifest.yaml`). No shims.
  - `node_modules` ignored by `frontend/.gitignore`; `dist/` by app `.gitignore` L17.
- **Local checks (agent report):** `npm ci` and `npm run build` passed; ephemeral migration skip logged.
- **Deviations:** todo file has no checkboxes or execution report.

## 41.3.2

- **Status:** rework. Commits 45ed0be `fix(agent-app): run the full vendored chat template`, 9c1567f `fix(agent-app): narrow frontend validation gate` (local agent). STOP review by orchestrator: corrections requested; the user directed the Databricks orchestrator to do the rework and 41.3.3.
- **Pass:** `start_app.py` uses `npm ci`; missing `frontend/package.json` sets `no_ui=True` before `API_PROXY`; `FRONTEND_READY` matches upstream `Backend server is running on http://localhost` (re.IGNORECASE); ports and `CHAT_APP_PORT` unchanged. CI on Node 22, cache on `frontend/package-lock.json`, separate Python and frontend steps, no `--write`. `app-check` = `app-lint app-test`.
- **Fail, lint gate:** `npx biome lint --only=correctness/noUnusedVariables` cannot fail (`biome.jsonc` sets that rule to `warn`; biome exits 0 on warnings).
- **Fail, typecheck:** root `npx tsc --noEmit` is the wrong project (root `tsconfig.json` has no `include` and no `@/*` alias; only `client/tsconfig.json` maps `@/*`). Upstream has no typecheck script; its CI runs only `npm ci` + `npm run lint`.
- **Not met:** `make app-frontend-check` never ran end to end (`npm ci` stalled locally). Smoke test blocked (no credentials); chat and `/api/config` move to 41.4.1, `--no-ui` still required.
- **Python (orchestrator, /tmp copy, `MLFLOW_TRACKING_URI=databricks`):** 61 passed. Ruff 0.17.1 check (`--extend-ignore EXE002`) and format check clean on app lint paths.
- **Gotchas:** upstream `server` `start` script uses `NODE_ENV=production node ...` (POSIX); it fails under Windows cmd.exe. Commit messages conventional, no plan numbers.

## 41.3.3

## 41.4.1
