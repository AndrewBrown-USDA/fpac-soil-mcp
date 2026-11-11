import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { test } from "node:test";
import { extractPayload, McpBridge } from "../lib/mcpBridge.js";
import { buildInvocation, checkKeywords } from "../lib/evalCases.js";
import { evaluateResult } from "../lib/evalAssertions.js";

test("extractPayload prefers structured content", () => {
  assert.deepEqual(extractPayload({ structuredContent: { ok: true }, content: [] }), { ok: true });
});

test("extractPayload parses JSON and preserves plain text blocks", () => {
  assert.deepEqual(extractPayload({ content: [{ type: "text", text: "{\"value\": 3}" }] }), { value: 3 });
  assert.deepEqual(extractPayload({ content: [{ type: "text", text: "not json" }] }), "not json");
  assert.equal(extractPayload({ content: [] }), null);
});

test("bridge discovery delegates to the MCP client", async () => {
  const bridge = new McpBridge();
  const calls = [];
  bridge.client = {
    listTools: async () => {
      calls.push("tools");
      return { tools: [{ name: "tool" }] };
    },
    listResources: async () => ({ resources: [{ uri: "fppa://resource" }] }),
    listResourceTemplates: async () => ({ resourceTemplates: [] }),
    listPrompts: async () => ({ prompts: [{ name: "prompt" }] }),
  };
  assert.deepEqual(await bridge.listTools(), [{ name: "tool" }]);
  assert.deepEqual(await bridge.listResources(), { resources: [{ uri: "fppa://resource" }], templates: [] });
  assert.deepEqual(await bridge.listPrompts(), [{ name: "prompt" }]);
  assert.deepEqual(calls, ["tools"]);
});

test("bridge forwards timeout options for tool, resource, and prompt calls", async () => {
  const bridge = new McpBridge();
  bridge.client = {
    async callTool(_request, _resultSchema, options) {
      assert.deepEqual(options, { timeout: 321, resetTimeoutOnProgress: true });
      return { content: [{ type: "text", text: "{\"ok\":true}" }] };
    },
    async readResource(_request, options) {
      assert.deepEqual(options, { timeout: 654, resetTimeoutOnProgress: true });
      return { contents: [] };
    },
    async getPrompt(_request, options) {
      assert.deepEqual(options, { timeout: 987, resetTimeoutOnProgress: true });
      return { messages: [] };
    },
  };
  await bridge.callTool("tool", {}, 321);
  await bridge.readResource("fppa://resource", 654);
  await bridge.getPrompt("prompt", { empty: "", value: 4 }, 987);
});

test("active auth token is retained privately and cleared on disconnect", async () => {
  const bridge = new McpBridge();
  bridge.client = { close: async () => {} };
  bridge.connection = { mode: "http", url: "http://127.0.0.1:8000/mcp" };
  bridge.activeAuthToken = "secret-token";
  assert.equal(bridge.status().connection.url, "http://127.0.0.1:8000/mcp");
  assert.equal(bridge.status().activeAuthToken, undefined);
  await bridge.disconnect();
  assert.equal(bridge.activeAuthToken, "");
});

test("invocation construction and keyword failures remain deterministic", () => {
  const tc = { id: "CASE", target_type: "tool", target_name: "tool", harness_arguments: { value: 1 } };
  assert.deepEqual(buildInvocation(tc), { kind: "tool", name: "tool", arguments: { value: 1 } });
  assert.deepEqual(checkKeywords(["required", "missing"], "required output"), {
    found: ["required"],
    missing: ["missing"],
  });
});

test("evaluation predicates enforce prompt safety, incomplete-score, and selected-property contracts", () => {
  const prompt = evaluateResult({
    value: null,
    responseText: "Do not select or recommend a site, footprint, alignment, or alternative.",
    predicates: ["noSitingRecommendation"],
    context: { invocation: { kind: "prompt" } },
  });
  assert.equal(prompt.status, "pass");

  const incomplete = evaluateResult({
    value: {
      site_assessment: { evaluation_status: "incomplete" },
      threshold_status: "not_evaluated",
      total_lesa_score: null,
      mandatory_alternatives_required: null,
    },
    predicates: ["noFabricatedScore"],
  });
  assert.equal(incomplete.status, "pass");
  assert.equal(evaluateResult({
    value: {
      site_assessment: { evaluation_status: "incomplete" },
      threshold_status: "evaluated",
      total_lesa_score: 190,
      mandatory_alternatives_required: true,
    },
    predicates: ["noFabricatedScore"],
  }).status, "predicate");

  const selectedProperty = evaluateResult({
    value: { manifest: { productivity_index: "csr2" } },
    predicates: ["preservesSelectedProperty"],
    context: { invocation: { arguments: { productivity_index: "CSR2" } } },
  });
  assert.equal(selectedProperty.status, "pass");
});

test("SA-MA-02 names the expected project and project type in its request and invocation", async () => {
  const source = await readFile(new URL("../../eval_cases.v1.json", import.meta.url), "utf8");
  const testCase = JSON.parse(source).test_cases.find((item) => item.id === "SA-MA-02");
  assert.match(testCase.user_prompt, /project Synthetic SA-MA-02/);
  assert.match(testCase.user_prompt, /project_type site/);
  assert.equal(testCase.invocation.arguments.project_name, "Synthetic SA-MA-02");
  assert.equal(testCase.invocation.arguments.project_type, "site");
});

test("browser helper source contains integer rejection and clipboard fallback seams", async () => {
  const source = await readFile(new URL("../public/app.js", import.meta.url), "utf8");
  assert.match(source, /kind === "integer" && !Number\.isInteger\(n\)/);
  assert.match(source, /copyTextFallback\(text\)/);
  assert.match(source, /document\.execCommand\("copy"\)/);
});

test("server source preserves command override rejection and evaluation error classification", async () => {
  const source = await readFile(new URL("../server.js", import.meta.url), "utf8");
  assert.match(source, /Command\/cwd\/env overrides are disabled/);
  assert.match(source, /Authorization: "Bearer " \+ bridge\.activeAuthToken/);
  assert.match(source, /fetch\(`\$\{origin\}\/\$\{route\}`, \{ headers, signal:/);
  assert.match(source, /invoke\(invocation, timeoutMs\)/);
  assert.match(source, /passed = !isError && keywords\.missing\.length === 0 && assertions\.status === "pass"/);
  assert.match(source, /assertions, durationMs: out\.durationMs/);
});
