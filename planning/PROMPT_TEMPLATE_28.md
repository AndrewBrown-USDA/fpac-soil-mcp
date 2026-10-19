# Prompt Template — Orchestration 28

You are implementing exactly one scoped task, supervised by an orchestrator
that reviews your plan before you may write code.

## Task {{id}}: {{title}}
{{task spec verbatim from EXECUTION_PLAN_28.md}}

## Ground rules (non-negotiable)
- NEVER write code or run state-changing commands before your plan is approved.
- NEVER touch files outside "Files in scope"; if required, STOP and report.
- NEVER go off-plan; discovered work goes in "## Discovered" and waits.
- NEVER assume: resolve unknowns by reading code in Analysis; anything still
  ambiguous becomes numbered questions (max 5) in your plan report.
- If a test fails twice for the same reason, stop and report — do not thrash.

## Project conventions
- **Conventions file:** `AGENTS.md` at repo root
- **Repo:** `fpac-soil-mcp` at `/Workspace/Users/andrew.g.brown@usda.gov/fpac-soil-mcp`
- **Branch:** `feat/phase-4-part-2-sdv-routing`
- **Python style:** Type annotations, `from __future__ import annotations`,
  Google-style docstrings, 4-space indent
- **Test runner:** `pytest` from repo root
- **Offline test command:** `pytest tests/ -x -q --deselect tests/test_live_sda.py`
- **Live test command:** `pytest tests/test_live_sda.py -x -q --live`
  (requires network access to SDA endpoint)
- **Commit format:** Conventional commits with domain scopes
  (e.g. `fix(sda):`, `test(analysis):`, `docs(adr-0008):`). One sentence,
  no phase/wave numbers in the message.
- **Temp/scratch:** `.development/` (untracked)
- **Ignore:** EXE002 lint suppressions (pre-date this review)

## [Worker] Analysis
Read:
1. `AGENTS.md` at repo root
2. The task spec section from `planning/EXECUTION_PLAN_28.md`
3. `planning/STATE_28.md` — reports of dependency tasks (if any)
4. The grep anchors listed in the task spec
5. The named reference implementation(s)

## [Worker] Micro-planning
Write `planning/tasks/{{id}}.todo.md`:
```
# {{id}} — {{title}}
## Goal        <one sentence>
## TODO items  - [ ] small, verifiable steps incl. explicit test steps
## Notes       <facts discovered in Analysis, constraints honored, risks>
## Questions   <numbered, max 5, omit if none>
```
Output the file contents as your report and END YOUR TURN.

## [Worker] Execution
Work the TODO strictly in order, flipping `- [ ]` to `- [x]`. Match
surrounding code style. Run only the targeted tests named in the spec.

## [Worker] Reporting
Append to `planning/STATE_28.md` under `## {{id}}` (≤15 lines):
- Status (done / blocked / failed)
- Files changed with line ranges
- Exact test commands + pass/fail counts
- Deviations from the approved plan (or "none")
- Gotchas for dependent tasks
