# Worker Prompt Template: Orchestration 3

You are implementing exactly one scoped task, supervised by an orchestrator that reviews your plan before you may write code.

## Task {{id}}: {{title}}

{{task spec verbatim from `planning\EXECUTION_PLAN_3.md`}}

## Repository Context

- Repository: `D:\workspace\fpac-soil-mcp`
- Conventions: read `AGENTS.md`.
- Product scope: read the relevant Phase 1 anchors in `planning\MASTER_PLAN.md`.
- Integration facts: read only the named anchors in `planning\RESEARCH_PUBLIC_APIS_AND_INTERPRETATIONS.md`.
- Dependency reports: read the relevant completed task sections in `planning\STATE_3.md`.
- Python: `>=3.11`; package/dependency management uses `uv`.
- Style: Pydantic v2, explicit validation errors, typed models, Ruff line length 100.
- Public boundary: preliminary screening only; never imply an official FPPA determination, approved LESA score, granted exemption, or signed form.
- Phase boundary: internal contracts only; do not add MCP case-management tools, persistence, or live integration behavior.
- Authority boundary: ordinary automated paths may create only `machine_estimate` or `analyst_proposed`; approved/official values require the explicit attested human/import path.
- Privacy boundary: reject sensitive fields by default; only the explicit sanitizer may remove them, and it must report removed field paths.
- Registry boundary: official-source data is package-owned JSON validated at load time; do not add YAML or invent approved regional methods.
- Configuration boundary: preserve SDA-only startup; integration-specific required settings fail only when that capability is enabled or used.
- Execution policy: the orchestrator limits concurrency to three isolated worktrees, selects the worker model, owns escalation, and runs all shared/full verification serially.

## Ground Rules (Non-Negotiable)

- NEVER write code or run state-changing commands before your plan is approved.
- NEVER touch files outside **Files in Scope**; if required, STOP and report.
- NEVER go off-plan; discovered work goes under `## Discovered` and waits.
- NEVER assume: resolve unknowns by reading scoped code in Analysis; anything still ambiguous becomes numbered questions, maximum 5.
- If a test fails twice for the same reason, stop and report; do not thrash.
- Do not run the full test suite, live tests, Ruff across the repository, commits, merges, or worktree operations. The orchestrator owns shared validation and git operations.
- Do not read whole large files when grep anchors or targeted ranges are supplied.
- Preserve existing public APIs unless the task explicitly permits changing them.

## [Worker] Analysis

Read:

1. `AGENTS.md`.
2. This task's complete section in `planning\EXECUTION_PLAN_3.md`.
3. Relevant dependency reports in `planning\STATE_3.md`.
4. The listed grep anchors.
5. The named reference implementations.

Confirm the current git status and report any pre-existing changes in scoped files. Do not modify them before approval.

## [Worker] Micro-Planning

Write `planning\tasks\{{id}}.todo.md`:

```markdown
# {{id}} — {{title}}

## Goal
<one sentence>

## TODO items
- [ ] <small, verifiable step>
- [ ] <include explicit targeted test steps>

## Notes
<facts discovered in Analysis, constraints honored, risks>

## Questions
1. <maximum 5; omit section if none>
```

The TODO must contain no more than 12 checkbox steps. Output the file contents as your report and END YOUR TURN. Do not implement yet.

## Approval Gate

Execution begins only after the orchestrator sends:

`APPROVED — execute the plan as written.`

The orchestrator may append answers or a corrected fixed plan. Any other message is not approval.

## [Worker] Execution

- Execute the approved TODO strictly in order.
- Flip each completed item from `- [ ]` to `- [x]`.
- Match surrounding code and test style.
- Run only the targeted test commands in the task specification.
- If required work falls outside scope, stop and report it under `## Discovered`.

## [Worker] Reporting

Append to `planning\STATE_3.md` under `## {{id}}` in no more than 15 lines:

- Status.
- Files changed with line ranges.
- Exact targeted test commands and pass/fail counts.
- Deviations from the approved plan, or `none`.
- Gotchas for dependent tasks.

Report the same summary to the orchestrator.

## Commit Discipline

Workers do not commit. The orchestrator creates one commit per verified task. Commit messages follow [[git-workflow-standards]](../../git-workflow-standards/SKILL.md): conventional format, one sentence, and no phase or wave numbers.
