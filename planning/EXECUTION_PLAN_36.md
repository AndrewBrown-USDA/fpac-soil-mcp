# EXECUTION PLAN 36: Integrate the Local JavaScript MCP Workbench

## Goal & Scope

**Goal:** Integrate PR #30's JavaScript UI as a documented, deterministic, local-only MCP workbench with layered contract checks, targeted tests, and CI coverage, after reconciling the rebased branch with the latest `main` evaluation architecture.

**In scope:**

- Correct the current harness runtime defects, including malformed auth-header syntax, active-token propagation, timeout handling, integer validation, and clipboard fallback.
- Centralize executable deterministic evaluation cases in a versioned fixture while preserving `eval/prompt_test_cases.json` for prompt/agent evaluation.
- Add JSON Schema-backed structural assertions and allowlisted domain-predicate hooks.
- Add offline Node tests and a fixture-based local smoke test.
- Document the harness scope, deterministic limitations, startup path, and relationship to existing Python/Databricks evaluation.
- Add runtime/static metadata parity coverage and Node CI integration.

**Out of scope:**

- Databricks App deployment, authentication, ingress, secrets, HTTPS, observability, rate/concurrency controls, and production hardening. These belong in the directly following PR.
- Model-based agent evaluation, LLM providers, trajectory scoring, or replacement of the existing Python/Databricks evaluation path.
- Keyboard/ARIA accessibility polish; schedule as a separate follow-up PR.
- Live USDA/Census/NASS calls as required merge gates.
- ADR creation; distill decisions after this orchestration's implementation results.

**Verbatim constraints from decisions:**

- Initial boundary is local-only; hosted deployment is a separate PR.
- Wave 1 evaluation is deterministic only.
- Pass criteria are layered: JSON Schema plus named FPPA/domain predicates.
- Keep `prompt_test_cases.json` for natural-language prompt and agent-evaluation inputs; centralize executable deterministic cases in `eval/eval_cases.v1.json`.
- Node and Python retain runtime-specific adapters over shared declarative contracts.
- The first representative case is a regulatory-sensitive polygon/corridor case using mocked upstream fixtures and invariant assertions.
- Use dependency-ordered waves with a thin vertical slice.
- Current PR includes correctness fixes; accessibility polish is deferred.
- Merge requires offline deterministic tests and a local fixture-based smoke test.

## Reconnaissance Log

- PR #30 head: `657446104947f7b95633e3fee6a2901d66dc0a9c`.
- Initial harness commit: `6023abe1817f470845f63b95dff7cc0273283b89`.
- Existing orchestration conventions were taken from `planning/EXECUTION_PLAN_26.md`, `PROMPT_TEMPLATE_26.md`, and `STATE_26.md`; no plan-35 artifacts are present in this checkout.
- Primary harness files are under `eval/fpac_soil_mcp_harness/`.
- Existing MCP runtime registration and tests are in `src/fpac_soil_mcp/app.py` and `tests/test_server.py`.
- Existing prompt-oriented fixtures are in `eval/prompt_test_cases.json` and are consumed by Python agent-evaluation code; the rebased `eval/` tree must remain authoritative for those consumers.
- The current harness has no dedicated JavaScript test suite.
- Current research report: `planning/RESEARCH_FEATURE_EVAL_HARNESS_DATABRICKS.md`.
- Pre-existing unrelated/untracked files must remain untouched: `TODO.md` and the research report.

## Decision Log

1. **2026-10-22 — Product boundary:** deliver the local-only deterministic workbench now; Databricks App hosting follows in a separate PR.
2. **2026-10-22 — Evaluation semantics:** deterministic MCP contract checks only; defer model-based evaluation.
3. **2026-10-22 — Assertions:** layered JSON Schema plus allowlisted named domain predicates.
4. **2026-10-22 — Fixture structure:** retain `prompt_test_cases.json`; add a versioned executable fixture.
5. **2026-10-22 — Ownership:** evaluation maintainers own technical cases; regulatory assertions require domain-owner approval.
6. **2026-10-22 — Runtime architecture:** Node and Python use runtime-specific adapters over shared declarative contracts.
7. **2026-10-22 — Vertical slice:** use a mocked regulatory-sensitive polygon/corridor fixture with invariant assertions.
8. **2026-10-22 — Sequencing:** use dependency-ordered waves and a thin vertical slice.
9. **2026-10-22 — Current PR fixes:** include correctness fixes; defer keyboard/ARIA work.
10. **2026-10-22 — Merge gate:** require offline tests plus a local fixture-based smoke test.
11. **2026-10-22 — Fixture boundary:** centralize executable deterministic cases in `eval/eval_cases.v1.json`; do not replace prompt/agent fixtures or unrelated Python benchmark/mocked-service fixtures.
12. **2026-10-22 — Rebase gate:** reconcile the rebased branch with latest `main` and run the existing evaluation baseline before changing implementation or fixture semantics.

