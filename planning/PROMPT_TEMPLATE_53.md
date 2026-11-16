# Worker Prompt Template — Orchestration 53

You are implementing exactly one scoped task, supervised by an orchestrator that reviews your micro-plan before you may write code.

## Task {{id}}: {{title}}

{{task spec verbatim from planning/EXECUTION_PLAN_53.md}}

## Ground rules

- Read root `AGENTS.md`, `apps/agent-fpac-soil-openai-sdk/AGENTS.md`, the task spec, and completed dependency reports in `planning/STATE_53.md`.
- Before implementation, create `planning/tasks/{{id}}.todo.md`: one-sentence goal, no more than 12 small TODO steps including tests, facts/constraints, and numbered questions (max 5). Report full contents and stop. Do not edit implementation files or run implementation state-changing commands until the orchestrator explicitly approves.
- After approval, execute only the approved TODO in order and change only the task's Must edit/Can create files. Out-of-scope needs are a stop-and-report issue; the orchestrator must amend the plan.
- Use existing patterns. No dependencies unless explicitly approved. Frontend lint must be read-only; never run `npm run lint`/`lint:fix`, and do not add a TypeScript check.
- Run only targeted task commands. The orchestrator owns shared/full suites and runs them serially.
- If a test fails twice for the same reason, stop and report.
- Keep the MapPanel hotspot single-owner: do not run concurrent tasks that edit it. Preserve server-provided map blocks/legends, fixed overlay URLs, AOI chat-context contract, and vector boundaries above raster/CDL layers.
- AOI labels must remain browser-only and must not enter chat/MCP context. Chat exports may include raw arguments/results and geometry only after an explicit user action and warning; never include hidden reasoning, credentials, or server traces.
- Update ADR 0015's `### Local changes` ledger for every modified or added vendored frontend path in the same implementation change.
- After targeted checks pass, make a focused local Conventional Commit. Keep planning edits out of code commits. Follow [[git-workflow-standards]](../../git-workflow-standards/SKILL.md) and [[conventional-commits]](../../conventional-commits/SKILL.md); commit subject must not contain wave/task numbers.
- No push, pull, fetch, deployment, PR edit, review comment, or other remote action is authorized. Preserve unrelated/user worktrees and changes.

## Reporting

After the implementation commit, report status, changed files, code commit ID, exact targeted commands/results, deviations (or `none`), and dependency gotchas. The orchestrator records a concise report in `planning/STATE_53.md` and performs integration/full-suite validation.
