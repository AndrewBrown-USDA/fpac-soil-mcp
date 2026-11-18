# PROMPT_TEMPLATE_57

You are implementing exactly one scoped task, supervised by an orchestrator that reviews your plan before you may write code.

## Task {{id}}: {{title}}
{{task spec verbatim from EXECUTION_PLAN_57.md}}

## Ground rules (non-negotiable)
- NEVER make implementation changes or run state-changing commands before your plan is approved. Creating `planning/tasks/{{id}}.todo.md` is allowed before approval.
- NEVER touch files outside "Files in scope"; if required, STOP and report.
- NEVER go off-plan; discovered work goes in "## Discovered" and waits.
- NEVER call live SDA, MCP, TIGERweb or NASS in tests; use fakes and `httpx.MockTransport` (pattern: `tests/test_polygon_analysis.py`).
- NEVER leave a relic of `include_nccpi`: no parameter, default, docstring line, kwargs key, compatibility shim, deprecation warning or `**kwargs` catch-all. The only allowed mentions are tests proving it is rejected.
- NEVER report a missing or unrated NCCPI baseline as 0, 0.0, a default percentage, or a class string; use `None`.
- NEVER change Land Evaluation math, `productivity_index` selection, or SDA query templates.
- NEVER push, deploy, or change remotes. One focused local commit after approval.
- If a test fails twice for the same reason, stop and report.

## Conventions
- Read: root `AGENTS.md`, the task's section of `planning/EXECUTION_PLAN_57.md` (Goal & Scope, Decision log, Hazards), and STATE_57 reports of dependency tasks.
- Enter `corridor_analyzer.py` (1410 lines) and `polygon_analyzer.py` only through the grep anchors.
- Python tests, from the repo root: `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/tmp/fpac-venv uv run --group dev pytest <files> -q -p no:cacheprovider`.
- App tests: `cd apps/agent-fpac-soil-openai-sdk && PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/tmp/app-venv uv run --frozen pytest tests -q -p no:cacheprovider`.
- JS harness: `source databricks/bootstrap-serverless.sh`; `git archive HEAD eval | tar -x -C /tmp/h57`; `npm ci` in `/tmp/h57/eval/fpac_soil_mcp_harness`; `node --test test/harness.test.js test/smoke.test.js`. Commit first, or copy working-tree changes in, so the archive holds your edit.
- Lint: Ruff on a `git archive HEAD` copy in `/tmp` (workspace FS gives false EXE002), `RUFF_CACHE_DIR=/tmp/ruff-cache`.
- Commits: follow `git-workflow-standards` (Conventional Commits, one-sentence subject, domain scope such as `feat(polygon):`, `feat(corridor):`, `feat(models):`, `refactor(mcp)!:`, `test(eval):`, `docs(adr):`; mark the breaking change with `!` and a `BREAKING CHANGE:` footer on the commit that removes a public parameter; never mention plan, wave or task numbers).

## [Worker] Analysis & Micro-planning
Write `planning/tasks/{{id}}.todo.md`:
  # {{id}} -- {{title}}
  ## Goal        <one sentence>
  ## TODO items  - [ ] <=12 small, verifiable steps incl. explicit test steps
  ## Notes       <facts found, constraints honored, risks>
  ## Questions   <numbered, max 5, omit if none>
Output the file contents as your report and END YOUR TURN.

## [Worker] Execution
After `APPROVED`, work the TODO in order, flipping - [ ] to - [x]. Run only the targeted tests named in the spec.

## [Worker] Reporting
Append to `planning/STATE_57.md` under `## {{id}}` (<=15 lines): status; files changed with line ranges; exact test commands + pass/fail counts; deviations (or "none"); gotchas for dependent tasks.
