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
| 2 | User + Databricks | 42.2.3 | done after fix 42.2.4 (first run failed step 5) |
| 2 | Databricks | 42.2.4 (fix) | done (a576f14); deployed re-check passed |
| 3 | Databricks | 42.3.1 | done (b351386); browser check pending |
| 3 | Databricks | 42.3.2 | done (5a56426), deployed check passed; run before 42.3.1 by user decision |
| 3 | gate | app-check, app-frontend-check, root check | done (b351386) |
| 4 | Databricks | 42.4.1 | done (cba02f3) |
| 4 | gate | app-check, app-frontend-check, root check | done (cba02f3) |
| 5 | Databricks | 42.5.1 | done (see report) |
| 5 | Databricks | 42.5.2 | done (see report) |
| 5 | Databricks | 42.5.3 | done (see report) |
| 5 | gate | app-check, app-frontend-check, root check | done (f4d1578) |
| 6 | User + Databricks | 42.6.1 | done (see report) |
| 6 | Databricks | 42.6.2 | done (see report) |

Plan amended 2026-10-31 (D9-D12): after the deployed check, the agent could not run LESA from the pasted summary (only `aoi_ref` was available). The map AOI becomes chat session context; geometry is allowed in traces and logs. The old 42.5.1 trial and 42.5.2 close-out became 42.6.1 and 42.6.2. The 42.3.2 button is replaced in 42.5.3.

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
- Resolved by 42.2.4; see its deployed re-check.
- Between 42.2.3 and 42.2.4 the workspace clone fast-forwarded e49975f..9ea80da (PR #54 review fixes: trace-id migration order, chunked body limit in `geo_screen`, page zoom, sidebar toggle label, ADR 0015 local-changes inventory, `planning/TODO_PR54.md`). `make app-check` on 9ea80da: 83 passed.

## 42.2.4

- Status: done, commit a576f14 `fix(agent-app): keep AOI screening MCP calls out of traces`; edited and committed in the workspace clone. Not pushed.
- Changed: `agent_server/geo.py` (`_call_tool_untraced` calls the undecorated Agents SDK parent `MCPServerStreamableHttp.call_tool`); `tests/test_geo_screen.py` (fixture now a real `McpServer` from `init_fpac_mcp_server` with only `connect`, `cleanup` and the session faked; new guard, class and control tests; no-trace test also asserts both tools ran); ADR 0016 (untraced-call bullet, test description); `planning/tasks/42.2.4.todo.md`.
- Checks: targeted `pytest tests/test_geo_screen.py tests/test_custom_routes.py` 28 passed; full app tests 86 passed; ruff check and format clean on `APP_LINT_PATHS`. Negative control: the new tests against the old `geo.py` (HEAD, loaded from `git show` in memory) fail with `assert 2 == 0`, two traces per screening as in production. Control test: the decorated `call_tool` creates 1 trace in the same SQLite setup.
- Deployed re-check: pass. User approved the push (9ea80da..97f144e, 22:56 UTC); deployment 01f1d4b5323a1fefaa0b073b7fe8106d SUCCEEDED on 97f144e. The user ran a screening and reported everything working. Experiment 517983779529169 after 22:57 UTC (checked 23:10): one trace, a `stream_handler` chat turn with no geometry pattern matches; no `call_tool` traces.
- Leak extent before the fix: 22 `call_tool` traces with AOI geometry (the 6 above plus 16 from 8 screenings 19:52-22:34 UTC on pre-fix deployments). The user chose not to delete them.
- Frontend and root checks not re-run (no frontend or root change since the wave 2 gate apart from the PR #54 fixes, which their author validated).

## 42.3.2

- Status: done, commit 5a56426 `feat(agent-app): add map screening summary to the chat input`; edited and committed in the workspace clone. Not pushed.
- Deviation: run before 42.3.1 (user decision 2026-10-30, to connect map and chat first); the files do not overlap.
- Changed: `map/MapPanel.tsx` (+16: "Add result to chat" outline button, shown only when status is `done` and `display.error` is unset, calls `offerSummary(chat_summary_text)`); `map/MapSummaryContext.tsx` (+5: `useOptionalMapSummary`, returns null outside the provider); `multimodal-input.tsx` (+13: effect prepends the summary and a blank line to any existing input, focuses the textarea, consumes the summary; no-op without the provider).
- Only `chat_summary_text` reaches the input; `display` is read only for the error check. The input is still mirrored to localStorage key `input` by the existing template code, so the geometry-free summary is persisted like typed text until sent.
- Checks: fresh `/tmp/p42g` clone at 5a56426, `make app-frontend-check` rc 0: `npm ci` 780 packages, biome 593 files 0 errors 10 warnings (baseline; the 2 in `multimodal-input.tsx` are existing unused imports), build OK. `tsc --noEmit -p client`: 4 existing errors in unrelated files, none in the changed files.
- Deployed check: pass. User approved the push (97f144e..f33d707, 23:22 UTC); deployment 01f1d4b8b7f91cc5bf763f845e1d02b2 SUCCEEDED on f33d707. The user ran a screening, used "Add result to chat" and sent the turn; reported working. Experiment 517983779529169 after 23:22 UTC (checked 23:26): one `stream_handler` trace (id ends a09c58, 8 spans). Its request preview (2086 chars, not truncated, so the full user message) has the summary and notice, `aoi_ref` present, zero coordinate objects, polygon types, bbox, WKT, coordinate pairs or 5+-decimal numbers; the response preview has preliminary-screening wording and none of those patterns; no `call_tool` traces. Span data still unavailable (`get_trace` "missing span data"; signed download URL returns 404), so span-level content was not inspected.

## 42.3.1

- Status: done, commit b351386 `feat(agent-app): show screening legend, table and notice on the map panel`; edited and committed in the workspace clone. Not pushed. Run after 42.3.2 (user decision).
- Changed (all under `frontend/client/src/components/map/`): new `farmlandClasses.ts` (one mapping: colour, solid/hatched hint, text code, label, `farmland_summary` key for prime, conditional prime, statewide, local, unique, not prime, unmapped; MapLibre `match` expression; `withFarmlandClass` adds `farmland_class` to soil features), `Legend.tsx`, `ResultsTable.tsx` (class acres/% plus total FPPA-protected; map units sortable by acres with `aria-sort`), `ScreeningResults.tsx` (notice verbatim or "Regulatory notice missing - treat this result as invalid."); `MapPanel.tsx` (persistent preliminary label, `role="alert"` area for invalid drawn shape, screening errors and basemap tile failure, shared class colours, "Add result to chat" hidden without a notice); `useScreening.ts` (`DisplayAnalysis` type, 422 shows the server's bounded `detail`, 502 "Screening unavailable"). Plus `planning/tasks/42.3.1.todo.md`.
- Class colours changed from the 42.2.2 placeholders to the Phase 8 symbology (P `#2E7D32`, S `#F9A825`, U `#6A1B9A`, L `#0288D1`, NP `#9E9E9E`); conditional prime `#81C784` and unmapped white are hatched in the legend. The map fill is colour only.
- Checks: client `classifyFarmland` vs server `categorize_farmland_class` on 16 SSURGO strings (incl. empty, null, padded and unknown): 0 mismatches, all 7 classes seen. Client `summaryKey`s equal the server's `geo.FARMLAND_CLASSES` keys. No coordinate-like values or browser storage in the changed files.
- Not yet checked in a browser.

## Wave 3 gate

- Fresh `/tmp/p42g` clone of the workspace clone at b351386: `make app-frontend-check` rc 0 (`npm ci` 780 packages, biome 597 files 0 errors 10 warnings, build OK); `tsc --noEmit -p client` only the 4 existing errors outside `components/map/**`; `make app-check` lint clean, 86 passed; root `make check` ruff clean, 518 formatted, 597 passed / 3 skipped / 44 deselected. Clone clean after checks.

## 42.4.1

- Status: done, commit cba02f3 `docs(agent-app): record map panel local frontend changes`; edited and committed in the workspace clone. Not pushed.
- Parity: blob-less fetch of `databricks/app-templates` at 0e57297 into a throwaway `/tmp` repo; `git ls-tree -r` (blob and mode) of `e2e-chatbot-app-next` vs `HEAD` `frontend/`: 640 upstream files, 36 excluded, 604 kept; 596 identical, 8 modified, 0 missing, 9 added (all under `client/src/components/map/`), no excluded file present. No mode-only differences.
- Changed: ADR 0015 `### Local changes` (modified: the 4 PR #54 files plus `client/package.json`, `package-lock.json`, `client/src/layouts/ChatLayout.tsx`, `client/src/components/multimodal-input.tsx`; added: `client/src/components/map/**`; one line each on why); app `AGENTS.md` (`geo.py` in Find Things, map file roles, new "Change AOI Screening" workflow); app `README.md` (stale "map deferred" paragraph replaced); `planning/tasks/42.4.1.todo.md`.
- Deviation: app `README.md` was not in the task's file list; no later task updates it and the old text said the map was deferred.
- Check: paths parsed from the ADR section equal the modified set exactly, and the `map/**` entry covers all 9 added files. (A first parse matched the inline mention of the heading in the Decision text; re-run anchored on the heading line.)

## Wave 4 gate

- Fresh `/tmp/p42g` clone of the workspace clone at cba02f3: `make app-check` lint clean, 86 passed; root `make check` ruff clean, 597 passed / 3 skipped / 44 deselected; `make app-frontend-check` `npm ci` 780 packages, biome 597 files 0 errors 10 warnings, build OK.

## Plan amendment (2026-10-31)

- Commit 117e86e `docs(planning): make the map AOI chat session context in plan 42`: D9-D12, waves 5 and 6, hazards, renumbered trial and close-out (42.6.1, 42.6.2). User decisions: amend ADR 0016 (only on this branch); browser sessionStorage per conversation; one AOI per conversation; geometry generally allowed with deployment limits and user guidance; fold into Plan 42.

## 42.5.1

- Status: done; edited and committed in the workspace clone. Not pushed. Commit `docs(decisions): amend ADR 0016 to make the map AOI chat session context`.
- Changed: ADR 0016 (title "Map AOI as Chat Session Context", same file name, `Proposed`, dated amendment note with the LESA finding, corrected ADR 0010 reading, new drivers/options/decision, "Map screening route" subsection for `/api/geo/screen`, consequences, scope, validation); `docs/decisions/README.md` (row title, Databricks Delivery sentence); app `AGENTS.md` ("Change AOI Screening" workflow, `geo.py` line); `planning/tasks/42.5.1.todo.md`.
- Root `AGENTS.md` unchanged: its coordinate rule is scoped to `privacy.py` for producer data and sensitive locations; no conflict with D11.
- Checks: `status: "Proposed"` matches; remaining "geometry-free"/"never enters" wording is history or the route summary; README title equals the ADR title; no coordinate-like values in the diff.
- Gotchas: app `README.md` still describes "Add result to chat" (42.5.3 updates it); app `AGENTS.md` now describes behaviour that 42.5.2/42.5.3 implement.

## 42.5.2

- Status: done; edited in the workspace clone, tested in a `/tmp` copy, committed in the workspace clone. Not pushed. Commit `feat(agent-app): give the agent the map AOI as session context`.
- Changed: new `agent_server/aoi_context.py` (read/validate `custom_inputs.active_aoi` with geo.py limits, coordinate-free instruction note, `geojson`/`geometry` substitution bound on the per-request `McpServer`); `agent_server/agent.py` (`create_agent(aoi_note=...)`, `_connect_fpac_agent(stack, aoi)`, both handlers read the AOI); new `tests/test_aoi_context.py` (45 tests); root `Makefile` lint paths; `planning/tasks/42.5.2.todo.md`.
- Behaviour: no or invalid AOI gives exactly the old `create_agent(mcp_servers=..., tools_unavailable=...)` call and an unbound server; tools unavailable keeps the unavailable note without the AOI note; the bound call stays on the traced `McpServer.call_tool` (1 trace in the SQLite check).
- Commands: `make app-check` in `/tmp/p42w` -> ruff clean, 131 passed (86 + 45). Negative controls: substitution removed -> 4 failed; binding in `agent.py` removed -> 2 failed.
- Gotchas: `geo` imports `agent`, so `aoi_context` imports `geo` lazily; `import agent_server.start_server` outside pytest fails on HEAD too (MLflow experiment id env), unrelated; new workspace files commit with `--chmod=-x`.

## 42.5.3

- Status: done; edited in the workspace clone, checked in a `/tmp` copy, committed in the workspace clone. Not pushed. Commit `feat(agent-app): send the map AOI with each chat turn`.
- Changed: `map/ActiveAoiContext.tsx` (new; replaces deleted `MapSummaryContext.tsx`), `map/ActiveAoiChip.tsx` (new), `map/MapPanel.tsx`; `chat.tsx`, `multimodal-input.tsx` (2 lines from upstream), `layouts/ChatLayout.tsx`; `packages/core/src/schemas/chat.ts`, `packages/core/src/ai/providers.ts`, `server/src/routes/chat.ts`, `packages/ai-sdk-providers/src/providers-server.ts`; ADR 0015 Local changes; app README and `AGENTS.md`; `planning/tasks/42.5.3.todo.md`.
- Request mechanism (recon): the chat route registers the validated `activeAoi` in a request-scoped map and passes only a random key header; `databricksFetch` strips it and adds `custom_inputs.active_aoi`. Released on response close. Invalid AOIs are dropped by the schema (`.catch`), never a 400.
- Checks: `make app-frontend-check` rc 0 (780 packages, biome 598 files 0 errors 10 warnings, build OK); `tsc -p client` 4 existing errors, `tsc -p server` same 2 as HEAD; tsx smoke of schema and `databricksFetch` passed; parity 640/36/591 identical/13 modified/10 added, ADR list equals the modified set.
- Deviation: `packages/core/src/ai/providers.ts` (re-export) was not in the task's file list.
- Gotcha for 42.6.1: the deployed app runs without a chat database, so a reload starts a new chat id and the AOI is not restored (messages are not either). Not yet checked in a browser.
- Follow-up (2026-10-31): a tab-level carry-over of the AOI across reloads (488c2be) was reverted by user decision; the AOI stays as ephemeral as the chat. D10, ADR 0016 (decision, validation, scope) and the 42.6.1 reload step now say a reload starts a new chat with no AOI. Deferred in Plan 42 and ADR 0016: opt-in chat history and stored sessions for users who opt in or approved secure deployments.

## 42.6.1

- Push: user approved; f33d707..171b470 pushed from the workspace clone at 07:34 UTC 2026-10-31.
- Deployment 01f1d4fd835d1105a6edb990112c5f5b SUCCEEDED (auto-deploy), `resolved_commit` 171b470; app RUNNING.
- Trial (user, browser): reported working well; ran a full preliminary FPPA workflow, 12 site-assessment questions and a refined LESA on one drawn AOI. Traces: 19 OK, one session = `context.conversation_id`, `custom_inputs.active_aoi` on turn 1 (later previews truncated), tool results AOI-specific (LE 73.89, refined LESA 194.89 / 260). Span data does not load; tool arguments checked by result shape.
- Steps 1, 2, 6 pass; steps 3-5 (paste, reload/new chat/detach, POINT-01) not shown in the traces; asked the user. Evidence: `planning/evidence/42.6.1-trial.md`.
- Steps 3-5 (user, second run): 3 more traces, all OK, separate sessions. Pasted AOI sent with a new reference and summary, answered on it (pass); a new session had no `active_aoi` and the agent asked for geometry (pass); the user ran PROMPT-01 (point screening) in a fresh chat instead of POINT-01 (pass, equivalent). Finding: the summary keeps the screening route's own `aoi_ref`, different from the browser's; the model never sees it (agent server renders the active ref); backlog item. Status: done.

## 42.6.2

- Status: done. ADR 0015 and 0016 `status: "Accepted"` with acceptance notes pointing to the 42.6.1 evidence; README rows `Accepted (2026-10-31, EP42)`. MASTER_PLAN Track A: status, delivered (Plans 35, 40, 41, 42; ADRs 0012, 0015, 0016), backlog (M0 delivered, M1 resolved by ADR 0016, M2 MVP delivered, M3 next, remaining M2 items, opt-in chat history, one AOI reference), open decisions 1 and 4 decided; Phase 8 M2 exit criterion aligned with ADR 0016.
- Acceptance: `grep -n 'status: "Accepted"'` matches both ADRs; both README rows match.

## Final summary

Plan 42 delivered the owned agent-app frontend with a map panel MVP: draw or paste one AOI, run a preliminary screening shown on the map, and use that AOI as chat session context, so the agent runs the FPPA tools and LESA on it without pasted geometry. The AOI is ephemeral like the chat. ADRs 0015 and 0016 are accepted. Next (user): merge the PR into `main`, then point the app's git source back at `main`. Follow-ups are in the MASTER_PLAN Track A backlog (M3 `map` envelope next).

## Wave 5 gate

- Fresh `/tmp/p42g` clone of the workspace clone at f4d1578: `make app-frontend-check` (`npm ci` 780 packages, biome 598 files 0 errors 10 warnings, build OK); `make app-check` lint clean, 131 passed; root `make check` ruff clean, 522 formatted, 597 passed / 3 skipped / 44 deselected. Clone clean after checks.
