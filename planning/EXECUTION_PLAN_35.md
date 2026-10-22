# Execution Plan 35 — Wire the `agent-fpac-soil-openai-sdk` Agent App to fpac-soil-mcp

Branch: `feat/agent-app-fpac-mcp` (from `origin/main` `ca799b0`, template cherry-picked as `58b5e89`) · Template: `planning/PROMPT_TEMPLATE_35.md` · State: `planning/STATE_35.md`

## Goal & Scope

**Goal.** Turn the template agent app `agent-fpac-soil-openai-sdk` into an FPAC Soil agent. It should call the deployed `mcp-fpac-soil` MCP server as its own service principal, run on `databricks-gpt-5-6-luna` like the T1 eval agent, and use an FPAC chat system prompt. The repo should declare the app's required resources, and the change should pass CI and one manual live check after redeploy.

**In scope (research finding → task):** source: `planning/RESEARCH_JS_HARNESS_AGENT_APP_INTEGRATION.md` §3.2 plus the 403 the user reported on 2026-10-22.

| # | Finding | Task |
|---|---|---|
| A1 | No fpac MCP server wired in | 35.1.2 (config), 35.3.1 (wiring) |
| A2 | Agent SP lacks `CAN_USE` on `mcp-fpac-soil` | 35.1.3 (declare), 35.5.1 (grant, manual) |
| A3 | Deployed app has no `llm-endpoint` resource | 35.1.3 (declare), 35.5.1 (add, manual) |
| A4 | Generic system prompt | 35.1.2 (prompt file), 35.2.1 (use it) |
| M1 | Chat returns 403 `PERMISSION_DENIED`: `databricks-claude-sonnet-5-5` is disabled at the workspace level | 35.1.2 (default model), 35.2.1 |
| T1 | Template leftovers (`get_current_time`, system.ai UC-functions server) | 35.2.1, 35.3.1 |
| L1 | Cherry-picked template breaks root Ruff gates (105 lint errors, 16 unformatted files, all in `apps/`) | 35.1.1 |
| DOC | Deployers need the env vars and grants written down | 35.1.4 |

**Out of scope (explicit):**

- A5 server session mode: `mcp-fpac-soil` stays stateful HTTP (D8). There are no `src/` changes in this plan.
- MCP resources and prompts in the agent: no `read_resource` / `get_prompt` wrapper tools (D3).
- Upgrading the T1 judge to `databricks-claude-sonnet-5-5` (D6). This is its own follow-up, blocked until Databricks approves access to that model.
- On-behalf-of-user auth to MCP (D2).
- Bundle-managed deployment and `databricks bundle deploy` (D9).
- Automated live smoke script and T2 deployed-app eval (D10).
- All JS harness work (`eval/fpac_soil_mcp_harness/`, research §2). It lives on `feature/evalHarnessDatabricks01` and is not on this branch.
- Lint cleanup of template files this plan does not touch (D11).

**Verbatim user constraints:**

- "switch to a new branch if needed (based off main unless we need to base off the JS harness)"
- "b, match T1. likely we can upgrade to use sonnet 5.5 as judge" (model choice; judge upgrade deferred in D6)

## Decision log

