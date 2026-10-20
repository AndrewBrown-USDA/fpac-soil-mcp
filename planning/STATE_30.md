# Orchestration 30 State

## Baseline checklist

- [x] Existing orchestration identified: 29; this plan is 30.
- [x] `git status --short` recorded: unrelated modified `Makefile`; do not touch.
- [x] Offline project suite: 314 passed, 14 deselected.
- [x] Focused eval suite: 28 passed, 2 deselected.
- [x] `uv run ruff check .`: passed.
- [x] `uv run ruff format --check .`: passed; 356 files formatted.
- [x] `git diff --check`: baseline clean apart from the unrelated `Makefile` change.
- [x] Agent-eval baseline status: not run during planning; deferred to serial closure after offline gates.
- [x] Accepted ADRs reviewed: 0001, 0003, 0011; no supersession required.
- [x] Research copied to `planning\RESEARCH_EVAL_FAILURES_30.md`.

## Wave board

| Task | Wave | Status | Worker | Notes |
|---|---:|---|---|---|
| 30.1.1 | 1 | done | worker-30.1.1-execution | Direct FastMCP prompt rendering tests verified |
| 30.2.1 | 2 | done | worker-30.2.1-plan | Explicit prompt instructions and gateway diagnostics verified |
| 30.3.1 | 3 | done | worker-30.3.1-plan | Eval regressions for all three failures verified |
| 30.4.1 | 4 | done | worker-30.4.1-plan | README documentation verified; closure gates pending |

## Task reports

<!-- Worker reports are appended below, one section per task, <=15 lines. -->

## Task 30.1.1 — Direct prompt-render regression coverage

- Status: complete.
- Changed `tests\test_server.py` only for planned point and corridor prompt assertions.
- Point coverage verifies the point lookup tool, regulatory boundaries, and preliminary limitation.
- Corridor coverage verifies `analyze_corridor_fppa`, § 658.5(c), 160 points, CPA-106, and preliminary limitation.
- Validation: `uv run pytest tests\test_server.py -q`
- Result: **16 passed, 3 deselected**.
- Deviations: one initial assertion capitalization mismatch was corrected; no production code changed.
- Unrelated pre-existing files remain untouched: `Makefile` and orchestration planning artifacts.
- Dependent-task gotchas: none identified; prompt names and direct FastMCP rendering remain stable.

## Task 30.2.1 — Making prompt execution and gateway diagnostics explicit

- Status: complete.
- Changed `eval\run_evals.py` only for implementation; appended this report to state.
- Prompt cases now explicitly instruct Pi to invoke/render the named MCP prompt first.
- Structured diagnostics retain bounded direct-call and nested `mcpScript` extraction.
- Diagnostics distinguish prompt mismatches, unavailable tool-list evidence, unadvertised tools, and advertised-but-not-executed tools.
- RES-01 retains exact `7 CFR Part 657`, `7 CFR Part 658`, and `preliminary` requirements.
- Validation: `uv run pytest eval\test_agent_eval.py -m "not agent_eval" -q`
- Result: **28 passed, 2 deselected**.
- Deviations: none.
- Wave 3 handoff: add regressions for prompt instruction text, bounded envelopes/prose exclusion, diagnostic distinctions, and exact RES-01 matching.

## Task 30.3.1 — Adding eval regressions for the three failures

- Status: complete.
- Changed `eval\test_agent_eval.py` and `planning\tasks\30.3.1.todo.md`; reused existing sanitized fixtures.
- Added PROMPT-01/PROMPT-02 instruction and structured prompt evidence regressions.
- Added exact RES-01 citation matching and near-match rejection coverage.
- Added verified initialization/tool-list envelope, prose exclusion, and diagnostic distinction coverage.
- Validation: `uv run pytest eval\test_agent_eval.py -m "not agent_eval" -q`
- Result: **33 passed, 2 deselected**.
- Deviations: no new fixture files were needed; existing sanitized envelopes covered the cases.
- Wave 4 gotchas: preserve prompt rendering semantics, exact RES-01 keywords, and structured-evidence-only diagnostics.

## Task 30.4.1 — Documenting operation and running closure gates

- Status: complete; documentation only.
- Changed `README.md` and `planning\tasks\30.4.1.todo.md`; no runtime or test files changed.
- Documented prompt rendering requirements, direct-vs-Pi test roles, exact citations, and structured-only diagnostics.
- Documented the six serial closure commands and orchestrator ownership of results.
- Validation: README diff reviewed; global closure gates pending.
- Deviations: none.
- Agent-eval and closure results will be appended by the orchestrator after serial execution.
