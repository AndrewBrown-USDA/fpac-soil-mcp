# Orchestration 28 State

## Baseline checklist

- [x] `git status --short` recorded before task execution: `?? planning/tasks/28.1.1.todo.md`; pre-existing `?? planning/tasks/28.1.2.todo.md`
- [x] `uv run pytest -m "not live_network and not agent_eval" -q`: 294 passed, 14 deselected in 13.94s
- [x] `uv run pytest eval\test_agent_eval.py -m "not agent_eval" -q`: 8 passed, 2 deselected in 0.04s
- [x] `uv run ruff check .`: all checks passed
- [x] `uv run ruff format --check .`: 340 files already formatted
- [x] PR #10 404/indexing limitation recorded; no unverifiable metadata treated as fact
- [x] Default eval transport confirmed as isolated stdio
- [x] SSE/HTTP shared-port hazard recorded; live/agent-eval gates remain opt-in
- [x] ADR-0010 privacy and ADR-0011 test constraints reviewed

## Task 28.1.1 reconstruction record

PR #10 could not be verified from the available GitHub/indexed repository evidence: direct PR metadata was unavailable (404/indexing limitation), and no authoritative PR title, branch, head SHA, review state, or changed-file list was available. Issue `AndrewBrown-USDA/fpac-soil-mcp#10` and the local `planning\RESEARCH_EVENT_CAPTURE_GAP.md` are therefore the authoritative reconstruction inputs. This records an access limitation, not a claim about missing PR contents.

To reconstruct PR metadata later, obtain an authoritative repository/API response for PR `10` containing its number, title, state, base/head repository and refs, head SHA, author, timestamps, changed-file list, additions/deletions, commits, and review status; cross-check those fields against the issue and local gap document before recording them. Do not infer any field from prose, a local branch name, or an unavailable index.

The baseline was rerun from the worker working tree. The two untracked task TODO files shown above are planning artifacts; no source or evaluation files were changed. Default tests remain offline and exclude `live_network` and `agent_eval`. Eval uses isolated stdio by default. SSE/HTTP defaults to `127.0.0.1:8000`, so any live/network execution must remain serialized or use distinct ports. ADR-0010 requires conservative privacy handling, and ADR-0011 requires mocked/offline default tests with live and agent-eval checks opt-in.

## Baseline results

Recorded 2026-10-14 during Wave 1 task execution from the current working tree. At execution start, `planning/tasks/28.1.1.todo.md` and pre-existing `planning/tasks/28.1.2.todo.md` were untracked. The default suite excludes `live_network` and `agent_eval`; Pi and external-service gates are opt-in. Network transports default to `127.0.0.1:8000` and must be serialized or assigned distinct ports.

## Orchestrator closure gates

Run serially after implementation waves:

```powershell
uv run pytest -m "not live_network and not agent_eval"
uv run ruff check .
uv run ruff format --check .
```

## Wave board

| Task | Wave | Status | Worker | Notes |
|---|---:|---|---|---|
| 28.1.1 | 1 | done | worker | PR evidence limitation recorded; baseline rerun |
| 28.1.2 | 1 | done | worker | Define capture/privacy/artifact contract |
| 28.2.1 | 2 | done | worker | Implemented opt-in runner capture |
| 28.3.1 | 3 | done | worker | Add sanitized parser/capture regression tests |
| 28.4.1 | 4 | done | worker | Validate privacy, cleanup, and boundaries |
| 28.5.1 | 5 | done | worker | Documentation complete; full verification left to orchestrator |

## Task reports

<!-- Worker reports are appended below, one section per task, <=15 lines. -->

## 28.2.1

- **Status**: complete.
- **Changed files**: `eval\run_evals.py`; created `planning\tasks\28.2.1.todo.md`.
- Added opt-in capture switches; default remains non-retaining.
- Added bounded, sanitized stdout/stderr/events/malformed-line artifacts with external-root enforcement.
- Added run/case/attempt metadata, retry-preserving paths, and evidence classification.
- Preserved parser, statuses, summary output, and structured-tool-only evidence semantics.
- **Validation**: `uv run pytest eval\test_agent_eval.py -m "not agent_eval" -q` — 8 passed, 2 deselected.
- **Deviation**: timeout/startup attempts expose diagnostics but cannot persist partial timeout streams without a completed process.
- No dependencies, tests, source modules, or prompt fixtures changed; no commit made.

