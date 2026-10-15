# Prompt for Wave-Orchestration Planning: Issue/PR #10 Event Capture Gap

## Executive Summary

Create a wave-orchestration implementation plan for the event-capture gap described by issue `AndrewBrown-USDA/fpac-soil-mcp#10` and `planning/RESEARCH_EVENT_CAPTURE_GAP.md`. GitHub PR `#10` itself could not be retrieved: PR metadata, files, commits, and pull-request search returned no verifiable result. Treat issue #10 and the local planning document as authoritative scope, and explicitly begin with a short reconstruction/verification task that records this uncertainty rather than inventing PR details. The core problem is that the eval harness parses Pi JSONL in memory, discards raw per-case stdout/stderr/events, and therefore cannot distinguish an unrecognized event envelope from a genuinely absent tool invocation. The plan should prioritize opt-in raw artifact retention, parser regression fixtures, privacy controls, and deterministic offline validation; production telemetry is a separate, deferred concern.

## Ready-to-pass prompt

You are planning work in `AndrewBrown-USDA/fpac-soil-mcp`. Produce the next numbered planning artifact set under `planning/`: `EXECUTION_PLAN_N.md`, `PROMPT_TEMPLATE_N.md`, and `STATE_N.md`, following the repository's existing wave-orchestration conventions.

### User goal

Refer to PR `#10` and `planning/RESEARCH_EVENT_CAPTURE_GAP.md`, then create an executable wave plan that closes the evaluation event-capture gap:

- retain raw per-case Pi JSONL/stdout artifacts;
- associate artifacts with both run IDs and case IDs;
- include artifact paths in failure diagnostics;
- preserve the existing human-readable summary;
- make raw streams available as parser-regression fixtures;
- distinguish “tool absent” from “tool present but not extracted”;
- preserve privacy and existing offline-by-default test behavior.

### Important uncertainty

PR `#10` could not be verified through GitHub. Direct PR reads returned 404, pull-request search found no matching PR, and no authoritative PR branch/head SHA or changed-file list was available. Issue `AndrewBrown-USDA/fpac-soil-mcp#10` states the requested raw-artifact behavior. The local planning document is present at `planning/RESEARCH_EVENT_CAPTURE_GAP.md` but was not present in the indexed GitHub contents snapshot. The plan must record this as a reconstruction/access uncertainty, not fabricate PR metadata.

### Verified repository facts and references

- Repository conventions and commands are in `AGENTS.md`.
- Canonical developer commands are in `Makefile`.
- Python/pytest markers and default exclusions are in `pyproject.toml`.
- Accepted ADRs are indexed in `docs/decisions/README.md`.
- Privacy constraints are defined by ADR-0010 and `src/fpac_soil_mcp/privacy.py`.
- Mocked-default/live-opt-in testing is defined by ADR-0011.
- Existing wave examples are `planning/EXECUTION_PLAN_26.md`, `planning/STATE_26.md`, and `planning/PROMPT_TEMPLATE_26.md`.
- Existing worker discipline requires scoped files, micro-plans before code, targeted tests, serial wave-boundary verification, and reports of no more than 15 lines.

Relevant references:

