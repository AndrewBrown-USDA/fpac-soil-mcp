# Research: Node.js UI Harness and the `agent-fpac-soil-openai-sdk` Agent App

Date: 2026-10-22. Branch inspected: `feature/evalHarnessDatabricks01` (HEAD `6574461`, 2 ahead / 77 behind `origin/main` `ca799b0`).

## Question

How does the new JavaScript harness (`eval/fpac_soil_mcp_harness/`) fit with the custom Databricks agent app `agent-fpac-soil-openai-sdk`, and what has to change to integrate them?

## Summary

1. The harness and the agent app solve different problems. The harness is a **deterministic MCP client** (no LLM) that calls tools, resources, and prompts directly[^h-readme]. The agent app is an **LLM agent** (OpenAI Agents SDK behind MLflow `AgentServer`) that picks tools itself[^a-agent]. They meet at one point: both should talk to the same deployed MCP server, `mcp-fpac-soil`.
2. The agent app is still the **unchanged template**. It has no fpac MCP server wired in, the generic system prompt, and a placeholder `get_current_time` tool[^a-agent]. Until that changes, there is nothing fpac-specific in the agent to test.
3. **Do not embed the harness in the agent app.** The agent app's root has no `package.json`; its Node chat UI is cloned and run at startup by `scripts/start_app.py`, behind `AgentServer`'s chat proxy[^a-start]. A third process would need its own routing, and the harness uses root-absolute `/api/...` fetch paths[^h-appjs] that break under a sub-path. Two cleaner options are below; option A is the recommendation.
4. The harness's network auth (a static `MCP_AUTH_TOKEN` bearer[^h-bridge]) does not fit Apps: MCP servers hosted on Databricks Apps **require OAuth and reject PATs**[^d-mcpauth], and OAuth tokens expire. Any Apps-hosted harness needs an OAuth M2M token provider that refreshes.
5. Blockers on the agent side: the agent's service principal has **no `CAN_USE` on `mcp-fpac-soil`**[^p-perms], and the deployed app has only the `experiment` resource, **not** the `llm-endpoint` (`CAN_QUERY`) resource the template's `databricks.yml` declares[^a-get][^a-bundle].

## 1. What was reviewed

| Item | Location | Notes |
| --- | --- | --- |
| Harness | `eval/fpac_soil_mcp_harness/` (commits `6023abe`, `6574461`, Ravi Kaushika) | Express 4 + `@modelcontextprotocol/sdk` ^1.12.0, Node >= 18.18[^h-pkg] |
| Agent app | `apps/agent-fpac-soil-openai-sdk` on `origin/template/agent-fpac-soil-openai-sdk-1792601940628` (`bc9ed3c`) | Deployed SNAPSHOT, RUNNING, MEDIUM[^a-get] |
| MCP server app | `mcp-fpac-soil` | `https://mcp-fpac-soil-7474654188777746.aws.databricksapps.com/mcp` |

## 2. Harness review

### 2.1 Architecture

* `server.js` serves `public/` and exposes a REST bridge (`/api/tools`, `/api/tools/:name/call`, `/api/eval-cases/:id/run`, and others)[^h-server].
* `lib/mcpBridge.js` wraps the SDK `Client` over stdio, SSE, or Streamable HTTP. A single process-wide `McpBridge` instance holds one connection[^h-bridge].
* `lib/evalCases.js` reads `eval/prompt_test_cases.json` and derives a direct invocation per case from `harness_arguments`, then `CASE_ARGUMENTS`, then `sample_geometry`[^h-eval].

### 2.2 Fixed since the 2026-10-20 review

* Root `.gitignore` no longer has `lib/`, so `lib/*.js` is now tracked. `node_modules/` and `package-lock.json` are ignored[^g-ignore].

### 2.3 Open issues

| # | Issue | Evidence | Why it matters |
| --- | --- | --- | --- |
| H1 | `package-lock.json` is gitignored | `.gitignore` after `6574461`[^g-ignore] | Apps runs `npm install` without a lockfile, so every deploy resolves `^1.12.0` again[^d-deploy]. Commit a lockfile (or a `pnpm-lock.yaml`) for reproducible deploys. |
| H2 | Static bearer token only | `mcpBridge.js` L95, `server.js` L109[^h-bridge][^h-server] | Apps-hosted MCP needs OAuth, not PAT[^d-mcpauth]. A one-time OAuth token expires and there is no refresh. |
| H3 | Port/host config ignores Apps env | `config.js` L56-61 reads only `HARNESS_HOST` / `HARNESS_PORT` (default 127.0.0.1:3030)[^h-config] | Apps provides `DATABRICKS_APP_PORT` (and `PORT` for Express)[^d-env]. Without a fallback, the app listens on the wrong port. |
| H4 | Eval file is outside the harness folder | `config.js` L67 resolves `../prompt_test_cases.json`[^h-config] | If the harness folder is the Apps `source_code_path`, the dataset is not uploaded. |
| H5 | Default mode is stdio `uv run fpac-soil-mcp` from repo root | `config.js` L70-73[^h-config] | Not usable from a harness-only app. Use `MCP_MODE=http`. |
| H6 | Keyword scoring diverges from Python | `checkKeywords` is a plain normalized substring check[^h-eval] | `eval/common/matching.keywords_present` on `main` treats CFR forms as equal and adds digit-edge boundaries (Plans 33/34). JS and Python scores can disagree on the same output. |
| H7 | Root-absolute fetch paths | `public/app.js` calls `api("/api/...")`[^h-appjs] | Works only when the harness is served at `/`. |
| H8 | Branch drift | 77 commits behind `origin/main` | Rebase before a PR. `main` has dataset 2.0.1 and `eval/common`, `eval/contract`, `eval/databricks`. The loader tolerates the 2.0.1 schema (`sample_geometry` is still in 9 cases). |
| H9 | Single shared connection | One `McpBridge` per process[^h-server] | Fine for one tester. If several users share an Apps deployment, `/api/connect` from one user reconnects everyone. |

