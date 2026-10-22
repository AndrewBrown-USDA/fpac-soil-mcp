// Thin wrapper around the official MCP TypeScript SDK client.
// Supports stdio (spawns the Python server), legacy SSE, and Streamable HTTP.

import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import { SSEClientTransport } from "@modelcontextprotocol/sdk/client/sse.js";
import { StreamableHTTPClientTransport } from "@modelcontextprotocol/sdk/client/streamableHttp.js";

const STDERR_LIMIT = 500;

function cleanEnv(obj) {
  const out = {};
  for (const [k, v] of Object.entries(obj || {})) {
    if (v !== undefined && v !== null) out[k] = String(v);
  }
  return out;
}

/** Parse the JSON payload of an MCP tool result (structuredContent first, then text blocks). */
export function extractPayload(result) {
  if (!result) return null;
  if (result.structuredContent !== undefined && result.structuredContent !== null) {
    return result.structuredContent;
  }
  const texts = (result.content || []).filter((c) => c.type === "text").map((c) => c.text);
  if (texts.length === 0) return null;
  const parsed = texts.map((t) => {
    try {
      return JSON.parse(t);
    } catch {
      return t;
    }
  });
  return parsed.length === 1 ? parsed[0] : parsed;
}

export class McpBridge {
  constructor({ clientName = "fpac-soil-mcp-harness", clientVersion = "0.1.0" } = {}) {
    this.clientName = clientName;
    this.clientVersion = clientVersion;
    this.client = null;
    this.transport = null;
    this.connection = null;
    this.activeAuthToken = "";
    this.connectedAt = null;
    this.lastError = null;
    this.stderr = [];
  }

  get connected() {
    return this.client !== null;
  }

  _pushStderr(text) {
    for (const line of String(text).split(/\r?\n/)) {
      if (!line.trim()) continue;
      this.stderr.push({ ts: new Date().toISOString(), line });
    }
    if (this.stderr.length > STDERR_LIMIT) this.stderr.splice(0, this.stderr.length - STDERR_LIMIT);
  }

  status() {
    return {
      connected: this.connected,
      connectedAt: this.connectedAt,
      connection: this.connection,
      lastError: this.lastError,
      serverVersion: this.client?.getServerVersion?.() ?? null,
      serverCapabilities: this.client?.getServerCapabilities?.() ?? null,
      instructions: this.client?.getInstructions?.() ?? null,
      stderrTail: this.stderr.slice(-100),
    };
  }

  /**
   * Connect to the MCP server.
   * @param {{mode:string, command?:string, args?:string[], cwd?:string, env?:object, url?:string, authToken?:string}} opts
   */
  async connect(opts) {
    await this.disconnect();
    const mode = (opts.mode || "stdio").toLowerCase();
    let transport;

    if (mode === "stdio") {
      transport = new StdioClientTransport({
        command: opts.command,
        args: opts.args || [],
        cwd: opts.cwd,
        env: cleanEnv({ ...process.env, ...(opts.env || {}), MCP_TRANSPORT: "stdio" }),
        stderr: "pipe",
      });
      const stream = transport.stderr;
      if (stream) stream.on("data", (chunk) => this._pushStderr(chunk.toString()));
    } else if (mode === "sse" || mode === "http") {
      if (!opts.url) throw new Error(`A server URL is required for '${mode}' mode.`);
      const headers = opts.authToken ? { Authorization: "Bearer " + opts.authToken } : {};
      const url = new URL(opts.url);
      transport =
        mode === "sse"
          ? new SSEClientTransport(url, {
              requestInit: { headers },
              eventSourceInit: {
                fetch: (input, init) =>
                  fetch(input, { ...init, headers: { ...(init?.headers || {}), ...headers } }),
              },
            })
          : new StreamableHTTPClientTransport(url, { requestInit: { headers } });
    } else {
      throw new Error(`Unsupported mode '${mode}'. Use stdio, sse, or http.`);
    }

    const client = new Client({ name: this.clientName, version: this.clientVersion });
    client.onerror = (err) => {
      this.lastError = String(err?.message || err);
    };
    client.onclose = () => {
      if (this.client === client) {
        this.client = null;
        this.transport = null;
        this._pushStderr("[harness] MCP connection closed.");
      }
    };

    try {
      await client.connect(transport);
    } catch (err) {
      this.lastError = String(err?.message || err);
      try {
        await transport.close();
      } catch {
        /* ignore */
      }
      throw err;
    }

    this.client = client;
    this.transport = transport;
    this.activeAuthToken = opts.authToken || "";
    this.lastError = null;
    this.connectedAt = new Date().toISOString();
    this.connection = {
      mode,
      command: mode === "stdio" ? opts.command : undefined,
      args: mode === "stdio" ? opts.args : undefined,
      cwd: mode === "stdio" ? opts.cwd : undefined,
      url: mode !== "stdio" ? opts.url : undefined,
    };
    this._pushStderr(`[harness] Connected via ${mode}.`);
    return this.status();
  }

  async disconnect() {
    const client = this.client;
    this.client = null;
    this.transport = null;
    this.connection = null;
    this.activeAuthToken = "";
    this.connectedAt = null;
    if (client) {
      try {
        await client.close();
      } catch {
        /* ignore */
      }
    }
  }

  _require() {
    if (!this.client) throw Object.assign(new Error("Not connected to an MCP server."), { status: 409 });
    return this.client;
  }

  async listTools() {
    const res = await this._require().listTools();
    return res.tools || [];
  }

  async callTool(name, args = {}, timeoutMs = 180000) {
    const client = this._require();
    const started = Date.now();
    const result = await client.callTool({ name, arguments: args }, undefined, {
      timeout: timeoutMs,
      resetTimeoutOnProgress: true,
    });
    return { durationMs: Date.now() - started, result, payload: extractPayload(result) };
  }

  async listResources() {
    const client = this._require();
    const resources = (await client.listResources()).resources || [];
    let templates = [];
    try {
      templates = (await client.listResourceTemplates()).resourceTemplates || [];
    } catch {
      templates = [];
    }
    return { resources, templates };
  }

  async readResource(uri, timeoutMs = 180000) {
    const client = this._require();
    const started = Date.now();
    const result = await client.readResource({ uri }, { timeout: timeoutMs, resetTimeoutOnProgress: true });
    const contents = (result.contents || []).map((c) => {
      let parsed;
      if (typeof c.text === "string") {
        try {
          parsed = JSON.parse(c.text);
        } catch {
          parsed = undefined;
        }
      }
      return { ...c, parsed };
    });
    return { durationMs: Date.now() - started, result: { ...result, contents } };
  }

  async listPrompts() {
    const res = await this._require().listPrompts();
    return res.prompts || [];
  }

  async getPrompt(name, args = {}, timeoutMs = 180000) {
    const client = this._require();
    // MCP prompt arguments are string-valued; drop empty values so server defaults apply.
    const stringArgs = {};
    for (const [k, v] of Object.entries(args || {})) {
      if (v === undefined || v === null || v === "") continue;
      stringArgs[k] = typeof v === "string" ? v : JSON.stringify(v);
    }
    const started = Date.now();
    const result = await client.getPrompt(
      { name, arguments: stringArgs },
      { timeout: timeoutMs, resetTimeoutOnProgress: true },
    );
    return { durationMs: Date.now() - started, result };
  }
}