| ID | Date | Decision |
|---|---|---|
| D1 | 2026-10-22 | Branch `feat/agent-app-fpac-mcp` from `origin/main`, with template commit `bc9ed3c` cherry-picked as `58b5e89`. The upstream link is unset, so the first push needs `git push -u origin feat/agent-app-fpac-mcp`. |
| D2 | 2026-10-22 | The agent authenticates to `mcp-fpac-soil` as the app service principal (`WorkspaceClient()`), not on behalf of the user. Requires `CAN_USE` for SP `app-2vrjmx agent-fpac-soil-openai-sdk` (ID 70416953425179). |
| D3 | 2026-10-22 | MCP tools only. Do not add resource or prompt wrapper tools. |
| D4 | 2026-10-22 | A new chat system prompt in the app (`agent_server/prompts/system_prompt.txt`), derived from eval v2's three rules, without the eval framing or forced-tool block, and with no steering toward specific tools (D12 of Plan 33). Loaded once and covered by a content test. |
| D5 | 2026-10-22 | Model `databricks-gpt-5-6-luna` (matches T1), sent `reasoning_effort="none"` via `ModelSettings(reasoning=Reasoning(effort="none"))`. The model name comes from env `AGENT_MODEL`. Verified with openai-agents 0.24.0 / openai 3.31.0: the Chat Completions path maps `reasoning.effort` to `reasoning_effort`. |
| D6 | 2026-10-22 | The judge upgrade to sonnet-5-5 is out of scope. A probe on 2026-10-22 shows sonnet-5-5 `PERMISSION_DENIED` (workspace-level), while luna and sonnet-4-5 respond OK. |
| D7 | 2026-10-22 | Remove `get_current_time` and `init_mcp_server` (system.ai). Add `init_fpac_mcp_server()` reading `FPAC_MCP_URL`. Keep `connect_healthy_mcp_servers` unchanged. |
| D8 | 2026-10-22 | No server change. Client timeout is 180 s (`FPAC_MCP_TIMEOUT_SECONDS`), matching the harness `MCP_TOOL_TIMEOUT_MS=180000` and replacing McpServer's 20 s default. |
| D9 | 2026-10-22 | Declare resources in `databricks.yml` (rename the app to `agent-fpac-soil-openai-sdk`, add an `app` resource `mcp-fpac-soil` with `CAN_USE`, and a `serving_endpoint` `databricks-gpt-5-6-luna` with `CAN_QUERY`). Deployment is a manual handoff (35.5.1): add the resources to the running app, switch the git source to this branch, redeploy, and run the live check. Never `bundle deploy`. |
| D10 | 2026-10-22 | Acceptance: targeted app pytest per task. Per wave, the app suite and the root offline suite stay green, plus root `ruff check .` / `ruff format --check .` once 35.1.1 lands. Final manual live check: 3 prompts in the chat UI (35.5.1). |
| D11 | 2026-10-22 | Root Ruff gets `extend-exclude = ["apps"]`. Files this plan creates or edits under `apps/` are still checked: tasks pass them to Ruff explicitly. |

## Recon log (2026-10-22)

- HEAD `58b5e89`. Untracked: `planning/RESEARCH_JS_HARNESS_AGENT_APP_INTEGRATION.md` (commit with the planning artifacts) and **`apps/agent-fpac-soil-openai-sdk/uv.lock`**. The planner's baseline `uv run` created that lockfile; it is not part of this plan (H4).
- Highest plan on any remote branch is 34, so this plan is 35. Plans 28-30 are used by other work.
- Baselines: root `uv run --group eval-databricks pytest -p no:cacheprovider -q` → 496 passed, 24 deselected (root `testpaths = ["tests", "eval"]` does not collect `apps/`). App `uv run --python 3.11 pytest -q` → 6 passed (`tests/test_history_normalization.py`). Root `ruff check . --extend-ignore EXE002` → 105 errors, all under `apps/`, clean with `--exclude apps`. `ruff format --check .` → 16 would reformat, all under `apps/`; 420 formatted with `--exclude apps`. CI: `.github/workflows/ci.yml` runs `make all`, which runs `ruff check .` and `ruff format --check .`.
- Root `pyproject.toml` `[tool.ruff]` L45-47 (`line-length = 100`, `target-version = "py311"`), `[tool.pytest.ini_options]` L49.
- App layout (`apps/agent-fpac-soil-openai-sdk/`): `agent_server/agent.py` (129 lines), `utils.py` (59), `history.py` (47), `start_server.py`, `evaluate_agent.py` (100); `app.yaml` (16); `databricks.yml` (56); `manifest.yaml`; `.env.example` (15); `pyproject.toml` (hatchling, `default-groups = ["dev", "setup"]`, `setup` has `ruamel.yaml`; `exclude-newer = "7 days"`); `README.md` (314); `tests/` has only `test_history_normalization.py` (unittest style, no conftest).
- `agent.py` anchors: client setup L29-34 (`set_default_openai_client(AsyncDatabricksOpenAI())` L30, `set_default_openai_api("chat_completions")` L31); `get_current_time` L37-40; `init_mcp_server` L43-48; `connect_healthy_mcp_servers` L51-75; `create_agent` L78-85 (`instructions="You are a helpful assistant."` L81, `model="databricks-claude-sonnet-5-5"` L82, `tools=[get_current_time]` L83); `invoke_handler` L88-105 (`async with AsyncExitStack() as stack:` L101); `stream_handler` L108-129 (L123).
- **Import hazard:** importing `agent_server.agent` builds `AsyncDatabricksOpenAI()` at module load, which fails with no Databricks credentials. It succeeds with dummy `DATABRICKS_HOST=https://example.cloud.databricks.com`, `DATABRICKS_TOKEN=dummy`, `DATABRICKS_CONFIG_FILE=/dev/null` (verified; no network call at import).
- `databricks_openai.agents.McpServer` 0.17.1 `__init__(url, workspace_client, timeout, params, **mcpserver_kwargs)`. It sets `params["timeout"]` and, unless given, `client_session_timeout_seconds = timeout`. Transport is `streamablehttp_client` with `DatabricksOAuthClientProvider(workspace_client)`. Base `MCPServerStreamableHttp` 0.24 also takes `max_retry_attempts`, `cache_tools_list`, `tool_filter` (unused here).
- `ModelSettings` 0.24 fields include `reasoning`. `Reasoning.effort` literal includes `"none"`. The Chat Completions model sends `reasoning_effort` and warns only on `reasoning.mode` / `reasoning.context`.
- Deployed app (`databricks apps get`, 2026-10-22): git source branch `template/agent-fpac-soil-openai-sdk-1792601940628`, `source_code_path` `apps/agent-fpac-soil-openai-sdk`, resources = `experiment` only (517983779529169), SP ID 70416953425179. `mcp-fpac-soil` ACL: team-03 `CAN_USE`, Andrew `CAN_MANAGE`, admins.
- MCP URL `https://mcp-fpac-soil-7474654188777746.aws.databricksapps.com/mcp`. Apps-hosted MCP accepts OAuth only, not PATs (Databricks docs, "MCP authentication and networking").
- `manifest.yaml` `resource_specs` uses `experiment_spec` and `serving_endpoint_spec` (no endpoint name). No verified schema exists for an app-type spec, so `manifest.yaml` is not edited (judgment call J1).
- Live-check prompts: `DISC-01`, `POINT-01` (Marshall County, IA), `LESA-01` (Maple Valley Substation) in `eval/prompt_test_cases.json` (dataset 2.0.1).
- Workspace recipe: file writes only through `editAsset`; shell writes and deletes under `/Workspace` may be blocked. Use `UV_PROJECT_ENVIRONMENT=/tmp/agent-venv` for the app and `/tmp/fpac-venv` for the root. This surface cannot spawn sub-agents: the orchestrator runs tasks inline but still writes each micro-TODO first (Plan 34 precedent).