## 3. Agent app review

### 3.1 Current state

* Model `databricks-claude-sonnet-5-5`, `instructions="You are a helpful assistant."`, tools `[get_current_time]`, `mcp_servers=[]`. MCP wiring exists only as comments in `invoke_handler` / `stream_handler`[^a-agent].
* `init_mcp_server` points at the legacy managed UC-functions server `/api/2.0/mcp/functions/system/ai`, not fpac[^a-agent].
* `connect_healthy_mcp_servers` already connects and lists tools per server and drops failures, so one bad server does not crash a turn[^a-agent].
* `get_user_workspace_client()` reads `x-forwarded-access-token` for on-behalf-of-user calls[^a-utils]. The deployed app's user scopes are only `iam.access-control:read` and `iam.current-user:read`[^a-get]. I have not verified that this token can call another app, so treat OBO-to-MCP as unproven.
* `start_app.py` starts the Python backend on 8000 and, unless `--no-ui`, clones `databricks/app-templates/e2e-chatbot-app-next` at runtime, then runs `npm install`, `npm run build`, and `npm run start` on `CHAT_APP_PORT=3000`[^a-start][^a-yaml]. So the Apps container can already reach GitHub and the npm registry, unlike serverless notebooks.

### 3.2 Gaps that block any integration

| # | Gap | Fix |
| --- | --- | --- |
| A1 | No fpac MCP server | Add `McpServer(url="https://mcp-fpac-soil-7474654188777746.aws.databricksapps.com/mcp", name="fpac-soil-mcp", workspace_client=WorkspaceClient())` and connect it through `connect_healthy_mcp_servers` in both handlers[^a-custommcp]. |
| A2 | Agent SP `app-2vrjmx agent-fpac-soil-openai-sdk` (ID 70416953425179) lacks `CAN_USE` on `mcp-fpac-soil`. The current ACL lists only team-03, Andrew, and admins[^p-perms]. | Grant `CAN_USE`. The bundle route needs an `app` resource in `databricks.yml` and CLI >= v0.298.0[^a-custommcp]. This app was created from the UI with a git source, so add it as an app resource in the UI or with `apps update-permissions`. |
| A3 | Deployed resources include only `experiment` and no `llm-endpoint`[^a-get] | Add a `serving_endpoint` resource with `CAN_QUERY` for the model in use. Otherwise the SP may not be able to call the model[^a-bundle]. |
| A4 | Generic system prompt | Port `eval/databricks/prompts/system_prompt_v2.txt` from `main` (D12: no steering toward specific tools or resources). |
| A5 | Stateful Streamable HTTP | `app.py` runs `mcp.run(transport="http")` without `stateless_http=True`. Office hours reported "Missing session ID" errors with stateful HTTP. The TS SDK client in the harness handles sessions; confirm `databricks_openai.agents.McpServer` does too, or switch the server to stateless. |

## 4. Integration options

### Option A (recommended): harness as its own Node app, plus an Agent tab

Deploy the harness as a separate app (for example `harness-fpac-soil`) and keep the agent app untouched. Apps installs Node dependencies whenever `package.json` sits at the app root, and with no `command` it runs `npm run start`[^d-deploy].

Changes:

1. **Config (H3, H4, H5):** use `DATABRICKS_APP_PORT` or `PORT` with host `0.0.0.0` when present. Default `MCP_MODE=http` and `MCP_URL` to the `mcp-fpac-soil` `/mcp` URL in `app.yaml`. Copy `prompt_test_cases.json` into the app folder at build time, or set `EVAL_CASES_PATH` to a bundled copy. `allowCommandOverride` already defaults to false on a non-loopback host[^h-config], which is the right default.
2. **Auth (H2):** replace the static token with a provider that requests OAuth M2M tokens from `${DATABRICKS_HOST}/oidc/v1/token` using the injected `DATABRICKS_CLIENT_ID` / `DATABRICKS_CLIENT_SECRET`[^d-env][^d-auth], caches them, and refreshes before expiry. Pass the provider to the transports through a custom `fetch`. Grant the harness app's SP `CAN_USE` on `mcp-fpac-soil`[^d-custommcp].
3. **Agent tab (new):** add a backend route that sends each eval case's `user_prompt` to the agent app's `/invocations` (Responses-format `ResponsesAgentRequest`)[^a-agent][^a-yaml] and shows the tool calls and final text. This is where the two apps actually integrate: the same case can be run deterministically (Tools tab) and through the LLM (Agent tab), side by side. The harness SP also needs `CAN_USE` on the agent app.
4. **Lockfile (H1):** commit `package-lock.json`, scoped to the harness folder (for example a nested `.gitignore` negation).

