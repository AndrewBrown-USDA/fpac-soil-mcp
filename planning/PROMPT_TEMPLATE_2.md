# Worker Prompt Template — Orchestration 2

You are implementing exactly one scoped task in `fpac-soil-mcp`, supervised by an orchestrator that reviews your plan before you may write code.

## Task {{id}}: {{title}}

{{task_spec_verbatim}}

## Ground Rules (Non-negotiable)
- NEVER write code or run state-changing commands before your plan is approved by the orchestrator.
- NEVER touch files outside "Files in scope"; if required, STOP and report immediately.
- NEVER go off-plan; any discovered work goes in "## Discovered" and waits.
- NEVER assume: resolve unknowns by reading existing documentation in Analysis; anything still ambiguous becomes numbered questions (max 5) in your plan report.
- If a check fails twice for the same reason, stop and report — do not thrash.
- Keep the master plan strategic. Reference the research report instead of copying technical specifics.

## [Worker] Phase 1 — Analysis
Read:
1. `AGENTS.md` or the repository instructions supplied by the orchestrator
2. `planning/EXECUTION_PLAN_2.md` (task spec and constraints)
3. `planning/STATE_2.md` (reports from dependent tasks)
4. `planning/MASTER_PLAN.md`
5. `planning/RESEARCH_PUBLIC_APIS_AND_INTERPRETATIONS.md`
6. The named grep anchors

## [Worker] Phase 2 — Micro-planning
Write `planning/tasks/{{id}}.todo.md`:
```markdown
# {{id}} — {{title}}

## Goal
<one clear sentence>

## TODO Items
- [ ] Step 1: <concrete action>
- [ ] Step 2: <concrete action>
...
- [ ] Step N: Run targeted checks (<command>)

## Notes
<facts discovered in Analysis, constraints honored, risks identified>

## Questions
<numbered, max 5, or 'None'>
```
Output the file contents as your report and END YOUR TURN. Wait for orchestrator approval.

## [Worker] Phase 3 — Execution
Work the TODO strictly in order, flipping `- [ ]` to `- [x]`. Match the surrounding documentation style. Run only the targeted checks named in the spec.

## [Worker] Phase 4 — Reporting
Append to `planning/STATE_2.md` under `## {{id}}` (at most 15 lines):
- Status: `done` / `blocked`
- Files created or changed with line ranges
- Exact check commands and results
- Deviations from the approved plan (or "none")
- Gotchas / notes for dependent tasks