## Shared contracts

- **K1 — `agent_server/config.py`** (pure: stdlib only, no `agents`/`mlflow`/`databricks` imports):
  - `DEFAULT_AGENT_MODEL = "databricks-gpt-5-6-luna"`
  - `DEFAULT_FPAC_MCP_URL = "https://mcp-fpac-soil-7474654188777746.aws.databricksapps.com/mcp"`
  - `DEFAULT_FPAC_MCP_TIMEOUT_SECONDS = 180.0`
  - `agent_model() -> str`: env `AGENT_MODEL`, stripped; empty or unset → default.
  - `fpac_mcp_url() -> str`: env `FPAC_MCP_URL`, same rule.
  - `fpac_mcp_timeout_seconds() -> float`: env `FPAC_MCP_TIMEOUT_SECONDS`; empty or unset → default; non-numeric or `<= 0` → `ValueError` naming the variable.
  - `uses_reasoning_effort_none(model: str) -> bool`: `True` iff `model.startswith("databricks-gpt-5")`.
  - `load_system_prompt() -> str`: `functools.lru_cache`; reads `Path(__file__).parent / "prompts" / "system_prompt.txt"` as UTF-8 and returns it `.strip()`ped.
  - Env is read at call time, not import time, so tests can monkeypatch.
- **K2 — `create_agent(mcp_servers: list[McpServer] | None = None, *, tools_unavailable: bool = False) -> Agent`**: `name="FPAC Soil Agent"`, `instructions=load_system_prompt()` plus, when `tools_unavailable`, a blank line and `TOOLS_UNAVAILABLE_NOTE`, `model=agent_model()`, `tools=[]`, `mcp_servers=mcp_servers or []`, `model_settings=ModelSettings(reasoning=Reasoning(effort="none"))` when `uses_reasoning_effort_none(model)`, else `ModelSettings()`. `TOOLS_UNAVAILABLE_NOTE` is a module constant: `"The fpac-soil-mcp tools are unavailable for this request. Tell the user you cannot run the screening right now; do not answer from memory."` (judgment call J2).
- **K3 — `init_fpac_mcp_server(workspace_client: WorkspaceClient) -> McpServer`** (sync): `McpServer(url=fpac_mcp_url(), name=FPAC_MCP_SERVER_NAME, workspace_client=workspace_client, timeout=fpac_mcp_timeout_seconds())`, with `FPAC_MCP_SERVER_NAME = "fpac-soil-mcp"`. Both handlers run, inside their existing `AsyncExitStack`: `servers, unavailable = await connect_healthy_mcp_servers(stack, [init_fpac_mcp_server(WorkspaceClient())])`, then `create_agent(mcp_servers=servers, tools_unavailable=bool(unavailable))`. When `unavailable` is non-empty, log one `logger.warning` naming the servers. Handler signatures, decorators, history normalization, and stream event processing do not change.
- **K4 — env names** (`app.yaml`, `databricks.yml`, `.env.example`, README): `AGENT_MODEL` (in `app.yaml` and `databricks.yml` via `valueFrom` / `value_from: "llm-endpoint"`), `FPAC_MCP_URL`, `FPAC_MCP_TIMEOUT_SECONDS` (`"180"`). The serving-endpoint resource key stays `llm-endpoint`.

