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
| 1 | 48.1.1 Reconcile corpus and validate unified schema | pending | | |
| 2 | 48.2.1 Migrate Python evaluation readers and ID coverage | pending | | |
| 2 | 48.2.2 Load the unified corpus directly in the harness | pending | | |
| 3 | 48.3.1 Retire the duplicate corpus and update active references | pending | | |

## Task Reports

<!-- Orchestrator appends <=15 lines per task under ## <id>. -->
