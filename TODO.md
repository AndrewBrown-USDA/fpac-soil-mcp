# TODO

## Goal
Simplify map workflows with explicit Area/Corridor modes, improve measurement completion and display, and expose the existing map legend in-map.

## Tasks

### 1. Add scoped Area/Corridor modes and shared naming
- [x] Add an accessible Area/Corridor mode toggle in the map toolbar that scopes visible drawing, edit, and screening tools to the selected mode.
- [x] Preserve existing AOI and corridor state/attachment semantics while switching modes; do not alter MCP schemas or screening payloads.
- [x] Reuse one name input for Area AOI naming and Corridor primary/alternative labeling where appropriate, without changing import/export geometry behavior.
- [x] Keep buffer distance/units, corridor status, feature removal, and screening options reachable in Corridor mode.

### 2. Improve measurement interaction
- [x] Place Measure distance on the same toolbar line as the other map tools.
- [x] Allow a deliberate finish gesture (double-click or equivalent) to complete a measured line and stop preview/drawing.
- [x] Keep a completed measurement visible until Clear measurement; toggling the measurement tool must not silently erase it.
- [x] Render distance in a map-anchored tooltip rather than in the toolbar/bezel; retain accessible distance text for assistive technology.

### 3. Integrate the map legend
- [x] Expose the existing legend content as a compact, collapsible overlay on the map.
- [x] Preserve server-provided map legend semantics and current map-result behavior; do not reconstruct server layers or legends in the browser.

### 4. Verify and commit
- [x] Update existing browser tests only to exercise meaningful final workflows: mode switching and naming, measurement completion/persistence/clear, and legend overlay.
- [x] Do not add tautological tests or checks that only assert removed UI is absent.
- [x] Update `docs/decisions/0015-vendored-agent-app-frontend.md` for each modified/added frontend path.
- [x] Run relevant isolated frontend tests, `make app-frontend-check`, and `git diff --check`.
- [x] Commit implementation and tracked planning/status separately; do not push, deploy, or perform remote actions.

## Notes
- Repository: `/home/andrew/work/fpac-soil-mcp`; continue on `feature/local-dev-trial`. Worktree was clean at plan creation.
- User decisions: modes scope visible tools; completed measurements remain until cleared; show distance in a map tooltip; show the existing legend in a map overlay; track planning artifacts separately.
- Relevant implementation is in `apps/agent-fpac-soil-openai-sdk/frontend/client/src/components/map/MapPanel.tsx`; toolbar and measurement behavior are in the same component. Existing legend components are `MapLegend.tsx` and `CDLLegend.tsx`.
- Keep AOI/corridor chat context mutually exclusive and preserve automatic corridor attachment, import/export, geometry validation, privacy controls, and MCP schemas/payloads.
- Follow `apps/agent-fpac-soil-openai-sdk/AGENTS.md`: update ADR 0015's frontend inventory and run `make app-frontend-check`; do not run rewrite-based upstream lint scripts.
- Meaningful existing browser suites include `test:map-toolbar`, `test:corridor-map`, and `test:map-legend`; inspect fixtures and add only behavior-focused coverage as needed.
- No remote actions are authorized.
- Validation: map toolbar 6 passed, corridor map 3 passed, map legend 4 passed; `make app-frontend-check` and `git diff --check` passed. Existing Biome warnings and npm audit findings remain.
- Implementation commit: `44df3f8` (`feat(agent-app): streamline map tools and measurement`); planning status commit follows separately.
