# Orchestration 46 State

## Baseline

- **Repository:** `D:\workspace\fpac-soil-mcp`
- **Branch:** `planning/agent-safety-eval`
- **Plan date:** 2026-11-09
- **Offline baseline:** `uv run pytest -q -m "not live_network and not agent_eval"` ->
  764 passed, 45 deselected, 181 warnings.
- **Required gates:** targeted tests per task; final `make check`,
  `make app-check`, `make test-eval`; deployed measurements opt-in.
- **Active constraints:** ADR 0002, 0003, 0011, 0012, 0014, 0015, 0016, 0017.
- **Concurrency limit:** two workers maximum; shared gates run serially.

## Wave board

| Wave | Task | Status |
|---|---|---|
| 1 | 46.1.1 Harden prompt policy | done |
| 1 | 46.1.2 Add policy assertions | done |
| 1 | gate prompt policy | done |
| 2 | 46.2.1 Add adversarial corpus | done |
| 2 | 46.2.2 Add deterministic scorers | done |
| 2 | gate adversarial evaluation | done |
| 3 | 46.3.1 Harden MCP contracts | pending |
| 3 | 46.3.2 Preserve map semantics | pending |
| 3 | gate MCP/map safety | pending |
| 4 | 46.4.1 Instrument benchmarks | pending |
| 4 | 46.4.2 Run performance evidence | pending |
| 4 | gate Criterion 2 evidence | pending |
| 5 | 46.5.1 Synchronize documentation | pending |
| 5 | gate final validation | pending |

## Task Reports

<!-- Append one report per task, maximum 15 lines. -->

## 46.1.1
- **Status:** done; worker lost its completion connection after edits, so orchestrator verified the delivered diff and acceptance tests.
- **Files:** app system prompt `7-19`; Databricks v1/v2 `7-19`; FastMCP prompt module `8-17, 62, 96, 128, 171`; `planning\tasks\46.1.1.todo.md`.
- **Validation:** combined targeted command recorded below: 151 passed, 2 deselected; Ruff check and format check passed.
- **Commit:** `64a0e3b` (`feat(prompts): enforce FPPA safety policy`); dependencies: none.
- **Deviations/gotchas:** none; live prompt contains no named tools.

## 46.1.2
- **Status:** done.
- **Files:** policy contract `1-149`; matching helper `16-70`; matching tests `17-121`; FastMCP tests `1-53`; app tests `7, 83-84`; Pi runner `31, 470-505, 549-555, 674-681`; Pi tests `26, 100-130, 1122-1129`; `planning\tasks\46.1.2.todo.md`.
- **Validation:** combined targeted command recorded below: 151 passed, 2 deselected; Ruff check and format check passed.
- **Commit:** `c92e462` (`test(eval): assert FPPA safety policy surfaces`); dependencies: none.
- **Deviations/gotchas:** required dimensions are individually asserted; use `PYTHONPATH=apps\agent-fpac-soil-openai-sdk;eval` for the root pytest process.

## Wave 1 Gate
- **Status:** pass; both tasks verified, and shared policy version/rule coverage matches the native prompts.
- **Exact tests:** `$env:PYTHONPATH = "apps\agent-fpac-soil-openai-sdk;eval"; uv run pytest tests\test_prompts.py eval\databricks\test_databricks_agent.py apps\agent-fpac-soil-openai-sdk\tests\test_agent_config.py eval\pi\test_agent_eval.py eval\common\test_common_matching.py -q` — 151 passed, 2 deselected.
- **Lint/format:** `uv run ruff check apps\agent-fpac-soil-openai-sdk\tests\test_agent_config.py eval\common\matching.py eval\common\test_common_matching.py eval\pi\run_evals.py eval\pi\test_agent_eval.py src\fpac_soil_mcp\prompts\fppa_prompts.py tests\test_prompts.py` and corresponding `uv run ruff format --check` — passed.
- **Dependency confirmation:** both wave-1 tasks have no prerequisites; wave 2's `46.1` gate dependency is satisfied.

## 46.2.1
- **Status:** done.
- **Files:** `eval\common\dataset.py` (42-71, 165-195, 333-339); `eval\common\test_common_dataset.py` (72-137); `eval\prompt_test_cases.json` (2, 803-912); `eval\eval_cases.v1.json` (2, 99-192); `planning\EXECUTION_PLAN_46.md` (table row 110, task scope); task TODO.
- **Validation:** `uv run pytest eval\common eval\contract -q` — 116 passed; Ruff check, format check, and `git diff --check` passed.
- **Commit:** pending; dependencies: Wave 1 prompt-policy gate passed.
- **Deviations/gotchas:** `evalCases.js` needed no change because the existing deterministic mapping accepts the new cases; all examples are synthetic.

## 46.2.2
- **Status:** done.
- **Files:** common matcher/tests (87-158, 85-130); Databricks scorers/tests (26-38, 201-290; tests 140-195); harness assertions/tests (30-120; tests 76-118); Pi runner/tests (23-32, 530-595, 908-950; tests 250-350); task TODO.
- **Validation:** `PYTHONPATH=apps\agent-fpac-soil-openai-sdk;eval uv run pytest eval\common eval\databricks\test_databricks_scorers.py eval\pi\test_agent_eval.py -q` — 163 passed, 2 deselected; harness `npm test` — 13 passed; `npm run check`, Ruff, and `git diff --check` passed.
- **Commit:** pending; dependency 46.2.1 passed and committed.
- **Deviations/gotchas:** Pi reports semantic status separately from runner health status; Databricks retry scoring counts repeated identical tool calls as retries, and latency scoring requires trace timing.

## Wave 2 Gate
- **Status:** pass; adversarial corpus loads deterministically and semantic/reliability scorers pass focused Python and harness tests.
- **Exact tests:** `uv run pytest eval\common eval\contract -q` — 116 passed; Python scorer suite — 163 passed, 2 deselected; harness `npm test` — 13 passed; `npm run check` passed.
- **Dependency confirmation:** 46.2.1 completed before 46.2.2; Wave 2 dependencies for Wave 3 are satisfied.

## Gate Evidence Convention

Each completed task/gate entry must record: status, exact command, pass/fail
counts, changed files or evidence artifact, commit/artifact identifier, and
dependency confirmation. A dependent task may not leave `pending` until its
prerequisite gate has an explicit passing entry.

## Deferred / Blocked

- **PR #79/CDL-dependent adjacency work:** deferred until PR #79 is merged,
  validated, and an authoritative adjacency source is approved.
- **Deployed `/mcp` measurements:** blocked when credentials, deployment, or
  upstream services are unavailable; record explicit unavailable fields rather
  than substituting local timings.
- **Map persistence, multiple AOIs, custom basemaps, and other M2/M4 work:**
  deferred until the current map contract and safety gate are stable.

## Gate Evidence Scaffold

| Gate | Status | Exact command | Counts/artifact | Dependency confirmation |
|---|---|---|---|---|
| Prompt policy | pass | targeted prompt/app/Pi/common pytest: 151 passed, 2 deselected; Ruff check/format pass | `64a0e3b`, `c92e462` | both Wave 1 tasks verified |
| Adversarial evaluation | pass | dataset: 116 passed; scorer Python: 163 passed, 2 deselected; harness: 13 passed; check passed | pending | 46.2.1 then 46.2.2 verified |
| MCP/map safety | pending | - | - | - |
| Criterion 2 evidence | pending | - | - | - |
| Final validation | pending | - | - | - |
