# TODO

## Goal
Replace the large, separate corridor drawing fieldset with compact accessible corridor controls integrated into the map toolbar, while preserving the corridor workflow.

## Tasks

### 1. Consolidate corridor controls
- [ ] In `apps/agent-fpac-soil-openai-sdk/frontend/client/src/components/map/MapPanel.tsx`, replace the large separate `Corridor (separate from AOI)` fieldset with compact icon-only controls integrated into the existing map toolbar.
- [ ] Give primary line, alternative line, staging area, edit, screen, and clear actions accessible names and hover/focus labels.
- [ ] Keep alternative label, buffer distance/units, corridor status, feature removal, and screening options reachable in a compact disclosure associated with the toolbar.
- [ ] Preserve AOI controls, corridor geometry state, automatic chat attachment, and existing MCP screening payloads and schemas.

### 2. Verify meaningful behavior
- [ ] Review existing `frontend/tests/corridor-map/corridor-map.spec.ts` and `frontend/tests/map-toolbar/toolbar.spec.ts`; modify or add coverage only if needed to exercise final user workflows through the consolidated controls (draw/edit, settings, screening, removal/clear).
- [ ] Do not add tautological tests, tests that only assert the old fieldset is absent, or tests of removed/intermediate UI.
- [ ] Update `docs/decisions/0015-vendored-agent-app-frontend.md` for every changed or added frontend path.
- [ ] Run `npm run test:corridor-map` and `npm run test:map-toolbar` from `apps/agent-fpac-soil-openai-sdk/frontend/`, then run `make app-frontend-check` and `git diff --check`.

### 3. Commit and record
- [ ] Make a focused local implementation commit after verification; update this TODO and record test results in a separate planning-only commit.
- [ ] Do not push, deploy, or perform other remote actions.

## Notes
- Repository: `/home/andrew/work/fpac-soil-mcp`, branch `feature/local-dev-trial`; do not switch branches.
- The visible defect is in `MapPanel.tsx`: the AOI toolbar occupies the “AOI tools” toolbar, while a separate fieldset labeled `Corridor (separate from AOI)` still renders large text buttons for Draw primary/alternative, Edit, Draw staging, Screen, and Clear.
- Relevant `MapPanel.tsx` anchors: AOI toolbar around lines 835–877; corridor fieldset around lines 879–902; callbacks/state include `startCorridorDrawing`, `clearCorridor`, `removeCorridorFeature`, `corridorScreening.run`, buffer settings, and alternative labels.
- Plan 55 decisions: keep AOI and Corridor tools visible as compact accessible icon controls; AOI and Corridor are mutually exclusive chat contexts; one shared chip detaches the active context.
- Keep screening, alternative labels, buffer distance/units, status, remove-feature, and clear workflows available. Do not change server/MCP schema or coordinate/privacy behavior.
- Scoped frontend paths: `apps/agent-fpac-soil-openai-sdk/frontend/client/src/components/map/MapPanel.tsx`, `client/src/components/map/corridor-map-fixture.tsx`, `client/map-toolbar-fixture.html`, `tests/corridor-map/corridor-map.spec.ts`, `tests/map-toolbar/toolbar.spec.ts`, and `docs/decisions/0015-vendored-agent-app-frontend.md`. Limit edits to paths actually needed.
- `apps/agent-fpac-soil-openai-sdk/AGENTS.md` requires updating ADR 0015's local-change inventory alongside vendored frontend changes. Use `make app-frontend-check`; do not run rewrite-based upstream lint scripts.
- Last integrated baseline (Plan 55): `make check` passed (993 passed, 3 skipped, 45 deselected); `make app-check` passed (297 passed); `make app-frontend-check` passed. Existing frontend warnings/audit findings are recorded in `planning/STATE_55.md`.
- Planning artifacts are tracked separately. No push, deploy, or other remote action is authorized.
