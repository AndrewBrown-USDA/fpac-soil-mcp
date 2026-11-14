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
| 1 | 51.1.1 Conservative missing-input scoring and ADR 0018 | done | `2899a61` / `062bc30`; follow-ups `aafb797` / `abc1f9f`, `38c544f` / `9f65159`; merges `1afeecb`, `f5cd0a7`, `ef99795` | Regression tests and formatting fixes passed targeted validation; shared gate remains in progress. |
| 1 | 51.1.2 Structured Site Assessment tool/history contract | in_progress | `f76e146` / `4fe9fea`; merge `c7e3e5d` | App suite passes; approved scoped Ruff follow-up executing. |
| 1 gate | Foundation contract checks | in_progress | | Root pytest: 1,023 passed, 45 deselected; root Ruff check passed; root format check awaits post-format rerun. App pytest: 206 passed; approved scoped Ruff follow-up executing. |
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

### 51.1.2 — Add the structured Site Assessment tool contract
- Status: complete; planning commit `f76e146`, implementation commit `4fe9fea`, integrated by merge `c7e3e5d`.
- Added resource-backed question and answer function tools; agent construction enables them only with validated criteria context.
- Added tests for resource-derived choices/citations/points, provenance, unknown/skipped records, supplied-point rejection, and history pass-through.
- `uv run --frozen --python 3.11 pytest tests\test_site_assessment_tools.py tests\test_agent_construction.py tests\test_agent_mcp_wiring.py tests\test_history_normalization.py -q` — 51 passed, 1 existing `asyncio_mode` warning.
- Deviations: none; shared `history.py` was not changed. Dependent-task note: answer records use `type: site_assessment_answer`; tool outputs are JSON strings in function-call output history.

## Final Acceptance

- [ ] Root tests and Ruff checks pass serially; record exact counts.
- [ ] Agent-app tests and Ruff checks pass; record exact counts.
- [ ] Playwright question/confirmation tests, read-only Biome lint, and
  frontend build pass.
- [ ] Review final diff and ensure no user-owned edits or remote actions were
  included.
- [ ] Dev-app trial and review-thread replies remain blocked until separately
  authorized.
