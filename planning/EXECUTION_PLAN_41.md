# EXECUTION PLAN 41: Fix the Plan 40 Agent App Frontend Vendoring Review Findings

## Goal & Scope

**Goal:** Fix the problems found in the two-axis review of PR branch `feature/agent-app-map1` (Plan 40) before it merges, in the order recommended by `planning/RESEARCH_AGENT_APP_FRONTEND_VENDORING_FIXES.md`. First, Databricks-side Python fixes (findings F7-F9). Then you push. Then the local agent re-vendors the full chat template and repairs the launcher, Makefile, CI and ADR (F1-F6, F11). Finally, a deployed check on the existing agent app (F10). The deployed agent app must keep working when the branch merges to `main`.

**In scope:**

- F7: restore `get_session_id` in both handlers; remove `sanitize_custom_inputs`; tests for the stream path and the trace session.
- F8: make the route tests self-contained; remove the meaningless route-order assertion; fix or drop the unknown-route test.
- F9: correct the Plan 40 evidence files (exact adapter loss; route-first matching).
- F1, F2, F11: vendor the whole `e2e-chatbot-app-next` folder at upstream commit `0e572976459aafa3d41047067382cb9a6c015d52` with its own lockfile; no shims.
- F3, F4, F5: frontend check commands; `npm ci` and the no-UI fallback in `start_app.py`; Python-only `app-check`; CI on Node 22.
- F6: ADR renumbered to 0015 in MADR format, plus the index row and app docs.
- F10: deployed check on the existing app, using a temporary switch of its git source branch.

**Out of scope:**

