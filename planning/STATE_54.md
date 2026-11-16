# STATE 54: Agent-App Map Usability and Corridor Workflow

Resume point for orchestration 54. Plan: `planning/EXECUTION_PLAN_54.md`. Worker prompt: `planning/PROMPT_TEMPLATE_54.md`.

## Baseline

- [x] Repository `/home/andrew/work/fpac-soil-mcp`, branch `feature/local-dev-trial`, clean at `f05b84c` before baseline rerun.
- [x] Existing Plan 53 final gates at this exact code commit: `make check` 993 passed, 3 skipped, 45 deselected; `make app-check` 266 passed; `make app-frontend-check` passed.
- [x] Frontend baseline caveats from Plan 53: 11 lint warnings (including one MapPanel exhaustive-dependency warning), 10 npm audit advisories, existing Vite/React/chunk warnings; build passed.
- [x] Planning artifacts tracked; plan-only commits remain separate from implementation commits.
- [x] Re-ran baseline at `f05b84c`: `make check` 993 passed/3 skipped/45 deselected; `make app-check` 266 passed; `make app-frontend-check` passed with 11 existing warnings, 10 npm advisories, ephemeral DB migration skip, and existing build warnings.

## Decisions

- Plan 54 follows Plan 53 on `feature/local-dev-trial`; user asks to start at G42 and include as many agent-app map UI goals as feasible.
- Usability-first priority: compact icon controls, accessible hover/focus labels, crosshair drawing/measurement cursor, miles as measure default.
- SSURGO default refers to returned server result polygons, not fixed context overlay. On each new successful result, show inline result vectors by default; preserve explicit hide control.
- Amend ADR 0016: corridor is a separate per-chat context from polygon `active_aoi`; primary centerline, alternatives, staging geometry, buffer distance and units.
- Both direct map corridor screening and chat handoff are supported. Corridor context auto-attaches per conversation, has a separate detach control, and does not replace polygon AOI.
- Corridor buffer is blank until user entry, unit defaults to feet, distance is on each side. Measurement unit independently defaults to miles.
- Map corridor screening stays preliminary and sends no Site Assessment inputs. Direct route is stateless/untraced and uses existing `analyze_corridor_fppa` only.
- CDL color key follows official USDA NASS code/name/color table; context imagery is not analysis evidence.
- NAIP source changes to the user-selected USDA FPAC `conus_naip` ImageServer. Planning probes returned HTTP 200 PNG with origin-specific CORS; service metadata includes `Purpose: test:202407180638 naip service`, a caveat the user approved retaining.
- At most two concurrent workers; planning artifacts are tracked and planning-only commits separate.
- Preserve ADR 0003, update ADR 0015 local-change ledger, amend ADR 0016, preserve ADR 0017 server-owned map contract.

## Wave Board

| Wave | Task | Status | Commit | Notes |
|---|---|---|---|---|
| 1 | 54.1.1 Compact accessible map controls and cursor defaults | done | `cc7560c` | G42; integrated app checks pass |
| 2 | 54.2.1 Map-pane server legend and authoritative CDL key | done | `d76c7cc` | G43; targeted + integrated checks pass |
| 2 | 54.2.2 Replace NAIP with fixed USDA FPAC ImageServer | done | `d37e63e` | G49; fixed endpoint; test-purpose caveat |
| 3 | 54.3.1 Returned SSURGO visibility on new results | done | `073f3f1` | G44; focused checks pass |
| 4 | 54.4.1 ADR 0016 corridor amendment and validated context model | done | `26bdc6b` | G45 |
| 5 | 54.5.1 Direct stateless corridor screening route | done | `1dd7313` | G46; 13 targeted tests; covered by app-check |
| 5 | 54.5.2 Bind corridor context to agent tool calls | done | `54b461d` | G47; AOI compatibility preserved; app-check passes |
| 6 | 54.6.1 Per-chat corridor context transport | pending | | G47 |
| 7 | 54.7.1 Corridor drawing and buffer controls | pending | | G48 |
| 8 | 54.8.1 Direct corridor submission and result display | pending | | G48 |
| 9 | Integrated validation and handoff | pending | | |

