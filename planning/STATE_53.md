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
| 1 | 53.1.1 Chat export serialization and privacy boundary | done | `66b8026`, `6545876` | ADR 0015 ledger scope amendment recorded; targeted tests pass |
| 2 | 53.1.2 Explicit chat export actions and warning | done | `0818dc8`, `450f9e5` | Frontend wave gate passed after focused lint correction |
| 3 | 53.2.1 Browser-only AOI label and GeoJSON exchange | done | `51369e1` | Focused AOI export and map identify tests pass |
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

### 53.1.1 — Define chat export serialization and privacy boundary
- Status: done; implementation `66b8026`, ADR ledger correction `6545876`.
- Added deterministic JSON/Markdown serialization and tests in `client/src/lib/chatExport.ts` and `client/src/lib/chatExport.test.ts`.
- ADR 0015 now lists both added paths; plan scope was amended after app guidance revealed its required local-change ledger.
- `node --import tsx --test client/src/lib/chatExport.test.ts` — 4 passed, 0 failed (worker and orchestrator reruns).
- No dependencies or manifests changed; no remote actions.

### 53.1.2 — Add explicit chat export actions and warning
- Status: done; implementation `0818dc8`, lint correction `450f9e5`.
- Added explicit Markdown/JSON export menu, sensitivity confirmation, download behavior, isolated Playwright fixture/spec, and ADR 0015 ledger entries; no dependencies added.
- `npm run test:chat-export` — 3 passed, 0 failed; `git diff --check` passed.
- Initial `make app-frontend-check` flagged new button-type/non-null-assertion errors; one focused retry fixed them. Rerun passed lint/build with 10 existing warnings and 10 npm advisories.
- Wave gate: `make check` — 993 passed, 3 skipped, 45 deselected; `make app-check` — 266 passed; `make app-frontend-check` passed.
- Existing upstream warnings/deprecations and no-database migration skip remain; no remote actions.

### 53.2.1 — Add browser-only AOI label and GeoJSON exchange
- Status: done; implementation `51369e1`.
- Added local-only AOI label UI, GeoJSON copy/download, clipboard feedback, sanitized filenames, serializer tests, and ADR 0015 entries.
- `node --import tsx --test client/src/components/map/aoiExport.test.ts` — 3 passed; `npm run test:map-identify` — 1 passed; diff check passed.
- Label is component-local and excluded from `ActiveAoi` context and server/chat payloads; no dependencies or remote actions.

## Final Acceptance

- [ ] All task reports and code commits recorded.
- [ ] `make app-check` passes.
- [ ] `make app-frontend-check` passes; existing warnings are documented.
- [ ] Focused Playwright and map identify suites pass, or explicitly documented as unavailable/waived.
- [ ] `git diff --check` passes; ADR 0015 ledger is complete.
- [ ] No remote actions performed.
