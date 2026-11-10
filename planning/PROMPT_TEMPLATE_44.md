# Worker Prompt Template -- Orchestration 44

In the Databricks environment one Genie Code session plays both orchestrator and worker (Plan 44 D8): it writes the micro-plan, checks it against the task spec, then executes. A worker-capable tool may use this template unchanged, with the orchestrator sending the approval message.

You are implementing exactly one scoped task, supervised by an orchestrator that reviews your plan before you may edit files.

## Task {{id}}: {{title}}

**Executor:** {{executor}} (see the wave table).

{{task spec verbatim}}

## Ground rules

- NEVER edit files or run state-changing commands before your micro-plan is approved (self-check against the spec in the Databricks environment).
- NEVER touch files outside the task's **Files in scope**. If you must, STOP and report; that is a decomposition bug.
- NEVER go off-plan; put discovered work under `## Discovered` in your todo file.
- Before planning, read:
  - root `AGENTS.md` and `apps/agent-fpac-soil-openai-sdk/AGENTS.md`
  - `planning/EXECUTION_PLAN_44.md`: Goal & Scope, Decision Log D1-D9, Hazards, and your task section
  - the reports of your dependency tasks in `planning/STATE_44.md`
  - ADR 0017 (from 44.1.1 on) and the grep anchors and named references (never read large files whole)
- Preserve ADR 0003 (render the server `regulatory_notice`; preliminary screening only), ADR 0004 (geodesic acreage), ADR 0010 and 0016 (geometry is operational data; no PII), ADR 0011 (mocked by default, live opt-in), ADR 0012 (separate MCP client, no wrapper tools), ADR 0013 (PyPI index), ADR 0015 (vendored frontend; list local changes).
- Exact geometry drives every number; display simplification and truncation touch only `map` layers (D7).
- Privacy: synthetic geometry and the marker `R6-MARKER` in tests; no real coordinates or parcel data in commits, tests, planning or evidence.
- Never edit frozen plans (`EXECUTION_PLAN_1`-`43`, their `STATE_`/`PROMPT_TEMPLATE_` files).
- Commits: conventional format (`feat(map):`, `feat(agent-app):`, `test(map):`, `docs(decisions):`), one sentence, no plan, wave or task numbers. One commit per task. Never amend. Never commit to `main`. Stage new files with `git add --chmod=-x`.
- If the same check fails twice for the same reason, stop and report.

## Environment (Databricks executor)

- Edit and commit in the workspace clone `/Workspace/Users/andrew.g.brown@usda.gov/fpac-soil-mcp` on `feature/agent-app-map2`. Use Python for file writes; shell writes under `/Workspace` and `mv` commands that mention workspace paths are blocked.
- Gates run in a fresh `/tmp` clone of the branch head (`git clone /Workspace/Users/andrew.g.brown@usda.gov/fpac-soil-mcp /tmp/p44`). `/tmp` is lost on compute restart: re-clone and resume from `STATE_44.md`.
- `source databricks/bootstrap-serverless.sh` from the repo root at the start of every shell that runs node, npm, npx or the MCP libs.
- Never run upstream `npm run lint` or `lint:fix` (they `--write`). Ruff on `/Workspace` paths needs `--extend-ignore EXE002`.
- `pkill -f` kills the executing shell; kill by PID. Never push or deploy without user approval. App logs and browser checks belong to the user.

## [Worker] Analysis

Read the conventions, your task section, dependency reports, grep anchors and named references. Resolve facts from the repository or cited upstream sources; do not ask the user about facts.

## [Worker] Micro-planning

Write `planning/tasks/{{id}}.todo.md`:

```markdown
# {{id}} -- {{title}}
## Goal        <one sentence>
## TODO items  - [ ] small, verifiable steps incl. explicit test steps (<=12)
## Notes       <facts from Analysis, constraints honored, risks>
## Questions   <numbered, max 5; omit if none>
```

Output the file contents as your report and END YOUR TURN (worker-capable tools). In the Databricks environment, check each TODO item against Files in scope and Acceptance, then continue.

## [Worker] Execution

Work the TODO in order, flipping `- [ ]` to `- [x]`. Match surrounding code style. Run only the targeted checks named in the spec; the wave check gate runs the full suites.

## [Worker] Reporting

Append to `planning/STATE_44.md` under `## {{id}}` (<=15 lines): status; files changed; exact commands and pass/fail counts; deviations (or "none"); gotchas for dependent tasks; commit hash.
