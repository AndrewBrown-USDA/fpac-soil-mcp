# STATE 48: Evaluation Corpus Consolidation

Resume point for orchestration 48. Plan: `planning/EXECUTION_PLAN_48.md`.
Worker prompt: `planning/PROMPT_TEMPLATE_48.md`.

## Baseline (recorded before wave 1; 2026-11-12)

- [x] Repo `D:\workspace\fpac-soil-mcp`, branch `refactor/eval-corpus1`; worktree clean except user-provided untracked `planning/RESEARCH_ISSUE_88_EVAL_CORPUS_CONSOLIDATION.md` (preserve).
- [x] Offline Python: `uv run pytest -m "not live_network and not agent_eval" -q` — **951 passed, 45 deselected**.
- [x] Ruff: `uv run ruff check .` — passed; `uv run ruff format --check .` — passed (652 files already formatted).
- [x] Harness: from `eval\fpac_soil_mcp_harness`, `npm run check` — passed; `npm test` — **18 passed, 0 failed**.
- [x] Corpus inventory: 38 prompt cases, 19 overlapping harness cases, 19 prompt-only cases, 38 unique IDs, no duplicate IDs.
- [x] ADR review: ADR 0011 Accepted; keep all new validation offline and live/agent evaluations opt-in.
- [x] Harness smoke tests bind to ephemeral loopback ports. Run the full harness suite as one command; run all wave gates serially.

## Wave Board

| Wave | Task | Status | Commit | Notes |
|---|---|---|---|---|
| 1 | 48.1.1 Reconcile corpus and validate unified schema | done | `150faaf` | Planning commit `0e65eb8`; all Wave 1 gates passed |
| 2 | 48.2.1 Migrate Python evaluation readers and ID coverage | pending | | |
| 2 | 48.2.2 Load the unified corpus directly in the harness | pending | | |
| 3 | 48.3.1 Retire the duplicate corpus and update active references | pending | | |

## Task Reports

<!-- Orchestrator appends <=15 lines per task under ## <id>. -->

## 48.1.1
- Status: done; implementation commit `150faaf` (`feat(eval): unify corpus and validate harness fields`); planning commits `0e65eb8`, with this report recorded separately.
- Files: `eval/eval_cases.v1.json`, `eval/common/dataset.py`, `eval/common/test_common_dataset.py`.
- Targeted test: `uv run pytest eval/common/test_common_dataset.py -q` — 54 passed, 0 failed.
- Wave gate: `uv run pytest -m "not live_network and not agent_eval" -q` — 963 passed, 45 deselected.
- Wave gate: `uv run ruff check .` — passed; `uv run ruff format --check .` — passed (659 files formatted).
- Wave gate: from `eval\fpac_soil_mcp_harness`, `npm run check` — passed; `npm test` — 18 passed, 0 failed.
- Corpus checks: 38 unique rows; every Python source field preserved; all 19 prior harness rows and their five harness-only fields preserved; no stale behavior ID.
- Deviations: none. Ruff formatting was applied after the initial format gate identified two in-scope files.
- Dependency note: old corpus retained for the Wave 2 consumer migrations; Python `DEFAULT_PATH` now points to the unified corpus.