## Hazards

- **H1** Import side effect (recon): any test importing `agent_server.agent` needs the dummy Databricks env *before* import. `tests/conftest.py` (35.1.2) sets it at module top with `os.environ.setdefault`. Tests must never make network calls; patch `McpServer`/`Runner` and never call a real endpoint.
- **H2** Same file across waves: `agent.py` is edited by 35.2.1, then 35.3.1, sequentially. 35.3.1 must not undo K2.
- **H3** Ruff path behavior after D11: root `extend-exclude` skips `apps/` during discovery, but explicitly passed file paths are still linted (`force-exclude` is off). Verified 2026-10-22 with `--config 'extend-exclude=["apps"]'`: `ruff check .` is clean, and an explicit `apps/.../scripts/start_app.py` still reports 5 errors. Task acceptance commands pass the task's own files explicitly. App files resolve settings from the root `pyproject.toml`, because the app's own `pyproject.toml` has no `[tool.ruff]`.
- **H8** Async tests: the app `dev` group has `pytest` but no `pytest-asyncio`, and the root `asyncio_mode = "auto"` does not apply to the app project. Drive coroutines with `asyncio.run(...)` inside sync tests. The `@invoke()` / `@stream()` decorators (MLflow `agent_server`) return a sync `functools.wraps` wrapper that returns the coroutine or async generator (verified), so `asyncio.run(agent_module.invoke_handler(req))` works. For the stream handler, collect events in an `async def` helper run by `asyncio.run`. Do not add dependencies.
- **H4** Untracked `apps/agent-fpac-soil-openai-sdk/uv.lock`, created by the planner's baseline run: **do not stage or commit it.** With `pyproject.toml` + `uv.lock` present, Apps deploy switches to `uv sync`, which changes install behavior. Stage files by explicit path only. The user decides whether to delete it.
- **H5** Deployed app vs repo: until 35.5.1 switches the git source, the running app still pulls the template branch, so a passing branch does not change the live 403.
- **H6** Live answers come from public USDA and Census data. The live check uses dataset prompts only (synthetic or public inputs).
- **H7** `valueFrom: "llm-endpoint"` resolves only after the resource is added to the running app (35.5.1). Before that, `AGENT_MODEL` is empty and K1 falls back to the default.

## Wave table

| Wave | Theme | Task | Title | Depends on | Files (must edit / can create) |
|---|---|---|---|---|---|
| 1 | Config and scaffolding | 35.1.1 | Root Ruff excludes `apps/` | — | `pyproject.toml` |
| 1 | Config and scaffolding | 35.1.2 | Agent config module and chat system prompt | — | create `apps/…/agent_server/config.py`, `apps/…/agent_server/prompts/system_prompt.txt`, `apps/…/tests/conftest.py`, `apps/…/tests/test_agent_config.py` |
| 1 | Config and scaffolding | 35.1.3 | Deployment config declarations | — | `apps/…/app.yaml`, `apps/…/databricks.yml`, `apps/…/.env.example`; create `apps/…/tests/test_deploy_config.py` |
| 1 | Config and scaffolding | 35.1.4 | App README FPAC section | — | `apps/…/README.md` |
| 2 | Agent construction | 35.2.1 | FPAC agent: model, prompt, reasoning, no template tool | 35.1.2 | `apps/…/agent_server/agent.py`; create `apps/…/tests/test_agent_construction.py` |
| 3 | MCP wiring | 35.3.1 | Connect `mcp-fpac-soil` in both handlers | 35.2.1 | `apps/…/agent_server/agent.py`; create `apps/…/tests/test_agent_mcp_wiring.py` |
| 4 | Verification (offline, serial) | 35.4.1 | Full offline gates | waves 1-3 | `planning/STATE_35.md` only |
| 5 | Deploy + live (MANUAL) | 35.5.1 | Grants, redeploy, 3-prompt live check | 35.4.1 | `planning/STATE_35.md` only |

