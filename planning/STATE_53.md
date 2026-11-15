# STATE 53: Map and Chat UI Enhancements

Resume point for orchestration 53. Plan: `planning/EXECUTION_PLAN_53.md`. Worker prompt: `planning/PROMPT_TEMPLATE_53.md`.

## Baseline (before wave 1)

- [x] Branch `feature/local-dev-trial`, clean at `757af9a` before planning edits.
- [x] `make check`: 952 passed, 3 skipped, 45 deselected.
- [x] `make app-check`: passed, 177 tests.
- [x] `make app-frontend-check`: lint/build passed; 10 existing lint warnings; npm audit reported 10 advisories.
- [ ] Re-run current baseline if implementation starts after branch changes.

## Decisions

- Plan 53 follows tracked orchestration 52 on `feature/local-dev-trial`.
- Chat export early; include visible conversation and raw tool data/geometry with warning and explicit action; exclude hidden reasoning/traces.
- NAIP uses user-supplied fixed USGS ImageServer URL.
- AOI label is browser-only and included in GeoJSON export, not agent/MCP context.
- Map/Results tabs auto-select Results after successful screening.
- Distance units selectable; layer order persisted locally; only raster/context order is user-controlled; vectors remain above rasters.
- Up to two concurrent workers; never parallelize edits to `MapPanel.tsx`.
- Planning artifacts tracked and committed separately. No remote actions authorized.

## Wave Board

| Wave | Task | Status | Commit | Notes |
|---|---|---|---|---|
| 1 | 53.1.1 Chat export serialization and privacy boundary | pending | | |
| 2 | 53.1.2 Explicit chat export actions and warning | pending | | Depends on 53.1.1 |
| 3 | 53.2.1 Browser-only AOI label and GeoJSON exchange | pending | | |
| 3 | 53.2.2 Map navigation, boundary visibility, and line measurement | pending | | Sequenced after 53.2.1; MapPanel hotspot |
| 4 | 53.3.1 Fixed NAIP imagery overlay | pending | | |
| 4 | 53.3.2 Persist raster order; vector-on-top invariant | pending | | Sequenced after 53.3.1 |
| 4 | 53.3.3 Improved map legends and layer semantics | pending | | Disjoint files from overlay tasks |
| 5 | 53.4.1 Map/Results tabs and post-screening switch | pending | | Depends on 53.2.2 and 53.3.3 |
| 5 | 53.4.2 Identify wording and accessibility polish | pending | | Disjoint files |
| 6 | Integrated serial validation and handoff | pending | | |

## Worker Worktrees

| Task | Path | Branch | Created | Status |
|---|---|---|---|---|

## Task Reports

<!-- Append concise reports (15 lines max per task). -->

## Final Acceptance

- [ ] All task reports and code commits recorded.
- [ ] `make app-check` passes.
- [ ] `make app-frontend-check` passes; existing warnings are documented.
- [ ] Focused Playwright and map identify suites pass, or explicitly documented as unavailable/waived.
- [ ] `git diff --check` passes; ADR 0015 ledger is complete.
- [ ] No remote actions performed.
