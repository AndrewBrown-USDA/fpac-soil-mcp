---
id: "0012"
title: "Databricks Agent App as a Separate MCP Client Project"
status: "Accepted"
date: 2026-10-22
authors:
  - "Andrew G. Brown"
supersedes: null
superseded_by: null
source_context: "EXECUTION_PLAN_35 (D2, D3, D4, D9, D11), PR #35"
---

# 12. Databricks Agent App as a Separate MCP Client Project

## Context and Problem Statement

USDA staff need a chat interface for preliminary FPPA screening that runs in the
Databricks workspace. The MCP server is already deployed as the `mcp-fpac-soil`
Databricks App (Streamable HTTP on `/mcp`). The chat agent came from the
Databricks `agent-openai-agents-sdk` template, a separate uv project with its own
dependencies (MLflow, OpenAI Agents SDK, Databricks clients) and template
tooling. We had to decide where the agent lives, how it reaches the server, how
it is configured and deployed, and how it is checked in CI without coupling it
to the server package.

## Decision Drivers

* The server package (`src/fpac_soil_mcp/`) must stay free of agent, MLflow, and
  Databricks SDK dependencies.
* The agent must use the deployed server's tools, not reimplement soil logic, so
  regulatory limitations stay centralized (ADR 0003).
* The app was created in the Databricks Apps UI and deploys from its git source.
* The template's model default (`databricks-claude-sonnet-5-5`) is disabled in
  this workspace (403 `PERMISSION_DENIED`).
* Template code and docs are lint-dirty and largely irrelevant; root CI must stay
  green while the app is still checked.

## Considered Options

1. **Separate uv project under `apps/agent-fpac-soil-openai-sdk/` that calls the
   deployed server over HTTP as an MCP client** -- own `pyproject.toml` and
   `uv.lock`, excluded from root Ruff and pytest discovery, own CI job.
2. **Agent code inside the root package** -- import server tools in-process.
3. **Server-side agent loop (Databricks Supervisor API)** -- declare the MCP
   server as a hosted tool and let Databricks run the loop.

## Decision Outcome

Chosen option: "Separate uv project that calls the deployed server as an MCP
client", because it keeps the server package's dependencies and release path
unchanged, exercises the same deployed `/mcp` endpoint that other clients use,
and keeps the template's agent loop under our control for testing.

Conventions this sets:

* **Auth**: the agent connects as the app's service principal
  (`WorkspaceClient()`), not on behalf of the user. The SP needs `CAN_USE` on
  `mcp-fpac-soil`; Apps-hosted MCP servers accept OAuth only.
* **Tools only**: the agent uses MCP tools; no wrapper tools for MCP resources or
  prompts. The template's local `get_current_time` tool and `system.ai` server
  were removed.
* **Configuration by env var, read at call time** (`agent_server/config.py`):
  `AGENT_MODEL` (default `databricks-gpt-5-6-luna`, sourced from the
  `llm-endpoint` app resource), `FPAC_MCP_URL`, `FPAC_MCP_TIMEOUT_SECONDS`
  (default 180 s; long LESA and corridor tools exceed the 20 s client default).
  GPT-5 endpoints get `reasoning_effort="none"` for tool calling.
* **Chat system prompt in a file** (`agent_server/prompts/system_prompt.txt`)
  carrying the preliminary-screening limitation and the no-invented-values rule,
  with no steering toward specific tools.
* **Graceful degradation**: an unreachable server is dropped by the health check
  (one WARNING with traceback); the agent is told the tools are unavailable and
  must not answer from memory.
* **Deployment**: through the app's git source in the Apps UI. Resources are
  declared in `databricks.yml` for reference, but `databricks bundle deploy` is
  not used for this app.
* **Lint and CI boundary**: root Ruff has `extend-exclude = ["apps"]`; the app is
  checked by `make app-check` (Ruff on the files this repo owns, plus app pytest
  against the committed `uv.lock`) in the dedicated `agent-app` CI job.
* **Template trimming**: template assistant skills, Lakebase, quickstart,
  preflight, tool-discovery, and placeholder evaluation files were removed. Agent
  evaluation stays in `eval/databricks/` (T1).

### Consequences

* **Positive**: server and agent evolve and deploy independently; the agent
  exercises the production MCP endpoint; model, URL, and timeout change without
  code edits; offline tests cover config, construction, and MCP wiring.
* **Negative**: two uv projects and two lock files to maintain; the app's
  remaining template runtime files (`start_app.py`, `start_server.py`, `utils.py`,
  `app_diagnostics.py`) are not linted; SP auth means MCP calls are not
  attributed to the requesting user; a cold CI run of the app job takes about
  5 minutes, mostly package installation.

## Validation & Compliance

* `make app-check` (CI job `agent-app`): app tests in `tests/test_agent_config.py`,
  `tests/test_agent_construction.py`, `tests/test_agent_mcp_wiring.py`, and
  `tests/test_deploy_config.py`.
* Live validation (Plan 35, task 35.5.1) is manual: grants, redeploy, and the
  DISC-01, POINT-01, and LESA-01 prompts in the chat UI. Results are recorded in
  `planning/STATE_35.md`.
