# TODO

## Goal
Deliver the approved PR #100 review fixes and guided Site Assessment interview/confirmation flow on the current checkout `feature/sa-checklist2`, with local validation and dev-app verification only after separately approved remote actions.

## Tasks

### 1. Merge and establish validation baseline
- [x] Confirm the current branch is `feature/sa-checklist1` in `D:\workspace\fpac-soil-mcp`; preserve the existing `.worktrees\` and their registered worktrees.
- [x] Merge `origin/main` into the task branch, resolving `planning\GOALS.md` by retaining both sides; use the locally available tracking ref and do not fetch or perform any other remote action. Merge commit: `1759c65`; origin-side goals were assigned unique IDs G21/G22 to avoid collisions.
- [x] Run `make check`, `make app-test`, `make app-lint`, and `make app-frontend-check`; record test counts and frontend lint/build results. Merged tree: root 1,017 passed / 45 deselected, 4,645 files formatted; app 183 passed, Ruff check/format passed; frontend lint 0 errors / 10 warnings and client/server builds passed.
- [x] Report dependency-related breakage: no lockfile or `mlflow`/`openai`/`agents` test/build breakage found; the app tests passed with the updated lockfile. `npm ci` reported 10 audit advisories (4 low, 6 moderate); no automatic dependency fixes were applied.

### 2. Fix review findings and conservative missing-input scoring
- [x] Exclude CDL overlays from MapPanel identify and Use-as-AOI handling; add a test proving a CDL click makes no TIGERweb request. Commit `8a00bbb`.
- [x] Build CDL context and histogram coordinate reference systems from service WKID or WKT using `pyproj.CRS.from_user_input`; add non-4326 WKT service tests for both paths. Commit `a0f1ad9`.
- [x] Validate Site Assessment criteria resource bands in `agent.py`: non-empty `band_id`/`label`, numeric-or-null points within `max_points`, and bounds consistent with the registry; disable interview on malformed resource and test each rejected field. Tests and app lint pass; test fixtures now load the authoritative bundled registry.
- [ ] Reject stale CDL results for unavailable/replaced AOIs in `ShowOnMapButton` before storing `cdlSummary`; add a replaced-AOI regression test.
- [ ] Score unknown, unavailable, or skipped Site Assessment criteria at maximum points with `assumed_conservative` labels; keep the result undetermined and expose a separate conservative bound.
- [ ] Update contracts/tests and the system prompt for conservative missing-input scoring, and add ADR 0018 documenting the decision.

### 3. Correct interview triggering and CDL tool flow
- [ ] Update agent instructions so a LESA request runs soil screening first, then offers Start/Skip for the interview (LE only), before any LESA call.
- [ ] Request CDL context once automatically for pasted WKT/GeoJSON or attached AOIs; do not call `analyze_cdl_histogram` after `analyze_cdl_context`.
- [ ] Add evaluation cases replaying the traced prompt and verify the interview/CDL sequence.

### 4. Add structured Site Assessment interview and confirmation gate
- [ ] Add an agent function tool that emits one criterion from the validated resource, with question, citation, resource-defined band choices, evidence/comment, and user/agent/tool provenance.
- [ ] Preserve answers, comments, provenance, skipped, and unknown states as structured history items; do not add Lakebase persistence.
- [ ] Require a confirmed summary in history that matches submitted answers before `calculate_preliminary_lesa`; derive points from selected bands rather than model-supplied points.
- [ ] Treat the summary card's explicit Confirm as the user approval; block the LESA MCP call agent-side unless conversation history contains a confirmed summary matching the submitted answers. Do not add a LESA-only MCP approval exception.
- [ ] Add tests proving calls are blocked without confirmation and on answer mismatch, and allowed after matching confirmation; cover structured answers and skipped/unknown states.

### 5. Add frontend interview cards
- [ ] Add a distinct Site Assessment question card that explains the criterion, shows registry-defined choices, citations and point schedules, and captures an optional comment and provenance as a structured answer.
- [ ] Add a summary card with Confirm/Edit actions, visually separated from response text using existing design tokens; Confirm creates the structured confirmation record.
- [ ] Add Playwright interaction tests for click-to-structured-answer and confirmation behavior; verify frontend lint/build with no new errors.

### 6. Verify, document, and close PR review
- [ ] Run targeted tests for each changed behavior and the repository/app checks required by the touched code.
- [ ] Review the final diff and update `planning\STATE_51.md` with the verified implementation and validation results.
- [ ] Ask for explicit approval before any push; after approval and redeployment, run one end-to-end interview on the dev apps.
- [ ] Verify dev traces show tool-routed questions, LESA only after Confirm and a matching history record, and conservative maximums labelled assumed. Follow ADR 0016: AOI geometry may appear in chat/tool traces; do not claim it is redacted.
- [ ] Reply to the five Copilot review threads only after the user explicitly authorizes remote actions; record closure status.

## Notes
- Workspace and branch: `D:\workspace\fpac-soil-mcp`, `feature/sa-checklist2` (current HEAD `151819c`); the user approved continuing on this current checkout, not switching to `feature/sa-checklist1` or a Databricks clone. Docs-only commits `f709c21` and `151819c` advanced the branch after the recorded test baseline at `7e8f71f`.
- The user specified `origin/main` as the merge source and approved resolving the `planning\GOALS.md` conflict by keeping both sides. The locally available `origin/main` was `16d592c`, merged by commit `1759c65`; colliding origin-side goal identifiers were renumbered to G21/G22. No fetch, push, PR update, comment, or other remote action is authorized by this plan; pushes and review-thread replies require separate explicit approval.
- Preserve the pre-existing untracked `.worktrees\` directory and all registered worktrees.
- Root `AGENTS.md` and `README.md` were committed in docs-only commit `f709c21` while this planning task was in progress; do not overwrite or revert those changes.
- Replace the existing tracked root `TODO.md` with this plan. Track planning artifacts and commit the approved plan/status/archive separately using `docs(planning):` commits.
- Pause and report Dependabot-related breakage before attempting a fix.
- The frontend install took about 8 minutes; its `db:migrate` step skipped safely because no database configuration was present.
- The frontend validation gate is lint and build; do not add `tsc` because upstream already fails it. Validate the CDL type correction with a targeted test.
- A pasted WKT/GeoJSON AOI counts as the AOI for automatic CDL context.
- Answers/comments/provenance remain structured tool-call items in conversation history and MLflow traces; Lakebase persistence is deferred to a follow-up PR.
- Missing Site Assessment inputs use conservative maximum points, remain labelled `assumed (no evidence)`, and leave the result undetermined, leaning toward the FPPA process being required unless evidence disproves it.
- Dev apps are `agent-fpac-soil-dev` and `mcp-fpac-soil-dev`; baseline deployment is `a1e1e66`. End-to-end verification is contingent on separately approved push/redeployment.
- Preserve accepted ADR 0016: geometry may appear in chat/tool traces. The earlier no-geometry trace acceptance is withdrawn.
- The confirmation model is Confirm-only: the user's summary-card Confirm plus the agent-side matching-history check; no separate MCP Approve click is required for LESA.
- Use the already-installed Playwright dependency for frontend interaction tests; do not add a React component-testing dependency.
