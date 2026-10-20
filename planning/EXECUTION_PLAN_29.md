# Execution Plan 29 — Resolve PR #22 Review Findings

## Goal & Scope

### Goal

Resolve all six open code-review findings on PR `#22` (`feat(eval): retain opt-in Pi eval event capture artifacts`) while preserving the harness's purpose: retain enough exact Pi output for evaluation debugging and complete model-behavior interrogation. Raw artifacts are a supported, explicitly opt-in local eval feature, must remain outside the repository, and must not change production/public-payload privacy behavior. The implementation must also make path construction safe, avoid truncating evaluation evidence, classify actual invocations correctly, finalize failed attempts, and surface artifact diagnostics.

### In scope

- Fix special-identifier path traversal in `eval\run_evals.py`.
- Support opt-in raw local artifact retention for exact Pi evaluation interrogation, with explicit warnings and repository-external enforcement.
- Preserve complete evaluation evidence independent of bounded artifact copies; add truncation indicators only to retained copies where limits apply.
- Correct invocation detection so discovery/listing events do not count as calls and nested dedicated call containers are recognized.
- Finalize retained artifacts and metadata for timeout and startup-failure attempts.
- Print artifact paths and capture errors in CLI diagnostics without changing the aggregate table.
- Add regression coverage for all six review findings and raw-artifact boundaries.
- Update ADR-0010 to document the eval-harness raw-retention exception while preserving its public/production sanitization rule.
- Keep live/agent-eval validation explicit and serial; require it for closure per the user decision.

### Out of scope

- Authentication or authorization for the local evaluation harness.
- Production server logging, tracing, HTTP retry instrumentation, or a general event bus.
- Changes to `src\fpac_soil_mcp\privacy.py` behavior for public MCP payloads.
- Changes to MCP tools, soil clients, regulatory logic, or live service behavior.
- Making raw artifacts part of checked-in fixtures or repository history.
- Building a complete provider-specific schema/allowlist for every Pi event envelope.

### Verbatim constraints

- “fix_all”
- “raw_supported”
- “these data sit uncontrolled in my pi session info or temp directories”
- “we just need to be able to interrogate them to verify exactly what the model is doing”
- “For the artifacts we do actually include in the repo they will be ‘sanitized’”
- “the genral intent was to make this system robust to support filtering out potentially sensitive parameters and location info etc.”
- “include_live”

## Recon log

