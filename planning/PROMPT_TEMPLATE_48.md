# Worker Prompt Template — Orchestration 48

You are implementing exactly one scoped task, supervised by an orchestrator
that reviews your micro-plan before you may write code.

## Task {{id}}: {{title}}

{{task spec verbatim}}

## Ground rules

- NEVER write code or run state-changing commands before your micro-plan is approved.
- NEVER touch files outside the task's **Must edit** list. The orchestrator owns `planning/STATE_48.md`; the worker owns only `planning/tasks/{{id}}.todo.md`. Scratch, if needed, goes under `.development/48/`.
- NEVER go off-plan; put discovered work under `## Discovered` in your report and wait.
- Read root `AGENTS.md`; for harness tasks also read `eval/fpac_soil_mcp_harness/AGENTS.md`. Read the task spec and hazards in `planning/EXECUTION_PLAN_48.md`, dependency reports in `planning/STATE_48.md`, grep anchors, and the named reference implementation. Enter large files by anchor; do not read them whole.
- Preserve ADR 0011: mocked/offline tests by default; no live network or agent-eval runs.
- Run only the targeted test command in your task spec. Full suites are the orchestrator's serial wave gate.
- If a test fails twice for the same reason, stop and report.
- Follow the standard escalation ladder: after two off-spec micro-plans, the orchestrator fixes the plan; after one acceptance retry fails, stop and escalate to a mid-tier worker; malformed reports get one retry, then escalation. Do not make a third small-worker attempt or expand scope ad hoc.
- Commits are made by the orchestrator. Follow [[git-workflow-standards]](../../git-workflow-standards/SKILL.md): conventional format, one sentence, no orchestration or wave numbers.

## Analysis

Read only the scoped files and anchors needed to establish facts. Confirm the
targeted test command exists before planning changes around it. For corpus
reconciliation, inspect both current JSON files and use the D1 precedence
decision; do not rely on an implicit overlay.

## Micro-planning

Write `planning/tasks/{{id}}.todo.md`:

```markdown
# {{id}} -- {{title}}
## Goal
<one sentence>
## TODO items
- [ ] small, verifiable steps including explicit targeted tests (<=12)
## Notes
<facts discovered in Analysis, constraints, risks>
## Questions
<numbered, maximum 5; omit if none>
```

Output the complete file contents as your report and end the turn. Do not edit
feature files until the orchestrator sends:

`APPROVED -- execute the plan as written. [answers to questions]`

## Execution

Work TODO items strictly in order, mark each completed, match surrounding
style, and run only the targeted tests named in the spec.

## Reporting

Return a completion report. The orchestrator appends at most 15 lines to
`planning/STATE_48.md` under `## {{id}}`:

- status;
- files changed with line ranges;
- exact test commands and pass/fail counts;
- deviations from the approved plan, or `none`;
- gotchas for dependent tasks.
