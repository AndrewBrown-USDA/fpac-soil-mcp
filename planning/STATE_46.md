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
- **Addendum opened:** 2026-11-10, at user request; original Waves 1-5 remain
  closed and their final validation record is unchanged.

## Wave board

| Wave | Task | Status |
|---|---|---|
| 1 | 46.1.1 Harden prompt policy | done |
| 1 | 46.1.2 Add policy assertions | done |
| 1 | gate prompt policy | done |
| 2 | 46.2.1 Add adversarial corpus | done |
| 2 | 46.2.2 Add deterministic scorers | done |
| 2 | gate adversarial evaluation | done |
| 3 | 46.3.1 Harden MCP contracts | done |
| 3 | 46.3.2 Preserve map semantics | done |
| 3 | gate MCP/map safety | done |
| 4 | 46.4.1 Instrument benchmarks | done |
| 4 | 46.4.2 Run performance evidence | done |
| 4 | gate Criterion 2 evidence | pass with limits |
| 5 | 46.5.1 Synchronize documentation | done |
| 5 | gate final validation | pass with limits |
| 6 | 46.6.1 Correct unavailable SA completion status | done |
| 6 | 46.6.2 Characterize DB45-E3 judge/null behavior | done |
| 6 | gate PR #83 follow-ups | pass |
| 7 | 46.7.1 Migrate Pi eval to built-in MCP | done |
| 7 | gate Pi native-MCP contract | pass |
| 8 | 46.8.1 Re-test Pi auth and evaluation | done |
| 8 | 46.8.2 Diagnose representative Pi evaluation failures | done |
| 8 | gate Pi auth/evaluation evidence | fail; 14 of 38 cases failed |

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
- **Commit:** `00f7e8f` (`test(eval): add adversarial safety case corpus`); dependencies: Wave 1 prompt-policy gate passed.
- **Deviations/gotchas:** `evalCases.js` needed no change because the existing deterministic mapping accepts the new cases; all examples are synthetic.

## 46.2.2
- **Status:** done.
- **Files:** common matcher/tests (87-158, 85-130); Databricks scorers/tests (26-38, 201-290; tests 140-195); harness assertions/tests (30-120; tests 76-118); Pi runner/tests (23-32, 530-595, 908-950; tests 250-350); task TODO.
- **Validation:** `PYTHONPATH=apps\agent-fpac-soil-openai-sdk;eval uv run pytest eval\common eval\databricks\test_databricks_scorers.py eval\pi\test_agent_eval.py -q` — 163 passed, 2 deselected; harness `npm test` — 13 passed; `npm run check`, Ruff, and `git diff --check` passed.
- **Commit:** `62a2286` (`feat(eval): score safety and reliability behavior`); dependency 46.2.1 passed and committed.
- **Deviations/gotchas:** Pi reports semantic status separately from runner health status; Databricks retry scoring counts repeated identical tool calls as retries, and latency scoring requires trace timing.

## 46.2.2 Follow-up
- **Status:** done; corrected stale Databricks dry-run assertions exposed by final validation.
- **Files:** `eval\databricks\test_databricks_runner.py` (17, 49, 63); `planning\tasks\46.2.2-followup.todo.md`.
- **Validation:** `uv run pytest eval\databricks\test_databricks_runner.py -q` — 5 passed.
- **Commit:** `94dd6c8` (`test(eval): refresh Databricks dry-run assertions`); dependency 46.2.2 committed as `62a2286`.
- **Deviations/gotchas:** use the full deterministic scorer list and shared dataset loader to avoid stale expectations.

## Wave 2 Gate
- **Status:** pass; adversarial corpus loads deterministically and semantic/reliability scorers pass focused Python and harness tests.
- **Exact tests:** `uv run pytest eval\common eval\contract -q` — 116 passed; Python scorer suite — 163 passed, 2 deselected; harness `npm test` — 13 passed; `npm run check` passed.
- **Dependency confirmation:** 46.2.1 completed before 46.2.2; Wave 2 dependencies for Wave 3 are satisfied.

## 46.3.1
- **Status:** done.
- **Files:** `src\fpac_soil_mcp\models.py` (51-156); `tools\lesa_tools.py` (171-410); `tools\soil_lookup_tools.py` (44-340); `tools\spatial_analysis_tools.py` (32-155); `tests\test_models.py` (new cases); `tests\test_tools.py` (new cases); `eval\contract\test_contract.py` (120-274); `planning\evidence\46.3.1-tool-surface-review.md`; task TODO.
- **Validation:** `uv run pytest tests\test_tools.py tests\test_models.py tests\test_server.py eval\contract\test_contract.py -q` — 83 passed, 3 deselected; Ruff check/format and `git diff --check` passed.
- **Commit:** `0000eef` (`feat(mcp): validate public tool contracts`); prompt-policy gate 46.1 passed.
- **Deviations/gotchas:** tool surface inventory covers all ten public tools; no wrapper was deferred.

