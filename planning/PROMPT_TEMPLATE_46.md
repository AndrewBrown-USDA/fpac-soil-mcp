# Worker Prompt Template — Orchestration 46

You are implementing exactly one scoped task, supervised by an orchestrator
that reviews your plan before you may write code.

## Task {{id}}: {{title}}

{{task spec verbatim}}

## Ground rules

- NEVER write code or run state-changing commands before your micro-plan is
  approved by the orchestrator.
- NEVER touch feature files outside the task's explicit scope. The
  orchestrator owns `planning\STATE_46.md` and the worker owns only its
  task's `planning\tasks\{{id}}.todo.md`; those reporting artifacts are
  explicitly exempt from feature-file scope.
- NEVER go off-plan; put discovered work under `## Discovered` in your report.
- Read the applicable `AGENTS.md`, the task spec, dependency reports in
  `planning\STATE_46.md`, named anchors, and reference implementations.
- If a test fails twice for the same reason, stop and report.
- Preserve ADR 0002 fixed SQL, ADR 0003 preliminary authority, ADR 0011
  mocked-default/live-opt-in testing, ADR 0012 app separation, ADR 0016 AOI
  privacy boundary, and ADR 0017 map result contract.
- Follow `[[git-workflow-standards]](../../git-workflow-standards/SKILL.md)`:
  use conventional commit format, one sentence, and do not include
  orchestration or wave numbers in commit messages.

## Analysis

Read only the scoped files and anchors needed to establish facts. Confirm the
existing test command and do not run shared/global suites.

## Micro-planning

Write the worker-owned `planning\tasks\{{id}}.todo.md`:

```markdown
# {{id}} -- {{title}}
## Goal
<one sentence>
## TODO items
- [ ] small, verifiable steps including explicit targeted tests
## Notes
<facts, constraints, risks>
## Questions
<numbered, maximum 5; omit if none>
```

End the turn after reporting the micro-plan. The orchestrator must send:

`APPROVED -- execute the plan as written. [answers to questions]`

before any implementation.

Output the complete contents of `planning\tasks\{{id}}.todo.md` in the
micro-planning report and end the turn. Do not edit feature files before the
approval message.

## Execution

Work TODO items strictly in order, mark each completed, match surrounding
style, and run only the targeted tests named in the task spec.

## Reporting

Return a completion report to the orchestrator. The orchestrator, not the
worker, appends at most 15 lines to `planning\STATE_46.md` under `## {{id}}`:

- status;
- files changed with line ranges;
- exact test commands and pass/fail counts;
- deviations from the approved plan, or `none`;
- gotchas for dependent tasks.
