# Execution Plan 30 — Resolve Pi Evaluation Prompt and Citation Failures

## Goal & Scope

### Goal

Resolve the three reported Pi evaluation failures in `D:\workspace\fpac-soil-mcp`:
the RES-01 exact-citation mismatch, PROMPT-01 prompt/tool discovery failure,
and PROMPT-02 missing corridor citation. Preserve the production MCP surface
and regulatory behavior while making prompt verification deterministic,
improving gateway-aware diagnostics, and retaining exact canonical citations.

### In scope

- Direct FastMCP registration/rendering tests for the affected prompts.
- Explicit prompt-case instructions in the Pi eval runner.
- Structured tool-list and gateway-envelope diagnostics that reject prose.
- Exact-citation preservation for RES-01.
- Focused regression tests and one serial agent-eval closure run.

### Out of scope

- Changes to soil-query algorithms, SDA/TIGERweb/NASS clients, or regulatory
  scoring logic.
- Converting MCP prompts into duplicate tools.
- A new generic MCP client implementation inside the eval runner.
- Live USDA network tests; these remain deferred because the failures are
  harness/prompt behavior issues.
- Changes to public production privacy, payload schemas, or dependency
  manifests.

### Verbatim constraints

- “copy that into planning and prepare for /plan-wave to resolve these issues”
- “recommended”
- “exact-citations”
- “direct-render-plus-pi”
- “three”
- “recommended” (offline + focused eval + Ruff + diff check + serial agent_eval)

## Recon Log

- Current plan number is 30; prior completed orchestration is 29.
- Entry points: `src\fpac_soil_mcp\app.py` (54 lines), `eval\run_evals.py`
  (879 lines), `eval\test_agent_eval.py` (1181 lines), and
  `tests\test_server.py` (389 lines).
- Baseline: `uv run pytest -m "not live_network and not agent_eval" -q`
  passed 314 tests with 14 deselected; focused eval tests passed 28 with 2
  deselected; Ruff check passed; Ruff format check passed.
- Worktree contains an unrelated modified `Makefile`; workers must not touch it.
- `AGENTS.md` requires mocked tests by default, centralized regulatory
  notices, FastMCP registration through `app.create_mcp_server()`, and no
  live tests in the default path.
- Accepted ADR-0001 requires FastMCP with centralized modular registration.
  ADR-0003 requires preliminary-screening authority boundaries and citations.
  ADR-0011 requires mocked default/live opt-in test architecture. No ADR is
  superseded by this plan.
