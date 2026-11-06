# AGENTS.md - FPAC Soil Agent App

Databricks App (`agent-fpac-soil-openai-sdk`) that serves a chat agent which calls the deployed `mcp-fpac-soil` MCP server. Separate uv project from the repository root; see [ADR 0012](../../docs/decisions/0012-databricks-agent-app-as-separate-mcp-client.md).

## Quick Start

Run from the repository root:

```bash
# Lint the app files this repo owns, then run the app's offline tests (Python only)
make app-check

# Tests only (installs from the committed uv.lock with --frozen)
make app-test

# Vendored frontend: npm ci, read-only biome lint, build (needs Node 22 + npm)
make app-frontend-check
```

Run locally from this directory (needs Databricks auth and a `.env` copied from `.env.example`):

```bash
uv run start-app          # agent server + chat UI (npm ci, build, start in frontend/)
uv run start-app --no-ui  # agent server only; also the fallback when frontend/package.json is missing
uv run start-server       # agent server only
```

## Find Things

- `agent_server/agent.py` - agent construction (`create_agent`), MCP client (`init_fpac_mcp_server`), invoke and stream handlers.
- `agent_server/config.py` - env-var getters and defaults (`AGENT_MODEL`, `FPAC_MCP_APP`, `FPAC_MCP_URL`, `FPAC_MCP_TIMEOUT_SECONDS`); `FPAC_MCP_APP` is resolved to a URL once per process; stdlib only.
- `agent_server/prompts/system_prompt.txt` - chat system prompt.
- `agent_server/history.py` - multi-turn history normalization for the chat UI.
- `agent_server/geo.py` - `POST /api/geo/screen` (map panel screening, [ADR 0016](../../docs/decisions/0016-out-of-band-aoi-screening-handoff.md)): request limits, the two MCP calls, the browser-only `display` part (including the server `map` block) and the allowlisted `chat_summary`; also `POST /api/geo/map` for tool-card "Show on map" (two allowlisted tools, `include_map` forced, AOI reference substitution); routes registered in `start_server.py`; tests in `tests/test_geo_screen.py` and `tests/test_geo_map.py`.
- `agent_server/start_server.py`, `agent_server/utils.py`, `scripts/` - template runtime (server startup, stream processing, diagnostics, `start-app` launcher).
- `tests/` - offline tests; `conftest.py` sets dummy Databricks credentials.
- `app.yaml` - command and env vars used by the deployed app.
- `databricks.yml` - declared app resources (`llm-endpoint`, `mcp_server`, `experiment`); reference only.
- `README.md` - configuration, required grants, deploy path, and API usage.
- `frontend/` - vendored `e2e-chatbot-app-next` npm workspace (`client/`, `server/`, `packages/*`, root `package-lock.json`) from upstream base commit `0e572976459aafa3d41047067382cb9a6c015d52`, owned by this repo; local changes are listed in [ADR 0015](../../docs/decisions/0015-vendored-agent-app-frontend.md). Map panel code lives under `frontend/client/src/components/map/` (`MapPanel.tsx` entry, `useScreening.ts` calls `/api/geo/screen`, `farmlandClasses.ts` is the one class mapping, `ActiveAoiContext.tsx` keeps the chat's AOI in sessionStorage, `ActiveAoiChip.tsx` shows it in `multimodal-input.tsx`; `mapLayers.ts` draws server map blocks (ADR 0017); `MapResultContext.tsx` and `ShowOnMapButton.tsx` handle tool-card results; `overlays.ts` is the fixed context-layer catalog with `OverlayControl.tsx`; `identify.ts` and `IdentifyPopup.tsx` do identify and Use as AOI); the panel column is in `client/src/layouts/ChatLayout.tsx`; `chat.tsx` sends `activeAoi`, which `server/src/routes/chat.ts` and `databricksFetch` turn into `custom_inputs.active_aoi`.

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

### Change AOI Screening

1. The map AOI is chat session context ([ADR 0016](../../docs/decisions/0016-out-of-band-aoi-screening-handoff.md)): the browser keeps one AOI per conversation in `sessionStorage` and sends it with each turn as `custom_inputs.active_aoi`; the agent server keeps no AOI state.
2. The model gets the AOI reference and summary, never coordinates; the server swaps the geometry into a `geojson` or `geometry` tool argument equal to the active `aoi_ref`. Geometry may appear in chat traces and logs; repository files use synthetic coordinates only.
3. `geo.py` (`/api/geo/screen`): stateless, no request-body or MCP-payload logging, no traces (map-only screenings would be session-less): call MCP tools through `_call_tool_untraced`, never `McpServer.call_tool`, which `databricks_openai` wraps in `@mlflow.trace`. The summary goes through the `build_chat_summary` allowlist.
4. `/api/geo/map` follows the same rules (untraced, no body logging) and only accepts the tools in `geo.MAP_TOOLS`; keep the frontend `MAP_TOOLS` in `ShowOnMapButton.tsx` in step.
5. Map layers come from the server `map` block (ADR 0017); do not rebuild layers or legends in the browser. Overlay URLs are string constants in `overlays.ts` and `identify.ts`; never build them from chat or user input.
6. Cover changes in `tests/test_geo_screen.py`, `tests/test_geo_map.py` and `tests/test_aoi_context.py` (route tests run against the real `McpServer` class); run `make app-check`.

### Deploy

Deploy from the app's git source in the Databricks Apps UI and redeploy. Do not run `databricks bundle deploy` for this app. Required resources and grants are listed in `README.md`. Branch trials use the dev apps `mcp-fpac-soil-dev` and `agent-fpac-soil-dev` (README "Dev trial apps"); a push to the branch redeploys both.

### Frontend

1. Local changes are allowed. List every modified upstream file and every added path in the `### Local changes` section of ADR 0015 in the same change. Map and AOI code goes under `client/src/components/map/`.
2. Add dependencies with `npm install <pkg> --workspace @databricks/chatbot-client --save-exact` in `frontend/`; commit `client/package.json` and the regenerated root `package-lock.json` together; `npm ci` must pass from clean.
3. Run `make app-frontend-check` (Node 22). Never run the upstream `npm run lint` or `lint:fix`; they use `--write`. There is no typecheck target; upstream fails `tsc` at the base commit.
4. To update upstream, follow the ADR 0015 update procedure: re-copy with the exclusions, re-apply the listed local changes, regenerate the lockfile, and compare `git ls-tree` hashes (file modes included) for unchanged upstream files.
5. Update the base commit in ADR 0015, `README.md`, and this file.

## Infrastructure

- Python `>=3.11`; CI uses 3.11 (`agent-app` job in `.github/workflows/ci.yml`).
- Node 22 for `frontend/` (Databricks Apps runtime 22.16; CI `setup-node` 22). npm is not available on Databricks serverless by default.
- Root Ruff and pytest skip `apps/` (`extend-exclude = ["apps"]`); `make app-lint` lints the owned files explicitly (`APP_LINT_PATHS` in the root `Makefile`).
- MCP auth: app service principal via `WorkspaceClient()`; needs `CAN_USE` on the `mcp_server` resource app (`mcp-fpac-soil`, or `mcp-fpac-soil-dev` for the dev app).
- If the MCP server is unreachable, the health check logs a WARNING and the agent tells the user the tools are unavailable.

## References

- [ADR 0012](../../docs/decisions/0012-databricks-agent-app-as-separate-mcp-client.md) - app boundary, auth, configuration, deploy, and CI decisions.
- [ADR 0013](../../docs/decisions/0013-pin-pypi-default-index-in-every-uv-project.md) - uv index pinning.
- [ADR 0015](../../docs/decisions/0015-vendored-agent-app-frontend.md) - vendored chat frontend pin, exclusions, checks, and update procedure.
- [ADR 0003](../../docs/decisions/0003-preliminary-screening-authority-boundary.md) - preliminary screening boundary the prompt must preserve.
- [ADR 0016](../../docs/decisions/0016-out-of-band-aoi-screening-handoff.md) - AOI handoff between the map panel and chat.
- [ADR 0017](../../docs/decisions/0017-server-map-result-contract.md) - server map result contract (`include_map`, layers, legends, size cap).
- `planning/EXECUTION_PLAN_35.md` - original integration plan and decision log.
- `eval/databricks/` - T1 agent evaluation (not part of this app).
- [Master plan Track A](../../planning/MASTER_PLAN.md#track-a-agent-app) - roadmap and backlog for this app, including the map widget ([map research](../../planning/RESEARCH_MAP_WIDGET_AGENT_APP.md)).
