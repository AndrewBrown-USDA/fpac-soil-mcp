# TODO

## Goal
Tighten the Area toolbar by combining draw/edit tools under “Area of interest” and swapping the AOI outline/zoom icons as requested.

## Tasks

### 1. Update the Area toolbar
- [x] Combine the existing “Draw area” and “Edit area” control groups into one “Area of interest” band, retaining all buttons and behavior.
- [x] Use the dotted-box/scan icon for the AOI outline visibility toggle and a magnifying-glass icon for Zoom to AOI.
- [x] Run the focused map-toolbar browser test and `make app-frontend-check`; ensure `git diff --check` passes.
- [x] Update the ADR 0015 frontend inventory and commit the implementation locally; do not push or perform remote actions.

## Notes
- Repository: `/home/andrew/work/fpac-soil-mcp`, branch `feature/local-dev-trial`; worktree was clean at plan creation.
- Likely implementation path: `apps/agent-fpac-soil-openai-sdk/frontend/client/src/components/map/MapPanel.tsx`; existing toolbar coverage is `apps/agent-fpac-soil-openai-sdk/frontend/tests/map-toolbar/toolbar.spec.ts`.
- Follow `apps/agent-fpac-soil-openai-sdk/AGENTS.md`; no new test is needed if existing meaningful toolbar coverage is sufficient.
- The previous run’s plan was initially left as a local modification; user now directs committing the outstanding TODO changes.
- Validation passed: map toolbar browser suite (6 tests), `make app-frontend-check`, and `git diff --check`.

---

## Follow-up TODO: map results and controls

### Goal
Fix map visibility/tooltips, improve results and legend presentation, and make corridor options more compact.

### Tasks

#### 1. Fix map controls
- [ ] Make AOI outline visibility toggle both the MapLibre outline and editable AOI geometry visible/invisible.
- [ ] Allow disabled toolbar buttons to show their tooltips on hover and keyboard focus.
- [ ] Remove the default white popup container/halo around the map-anchored measurement tooltip while retaining accessible tooltip text.

#### 2. Improve results and legend
- [ ] Widen the desktop map/results pane to 50% while keeping it within the viewport; make the map-unit table horizontally scroll rather than clip long text.
- [ ] Remove the redundant screening map legend from the Results tab; retain the results table and map-tab legend.
- [ ] Put the server-provided farmland-class legend first in the map legend, followed by the CDL color key, then other screening layer details/disclaimers.
- [ ] Move the CDL color key out of the Layers control and into the map legend beneath farmland classes.

#### 3. Compact corridor options
- [ ] Place corridor options as a compact second toolbar row, right-aligned below the corridor controls and measure tool.
- [ ] Reduce excess whitespace and condense the buffer-distance caveat without removing required caveat information or corridor settings/actions.

#### 4. Verify and commit
- [ ] Add/update behavior-focused tests for AOI outline visibility, disabled-button tooltips, results/table width, map legend ordering/CDL placement, and corridor options layout.
- [ ] Update `docs/decisions/0015-vendored-agent-app-frontend.md` for all changed frontend paths.
- [ ] Run relevant map-toolbar, map-legend, corridor-map tests, `make app-frontend-check`, and `git diff --check`.
- [ ] Commit implementation locally; commit planning-only updates separately with a `docs(planning):` message; do not push or perform remote actions.

### Notes
- Continue on `feature/local-dev-trial`; the pre-existing local TODO modification is user-owned and preserved above.
- User decisions: widen the desktop panel to 50% and also use horizontal scrolling to keep full map-unit text readable; commit planning updates separately.
- Follow `apps/agent-fpac-soil-openai-sdk/AGENTS.md`. No server/MCP schema changes or remote actions.
