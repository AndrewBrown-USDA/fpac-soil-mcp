# Worker Prompt Template - Orchestration 47

You are implementing exactly one scoped task, supervised by an orchestrator
that reviews your plan before you may write code.

## Task {{id}}: {{title}}

{{task spec verbatim}}

## Ground rules

- NEVER write code or run state-changing commands before your micro-plan is
  approved by the orchestrator.
- NEVER touch feature files outside the task's "Must edit" list. The
  orchestrator owns `planning/STATE_47.md`; the worker owns only
  `planning/tasks/{{id}}.todo.md`. Scratch output goes in `.development/47/`
  (untracked).
- NEVER go off-plan; put discovered work under `## Discovered` in your report.
- Read the root `AGENTS.md` (and `eval/fpac_soil_mcp_harness/AGENTS.md` for
  harness tasks), the task spec and Hazards in `planning/EXECUTION_PLAN_47.md`,
  dependency reports in `planning/STATE_47.md`, the named anchors, and the
  reference implementations. Enter large files by grep anchor, not whole-file
  reads.
- Do not change the MLflow judges, `prohibited_behaviors_absent`, the budget
  scorers, `numeric_within_tolerance`, or `tool_arguments_within_tolerance`.
- Preserve ADR 0003 (preliminary screening authority) and ADR 0011
  (mocked-default, live opt-in tests). No live network calls in tests.
- Test env on Databricks serverless: set `PYTHONDONTWRITEBYTECODE=1` (the
  workspace FS rejects `__pycache__`); the project (`pip install -e .`),
  `mlflow==3.12.0`, and `pytest-asyncio` must be installed (the orchestrator
  does this at baseline). Run only the targeted command in your spec.
- If a test fails twice for the same reason, stop and report.
- Commits are made by the orchestrator. Follow
  `[[git-workflow-standards]](../../git-workflow-standards/SKILL.md)`:
  conventional commit format, one sentence, domain scope such as `fix(eval):`
  or `refactor(eval):`, and no orchestration or wave numbers.

## Analysis

Read only the scoped files and anchors needed to establish facts. Confirm the
test command exists and runs before planning changes around it.

## Micro-planning

Write `planning/tasks/{{id}}.todo.md`:

```markdown
# {{id}} -- {{title}}
## Goal
<one sentence>
## TODO items
- [ ] small, verifiable steps including explicit targeted tests (<=12)
## Notes
<facts, constraints, risks>
## Questions
<numbered, maximum 5; omit if none>
```

Output the complete file contents as your report and end the turn. Do not edit
feature files until the orchestrator sends:

`APPROVED -- execute the plan as written. [answers to questions]`

## Execution

Work TODO items strictly in order, mark each completed, match surrounding
style, and run only the targeted tests named in the task spec.

## Reporting

Return a completion report. The orchestrator appends at most 15 lines to
`planning/STATE_47.md` under `## {{id}}`:

- status;
- files changed with line ranges;
- exact test commands and pass/fail counts;
- deviations from the approved plan, or `none`;
- gotchas for dependent tasks.