## 46.3.2
- **Status:** done.
- **Files:** app `agent_server\geo.py` (29-440); map `farmlandClasses.ts` (3-114); `tests\test_geo_screen.py` (261-300); `tests\test_geo_map.py` (33-151); task TODO.
- **Validation:** `make app-check` — 177 passed; targeted map tests — 59 passed; Ruff and `git diff --check` passed.
- **Commit:** `b50e30a` (`fix(app): preserve map classification uncertainty`); adversarial corpus gate 46.2 passed.
- **Deviations/gotchas:** map-only calls remain geometry-free/untraced and statuses stay bounded; frontend bundle check was not run because only Node v26 is available while the app requires Node 22.

## Wave 3 Gate
- **Status:** pass; MCP contract tests and map uncertainty/privacy checks pass.
- **Exact tests:** `uv run pytest tests\test_tools.py tests\test_models.py tests\test_server.py eval\contract\test_contract.py -q` — 83 passed, 3 deselected; `make app-check` — 177 passed.
- **Dependency confirmation:** 46.3.1 follows prompt-policy gate 46.1; 46.3.2 follows adversarial corpus gate 46.2.

## 46.4.1
- **Status:** done.
- **Files:** `eval\criterion2_benchmark.py` (1-300); `tests\test_criterion2_benchmark.py` (1-126); `tests\fixtures\criterion2_benchmark.v1.json` (1-158); `Makefile` (11, 19, 70-72); task TODO.
- **Validation:** `uv run pytest tests\test_criterion2_benchmark.py -q` — 7 passed; one-run manifest dry run emitted all four fixtures and full aggregate schema; Ruff, format, and `git diff --check` passed.
- **Commit:** `353ee0a` (`feat(eval): instrument Criterion 2 benchmarks`); adversarial evaluation and MCP/map safety gates passed.
- **Deviations/gotchas:** dry-run labels outcomes unmeasured; exact fixture arguments are preserved, and concurrent runs do not claim per-case tracemalloc memory.

## 46.4.2
- **Status:** done; evidence documents manifest scheduling only because service measurements were unavailable.
- **Files:** `planning\evidence\46.4.2-performance.md` (1-48); `planning\evidence\46.4.2-performance.json` (run `20261110T144926Z`, 20 case records); task TODO.
- **Validation:** five-run, two-worker dry run with committed manifest `criterion2-benchmark-fixtures.v1`; four fixtures and six county FIPS values; JSON schema and `git diff --check` passed.
- **Commit:** `e75de91` (`docs(eval): record Criterion 2 performance evidence`); dependency 46.4.1 committed as `353ee0a`.
- **Deviations/gotchas:** `MCP_URL` absent, so deployed HTTP was not attempted; `pi auth check --model gpt-5.6-luna --json --no-refresh` returned `invalid_state`, so `make test-eval` was not run. Latency/failure/retry metrics remain null.

## Wave 4 Gate
- **Status:** pass with environment limitations; reproducible manifest evidence is complete, but there are no observed service-performance or model-assisted results.
- **Exact evidence run:** `uv run python eval\criterion2_benchmark.py --fixture-manifest tests\fixtures\criterion2_benchmark.v1.json --runs 5 --max-workers 2 --output planning\evidence\46.4.2-performance.json`; dry-run per-case and aggregate measured outcomes are null.
- **Dependency confirmation:** task 46.4.2 consumed the canonical manifest from committed task 46.4.1; Waves 2 and 3 gates passed.

## 46.5.1
- **Status:** done; synchronized evaluation, planning, and submission documentation with explicit evidence limits and deferrals.
- **Files:** `planning\GOALS.md`, `planning\MASTER_PLAN.md`, `README.md`, `eval\databricks\README.md`, `apps\agent-fpac-soil-openai-sdk\README.md`, `eval\fpac_soil_mcp_harness\README.md`, `planning\evidence\46.5.1-closeout.md`, task TODO.
- **Validation:** local Markdown links and `git diff --check` passed; `make check` — 843 passed, 45 deselected; `make app-check` — 177 passed.
- **Commit:** `94d740d` (`docs(eval): synchronize safety evaluation guidance`); dependency Wave 4 Criterion 2 evidence gate passed with limitations.
- **Deviations/gotchas:** `make test-eval` was not run after the unqualified Pi model auth check returned `invalid_state`; no model-assisted or deployed performance result is claimed.