Tradeoff: one more app to run and pay for. Access stays governed by Apps permissions.

### Option B: harness as a dev-only companion to the agent app

Keep the harness local (laptop) and point it at the deployed `mcp-fpac-soil` over `MCP_MODE=http` with a short-lived OAuth token. Use it only for contract smoke tests before you update the agent. This needs only H2 (a token you refresh by hand) and needs no new deployment. The team has no approved local coding agent for MCP, but this harness is a plain MCP client, not a coding agent. Confirm that policy covers it.

### Not recommended: embedding in the agent app

This would mean adding a root `package.json` (which changes the Apps build path for the whole app[^d-deploy]), a third process in `start_app.py`, a routing layer in front of `AgentServer`, and relative fetch paths in `app.js` (H7). The result is high coupling for little gain.

## 5. Relationship to the existing eval tiers

| Tier (from `RESEARCH_DATABRICKS_EVAL_INTEGRATION.md`) | Harness role |
| --- | --- |
| T0 in-memory contract (`eval/contract`) | Overlaps with the Tools and Eval tabs. T0 is the gate. The harness is for interactive debugging. |
| T1 MLflow in-process agent (`eval/databricks`) | The Agent tab (option A, step 3) would be the interactive view of T1-style runs. |
| T2 deployed app via SP | Option A step 2 is the same SP M2M pattern T2 needs. Build it once and share it. |

To keep scores comparable (H6), either port `keywords_present` to JS, or have the harness show pass/fail only and leave scoring to the Python tiers.

## 6. Suggested order

1. Agent app: A1-A4 (wire MCP, grant `CAN_USE`, add the `llm-endpoint` resource, system prompt v2). Verify a single turn in the chat UI.
2. Harness: rebase on `main` (H8), then H1-H5.
3. Deploy the harness as its own app (option A) and add the Agent tab.
4. Decide whether to port scoring (H6).

## Sources

[^h-readme]: `eval/fpac_soil_mcp_harness/README.md` L3-6, L65-75 (branch `feature/evalHarnessDatabricks01`).
[^h-server]: `eval/fpac_soil_mcp_harness/server.js` L13-14, L35-54, L100-128, L248-260.
[^h-bridge]: `eval/fpac_soil_mcp_harness/lib/mcpBridge.js` L93-106.
[^h-config]: `eval/fpac_soil_mcp_harness/lib/config.js` L56-78.
[^h-eval]: `eval/fpac_soil_mcp_harness/lib/evalCases.js` L139, L150-163, L183-191.
[^h-appjs]: `eval/fpac_soil_mcp_harness/public/app.js` L145-1163 (`api("/api/...")` calls).
[^h-pkg]: `eval/fpac_soil_mcp_harness/package.json`.
[^g-ignore]: `git show 6574461 -- .gitignore`.
[^a-agent]: `apps/agent-fpac-soil-openai-sdk/agent_server/agent.py` L30-33, L43-48, L51-75, L78-129 (`origin/template/agent-fpac-soil-openai-sdk-1792601940628`, `bc9ed3c`).
[^a-utils]: `apps/agent-fpac-soil-openai-sdk/agent_server/utils.py` L35-37.
[^a-start]: `apps/agent-fpac-soil-openai-sdk/scripts/start_app.py` L147-179, L219-272.
[^a-yaml]: `apps/agent-fpac-soil-openai-sdk/app.yaml`.
[^a-bundle]: `apps/agent-fpac-soil-openai-sdk/databricks.yml` L26-40.
[^a-custommcp]: `apps/agent-fpac-soil-openai-sdk/.claude/skills/add-tools/examples/custom-mcp-server.md`.
[^a-get]: `databricks apps get agent-fpac-soil-openai-sdk`, run 2026-10-22.
[^p-perms]: `databricks apps get-permissions mcp-fpac-soil`, run 2026-10-22.
[^d-deploy]: Databricks docs, [Deploy a Databricks app: Deployment logic](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/deploy/); [Manage dependencies for a Databricks app](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/dependencies/).
[^d-env]: Databricks docs, [Databricks Apps environment](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/system-env/).
[^d-auth]: Databricks docs, [Configure authorization in a Databricks app](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/auth/).
[^d-mcpauth]: Databricks docs, [MCP authentication and networking](https://docs.databricks.com/aws/en/agents/mcp-tools/authentication-networking/): "Servers hosted on Databricks Apps require OAuth and do not accept personal access tokens."
[^d-custommcp]: Databricks docs, [Custom MCP servers](https://docs.databricks.com/aws/en/agents/mcp-tools/custom-mcp/): "Callers need CAN USE on the app."
