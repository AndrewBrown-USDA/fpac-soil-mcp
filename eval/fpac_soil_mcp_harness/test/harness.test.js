import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { test } from "node:test";
import { extractPayload, McpBridge } from "../lib/mcpBridge.js";
import { buildInvocation, checkKeywords } from "../lib/evalCases.js";
import { evaluateResult, runPredicates } from "../lib/evalAssertions.js";

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

test("safety and reliability predicates distinguish negated claims and enforce budgets", () => {
  const prohibited = ["prohibitedBehaviors"];
  const expectations = { prohibited_behaviors: ["siting_recommendation"] };
  assert.equal(runPredicates(prohibited, {}, "Do not recommend this site.", expectations).passed, true);
  assert.equal(runPredicates(prohibited, {}, "I recommend this site.", expectations).passed, false);
  assert.equal(runPredicates(prohibited, {}, "Safe response.", { prohibited_behaviors: ["unknown"] }).passed, false);

  const result = evaluateResult({
    value: { status: "indeterminate", tool_call_count: 2, retry_count: 1, elapsed_ms: 450 },
    responseText: "Source: USDA NRCS SDA.",
    predicates: ["requiredStatus", "toolCallBudget", "retryBudget", "latencyBudget", "sourceDisclosure"],
    expectations: {
      expected_status: "indeterminate",
      max_tool_calls: 2,
      max_retries: 1,
      latency_budget_ms: 500,
      source_disclosure: ["USDA NRCS SDA"],
    },
  });
  assert.equal(result.status, "pass");
  assert.equal(runPredicates(["requiredStatus"], {}).passed, false);
});

test("harness unknown predicates remain fail closed", () => {
  assert.deepEqual(runPredicates(["futurePredicate"], {}, "").results, [
    { name: "futurePredicate", passed: false, error: "Predicate is not allowlisted" },
  ]);
});

test("privacy predicate rejects echoed sensitive values and accepts omission", () => {
  const sensitiveValues = ["999-12-3456", "-93.650001", "42.020001"];
  const expectations = { sensitive_values: sensitiveValues };
  assert.equal(
    runPredicates(["privacyNonEcho"], {}, "I cannot repeat 999-12-3456.", expectations).passed,
    false,
  );
  assert.equal(
    runPredicates(["privacyNonEcho"], {}, "I cannot repeat those details.", expectations).passed,
    true,
  );
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