## 28.1.1

- **Status**: complete; PR/issue reconstruction limits and exact pre-wave baselines recorded.
- **Changed files**: `planning\STATE_28.md`; created `planning\tasks\28.1.1.todo.md` as required.
- **Validation**: offline pytest `294 passed, 14 deselected`; eval parser `8 passed, 2 deselected`; Ruff check passed; format check `340 files already formatted`.
- **Deviations**: working tree was not clean because `planning\tasks\28.1.2.todo.md` was already untracked; it was not modified.
- **Gotchas**: PR #10 metadata remains unverifiable; no PR facts were fabricated. Live/network and agent-eval gates remain opt-in.

## Task 28.1.2 report

- Status: complete.
- Created `planning\CAPTURE_CONTRACT_28.md`; the plan names the corrected 28 contract, not a 27 contract.
- Defined run/case/attempt IDs, UTC timestamps, model/provider, transport, and safe command/revision metadata.
- Defined separated stdout, stderr, parsed JSONL, malformed-line handling, diagnostics, evidence classes, and raw-vs-summary boundaries.
- Defined explicit opt-in retention, default non-retention, external artifact roots, safe filenames, bounds, retry preservation, and cleanup.
- Defined conservative redaction for prohibited keys, free-form sensitive values, coordinates, prompts, arguments, responses, and producer data.
- Validation: `rg -n "run_id|case_id|attempt|timestamp|model|provider|stdout|stderr|JSONL|cleanup|opt-in|coordinate|redact" planning\CAPTURE_CONTRACT_28.md` — 40 matches.
- Validation: `git diff --check` — passed.
- No source files or prior planning artifacts were modified.
- Note: `git status --short` also shows pre-existing untracked `planning\tasks\28.1.1.todo.md`; it was not changed.

## 28.3.1

- **Status**: complete.
- **Changed files**: `eval\test_agent_eval.py`; sanitized fixtures under `eval\fixtures\event_capture\`; created `planning\tasks\28.3.1.todo.md`.
- Added deterministic mocked-subprocess coverage for success, stderr, malformed/non-JSON lines, timeout, startup error, retries, opt-in retention, default non-retention, paths, metadata, and all evidence classes.
- Prose-only output remains `absent`; dedicated unrecognized events are `present_unrecognized`; recognized structured calls are `recognized`.
- Historical raw captures for POINT-02, POLY-01, PROMPT-01, and LESA-02 were unavailable; envelope-specific fixtures are explicitly deferred.
- **Validation**: `uv run pytest eval\test_agent_eval.py -m "not agent_eval" -q` — 15 passed, 2 deselected.
- No production files, external-service tests, prompt fixtures, or dependencies changed; no commit made.

## 28.4.1

- **Status**: complete.
- **Changed files**: `eval\test_agent_eval.py`; created `planning\tasks\28.4.1.todo.md`.
- Added validation for repository-external roots, rejected repository-local retention, safe opaque paths, and prompt exclusion.
- Added bounded stream assertions, prohibited-key/coordinate redaction checks, explicit cleanup, and default non-retention coverage.
- Existing timeout/startup/retry tests preserve partial-failure and attempt evidence; `tests\test_privacy.py` remains covered.
- **Validation**: `uv run pytest eval\test_agent_eval.py tests\test_privacy.py -m "not live_network and not agent_eval" -q` — 21 passed, 2 deselected in 0.25s.
- No production files or `privacy.py` were modified; no replan required; no commit made.

## 28.5.1

- **Status**: complete.
- **Changed files**: `README.md`; created `planning\tasks\28.5.1.todo.md`.
- Documented CLI/environment opt-in capture, required external artifact roots, and default non-retention.
- Documented run/case/attempt layout, stream inspection, bounded artifacts, explicit cleanup, and retry/failure diagnostics.
- Documented sanitization limits, prohibited sensitive content, structured-evidence semantics, and non-official FPPA scope.
- Documented deterministic sanitized fixture creation and deferral of unavailable historical Pi envelopes.
- Documented offline default tests and kept `live_network`/`agent_eval` explicitly opt-in and serial.
- **Validation**: targeted README/state search passed; full-suite verification is explicitly left to the orchestrator.
- No runtime files, tests, dependencies, or prior planning artifacts were modified; no commit made.
