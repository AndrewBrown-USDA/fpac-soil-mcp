# Worker Prompt Template — Plan 32

You are executing the bounded task `{{TASK_ID}} — {{TASK_TITLE}}` from `EXECUTION_PLAN_32.md` in `D:\workspace\fpac-soil-mcp`.

Read first:

- `AGENTS.md`
- `docs\decisions\0002-fixed-sql-templates-over-user-passthrough.md`
- `docs\decisions\0007-unified-lesa-module-architecture.md`
- `docs\decisions\0008-nccpi-validated-public-index-with-extensible-sdv-routing.md`
- `docs\decisions\0011-mocked-default-live-opt-in-test-architecture.md`
- `planning\EXECUTION_PLAN_32.md`
- the assigned task specification below
- `[[git-workflow-standards]](../../git-workflow-standards/SKILL.md)` when available

## Assigned task specification

{{TASK_SPEC}}

## Operating rules

1. Confirm the task dependency state before editing.
2. Stay within the task's files-in-scope and grep anchors.
3. Do not broaden the task or refactor unrelated code.
4. Preserve fixed SQL templates, explicit validation, privacy protections, and the mocked-default/live-opt-in test architecture.
5. Shared files are serialized. Do not edit a shared file concurrently with another worker.
6. Never schedule or assume more than three concurrent workers; shared files are serialized.
7. Run the task's targeted acceptance command.
8. Append the handoff to `planning\STATE_32.md` under `## Task Reports`, using the task ID as a heading, unless the orchestrator provides another report channel.
9. Report changed files, tests, deviations, and unresolved blockers.
10. Commit only when the orchestrator requests it, using the repository's conventional one-sentence commit format; do not include phase or wave numbers.

## Gate messages

- Before work: `READY: <task-id> — dependencies verified`
- On completion: `DONE: <task-id> — <short result>`
- If blocked: `BLOCKED: <task-id> — <specific blocker and evidence>`

## Required handoff

```text
Task: <task-id>
Status: done | blocked
Changes:
- <file>: <meaningful change>
Validation:
- <command>: pass/fail
Deviations:
- none, or explain
Follow-up:
- none, or exact next task/blocker
```