- Any map, AOI, `custom_inputs`/`custom_outputs` feature, basemap or proxy work (Plan 40's M2+ remains blocked on R6).
- Upgrading the vendored template beyond commit 0e57297.
- Lakebase chat history, feedback UI enablement, or OBO auth changes.
- MCP server code, root `src/`, and `tests/` (other than running `make check`).
- Editing `planning/EXECUTION_PLAN_40.md`, `planning/STATE_40.md`, `planning/PROMPT_TEMPLATE_40.md`, or any other frozen plan.
- Merging the PR, and a separate test app (see D6).

**Verbatim constraints from the user:**

- "create a plan following your suggested order"
- "use plan number 41"
- "single executor" (read as: one plan with executor-tagged waves; see D2)

## Reconnaissance Log

Captured 2026-10-28 on Databricks serverless, in the personal clone `/Workspace/Users/andrew.g.brown@usda.gov/fpac-soil-mcp`.

- Branch `feature/agent-app-map1`, 1 commit ahead of origin (7c1f2b8, research note). Highest plan on any remote branch = 40.
- Sizes: `agent_server/agent.py` 167, `agent_server/history.py` 64, `agent_server/utils.py` 59, `agent_server/start_server.py` 33, `scripts/start_app.py` 306, `tests/test_aoi_handoff.py` 66, `tests/test_custom_routes.py` 25, `planning/evidence/40.2.1-aoi.md` 53, `planning/evidence/40.2.2-routes.md` 48, `Makefile` 97, `.github/workflows/ci.yml` 139.
- App test baseline: **60 passed** only with `env -u MLFLOW_TRACKING_URI`. With the serverless default (`MLFLOW_TRACKING_URI=databricks`), collecting `tests/test_custom_routes.py` fails with `MlflowException: experiment_ids must be a list of strings`. The cause is that the module-level `from agent_server.start_server import app` runs `setup_mlflow_git_based_version_tracking()` (`start_server.py` imports it from `mlflow.genai.agent_server`).
- Ruff (`--extend-ignore EXE002`) passes on `agent.py`, `history.py`, `tests/`.
- `sanitize_custom_inputs` is referenced only in `agent.py` L33/L142/L157, `history.py` L12, `tests/test_aoi_handoff.py` L7/L19/L23-24, and `planning/evidence/40.2.1-aoi.md` L21.
- The reference stream-handler test pattern is the `patched` fixture plus `_run_stream()` in `tests/test_agent_mcp_wiring.py` (L35-L68, L125).
- npm is not usable on serverless (dangling `/usr/local/bin/npm` symlink). All frontend validation must run locally.
- Upstream facts, MLflow proxy behaviour, and the Apps runtime (Node 22.16) are cited in the research note.

## Decision Log

1. **D1, 2026-10-28, numbering:** Plan number 41.
2. **D2, 2026-10-28, structure:** One plan with four executor-tagged waves and a single `STATE_41.md`. Wave 1 = Databricks, wave 2 = user push gate, wave 3 = local agent, wave 4 = Databricks/user deployed check.
3. **D3, 2026-10-28, route-test environment:** Make `tests/test_custom_routes.py` self-contained by patching `setup_mlflow_git_based_version_tracking` to a no-op (or setting a local tracking URI) before importing `agent_server.start_server`. Do not change app runtime code for this.
4. **D4, 2026-10-28, session id:** Restore `get_session_id(request)` in both handlers. Delete `sanitize_custom_inputs` and its two unit tests. Keep the test that `custom_inputs` never reach `Runner.run`, add a stream-handler version, and add a test that `context.conversation_id` becomes `mlflow.trace.session`. Update the 40.2.1 evidence to match.
5. **D5, 2026-10-28, local wave split:** Three serial tasks: 41.3.1 full template (F1, F2, F11; keep upstream `public/` images for exact parity), 41.3.2 launcher/Makefile/CI plus local smoke test (F3-F5), 41.3.3 docs (F6). **STOP** after 41.3.2 for your review before docs.
6. **D6, 2026-10-28, deployed check:** Temporarily point the existing app's git source at `feature/agent-app-map1`, redeploy, check, then restore `main` and redeploy. No separate test app.
7. **D7, 2026-10-28, acceptance and commits:**
   - **Wave 1:** one commit per task on the branch, no push. Each task passes app pytest in the normal serverless environment (no `env -u` workaround) with 0 failures (about 60 tests; exact count reported), plus ruff check and format check on the lint paths.
   - **Wave 2:** you push (this includes 7c1f2b8).
   - **Wave 3:** one commit per task. Each passes `make app-check` and `make app-frontend-check`; root `make check` runs once at wave end; the 41.3.2 smoke test is recorded in STATE. The local agent pushes only after your approval at the STOP.
   - **Wave 4:** results go in STATE and `main` is restored as the git source. A failure returns to wave 3; it is never recorded as a pass.
   - **Frozen:** Plan 40 plan, state and template files stay frozen; only the Plan 40 evidence files may be corrected.

## Wave & Dependency Table

| Wave | Executor | Task | Title | Files in scope | Depends on |
|---|---|---|---|---|---|
| 1 | Databricks | 41.1.1 | Restore trace session id and remove the custom-input sanitizer | `agent_server/agent.py`, `agent_server/history.py`, `tests/test_aoi_handoff.py`, `planning/evidence/40.2.1-aoi.md` | none |
| 1 | Databricks | 41.1.2 | Make route tests self-contained and meaningful | `tests/test_custom_routes.py`, `planning/evidence/40.2.2-routes.md` | none |
| 2 | User | 41.2.1 | Push gate | none (git push only) | 41.1.1, 41.1.2 |
| 3 | Local agent | 41.3.1 | Vendor the full chat template at 0e57297 | `frontend/**` | 41.2.1 |
| 3 | Local agent | 41.3.2 | Launcher, Makefile and CI for the full template, plus smoke test (**STOP after**) | `scripts/start_app.py`, `Makefile`, `.github/workflows/ci.yml`, `.gitignore` (app) | 41.3.1 |
| 3 | Local agent | 41.3.3 | ADR 0015 and app docs | `docs/decisions/0014-vendored-agent-app-frontend.md` -> `0015-...`, `docs/decisions/README.md`, app `README.md`, app `AGENTS.md` | 41.3.2 |
| 4 | Databricks / user | 41.4.1 | Deployed check on the existing app | `planning/STATE_41.md` only | 41.3.3 |

The app paths are relative to `apps/agent-fpac-soil-openai-sdk/` unless they start with `planning/`, `docs/`, `Makefile` or `.github/`.

Wave 1 tasks have pairwise-disjoint files. On Databricks there are no sub-agents, so the orchestrator runs them one after another and commits each separately. Wave 3 tasks are serial by design. `planning/STATE_41.md` is written by the orchestrator only.

## Hazards

- **Databricks Git folder:** run `git status -sb` and `git diff` immediately before every commit. The Git folder UI has switched HEAD and reverted working files before. `git commit --amend` is blocked; make a new commit instead.
- **Databricks writes:** edit files only through workspace file tools; shell writes under `/Workspace` are blocked. To run tests, copy the working tree (not `git archive`, which drops uncommitted edits) to `/tmp`, excluding `frontend/` and `.venv/`, then use `UV_PROJECT_ENVIRONMENT=/tmp/appvenv PYTHONDONTWRITEBYTECODE=1 uv run --frozen --python 3.11 pytest -p no:cacheprovider tests -q`. Ruff on `/Workspace` needs `--extend-ignore EXE002`.
- **Route-first matching:** the MLflow 3.17.1 chat proxy serves any registered route before forwarding; route order is irrelevant. Unknown `/api/*` paths are forwarded to `CHAT_APP_PORT` (503 on connection error).
- **Session id:** the upstream UI sends `context.conversation_id`, never `custom_inputs.session_id`. Do not reintroduce a sanitizer between `get_session_id` and `mlflow.update_current_trace`.
- **Template layout:** the upstream server serves `../../client/dist` relative to `server/dist`. Keep `client/`, `server/`, `packages/` as siblings under `frontend/`. Do not flatten.
- **Lockfile:** use the upstream root `package-lock.json` byte-for-byte; never regenerate from the client alone. Root `lint` uses `--write --unsafe` and must not run in CI.
- **Apps runtime:** Node 22.16, and no auto-install for a non-root `package.json`; the launcher must keep running npm itself. Egress to `registry.npmjs.org` is assumed from current `main` behaviour.
- **Production impact (wave 4):** while the git source points at the branch, real users get the branch build. Keep the window short and always restore `main`.
- **Privacy:** no raw AOI coordinates, WKT/GeoJSON, bounding boxes or parcel properties anywhere (ADR 0010; Plan 40 D6).
- **ADR numbering:** 0014 is taken on `origin/feat/sdv-metadata-contract`. Use 0015 and re-check before committing.

## Task Specifications

### 41.1.1 -- Restore trace session id and remove the custom-input sanitizer

**Executor:** Databricks orchestrator (inline).

**Files in scope**

- Must edit: `apps/agent-fpac-soil-openai-sdk/agent_server/agent.py`, `apps/agent-fpac-soil-openai-sdk/agent_server/history.py`, `apps/agent-fpac-soil-openai-sdk/tests/test_aoi_handoff.py`, `planning/evidence/40.2.1-aoi.md`.
- Can create: `planning/tasks/41.1.1.todo.md`.
- Temp: `/tmp/` test copy only.
- Do not touch: `agent_server/utils.py`, `start_server.py`, frontend, other tests, Plan 40 plan/state files.

**Depends on:** none.

**Specification:**

1. In `agent.py`, re-import `get_session_id` from `agent_server.utils` and use `if session_id := get_session_id(request):` in both `invoke_handler` and `stream_handler`. Drop `sanitize_custom_inputs` from the `agent_server.history` import.
2. Delete `sanitize_custom_inputs` and the now-unused `from typing import Any` from `history.py`, so the file again matches its upstream-synced form.
3. In `test_aoi_handoff.py`:
   - Delete the two sanitizer tests.
   - Keep `test_invoke_does_not_pass_custom_inputs_to_model`.
   - Add a stream-handler counterpart asserting no `coordinates` reach `Runner.run_streamed` input.
   - Add a test that a request with `context={"conversation_id": "conv-1"}` calls `mlflow.update_current_trace(metadata={"mlflow.trace.session": "conv-1"})` for invoke and stream (one test may be parametrized).
   - Use the `patched` / `_run_stream` pattern from `test_agent_mcp_wiring.py` as the reference.
4. Update `planning/evidence/40.2.1-aoi.md`:
   - Replace the sanitizer paragraph with "session id comes from `get_session_id` (context first)".
   - Record the exact adapter loss: upstream template at 0e57297 has no `custom_inputs`/`custom_outputs` handling in `server/`, `packages/`, `client/src`, and sends only `context.conversation_id`/`user_id`. Cite the research note.
   - Keep the "AOI integration is blocked" result unchanged.

**Grep anchors:** `sanitize_custom_inputs`, `get_session_id`, `update_current_trace`, `Runner.run_streamed`, `def patched`, `def _run_stream`, `mlflow.trace.session`.

**Acceptance:**

- `grep -rn sanitize_custom_inputs apps/` returns nothing.
- App pytest from the `/tmp` copy, without unsetting `MLFLOW_TRACKING_URI`, is green for `tests/test_aoi_handoff.py tests/test_agent_mcp_wiring.py`. A full-suite run may still fail only on the known `test_custom_routes.py` collection issue until 41.1.2 lands.
- `uv run ruff check --extend-ignore EXE002` and `uv run ruff format --check` on `agent_server/agent.py agent_server/history.py tests` both pass.
- Commit: `fix(agent-app): restore conversation-based trace session id`.

### 41.1.2 -- Make route tests self-contained and meaningful

**Executor:** Databricks orchestrator (inline).

**Files in scope**

- Must edit: `apps/agent-fpac-soil-openai-sdk/tests/test_custom_routes.py`, `planning/evidence/40.2.2-routes.md`.
- Can create: `planning/tasks/41.1.2.todo.md`.
- Do not touch: `start_server.py`, `conftest.py`, other tests, app runtime code (D3).

**Depends on:** none.

**Specification:**

1. Before `agent_server.start_server` is imported, make `setup_mlflow_git_based_version_tracking` a no-op. For example, patch the attribute on `mlflow.genai.agent_server` at module top before the import, or import inside a module-scoped fixture under `monkeypatch`/`pytest.MonkeyPatch.context()`. The test must not call any live tracking server, whatever `MLFLOW_TRACKING_URI` is set to.
2. Remove the `/invocations` route-order assertion; keep a registration assertion.
3. Keep the 200 `{"status":"ok"}` probe test.
4. Replace the unknown-route test with one that patches the AgentServer proxy client's `send` to a mock and asserts `/api/geo/not-a-route` is forwarded to the chat app (the mock is called), not served by `geo_health`. If the proxy client can't be reached cleanly, delete the test and record why in the todo notes.
5. In `planning/evidence/40.2.2-routes.md`, replace the ordering bullet with the route-first matching rule (MLflow 3.17.1 `server.py` L167-168) and keep the procedure. State that the deployed probe is pending in Plan 41 wave 4.

**Grep anchors:** `setup_mlflow_git_based_version_tracking`, `enable_chat_proxy`, `proxy_client`, `paths.index`, `not-a-route`.

**Acceptance:**

- Full app pytest from the `/tmp` copy, **without** unsetting `MLFLOW_TRACKING_URI`, passes with 0 failures and 0 errors. Expected count = 60 − 2 deleted sanitizer tests + the tests added in 41.1.1 ± any route test removed in 41.1.2. Report the exact count and the arithmetic.
- Ruff check and format check pass on the lint paths.
- Commit: `test(agent-app): isolate custom route tests from live MLflow`.

### 41.2.1 -- Push gate

**Executor:** User.

**Spec:** Review the wave 1 commits, then push `feature/agent-app-map1` (this includes 7c1f2b8, 41.1.1 and 41.1.2). Then tell the local agent to pull and resume at wave 3 from `planning/STATE_41.md`.

**Acceptance:** `git status -sb` shows the branch even with origin; STATE_41 wave board marks 41.2.1 done.

### 41.3.1 -- Vendor the full chat template at 0e57297

**Executor:** Local agent (Windows, Node 22, npm).

**Files in scope**

- Must edit / replace: `apps/agent-fpac-soil-openai-sdk/frontend/**`.
- Can create: `planning/tasks/41.3.1.todo.md`; untracked staging under `apps/agent-fpac-soil-openai-sdk/.development/` (removed before reporting).
- Do not touch: `scripts/start_app.py`, `Makefile`, CI, docs, `agent_server/`, tests.

**Depends on:** 41.2.1.

**Specification:**

1. Replace `frontend/` with the contents of `databricks/app-templates` folder `e2e-chatbot-app-next` at commit `0e572976459aafa3d41047067382cb9a6c015d52`, keeping its layout:
   - **Keep:** root `package.json`, root `package-lock.json` (byte-for-byte), `client/`, `server/`, `packages/`, `scripts/`, `biome.jsonc`, `tsconfig.json`, `drizzle.config.ts`, `.gitignore`, `.env.example`, `README.md`.
   - **Exclude:** `.claude/`, `CLAUDE.md`, `tests/`, `playwright.config.ts`, `app.yaml`, `databricks.yml`, `manifest.yaml`.
2. Keep upstream `client/public/` images (D5).
3. No local shims: `client/src/types/databricks-chatbot-packages.d.ts` and `client/src/vendor/chatbot-core-errors.ts` must not exist, and `client/vite.config.ts`, `client/tsconfig.json` and `client/package.json` equal upstream.
4. Verify parity: the tree hash of `frontend/client` should equal `c7e05c0787909bc6e0b79adf2f162fd0bc2a8edd`. If line-ending normalisation prevents a hash match, show a file-by-file content diff with no differences instead.
5. No map behaviour.

**Grep anchors:** upstream `package.json` `workspaces`, `server/src/index.ts` `Backend server is running`, `client/dist`.

**Acceptance:**

- `cd apps/agent-fpac-soil-openai-sdk/frontend && npm ci && npm run build` passes. `build` runs `db:migrate`, which must log the ephemeral-mode skip with no Postgres variables set.
- `git ls-files apps/agent-fpac-soil-openai-sdk/frontend` shows the upstream layout and no shims.
- `node_modules/` and `dist/` are untracked.
- Commit: `feat(agent-app): vendor full pinned chat template`.

### 41.3.2 -- Launcher, Makefile and CI for the full template, plus smoke test (STOP after)

**Executor:** Local agent.

**Files in scope**

- Must edit: `apps/agent-fpac-soil-openai-sdk/scripts/start_app.py`, `Makefile`, `.github/workflows/ci.yml`; `apps/agent-fpac-soil-openai-sdk/.gitignore` only if build outputs are not already ignored.
- Can create: `planning/tasks/41.3.2.todo.md`.
- Do not touch: `frontend/**` (except reading), docs/ADR, `agent_server/`.

**Depends on:** 41.3.1.

**Specification:**

1. `start_app.py`:
   - Run `npm ci` instead of `npm install`.
   - If `frontend/package.json` is missing, print a warning, set `self.no_ui = True`, and skip `API_PROXY`. This restores `main`'s backend-only fallback.
   - Keep `npm run build`, `npm run start`, `FRONTEND_READY` and the ports unchanged. The upstream log "Backend server is running on http://localhost" already matches under `re.IGNORECASE`.
2. `Makefile`:
   - `app-check` = `app-lint app-test` (Python only).
   - `app-frontend-check` runs in `frontend/`: `npm ci && npx biome lint && npm run build`, plus a typecheck command proven to pass on the full workspace. Record it, or record "no workspace typecheck" with the reason. Never use the upstream `--write` lint scripts.
   - Update the `help` text.
3. CI: `actions/setup-node` `node-version: "22"`; `cache-dependency-path` pointing at `apps/agent-fpac-soil-openai-sdk/frontend/package-lock.json`; keep separate steps for `make app-test`/`app-lint` and `make app-frontend-check`.
4. **Smoke test** (record in the report). Run `uv run start-app` locally with Databricks auth. Check that:
   - the frontend log has "Backend server is running"
   - `GET http://localhost:8000/` returns the UI
   - `GET /api/config` returns 200
   - `GET /api/geo/health` returns 200 `{"status":"ok"}`
   - one chat turn against the deployed MCP server succeeds

   Also run `uv run start-app --no-ui` once to confirm the backend-only path still works.

**Grep anchors:** `npm`, `install`, `no_ui`, `API_PROXY`, `FRONTEND_READY`, `app-frontend-check`, `setup-node`.

**Acceptance:**

- `make app-check` and `make app-frontend-check` pass.
- Smoke results recorded.
- Commit: `fix(agent-app): run the full vendored chat template`.
- **STOP**: report to the user and wait for approval before 41.3.3.

### 41.3.3 -- ADR 0015 and app docs

**Executor:** Local agent.

**Files in scope**

- Must edit: `git mv docs/decisions/0014-vendored-agent-app-frontend.md docs/decisions/0015-vendored-agent-app-frontend.md` (then edit), `docs/decisions/README.md`, `apps/agent-fpac-soil-openai-sdk/README.md`, `apps/agent-fpac-soil-openai-sdk/AGENTS.md`.
- Can create: `planning/tasks/41.3.3.todo.md`.
- Do not touch: other ADRs, root `AGENTS.md` (unless an existing pointer names the ADR number), Plan 40 files.

**Depends on:** 41.3.2 and your approval at the STOP.

**Specification:**

1. ADR 0015:
   - YAML frontmatter and sections in the ADR 0013 style (`id`, `title`, `status: Accepted`, `date`, `authors`, `supersedes`, `superseded_by`, `source_context: "EXECUTION_PLAN_40, EXECUTION_PLAN_41"`; Context, Decision Drivers, Considered Options, Decision Outcome, Validation & Compliance).
   - Record the upstream **commit** 0e57297 and full-folder scope, the excluded files, the update procedure (re-copy + upstream lockfile + checks), and that `app-check` stays Python-only.
2. Add a 0015 row to the README index.
3. App README and AGENTS: update the pin wording (commit, not tree), the frontend layout, the commands, and the Node 22 requirement.
4. Re-check that 0015 is unused on all remote branches before committing.

**Grep anchors:** `0014`, `c7e05c07`, `tree`, `npm run lint`, `typecheck`.

**Acceptance:**

- `git grep -n "0014-vendored\|c7e05c07"` returns nothing outside `planning/` history files.
- Root `make check` passes once.
- Commit: `docs(agent-app): record vendored chat template decision`.
- Then push, after your approval.

### 41.4.1 -- Deployed check on the existing app

**Executor:** Databricks orchestrator, with you doing the UI steps.

**Files in scope:** `planning/STATE_41.md` only. App configuration changes are manual and reverted.

**Depends on:** 41.3.3 pushed.

**Specification:**

1. In the Apps UI, set `agent-fpac-soil-openai-sdk` git source branch to `feature/agent-app-map1` and redeploy.
2. Check:
   - deployment SUCCEEDED, and the app logs show npm ci/build and "Backend server is running"
   - `/` loads in the browser
   - `/api/config` returns 200
   - `/api/geo/health` returns 200
   - one chat turn works (for example, the POINT-01 prompt)
   - the MLflow trace for that turn has `mlflow.trace.session` equal to the chat ID
3. Restore git source branch `main` and redeploy; confirm SUCCEEDED.
4. Record the deployment IDs, check results and the trace ID in STATE_41.

**Acceptance:**

- All checks pass and `main` is restored.
- Any failure is recorded as failed, `main` is restored, and the fix returns to wave 3. It is never marked done.
