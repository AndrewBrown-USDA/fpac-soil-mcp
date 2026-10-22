# Orchestration 36 State

## Baseline

- **Repository:** `D:\workspace\fpac-soil-mcp`
- **Baseline source:** rebased and cleaned branch after reconciliation with latest `main`; preserve unrelated changes.
- **Required baseline commands:** `uv run pytest -m "not live_network"`, `uv run ruff check .`, `uv run ruff format --check .`, harness `node --check` commands.
- **Conditional gates:** `uv run pytest -m live_network` and model/agent evaluations remain opt-in.
- **Worker policy:** maximum two concurrent workers; targeted tests only; full verification serially at wave end.
- **Known pre-existing/unrelated files:** `TODO.md`, `planning/RESEARCH_FEATURE_EVAL_HARNESS_DATABRICKS.md`.
- **Baseline capture:** required in task 36.1.4 before implementation; record exact counts and post-rebase compatibility findings here.

## Wave board

| Wave | Task | Status |
|---|---|---|
| 1 | 36.1.1 | done |
| 1 | 36.1.2 | done |
| 1 | 36.1.3 | done |
| 1 | 36.1.4 | done |
| 2 | 36.2.1 | done |
| 2 | 36.2.2 | done |
| 2 | 36.2.3 | done |
| 3 | 36.3.1 | done |
| 3 | 36.3.2 | done |
| 4 | 36.4.1 | done |

## Task reports

<!-- Append one concise report under each task heading. Include status, changed files/line ranges, exact validation commands and counts, deviations, and dependent-task gotchas. -->

## 36.1.1

- **Status:** complete
- **Changes:** Corrected both network auth headers to use explicit `Bearer` plus the active token; retained the active token in the private `McpBridge.activeAuthToken` field (not public status/connection state); forwarded evaluation timeouts through tool/resource/prompt paths.
- **Validation:** Re-ran `node --check server.js`, `node --check lib\config.js`, and `node --check lib\mcpBridge.js` — all passed (exit code 0).
- **Scope:** `eval\fpac_soil_mcp_harness\server.js`, `lib\mcpBridge.js`, `lib\config.js`; no unrelated implementation files changed.
- **Deviations:** None.
- **Gotchas:** Runtime/API coverage for active-token, timeout, and override behavior remains assigned to task 36.2.2.

## 36.1.2

- **Status:** complete
- **Changes:** Added integer validation and clipboard fallback in `eval/fpac_soil_mcp_harness/public/app.js`.
- **Validation:** `Set-Location eval\fpac_soil_mcp_harness; node --check public\app.js` — exit code 0.
- **Scope:** Browser input and clipboard behavior only; no rendering or accessibility changes.
- **Deviations:** Initial root-relative syntax command failed because it resolved `public\app.js` from the repository root; corrected by changing to the harness directory.
- **Gotchas:** Clipboard API rejection falls back to a temporary textarea; fallback cleanup is guaranteed.

## 36.1.3

- **Status:** complete
- **Changes:** Documented local browser harness startup, transports, local security boundary,
  deterministic evaluation semantics, Python/Databricks evaluation distinction, and FPPA limits.
- **Files:** `README.md`, `QUICKSTART.md`, `eval\fpac_soil_mcp_harness\README.md`.
- **Validation:** Commands and paths checked against `package.json`, `.env.example`, and nested AGENTS guidance.
- **Deviations:** Updated this state record as explicitly requested after documentation approval.
- **Gotchas:** Harness remains local-only; Databricks App hosting and model-based evaluation are separate work.

## 36.1.4

- **Status:** complete
- **Changes:** Captured the post-rebase offline evaluation baseline and compatibility findings. The branch is
  `feature/evalHarnessDatabricks01` at `52e51d3` (`docs(planning): JS harness alignment`).
- **Validation:** `uv run pytest -m "not live_network and not agent_eval"` — exit 0;
  470 passed, 3 skipped, 24 deselected, 104 warnings (494 collected). `uv run ruff check .`
  — exit 0 (`All checks passed!`). `uv run ruff format --check .` — exit 0
  (`436 files already formatted`). From `eval\fpac_soil_mcp_harness`, all four
  `node --check` commands for `server.js`, `lib\config.js`, `lib\mcpBridge.js`, and
  `public\app.js` passed with exit 0.