## Wave 5 Final Validation Gate
- **Status:** pass with limits; serial offline checks passed, Pi model-assisted evaluation remains unavailable.
- **Exact commands:** `make check` — 843 passed, 45 deselected; then `make app-check` — 177 passed. At that closeout, `make test-eval` was not run after `pi auth check --model gpt-5.6-luna --json --no-refresh` returned `invalid_state`; the model was unqualified.
- **Evidence:** `planning\evidence\46.5.1-closeout.md`; stale Databricks dry-run assertions corrected in commit `94dd6c8`.
- **Dependency confirmation:** Waves 2, 3, and 4 gates are complete; Wave 5 documentation is synchronized.

## 46.6.1
- **Status:** done; unavailable criteria keep no-input Site Assessment incomplete.
- **Files:** `src\fpac_soil_mcp\lesa.py` (765-769); `tests\test_lesa.py` (508-535); task TODO.
- **Validation:** `uv run pytest tests\test_lesa.py -q` — 47 passed; `git diff --check` passed.
- **Commit:** `c685536` (`fix(lesa): preserve incomplete status for unavailable criteria`); dependency 46.3.1 gate passed.
- **Deviations/gotchas:** Criterion 7's machine estimate remains, but does not make the other unavailable criteria complete.

## 46.6.2
- **Status:** done; DB45-E3 is characterized with a synthetic contract fixture, not an exact reproduction of the judge event.
- **Files:** Databricks scorer tests (228-246); phase-4 contract test (135-143); `planning\evidence\46.6.2-judge-followup.md`; task TODO.
- **Validation:** scorer/contract tests — 20 passed; offline Pi tests — 36 passed, 2 deselected; Ruff, format, and `git diff --check` passed.
- **Commit:** `1c745d5` (`test(eval): characterize DB45-E3 judge limitations`); dependency Wave 2 gate passed.
- **Deviations/gotchas:** Existing rubric was not retuned; null judge scores mean absent case-grounded expectations, not pass or fail.

## Wave 6 PR #83 Follow-up Gate
- **Status:** pass; DB45-10 status semantics are fixed and DB45-E3/null expectations have offline contract coverage.
- **Exact combined command:** `uv run pytest tests\test_lesa.py eval\databricks\test_databricks_scorers.py tests\eval\test_phase4_databricks_contract.py eval\pi\test_agent_eval.py -m "not agent_eval" -q` — 103 passed, 2 deselected.
- **Lint/format:** Ruff check and format check passed for all changed Python files; `git diff --check` passed.
- **Dependency confirmation:** completed 46.3.1 and Wave 2 gates; no WKT/DB45-E4 work included per user direction.

## 46.7.1
- **Status:** done; Pi runner now uses temporary project `.pi\mcp.json` with the built-in MCP support and `--approve`.
- **Files:** `eval\pi\run_evals.py` (250-253, 609-620); `eval\pi\test_agent_eval.py` (263-305, 1100-1127, 1190-1205); task TODO.
- **Validation:** `uv run pytest eval\pi\test_agent_eval.py -m "not agent_eval" -q` — 38 passed, 2 deselected; Ruff, format, and `git diff --check` passed.
- **Commit:** `eef05f2` (`fix(eval): use Pi built-in MCP configuration`); dependency 46.5 final-validation gate passed.
- **Deviations/gotchas:** no global Pi configuration or credentials touched; built-in config is limited to the temporary runner sandbox.

## Wave 7 Pi Native-MCP Gate
- **Status:** pass; offline runner contract now matches Pi 1.5.2's project-local MCP configuration.
- **Exact command:** `uv run pytest eval\pi\test_agent_eval.py -m "not agent_eval" -q` — 38 passed, 2 deselected; Ruff and format passed.
- **Dependency confirmation:** completed Wave 5 final-validation gate; Wave 8 runtime/auth evidence can proceed.

## 46.8.1
- **Status:** done; catalog-qualified auth is ready and POINT-01 passed, but the full Pi evaluation failed 14 of 38 cases.
- **Evidence:** `planning\evidence\46.8.1-pi-auth-eval.md`; task checklist `planning\tasks\46.8.1.todo.md`.
- **Exact commands/results:** qualified `pi auth check` — ready with OAuth; POINT-01 runner — 1 passed; `make test-eval` — 24 passed, 14 failed (exit 2).
- **Artifact review:** the external store contains only older 20-case runs from 2026-10-19 and 2026-10-21; the 2026-11-10 run directory was removed before its contents were reviewed. Failure causes are unavailable; no evaluation was rerun for review.
- **Diagnostic note:** POINT-01's `recognized` classification is implied by PASS and its expected structured tool, but was not emitted. `outcome=unknown` is the CLI fallback because attempt metadata omits `outcome`.
- **Deviations/gotchas:** no credentials, prompts, coordinates, geometry, responses, or raw artifacts retained.

