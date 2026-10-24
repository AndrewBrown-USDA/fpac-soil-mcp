# AGENTS.md - FPAC Soil Agent App

Databricks App (`agent-fpac-soil-openai-sdk`) that serves a chat agent which calls the deployed `mcp-fpac-soil` MCP server. Separate uv project from the repository root; see [ADR 0012](../../docs/decisions/0012-databricks-agent-app-as-separate-mcp-client.md).

## Quick Start

Run from the repository root:

```bash
# Lint the app files this repo owns, then run the app's offline tests
make app-check

# Tests only (installs from the committed uv.lock with --frozen)
make app-test
```

Run locally from this directory (needs Databricks auth and a `.env` copied from `.env.example`):

```bash
uv run start-app      # agent server + chat UI
uv run start-server   # agent server only
```

## Find Things

- `agent_server/agent.py` - agent construction (`create_agent`), MCP client (`init_fpac_mcp_server`), invoke and stream handlers.
- `agent_server/config.py` - env-var getters and defaults (`AGENT_MODEL`, `FPAC_MCP_URL`, `FPAC_MCP_TIMEOUT_SECONDS`); stdlib only.
- `agent_server/prompts/system_prompt.txt` - chat system prompt.
- `agent_server/history.py` - multi-turn history normalization for the chat UI.
- `agent_server/start_server.py`, `agent_server/utils.py`, `scripts/` - template runtime (server startup, stream processing, diagnostics, `start-app` launcher).
- `tests/` - offline tests; `conftest.py` sets dummy Databricks credentials.
- `app.yaml` - command and env vars used by the deployed app.
- `databricks.yml` - declared app resources (`llm-endpoint`, `mcp_server`, `experiment`); reference only.
- `README.md` - configuration, required grants, deploy path, and API usage.

## Workflows

### Change Agent Behavior

1. Model, MCP URL, or timeout: change env vars in `app.yaml` (and mirror in `databricks.yml` and `.env.example`); defaults live in `config.py`.
2. Instructions: edit `system_prompt.txt`. Keep the preliminary-screening limitation and the no-invented-values rule; do not name specific tools. `tests/test_agent_config.py` checks both.
3. Agent wiring: edit `agent.py`; cover it in `tests/test_agent_construction.py` or `tests/test_agent_mcp_wiring.py`.
4. Run `make app-check`.

### Change Dependencies

1. Edit `pyproject.toml`, then run `uv lock` in this directory.
2. Keep the PyPI `[[tool.uv.index]]` block ([ADR 0013](../../docs/decisions/0013-pin-pypi-default-index-in-every-uv-project.md)); `test_lockfile_uses_public_pypi` fails if proxy URLs reach `uv.lock`.
3. Commit `pyproject.toml` and `uv.lock` together.

### Deploy

Deploy from the app's git source in the Databricks Apps UI and redeploy. Do not run `databricks bundle deploy` for this app. Required resources and grants are listed in `README.md`.

## Infrastructure

- Python `>=3.11`; CI uses 3.11 (`agent-app` job in `.github/workflows/ci.yml`).
- Root Ruff and pytest skip `apps/` (`extend-exclude = ["apps"]`); `make app-lint` lints the owned files explicitly (`APP_LINT_PATHS` in the root `Makefile`).
- MCP auth: app service principal via `WorkspaceClient()`; needs `CAN_USE` on `mcp-fpac-soil`.
- If the MCP server is unreachable, the health check logs a WARNING and the agent tells the user the tools are unavailable.

## References

- [ADR 0012](../../docs/decisions/0012-databricks-agent-app-as-separate-mcp-client.md) - app boundary, auth, configuration, deploy, and CI decisions.
- [ADR 0013](../../docs/decisions/0013-pin-pypi-default-index-in-every-uv-project.md) - uv index pinning.
- [ADR 0003](../../docs/decisions/0003-preliminary-screening-authority-boundary.md) - preliminary screening boundary the prompt must preserve.
- `planning/EXECUTION_PLAN_35.md` - original integration plan and decision log.
- `eval/databricks/` - T1 agent evaluation (not part of this app).
- [Master plan Track A](../../planning/MASTER_PLAN.md#track-a-agent-app) - roadmap and backlog for this app, including the map widget ([map research](../../planning/RESEARCH_MAP_WIDGET_AGENT_APP.md)).