## Task Reports

(Workers append <=15-line reports here after each committed task.)

### 54.5.1 — Direct stateless corridor screening route

- Status: done; code commit `1dd7313` (`feat(agent-app): add direct corridor screening route`); planning commit `ccbb312`.
- Added `/api/geo/corridor`, shared-context request validation, untraced `analyze_corridor_fppa` call with `include_map=True`, bounded allowlisted result/map/notice, and route tests.
- `uv run pytest tests/test_geo_corridor.py -q`: 13 passed (one existing pytest config warning).
- Earlier fixture attempts timed out entering a real MCP context; worker replaced it with a local fake context. Final targeted suite passed.
- Formatting follow-up: planning `835b47a`, format-only commit `cb65d24`.
- Deviations: none. No remote actions.

### 54.5.2 — Bind corridor context to agent tool calls

- Status: done; code commit `54b461d` (`feat(agent-app): bind active corridor context`); planning commit `c3182e6`.
- Binds corridor validation and note independently of AOI; only matching corridor tool references are substituted. Initial imports are deferred to avoid circular imports.
- `uv run pytest tests/test_corridor_context.py tests/test_agent_mcp_wiring.py -q`: 82 passed; after compatibility fix, `uv run pytest tests/test_aoi_context.py tests/test_corridor_context.py -q`: 65 passed.
- Integration fixes: planning `b82f58a`, lint fix `d6a97aa`; planning `b95ffda`, AOI-call compatibility fix `c593d24`.
- `make app-check`: Ruff check/format passed; 297 tests passed (122 existing deprecation/config warnings).
- Deviations: integrated app check caught AOI-only `create_agent` kwargs regression; fixed so AOI-only calls retain prior contract. No other deviations.

### Wave 5 integrated gate

- `make app-check`: Ruff check passed; 20 files formatted; 297 passed.
- `git diff --check`: passed; implementation and planning commits remain separate.
- Direct route is stateless/untraced, uses the existing corridor tool with `include_map=True`, and has no Site Assessment inputs; AOI-only chat behavior remains unchanged.

### 54.4.1 — ADR 0016 corridor amendment and validated context model

- Status: done; code commit `26bdc6b` (`feat(agent-app): add validated corridor context`).
- Changed `agent_server/corridor_context.py`, `tests/test_corridor_context.py`, and ADR 0016.
- Corridor context remains separate from AOI; validates references, finite lines/buffers, supported units, alternative/staging limits, and substitutes only matching corridor calls.
- `cd apps/agent-fpac-soil-openai-sdk && uv run pytest tests/test_corridor_context.py -q`: 17 passed (one existing pytest config warning).
- App Ruff check/format passed; root `git diff --check` passed.
- Deviations: none. Gotcha: integration into agent binding is the dependent task 54.5.2.

### 54.1.1 — Compact accessible map controls and cursor defaults

- Status: done; code commit `cc7560c` (`feat(map): compact accessible toolbar controls`); planning report commit `5eda878`.
- Changed `frontend/client/src/components/map/MapPanel.tsx`, toolbar fixture HTML/TSX, `frontend/playwright.map-toolbar.config.ts`, `frontend/tests/map-toolbar/toolbar.spec.ts`, `frontend/package.json`, and ADR 0015 local-change ledger (paths relative to app except ADR).
- From `apps/agent-fpac-soil-openai-sdk/frontend`: `npm run test:map-toolbar` 3 passed; `npm run test:map-identify` 2 passed. `git diff --check` passed.
- Integrated gates: `make app-check` 266 passed; `make app-frontend-check` passed with 11 baseline warnings, 10 npm advisories, ephemeral DB migration skip, and existing build warnings.
- Deviations: none. A first rectangle completion test used dragging and failed; Terra Draw defaults to click–move–click, and the corrected test passed.
- Gotchas: fixture mounts the production panel and aborts external HTTPS; cursor is a canvas CSS override in draw/measure modes. Orchestrator owns frontend lint/build and full suites.

### 54.2.1 — Map-pane server legend and authoritative CDL key

