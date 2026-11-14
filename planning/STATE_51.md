# STATE 51: Structured Site Assessment Interview and Confirmation

Resume point for orchestration 51. Plan: `planning/EXECUTION_PLAN_51.md`.
Worker prompt: `planning/PROMPT_TEMPLATE_51.md`.

## Baseline (recorded before wave 1)

Baseline tests were recorded on branch `feature/sa-checklist2` at `7e8f71f`.
The current branch advanced through docs-only commits `f709c21` and `151819c`;
the test baseline remains applicable because those commits changed only
documentation.

- [x] Root pytest: 1,019 passed, 45 deselected. The final fixture-only update
  after this run was app-scoped; root pytest excludes `apps/`.
- [x] Root Ruff check and format check passed.
- [x] Agent-app pytest: 196 passed.
- [x] Agent-app Ruff check and format check passed.
- [x] Frontend read-only Biome lint and client/server builds passed; 10
  existing lint warnings, no errors.
- [x] Frontend `npm ci` completed; npm audit reported 10 existing advisories
  (4 low, 6 moderate). No automated dependency changes.
- [ ] Databricks-authenticated integrated chat trial — not run; local auth is
  not configured.
- [ ] Dev-app trial — pending separate explicit push/redeployment approval.
- [!] `make app-check` previously failed to start on this Windows host with an
  Rtools path error; direct `uv`/Ruff commands are the fallback.

## Decisions

- Continue on current branch `feature/sa-checklist2` at `151819c`; preserve the
  committed root `AGENTS.md`/`README.md` changes and all existing
  `.worktrees\`.
- Use at most two concurrent workers in new isolated `51.*` worktrees.
- Keep project-wide G1 active and add PR-scoped goals G23-G30.
- Preserve ADR 0016; geometry may appear in chat/tool traces.
- Use summary-card Confirm as the sole user approval; agent-side gate requires
  a matching confirmed-summary history record. No second MCP Approve step.
- Use existing Playwright for frontend interactions; no new component-test
  dependency and no TypeScript-check gate.
- Planning files are tracked; commit them separately with
  `docs(planning):` after plan approval.
- No remote actions are authorized by this plan.

## Wave Board

| Wave | Task | Status | Commit | Notes |
|---|---|---|---|---|
| 1 | 51.1.1 Conservative missing-input scoring and ADR 0018 | done | `2899a61` / `062bc30`; follow-ups `aafb797` / `abc1f9f`, `38c544f` / `9f65159`; merges `1afeecb`, `f5cd0a7`, `ef99795` | Conservative assumptions, regression contracts, and formatting verified. |
| 1 | 51.1.2 Structured Site Assessment tool/history contract | done | `f76e146` / `4fe9fea`; follow-up `e251d92` / `b4a1ce0`; merges `c7e3e5d`, `7412853` | Structured tools and scoped app Ruff checks verified. |
| 1 gate | Foundation contract checks | done | | Root: 1,023 passed, 45 deselected; Ruff check/format passed. App: 206 passed; Ruff check/format passed on changed owned files. |
| 2 | 51.2.1 Interview trigger/CDL sequence and eval cases | pending | | |
| 2 | 51.2.2 Question/summary cards, Playwright fixture, stale-CDL guard | pending | | |
| 2 gate | Interview flow and frontend checks | pending | | |
| 3 | 51.3.1 Confirm-only matching-history gate | pending | | |
| 3 gate | Serial integrated local acceptance | pending | | |
| 4 | Conditional dev-app trial | blocked | | Requires separate user approval to push/redeploy. |

## Worker Worktrees

Preserve all pre-existing worktrees from orchestration 50. Add new `51.*`
worktrees only when a wave starts; record their path, branch, and disposition
here.

| Task | Path | Branch | Created (local) | Status |
|---|---|---|---|---|
| 51.1.1 | `.worktrees\51.1.1` | `feature/sa-checklist2-51.1.1-worker` | 2026-11-13 17:08:16 -08:00 | complete; retain |
| 51.1.2 | `.worktrees\51.1.2` | `feature/sa-checklist2-51.1.2-worker` | 2026-11-13 17:08:16 -08:00 | complete; retain |

## Task Reports

<!-- Append one concise report per completed task; keep each to 15 lines max. -->

### 51.1.1 — Score missing Site Assessment inputs conservatively
- Status: complete; planning commits `2899a61`, `aafb797`, `38c544f`; code/style commits `062bc30`, `abc1f9f`, `9f65159`; integrated merges `1afeecb`, `f5cd0a7`, `ef99795`.
- Added registry-maximum assumptions with separate provenance and upper bound; actual awards remain zero for missing inputs and incomplete results remain undetermined. Added and indexed ADR 0018.
- Root targeted scoring/contracts — 96 passed; amended regression contracts and prompts — 171 passed; app prompt test — 33 passed with one existing config warning.
- Final `uv run --group dev pytest -q` — 1,023 passed, 45 deselected, 220 warnings.
- `uv run ruff check .` and `uv run ruff format --check .` — passed; 6,031 files already formatted.
- Plan scope was amended in `6919b42` after the full suite exposed directly coupled stale assertions; all were fixed within the amended scope. No remote actions.

### 51.1.2 — Add the structured Site Assessment tool contract
- Status: complete; planning commits `f76e146`, `e251d92`; code/style commits `4fe9fea`, `b4a1ce0`; integrated merges `c7e3e5d`, `7412853`.
- Added resource-backed question and answer function tools; agent construction enables them only with validated criteria context.
- Added tests for resource-derived choices/citations/points, provenance, unknown/skipped records, supplied-point rejection, and history pass-through.
- `uv run --frozen --python 3.11 pytest tests\test_site_assessment_tools.py tests\test_agent_construction.py tests\test_agent_mcp_wiring.py tests\test_history_normalization.py -q` — 51 passed, 1 existing `asyncio_mode` warning.
- Final app `uv run --frozen --python 3.11 pytest tests -q` — 206 passed, 122 existing warnings. Ruff check and format passed on the seven changed owned Python files.
- Whole-app Ruff also identified 19 findings in other app files and formatting issues in `scripts/app_diagnostics.py` and `scripts/start_app.py`; left untouched. Shared `history.py` was not changed. Answer records use `type: site_assessment_answer`; outputs are JSON strings in function-call history.

## Final Acceptance

- [x] Root tests and Ruff checks pass serially; 1,023 passed, 45 deselected; Ruff check/format passed.
- [x] Agent-app tests and Ruff checks pass on changed owned files; 206 passed; scoped Ruff check/format passed.
- [ ] Playwright question/confirmation tests, read-only Biome lint, and
  frontend build pass.
- [ ] Review final diff and ensure no user-owned edits or remote actions were
  included.
- [ ] Dev-app trial and review-thread replies remain blocked until separately
  authorized.