## Wave & Dependency Table

| Wave | Task | Title | Files in scope | Depends on |
|---|---|---|---|---|
| 1 | 36.1.1 | Correct harness connection and evaluation runtime defects | `eval/fpac_soil_mcp_harness/server.js`, `eval/fpac_soil_mcp_harness/lib/mcpBridge.js`, `eval/fpac_soil_mcp_harness/lib/config.js` | none |
| 1 | 36.1.2 | Correct browser input and clipboard behavior | `eval/fpac_soil_mcp_harness/public/app.js` | none |
| 1 | 36.1.3 | Document local deterministic harness scope | `README.md`, `QUICKSTART.md`, `eval/fpac_soil_mcp_harness/README.md` | none |
| 1 | 36.1.4 | Capture post-rebase evaluation baseline | `planning/STATE_36.md` | none |
| 2 | 36.2.1 | Centralize executable fixture and assertion contracts | `eval/eval_cases.v1.json`, `eval/fpac_soil_mcp_harness/lib/evalAssertions.js`, `eval/fpac_soil_mcp_harness/lib/evalCases.js` | 36.1.1, 36.1.4 |
| 2 | 36.2.2 | Add mocked Node harness contract tests | `eval/fpac_soil_mcp_harness/test/harness.test.js`, `eval/fpac_soil_mcp_harness/package.json` | 36.1.1, 36.1.2 |
| 2 | 36.2.3 | Extend runtime and published metadata parity | `tests/test_server.py`, `manifest.yaml`, `server.json` | 36.1.4 |
| 3 | 36.3.1 | Add local fixture-based smoke test | `eval/fpac_soil_mcp_harness/test/smoke.test.js`, `eval/fpac_soil_mcp_harness/package.json` | 36.2.1, 36.2.2 |
| 3 | 36.3.2 | Add Node checks to CI | `.github/workflows/ci.yml` | 36.2.2, 36.3.1 |
| 4 | 36.4.1 | Run serial integration verification and record gate | `planning/STATE_36.md` | 36.3.2 |

## Task Specifications

### 36.1.1 — Correct harness connection and evaluation runtime defects

**Repository:** `D:\workspace\fpac-soil-mcp`

**Files in scope**

- Must edit: `eval/fpac_soil_mcp_harness/server.js`, `eval/fpac_soil_mcp_harness/lib/mcpBridge.js`, `eval/fpac_soil_mcp_harness/lib/config.js`
- Can create: none
- Temp/scratch: `.development/` only, if needed

**Depends on:** none.

**Specification:** Make the current local harness parse and run. Fix malformed Authorization header construction, preserve the active connection's auth token for server-route checks, forward configured timeout behavior consistently to tool/resource/prompt evaluation calls, and preserve the local-only command-override boundary. Errors must remain explicit.

**Constraints:** Do not add hosted deployment behavior, arbitrary code execution beyond the existing local override model, or unrelated refactors.

**Grep anchors:** `resolveConnectOptions`, `/api/server-routes`, `invoke`, `McpBridge.connect`, `callTool`, `readResource`, `getPrompt`, `allowCommandOverride`.

**Reference implementations:** Existing `config.js` environment parsing; existing Python route/auth tests in `tests/test_server.py`.

**Acceptance:** `node --check server.js lib/config.js lib/mcpBridge.js`; targeted unit/API tests in 36.2.2 pass; active-token, timeout, and non-loopback override behavior are mechanically covered.

### 36.1.2 — Correct browser input and clipboard behavior

**Repository:** `D:\workspace\fpac-soil-mcp`

**Files in scope**

- Must edit: `eval/fpac_soil_mcp_harness/public/app.js`
- Can create: none
- Temp/scratch: `.development/` only, if needed

**Depends on:** none.

**Specification:** Reject fractional values for integer schemas and make clipboard copying safe when the Clipboard API or secure context is unavailable. Preserve existing UI behavior and do not implement deferred keyboard/ARIA work.