`apps/…` = `apps/agent-fpac-soil-openai-sdk`. Files are pairwise disjoint within every wave: 35.1.2 owns `tests/conftest.py`, and 35.1.3's test does not import `agent_server`. Waves 1-4 are offline. Wave 5 is manual, done by the user or on the Apps page. Scratch output goes in `.development/` (untracked).

## Task specs

### 35.1.1 — Root Ruff excludes `apps/`

- **Repo:** fpac-soil-mcp · **Depends on:** none
- **Files in scope:** must edit `pyproject.toml` (root).
- **Spec:** Implement D11. Under `[tool.ruff]`, add `extend-exclude = ["apps"]` with a one-line comment: Databricks app templates are separate uv projects; files changed under `apps/` are linted explicitly. Change nothing else in the file.
- **Constraints:** no edits under `apps/`; do not change the pytest config, dependencies, or `[tool.uv]`.
- **Anchors:** `[tool.ruff]` L45-47.
- **Acceptance:** `UV_PROJECT_ENVIRONMENT=/tmp/fpac-venv uv run ruff check . --extend-ignore EXE002` → All checks passed. `uv run ruff format --check .` → 0 would reformat. `uv run ruff check --extend-ignore EXE002 apps/agent-fpac-soil-openai-sdk/agent_server/history.py` still runs (proves explicit paths are linted, H3; record the result, pass or fail).

### 35.1.2 — Agent config module and chat system prompt

- **Repo:** fpac-soil-mcp · **Depends on:** none
- **Files in scope:** can create `apps/agent-fpac-soil-openai-sdk/agent_server/config.py`, `apps/agent-fpac-soil-openai-sdk/agent_server/prompts/system_prompt.txt`, `apps/agent-fpac-soil-openai-sdk/tests/conftest.py`, `apps/agent-fpac-soil-openai-sdk/tests/test_agent_config.py`.
- **Spec:** Implement K1 exactly. Write `system_prompt.txt` with this text verbatim (D4):

  ```text
  You are the FPAC Soil assistant. You help USDA staff run preliminary Farmland Protection Policy Act (FPPA) screening with the fpac-soil-mcp tools, which use USDA NRCS Soil Data Access (SSURGO), US Census Bureau TIGERweb, and USDA NASS data.

  Your answers are preliminary screening only. They are based on SSURGO soil inventory data under 7 CFR Part 657 and are not an official FPPA determination, a Land Evaluation and Site Assessment (LESA) score, or a completed Form AD-1006 or Form NRCS-CPA-106. Say so in every answer that reports soil or farmland results, and refer formal determinations to the appropriate USDA NRCS State or local office.

  Report tool results as returned. If a tool returns no data or an error for an input, say that plainly; do not estimate, infer, or invent values.
  ```

  `tests/conftest.py`: at module top, `os.environ.setdefault` for `DATABRICKS_HOST=https://example.cloud.databricks.com`, `DATABRICKS_TOKEN=dummy`, `DATABRICKS_CONFIG_FILE=/dev/null` (H1), plus a docstring saying why. `tests/test_agent_config.py` (pytest style, `monkeypatch`):
  - defaults when the env is unset or blank for all three getters
  - env overrides
  - timeout `"abc"`, `"0"`, and `"-5"` each raise `ValueError` mentioning `FPAC_MCP_TIMEOUT_SECONDS`
  - `uses_reasoning_effort_none` is True for `databricks-gpt-5-6-luna` and False for `databricks-claude-sonnet-4-5`
  - `DEFAULT_AGENT_MODEL != "databricks-claude-sonnet-5-5"` (M1 guard)
  - the prompt contains `7 CFR Part 657`, `AD-1006`, `NRCS-CPA-106`, and `do not estimate, infer, or invent values`
  - the prompt does not contain `evaluation agent`, `[forced-tool]`, or any tool name from the server: scan for `get_farmland_classification`, `analyze_`, `calculate_preliminary_lesa`, `explain_fppa_screening_scope` (D4/D12)
  - `load_system_prompt() is load_system_prompt()` (cached)
