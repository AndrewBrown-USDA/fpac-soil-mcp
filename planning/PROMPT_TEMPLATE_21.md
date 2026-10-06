# Worker Prompt Template — Orchestration 21

You are implementing exactly one scoped task from `planning/EXECUTION_PLAN_21.md`.
The orchestrator reviews your micro-plan before you may write code.

## Ground rules
- Read `AGENTS.md`, the task specification, and dependency reports first.
- Do not write code or run state-changing commands before your micro-plan is approved.
- Touch only the task's explicit files-in-scope.
- Use grep anchors and named reference implementations; do not read oversized files wholesale.
- Run only the targeted acceptance command in the task spec.
- If a test fails twice for the same reason, stop and report.
- Record discoveries instead of expanding scope.
- Follow [[git-workflow-standards]](../../git-workflow-standards/SKILL.md):
  one conventional commit sentence, with no phase or wave numbers.

## Micro-plan gate
Write `planning/tasks/21.W.id.todo.md` with:
`Goal`, no more than 12 checkbox `TODO items`, `Notes`, and optional numbered
`Questions` (maximum five). Stop and report the file contents. Continue only
after the orchestrator sends `APPROVED -- execute the plan as written`.

## Reporting
After execution, report status, changed files and line ranges, exact test
commands and counts, deviations (or `none`), and gotchas for dependents. The
orchestrator appends a concise report to `planning/STATE_21.md`.
