# TODO

## Goal
Require the agent to retrieve each Site Assessment interview question from the validated question tool before presenting it.

## Tasks

### 1. Make question retrieval explicit
- [ ] Update the system prompt and question-tool description to require a `get_site_assessment_question` call for every criterion, before presenting its question and scoring choices.
- [ ] Add a focused prompt assertion covering the per-criterion tool-call requirement.

### 2. Validate and commit
- [ ] Run the focused agent prompt tests and `make app-check`; run `git diff --check`.
- [ ] Commit the implementation and its test as one focused local commit; do not push or perform remote actions.

### 3. Commit existing work and clean the tree
- [ ] Review and validate the existing map interaction changes, then commit them in a separate focused Conventional Commit.
- [ ] Commit their related planning/documentation changes separately using `docs(planning):`.
- [ ] Archive this completed TODO under `planning/` and commit the planning archive/status separately.
- [ ] Confirm the working tree is clean; do not push or perform remote actions.

## Notes
- Repository: `/home/andrew/work/fpac-soil-mcp`; continue on `feature/map-interaction-stability`.
- Planning artifacts are tracked; commit planning changes separately with `docs(planning):`.
- Archived the previous completed root TODO at `planning/TODO_20261116-7.md`.
- User authorized committing the pre-existing map and planning edits to leave the tree clean; keep them separated by implementation and planning purpose.
