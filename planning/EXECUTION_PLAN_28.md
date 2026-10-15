# Execution Plan 28 — Eval Event Capture Artifacts

## Goal & Scope

### Goal

Close the evaluation event-capture gap described in `planning/RESEARCH_EVENT_CAPTURE_GAP.md` and issue `AndrewBrown-USDA/fpac-soil-mcp#10`: preserve inspectable raw Pi JSONL/stdout per evaluation case, associate evidence with run/case/attempt identifiers, include artifact paths in diagnostics, retain the current human-readable summary and structured-tool semantics, and provide privacy-safe parser regression fixtures so failures distinguish an absent tool from a tool that was present but not extracted.

### In scope

- Verify and record the unavailable PR #10 metadata without fabricating facts.
- Define an eval-only capture, artifact, privacy, retention, and cleanup contract.
- Add opt-in raw stdout/stderr/JSONL capture to `eval/run_evals.py`, including retry/error paths.
- Add sanitized parser-regression fixtures and deterministic tests.
- Validate privacy, bounded artifacts, retry preservation, malformed JSON, timeout, startup failure, and cleanup.
- Document opt-in behavior, artifact inspection, privacy limits, retention, cleanup, and fixture creation.

### Out of scope

- Production server logging, tracing, HTTP retry instrumentation, or a general event bus.
- Changes to `src\fpac_soil_mcp\` workflow `StateTransitionEvent`.
- SDA, TIGERweb, NASS, or other live-service behavior.
- Treating prose or prompt echo as proof of tool execution.
- Persisting unsanitized prompts, tool arguments, generated responses, coordinates, or producer data.
- Any claim about PR #10 title, branch, SHA, review state, or changed files that cannot be verified.

### Verbatim constraints

- “Retention must be opt-in and non-retaining by default.”
- “Sanitize before persistence; do not rely only on field-name matching.”
- “Preserve the current human-readable summary and parser semantics.”
- “Dedicated structured tool fields must remain the only evidence of tool execution; prose must never count as a tool call.”
- “Capture successful, failed, timeout, startup-error, malformed-JSON, and retry attempts.”
- “Build fixtures from real captured failure shapes rather than speculative envelopes.”
- “Keep production logging, HTTP retry instrumentation, workflow events, and general event bus work explicitly deferred.”
- “Same-file tasks must be sequential, not parallel.”

## Recon log

- Next available orchestration number is 28; prior artifacts run through 26.
- Entry points: `src\fpac_soil_mcp\app.py` (58 lines), `main.py` (28), `eval\run_evals.py` (537), `eval\test_agent_eval.py` (617), `eval\prompt_test_cases.json` (468).
- `run_case()` captures Pi stdout/stderr in memory, parses JSONL, derives diagnostics, and returns no raw stream, event list, attempt list, return code, or artifact path (`eval\run_evals.py:329-471`).
- Test-side JSONL parsing and live Pi assertions are in `eval\test_agent_eval.py:30-40` and `:562-617`.
- The gap document identifies missing per-case serialized events and failures `POINT-02`, `POLY-01`, `PROMPT-01`, and `LESA-02` (`planning\RESEARCH_EVENT_CAPTURE_GAP.md:1-17`).
- Default baseline reported by reconnaissance: offline `294 passed, 14 deselected`; eval parser tests `8 passed, 2 deselected`; Ruff check and format check passed. Reconfirm before Wave 1.
- Default eval transport is isolated stdio; SSE/HTTP defaults to `127.0.0.1:8000` and must remain serial if exercised.
- Accepted ADR-0010 requires centralized privacy handling but warns field-name matching misses free-form sensitive values and coordinates. ADR-0011 requires mocked/offline default tests with live and agent-eval opt-in.

## Decisions and assumptions

| Date | Decision |
|---|---|
| 2026-10-14 | Treat issue #10 and the local gap document as authoritative because PR #10 metadata is unavailable; record the 404/indexing limitation in the plan and do not block implementation on unverifiable PR facts. |
| 2026-10-14 | Use eval-only, opt-in persistence with no new runtime dependencies; keep default runs non-retaining. |
| 2026-10-14 | Use run/case/attempt identity and a repository-external artifact root supplied by the caller/environment; never use prompt text in filenames. |
| 2026-10-14 | Preserve the current structured evidence rule and human-readable summary; add evidence fields rather than replacing existing output semantics. |
| 2026-10-14 | Use sanitized, minimal checked-in fixtures for parser regression. Raw captured streams remain local/ephemeral unless explicitly retained by the opt-in mechanism. |
| 2026-10-14 | Maximum two concurrent workers; same-file work is serial; full suites run serially at wave boundaries. |
| 2026-10-14 | Acceptance requires deterministic offline tests, Ruff check/format, and explicit opt-in Pi/live gates only where applicable; the exact non-quiet offline command is the closure gate. |

## Wave/dependency table

| Wave | Tasks | Depends on | Purpose |
|---|---|---|---|
| 1 | 28.1.1, 28.1.2 | none | Evidence/contract and baseline/privacy design; disjoint planning/contract files |
| 2 | 28.2.1 | 28.1.1, 28.1.2 | Implement runner capture and result plumbing |
| 3 | 28.3.1 | 28.2.1 | Add deterministic fixtures and parser/capture tests in the shared test file |
| 4 | 28.4.1 | 28.3.1 | Validate privacy, cleanup, retry/error paths, and fixture schema |
| 5 | 28.5.1 | 28.4.1 | Documentation and serial full verification |

## Hazards

- `eval\run_evals.py` and `eval\test_agent_eval.py` are large shared surfaces; do not parallelize edits to either file.
- Raw Pi output may contain coordinates, geometry, producer data, prompts, or generated text. Never persist unsanitized content.
- The existing parser ignores malformed/non-JSON lines; capture must preserve them separately without making them tool evidence.
- Retry attempts currently overwrite evidence; capture must retain bounded per-attempt records.
- Startup and timeout failures may have no `CompletedProcess`; tests must cover partial output where the subprocess API provides it.
- The default suite must not invoke Pi, external services, or a shared network port.

## Task specifications

### 28.1.1 — Reconstructing issue/PR evidence and establishing baseline

- **Repo:** `D:\workspace\fpac-soil-mcp`
- **Files in scope:** may update only the baseline/reconstruction sections of `planning\STATE_28.md`; no source files and no edits to this execution plan during worker execution.
- **Depends on:** none.
- **Spec:** Record the PR #10 404/indexing limitation, issue/local-document authority, current baseline commands/results, and exact evidence needed to reconstruct PR metadata. Do not invent PR details. Include the pre-wave baseline in `STATE_28.md`.
- **Do not touch:** `src\`, `eval\`, `tests\`, dependency manifests, or prior orchestration artifacts.
- **Anchors/reference:** `planning\RESEARCH_EVENT_CAPTURE_WAVE_PLAN_PROMPT.md:23-25`; `planning\STATE_26.md:1-31`.
- **Acceptance:** `STATE_28.md` contains `git status --short`, exact baseline commands/results, marker/port constraints, ADR review, and a pending wave board; no source changes.
- **Targeted command:** `git status --short; uv run pytest -m "not live_network and not agent_eval" -q; uv run pytest eval\test_agent_eval.py -m "not agent_eval" -q; uv run ruff check .; uv run ruff format --check .`

### 28.1.2 — Defining capture, privacy, and artifact contract

- **Repo:** `D:\workspace\fpac-soil-mcp`
- **Files in scope:** can create `planning\CAPTURE_CONTRACT_28.md`; must not edit source.
- **Depends on:** none.
- **Spec:** Define run/case/attempt metadata, artifact root and filename rules, stdout/stderr/JSONL separation, malformed-line handling, opt-in switch, default non-retention, bounded size, cleanup, diagnostic path fields, and conservative redaction requirements for free-form values and coordinates.
- **Do not touch:** `src\fpac_soil_mcp\privacy.py`, production logging, HTTP clients, or eval implementation.
- **Anchors/reference:** `docs\decisions\0010-public-payload-pii-detection-and-sanitization.md:63-71`; `planning\RESEARCH_EVENT_CAPTURE_GAP.md:11-17`.
- **Acceptance:** Contract names run/case/attempt IDs, UTC timestamps, model/provider, safe command/revision metadata, stdout/stderr/JSONL/malformed-line fields, artifact paths, opt-in switch, bounded size, cleanup, raw-vs-summary distinction, and prohibited persisted content. A checklist or `rg` check confirms every required heading.
- **Targeted command:** `rg -n "run_id|case_id|attempt|timestamp|model|provider|stdout|stderr|JSONL|cleanup|opt-in|coordinate|redact" planning\CAPTURE_CONTRACT_28.md`

### 28.2.1 — Adding opt-in eval capture and diagnostics

- **Repo:** `D:\workspace\fpac-soil-mcp`
- **Files in scope:** must edit `eval\run_evals.py`; can create a focused helper only under `eval\` if required; must not edit tests in this task.
- **Depends on:** 28.1.1, 28.1.2.
- **Spec:** Implement the contract at `run_case()`/`main()` anchors. Preserve existing summary/status/parser semantics. Capture bounded per-attempt stdout, stderr, parsed JSON events, malformed lines, return code, timestamps, model/provider, and safe command/revision metadata. Persist only when explicitly enabled, associate artifacts with run/case/attempt IDs, include sanitized artifact paths in results/diagnostics, and retain prior attempts during one retry. Add a mechanically inspectable evidence classification that distinguishes `absent` (no dedicated structured event), `present_unrecognized` (dedicated structured tool evidence exists but normalized extraction found no tool), and `recognized`; prose-only output must remain `absent`. Handle success, failure, timeout, startup error, and partial output without broad catches or silent fallbacks.
- **Do not touch:** `eval\test_agent_eval.py`, `src\`, `pyproject.toml`, `Makefile`, and prompt fixtures.
- **Anchors/reference:** `eval\run_evals.py:329-471`; commit `8037dd457115c6778e52814c3baa77b9d7e79b05`.
- **Acceptance:** Existing CLI summary remains compatible; opt-in disabled produces no retained artifacts; opt-in produces run/case/attempt artifacts outside the repository; diagnostics identify artifacts without raw content; metadata and retry evidence are complete; evidence classification is returned and bounded.
- **Targeted command:** `uv run pytest eval\test_agent_eval.py -m "not agent_eval" -q`

### 28.3.1 — Adding sanitized parser and capture regression tests

- **Repo:** `D:\workspace\fpac-soil-mcp`
- **Files in scope:** must edit `eval\test_agent_eval.py`; can create sanitized fixtures under `eval\fixtures\event_capture\`; update `eval\prompt_test_cases.json` only if a verified fixture requires it.
- **Depends on:** 28.2.1.
- **Spec:** Add deterministic mocked-subprocess tests for success, stderr, non-JSON lines, malformed JSON, timeout, startup failure, retry attempts, opt-in/off behavior, artifact paths, metadata, and the `absent`/`present_unrecognized`/`recognized` evidence classification. Use real captured shapes from the four documented failures when those raw captures are available. If they are unavailable, explicitly defer envelope-specific fixtures and limit checked-in fixtures to verified existing shapes plus transport/error boundaries; do not treat synthetic envelopes as evidence of the historical failures. Preserve the rule that prose never counts as tool execution.
- **Do not touch:** production server modules, external-service tests, and unverified provider-envelope behavior.
- **Anchors/reference:** `eval\test_agent_eval.py:30-40`, `:99-420`, `:475-530`; `planning\RESEARCH_EVENT_CAPTURE_GAP.md:5-13`.
- **Acceptance:** Focused test file passes offline; tests assert raw evidence is separate from normalized output, prose-only output is `absent`, dedicated-but-unrecognized evidence is `present_unrecognized`, recognized evidence is `recognized`, and no sensitive fixture values are persisted. Any missing historical raw capture is recorded as an explicit deferral.
- **Targeted command:** `uv run pytest eval\test_agent_eval.py -m "not agent_eval" -q`

### 28.4.1 — Validating privacy, cleanup, and artifact boundaries

- **Repo:** `D:\workspace\fpac-soil-mcp`
- **Files in scope:** must edit `eval\test_agent_eval.py` only if needed for validation gaps; can create/update a narrowly scoped eval fixture/test file; no production files.
- **Depends on:** 28.3.1.
- **Spec:** Verify default non-retention, explicit cleanup, repository-external paths, bounded artifact content, no prompt text in filenames, redaction of prohibited keys and coordinate/free-form sensitive values, and preservation of partial failure evidence. Include a test that existing privacy behavior is not weakened. Keep this task to no more than twelve TODO steps; if implementation requires new source files or privacy-module changes, stop for replan.
- **Do not touch:** `src\fpac_soil_mcp\privacy.py` unless a separate replan is approved; no live/network tests.
- **Anchors/reference:** `src\fpac_soil_mcp\privacy.py:62-143`; `tests\test_privacy.py:49-100`.
- **Acceptance:** Offline focused tests and privacy tests pass; artifact tests fail if raw sensitive values or repository-local retained files appear.
- **Targeted command:** `uv run pytest eval\test_agent_eval.py tests\test_privacy.py -m "not live_network and not agent_eval" -q`

### 28.5.1 — Documenting operation and running closure verification

- **Repo:** `D:\workspace\fpac-soil-mcp`
- **Files in scope:** must edit `README.md` or the existing eval documentation location and `planning\STATE_28.md`; can create no new runtime files.
- **Depends on:** 28.4.1.
- **Spec:** Document opt-in capture configuration, artifact layout, inspection, retention/cleanup, privacy limitations, fixture creation, and default test behavior. Update `STATE_28.md` with task reports. The orchestrator, not the worker, runs serial full-suite verification and records exact counts, deviations, and opt-in gates.
- **Do not touch:** prior plan/state files or unrelated user documentation.
- **Anchors/reference:** `AGENTS.md:3-22`; `Makefile:30-55`; `planning\PROMPT_TEMPLATE_26.md:57-65`.
- **Acceptance:** Documentation matches implementation; targeted documentation checks pass; state board/reports are complete; live/agent-eval commands remain explicitly opt-in. The orchestrator separately runs the exact closure gate `uv run pytest -m "not live_network and not agent_eval"` plus Ruff checks serially.
- **Targeted command:** `rg -n "opt-in|artifact|retention|cleanup|privacy|fixture|agent_eval|live_network" README.md planning\STATE_28.md`
