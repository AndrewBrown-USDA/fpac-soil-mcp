# FPAC Soil MCP UI Harness

A local browser harness (HTML + CSS + vanilla JavaScript front end, Node.js/Express back end) for
exercising the `fpac-soil-mcp` FastMCP server in `src/fpac_soil_mcp`. The Node.js process acts as an
MCP client using the official `@modelcontextprotocol/sdk`, so the server is tested through the same
MCP protocol surface that LLM hosts use.

> Results are preliminary soil inventory screening under 7 CFR Part 657 only. They are not an
> official FPPA determination, LESA score, Form AD-1006, or NRCS-CPA-106 (7 CFR Part 658).

## Layout

```
eval/fpac_soil_mcp_harness/
  package.json          Node dependencies and scripts
  server.js             Express server + REST API bridging the browser to MCP
  lib/config.js         Environment/.env configuration
  lib/mcpBridge.js      MCP client wrapper (stdio, SSE, Streamable HTTP)
  lib/evalCases.js      Maps eval/prompt_test_cases.json to concrete MCP invocations
  public/index.html     UI shell
  public/styles.css     Styles
  public/app.js         UI logic (schema-driven forms, result rendering, SVG geometry preview)
  .env.example          Harness configuration reference
```

## Prerequisites

* Node.js 18.18+ (20 LTS recommended)
* The Python server installed per the repository README (`uv sync` at the repo root)
* Run the workbench locally; it is not a hosted or production deployment

## Run

```powershell
Set-Location eval\fpac_soil_mcp_harness
npm install
npm start
# open http://127.0.0.1:3030
```

By default the harness spawns `uv run fpac-soil-mcp` over stdio from the repository root and
connects automatically. To test a running network server instead:

```powershell
# terminal 1 (repo root)
$env:MCP_TRANSPORT="sse"; uv run fpac-soil-mcp

# terminal 2 (harness)
$env:MCP_MODE="sse"; $env:MCP_URL="http://127.0.0.1:8000/sse"; npm start
```

Use `MCP_MODE=http` with `MCP_URL=http://127.0.0.1:8000/mcp` for Streamable HTTP. The transport can
also be switched from the connection bar in the UI. See `.env.example` for all settings.

For a quick syntax check without starting the server:

```powershell
npm run check
```

## Features

| Tab | What it does |
| --- | --- |
| Tools | Lists all registered tools; builds an argument form from each tool's JSON input schema (GeoJSON/dict fields accept JSON or raw WKT strings); presets from eval cases plus negative/validation inputs; JSON editing mode; renders summary fields, regulatory notice, limitations, tables of map units / county segments, an SVG preview of input and returned geometries, and raw `CallToolResult` JSON. Ctrl+Enter runs the tool. |
| Resources | Lists and reads `fppa://` resources (and templates, if any). |
| Prompts | Renders MCP prompts with their arguments and shows the resulting messages. |
| Eval Cases | Loads `eval/prompt_test_cases.json`, derives a direct MCP invocation for each case, runs one or all cases, and checks the response for `expected_keywords`. "Open" loads a case into the Tools/Prompts/Resources tab for editing. Results can be downloaded as JSON. |
| History | Server-side log of recent calls, durations, and errors. |
| Server | Connection status, server capabilities and instructions, stderr tail (stdio), and `/health` + `/meta` checks (SSE/HTTP only). |

## Deterministic evaluation

The eval tab is deterministic: there is no LLM in the loop, so `expected_tools` is satisfied by
construction and only keyword coverage and tool errors are scored. Arguments come from, in order:

1. `harness_arguments` on the test case (optional field you can add to the JSON),
2. per-case overrides in `lib/evalCases.js` (`CASE_ARGUMENTS`) for parameters that only appear in prose
   (mukeys, buffer distances, alternatives, site-assessment inputs, prompt arguments),
3. generic derivation from `sample_geometry` by tool name.

Use `eval/run_evals.py` / `eval/test_agent_eval.py` for agent tool-selection behaviour.
Those Python evaluations and the T0/T1 contract and Databricks evaluation paths are separate
from this browser workbench. This harness does not provide model-based scoring, production
readiness, or a Databricks App deployment; those are separate forthcoming work.

## REST API (used by the UI)

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/config` | Non-secret harness configuration |
| GET | `/api/status` | MCP connection status |
| POST | `/api/connect` | Connect (`mode`, `command`, `args`, `cwd`, `url`, `authToken`) |
| POST | `/api/disconnect` | Disconnect |
| GET | `/api/tools` | `tools/list` |
| POST | `/api/tools/:name/call` | `tools/call` with `{ arguments, timeoutMs }` |
| GET | `/api/resources` | `resources/list` + templates |
| GET | `/api/resources/read?uri=` | `resources/read` |
| GET | `/api/prompts` | `prompts/list` |
| POST | `/api/prompts/:name` | `prompts/get` with `{ arguments }` |
| GET | `/api/eval-cases` | Eval cases with derived invocations |
| POST | `/api/eval-cases/:id/run` | Run one case and score keywords |
| GET | `/api/presets` | Argument presets per tool/prompt |
| GET | `/api/server-routes` | Proxy `/health` and `/meta` (network transports) |
| GET/DELETE | `/api/history` | Call history |

## Notes

* Live tool calls contact USDA SDA, Census TIGERweb, and (if configured) NASS QuickStats; corridor
  and LESA analyses can take a minute or more. Adjust the per-call timeout in the UI or with
  `MCP_TOOL_TIMEOUT_MS`.
* The harness binds to `127.0.0.1` by default. Command/cwd overrides from the browser are disabled
  automatically when bound to a non-loopback host unless `HARNESS_ALLOW_COMMAND_OVERRIDE=true`.
  These overrides are local-development controls and require an explicit security design before
  any shared deployment.
* The harness does not modify the server; it only uses its public MCP surface.
* Harness output is preliminary soil inventory screening only. It is not an official FPPA
  determination, LESA score, Form AD-1006, or NRCS-CPA-106.
* `node_modules/` and `.env` should not be committed.