- **Constraints:** `config.py` must stay pure (K1). Do not edit `agent.py` or any existing file.
- **Anchors:** none (new files). For reading the prompt, follow `eval/databricks/agent.py` `def load_system_prompt` (grep), simplified to a single file.
- **Reference:** `eval/databricks/prompts/system_prompt_v2.txt` for wording lineage.
- **Acceptance:** `cd apps/agent-fpac-soil-openai-sdk && UV_PROJECT_ENVIRONMENT=/tmp/agent-venv PYTHONDONTWRITEBYTECODE=1 uv run --python 3.11 pytest -p no:cacheprovider tests/test_agent_config.py tests/test_history_normalization.py -q` passes. From the repo root, `UV_PROJECT_ENVIRONMENT=/tmp/fpac-venv uv run ruff check --extend-ignore EXE002 <the 3 .py files>` and `uv run ruff format --check <same>` pass.

### 35.1.3 — Deployment config declarations

- **Repo:** fpac-soil-mcp · **Depends on:** none
- **Files in scope:** must edit `apps/agent-fpac-soil-openai-sdk/app.yaml`, `apps/agent-fpac-soil-openai-sdk/databricks.yml`, `apps/agent-fpac-soil-openai-sdk/.env.example`. Can create `apps/agent-fpac-soil-openai-sdk/tests/test_deploy_config.py`.
- **Spec:** Implement K4 and D9.
  - **`app.yaml`:** append env entries:
    - `AGENT_MODEL` with `valueFrom: "llm-endpoint"`
    - `FPAC_MCP_URL` with the K1 default URL
    - `FPAC_MCP_TIMEOUT_SECONDS` with `"180"`
  - **`databricks.yml`:**
    - Set `resources.apps.agent_openai_agents_sdk.name` (L7) and the prod-target `name` (L56) to `agent-fpac-soil-openai-sdk`. Keep the resource key and `bundle.name` unchanged.
    - Mirror the three env entries under `config.env`, using `value_from`.
    - Change `llm-endpoint` `serving_endpoint.name` (L39) to `databricks-gpt-5-6-luna`, and update the NOTE comment (L33-36) to point at `AGENT_MODEL`.
    - Add an `app` resource: `name: 'mcp_server'`, with `app: {name: 'mcp-fpac-soil', permission: CAN_USE}`. Use the shape from `.claude/skills/add-tools/examples/custom-mcp-server.md`.
  - **`.env.example`:** add `AGENT_MODEL=databricks-gpt-5-6-luna`, `FPAC_MCP_URL=<default>`, and `FPAC_MCP_TIMEOUT_SECONDS=180`, with one comment line.
  - **`tests/test_deploy_config.py`:** parse `app.yaml` and `databricks.yml` with `ruamel.yaml` (`YAML(typ="safe")`; the `setup` group is a default group). Assert:
    - the three env names are present in both files, with matching values or `valueFrom`
    - the `llm-endpoint` name is `databricks-gpt-5-6-luna`
    - the `mcp-fpac-soil` app resource has `CAN_USE`
    - the app name is `agent-fpac-soil-openai-sdk` in both places
    - no file mentions `databricks-claude-sonnet-5-5`

    Use literal expected strings. Do not import `agent_server`.
- **Constraints:** do not edit `manifest.yaml` (J1), `pyproject.toml`, `scripts/`, or `agent_server/`. Do not add a `uv.lock` (H4).
- **Anchors:** `app.yaml` L4-16. `databricks.yml` L6-7, L12-24, L26-40, L53-56.
- **Reference:** `.claude/skills/add-tools/examples/custom-mcp-server.md` (app resource) and `.claude/skills/add-tools/examples/serving-endpoint.yaml`.
- **Acceptance:** `cd apps/agent-fpac-soil-openai-sdk && UV_PROJECT_ENVIRONMENT=/tmp/agent-venv PYTHONDONTWRITEBYTECODE=1 uv run --python 3.11 pytest -p no:cacheprovider tests/test_deploy_config.py -q` passes. Ruff check and format on the new test file pass.

### 35.1.4 — App README FPAC section