**Constraints:** No redesign of the UI and no accessibility scope expansion.

**Grep anchors:** clipboard helper near `copyText`; schema argument parsing near `parseArguments`; tool/resource/prompt rendering anchors are explicitly out of scope.

**Reference implementations:** Existing schema parsing and result error display in `public/app.js`.

**Acceptance:** targeted browser/helper tests or a deterministic Node-executable helper test cover integer rejection and unavailable clipboard behavior; `node --check public/app.js` passes.

### 36.1.3 — Document local deterministic harness scope

**Repository:** `D:\workspace\fpac-soil-mcp`

**Files in scope**

- Must edit: `README.md`, `QUICKSTART.md`, `eval/fpac_soil_mcp_harness/README.md`
- Can create: none
- Temp/scratch: none

**Depends on:** none.

**Specification:** Link the harness from root documentation and describe startup, supported transports, local-only security assumptions, deterministic contract-check semantics, limitations versus Python/Databricks agent evaluation, and the separate forthcoming Databricks App PR.

**Constraints:** Do not claim production readiness, model-based evaluation, or official FPPA determination behavior.

**Grep anchors:** root transport/development sections; QUICKSTART evaluation commands; harness README prerequisites, features, and evaluation sections.

**Reference implementations:** Existing regulatory notices and evaluation documentation.

**Acceptance:** all commands and paths match `package.json`/`config.js`; documentation explicitly states the current PR's out-of-scope deployment and model-evaluation work.

### 36.1.4 — Capture post-rebase evaluation baseline

**Repository:** `D:\workspace\fpac-soil-mcp`

**Files in scope**

- Must edit: `planning/STATE_36.md`
- Can create: none
- Temp/scratch: `.development/` only, if needed

**Depends on:** none.

**Specification:** Verify the rebased branch against the latest `main` evaluation architecture before implementation. Record exact baseline commands, pass/fail/deselected counts, current fixture consumers, and any reconciliation needed by later tasks. Confirm that Python agent-evaluation consumers remain pointed at `eval/prompt_test_cases.json`.

**Constraints:** This is a read/verification gate; do not alter implementation, fixtures, or docs. Live network and model/agent gates remain opt-in unless already required by repository policy.

**Grep anchors:** `eval/run_evals.py` fixture loading, `eval/test_agent_eval.py` fixture loading, recent `eval/` Databricks runner/scorer tests, and existing Makefile test targets.

**Reference implementations:** `planning/STATE_26.md` baseline format and current `main` evaluation tests.

**Acceptance:** STATE_36 records a green or explicitly blocked post-rebase baseline and names every required compatibility adjustment before Wave 2.

### 36.2.1 — Centralize executable fixture and assertion contracts

**Repository:** `D:\workspace\fpac-soil-mcp`

**Files in scope**

- Must create: `eval/eval_cases.v1.json`, `eval/fpac_soil_mcp_harness/lib/evalAssertions.js`
- Must edit: `eval/fpac_soil_mcp_harness/lib/evalCases.js`
- Temp/scratch: `.development/` only, if needed

**Depends on:** 36.1.1.

**Specification:** Centralize executable deterministic evaluation cases in a versioned `eval/eval_cases.v1.json`. Keep `prompt_test_cases.json` unchanged as the prompt/agent-evaluation corpus. Move duplicated executable arguments from `evalCases.js` into the centralized fixture where appropriate, while preserving explicit legacy compatibility during migration. Include one mocked polygon/corridor case with invocation data, expected result shape, layered assertions, ownership metadata, and protected regulatory assertion markers. Implement JSON Schema-compatible structural checks plus an allowlisted named-predicate interface.

**Constraints:** No arbitrary executable expressions in fixture JSON; no model calls; no live upstream dependency.

**Grep anchors:** `loadEvalCases`, `CASE_ARGUMENTS`, `TOOL_DERIVERS`, `checkKeywords`, invocation construction.

**Reference implementations:** Existing `evalCases.js` mapping and Python fixture consumers in `eval/run_evals.py` and `eval/test_agent_eval.py`.

**Acceptance:** fixture parses and validates; one representative case can classify transport/MCP/schema/predicate/pass outcomes; existing Python prompt/agent fixture consumers remain compatible; all migrated executable arguments have a single authoritative source.

### 36.2.2 — Add mocked Node harness contract tests

**Repository:** `D:\workspace\fpac-soil-mcp`

**Files in scope**

