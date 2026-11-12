// FPAC Soil MCP UI harness - Node.js backend.
//
// Serves the static UI in ./public and exposes a small REST API that bridges the browser to the
// fpac-soil-mcp FastMCP server through the official MCP client SDK (stdio, SSE, or Streamable HTTP).

import path from "node:path";
import express from "express";

import { HARNESS_ROOT, config, defaultUrlFor, publicConfig, splitArgs } from "./lib/config.js";
import { McpBridge } from "./lib/mcpBridge.js";
import { buildPresets, checkKeywords, loadEvalCases } from "./lib/evalCases.js";
import { evaluateResult } from "./lib/evalAssertions.js";

const app = express();
const bridge = new McpBridge();
const history = [];

app.disable("x-powered-by");
app.use(express.json({ limit: "10mb" }));
app.use(express.static(path.join(HARNESS_ROOT, "public")));

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
const asyncRoute = (fn) => (req, res, next) => Promise.resolve(fn(req, res, next)).catch(next);

function record(entry) {
  history.unshift({ id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`, ts: new Date().toISOString(), ...entry });
  if (history.length > config.historyLimit) history.length = config.historyLimit;
}

function errorInfo(err) {
  return { message: String(err?.message || err), code: err?.code ?? null, data: err?.data ?? null };
}

function resolveConnectOptions(body = {}) {
  const mode = String(body.mode || config.mcp.mode).toLowerCase();
  const wantsOverride =
    body.command !== undefined || body.args !== undefined || body.cwd !== undefined || body.env !== undefined;
  if (mode === "stdio" && wantsOverride && !config.allowCommandOverride) {
    throw Object.assign(
      new Error("Command/cwd/env overrides are disabled. Set HARNESS_ALLOW_COMMAND_OVERRIDE=true to enable."),
      { status: 403 },
    );
  }
  return {
    mode,
    command: body.command || config.mcp.command,
    args: body.args !== undefined ? splitArgs(body.args) : config.mcp.args,
    cwd: body.cwd ? path.resolve(body.cwd) : config.mcp.cwd,
    env: body.env && typeof body.env === "object" ? body.env : {},
    url: body.url || config.mcp.url || defaultUrlFor(mode),
    authToken: body.authToken || config.mcp.authToken,
  };
}

function responseText(kind, out) {
  if (kind === "tool") {
    const blocks = (out.result?.content || []).map((c) => c.text || "").join("\n");
    return `${blocks}\n${JSON.stringify(out.result?.structuredContent ?? "")}`;
  }
  if (kind === "resource") return (out.result?.contents || []).map((c) => c.text || "").join("\n");
  return (out.result?.messages || []).map((m) => m.content?.text || JSON.stringify(m.content)).join("\n");
}

async function invoke(inv, timeoutMs) {
  if (inv.kind === "tool") return bridge.callTool(inv.name, inv.arguments || {}, timeoutMs);
  if (inv.kind === "resource") return bridge.readResource(inv.uri, timeoutMs);
  if (inv.kind === "prompt") return bridge.getPrompt(inv.name, inv.arguments || {}, timeoutMs);
  throw Object.assign(new Error(`Unknown invocation kind '${inv.kind}'.`), { status: 400 });
}

// ---------------------------------------------------------------------------
// Connection
// ---------------------------------------------------------------------------
app.get("/api/config", (_req, res) => res.json(publicConfig()));

app.get("/api/status", (_req, res) => res.json(bridge.status()));

app.post(
  "/api/connect",
  asyncRoute(async (req, res) => {
    const opts = resolveConnectOptions(req.body);
    try {
      res.json(await bridge.connect(opts));
    } catch (err) {
      res.status(502).json({ error: errorInfo(err), status: bridge.status() });
    }
  }),
);

app.post(
  "/api/disconnect",
  asyncRoute(async (_req, res) => {
    await bridge.disconnect();
    res.json(bridge.status());
  }),
);

// Proxy the server's HTTP-only /health and /meta routes (network transports only).
app.get(
  "/api/server-routes",
  asyncRoute(async (_req, res) => {
    const conn = bridge.connection;
    const baseUrl = conn?.url || config.mcp.url || defaultUrlFor("sse");
    if (conn && conn.mode === "stdio") {
      return res.json({ available: false, reason: "/health and /meta are only served over SSE/HTTP transports." });
    }
    const origin = new URL(baseUrl).origin;
    const headers = bridge.activeAuthToken ? { Authorization: "Bearer " + bridge.activeAuthToken } : {};
    const out = { available: true, origin };
    for (const route of ["health", "meta"]) {
      try {
        const r = await fetch(`${origin}/${route}`, { headers, signal: AbortSignal.timeout(10000) });
        const text = await r.text();
        let body;
        try {
          body = JSON.parse(text);
        } catch {
          body = text;
        }
        out[route] = { status: r.status, body };
      } catch (err) {
        out[route] = { status: null, error: String(err?.message || err) };
      }
    }
    res.json(out);
  }),
);

// ---------------------------------------------------------------------------
// Tools / resources / prompts
// ---------------------------------------------------------------------------
app.get("/api/tools", asyncRoute(async (_req, res) => res.json({ tools: await bridge.listTools() })));

app.post(
  "/api/tools/:name/call",
  asyncRoute(async (req, res) => {
    const name = req.params.name;
    const args = req.body?.arguments ?? {};
    const timeoutMs = Number(req.body?.timeoutMs) || config.mcp.toolTimeoutMs;
    try {
      const out = await bridge.callTool(name, args, timeoutMs);
      record({ kind: "tool", name, arguments: args, durationMs: out.durationMs, ok: !out.result?.isError });
      res.json(out);
    } catch (err) {
      record({ kind: "tool", name, arguments: args, ok: false, error: errorInfo(err).message });
      res.status(err.status || 502).json({ error: errorInfo(err) });
    }
  }),
);

app.get("/api/resources", asyncRoute(async (_req, res) => res.json(await bridge.listResources())));

app.get(
  "/api/resources/read",
  asyncRoute(async (req, res) => {
    const uri = String(req.query.uri || "");
    if (!uri) return res.status(400).json({ error: { message: "Query parameter 'uri' is required." } });
    try {
      const out = await bridge.readResource(uri);
      record({ kind: "resource", name: uri, durationMs: out.durationMs, ok: true });
      res.json(out);
    } catch (err) {
      record({ kind: "resource", name: uri, ok: false, error: errorInfo(err).message });
      res.status(err.status || 502).json({ error: errorInfo(err) });
    }
  }),
);

app.get("/api/prompts", asyncRoute(async (_req, res) => res.json({ prompts: await bridge.listPrompts() })));

app.post(
  "/api/prompts/:name",
  asyncRoute(async (req, res) => {
    const name = req.params.name;
    const args = req.body?.arguments ?? {};
    try {
      const out = await bridge.getPrompt(name, args);
      record({ kind: "prompt", name, arguments: args, durationMs: out.durationMs, ok: true });
      res.json(out);
    } catch (err) {
      record({ kind: "prompt", name, arguments: args, ok: false, error: errorInfo(err).message });
      res.status(err.status || 502).json({ error: errorInfo(err) });
    }
  }),
);

// ---------------------------------------------------------------------------
// Eval cases & presets
// ---------------------------------------------------------------------------
app.get("/api/eval-cases", (_req, res) => res.json(loadEvalCases(config.evalCasesPath)));

app.get("/api/presets", (_req, res) => res.json(buildPresets(loadEvalCases(config.evalCasesPath).test_cases)));

app.post(
  "/api/eval-cases/:id/run",
  asyncRoute(async (req, res) => {
    const { test_cases: cases } = loadEvalCases(config.evalCasesPath);
    const tc = cases.find((c) => c.id === req.params.id);
    if (!tc) return res.status(404).json({ error: { message: `Unknown eval case '${req.params.id}'.` } });
    // Allow the UI to override the derived arguments for ad-hoc experimentation.
    const invocation = { ...tc.invocation };
    if (req.body?.arguments && invocation.kind !== "resource") invocation.arguments = req.body.arguments;
    const timeoutMs = Number(req.body?.timeoutMs) || config.mcp.toolTimeoutMs;

    const started = Date.now();
    try {
      const out = await invoke(invocation, timeoutMs);
      const isError = invocation.kind === "tool" && Boolean(out.result?.isError);
      const text = responseText(invocation.kind, out);
      const keywords = checkKeywords(tc.expected_keywords, text);
      const assertions = evaluateResult({
        value: out.payload ?? out.result?.structuredContent ?? out.result?.messages,
        responseText: text,
        expectedResult: tc.expected_result,
        predicates: tc.assertions?.predicates || [],
        context: { invocation },
        expectations: tc,
      });
      const passed = !isError && keywords.missing.length === 0 && assertions.status === "pass";
      record({ kind: `eval:${invocation.kind}`, name: tc.id, durationMs: out.durationMs, ok: passed });
      res.json({ id: tc.id, invocation, passed, isError, keywords, assertions, durationMs: out.durationMs, output: out });
    } catch (err) {
      record({ kind: `eval:${invocation.kind}`, name: tc.id, ok: false, error: errorInfo(err).message });
      res.json({
        id: tc.id,
        invocation,
        passed: false,
        isError: true,
        keywords: { found: [], missing: tc.expected_keywords || [] },
        assertions: evaluateResult({
          value: null,
          responseText: "",
          expectedResult: tc.expected_result,
          predicates: tc.assertions?.predicates || [],
          context: { invocation },
          expectations: tc,
        }),
        durationMs: Date.now() - started,
        error: errorInfo(err),
      });
    }
  }),
);

// ---------------------------------------------------------------------------
// History
// ---------------------------------------------------------------------------
app.get("/api/history", (_req, res) => res.json({ history }));
app.delete("/api/history", (_req, res) => {
  history.length = 0;
  res.json({ history });
});

// ---------------------------------------------------------------------------
// Errors & startup
// ---------------------------------------------------------------------------
app.use("/api", (_req, res) => res.status(404).json({ error: { message: "Not found" } }));

// eslint-disable-next-line no-unused-vars
app.use((err, _req, res, _next) => {
  res.status(err.status || 500).json({ error: errorInfo(err) });
});

const server = app.listen(config.port, config.host, async () => {
  console.log(`[harness] UI available at http://${config.host}:${config.port}`);
  console.log(`[harness] MCP mode=${config.mcp.mode} cwd=${config.mcp.cwd}`);
  if (config.autoConnect) {
    try {
      await bridge.connect(resolveConnectOptions({}));
      const tools = await bridge.listTools();
      console.log(`[harness] Connected to fpac-soil-mcp (${tools.length} tools).`);
    } catch (err) {
      console.warn(`[harness] Auto-connect failed: ${err?.message || err}. Use the UI to connect.`);
    }
  }
});

async function shutdown() {
  console.log("\n[harness] Shutting down...");
  await bridge.disconnect();
  server.close(() => process.exit(0));
  setTimeout(() => process.exit(0), 2000).unref();
}
process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);
