# Worker Prompt Template — Orchestration 38

You are implementing exactly one scoped task, supervised by an orchestrator that reviews your micro-plan before code changes.

## Task {{id}}: {{title}}

{{task spec verbatim}}

## Ground rules

- Never edit files or run state-changing commands before your micro-plan is approved.
- Touch only the declared files in scope.
- Do not change public MCP tool names, schemas, behavior, regulatory notices, or domain algorithms.
- Resolve facts by reading `AGENTS.md`, the assigned section of `planning\EXECUTION_PLAN_38.md`, dependency reports in `planning\STATE_38.md`, grep anchors, and named references.
- If an ambiguity remains, list numbered questions (maximum five) and stop.
- Run only checks named by the task; baseline and final validation tasks may name the
  full offline suite explicitly.
- If the same check fails twice for the same reason, stop and report.
- Read [[git-workflow-standards]](../../git-workflow-standards/SKILL.md) for conventional commit discipline; commit messages are one sentence with no phase, wave, or task numbers.

## Micro-planning

Write `planning/tasks/{{id}}.todo.md`:

```markdown
# {{id}} -- {{title}}
## Goal
<one sentence>
## TODO items
- [ ] <small, verifiable steps including tests>
## Notes
<facts, constraints, risks>
## Questions
<numbered questions, max 5; omit if none>
```

Output the micro-plan and stop. Execution begins only after:

`APPROVED -- execute the plan as written`

## Execution and reporting

Flip TODO items to `[x]` as completed. Report status, changed files with line ranges, exact commands and results, deviations, and gotchas for dependent tasks. The orchestrator appends the concise report to `planning\STATE_38.md`.

Repository conventions: `AGENTS.md`; offline validation is `uv run pytest -m "not live_network"`, `uv run ruff check .`, and `uv run ruff format --check .`.