- Status: done; code commit `d76c7cc` (`feat(map): show result and CDL legends`).
- Changed map `MapPanel.tsx`, `Legend.tsx`, `OverlayControl.tsx`, added `CDLLegend.tsx` and `cdlLegend.ts`, legend fixture/config/spec, frontend `package.json` test script, and ADR 0015 local-change ledger.
- From `apps/agent-fpac-soil-openai-sdk/frontend`: `npm run test:map-legend` 4 passed; `npm run test:map-identify` 2 passed. `git diff --check` passed.
- Orchestrator reruns: `npm run test:map-legend` 4 passed; `npm run test:map-identify` 2 passed.
- Deviations: none. A first screening-switch assertion matched both the map and existing Results-tab legends; scoping it to the map legend passed.
- Gotchas: CDL table contains 133 official NASS records; fixture aborts external HTTPS. Orchestrator owns lint/build and full suites; 54.2.2 follows due shared files.

### 54.2.2 — Fixed USDA FPAC NAIP ImageServer

- Status: done; code commit `d37e63e` (`feat(map): use USDA FPAC NAIP imagery`).
- Changed `frontend/client/src/components/map/overlays.ts`, `OverlayControl.tsx`, `overlays.test.ts` (paths relative to app), and ADR 0015.
- From `apps/agent-fpac-soil-openai-sdk/frontend`: `node --import tsx --test client/src/components/map/overlays.test.ts` passed (3 tests); root `git diff --check` passed.
- Orchestrator rerun: `node --import tsx --test client/src/components/map/overlays.test.ts` 3 passed.
- Deviations: none. Initial component-render assertion failed because the Node TSX loader expected a React global; replaced it with a test of the shared caveat text.
- Gotchas: metadata labels purpose `test:202407180638 naip service`; availability may change. No live verification; orchestrator owns shared/full suites.

### 54.3.1 — Returned result visibility

- Status: done; code commit `073f3f1` (`fix(map): show new screening result layers`); planning report commit `ff4a74a`.
- Changed `frontend/client/src/components/map/MapPanel.tsx`, added `resultVisibility.ts` and `resultVisibility.test.ts`, and updated ADR 0015 (frontend paths relative to app).
- From `apps/agent-fpac-soil-openai-sdk/frontend`: `node --import tsx --test client/src/components/map/resultVisibility.test.ts` 1 passed; `npm run test:map-identify` 2 passed. Root `git diff --check` passed.
- Orchestrator reruns: result visibility 1 passed; map-identify 2 passed.
- A successful screening transition resets result visibility; tab revisits, old result selection, and failed screening do not. Context SSURGO is independently controlled.
- Deviation/limitation: focused test exercises the production-wired transition and renderer with a mock map, not the production React panel or browser navigation; the overlay independence assertion uses copied default flags. Orchestrator owns integration validation.
- Dependency gotchas: result layers are applied by both the visibility and render effects; NAIP's test-purpose service caveat remains unchanged.

### Wave 3 integrated gate

- `make app-check`: 266 passed; Ruff check/format passed.
- `make app-frontend-check`: passed; 11 baseline lint warnings, 10 npm advisories, ephemeral DB migration skip, and existing build warnings.
- `git diff --check`: passed; working tree clean after planning commit.

### Wave 2 integrated gate

- `make app-check`: 266 passed; Ruff check/format passed.
- `make app-frontend-check`: passed; 11 lint warnings, 10 npm advisories, ephemeral DB migration skip, and existing Vite/chunk warnings.
- `git diff --check`: passed; working tree clean after planning commit.

## Final Acceptance

- [ ] All task reports and implementation commits recorded.
- [ ] `make app-check` passes.
- [ ] `make app-frontend-check` passes; warnings are compared with baseline.
- [ ] Focused corridor, legend, map, and existing regression suites pass.
- [ ] `git diff --check` passes; ADR 0015 ledger and ADR 0016 amendment reviewed.
- [ ] Polygon AOI and corridor context remain separate; direct map calls remain untraced and preliminary; no Site Assessment inputs are submitted.
- [ ] No remote actions performed.
