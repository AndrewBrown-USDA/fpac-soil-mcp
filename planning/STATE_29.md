# Orchestration 29 State

## Baseline checklist

- [x] `git status --short` recorded before Wave 1: clean after planning commit
- [x] `uv run pytest -m "not live_network and not agent_eval" -q`: 303 passed, 14 deselected
- [x] `uv run pytest eval\test_agent_eval.py -m "not agent_eval" -q`: 17 passed, 2 deselected
- [x] `uv run ruff check .`: all checks passed
- [x] `uv run ruff format --check .`: 349 files already formatted
- [x] Existing PR #22 review findings and ADR-0010 scope recorded in `EXECUTION_PLAN_29.md`
- [x] Pi availability and live/agent-eval prerequisites checked: Pi found at `C:\Users\Andrew.G.Brown\AppData\Roaming\npm\pi.ps1`
- [x] Live/agent-eval shared-port and serial-execution constraints recorded

### Baseline results

| Check | Date | Result | Notes |
|---|---|---|---|
| `git status --short` | 2026-10-15 | clean | Baseline taken after planning commit `a7cec87` |
| Offline pytest | 2026-10-15 | 303 passed, 14 deselected | `uv run pytest -m "not live_network and not agent_eval" -q` |
| Eval pytest | 2026-10-15 | 17 passed, 2 deselected | `uv run pytest eval\test_agent_eval.py -m "not agent_eval" -q` |
| Ruff check | 2026-10-15 | passed | `uv run ruff check .` |
| Ruff format | 2026-10-15 | passed | `uv run ruff format --check .` |
| Pi/live prerequisites | 2026-10-15 | attempted; 1 passed, 1 failed, 324 deselected | `uv run pytest -m agent_eval -q`; failure: `test_pi_point_screening_evaluation` raised `KeyError: 'latitude'` while reading structured target-call arguments |

## Closure checklist

- [x] Targeted review-regression tests pass
- [x] Offline project suite passes
- [x] Ruff check passes
- [x] Ruff format check passes
- [x] `git diff --check` passes
- [x] Raw artifacts remain outside the repository and no raw fixture is tracked
- [x] Live/agent-eval validation ran serially and passed after Wave 6 added verified `mcpScript` envelope handling

## Wave 6 scope

- The prior live diagnostic captured a real Pi `mcpScript` wrapper: nested tool calls are represented in `args.code`, `details.calls[].path`, and result `structuredContent`, not as direct soil-tool call arguments.
- Raw diagnostic output was deleted after inspection. Wave 6 must add only sanitized fixture evidence and must rerun the live gate with any new raw output kept outside the repository.

## Wave board

| Task | Wave | Status | Worker | Notes |
|---|---:|---|---|---|
| 29.1.1 | 1 | done | 29.1.1-retention-contract-execution | Define eval raw-retention exception and update ADR-0010 |
| 29.2.1 | 2 | done | 29.2.1-runner-core | Capture core complete; one existing classification fixture must be updated by 29.3.1 |
| 29.2.2 | 3 | done | 29.2.2-cli-diagnostics | Metadata-only CLI diagnostics; stale classification expectation deferred to 29.3.1 |
| 29.3.1 | 4 | done | 29.3.1-review-regressions | Six review regressions covered; focused eval suite passes |
| 29.4.1 | 5 | done | 29.4.1-documentation-closure | README operation documented; closure execution remains orchestrator-owned |
| 29.6.1 | 6 | done | 29.6.1-pi-envelope | Verified `mcpScript` nested-MCP envelope handled; live gate passes |

## Task reports

<!-- Worker reports are appended below, one section per task, <=15 lines. -->

### 29.1.1 — Defining the eval retention exception

- Status: complete.
- Changed only `docs\decisions\0010-public-payload-pii-detection-and-sanitization.md`,
  `planning\CAPTURE_CONTRACT_29.md`, this TODO, and this state file.
- Documented explicit opt-in raw retention, external repository-independent
  roots, safe identifiers, operator warnings/protection/cleanup, sanitized
  fixtures, and prohibited repository-local raw artifacts.
- Preserved public/production `privacy.py`, Section 1619, and payload
  sanitization requirements; bounded-copy truncation is distinct from complete
  evaluation evidence.
- Command: `rg -n "eval|raw|opt-in|external|repository|production|fixture|sanitize|retention" docs\decisions\0010-public-payload-pii-detection-and-sanitization.md planning\CAPTURE_CONTRACT_29.md`
- Result: passed; all required anchors and boundaries were present.
- Deviations: none. No runtime code or tests changed.
- Dependent-task gotchas: 29.2.x must enforce the documented external-root,
  identifier-safety, opt-in, and complete-evidence/bounded-copy boundaries;
  raw artifacts remain outside the repository.

