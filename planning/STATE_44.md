# Orchestration 44 State

## Baseline

- **Repository:** workspace clone `/Workspace/Users/andrew.g.brown@usda.gov/fpac-soil-mcp`; edits and commits happen there; gates run in `/tmp` clones (D8).
- **Branch:** `feature/agent-app-map2` off `origin/main` 06525de (PR #75 and PR #74 merged); plan commits 5b5ed9a, 3ca93a1 are on `origin/feature/agent-app-map2` (in sync at baseline).
- **Plan date:** 2026-11-04; approved by the user 2026-11-04.
- **Agent app:** `agent-fpac-soil-openai-sdk` RUNNING, git `main`, `auto_deploy: true`, active deployment 06525de.
- **MCP server app:** `mcp-fpac-soil` RUNNING, deployed 2026-10-21 from `/Workspace/Users/Groups/team-03/fpac-soil-mcp` (predates Plan 43).
- **Last known suite results (from STATE_43 and the PR #75 gate; not yet re-run on 06525de):** root offline 599+ passed / 3 skipped; live 41 passed / 1 pre-existing SDA "kill state" failure / 3 skipped; frontend biome 0 errors / 10 warnings, client build OK with the MapLibre worker asset.
- [x] **Pre-wave-1 baseline on 06525de** (fresh `/tmp/p44`, 2026-11-04):
  - root `make check`: rc 0; ruff + format clean; 626 passed / 3 skipped / 45 deselected.
  - `make test-live`: rc 0; 43 passed / 3 skipped (the STATE_43 SDA "kill state" failure did not recur).
  - `make app-check`: rc 0; ruff clean; 135 passed.
  - `make app-frontend-check`: rc 0; `npm ci` 573 packages; biome 0 errors / 10 warnings; build OK, emits `maplibre-gl-worker-*.js`.
  - Node v22.20.0, npm 10.9.3 via `databricks/bootstrap-serverless.sh`.

## Wave board

| Wave | Executor | Task | Status |
|---|---|---|---|
| 1 | Genie Code | 44.1.1 | done |
| 1 | User + Genie Code | 44.1.2 | waiting for user browser check |
| 1 | gate | root check, app-check | pending |
| 2 | Genie Code | 44.2.1 | pending |
| 2 | Genie Code | 44.2.2 | pending |
| 2 | gate | root check, app-check, test-live | pending |
| 3 | Genie Code | 44.3.1 | pending |
| 3 | Genie Code | 44.3.2 | pending |
| 3 | gate | root check, app-check, test-live | pending |
| 4 | Genie Code | 44.4.1 | pending |
| 4 | gate | root check, app-check, test-live | pending |
| 5 | Genie Code | 44.5.1 | pending |
| 5 | User + Genie Code | 44.5.2 | pending |
| 5 | gate | root check, app-check | pending |
| 6 | Genie Code | 44.6.1 | pending |
| 6 | gate | root check, app-check, app-frontend-check | pending |
| 7 | Genie Code | 44.7.1 | pending |
| 7 | gate | root check, app-check, app-frontend-check | pending |
| 8 | User + Genie Code | 44.8.1 | pending |
| 8 | Genie Code | 44.8.2 | pending |
| 8 | gate | root check, app-check, app-frontend-check | pending |
| 9 | Genie Code | 44.9.1 | pending |
| 9 | Genie Code | 44.9.2 | pending |
| 9 | gate | root check, app-check, app-frontend-check | pending |
| 10 | User + Genie Code | 44.10.1 | pending |
| 11 | Genie Code | 44.11.1 | pending |
| 12 | Genie Code + User | 44.12.1 | pending |
| 12 | gate | all suites | pending |

## Task Reports

<!-- Append one report per task (<=15 lines): status, files, commands/results, deviations, gotchas, commit. -->

## 44.1.1

- **Status:** done. Commit 3d9d9b6 (`docs(decisions): propose the server map result contract for the analyze tools`).
- **Files:** `docs/decisions/0017-server-map-result-contract.md` (new, 223 lines, `Proposed`); `docs/decisions/README.md` (index row, Databricks Delivery era sentence); `planning/tasks/44.1.1.todo.md`.
- **Checks:** `grep -n 0017 docs/decisions/README.md` shows the row and link; link target exists; no coordinate-like numbers in the ADR. Root `make check` does not read `docs/` (wave gate below).
- **Deviations:** none.
- **Gotchas for 44.2.1:** legend values follow `categorize_farmland_class` (7 values incl. `conditional_prime`, `unmapped`); those two take the deployed `farmlandClasses.ts` colours. Patterns enum: `solid`, `diagonal_hatch`, `cross_hatch`, `dot_stipple`, `outline`, `dashed_outline`. `bounds` is null when no layer is inline. The size cap drops whole layers from the end of the list (`delivery: omitted`, `truncated: true`, warning in `map.warnings`); it never drops part of a layer. Layer `authority` values: `user_input`, `machine_estimate`, `reference_data`. `data_vintage` nullable (no SSURGO vintage without an extra query). The section 4 mapping table is what 44.4.1 asserts.

## 44.1.2

- **Status:** part 1-2 done (serverless metadata and requests with the app `Origin`); part 3 waiting for the user's browser-console run from the deployed app.
- **Files:** `planning/evidence/44.1.2-overlays.md` (new).
- **Findings so far:** all four requests succeed with CORS for the app origin (SSURGO `*`; TIGERweb echoes the origin). SSURGO GetFeatureInfo supports only `text/plain`/`text/html`/`gml2` and returns `mukey`/`musym`, not farmland class. Sample urban area 5694 vertices (over the 2000 cap); sample county 1050.
- **Gotchas:** TIGERweb CORS needs simple GETs (preflight gets no CORS headers). Browser CSP of the app is not covered by the server-side probe; the browser run checks it.