- **Repo:** fpac-soil-mcp · **Depends on:** none (wording follows K1, K4, D9; no code dependency)
- **Files in scope:** must edit `apps/agent-fpac-soil-openai-sdk/README.md`.
- **Spec:** Insert an `## FPAC Soil configuration` section after the title block. It must cover:
  - what the agent does, with the preliminary-screening limitation sentence from the prompt
  - the env table (K4: name, default, purpose)
  - required grants: SP `CAN_USE` on `mcp-fpac-soil`, and the `llm-endpoint` resource with `CAN_QUERY` on the configured model
  - the note that `databricks-claude-sonnet-5-5` is disabled in this workspace (2026-10-22)
  - the deploy path: the UI-created app's git source is `feat/agent-app-fpac-mcp` → `main` after merge; do not run `databricks bundle deploy` (D9)
  - the 180 s timeout and why

  Keep the rest of the template README unchanged. Plain, short sentences.
- **Constraints:** README only.
- **Anchors:** the first `## ` heading in `README.md` (grep `^## `).
- **Acceptance:** `grep -c "FPAC_MCP_URL\|AGENT_MODEL\|CAN_USE" apps/agent-fpac-soil-openai-sdk/README.md` ≥ 3. The orchestrator reviews the diff for accuracy against K1 and K4.

### 35.2.1 — FPAC agent: model, prompt, reasoning, no template tool

- **Repo:** fpac-soil-mcp · **Depends on:** 35.1.2 done
- **Files in scope:** must edit `apps/agent-fpac-soil-openai-sdk/agent_server/agent.py`. Can create `apps/agent-fpac-soil-openai-sdk/tests/test_agent_construction.py`.
- **Spec:** Implement K2.
  - Delete `get_current_time` (L37-40) and the now-unused `datetime` and `function_tool` imports.
  - Import `ModelSettings` from `agents` and `Reasoning` from `openai.types.shared`.
  - Import `agent_model`, `load_system_prompt`, and `uses_reasoning_effort_none` from `agent_server.config`.
  - Add the `TOOLS_UNAVAILABLE_NOTE` constant.
  - Rewrite `create_agent` per K2.
  - Leave `init_mcp_server`, the handlers, and the L29-34 client setup unchanged. 35.3.1 replaces `init_mcp_server`.
  - Tests (the pytest-style conftest from 35.1.2 provides the env):
    - default: model is luna, `model_settings.reasoning.effort == "none"`, `tools == []`, and instructions equal `load_system_prompt()`
    - `AGENT_MODEL=databricks-claude-sonnet-4-5`: `model_settings.reasoning is None`
    - `tools_unavailable=True`: instructions end with `TOOLS_UNAVAILABLE_NOTE`
    - `mcp_servers` passthrough: a sentinel list is kept
    - `not hasattr(agent_module, "get_current_time")`
- **Constraints:** no handler changes. No network. Do not edit `config.py` (needing to means a K1 bug: stop and report).
- **Anchors:** imports L1-25, `get_current_time` L37, `def create_agent` L78.
- **Reference:** `eval/databricks/agent.py` `def chat_params` (grep) for the GPT-5 reasoning rule.
- **Acceptance:** `cd apps/agent-fpac-soil-openai-sdk && UV_PROJECT_ENVIRONMENT=/tmp/agent-venv PYTHONDONTWRITEBYTECODE=1 uv run --python 3.11 pytest -p no:cacheprovider tests -q` passes (all app tests). Ruff check and format on `agent_server/agent.py` and the new test pass.

### 35.3.1 — Connect `mcp-fpac-soil` in both handlers

- **Repo:** fpac-soil-mcp · **Depends on:** 35.2.1 done
- **Files in scope:** must edit `apps/agent-fpac-soil-openai-sdk/agent_server/agent.py`. Can create `apps/agent-fpac-soil-openai-sdk/tests/test_agent_mcp_wiring.py`.
- **Spec:** Implement K3 and D7.
  - Replace `init_mcp_server` with sync `init_fpac_mcp_server` and the `FPAC_MCP_SERVER_NAME` constant.
  - Remove the `build_mcp_url` import if it becomes unused. Do not edit `utils.py`.
  - In both handlers, replace the commented example block (L92-100, L114-122) with the K3 calls and a 2-line comment: service principal auth (D2), and that health-checking drops a failing server.
  - Import `fpac_mcp_url` and `fpac_mcp_timeout_seconds`.
  - Tests (use `unittest.mock` / `monkeypatch`; no network):
    - `init_fpac_mcp_server(mock_ws)`: patch `agent_module.McpServer` and assert it is called with `url=`, `name="fpac-soil-mcp"`, `workspace_client=mock_ws`, and `timeout=180.0`. Repeat with env overrides for URL and timeout.
    - For both handlers, patch `WorkspaceClient`, `init_fpac_mcp_server`, `connect_healthy_mcp_servers`, `Runner.run` / `Runner.run_streamed`, and `create_agent`:
      - healthy path: `create_agent` is called with `mcp_servers=[server], tools_unavailable=False`
      - unavailable path: `create_agent` is called with `tools_unavailable=True`, and a warning is logged (`caplog`)
    - Build `ResponsesAgentRequest(input=[{"role": "user", "content": "hi"}])`. For the stream handler, feed an empty async iterator from `stream_events()`.
    - `not hasattr(agent_module, "init_mcp_server")`.