- `planning/RESEARCH_EVENT_CAPTURE_GAP.md`: aggregate transcript lacks serialized event objects, per-case JSONL, tool-call payloads, and MCP tool-list responses; four cases failed (`POINT-02`, `POLY-01`, `PROMPT-01`, `LESA-02`); raw streams are recommended.
- `eval/run_evals.py:365-386`: Pi stdout/stderr are captured in memory; JSONL is parsed and invalid lines ignored.
- `eval/run_evals.py:391-451`: structured tools, advertised tools, assistant text, retry diagnostics, and keyword checks are derived; raw events are discarded.
- `eval/run_evals.py:453-471`: returned result has status/error/output/expected fields but no raw stdout, stderr, events, attempts, return code, or artifact path.
- `eval/test_agent_eval.py:30-40`: test parser parses JSONL and discards non-JSON lines.
- `eval/test_agent_eval.py:562-617`: live Pi test parses events and asserts initialization, tool names, structured arguments, and keywords, but retains nothing after the test.
- `eval/run_evals.py:109-270`: parser/extraction helpers support several direct and one-level nested shapes, advertised-tool precedence/fallback, namespaced matching, and one retry.
- `eval/test_agent_eval.py:127-394`: test-side structured tool and argument extraction, including exact POINT-01 coordinate assertions.
- `eval/prompt_test_cases.json`: structured cases with IDs, target types/names, expected tools, keywords, and optional geometry.
- `8037dd457115c6778e52714c3baa77b9d7e79b05`: preserves structured eval results when subprocess startup fails.
- `c1a9c6727759b9328c79dc551ad58c27f92e8745`: structured tool-call and assistant-text extraction.
- `daf441ce625c05f1a6a99a14b4884c057bb31234`: support for structured agent call events and direct nested args.
- `docs/decisions/0010-public-payload-pii-detection-and-sanitization.md:15-71`: no producer PII in external payloads/responses; sanitizer is field-name based; coordinate privacy is not fully automated.
- `src/fpac_soil_mcp/privacy.py:62-143`: recursive validation/sanitization returns paths and does not log sensitive values.
- `AGENTS.md:99-124`: preserve regulatory notices, validate coordinates/mukeys, fixed SQL, Section 1619 protections, and offline default tests.
- `pyproject.toml:35-43`: default pytest excludes `live_network` and `agent_eval`.
- `Makefile:1-70`: `make test`, `make test-eval`, `make test-live`, `make lint`, `make format-check`, and `make check`.

Indexed repository commit used for most code references: `e2a4ea215d49b02e3047daf088a01da1e5ba0471`.

### Planning requirements

1. Start with a reconstruction/verification task for PR #10/issue #10. State the 404/indexing limitation and define what evidence is needed; do not block all implementation if the issue and local planning document are sufficient.
2. Define a raw-capture contract before implementation:
   - run ID and case ID;
   - timestamps, model/provider, command/revision where safe;
   - stdout/stderr/JSONL treatment;
   - per-attempt records for retries;
   - artifact naming and location;
   - artifact-path diagnostics;
   - retention and cleanup;
   - distinction between raw events and normalized summary.
3. Keep retention opt-in and non-retaining by default. Do not add raw artifacts to the repository or source tree.
4. Sanitize before persistence. Do not rely only on ADR-0010 field-name matching because free-form values and coordinates may still be sensitive. Avoid logging complete prompts/results in diagnostics.
5. Preserve the current human-readable aggregate report and current parser semantics. Dedicated structured tool fields must remain the only evidence of tool execution; prose must never count as a tool call.
6. Capture successful, failed, timeout, startup-error, malformed-JSON, and retry attempts. Preserve partial diagnostics when available.
7. Build fixtures from real captured failure shapes, especially `POINT-02`, `POLY-01`, `PROMPT-01`, and `LESA-02`. Add tests for provider/nested envelopes only when verified by captured fixtures; do not speculate about unsupported shapes.
8. Consider whether to consolidate duplicated parsing between `run_evals.py` and `test_agent_eval.py`; if proposed, make it a separate, clearly scoped task with explicit regression coverage.
9. Keep production server logging, HTTP retry instrumentation, workflow `StateTransitionEvent`, and a general event bus out of scope unless the plan explicitly defers them. The first implementation should be eval-only.
10. Add or update documentation for artifact locations, inspection, privacy, cleanup, and fixture creation.

### Expected wave shape

Use a small DAG with disjoint file scopes inside each wave. A reasonable starting point is:

