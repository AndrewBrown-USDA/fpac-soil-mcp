import assert from "node:assert/strict";
import net from "node:net";
import { once } from "node:events";
import { spawn } from "node:child_process";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const harnessDir = fileURLToPath(new URL("..", import.meta.url));
const serverPath = fileURLToPath(new URL("../server.js", import.meta.url));

async function freePort() {
  const probe = net.createServer();
  probe.listen(0, "127.0.0.1");
  await once(probe, "listening");
  const port = probe.address().port;
  await new Promise((resolve, reject) => probe.close((error) => (error ? reject(error) : resolve())));
  return port;
}

async function waitForHttp(url, child) {
  const deadline = Date.now() + 10_000;
  while (Date.now() < deadline) {
    if (child.exitCode !== null) throw new Error(`Harness exited before startup (code ${child.exitCode}).`);
    try {
      const response = await fetch(url);
      return response;
    } catch {
      await new Promise((resolve) => setTimeout(resolve, 50));
    }
  }
  throw new Error(`Harness did not start at ${url}.`);
}

async function stopChild(child) {
  if (child.exitCode !== null) return;
  child.kill("SIGTERM");
  await Promise.race([
    once(child, "exit"),
    new Promise((resolve) => setTimeout(resolve, 2_000)),
  ]);
  if (child.exitCode === null) child.kill("SIGKILL");
}

async function smokeTest(databricks) {
  const port = await freePort();
  const child = spawn(process.execPath, [serverPath], {
    cwd: harnessDir,
    env: {
      ...process.env,
      HARNESS_HOST: databricks ? "0.0.0.0" : "127.0.0.1",
      HARNESS_PORT: databricks ? "1" : String(port),
      DATABRICKS_APP_PORT: databricks ? String(port) : "",
      HARNESS_AUTOCONNECT: "false",
      HARNESS_ALLOW_COMMAND_OVERRIDE: databricks ? "false" : "true",
      MCP_MODE: databricks ? "http" : "stdio",
    },
    stdio: ["ignore", "pipe", "pipe"],
  });
  let output = "";
  child.stdout.on("data", (chunk) => { output += chunk.toString(); });
  child.stderr.on("data", (chunk) => { output += chunk.toString(); });
  child.on("error", (error) => { output += `${error}\n`; });

  try {
    const base = `http://127.0.0.1:${port}`;
    const configResponse = await waitForHttp(`${base}/api/config`, child);
    assert.equal(configResponse.status, 200);
    const config = await configResponse.json();
    assert.equal(config.host, databricks ? "0.0.0.0" : "127.0.0.1");
    assert.equal(config.port, port);
    assert.equal(config.allowCommandOverride, !databricks);
    assert.equal(config.mcp.mode, databricks ? "http" : "stdio");

    const statusResponse = await fetch(`${base}/api/status`);
    assert.equal(statusResponse.status, 200);
    assert.equal((await statusResponse.json()).connected, false);

    const casesResponse = await fetch(`${base}/api/eval-cases`);
    assert.equal(casesResponse.status, 200);
    const cases = await casesResponse.json();
    assert.equal(cases.executable_version, "1.0.0");
    assert.ok(cases.test_cases.some((item) => item.id === "CORR-01"));

    const presetsResponse = await fetch(`${base}/api/presets`);
    assert.equal(presetsResponse.status, 200);
    const presets = await presetsResponse.json();
    assert.ok(presets["tool:analyze_corridor_fppa"]);

    for (const request of [
      fetch(`${base}/api/tools/analyze_corridor_fppa/call`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ arguments: {} }),
      }),
      fetch(`${base}/api/resources/read?uri=fppa%3A%2F%2Fmissing`),
      fetch(`${base}/api/prompts/fppa_screening`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ arguments: {} }),
      }),
    ]) {
      const response = await request;
      assert.equal(response.status, 409);
      const body = await response.json();
      assert.equal(typeof body.error.message, "string");
      assert.match(body.error.message, /Not connected/);
    }

    const evalResponse = await fetch(`${base}/api/eval-cases/CORR-01/run`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({}),
    });
    assert.equal(evalResponse.status, 200);
    const evaluation = await evalResponse.json();
    assert.equal(evaluation.passed, false);
    assert.equal(evaluation.isError, true);
    assert.equal(typeof evaluation.error.message, "string");

    const notFoundResponse = await fetch(`${base}/api/does-not-exist`);
    assert.equal(notFoundResponse.status, 404);
    assert.equal((await notFoundResponse.json()).error.message, "Not found");
  } catch (error) {
    error.message += `\nHarness output:\n${output}`;
    throw error;
  } finally {
    await stopChild(child);
  }
}

test("harness HTTP smoke test with local configuration", () => smokeTest(false));
test("harness HTTP smoke test with Databricks configuration", () => smokeTest(true));