- **Scope:** Read-only verification and this state record only. The worktree already contained
  unrelated/pre-existing changes in the harness, documentation, planning artifacts, and this
  state file; no implementation, fixture, or documentation files were changed by this task.
- **Compatibility findings:** `eval\run_evals.py` loads `eval\prompt_test_cases.json`;
  `eval\test_agent_eval.py` loads the same file for `prompt_dataset`; and
  `eval\common\dataset.py` uses it as the shared default dataset for Databricks evaluation.
  Databricks runner/scorer tests consume records and expectations derived from that shared
  dataset. The Makefile keeps offline tests separate from live (`test`), Pi (`test-eval`),
  and Databricks (`eval-databricks`) gates. Later fixture work must preserve
  `eval\prompt_test_cases.json` as the authoritative Python prompt/agent dataset and add
  executable deterministic cases without replacing it.
- **Deviations:** No baseline command failures. Live-network and model/agent gates were not run,
  as required by the task and repository policy. The offline marker expression still selected
  unmarked evaluation tests; this is reflected in the exact counts above.
- **Gotchas:** Existing branch changes include modified files beyond this task's scope; preserve
  them during later waves. Harness runtime/API behavior remains covered by dependent task 36.2.2.

## 36.2.1

- **Status:** complete
- **Changes:** Added declarative `eval\eval_cases.v1.json` with a representative corridor case, layered result metadata, ownership, and protected regulatory markers. Added JSON Schema-compatible structural checks and an allowlisted named-predicate interface in `eval\fpac_soil_mcp_harness\lib\evalAssertions.js`. Updated `lib\evalCases.js` to merge centralized executable cases while preserving legacy prompt-fixture compatibility.
- **Validation:** From `eval\fpac_soil_mcp_harness`, `node --check lib\evalCases.js` and `node --check lib\evalAssertions.js` passed. Targeted fixture merge check passed (`fixture merge: PASS 20 tool`). Targeted layered assertion check passed (`layered assertions: PASS pass`).
- **Scope:** Only the approved fixture, assertion module, eval case loader, task todo, and this STATE report changed. `eval\prompt_test_cases.json` and Python consumers were preserved.
- **Deviations:** None.
- **Gotchas:** Centralized fixture cases are merged by case ID when loading the legacy prompt fixture; legacy `CASE_ARGUMENTS`, derivation, presets, and keyword checks remain available for unmigrated cases.

## 36.2.2

