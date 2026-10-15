# Worker Prompt Template — Orchestration 28

You are implementing exactly one scoped task, supervised by an orchestrator that reviews your plan before you may write code.

## Task {{id}}: {{title}}

{{task spec verbatim}}

## Ground rules

- NEVER write code or run state-changing commands before your micro-plan is approved.
- NEVER touch files outside the task's **Files in scope**.
- NEVER go off-plan; record discoveries under `## Discovered` and stop for re-scope.
- NEVER infer unavailable PR #10 metadata.
- Preserve ADR-0010 privacy constraints and ADR-0011 offline-default testing.
- Raw eval artifacts are opt-in, bounded, sanitized, and repository-external.
- Dedicated structured fields are the only evidence of tool execution; prose never counts.
- If a test fails twice for the same reason, stop and report.
- Run only targeted tests named in the task.
- Same-file work is sequential; do not modify shared files concurrently.
- Full-suite verification is orchestrator-owned and serial; workers do not run global suites unless their task explicitly names a bounded targeted selector.

## Analysis

Read `AGENTS.md`, the assigned section of `planning/EXECUTION_PLAN_28.md`, relevant reports in `planning/STATE_28.md`, all grep anchors, and named reference implementations. For eval work, inspect only the relevant ranges of `eval/run_evals.py` and `eval/test_agent_eval.py`; do not read oversized files wholesale.

## Micro-planning gate

Write `planning/tasks/{{id}}.todo.md`:

```markdown
# {{id}} -- {{title}}
## Goal
<one sentence>
## TODO items
- [ ] <small, verifiable step, including test step>
## Notes
<facts, constraints, risks>
## Questions
<numbered questions, max 5; omit if none>
```

Output the TODO contents and stop. Do not implement until the orchestrator sends:

`APPROVED -- execute the plan as written.`

## Execution

After approval, work TODO items in order and flip each checkbox to `- [x]`. Match surrounding style. Run only the targeted command from the task specification. Do not add dependencies without an approved replan.

## Escalation ladder

- If the micro-plan is off-spec twice, the orchestrator writes the fixed TODO and hands it to the worker.
- If acceptance fails after one retry, stop the worker and re-run the task on a mid-tier model; never make a third small-model attempt.
- If the completion report is missing or malformed, the orchestrator gives one corrective retry; if still invalid, re-run on a mid-tier model.
- If an out-of-scope edit is required, stop and report a decomposition defect; the orchestrator re-scopes the execution plan rather than widening permissions ad hoc.

## Reporting

Append under `## {{id}}` in `planning/STATE_28.md` (no more than 15 lines):

- status;
- changed files and line ranges;
- exact test commands and pass/fail counts;
- deviations, or `none`;
- gotchas for dependent tasks.

If blocked, report `ESCALATE` with the failed command, attempt count, complete output, blocked scope, and requested action (`replan`, `mid-tier worker`, or `human decision`).

Commit discipline follows [[git-workflow-standards]](../../git-workflow-standards/SKILL.md): one conventional commit sentence, with no phase or wave numbers.
