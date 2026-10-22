# AGENTS.md - FPAC Soil MCP UI Harness

## Quick Start

```powershell
# From the repository root
Set-Location eval\fpac_soil_mcp_harness

# Install Node.js dependencies
npm install

# Start the browser harness
npm start

# Start with Node.js watch mode
npm run dev

# Check JavaScript syntax
npm run check
```

Open `http://127.0.0.1:3030` after starting the harness. The default configuration starts `uv run fpac-soil-mcp` from the repository root over stdio.

To connect to an existing network server:

```powershell
$env:MCP_MODE="sse"
$env:MCP_URL="http://127.0.0.1:8000/sse"
npm start
```

Use `MCP_MODE=http` and an `/mcp` URL for Streamable HTTP. The package currently exposes `start`, `dev`, and `check` scripts.

## Find Things

- `server.js` - Express server, static-file host, REST API, MCP lifecycle, history, and startup/shutdown.
- `lib\config.js` - environment loading, paths, host/port, transport configuration, and public configuration.
- `lib\mcpBridge.js` - official MCP SDK client wrapper for stdio, SSE, and Streamable HTTP.
- `lib\evalCases.js` - deterministic mapping from `..\prompt_test_cases.json` to tool, resource, and prompt invocations.
- `public\index.html` - browser UI shell.
- `public\app.js` - UI behavior, schema-driven forms, MCP calls, evaluation, and result rendering.
- `public\styles.css` - browser harness styling.
- `.env.example` - local configuration reference.
- `..\prompt_test_cases.json` - shared evaluation cases.
- `README.md` - harness usage, REST API, transports, and evaluation behavior.
- `..\..\src\fpac_soil_mcp\` - Python MCP server exercised by this harness.

## Workflows

### Change Backend or MCP Connectivity

1. Update `server.js`, `lib\config.js`, or `lib\mcpBridge.js`.
2. Preserve the REST API documented in `README.md` unless the change is intentional.
3. Run `npm run check`.
4. Start the harness and verify the affected connection or endpoint.
5. Update `README.md` when routes, transports, configuration, or prerequisites change.

### Change Evaluation Cases

1. Update `..\prompt_test_cases.json` for shared prompt/input coverage.
2. Update `lib\evalCases.js` for explicit arguments, derivation, or presets.
3. Keep deterministic mappings explicit; this harness does not use an LLM to select tools.
4. Run `npm run check`.
5. Run the affected case from the Eval Cases tab and verify expected coverage.

### Change the Browser UI

1. Update `public\index.html`, `public\app.js`, or `public\styles.css`.
2. Run `npm run check` when JavaScript changes.
3. Start the harness and verify the affected tab, form, result, or connection flow.
4. Keep the UI compatible with the REST endpoints in `server.js`.

### Validate Against the Python Server

From the repository root:

```powershell
uv run pytest -m "not live_network"
uv run ruff check .
uv run ruff format --check .
```

Use the harness for MCP-surface checks when changing tools, resources, prompts, transports, or response rendering.

## Infrastructure

- Runtime: Node.js `>=18.18`; Node.js 20 LTS is recommended.
- Package type: ES modules.
- Dependencies: `express` and `@modelcontextprotocol/sdk`.
- Default bind address: `127.0.0.1`.
- Default browser port: `3030`.
- Default MCP mode: `stdio`.
- Default MCP command: `uv`.
- Default MCP arguments: `run fpac-soil-mcp`.
- Default MCP working directory: repository root.
- Default evaluation file: `..\prompt_test_cases.json`.
- Default per-call timeout: 180000 milliseconds.
- Supported MCP modes: `stdio`, `sse`, and `http`.
- `/health` and `/meta` are available through the harness only for SSE/HTTP connections.
- Command, working-directory, and environment overrides are local-development controls; do not expose them on shared deployments without explicit security design.
- Live calls may contact USDA SDA, Census TIGERweb, and USDA NASS QuickStats.
- Do not commit `node_modules\`, `.env`, credentials, or generated artifacts.
- The harness is a client/workbench and does not produce an official FPPA determination, LESA score, Form AD-1006, or NRCS-CPA-106.

## References

- `README.md` - complete harness usage, feature overview, REST API, transport configuration, and evaluation mapping.
- `.env.example` - environment variable reference.
- `..\prompt_test_cases.json` - shared evaluation cases.
- `..\run_evals.py` - Python evaluation runner.
- `..\test_agent_eval.py` - Python evaluation tests.
- `..\..\AGENTS.md` - repository-wide architecture and commands.
- `..\..\README.md` - overall server architecture, MCP interface, and FPPA scope.
- `https://github.com/modelcontextprotocol/typescript-sdk` - MCP TypeScript SDK.
