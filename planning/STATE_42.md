# Orchestration 42 State

## Baseline

- **Repository:** personal clone `/Workspace/Users/andrew.g.brown@usda.gov/fpac-soil-mcp`; work happens in a `/tmp` clone and is fast-forwarded into the workspace clone after each task (D8).
- **Branch:** `feature/agent-app-map1` at 0823c7f (merge of main 6e730b8); 0 behind / 20 ahead of `origin/main`; pushed. PR open, not merged.
- **Baseline date:** 2026-10-30.
- **App tests (`make app-test`, /tmp merge of 421acaf + 6e730b8, same tree as 0823c7f):** 61 passed; `make app-lint` clean.
- **Root `make check`:** ruff clean, 508 files formatted, 597 passed / 3 skipped / 44 deselected.
- **`make app-frontend-check` (421acaf; frontend unchanged since):** `npm ci` 753 packages; biome 588 files, 0 errors, 10 warnings; client and server builds complete.
- **Frontend parity:** 604 files blob- and mode-identical to upstream 0e57297; only ADR 0015 exclusions missing.
- **Deployed app:** `agent-fpac-soil-openai-sdk` `default_git_source.branch = feature/agent-app-map1`, `auto_deploy: true` (user changed it 2026-10-30; `apps get` at plan time showed compute STARTING, no active deployment listed yet). Experiment 517983779529169.
- **PR CI:** green per the user on 421acaf; not re-checked on 0823c7f.
- **Re-baseline:** at the start of wave 1, re-run the three checks on the branch head from a fresh `/tmp` clone and record here.
- **Re-baseline result (2026-10-30, fresh `/tmp/p42` at 9a19b7e, new compute):** `make app-check` lint clean, 61 passed; `make app-frontend-check` `npm ci` 753 packages, biome 588 files 0 errors 10 warnings, client and server builds complete; root `make check` ruff clean, 511 files formatted, 597 passed / 3 skipped / 44 deselected. Matches the baseline above (ruff's formatted-file count differs by clone; not a regression). Node via `/tmp/nodevenv` + `/tmp/nbin` wrappers (npm 10.9.3, node 22.20.0).

## Wave board

| Wave | Executor | Task | Status |
|---|---|---|---|
| 1 | Databricks | 42.1.1 | done (4da95a2) |
| 1 | Databricks | 42.1.2 | done (254910a) |
| 1 | gate | app-check, root check | done (254910a) |
| 2 | Databricks | 42.2.1 | done (8dfb26c) |
| 2 | Databricks | 42.2.2 | done (2a138df) |
| 2 | gate | app-check, app-frontend-check, root check | done (2a138df) |
| 2 | User + Databricks | 42.2.3 | failed step 5 (traces); fix 42.2.4 |
| 2 | Databricks | 42.2.4 (fix) | done (a576f14); deployed re-check pending |
| 3 | Databricks | 42.3.1 | pending |
| 3 | Databricks | 42.3.2 | pending |
| 3 | gate | app-check, app-frontend-check, root check | pending |
| 4 | Databricks | 42.4.1 | pending |
| 4 | gate | app-check, app-frontend-check, root check | pending |
| 5 | User + Databricks | 42.5.1 | pending |
| 5 | Databricks | 42.5.2 | pending |

## Task reports

<!-- Append one concise report (<=15 lines) under each task heading: status, changed files, exact commands and results, deviations, gotchas, commit. No coordinates. -->

## 42.1.1

- Status: done, commit 4da95a2 `docs(agent-app): allow owned local changes to the vendored frontend`.
- Changed: `docs/decisions/0015-vendored-agent-app-frontend.md` (status `Proposed`, `EXECUTION_PLAN_42` in `source_context`, drivers/option 1/outcome reworded to an owned copy from base 0e57297, new Lockfile and Local changes bullets, `### Local changes` empty-state line, 6-step update procedure, merged Negative consequence, scope boundary points to ADR 0016, parity and deployed-check validation updated); app `AGENTS.md` (`frontend/` Find-Things line, Frontend workflow steps 1-5 incl. `npm install --workspace @databricks/chatbot-client --save-exact`); app `README.md` (vendored-frontend paragraph and update sentence).
- Checks: `grep -nE 'No local edits|never regenerate|byte-for-byte|Do not add map' <3 files>` empty; `status: "Proposed"` and `### Local changes` match.
- Deviations: none. Left README "Deploying" (`main` git source) unchanged as the steady-state instruction.
- Gotchas: 42.4.1 fills `### Local changes`; 42.2.2 must list its added/changed frontend paths there too, or leave a note for 42.4.1.

## 42.1.2

- Status: done, commit 254910a `docs(decisions): propose out-of-band AOI screening handoff`.
- Changed: new `docs/decisions/0016-out-of-band-aoi-screening-handoff.md` (`Proposed`, 2026-10-30; context cites Plan 40 R6 evidence and decision; options 1-4; outcome states the 42.2.1 request limits, MCP calls, response shape, `chat_summary` allowlist and exclusions, handoff, privacy and lifecycle; validation lists the 42.2.1 offline tests and 42.5.1 trial); `docs/decisions/README.md` (0015 row `Proposed`, context `40, 41, 42`; new 0016 row; one Databricks Delivery sentence).
- Checks: `status: "Proposed"` matches; both README rows `Proposed`; `grep -nE '[0-9]{1,3}\.[0-9]{4,}'` on ADR 0016 empty.
- Deviations: none.
- Gotchas: 42.2.1 implements the ADR 0016 contract as written; if it must differ (status codes, field names), update ADR 0016 in the same task.

## Wave 1 gate

- Fresh `/tmp/p42g` clone at 254910a: `make app-check` ruff clean, 11 files formatted, 61 passed; root `make check` ruff clean, 514 files formatted, 597 passed / 3 skipped / 44 deselected. `app-frontend-check` not required (no frontend change). Clone clean after checks.

## 42.2.1

- Status: done, commit 8dfb26c `feat(agent-app): add out-of-band AOI screening route`.
- Changed: new `agent_server/geo.py` (raw-body parse: 256 KB cap, Polygon/MultiPolygon only, ring/position checks, `GEO_MAX_VERTICES` default 2000, fixed 422 messages; `async with init_fpac_mcp_server(WorkspaceClient())`; `parse_tool_result` structured -> `{"result": ...}` unwrap -> JSON text; allowlisted `build_chat_summary`; `render_chat_summary_text` <= 2,000 chars; `aoi-` + `secrets.token_hex(4)`); `agent_server/start_server.py` (+14, `POST /api/geo/screen`); root `Makefile` (`geo.py` in `APP_LINT_PATHS`); new `tests/test_geo_screen.py` (21 tests).
- Checks: targeted `pytest tests/test_geo_screen.py tests/test_custom_routes.py` 24 passed; `make app-check` lint clean, 82 passed. Positive control (temporary, not committed): wrapping the route in `mlflow.start_span` gives 1 trace in the same SQLite setup; the real route gives 0.
- Deviations: summary groups classes as `farmland_classes.<class>.{acres,pct}` and urban as `urban_screening.urban_intersected` (the server has no urban-acres field; a numeric `urban_acres` passes through if added). Tool errors (`isError` or an `error` key) return 200 with `display.error = "screening_failed"`; exceptions return 502 `{"error": "screening_unavailable"}`. Logs record the exception type only. `# noqa: BLE001` on the deliberate broad catch.
- Gotchas: the fake MCP proves the route opens no trace; whether the real `McpServer` emits spans is checked in 42.2.3 step 5.

## 42.2.2

- Status: done, commit 2a138df `feat(agent-app): add map panel with AOI drawing and screening`.
- Deps (exact, client workspace): `maplibre-gl` 5.24.0 (BSD-3-Clause), `terra-draw` 1.39.0 (MIT), `terra-draw-maplibre-gl-adapter` 1.5.0 (MIT). Lockfile: +27 packages; only other change is 4 `"dev": true` flags dropped (`@types/react`, `@types/react-dom`, `@types/prop-types`, `csstype`). `npm audit` unchanged (26 findings, all pre-existing).
- Added: `frontend/client/src/components/map/{MapPanel.tsx,GeoJsonInput.tsx,useScreening.ts,MapSummaryContext.tsx,geojson.ts}`. Modified: `frontend/client/package.json`, `frontend/package-lock.json`, `frontend/client/src/layouts/ChatLayout.tsx` (provider wrap, `<aside>` panel column `md:w-[40%]`, toggle; open by default on md+). 42.4.1 lists these in ADR 0015.
- Basemap: USGSTopo `.../MapServer/tile/{z}/{y}/{x}`, 256 px, maxzoom 16, CORS `*` (metadata checked 2026-10-30), attribution "USGS The National Map".
- Checks: biome (two skips) on the 6 files: 0 diagnostics; `tsc -p client` only the 4 upstream errors, none in new files; `make app-frontend-check` green. Bundle: main JS 2,556.78 -> 3,737.51 kB (gzip 759.42 -> 1,065.78 kB); CSS 78.74 -> 149.14 kB.
- Deviations: MapLibre 6.16.0 resolves its worker via `new URL(..., import.meta.url)`, which Vite does not emit without a `vite.config.ts` change (out of scope); 5.24.0 inlines the worker. MultiPolygon AOIs (paste only) show as an outline and are not editable.
- Recovery: the first commit (ac9e1b3) and its STATE commit lived only in `/tmp/p42`; the workspace fast-forward was blocked by the execution safety check, then compute restarted and `/tmp` was lost. Rebuilt with the same versions and edits as 2a138df; per-file line counts and the content-hashed build assets (`index-BZyQY39P.js`, `index-B8uFTTaB.css`) match the original build. Fast-forwarded to the workspace clone right after the gate.
- Gotchas: no browser run yet (42.2.3). A future CSP needs `worker-src blob:` and tile access to `basemap.nationalmap.gov`.

## Wave 2 gate

- Fresh `/tmp/p42g` clone of `/tmp/p42` at 2a138df: `make app-check` lint clean, 82 passed; `make app-frontend-check` `npm ci` 780 packages, biome 593 files 0 errors 10 warnings, builds complete; root `make check` ruff clean, 516 formatted, 597 passed / 3 skipped / 44 deselected. Clone clean after checks.

## 42.2.3

- Status: failed at step 5; fix task 42.2.4 added.
- Step 1-2: user approved; pushed 0823c7f..e49975f from the workspace clone.
- Step 3: pass. Deployment 01f1d49639b11a74ab79a9f90fbade8e SUCCEEDED 19:15 UTC, `resolved_commit` e49975f. An earlier deployment at 17:36 UTC (01f1d488757d...) had failed "unexpectedly" with no resolved commit.
- Step 4: pass per the user (map panel, tiles, draw, Run screening returned soil polygons).
- Step 5: fail. Experiment 517983779529169 had 7 traces after 19:15 UTC: 6 `call_tool` traces (19:34:30-19:35:39, three screenings x two tools; ids end 33fd86, c8e049, c4504a, 5de929, 819476, 4ecd8a) whose request previews and inputs contain the AOI geometry, and whose `get_soil_polygons_by_geometry` responses contain clipped soil polygons. Checked by pattern counts only; no values were printed. The 7th trace (`stream_handler`, a chat turn, id ends 32e424) had no matches. Span data could not be loaded ("missing span data", as in 41.4.1).
- Cause: `databricks_openai` decorates `McpServer.call_tool` with `@mlflow.trace(span_type=TOOL)`. The 42.2.1 tests replaced the whole MCP client with a fake, so the decorated method never ran offline.
- Open: the 6 traces with AOI geometry remain in the experiment pending the user's decision on deletion.
- Between 42.2.3 and 42.2.4 the workspace clone fast-forwarded e49975f..9ea80da (PR #54 review fixes: trace-id migration order, chunked body limit in `geo_screen`, page zoom, sidebar toggle label, ADR 0015 local-changes inventory, `planning/TODO_PR54.md`). `make app-check` on 9ea80da: 83 passed.

## 42.2.4

- Status: done, commit a576f14 `fix(agent-app): keep AOI screening MCP calls out of traces`; edited and committed in the workspace clone. Not pushed.
- Changed: `agent_server/geo.py` (`_call_tool_untraced` calls the undecorated Agents SDK parent `MCPServerStreamableHttp.call_tool`); `tests/test_geo_screen.py` (fixture now a real `McpServer` from `init_fpac_mcp_server` with only `connect`, `cleanup` and the session faked; new guard, class and control tests; no-trace test also asserts both tools ran); ADR 0016 (untraced-call bullet, test description); `planning/tasks/42.2.4.todo.md`.
- Checks: targeted `pytest tests/test_geo_screen.py tests/test_custom_routes.py` 28 passed; full app tests 86 passed; ruff check and format clean on `APP_LINT_PATHS`. Negative control: the new tests against the old `geo.py` (HEAD, loaded from `git show` in memory) fail with `assert 2 == 0`, two traces per screening as in production. Control test: the decorated `call_tool` creates 1 trace in the same SQLite setup.
- Next: push (user approval), confirm a SUCCEEDED deployment on the head, one screening by the user, then confirm no `call_tool` traces in that window. Frontend and root checks not re-run (no frontend or root change since the wave 2 gate apart from the PR #54 fixes, which their author validated).