- Wave 1: reconstruct/verify PR #10 and define capture/privacy contract.
- Wave 2: implement eval raw capture and result/diagnostic plumbing in `eval/run_evals.py`.
- Wave 3: add parser-regression fixtures and focused tests in `eval/test_agent_eval.py` and new fixture files.
- Wave 4: validate privacy, cleanup, retry/error paths, and fixture/schema behavior.
- Wave 5: documentation, serial full verification, and planning closure.

Adjust this decomposition after inspecting the current tree. Same-file tasks must be sequential, not parallel. Do not create a wave with more than eight tasks. Keep each task to no more than twelve micro-plan steps.

### Acceptance bar

The plan must name exact targeted commands. At minimum:

```powershell
uv run pytest eval\test_agent_eval.py -m "not agent_eval" -q
uv run pytest -m "not live_network and not agent_eval"
uv run ruff check .
uv run ruff format --check .
```

Run `uv run pytest -m live_network` or `make test-eval` only as explicit opt-in gates when the changed behavior requires external services or Pi. Full-suite verification is serial at wave boundaries.

### Required output

Write:

1. `planning/EXECUTION_PLAN_N.md`
   - Goal & Scope, including explicit out-of-scope production telemetry.
   - Verbatim constraints from this prompt and `planning/RESEARCH_EVENT_CAPTURE_GAP.md`.
   - Recon log and baseline commands.
   - Decision log with assumptions about unavailable PR #10 metadata.
   - Wave/dependency table.
   - One task spec per task containing: ID, repo, files-in-scope (must edit/can create), dependencies, spec prose, constraints/do-not-touch list, grep anchors, reference implementations, acceptance criteria, and targeted command.
2. `planning/PROMPT_TEMPLATE_N.md`
   - Existing worker skeleton, repository conventions, plan-gate rules, targeted-test rules, escalation rules, and pointer to `[[git-workflow-standards]](../../git-workflow-standards/SKILL.md)`.
3. `planning/STATE_N.md`
   - Green baseline, wave board with every task `pending`, and an empty task-reports section.

Before presenting the artifacts, review the plan on two axes:

- **Spec:** every requirement above maps to a task or explicit deferral; no invented PR facts.
- **Standards:** tasks are right-sized, acceptance is mechanically checkable, file scopes within waves are disjoint, shared eval files are sequenced, privacy and serial-suite hazards are explicit.

Do not implement code. Stop after the plan artifacts are reviewed and ready for approval.

## Confidence Assessment

**High confidence:** the eval harness currently discards raw structured events and does not persist per-case stdout/stderr; issue #10 and the local gap document request raw artifact retention; repository testing, privacy, and wave-planning conventions are established.  
**Medium confidence:** the exact final file split and whether a shared parser helper should be introduced; this depends on fresh inspection of the current working tree.  
**Low confidence/unverified:** PR #10 title, branch, head/base SHA, changed files, review state, and whether any later implementation exists outside the indexed default branch. Do not use these as facts without fresh GitHub evidence.

## Footnotes

[^1]: `planning/RESEARCH_EVENT_CAPTURE_GAP.md:1-17`; local planning artifact supplied with the task.
[^2]: `eval/run_evals.py:365-471`; indexed commit `e2a4ea215d49b02e3047daf088a01da1e5ba0471`.
[^3]: `eval/test_agent_eval.py:30-40`, `:562-617`; indexed commit `e2a4ea215d49b02e3047daf088a01da1e5ba0471`.
[^4]: `eval/run_evals.py:109-270`; indexed commit `e2a4ea215d49b02e3047daf088a01da1e5ba0471`.
[^5]: `8037dd457115c6778e52714c3baa77b9d7e79b05`; `c1a9c6727759b9328c79dc551ad58c27f92e8745`; `daf441ce625c05f1a6a99a14b4884c057bb31234`.
[^6]: `docs/decisions/0010-public-payload-pii-detection-and-sanitization.md:15-71`; `src/fpac_soil_mcp/privacy.py:62-143`.
[^7]: `AGENTS.md:99-124`; `pyproject.toml:35-43`; `Makefile:1-70`.