## 29.2.1

- Status: complete; implementation verified, one stale expectation deferred to 29.3.1.
- Changed `eval\run_evals.py`: safe identifiers, complete evidence parsing,
  bounded-copy truncation metadata, structured invocation classification, and
  terminal artifact finalization for normal, retry, timeout, and startup paths.
- Raw opt-in artifacts remain repository-external; bounded sanitized copies are
  retained alongside exact raw streams for local interrogation.
- Command: `uv run pytest eval\test_agent_eval.py -m "not agent_eval" -q`
- Result: 17 passed, 2 deselected.
- Deviations: none.
- Gotchas: CLI artifact diagnostics remain deferred to 29.2.2; tests/fixtures
  were not modified.

### 29.2.1 verification retry

- Removed the bare event-type fallback from `_has_dedicated_invocation()`;
  explicit direct/nested containers and message tool-call/content blocks remain.
- Command: `uv run pytest eval\test_agent_eval.py -m "not agent_eval" -q`
- Result: 16 passed, 1 failed, 2 deselected.
- The sole failure is the existing `dedicated_unrecognized.jsonl` regression,
  which expects bare `tool_execution` types to count; tests remain out of scope.

## 29.2.2

- Status: implementation complete; focused verification has one pre-existing failure.
- Changed `eval\run_evals.py` lines 790-805: per-case attempt outcomes,
  metadata paths, artifact paths, and capture errors are now printed as
  metadata-only diagnostics.
- Raw stdout, stderr, and event contents are not added to diagnostics;
  aggregate summary and exit behavior remain unchanged.
- Command: `uv run pytest eval\test_agent_eval.py -m "not agent_eval" -q`
- Result: 16 passed, 1 failed, 2 deselected.
- Failure is the existing `dedicated_unrecognized.jsonl` expectation that bare
  `tool_execution` event types count; capture core and tests were not changed.
- Deviations: none. Dependent task 29.3.1 should retain the named regression.

## 29.3.1

- Status: complete.
- Changed `eval\test_agent_eval.py` and this worker TODO/state report only; no
  production code or raw artifacts were added.
- Added regressions for special identifiers, external exact raw opt-in
  retention, late evidence beyond bounded copies, invocation classification,
  failed-attempt finalization, retry paths, CLI diagnostics, and fixture
  sanitization.
- Updated the stale bare `tool_execution` fixture expectation to `absent`;
  dedicated synthetic nested-container cases cover `present_unrecognized` and
  `recognized`.
- Command: `uv run pytest eval\test_agent_eval.py -m "not agent_eval" -q`
- Result: 26 passed, 2 deselected.
- `git diff --check`: passed. Deviations: none.
- Gotcha: existing checked-in fixtures remain historical/sanitized; synthetic
  events are used only for explicitly tested structural boundaries.

## 29.4.1

- Status: complete.
- Changed only `README.md`, this task TODO, and this state report; no runtime
  code, tests, ADR-0010, or raw artifacts were changed.
- Documented opt-in capture flags and `EVAL_CAPTURE_*` equivalents, the required
  repository-external root, metadata-first interrogation, bounded sanitized
  copies versus complete `raw-*` evidence, and sanitized path identifiers.
- Documented local-sensitive handling, access protection, caller-controlled
  cleanup, checked-in fixture rules, and the boundary from production privacy
  behavior and FPPA scope.
- Checks recorded from prior completed work: targeted eval tests 26 passed,
  2 deselected; offline suite 303 passed, 14 deselected; Ruff check passed;
  Ruff format check passed.
- Command run for this task: `git diff --check`; result: passed.
- Raw-artifact tracking check: passed; no raw artifact was added. Live/agent-eval
  execution was not run; orchestrator owns and must record that result.
- Deviations: none. Gotcha: README documents raw files as sensitive local
  debugging output even though bounded review files remain sanitized.

## 29.6.1

- Status: complete; added narrow verified Pi `mcpScript` envelope extraction.
- Changed `eval\run_evals.py`, `eval\test_agent_eval.py`, and sanitized
  `eval\fixtures\event_capture\mcp_script_sanitized.jsonl`.
- Nested names come from `args.code` `tools.call(...)` and `details.calls[].path`;
  numeric object-literal coordinates are extracted for test evidence.
- Direct calls, prose exclusion, discovery handling, and existing classifications
  remain covered; no raw diagnostics or `.development\` files were added.
- Focused eval tests: `28 passed, 2 deselected`.
- Ruff check/format and `git diff --check`: passed.
- Serial agent gate: `uv run pytest -m agent_eval -q`: `2 passed, 326 deselected`.
- Deviations: none; live POINT-01 passed with no repository-retained raw output.
