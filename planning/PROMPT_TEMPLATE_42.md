# Worker Prompt Template — Orchestration 42

In the Databricks environment one agent plays both orchestrator and worker (Plan 42 D8): it writes the micro-plan, checks it against the task spec itself, then executes. A worker-capable tool may use this template unchanged, with the orchestrator sending the approval message.

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
  - `planning/EXECUTION_PLAN_42.md`: Goal & Scope, Decision Log D1-D8, Hazards, and your task section
  - the reports of your dependency tasks in `planning/STATE_42.md`
  - the grep anchors and named reference implementations (never read large files whole)
- Preserve ADR 0003 (render the server `regulatory_notice`; preliminary screening only), ADR 0010 (privacy), ADR 0012 (separate MCP client, no wrapper tools), ADR 0013 (PyPI default index), and ADRs 0015/0016 as amended by this plan.
- Privacy: never put real coordinates, WKT/GeoJSON, bounding boxes or parcel properties into commits, tests, logs, planning or evidence files. Tests use synthetic geometry and the marker `R6-MARKER`.
- Never edit frozen plans (`EXECUTION_PLAN_40/41`, `STATE_40/41`, `PROMPT_TEMPLATE_40/41`).
- Commits: conventional format (`feat(agent-app): ...`, `docs(decisions): ...`), one sentence, no plan, wave or task numbers. One commit per task. Never amend. Never commit to `main`.
- If the same check fails twice for the same reason, stop and report.

## Environment (Databricks executor)

- Work in a `/tmp` clone (`git clone /Workspace/Users/andrew.g.brown@usda.gov/fpac-soil-mcp /tmp/p42`, branch `feature/agent-app-map1`). Shell writes under `/Workspace` are blocked.
- After each task: run `git status -sb` and `git diff` in `/tmp`, commit there, then in the workspace clone run `git fetch /tmp/p42 feature/agent-app-map1` and `git merge --ff-only FETCH_HEAD`, and confirm `git log -1` matches. Never push without user approval.
- Python: `UV_PROJECT_ENVIRONMENT=/tmp/appvenv PYTHONDONTWRITEBYTECODE=1` for app tests; a separate `/tmp/rootvenv` for root `make` targets. Local MLflow needs `MLFLOW_TRACKING_URI=sqlite:///...`.
- Node: `uv venv /tmp/nodevenv` + `nodejs-wheel-binaries>=22,<23`; `/tmp/nbin/npm` and `/tmp/nbin/npx` wrappers call `npm-cli.js`/`npx-cli.js` with the wheel's node; `export PATH=/tmp/nbin:$PATH`.
- Never run upstream `npm run lint` or `lint:fix` (they `--write`). Ruff on `/Workspace` paths needs `--extend-ignore EXE002`.
- `pkill -f` kills the executing shell; kill by PID.
- `/tmp` is lost on compute restart: re-clone and resume from `STATE_42.md`.

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

Append to `planning/STATE_42.md` under `## {{id}}` (<=15 lines): status; files changed; exact commands and pass/fail counts; deviations (or "none"); gotchas for dependent tasks; commit hash.
