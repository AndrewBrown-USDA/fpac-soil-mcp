# Worker Prompt Template — Orchestration 49

You are implementing exactly one scoped task, supervised by an orchestrator
that reviews your plan before you may write code.

## Task {{id}}: {{title}}

{{task spec verbatim}}

## Ground rules

- NEVER make implementation changes or run implementation state-changing commands before your micro-plan is approved.
- NEVER touch files outside the task's **Must edit** list. The orchestrator owns `planning/STATE_49.md`; the worker owns only `planning/tasks/{{id}}.todo.md`. Scratch, if needed, goes under `.development/49/`.
- NEVER go off-plan; put discovered work under `## Discovered` in your report and wait.
- Read root `AGENTS.md`, the task spec and hazards in `planning/EXECUTION_PLAN_49.md`, dependency reports in `planning/STATE_49.md`, grep anchors, and the named reference implementation. Enter large files by anchor; do not read them whole.
- Preserve ADR 0011: mocked/offline tests are the default; no live call from unit tests. Preserve ADR 0012's separate-client boundary.
- Never add credentials, PATs, secret values, full principal identifiers, or raw request/response bodies to code, logs, tests, or evidence.
- Do not create identities, change grants, deploy applications, or alter workspace configuration. The dedicated service principal and `CAN_USE` grant are external prerequisites.
- Workers do not perform remote actions. The orchestrator owns the live Databricks smoke after the external prerequisite is verified.
- Run only the targeted test command in your task spec. Full `make check` is the orchestrator's serial wave gate.
- If a test fails twice for the same reason, stop and report.
- Follow the standard escalation ladder: after two off-spec micro-plans, the orchestrator fixes the plan; after one acceptance retry fails, stop and escalate to a mid-tier worker; malformed reports get one retry, then escalation. Do not make a third small-worker attempt or expand scope ad hoc.
- After approval and successful targeted verification, make a focused local Conventional Commit for the task's code. Do not push or take other remote action. Follow [[git-workflow-standards]](../../git-workflow-standards/SKILL.md): one sentence, no orchestration or wave numbers.

## Analysis

Read only the scoped files and anchors needed to establish facts. Confirm the
targeted test command exists before planning changes around it. Use
`WorkspaceClient.apps.get(...)` and the T1 CLI/notebook patterns as references;
do not read or expose credential values.

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
style, and run only the targeted test command named in your task spec. Keep
planning-only changes out of the code commit; the orchestrator commits tracked
plan/state changes separately with `docs(planning):`.

## Reporting

Return a completion report. The orchestrator appends at most 15 lines to
`planning/STATE_49.md` under `## {{id}}`:

- status;
- files changed with line ranges;
- code commit IDs;
- exact targeted test commands and pass/fail counts;
- deviations from the approved plan, or `none`;
- gotchas for dependent tasks.

Planning-only changes are committed separately by the orchestrator using
`docs(planning):`; never include plan/state updates in a code commit.
