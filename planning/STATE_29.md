# Orchestration 29 State

## Baseline checklist

- [x] `git status --short` recorded before Wave 1: clean after planning commit
- [x] `uv run pytest -m "not live_network and not agent_eval" -q`: 303 passed, 14 deselected
- [x] `uv run pytest eval\test_agent_eval.py -m "not agent_eval" -q`: 17 passed, 2 deselected
- [x] `uv run ruff check .`: all checks passed
- [x] `uv run ruff format --check .`: 349 files already formatted
- [x] Existing PR #22 review findings and ADR-0010 scope recorded in `EXECUTION_PLAN_29.md`
- [ ] Pi availability and live/agent-eval prerequisites checked
- [x] Live/agent-eval shared-port and serial-execution constraints recorded

### Baseline results

| Check | Date | Result | Notes |
|---|---|---|---|
| `git status --short` | 2026-10-15 | clean | Baseline taken after planning commit `a7cec87` |
| Offline pytest | 2026-10-15 | 303 passed, 14 deselected | `uv run pytest -m "not live_network and not agent_eval" -q` |
| Eval pytest | 2026-10-15 | 17 passed, 2 deselected | `uv run pytest eval\test_agent_eval.py -m "not agent_eval" -q` |
| Ruff check | 2026-10-15 | passed | `uv run ruff check .` |
| Ruff format | 2026-10-15 | passed | `uv run ruff format --check .` |
| Pi/live prerequisites | pending | pending | Record availability, credentials, network, and port conditions |

## Closure checklist

- [ ] Targeted review-regression tests pass
- [ ] Offline project suite passes
- [ ] Ruff check passes
- [ ] Ruff format check passes
- [ ] `git diff --check` passes
- [ ] Raw artifacts remain outside the repository and no raw fixture is tracked
- [ ] Live/agent-eval validation ran serially and passed, or the exact environmental block is recorded

## Wave board

| Task | Wave | Status | Worker | Notes |
|---|---:|---|---|---|
| 29.1.1 | 1 | done | 29.1.1-retention-contract-execution | Define eval raw-retention exception and update ADR-0010 |
| 29.2.1 | 2 | done | 29.2.1-runner-core | Capture core complete; one existing classification fixture must be updated by 29.3.1 |
| 29.2.2 | 3 | done | 29.2.2-cli-diagnostics | Metadata-only CLI diagnostics; stale classification expectation deferred to 29.3.1 |
| 29.3.1 | 4 | done | 29.3.1-review-regressions | Six review regressions covered; focused eval suite passes |
| 29.4.1 | 5 | pending | — | Document operation and record closure verification |

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
