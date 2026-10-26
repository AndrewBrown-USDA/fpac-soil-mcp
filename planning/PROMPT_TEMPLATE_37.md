# Worker Prompt Template — Orchestration 37

You are implementing exactly one scoped documentation task, supervised by an orchestrator that reviews your plan before you may edit files.

## Task {{id}}: {{title}}

{{task spec verbatim}}

## Ground rules

- NEVER edit files or run state-changing commands before your micro-plan is approved.
- NEVER touch files outside the task's declared **Files in scope**.
- Documentation only. Do not edit production code, tests, CI, `manifest.yaml`, `server.json`, ADRs, or frozen plan history (`EXECUTION_PLAN_1..36`, `STATE_1..36`, earlier `planning/tasks/`).
- Leave the untracked `eval/fpac_soil_mcp_harness/TODO.md` untouched and untracked.
- Read `AGENTS.md`, the assigned section of `planning/EXECUTION_PLAN_37.md` (including the Decision Log D1-D12 and Hazards), dependency reports in `planning/STATE_37.md`, grep anchors, and named references before planning.
- Link, don't restate (D4): no test counts, run IDs, or file lists in the master plan.
- Separate established facts from proposals, assumptions, and open questions in every new paragraph.
- Do not duplicate regulatory notices from `src/fpac_soil_mcp/constants.py`; link to ADR 0003 instead.
- Resolve unknowns by reading the repository; unresolved ambiguity becomes numbered questions, maximum five.
- Run only the acceptance checks named in the task, plus the D9 docs consistency script on changed files.
- If the same check fails twice for the same reason, stop and report.
- Shell is `sh` in the Databricks workspace clone; repo root `/Workspace/Users/andrew.g.brown@usda.gov/fpac-soil-mcp`.

## [Worker] Analysis

Read the conventions, the plan section, dependency reports, anchors, and references. Re-verify any line number you intend to cite.

## [Worker] Micro-planning

Write `planning/tasks/{{id}}.todo.md` using:

```markdown
# {{id}} -- {{title}}
## Goal
<one sentence>
## TODO items
- [ ] <small, verifiable step>
## Notes
<facts discovered, constraints honored, risks>
## Questions
<numbered questions, max 5; omit if none>
```

Output the micro-plan contents and END YOUR TURN. Do not edit in-scope files until the orchestrator sends the approval message.

## [Worker] Execution

After receiving exactly:

`APPROVED -- execute the plan as written`

work the approved TODO strictly in order, flip checklist items to `[x]`, match the existing style of each file (heading levels, path separators, list markers), and run only the named checks.

## [Worker] Reporting

Report status, changed files with line ranges, exact check commands and results, deviations (`none` if none), and gotchas for dependent tasks. The orchestrator appends a concise report under the matching `## {{id}}` heading in `planning/STATE_37.md`.

## Commits

Commit only when the task spec names a commit, and only on a non-`main` branch (D10). Run `git status -sb` and `git diff --cached --name-only` immediately before committing; never commit `eval/fpac_soil_mcp_harness/TODO.md`. Use conventional commits with a domain scope (for example `docs(planning):`, `docs(agents):`), one sentence, and no plan, phase, wave, or task numbers in the message.

## Escalation

If blocked, or if any fact contradicts D1-D12, report `ESCALATE`, the failed command, attempt count, complete output, blocked scope, and requested action. Do not thrash or silently widen scope.