- PR `#22` has six open review threads: special identifiers permit traversal; retained payloads are unsanitized; capture limits truncate evaluation evidence; invocation detection misclassifies discovery/nested calls; failed attempts are not finalized; CLI diagnostics omit artifact paths/errors.
- Primary implementation surface is `eval\run_evals.py` (724 lines); use anchors around `_safe_id`, `_capture_attempt`, `extract_structured_tool_names`, `run_case`, and `main`.
- Primary shared test surface is `eval\test_agent_eval.py` (617+ lines); same-file work must be serial.
- Existing tests report the current behavior: 15 eval tests plus 2 deselected in the last orchestration, with timeout/startup retention gaps explicitly recorded in `planning\STATE_28.md`.
- Default project baseline from orchestration 28: 294 passed, 14 deselected; Ruff check passed; format check reported 340 files formatted. Reconfirm before Wave 1.
- Eval uses isolated stdio by default. Live/agent-eval runs require Pi and external services and must be serial; HTTP/SSE defaults to shared port `127.0.0.1:8000`.
- Accepted ADR-0010 centralizes public-payload privacy. This plan updates its scope to distinguish public/production payload handling from explicitly opt-in local eval artifact retention. ADR-0011 continues to require mocked/offline default tests.
- Reference implementation: current capture/retry plumbing in `eval\run_evals.py`; current mocked capture tests and fixtures in `eval\test_agent_eval.py` and `eval\fixtures\event_capture\`.

## Decision log

| Date | Decision |
|---|---|
| 2026-10-15 | Fix all six PR #22 findings; none are deferred as “intentional.” |
| 2026-10-15 | Raw local artifacts are a supported opt-in eval feature because exact model-behavior interrogation is required. They remain repository-external and are never checked in. |
| 2026-10-15 | Update ADR-0010 to document the eval-harness exception instead of claiming raw persistence is transient. Public/production payload sanitization remains unchanged. |
| 2026-10-15 | Avoid a brittle complete event-schema allowlist; preserve exact raw streams for explicitly enabled local retention and keep checked-in fixtures sanitized. |
| 2026-10-15 | Maximum three concurrent workers is allowed, but shared-file tasks remain serial and the runner task precedes the eval-test task. |
| 2026-10-15 | Closure requires offline suites, Ruff, targeted review-regression tests, and one explicit serial live/agent-eval validation. |

## Wave/dependency table

| Wave | Tasks | Depends on | Purpose |
|---|---|---|---|
| 1 | 29.1.1 | none | Record the retention contract and update ADR-0010 scope |
| 2 | 29.2.1 | 29.1.1 | Fix capture bounds, path safety, classification, and terminal finalization |
| 3 | 29.2.2 | 29.2.1 | Fix CLI diagnostics and result plumbing in the same runner file |
| 4 | 29.3.1 | 29.2.2 | Add regression tests and verify sanitized checked-in fixtures |
| 5 | 29.4.1 | 29.3.1 | Document operation and run serial closure gates, including live/agent-eval |
| 6 | 29.6.1 | 29.4.1 | Handle the verified Pi `mcpScript` nested-MCP envelope and rerun live validation |

Tasks in each wave have disjoint file scopes. `eval\run_evals.py` and `eval\test_agent_eval.py` are intentionally sequenced, not parallelized.

## Hazards

- Raw retention is intentionally supported by user decision, so CLI help and README text must state that artifacts may contain prompt/tool/provider data and must be handled as local sensitive output.
- The existing `MAX_CAPTURE_*` limits currently affect parsing/evaluation; separate evaluation evidence from artifact-copy bounds so late events cannot disappear from pass/fail decisions.
- `_safe_id` currently permits `.` and `..`; sanitize complete identifiers before any path is constructed.
- Timeout exceptions may expose bytes or partial text; startup failures may have no stream. Both still require terminal metadata and artifact directories when retention is enabled.
- Existing extraction logic is duplicated in the runner and tests; update the runner first, then align tests without broad unrelated refactors.
- Live/agent-eval may require credentials, Pi availability, network access, and a shared HTTP port. Run serially and record skips/failures explicitly.

## Task specifications

### 29.1.1 — Defining the eval retention exception

- **Repo:** `D:\workspace\fpac-soil-mcp`
- **Files in scope:** must edit `docs\decisions\0010-public-payload-pii-detection-and-sanitization.md`; can create `planning\CAPTURE_CONTRACT_29.md`; may create its worker TODO under `planning\tasks\` and append its report to `planning\STATE_29.md`; must not edit runtime code or tests.
- **Depends on:** none.
- **Spec:** Document the supported eval-harness exception for explicitly opt-in raw local artifacts. Define repository-external roots, operator responsibility, no default retention, no checked-in raw fixtures, path/identifier safety, bounded diagnostic copies, and the distinction between public/production payload sanitization and local eval retention. Do not weaken the existing server privacy decision.
- **Do not touch:** `src\fpac_soil_mcp\privacy.py`, `eval\run_evals.py`, `eval\test_agent_eval.py`, dependencies, or prior orchestration files.
- **Grep anchors/reference:** ADR-0010 frontmatter and “Decision Outcome”; `planning\CAPTURE_CONTRACT_28.md`; `AGENTS.md` operational privacy rules.
- **Acceptance:** ADR-0010 explicitly names the eval exception and preserves public/production behavior; contract names raw opt-in, external root, warnings, cleanup, fixture sanitization, and prohibited repository use.
- **Targeted command:** `rg -n "eval|raw|opt-in|external|repository|production|fixture|sanitize|retention" docs\decisions\0010-public-payload-pii-detection-and-sanitization.md planning\CAPTURE_CONTRACT_29.md`

### 29.2.1 — Correcting runner capture and finalization

- **Repo:** `D:\workspace\fpac-soil-mcp`
- **Files in scope:** must edit `eval\run_evals.py`; may create its worker TODO under `planning\tasks\` and append its report to `planning\STATE_29.md`; no other source files.
- **Depends on:** 29.1.1.
- **Spec:** Implement the capture core only: make `.`/`..` and equivalent special identifiers safe before path construction; keep raw streams/events available for explicitly enabled repository-external retention while applying bounds only to artifact copies and recording truncation metadata; evaluate complete stdout/event evidence for tool and keyword checks; detect actual dedicated invocation containers rather than arbitrary event-type substrings; recognize nested `tool_calls`/content structures; classify absent versus present-unrecognized correctly; and use shared finalization for success, non-zero exit, timeout, startup error, malformed output, and retry attempts. Preserve existing status, retry, and structured-evidence semantics. Leave CLI presentation to 29.2.2.
- **Do not touch:** tests, fixtures, README, ADR files, `src\`, dependency manifests, or public server behavior.
- **Grep anchors/reference:** `_safe_id`/`_artifact_root` around lines 80-105; `_capture_attempt` around 110-145; `extract_structured_tool_names` around 220-300; `run_case` around 329-605; `main` around 650-724.
- **Acceptance:** `run_case` cannot escape the external root for any run/case identifier; late events affect evaluation; raw opt-in artifacts preserve exact interrogable data while artifact-copy truncation is explicit; discovery-only events are absent; nested calls classify correctly; all terminal paths produce attempt metadata/artifacts when enabled.
- **Targeted command:** `uv run pytest eval\test_agent_eval.py -m "not agent_eval" -q`

### 29.2.2 — Surfacing CLI capture diagnostics

- **Repo:** `D:\workspace\fpac-soil-mcp`
- **Files in scope:** must edit `eval\run_evals.py`; may create its worker TODO under `planning\tasks\` and append its report to `planning\STATE_29.md`; no other source files.
- **Depends on:** 29.2.1.
- **Spec:** Wire artifact paths and capture errors into per-case CLI diagnostics. Print per-attempt metadata references and capture failures alongside existing case diagnostics while leaving the aggregate summary table and exit behavior compatible. Keep raw content out of diagnostics; print only paths, statuses, and error descriptions.
- **Do not touch:** tests, fixtures, README, ADR files, `src\`, dependency manifests, or public server behavior.
- **Grep anchors/reference:** `main` around lines 650-724; result fields returned by `run_case`; existing summary-table output.
- **Acceptance:** CLI output includes artifact paths and capture errors per case, excludes raw content from diagnostics, and retains the aggregate table. The focused eval test command passes.
- **Targeted command:** `uv run pytest eval\test_agent_eval.py -m "not agent_eval" -q`

### 29.3.1 — Adding review-regression coverage

- **Repo:** `D:\workspace\fpac-soil-mcp`
- **Files in scope:** must edit `eval\test_agent_eval.py`; can update only sanitized fixtures under `eval\fixtures\event_capture\`; may create its worker TODO under `planning\tasks\` and append its report to `planning\STATE_29.md`; no production files.
- **Depends on:** 29.2.2.
- **Spec:** Add deterministic mocked-subprocess tests for each review finding: `.`/`..` traversal rejection, exact raw opt-in retention outside the repository, late-event evaluation beyond artifact bounds, discovery versus nested invocation classification, timeout/startup/non-zero finalization, retry preservation, CLI diagnostics, and checked-in fixture sanitization. Keep historical provider-envelope claims limited to verified fixtures; use synthetic cases only to exercise the explicitly stated boundary, not to claim historical Pi shapes. Ensure raw artifact tests assert exact retained content without committing raw data.
- **Do not touch:** `eval\run_evals.py`, `src\`, live-service tests, prompt dataset semantics, or dependency manifests.
- **Grep anchors/reference:** existing capture tests around lines 99-220 and 475-530; fixtures in `eval\fixtures\event_capture\`; PR #22 review findings.
- **Acceptance:** focused eval tests pass; each of six findings has a named regression; tests prove raw retention is opt-in/external, checked-in fixtures are sanitized, and full evidence is evaluated independently from copy limits.
- **Targeted command:** `uv run pytest eval\test_agent_eval.py -m "not agent_eval" -q`

### 29.4.1 — Documenting operation and running closure verification

- **Repo:** `D:\workspace\fpac-soil-mcp`
- **Files in scope:** must edit `README.md`; can update `planning\STATE_29.md`; may create its worker TODO under `planning\tasks\`; no runtime code or tests.
- **Depends on:** 29.3.1.
- **Spec:** Document the opt-in raw-artifact mode, required external root, exact interrogation workflow, operator handling/cleanup expectations, checked-in fixture sanitization, path-safety guarantees, and the distinction from production privacy behavior. Then record exact closure results. The orchestrator owns serial full-suite and live/agent-eval execution; this task must not run or modify the live environment itself.
- **Do not touch:** `eval\run_evals.py`, `eval\test_agent_eval.py`, ADR-0010, prior plan/state files, or unrelated docs.
- **Grep anchors/reference:** existing README eval section; `AGENTS.md` quick-start/test commands; `planning\STATE_28.md` closure gates.
- **Acceptance:** README matches the implemented CLI; `STATE_29.md` records offline suites, Ruff, targeted tests, and explicit live/agent-eval results or a clearly stated environmental block. No raw artifact is added to git, and `git diff --check` passes.
- **Targeted command:** `rg -n "capture|artifact|raw|external|retention|cleanup|privacy|agent_eval|live_network" README.md planning\STATE_29.md`

### 29.6.1 — Handling the verified Pi mcpScript envelope

- **Repo:** `D:\workspace\fpac-soil-mcp`
- **Files in scope:** must edit `eval\run_evals.py` and `eval\test_agent_eval.py`; can create or update only sanitized fixtures under `eval\fixtures\event_capture\`; may create `planning\tasks\29.6.1.todo.md` and append its report to `planning\STATE_29.md`.
- **Depends on:** 29.4.1.
- **Spec:** Add explicit support for the verified Pi JSONL shape captured during the failed live gate: `tool_execution_start/end` with `toolName: "mcpScript"`, JavaScript `args.code` containing `tools.call(...)`, and result metadata under `details.calls[].path` plus `structuredContent`. Extract the nested MCP tool name and its object-literal arguments sufficiently to validate POINT-01 coordinates, while preserving direct tool-call support, prose exclusion, discovery-event handling, and existing evidence classifications. Use the real captured shape only through a sanitized checked-in fixture; never commit raw session IDs, encrypted reasoning, provider metadata, or unredacted payloads. Keep runner and test helper behavior aligned.
- **Do not touch:** `src\`, README, ADRs, dependencies, prompt dataset semantics, live-service code, or raw diagnostic files under `.development\`.
- **Grep anchors/reference:** `eval\run_evals.py` `extract_structured_tool_names` and `run_case`; `eval\test_agent_eval.py` `extract_structured_tool_names` and `extract_tool_calls`; the sanitized `mcpScript` fixture; the diagnostic evidence summarized in `planning\STATE_29.md`.
- **Acceptance:** the focused eval suite passes; sanitized fixture tests prove nested tool-name and coordinate extraction; direct and existing classification tests remain green; `uv run pytest -m agent_eval -q` passes POINT-01 or records a new evidence-based blocker with retained external diagnostics; Ruff check/format and `git diff --check` pass.
- **Targeted command:** `uv run pytest eval\test_agent_eval.py -m "not agent_eval" -q`
