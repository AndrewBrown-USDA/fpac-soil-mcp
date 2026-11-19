# PROMPT_TEMPLATE_59

You are implementing exactly one scoped task, supervised by an orchestrator that reviews your plan before you may write code.

## Task {{id}}: {{title}}
{{task spec verbatim from EXECUTION_PLAN_59.md}}

## Ground rules (non-negotiable)
- NEVER make implementation changes or run state-changing commands before your plan is approved. Creating `planning/tasks/{{id}}.todo.md` is allowed before approval.
- NEVER touch files outside "Files in scope"; if required, STOP and report.
- NEVER go off-plan; discovered work goes in "## Discovered" and waits.
- NEVER call live SDA, MCP, TIGERweb or NASS in tests; use fakes and `httpx.MockTransport` (patterns: `tests/test_map_tool_contracts.py`, `tests/test_polygon_analysis.py`).
- NEVER put coordinates, `feature_collection`, `bounds`, `display_crs`, map `warnings`, `feature_count`, `simplified`, `simplify_tolerance_m` or `truncated` in a map tool's body (`content`/`structuredContent`). Display data goes only in `_meta["gov.usda.fpac-soil/map"]`. `get_soil_polygons_by_geometry` top-level `features` stay in the body (D2).
- NEVER hand-write enum lists in output schemas; build them with `model_json_schema()` from the models (coverage values come from `fpac_soil_mcp.models.coverage`).
- NEVER weaken `test_tool_output_schemas_list_coverage_enums`; only add rows.
- NEVER change coverage behaviour, acreage, `geometry_hash`, `tabular_csv`, summaries, legends, categories, simplification maths or SDA query templates.
- NEVER leave aliases, compatibility shims or always-null relics of moved fields; never accept `inline_geojson` in the server.
- NEVER push, deploy, or change remotes. One focused local commit after approval.
- If a test fails twice for the same reason, stop and report.

## Conventions
- Read: root `AGENTS.md` (and `apps/agent-fpac-soil-openai-sdk/AGENTS.md` for wave 2), the task's section of `planning/EXECUTION_PLAN_59.md` (Goal & Scope, Decision log, Hazards), and STATE_59 reports of dependency tasks.
- Enter `corridor_analyzer.py` (1457 lines) and `polygon_analyzer.py` (655) only through the grep anchors.
- FastMCP 4.1.7: read schemas with `Tool.output_schema` (not `.outputSchema`); in-memory client `fastmcp.Client(create_mcp_server())` (`fpac_soil_mcp.mcp.app`); raw results via `call_tool_mcp(...)` and `model_dump(by_alias=True)["_meta"]`.
- Python tests, from the repo root: `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/tmp/fpac-venv uv run --group dev pytest <files> -q -p no:cacheprovider`.
- App tests: never run `uv run` in the workspace app directory (it creates a slow `.venv`). Copy first: `rm -rf /tmp/a59 && mkdir -p /tmp/a59 && git ls-files -z | tar --null -T - -cf - | tar -x -C /tmp/a59`. Then `cd /tmp/a59/apps/agent-fpac-soil-openai-sdk && UV_PROJECT_ENVIRONMENT=/tmp/app-venv uv run --frozen --python 3.11 pytest <tests> -q`.
- Frontend (orchestrator gates only): `source databricks/bootstrap-serverless.sh`; in the copy's `frontend/`: `npm ci && npx biome lint --skip=nursery/useSortedClasses --skip=style/useTemplate . && npm run build`.
- JS harness (gate only): `npm ci && node --test test/harness.test.js test/smoke.test.js` in the copy's `eval/fpac_soil_mcp_harness`.
- Lint: Ruff on a `/tmp` copy (the workspace FS gives false EXE002), `RUFF_CACHE_DIR=/tmp/ruff-cache`. App lint paths: `agent_server/{agent,aoi_context,config,geo,history}.py` and `tests`.
- Commits: follow `git-workflow-standards` (Conventional Commits, one-sentence subject, domain scope such as `feat(map)!:`, `feat(tools):`, `test(map):`, `feat(app):`, `docs(adr):`; contract breaks get `!` and a `BREAKING CHANGE:` footer; never mention plan, wave or task numbers).

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
Append to `planning/STATE_59.md` under `## {{id}}` (<=15 lines): status; files changed with line ranges; exact test commands + pass/fail counts; deviations (or "none"); gotchas for dependent tasks.
