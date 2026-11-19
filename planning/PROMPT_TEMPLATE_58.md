# PROMPT_TEMPLATE_58

You are implementing exactly one scoped task, supervised by an orchestrator that reviews your plan before you may write code.

## Task {{id}}: {{title}}
{{task spec verbatim from EXECUTION_PLAN_58.md}}

## Ground rules (non-negotiable)
- NEVER make implementation changes or run state-changing commands before your plan is approved. Creating `planning/tasks/{{id}}.todo.md` is allowed before approval.
- NEVER touch files outside "Files in scope"; if required, STOP and report.
- NEVER go off-plan; discovered work goes in "## Discovered" and waits.
- NEVER call live SDA, MCP, TIGERweb or NASS in tests (SDA is down); use fakes and `httpx.MockTransport` (pattern: `tests/test_polygon_analysis.py`).
- NEVER report a failed request or upstream query as `unmapped`, `unrated`, `unknown` or null; it is `error`, with the cause in `limitations`.
- NEVER write a coverage value as a bare string in `src/`; use the constants in `fpac_soil_mcp.models.coverage`.
- NEVER add aliases, compatibility shims or mappings that accept the retired values (`partially_covered`, `no_data`, `invalid_request`, status `no_coverage` / `not_found`, rating `covered`), except the transitional `LandEvaluationSummary` widening (D19) until 58.4.1.
- NEVER rename fields or `SDV_CAVEATS` keys, and never change farmland category keys, map categories, Land Evaluation math or SDA query templates.
- NEVER push, deploy, or change remotes. One focused local commit after approval.
- If a test fails twice for the same reason, stop and report.

## Conventions
- Read: root `AGENTS.md`, the task's section of `planning/EXECUTION_PLAN_58.md` (Goal & Scope, Vocabulary, Decision log, Hazards), and STATE_58 reports of dependency tasks.
- Enter `corridor_analyzer.py` (1416 lines), `polygon_analyzer.py` and `clients/sda/client.py` only through the grep anchors.
- Python tests, from the repo root: `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/tmp/fpac-venv uv run --group dev pytest <files> -q -p no:cacheprovider`.
- App tests: `cd apps/agent-fpac-soil-openai-sdk && PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/tmp/app-venv uv run --frozen pytest tests -q -p no:cacheprovider`. Frontend: `. databricks/bootstrap-serverless.sh` then `make app-frontend-check`.
- JS harness: `git archive HEAD eval | tar -x -C /tmp/h58`; `npm ci` in `/tmp/h58/eval/fpac_soil_mcp_harness`; `node --test test/harness.test.js test/smoke.test.js`. Commit first so the archive holds your edit.
- Lint: Ruff on a `git archive HEAD` copy in `/tmp` (workspace FS gives false EXE002), `RUFF_CACHE_DIR=/tmp/ruff-cache`; app files via the Makefile `APP_LINT_PATHS`.
- Commits: follow `git-workflow-standards` (Conventional Commits, one-sentence subject, domain scope such as `feat(models):`, `fix(polygon):`, `fix(corridor):`, `refactor(sda):`, `fix(lesa)!:`, `test(eval):`, `docs(adr):`; mark breaking value renames with `!` and a `BREAKING CHANGE:` footer; never mention plan, wave or task numbers).

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
Append to `planning/STATE_58.md` under `## {{id}}` (<=15 lines): status; files changed with line ranges; exact test commands + pass/fail counts; deviations (or "none"); gotchas for dependent tasks.
