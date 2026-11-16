# STATE 55: Corridor, Map, Measurement & Chat Tool UX

Resume point for orchestration 55. Plan: `planning/EXECUTION_PLAN_55.md`. Worker prompt: `planning/PROMPT_TEMPLATE_55.md`.

## Baseline
- [x] Root worktree branch `feature/local-dev-trial` at `c0ce702`; clean before Plan 55 planning.
- [x] Fresh baseline: `make check` — Ruff passed, 764 files formatted, 993 passed / 3 skipped / 45 deselected.
- [x] Fresh baseline: `make app-check` — Ruff passed, 20 files formatted, 297 passed.
- [x] Fresh frontend baseline: `make app-frontend-check` passed (Biome warnings only; client and server builds succeeded).
- Planning artifacts are tracked and will be committed separately as `docs(planning):`; no remote actions authorized.

## Wave Board

| Wave | Task | Status | Commit | Notes |
|---|---|---|---|---|
| 1 | 55.1.1 AOI/corridor chat attachment exclusivity | done | `4bf4fa3` | Verified targeted test and frontend check; cross-provider UI integration coverage remains a limitation. |
| 1 | 55.2.1 Collapse tool output & promote Show on Map | done | `e070950` | Focused test passed on worker retry and orchestrator rerun. |
| 2 | 55.1.2 Corridor labels and remove/clear synchronization | done | `78b4efc` | Labels remain browser/session metadata; focused Node tests 10/10, corridor-map Playwright 2/2, and frontend check passed. |
| 3 | 55.2.2 Measurement preview | done | `b71ae66` | Focused distance tests 2/2, toolbar Playwright 4/4, and `make app-frontend-check` passed. |
| 4 | 55.3.1 Toolbar, attachment chip, unified geometry I/O | pending | | |
| 5 | 55.4.1 Integrated validation and handoff | pending | | |

## Task Reports

### 55.1.1
- Implemented exclusive AOI/corridor attachment; replacing a context clears the other context and its persisted value.
- Requests serialize at most one context; legacy dual-context state prefers corridor.
- `node --import tsx --test client/src/components/map/corridorSession.test.ts` — 5 passed (worker and orchestrator rerun).
- `make app-frontend-check` — passed in worker; existing Biome warnings only; client/server builds succeeded.
- Changed five scoped frontend files; no server schema changes or remote actions.
- Limitation: no provider-level UI integration test for cross-provider replacement/persistence; recorded by worker.
- Worker implementation commit `be6442b`; integrated commit `4bf4fa3`.

### 55.2.1
- Regular tool details start collapsed; MCP approval cards remain unchanged.
- Map-capable regular tool action is in the top bar with accessible tool/AOI context; availability/staleness checks preserved.
- Focused Playwright command passed on worker retry and orchestrator rerun: `npx playwright test --config playwright.site-assessment.config.ts tests/site-assessment/tool-card.spec.ts` — 1 passed.
- `make app-frontend-check` passed in worker; existing Biome warnings only; client/server builds succeeded.
- Changed `message.tsx`, `elements/tool.tsx`, `ShowOnMapButton.tsx`, fixture and focused spec; no scope deviation.
- Initial orchestrator rerun failed to find the action; worker retry and second orchestrator rerun passed, indicating a transient/flaky first run.
- Worker implementation commit `7e57d8f`; integrated commit `e070950`.

### 55.1.2
- TerraDraw `onFinish` assigns the unified role/label metadata; `onChange` is the single source of truth for React draft arrays, avoiding duplicate entries.
- Alternative labels round-trip in browser corridor session state. The existing chat schema strips this optional browser metadata; `alternatives` remain bare LineString geometries, with primary/staging represented by existing centerline/indirect-geometry fields. No MCP geometry schema change.
- Removal synchronizes TerraDraw and draft arrays; primary removal also clears attached corridor state. Clear removes all TerraDraw/draft features and attached state.
- `node --import tsx --test client/src/components/map/corridorGeometry.test.ts client/src/components/map/corridorSession.test.ts` — 10 passed.
- `npm run test:corridor-map` — 2 passed, including alternative label retention and removal of alternative, staging, and primary features plus clear.
- `make app-frontend-check` — passed; read-only Biome reported existing warnings, client/server builds succeeded. npm reported 10 existing dependency audit findings.
- `git diff --check` — passed.
- The first Node test attempt failed because `tsx` was not installed in the isolated worktree; `make app-frontend-check` ran `npm ci`, after which the exact targeted Node command passed. Initial Playwright attempts exposed a non-completing alternative draw with the first coordinates and then duplicate UI rows from both `onFinish` and `onChange`; stable in-map coordinates and making `onChange` authoritative resolved it. No scope deviation.
- ADR 0015 already listed every changed/modified frontend path; no ADR update was required.
- Implementation commit: `78b4efc`; planning-only status/TODO commit follows separately. No remote actions.

### 55.2.2
- Added transient pointer preview to the existing measurement GeoJSON source after the first committed point; pointer movement does not update committed points or distance. The active indicator is now the concise accessible status “Measuring.”
- `node --import tsx --test client/src/components/map/distance.test.ts` — 2 passed.
- `npm run test:map-toolbar` — 4 passed, including live-preview activation, unchanged committed distance during pointer movement, and cancel behavior.
- `make app-frontend-check` — passed; existing Biome warnings only; client/server builds succeeded. npm reported 10 dependency audit findings.
- The first toolbar run lacked installed dependencies; after `npm ci`, a concurrent frontend gate reinstalled dependencies and caused a transient Playwright module-resolution error. Sequential toolbar rerun passed.
- ADR 0015 already listed all modified frontend paths; no inventory update was needed. No scope deviation or remote actions.
- Implementation commit: `b71ae66`; planning-only status/TODO commit follows separately.
