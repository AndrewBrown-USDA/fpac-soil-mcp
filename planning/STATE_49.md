# STATE 49: Deployed MCP T2 Access Smoke

Resume point for orchestration 49. Plan: `planning/EXECUTION_PLAN_49.md`.
Worker prompt: `planning/PROMPT_TEMPLATE_49.md`.

## Baseline (recorded before wave 1; 2026-11-12)

- [x] Repo `D:\workspace\fpac-soil-mcp`, branch `refactor/eval-corpus1`, HEAD `ad56ace`; current uncommitted changes are this session's `planning/GOALS.md` update and the three new orchestration 49 planning artifacts.
- [x] Planning artifacts are tracked; orchestration 48 is the latest completed plan. Orchestration 49 is new; preserve all historical plans/states.
- [x] `make check` — Ruff check passed; 663 files formatted; offline Python suite **964 passed, 45 deselected**. Existing deprecation warnings are recorded in `EXECUTION_PLAN_49.md`.
- [x] Accepted ADRs reviewed: 0011 (offline/mock default, live opt-in), 0012 (agent app is separate MCP client with service-principal auth precedent), and 0017 (map response contract; no server changes in scope).
- [x] T2 runner does not yet exist. Reference code: `eval/databricks/run_mlflow_eval.py`, `run_t1_eval_notebook.py`, `test_databricks_runner.py`, and `apps/agent-fpac-soil-openai-sdk/agent_server/config.py`.
- [ ] External prerequisite: workspace owner provisions/approves a dedicated T2 evaluation service principal, assigns it as the Databricks job/notebook run-as identity, and grants only `CAN_USE` on `mcp-fpac-soil`. Do not run the live smoke until this is available.
- [x] No shared local port is required by the targeted unit test. The live acceptance uses the deployed endpoint only; do not substitute a local server.

## Wave Board

| Wave | Task | Status | Commit | Notes |
|---|---|---|---|---|
| 1 | 49.1.1 Build the authenticated T2 MCP smoke client | pending | - | Offline unit tests; no live credentials |
| 2 | 49.2.1 Add the Databricks run-as entry point and record smoke evidence | pending | - | Depends on 49.1.1 and external principal/grant |

## Task Reports

<!-- Orchestrator appends <=15 lines per task under ## <id>. -->