- **Status:** complete
- **Changes:** Added `eval\fpac_soil_mcp_harness\test\harness.test.js` with eight deterministic Node tests covering payload extraction, mocked discovery, timeout forwarding, private active-token lifecycle, invocation/keyword classification, integer-validation and clipboard source seams, and command-override/evaluation classification guards. Added the `npm test` script to `eval\fpac_soil_mcp_harness\package.json`.
- **Validation:** From `eval\fpac_soil_mcp_harness`, `npm test` passed: 8 tests passed, 0 failed, 0 skipped. `npm run check` passed with exit code 0. Initial `npm test` was blocked by missing installed dependencies; `npm install --no-audit --no-fund` resolved the environment dependency issue before rerunning validation.
- **Scope:** Only the task test, package script, this task TODO, and this state report were changed. Tests use local mocks/source assertions only; no USDA/Census/NASS/Databricks or live harness service was contacted.
- **Deviations:** Because `server.js` and `public\app.js` are not importable test modules and implementation edits were prohibited, route/browser seams are covered with deterministic source guards rather than invasive runtime instrumentation.
- **Gotchas:** `node_modules\` was installed locally to satisfy the existing package dependencies and remains an ignored development artifact; no lockfile or package dependency manifest changes were made.

## 36.2.3

- **Status:** complete
- **Changes:** Extended `tests\test_server.py` to assert the exact ten-tool, three-resource, and four-prompt runtime surface; added runtime tool-description parity against `server.json`; added published resource/prompt metadata shape and count checks. Synchronized all published tool descriptions in `manifest.yaml` and `server.json` with runtime registration descriptions. Existing regulatory language and the no-UI-registry boundary were preserved.
- **Validation:** `uv run pytest tests\test_server.py -q` — exit 0; 18 passed, 3 deselected. `uv run ruff check tests\test_server.py` — exit 0 (`All checks passed!`). `uv run ruff format --check tests\test_server.py` — exit 0 (`1 file already formatted`). JSON validation of `server.json` — exit 0 (`server.json: valid JSON`).
- **Scope:** Changed only `tests\test_server.py`, `manifest.yaml`, `server.json`, `planning\tasks\36.2.3.todo.md`, and this STATE report. Existing unrelated worktree changes were preserved.
- **Deviations:** None. Per instructions, only targeted tests and focused checks were run; no live-network or full-suite gates were run.
- **Gotchas:** Runtime and published metadata now intentionally share the registered tool descriptions. Resource and prompt runtime checks enforce exact counts/names; manifest checks enforce published entries are present and non-empty.

## 36.3.1

- **Status:** complete
- **Changes:** Added `eval\fpac_soil_mcp_harness\test\smoke.test.js` covering isolated loopback startup, disabled auto-connect, config/status discovery, versioned eval-case and preset loading, deterministic disconnected tool/resource/prompt/eval paths, structured JSON errors, and child-process cleanup. Updated the harness `test` script to run both contract and smoke tests. Updated the task TODO.
- **Validation:** From `eval\fpac_soil_mcp_harness`, `npm test` passed: 9 tests passed, 0 failed, 0 skipped. `npm run check` passed with exit code 0; all configured `node --check` commands succeeded.
- **Scope:** Only `eval\fpac_soil_mcp_harness\test\smoke.test.js`, `eval\fpac_soil_mcp_harness\package.json`, `planning\tasks\36.3.1.todo.md`, and this report changed.
- **Deviations:** No external services or MCP peer were started. The smoke test verifies the tool/resource/prompt route seams in a structured disconnected state and the deterministic eval error path; a successful fixture-peer invocation would require additional implementation/test infrastructure outside the approved file scope.
- **Gotchas:** The test allocates a free loopback port and disables auto-connect, so it does not exercise live MCP calls or USDA/Census/NASS dependencies.

## 36.3.2

- **Status:** complete
- **Changes:** Added an independent `harness` job to `.github\workflows\ci.yml`
  using `actions/setup-node@v4` with Node `20.19.5`, npm cache keyed to the
  harness lockfile, reproducible `npm ci`, `npm run check`, and `npm test`.
  The existing Python matrix and `make test-live` step remain unchanged.
- **Validation:** `npm ci` — exit 0; `npm run check` — exit 0; `npm test` —
  9 passed, 0 failed, 0 skipped. YAML structure validation with
  `python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"`
  — exit 0. Workflow structure inspection confirmed both `test` and `harness`
  jobs, pinned Node setup, lockfile cache path, `npm ci`, syntax checks, and
  contract/smoke tests.
- **Scope:** `.github\workflows\ci.yml`,
  `planning\tasks\36.3.2.todo.md`, and this STATE report only.
- **Deviations:** None.
- **Gotchas:** The harness checks remain offline; no USDA, Census, NASS,
  Databricks, deployment, credentials, or hosted-service gates were added.

## 36.4.1

- **Status:** complete
- **Changes:** Ran the final serial offline integration gate and recorded the release decision.
- **Validation:** `uv run pytest -m "not live_network"` — 474 passed, 3 skipped, 22 deselected, 104 warnings; `uv run ruff check .` — passed; `uv run ruff format --check .` — 436 files formatted; harness `npm run check` — passed; harness `npm test` — 9 passed, 0 failed, 0 skipped.
- **Scope:** Orchestrator verification and this STATE report only; no implementation files changed by this task.
- **Deviations:** Live-network and model/agent gates remained opt-in and were not run.
- **Gotchas:** Existing deprecation warnings are non-blocking; unrelated pre-existing worktree changes remain preserved.