- **Constraints:** do not change `connect_healthy_mcp_servers`, `create_agent` (K2), decorators, handler signatures, history normalization, or `process_agent_stream_events` usage. Call the decorated handlers as described in H8 (`asyncio.run`, no pytest-asyncio). Do not change the decorators.
- **Anchors:** `init_mcp_server` L43-48, `invoke_handler` L88-105, `stream_handler` L108-129 (re-grep: 35.2.1 shifted lines).
- **Reference:** the template's commented example in the handlers, which this task implements.
- **Acceptance:** `cd apps/agent-fpac-soil-openai-sdk && UV_PROJECT_ENVIRONMENT=/tmp/agent-venv PYTHONDONTWRITEBYTECODE=1 uv run --python 3.11 pytest -p no:cacheprovider tests -q` passes. Ruff check and format on `agent_server/agent.py` and the new test pass. `grep -n "system/ai\|get_current_time\|claude-sonnet-5-5" agent_server/agent.py` prints nothing.

### 35.4.1 — Full offline gates (serial)

- **Repo:** fpac-soil-mcp · **Depends on:** waves 1-3 done
- **Files in scope:** `planning/STATE_35.md` only.
- **Spec:** Run serially and record the counts in the wave-gates table:
  - the full app suite
  - root `uv run --group eval-databricks pytest -p no:cacheprovider -q` (expect 496 passed, 24 deselected; this plan adds no root tests)
  - root `ruff check . --extend-ignore EXE002` and `ruff format --check .`
  - Ruff on every `apps/` file this plan created or edited
  - `git status --short`: only expected files changed, and `uv.lock` is still untracked (H4)
- **Acceptance:** all green. Any failure goes back to the owning task through the escalation ladder.

### 35.5.1 — Grants, redeploy, and 3-prompt live check (MANUAL)

- **Repo:** deployed workspace apps · **Depends on:** 35.4.1, branch pushed (`git push -u origin feat/agent-app-fpac-mcp`)
- **Files in scope:** `planning/STATE_35.md` only (record results).
- **Spec:** The user (or the Apps page agent) runs these steps. This orchestrator surface cannot deploy apps or change their permissions.
  1. Grant SP `app-2vrjmx agent-fpac-soil-openai-sdk` `CAN_USE` on `mcp-fpac-soil`, preferably by adding an App resource `mcp_server` → `mcp-fpac-soil`, `CAN_USE`, to `agent-fpac-soil-openai-sdk`.
  2. Add a serving-endpoint resource `llm-endpoint` → `databricks-gpt-5-6-luna`, `CAN_QUERY`.
  3. Switch the app's git source branch to `feat/agent-app-fpac-mcp` (same `source_code_path`) and redeploy.
  4. In the chat UI, run the `user_prompt` of `DISC-01`, `POINT-01`, and `LESA-01`.

  Each must:
  - return no 403
  - show at least one fpac MCP tool call in the trace in experiment `517983779529169`
  - include the preliminary-screening limitation
  - LESA-01 must also finish inside the 180 s timeout

  Record the trace IDs and pass/fail per prompt.
- **Acceptance:** 3/3 prompts meet all criteria. If the MCP connection fails (the agent says tools are unavailable), check the grant first, then session errors (out-of-scope A5; open a follow-up).

## Judgment calls (flagged in review)

- **J1** `manifest.yaml` is not edited (D9 mentioned a matching spec). No verified schema exists for an app-type `resource_spec`, and the UI flow adds resources directly. Revisit if the Apps docs publish one.
- **J2** K2's `tools_unavailable` note is a small addition beyond the template's "drop and continue" behavior. Without it, the model could answer screening questions from memory when the MCP server is down, which goes against the prompt's do-not-invent rule.
- **J3** 35.1.4 (README) was not requested by name. It exists because D9 makes deployment a manual handoff that needs written steps.