- Existing reference implementations: prompt registration/render assertions
  in `tests\test_server.py`; nested Pi envelope parsing in
  `eval\run_evals.py:262-291`; current evaluator fixtures under
  `eval\fixtures\event_capture\`.
- Same-file work is serialized. Maximum three concurrent workers is allowed.
- Pi/agent-eval uses stdio and must be run serially; no shared HTTP port is
  needed for the targeted closure run.

## Decision Log

| Date | Decision |
|---|---|
| 2026-10-19 | Order work as prompt protocol/content, then runner diagnostics, then regression/closure. |
| 2026-10-19 | Preserve exact canonical RES-01 citation matching; do not weaken to fuzzy global matching. |
| 2026-10-19 | Use direct FastMCP `list_prompts()`/`render_prompt()` tests plus Pi downstream behavior; do not add a second MCP client path to the runner. |
| 2026-10-19 | Permit up to three concurrent workers, but serialize shared-file work. |
| 2026-10-19 | Require offline suite, focused eval suite, Ruff, `git diff --check`, and one serial `agent_eval` run; defer live network tests. |

## Wave / Dependency Table

| Wave | Tasks | Depends on | Purpose |
|---|---|---|---|
| 1 | 30.1.1 | none | Add direct prompt-render coverage. |
| 2 | 30.2.1 | 30.1.1 | Make prompt-case execution explicit, preserve exact RES-01 citations, and improve structured discovery diagnostics. |
| 3 | 30.3.1 | 30.2.1 | Add evaluator regressions for prompt instructions, envelopes, diagnostics, and citation matching. |
| 4 | 30.4.1 | 30.3.1 | Update operational documentation and run serial closure verification. |

## Hazards

- `eval\run_evals.py` and `eval\test_agent_eval.py` are large and must be
  entered through named anchors, not read wholesale by workers.
- Prompt tests must use FastMCP prompt APIs, not tool-list assertions.
- Do not count prompt names or tool names found only in prose as structured
  invocation evidence.
- Gateway envelope support must remain bounded to structured fields and known
  wrappers; arbitrary recursive text scanning risks false positives.
- Exact citation matching is intentional. Any fixture adjustment must retain
  canonical `7 CFR Part 657` and `7 CFR Part 658` coverage.
- The current modified `Makefile` is unrelated and must remain untouched.
- Agent-eval can require Pi/provider/network availability; run it once,
  serially, after offline gates pass, and record a clear environmental block
  if unavailable.

## Task Specifications

### 30.1.1 — Adding direct prompt-render regression coverage

- **Repo:** `D:\workspace\fpac-soil-mcp`
- **Files in scope:** must edit `tests\test_server.py`; may create
  `planning\tasks\30.1.1.todo.md`; may append a report to
  `planning\STATE_30.md`; no runtime or eval-runner files.
- **Depends on:** none.
- **Spec:** Add deterministic tests using the existing `create_mcp_server()`,
  `list_prompts()`, and `render_prompt()` patterns. Cover
  `fppa_screening_assistant` with point arguments and assert the point tool,
  screening language, and canonical regulatory boundary. Cover
  `fppa_corridor_screening_assistant` with representative corridor arguments
  and assert `analyze_corridor_fppa`, `7 CFR § 658.5(c)`, CPA-106 guidance,
  the 160-point threshold, and the preliminary limitation. Do not convert
  prompts into tools.
- **Do not touch:** `eval\run_evals.py`, `eval\test_agent_eval.py`,
  `eval\prompt_test_cases.json`, production prompt source, dependencies,
  `Makefile`, or live tests.
- **Grep anchors/reference:** existing prompt registration/list tests and
  render assertions around `tests\test_server.py:68-76,120-213`.
- **Acceptance:** focused server tests pass and demonstrate prompt
  registration/content independently of Pi.
- **Targeted command:** `uv run pytest tests\test_server.py -q`

### 30.2.1 — Making prompt execution and gateway diagnostics explicit

- **Repo:** `D:\workspace\fpac-soil-mcp`
- **Files in scope:** must edit `eval\run_evals.py`; may create
  `planning\tasks\30.2.1.todo.md`; may append a report to
  `planning\STATE_30.md`; no tests or production source.
- **Depends on:** 30.1.1.
- **Spec:** Add a prompt-case command builder or equivalent narrow logic so
  `target_type == "prompt"` explicitly tells Pi to invoke/render the named
  MCP prompt before answering. Preserve existing behavior for tool/resource
  cases. Improve advertised-tool extraction and diagnostics for the verified
  Pi/gateway structured envelopes while rejecting prose and arbitrary text.
  Keep the existing nested `mcpScript` support and direct-call matching.
  Distinguish prompt discovery, tool-list discovery, unadvertised tools, and
  advertised-but-not-executed tools in diagnostics. Do not call FastMCP
  internals from this runner. Preserve RES-01's exact expected keywords
  `7 CFR Part 657`, `7 CFR Part 658`, and `preliminary`; if wording is
  clarified, use an explicit instruction to retain those citations rather
  than broadening the matcher.
- **Do not touch:** `eval\test_agent_eval.py`, `eval\prompt_test_cases.json`,
  `src\`, README, ADRs, dependencies, `Makefile`, or raw artifacts.
- **Grep anchors/reference:** `normalize_text` and extraction helpers around
  `eval\run_evals.py:251-460`; command construction around `478-513`;
  result/diagnostic handling around `637-658`; nested `mcpScript` parsing
  around `262-291`.
- **Acceptance:** prompt cases receive explicit render/invoke instructions;
  direct and nested structured calls remain recognized; prose does not count;
  diagnostics no longer collapse every unknown envelope into a false server
  configuration claim; RES-01 still requires the three exact keywords; named
  regression tests in 30.3.1 cover each new distinction.
- **Targeted command:** `uv run pytest eval\test_agent_eval.py -m "not agent_eval" -q`

### 30.3.1 — Adding eval regressions for the three failures

- **Repo:** `D:\workspace\fpac-soil-mcp`
- **Files in scope:** must edit `eval\test_agent_eval.py`; may add or update
  only sanitized fixtures under `eval\fixtures\event_capture\`; may create
  `planning\tasks\30.3.1.todo.md`; may append a report to
  `planning\STATE_30.md`.
- **Depends on:** 30.2.1.
- **Spec:** Add focused mocked tests for prompt-case instruction generation,
  exact RES-01 citation matching, the verified gateway/tool-list envelopes,
  prose exclusion, and differentiated diagnostics. Test that PROMPT-01
  explicitly names and renders/invokes `fppa_screening_assistant`, then still
  requires the point tool. Test that PROMPT-02 explicitly names and
  renders/invokes `fppa_corridor_screening_assistant`, preserves
  `7 CFR § 658.5(c)`, CPA-106 guidance, and the preliminary limitation, and
  remains guidance-only without executable geometry. Use sanitized synthetic
  events; never add raw Pi session data, provider metadata, encrypted
  reasoning, or unredacted location payloads.
- **Do not touch:** `eval\run_evals.py`, production source, prompt dataset
  semantics, live tests,
  dependencies, README, ADRs, or `Makefile`.
- **Grep anchors/reference:** helper/import section and advertisement tests
  around `eval\test_agent_eval.py:1-120`; capture fixtures/tests around
  `eval\test_agent_eval.py:99-220,735-816`; sanitized fixtures under
  `eval\fixtures\event_capture\`.
- **Acceptance:** named tests cover prompt instruction/render evidence for both
  prompt cases, the exact RES-01 citation contract, each gateway diagnostic
  distinction, and prose exclusion; focused eval tests pass; prose cannot
  substitute for structured invocation; exact citation matching remains
  enforced.
- **Targeted command:** `uv run pytest eval\test_agent_eval.py -m "not agent_eval" -q`

### 30.4.1 — Documenting operation and running closure gates

- **Repo:** `D:\workspace\fpac-soil-mcp`
- **Files in scope:** must edit the eval section of `README.md`; may create
  `planning\tasks\30.4.1.todo.md`; no runtime/test changes.
- **Depends on:** 30.3.1.
- **Spec:** Document that prompt cases require MCP prompt rendering, that
  direct FastMCP tests and Pi downstream tests serve different purposes, that
  exact regulatory citations are intentional, and that gateway diagnostics
  distinguish structured evidence from prose. Then run closure checks serially:
  offline project suite, focused eval suite, Ruff check, Ruff format check,
  `git diff --check`, and one `uv run pytest -m agent_eval -q` run. The
  orchestrator owns and runs these global/serial closure commands after worker
  changes are merged; the worker only edits README and reports the required
  command checklist. The orchestrator records exact results and environmental
  blocks in `STATE_30.md`. Do not alter the unrelated `Makefile`.
- **Do not touch:** `eval\run_evals.py`, `eval\test_agent_eval.py`,
  `eval\prompt_test_cases.json`, `src\`, ADRs, dependencies, or raw artifacts.
- **Grep anchors/reference:** README MCP prompt/testing sections; `AGENTS.md`
  validation commands; `planning\STATE_29.md` closure format.
- **Acceptance:** README matches implementation. After the worker change is
  merged, the orchestrator must run and record all six closure gates:
  `uv run pytest -m "not live_network and not agent_eval" -q`,
  `uv run pytest eval\test_agent_eval.py -m "not agent_eval" -q`,
  `uv run ruff check .`, `uv run ruff format --check .`,
  `git diff --check`, and serial `uv run pytest -m agent_eval -q` (or a
  clearly recorded environmental block). The orchestrator records closure
  results in `planning\STATE_30.md`; no raw artifacts are tracked.
- **Targeted command:** `uv run pytest -m "not live_network and not agent_eval" -q`

## Review Status

Two independent reviews completed on 2026-10-19. The current research artifact
records three failures from the 20-case run (`RES-01`, `PROMPT-01`, and
`PROMPT-02`); the older four-case observability gap is historical and
superseded, so it is not added to this remediation scope. The current
post-commit working-tree baseline is authoritative for this orchestration:
316 offline tests passed, 12 deselected, and 28 focused eval tests passed with
2 deselected. The revised plan has been approved for execution.
