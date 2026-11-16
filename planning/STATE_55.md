# STATE 55: Corridor, Map, Measurement & Chat Tool UX

Resume point for orchestration 55. Plan: `planning/EXECUTION_PLAN_55.md`. Worker prompt: `planning/PROMPT_TEMPLATE_55.md`.

## Baseline
- [x] Root worktree branch `feature/local-dev-trial` at `c11293a`; clean before Plan 55 planning.
- [x] Fresh baseline: `make check` — Ruff passed, 764 files formatted, 993 passed / 3 skipped / 45 deselected.
- [x] Fresh baseline: `make app-check` — Ruff passed, 20 files formatted, 297 passed.
- [x] Fresh frontend baseline: `make app-frontend-check` passed (Biome warnings only; client and server builds succeeded).
- Planning artifacts are tracked and will be committed separately as `docs(planning):`; no remote actions authorized.

## Wave Board

| Wave | Task | Status | Commit | Notes |
|---|---|---|---|---|
| 1 | 55.1.1 AOI/corridor chat attachment exclusivity | done | `172827b` | Verified targeted test and frontend check; cross-provider UI integration coverage remains a limitation. |
| 1 | 55.2.1 Collapse tool output & promote Show on Map | done | `05c31d7` | Focused test passed on worker retry and orchestrator rerun. |
| 2 | 55.1.2 Corridor labels and remove/clear synchronization | done | `78b4efc` | Labels remain browser/session metadata; focused Node tests 10/10, corridor-map Playwright 2/2, and frontend check passed. |
| 3 | 55.2.2 Measurement preview | done | `b71ae66` | Focused distance tests 2/2, toolbar Playwright 4/4, and `make app-frontend-check` passed. |
| 4 | 55.3.1 Toolbar, attachment chip, unified geometry I/O | done | `21414c8`, `c8565de` | Corridor-to-AOI replacement and shared-chip detach covered; corridor-map 3/3, toolbar 5/5, frontend check passed after mid-tier recovery. |
| 5 | 55.4.1 Integrated validation and handoff | done | — | Final root/app/frontend gates passed; all scoped browser and Node tests passed. |

## Task Reports

### 55.1.1
- Implemented exclusive AOI/corridor attachment; replacing a context clears the other context and its persisted value.
- Requests serialize at most one context; legacy dual-context state prefers corridor.
- `node --import tsx --test client/src/components/map/corridorSession.test.ts` — 5 passed (worker and orchestrator rerun).
- `make app-frontend-check` — passed in worker; existing Biome warnings only; client/server builds succeeded.
- Changed five scoped frontend files; no server schema changes or remote actions.
- Limitation: no provider-level UI integration test for cross-provider replacement/persistence; recorded by worker.
- Worker implementation commit `be6442b`; integrated commit `172827b`.

### 55.2.1
- Regular tool details start collapsed; MCP approval cards remain unchanged.
- Map-capable regular tool action is in the top bar with accessible tool/AOI context; availability/staleness checks preserved.
- Focused Playwright command passed on worker retry and orchestrator rerun: `npx playwright test --config playwright.site-assessment.config.ts tests/site-assessment/tool-card.spec.ts` — 1 passed.
- `make app-frontend-check` passed in worker; existing Biome warnings only; client/server builds succeeded.
- Changed `message.tsx`, `elements/tool.tsx`, `ShowOnMapButton.tsx`, fixture and focused spec; no scope deviation.
- Initial orchestrator rerun failed to find the action; worker retry and second orchestrator rerun passed, indicating a transient/flaky first run.
- Worker implementation commit `7e57d8f`; integrated commit `05c31d7`.

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

### 55.3.1
- Existing Area/Corridor toolbar controls were already compact icon-only buttons with accessible labels; preserved them.
- Removed separate corridor attach/detach controls; the shared chat chip now reports either AOI or Corridor (reference only) and detaches the active context.
- Grouped GeoJSON upload, paste, copy, and download in an expandable panel; retained parsing and size validation.
- `npm run test:corridor-map` — 3 passed, including AOI-to-corridor replacement, shared-chip detach, and persisted-state cleanup.
- `npm run test:map-toolbar` — 5 passed, including unified transfer actions and measurement coverage.
- `make app-frontend-check` and `git diff --check` — passed; 11 existing Biome warnings and 10 existing npm audit findings.
- Initial corridor-chip coverage failed because the fixture lacked the production shared chip; a small-worker retry also failed before assertions due to this fixture gap. Mid-tier recovery mounted both providers and chip, supplied valid buffer inputs, and verified replacement/detach.
- Modified paths are inventoried in ADR 0015; no geometry schema, dependency, or privacy changes. No remote actions.
- Worker implementation commits `3b0c125`, `0bf9167`; integrated commits `21414c8`, `c8565de`.

### 55.2.2
- Added transient pointer preview to the existing measurement GeoJSON source after the first committed point; pointer movement does not update committed points or distance. The active indicator is now the concise accessible status “Measuring.”
- `node --import tsx --test client/src/components/map/distance.test.ts` — 2 passed.
- `npm run test:map-toolbar` — 4 passed, including live-preview activation, unchanged committed distance during pointer movement, and cancel behavior.
- `make app-frontend-check` — passed; existing Biome warnings only; client/server builds succeeded. npm reported 10 dependency audit findings.
- The first toolbar run lacked installed dependencies; after `npm ci`, a concurrent frontend gate reinstalled dependencies and caused a transient Playwright module-resolution error. Sequential toolbar rerun passed.
- ADR 0015 already listed all modified frontend paths; no inventory update was needed. No scope deviation or remote actions.
- Implementation commit: `b71ae66`; planning-only status/TODO commit follows separately.

### 55.4.1 — Integrated validation and handoff
- Integrated root branch: `feature/local-dev-trial`; all five implementation tasks are complete and the working tree is clean.
- `make check` — Ruff passed, 771 files formatted, 993 passed / 3 skipped / 45 deselected.
- `make app-check` — Ruff passed, 20 files formatted, 297 passed.
- `make app-frontend-check` — passed; client/server builds succeeded. Biome emitted 11 existing warnings; npm reports 10 dependency audit findings (4 low, 6 moderate).
- Focused Node tests: corridor geometry/session 10 passed; distance 2 passed; corridor session 5 passed.
- Focused Playwright: corridor-map 3 passed; map-toolbar 5 passed; tool-card 1 passed.
- No network tests, deployment, push, or remote actions.
- Plan 55 is complete; this report is the final handoff.
