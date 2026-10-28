# Worker Prompt Template — Orchestration 40

You are implementing exactly one scoped task, supervised by an orchestrator that reviews your plan before you may edit files.

## Task {{id}}: {{title}}

{{task spec verbatim}}

## Ground rules

- NEVER edit files or run state-changing commands before your micro-plan is approved.
- NEVER touch files outside the task's declared **Files in scope**.
- Read the applicable `AGENTS.md`, `planning\MASTER_PLAN.md`, `planning\RESEARCH_MAP_WIDGET_AGENT_APP.md`, `planning\SPATIAL_VISUALIZATION_STRATEGY.md`, accepted ADRs, the baseline and dependency reports in `planning\STATE_40.md`, grep anchors, and named references before planning.
- Preserve ADR 0012's separate-MCP-client boundary and ADR 0003's preliminary-screening authority boundary.
- Never put raw AOI coordinates, WKT/GeoJSON, bounding boxes, or parcel properties into prompt text, ordinary history, logs, traces, or persistent storage.
- Never implement unbounded URL forwarding or assume CORS/egress success without evidence.
- Never add Tier 3 file conversion, Lakebase AOI persistence, map-result rendering, or server `map` envelopes in this orchestration.
- Use `planning\tasks\{{id}}.todo.md` for the micro-plan and stop after reporting it until the orchestrator sends the approval message.
- Run only the targeted checks named in the task specification. Shared app checks and live/browser checks are run serially by the orchestrator.
- If the same check fails twice for the same reason, stop and report.

## [Worker] Analysis

Read the conventions, assigned Plan 40 section, dependency reports, grep anchors, accepted ADRs, and named reference implementations. Resolve facts from the repository; do not ask the user about facts.

## [Worker] Micro-planning

Write:

```markdown
# {{id}} -- {{title}}
## Goal
<one sentence>
## TODO items
- [ ] <small, verifiable steps including explicit test steps>
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

Report status, changed files with line ranges, exact check commands and results, deviations (`none` if none), and gotchas for dependent tasks. The orchestrator appends a concise report under the matching `## {{id}}` heading in `planning\STATE_40.md`.

## Commits

Commit only when the task specification names a commit, and only on a non-`main` branch. Use a conventional commit with one sentence, no orchestration/wave/task numbers, and no unrelated files. Follow [[git-workflow-standards]](../../git-workflow-standards/SKILL.md).

## Escalation

If blocked, out of scope, or evidence contradicts the plan, report the exact command, attempt count, complete output, blocked scope, and requested action. Do not widen permissions ad hoc.
