// Harness configuration: environment variables with sensible defaults.
// An optional `.env` file in the harness directory is loaded (no extra dependency).

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export const HARNESS_ROOT = path.resolve(__dirname, "..");
export const EVAL_ROOT = path.resolve(HARNESS_ROOT, "..");
export const REPO_ROOT = path.resolve(EVAL_ROOT, "..");

function loadDotEnv(file) {
  if (!fs.existsSync(file)) return;
  const lines = fs.readFileSync(file, "utf-8").split(/\r?\n/);
  for (const raw of lines) {
    const line = raw.trim();
    if (!line || line.startsWith("#")) continue;
    const eq = line.indexOf("=");
    if (eq === -1) continue;
    const key = line.slice(0, eq).trim();
    let value = line.slice(eq + 1).trim();
    if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
      value = value.slice(1, -1);
    }
    if (process.env[key] === undefined) process.env[key] = value;
  }
}

loadDotEnv(path.join(HARNESS_ROOT, ".env"));

const env = process.env;

function bool(value, fallback) {
  if (value === undefined || value === "") return fallback;
  return ["1", "true", "yes", "on"].includes(String(value).toLowerCase());
}

function int(value, fallback) {
  const n = Number.parseInt(value, 10);
  return Number.isFinite(n) ? n : fallback;
}

export function resolveEvalCasesPath(value = env.EVAL_CASES_PATH) {
  return path.resolve(HARNESS_ROOT, value || path.join(EVAL_ROOT, "eval_cases.v1.json"));
}

/** Split a shell-like argument string, honouring simple single/double quotes. */
export function splitArgs(value) {
  if (Array.isArray(value)) return value.map(String);
  if (!value) return [];
  const out = [];
  const re = /"([^"]*)"|'([^']*)'|(\S+)/g;
  let m;
  while ((m = re.exec(String(value))) !== null) out.push(m[1] ?? m[2] ?? m[3]);
  return out;
}

const host = env.HARNESS_HOST || "127.0.0.1";
const isLoopback = ["127.0.0.1", "localhost", "::1"].includes(host);

export const config = {
  host,
  port: int(env.DATABRICKS_APP_PORT || env.HARNESS_PORT, 3030),
  autoConnect: bool(env.HARNESS_AUTOCONNECT, true),
  // Allow the browser to change the spawned command / cwd / env. Defaults to
  // enabled only when bound to loopback, because it permits process execution.
  allowCommandOverride: bool(env.HARNESS_ALLOW_COMMAND_OVERRIDE, isLoopback),
  // Relative paths are resolved against the harness directory.
  evalCasesPath: resolveEvalCasesPath(),
  historyLimit: int(env.HARNESS_HISTORY_LIMIT, 200),
  mcp: {
    mode: (env.MCP_MODE || "stdio").toLowerCase(), // stdio | sse | http
    command: env.MCP_COMMAND || "uv",
    args: splitArgs(env.MCP_ARGS || "run fpac-soil-mcp"),
    cwd: path.resolve(HARNESS_ROOT, env.MCP_CWD || REPO_ROOT),
    url: env.MCP_URL || "",
    authToken: env.MCP_AUTH_TOKEN || "",
    toolTimeoutMs: int(env.MCP_TOOL_TIMEOUT_MS, 180000),
  },
};

export function defaultUrlFor(mode) {
  if (mode === "sse") return "http://127.0.0.1:8000/sse";
  if (mode === "http") return "http://127.0.0.1:8000/mcp";
  return "";
}

/** Config safe to expose to the browser (no secrets). */
export function publicConfig() {
  return {
    host: config.host,
    port: config.port,
    allowCommandOverride: config.allowCommandOverride,
    evalCasesPath: config.evalCasesPath,
    repoRoot: REPO_ROOT,
    mcp: {
      mode: config.mcp.mode,
      command: config.mcp.command,
      args: config.mcp.args,
      cwd: config.mcp.cwd,
      url: config.mcp.url || defaultUrlFor(config.mcp.mode),
      authTokenConfigured: Boolean(config.mcp.authToken),
      toolTimeoutMs: config.mcp.toolTimeoutMs,
    },
  };
}