## 46.8.2
- **Status:** done; five failed cases rerun individually, and no rerun passed.
- **Files:** Pi status extraction and focused regression test; `planning\evidence\46.8.2-pi-failure-diagnostics.md`; task checklist; execution plan and state.
- **Exact runs:** five individual runner commands with `--capture-artifacts`, qualified model, and `--no-show-output`; each returned FAIL with code 0; see evidence report.
- **Validation:** offline Pi tests — 39 passed, 2 deselected; Ruff check/format and `git diff --check` passed.
- **Commit:** `7817c28` (`fix(eval): ignore MCP progress in case status`); dependency 46.8.1 evidence recorded.
- **Artifacts:** retained outside repo at `D:\workspace\fpac-soil-mcp-eval-artifacts\diagnostics-20261110T1552Z`; raw files remain uncommitted.
- **Deviations/gotchas:** fixed status extraction of transient MCP call statuses; no live case rerun because focused regression test covers the parser defect. Nine original failures remain undiagnosed.

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
- **Pi built-in MCP follow-up:** Pi 1.5.2 is installed. The unqualified
  `pi auth check --model gpt-5.6-luna --json --no-refresh` returned `invalid`,
  but the catalog-qualified `pi auth check --model
  github-copilot/gpt-5.6-luna --json --no-refresh` returned `ready` with OAuth.
  Wave 7 migrated the runner; Wave 8 verified POINT-01 and the full evaluation
  had 14 failures. Five selected cases were rerun and diagnosed in
  `planning\evidence\46.8.2-pi-failure-diagnostics.md`; nine failures remain
  undiagnosed. Do not treat the selected reruns as a full evaluation.
- **Map persistence, multiple AOIs, custom basemaps, and other M2/M4 work:**
  deferred until the current map contract and safety gate are stable.

## Gate Evidence Scaffold

| Gate | Status | Exact command | Counts/artifact | Dependency confirmation |
|---|---|---|---|---|
| Prompt policy | pass | targeted prompt/app/Pi/common pytest: 151 passed, 2 deselected; Ruff check/format pass | `64a0e3b`, `c92e462` | both Wave 1 tasks verified |
| Adversarial evaluation | pass | dataset: 116 passed; scorer Python: 163 passed, 2 deselected; harness: 13 passed; check passed | `00f7e8f`, `62a2286` | 46.2.1 then 46.2.2 verified |
| MCP/map safety | pass | MCP contract pytest: 83 passed, 3 deselected; app-check: 177 passed; targeted map: 59 passed | `0000eef`, `b50e30a` | both dependencies verified; frontend bundle unavailable under installed Node v26 |
| Criterion 2 evidence | pass with limits | five-run/two-worker manifest dry run; 20 slots, 4 fixtures, 6 counties; external/model metrics unavailable | `353ee0a`, `e75de91` | 46.4.1 and 46.4.2 verified |
| Final validation | pass with limits | `make check`: 843 passed, 45 deselected; `make app-check`: 177 passed; `make test-eval` not run at closeout after unqualified model check returned invalid | `94dd6c8`, `planning\evidence\46.5.1-closeout.md` | Waves 2-4 and documentation task verified |
| PR #83 deferred work | pass | DB45-10 fixed; DB45-E3/null expectations characterized; DB45-E4/WKT excluded per user direction | `c685536`, `1c745d5`, `planning\evidence\46.6.2-judge-followup.md` | Waves 2-3 complete |
| Pi native MCP | pass | Pi 1.5.2 runner uses built-in MCP; qualified GitHub Copilot auth is ready | `eef05f2`, `planning\evidence\46.8.1-pi-auth-eval.md` | 46.7.1 verified before 46.8.1 |
| Pi auth/evaluation | fail; 14 cases failed | POINT-01 passed; `make test-eval`: 24 passed, 14 failed; five representative failures rerun; nine causes remain unknown | `planning\evidence\46.8.1-pi-auth-eval.md`, `planning\evidence\46.8.2-pi-failure-diagnostics.md` | Wave 7 native-MCP gate passed; 46.8.1 recorded |
