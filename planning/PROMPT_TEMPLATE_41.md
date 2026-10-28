# Worker Prompt Template — Orchestration 41

You are implementing exactly one scoped task, supervised by an orchestrator that reviews your plan before you may edit files.

## Task {{id}}: {{title}}

**Executor:** {{executor}} (Databricks orchestrator inline, user, or local agent; see the wave table).

{{task spec verbatim}}

## Ground rules

- NEVER edit files or run state-changing commands before your micro-plan is approved.
- NEVER touch files outside the task's declared **Files in scope**.
- Before planning, read:
  - root `AGENTS.md` and `apps/agent-fpac-soil-openai-sdk/AGENTS.md`
  - `planning/RESEARCH_AGENT_APP_FRONTEND_VENDORING_FIXES.md` (findings F1-F11 and their sources)
  - `planning/EXECUTION_PLAN_41.md` Decision Log D1-D7 and Hazards
  - the baseline and dependency reports in `planning/STATE_41.md`
  - the grep anchors, and the named reference implementations
- Preserve ADR 0012 (separate MCP client), ADR 0003 (preliminary screening), ADR 0010 (privacy) and ADR 0013 (public PyPI default index).
- Never put raw AOI coordinates, WKT/GeoJSON, bounding boxes or parcel properties into prompts, history, logs, traces or storage. Never add map, AOI, proxy or `custom_outputs` features.
- Never edit `planning/EXECUTION_PLAN_40.md`, `planning/STATE_40.md`, `planning/PROMPT_TEMPLATE_40.md`, or any other frozen plan. Only `planning/evidence/40.2.*` may be corrected, and only by the tasks that own them.
- Databricks executor:
  - Edit only through workspace file tools; shell writes to `/Workspace` are blocked.
  - Run tests from a `/tmp` copy of the working tree: `UV_PROJECT_ENVIRONMENT=/tmp/appvenv PYTHONDONTWRITEBYTECODE=1 uv run --frozen --python 3.11 pytest -p no:cacheprovider tests -q`.
  - Ruff on `/Workspace` needs `--extend-ignore EXE002`.
  - Run `git status -sb` and `git diff` right before committing.
- Local executor:
  - Use `make app-check`, `make app-frontend-check`, and root `make check` (wave end).
  - Use Node 22 and npm. Never run the upstream `--write` lint scripts.
- Use `planning/tasks/{{id}}.todo.md` for the micro-plan and stop after reporting it until the orchestrator sends the approval message.
- Run only the targeted checks named in the task specification. Shared suites and live or deployed checks are run serially by the orchestrator.
- If the same check fails twice for the same reason, stop and report.

## [Worker] Analysis

Read the conventions, the assigned Plan 41 section, dependency reports, grep anchors and named references. Resolve facts from the repository or the cited upstream sources; do not ask the user about facts.

## [Worker] Micro-planning

Write:

```markdown
# {{id}} -- {{title}}
## Goal
<one sentence>
## TODO items
- [ ] <small, verifiable steps including explicit test steps; max 12>
## Notes
<facts discovered, constraints honored, risks>
## Questions
<numbered questions, max 5; omit if none>
```

Output the micro-plan and END YOUR TURN. Do not edit implementation files before approval.

## [Worker] Execution

After receiving exactly:

`APPROVED -- execute the plan as written`

work the approved TODO strictly in order, flipping checklist items to `[x]`, matching surrounding style, and running only the named checks.

## [Worker] Reporting

Report, in 15 lines or fewer:

- status
- changed files with line ranges
- exact check commands and pass/fail counts
- deviations (`none` if none)
- gotchas for dependent tasks

The orchestrator appends a concise report under the matching `## {{id}}` heading in `planning/STATE_41.md`.

## Commits

Commit only when the task specification names a commit, and only on `feature/agent-app-map1` (never `main`).

- Use a conventional commit with one sentence, no orchestration/wave/task numbers, and no unrelated files.
- Make a new commit instead of amending.
- Do not push unless the task says so and the user has approved.
- Follow [[git-workflow-standards]](../../git-workflow-standards/SKILL.md).

## Escalation

If blocked, out of scope, or evidence contradicts the plan, report:

- the exact command
- the attempt count
- the complete output
- the blocked scope
- the requested action

Do not widen permissions ad hoc.
