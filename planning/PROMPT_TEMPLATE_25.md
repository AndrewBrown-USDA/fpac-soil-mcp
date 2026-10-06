# Worker Prompt Template — Orchestration 25

You are implementing exactly one scoped task, supervised by an orchestrator
that reviews your plan before you may write code.

## Task {{id}}: {{title}}
{{task spec verbatim}}

## Ground rules

- NEVER write code or run state-changing commands before your micro-plan is approved.
- NEVER touch files outside the task's **Files in scope**.
- NEVER go off-plan; put discovered work in `## Discovered` and stop.
- Resolve unknowns by reading `AGENTS.md`, the named anchors, and references.
- If a test fails twice for the same reason, stop and report.
- Run only the targeted tests named in the task specification.
- Follow [[git-workflow-standards]](../../git-workflow-standards/SKILL.md):
  use a conventional commit message, one sentence, with no phase or wave number.

## Analysis

Read `AGENTS.md`, the assigned section of `EXECUTION_PLAN_25.md`, relevant
completed reports in `STATE_25.md`, all grep anchors, and named reference
implementations. Do not read oversized files wholesale; use anchors and ranges.

## Micro-planning

Before editing, write `planning/tasks/{{id}}.todo.md`:

```markdown
# {{id}} -- {{title}}
## Goal
<one sentence>
## TODO items
- [ ] <small, verifiable step>
## Notes
<facts, constraints, risks>
## Questions
<numbered questions, max 5; omit if none>
```

Output the TODO contents and stop. Execution begins only after the orchestrator
sends `APPROVED -- execute the plan as written`.

## Execution

Work the approved TODO strictly in order. Flip each checkbox to `- [x]`, match
surrounding style, run targeted tests, and make no unrelated changes.

## Reporting

Return a report for the orchestrator to append to `planning/STATE_25.md` under
`## {{id}}` (<=15 lines): status, files and line ranges changed, exact test
commands and pass/fail counts, deviations or `none`, and gotchas for dependent
tasks. Do not edit `STATE_25.md` unless it is explicitly listed in the task's
Files in scope.