- Must create: `eval/fpac_soil_mcp_harness/test/harness.test.js`
- Must edit: `eval/fpac_soil_mcp_harness/package.json`
- Temp/scratch: `.development/` only, if needed

**Depends on:** 36.1.1, 36.1.2.

**Specification:** Add an offline Node test command and mocked tests for bridge payload extraction, discovery, active auth-token propagation, timeout forwarding, command override rejection, evaluation failure classification, integer parsing, and clipboard fallback seams.

**Constraints:** Do not call USDA/Census/NASS; do not require a running Databricks service; keep tests deterministic and targeted.

**Grep anchors:** package scripts; `McpBridge`; Express route registration; `invoke`; browser helper seams.

**Reference implementations:** Existing Python mocked tests in `tests/` and deterministic evaluation tests in `eval/test_agent_eval.py`.

**Acceptance:** `npm test` and `npm run check` pass from the harness directory; tests report named cases for the required correctness boundaries.

### 36.2.3 — Extend runtime and published metadata parity

**Repository:** `D:\workspace\fpac-soil-mcp`

**Files in scope**

- Must edit: `tests/test_server.py`, `manifest.yaml`, `server.json`
- Can create: none
- Temp/scratch: none

**Depends on:** none.

**Specification:** Extend existing tests so published resources/prompts and runtime discovery remain aligned, correct stale tool-count wording, and preserve the ten-tool/three-resource/four-prompt public surface. Do not add a UI-specific registry.

**Constraints:** Keep metadata synchronized with actual runtime registration and existing regulatory language.

**Grep anchors:** `test_manifest_and_server_json_match_tools`, runtime list tests, manifest resource/prompt sections, server metadata.

**Reference implementations:** Existing `tests/test_server.py` tool parity and runtime discovery tests.

**Acceptance:** targeted `uv run pytest tests\test_server.py` passes; manifest/server/runtime names and descriptions are checked for the supported public surface.

### 36.3.1 — Add local fixture-based smoke test

**Repository:** `D:\workspace\fpac-soil-mcp`

**Files in scope**

- Must create: `eval/fpac_soil_mcp_harness/test/smoke.test.js`
- Must edit: `eval/fpac_soil_mcp_harness/package.json`
- Temp/scratch: `.development/` only, if needed

**Depends on:** 36.2.1, 36.2.2.

**Specification:** Start the harness with auto-connect disabled or a fixture MCP peer and verify startup, config/status discovery, one deterministic tool/resource/prompt path, and structured error handling without external services.

**Constraints:** No live USDA/Census/NASS calls; clean up child processes; avoid port collisions.

**Grep anchors:** server startup/shutdown, `/api/config`, `/api/status`, `/api/eval-cases`, `/api/presets`.

**Reference implementations:** Existing harness startup and route definitions; Python fixture-based tests.

**Acceptance:** smoke test passes locally and through the package test command; child process exits cleanly.

### 36.3.2 — Add Node checks to CI

**Repository:** `D:\workspace\fpac-soil-mcp`

**Files in scope**

- Must edit: `.github/workflows/ci.yml`
- Can create: none
- Temp/scratch: none

**Depends on:** 36.2.2, 36.3.1.

**Specification:** Add a pinned Node job or step that installs harness dependencies reproducibly, runs syntax/tests/smoke checks, and does not make external federal APIs a required gate.

**Constraints:** Preserve existing Python matrix and live-test policy; do not add Databricks deployment.

**Grep anchors:** workflow matrix/setup, `make all`, `make test-live`.

**Reference implementations:** Existing Python setup in `.github/workflows/ci.yml`; Node engine requirement in harness `package.json`.

**Acceptance:** workflow YAML is valid and includes Node setup plus harness checks; existing Python jobs remain intact.

### 36.4.1 — Run serial integration verification and record gate

**Repository:** `D:\workspace\fpac-soil-mcp`

**Files in scope**

- Must edit: `planning/STATE_36.md`
- Can create: none
- Temp/scratch: none

**Depends on:** 36.3.2.

**Specification:** Orchestrator-only verification task. Run the documented offline Python suite, Ruff checks, harness syntax/tests/smoke, and any conditional live gates separately. Record exact commands, counts, deviations, and final wave status.

**Constraints:** Do not modify implementation files; preserve serial full-suite verification.

**Acceptance:** state records green baseline comparison, all required gates, any opt-in gates, and no unresolved merge-blocking failure.
