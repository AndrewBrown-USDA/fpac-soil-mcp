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
- User chose not to track this run’s planning changes. The root `TODO.md` is already tracked in Git, so its plan update will remain as a local modification and will not be staged or committed.
- Validation passed: map toolbar browser suite (6 tests), `make app-frontend-check`, and `git diff --check`.
