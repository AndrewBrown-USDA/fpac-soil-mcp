# EXECUTION PLAN 46: Agent Safety, Evaluation, and Reliability Contract

## Goal & Scope

**Goal:** Make the FPAC Soil agent robust to Criterion 2 (server
performance/reliability) and Criterion 3 (MCP design), while enforcing the
preliminary FPPA boundary. The live agent, FastMCP prompts, Pi/Databricks
evaluations, and map app must refuse unrelated work, avoid official/legal
claims, preserve uncertainty, and never turn “not prime farmland” into a
siting or suitability recommendation. The plan also produces reproducible
evaluation setup/results evidence.

**In scope:**

- Native prompt copies for the live app, FastMCP, Pi, and Databricks surfaces,
  synchronized through a policy version and shared required-rule tests.
- Refusal of unrelated requests and official-determination requests.
- Neutral comparison only for supplied alternatives; no siting, relocation,
  footprint, route, alignment, mitigation, or design recommendations.
- Explicit rules for non-prime, conditional classes, urban screening, LESA,
  unknown/unmapped/partial/unavailable states, tool failure, and prompt
  injection.
- Adversarial evaluation cases and deterministic semantic/status/provenance
  scorers.
- Map summary/rendering safeguards for unknown and unrecognized classifications.
- Strict public MCP input contracts and structured failure semantics where
  required by the safety/evaluation contract.
- Criterion 2 latency, retry, failure, memory, stability, bounded-concurrency,
  and deployed-transport evidence.
- Planning and submission documentation.

**Out of scope:**

- Official FPPA/NRCS determinations, legal advice, signed forms, exemptions,
  approvals, or preferred alternatives.
- New agricultural-land adjacency sources before PR #79/CDL work and source
  approval are complete.
- Broad frontend redesign, map persistence, multiple AOIs, or custom basemaps.
- Runtime cross-project prompt imports or new prompt-generation dependencies.
- Making live-network tests part of the default offline gate.

**Verbatim constraints:**

- “currently the agent will not refuse unrelated non-FPPA tasks”
- “we also want to be sure that the agent does not overinterpret output like
  try to suggest moving projects to non-prime farmlands”
- Criterion 2 requires documenting “how they tested the server, what inputs
  were used, and how the server performed”
- Criterion 3 requires Pydantic validation, precise tool descriptions, and
  meaningful agent-facing actions rather than thin REST wrappers.
- “safety-first”
- “all four”
- “native-copies-tested”
- “2”
- “recommended”

## Reconnaissance Log

- Repository: `D:\workspace\fpac-soil-mcp`.
- Current branch for this planning work: `planning/agent-safety-eval`.
- Offline baseline: `uv run pytest -q -m "not live_network and not agent_eval"` ->
  **764 passed, 45 deselected**, with existing asyncio and Shapely/MLflow
  warnings.
- Key file sizes: `fppa_prompts.py` 12,258 bytes; `spatial_analysis_tools.py`
  9,497; `models.py` 29,730; `scorers.py` 8,259; `run_evals.py` 36,456;
  app `geo.py` 17,337; live prompt 796 bytes.
- Required conventions: root `AGENTS.md`; app
  `apps\agent-fpac-soil-openai-sdk\AGENTS.md`; harness
  `eval\fpac_soil_mcp_harness\AGENTS.md`.
- Active accepted ADR constraints: 0002 fixed SQL; 0003 preliminary authority;
  0011 mocked default/live opt-in; 0012 separate agent app; 0014 validated
  metadata; 0015 vendored frontend; 0016 AOI session context; 0017 map result
  contract.
- Reference implementations: `tests\test_prompts.py`,
  `tests\test_server.py`, `eval\common\matching.py`,
  `eval\databricks\scorers.py`, `eval\pi\run_evals.py`,
  `apps\agent-fpac-soil-openai-sdk\tests\test_agent_config.py`,
  `tests\test_geo_screen.py`, `tests\test_geo_map.py`,
  `src\fpac_soil_mcp\authority.py`, and `src\fpac_soil_mcp\privacy.py`.
- Shared tests must run serially after waves; no two workers may edit the same
  file in one wave.

## Decision Log

1. **D1 — 2026-11-09 — priority:** Safety policy and refusal behavior are the
   critical path, followed by adversarial scoring, MCP/map contracts, and
   performance evidence.
2. **D2 — 2026-11-09 — surface boundary:** Cover the live agent, FastMCP
   prompts, Pi/Databricks evaluations, and map app; exclude unrelated redesign,
   workbench UX, and new adjacency sources.
3. **D3 — 2026-11-09 — prompt distribution:** Keep native prompt files per
   surface, with a policy version and shared required-rule assertions; do not
   add runtime cross-project imports or a generation dependency.
4. **D4 — 2026-11-09 — parallelism:** Maximum two workers per wave, with
   disjoint files and serial shared gates.
5. **D5 — 2026-11-09 — acceptance:** Targeted tests per wave; final
   `make check`, `make app-check`, `make test-eval`, and opt-in deployed
   measurements when the environment is available.
6. **D6 — 2026-11-09 — authority:** No task may weaken ADR 0003, claim legal
   exemption, or select a preferred alternative. Any conflict requires a new
   ADR before implementation.

## Wave & Dependency Table

| Wave | Task | Title | Must edit | Can create | Depends on |
|---|---|---|---|---|---|
| 1 | 46.1.1 | Harden native prompt policy text | `apps\agent-fpac-soil-openai-sdk\agent_server\prompts\system_prompt.txt`; `eval\databricks\prompts\system_prompt_v2.txt`; `eval\databricks\prompts\system_prompt_v1.txt`; `src\fpac_soil_mcp\prompts\fppa_prompts.py` | none | none |
| 1 | 46.1.2 | Add cross-surface policy assertions | `eval\common\matching.py`; `eval\common\test_common_matching.py`; `tests\test_prompts.py`; `apps\agent-fpac-soil-openai-sdk\tests\test_agent_config.py`; `eval\pi\run_evals.py`; `eval\pi\test_agent_eval.py` | `eval\common\policy_rules.v1.json` | none |
| 1 gate | - | Prompt policy gate | none | none | 46.1.1, 46.1.2 |
| 2 | 46.2.1 | Add adversarial case corpus and status schema | `eval\eval_cases.v1.json`; `eval\prompt_test_cases.json`; `eval\common\dataset.py`; `eval\common\test_common_dataset.py`; `eval\fpac_soil_mcp_harness\lib\evalCases.js` | none | 46.1 gate |
| 2 | 46.2.2 | Add deterministic safety and reliability scorers | `eval\common\matching.py`; `eval\common\test_common_matching.py`; `eval\databricks\scorers.py`; `eval\databricks\test_databricks_scorers.py`; `eval\fpac_soil_mcp_harness\lib\evalAssertions.js`; `eval\fpac_soil_mcp_harness\test\harness.test.js`; `eval\pi\run_evals.py`; `eval\pi\test_agent_eval.py` | none | 46.2.1 |
| 2 gate | - | Adversarial evaluation gate | none | none | 46.2.1, 46.2.2 |
| 3 | 46.3.1 | Harden public MCP input/error contracts and tool metadata | `src\fpac_soil_mcp\tools\__init__.py`; `src\fpac_soil_mcp\tools\soil_lookup_tools.py`; `src\fpac_soil_mcp\tools\spatial_analysis_tools.py`; `src\fpac_soil_mcp\tools\lesa_tools.py`; `src\fpac_soil_mcp\tools\exemption_tools.py`; `src\fpac_soil_mcp\tools\fppa_tools.py`; `src\fpac_soil_mcp\models.py`; `src\fpac_soil_mcp\case_models.py`; `src\fpac_soil_mcp\integration_models.py`; `tests\test_tools.py`; `tests\test_models.py`; `tests\test_server.py`; `eval\contract\test_contract.py`; no prompt files | `planning\evidence\46.3.1-tool-surface-review.md` | 46.1 gate |
| 3 | 46.3.2 | Preserve map uncertainty and non-prime semantics | `apps\agent-fpac-soil-openai-sdk\agent_server\geo.py`; `apps\agent-fpac-soil-openai-sdk\frontend\client\src\components\map\farmlandClasses.ts`; `apps\agent-fpac-soil-openai-sdk\tests\test_geo_screen.py`; `apps\agent-fpac-soil-openai-sdk\tests\test_geo_map.py` | `apps\agent-fpac-soil-openai-sdk\tests\fixtures\geo_semantics.json` | 46.2.1 |
| 3 gate | - | MCP/map safety gate | none | none | 46.3.1, 46.3.2 |
| 4 | 46.4.1 | Instrument reproducible Criterion 2 benchmarks | `eval\criterion2_benchmark.py`; `tests\test_criterion2_benchmark.py`; `tests\fixtures\criterion2_benchmark.v1.json`; `Makefile` | `planning\evidence\46.4.1-fixture-manifest.md` | 46.2 gate, 46.3 gate |
| 4 | 46.4.2 | Run repeated, bounded-load, and deployed evidence | benchmark outputs and evidence report only | `planning\evidence\46.4.2-performance.md`; `planning\evidence\46.4.2-performance.json` | 46.4.1 |
| 4 gate | - | Criterion 2 evidence gate | none | none | 46.4.2 |
| 5 | 46.5.1 | Synchronize planning and submission documentation | `planning\GOALS.md`; `planning\MASTER_PLAN.md`; `README.md`; `eval\databricks\README.md`; `apps\agent-fpac-soil-openai-sdk\README.md`; `eval\fpac_soil_mcp_harness\README.md` | `planning\evidence\46.5.1-closeout.md` | 46.2 gate, 46.3 gate, 46.4 gate |
| 5 gate | - | Final serial validation and review | none | none | 46.5.1 |
| 6 | 46.6.1 | Correct unavailable Site Assessment completion status | `src\fpac_soil_mcp\lesa.py`; `tests\test_lesa.py` | none | 46.3 gate |
| 6 | 46.6.2 | Characterize DB45-E3 judge noise and null scores | `eval\databricks\test_databricks_scorers.py`; `tests\eval\test_phase4_databricks_contract.py` | `planning\evidence\46.6.2-judge-followup.md` | 46.2 gate |
| 6 gate | - | PR #83 evaluation follow-up gate | none | none | 46.6.1, 46.6.2 |
| 7 | 46.7.1 | Migrate Pi eval runner to built-in MCP | `eval\pi\run_evals.py`; `eval\pi\test_agent_eval.py` | none | 46.5 gate |
| 7 gate | - | Pi native-MCP contract gate | none | none | 46.7.1 |
| 8 | 46.8.1 | Re-test Pi auth and evaluation | evidence report only | `planning\evidence\46.8.1-pi-auth-eval.md` | 46.7 gate |
| 8 | 46.8.2 | Diagnose representative Pi evaluation failures | evidence report and state only unless artifacts prove a code defect | `planning\evidence\46.8.2-pi-failure-diagnostics.md`; `planning\tasks\46.8.2.todo.md` | 46.8.1 |
| 8 gate | - | Pi auth and evaluation evidence gate | none | none | 46.8.1 |

Tasks in the same wave have disjoint edit sets. Wave 1 tasks use the
policy requirements recorded in this plan and can run in parallel; the gate
after Wave 1 verifies that the implemented text and assertions agree.
Waves 2 and 3 are separately themed even where technically independent.

## Task Specifications

### 46.1.1 — Harden live and evaluation prompt policy

- **Repo:** `D:\workspace\fpac-soil-mcp`
- **Files in scope:** the four prompt surfaces listed in the wave table;
  prompt tests may be read but not edited by this task.
- **Depends on:** none.
- **Spec:** Add a clearly versioned policy block covering FPPA-only scope,
  refusal of unrelated requests, no official/legal determinations, no
  siting/relocation recommendations, non-prime and conditional-class
  semantics, urban-screening limits, LESA threshold language, explicit
  unknown/partial/unavailable handling, and untrusted user/tool text.
  Preserve existing no-invention and regulatory wording. Do not name specific
  tools in the live system prompt.
- **Anchors:** live `system_prompt.txt`; `fppa_prompts.py` registered prompt
  functions; Databricks v1/v2 prompt files.
- **Reference:** `src\fpac_soil_mcp\constants.py`; ADR 0003; current
  `tests\test_prompts.py`.
- **Do not touch:** tool implementations, model schemas, frontend files,
  evaluation case data.
- **Checklist (8 steps max):** update live text; update Databricks v1/v2;
update FastMCP prompt text; preserve existing notices; add policy version;
inspect resulting prompt lengths; review forbidden recommendation wording;
hand off exact required-rule list to 46.1.2.
- **Acceptance:** prompt tests assert the required rules and existing
  authority notices remain present. Command:
  `uv run pytest tests\test_prompts.py eval\databricks\test_databricks_agent.py -q`.

### 46.1.2 — Add shared policy-version assertions

- **Repo:** `D:\workspace\fpac-soil-mcp`
- **Files in scope:** `eval\common\matching.py`,
  `eval\common\test_common_matching.py`, `tests\test_prompts.py`,
  `apps\agent-fpac-soil-openai-sdk\tests\test_agent_config.py`,
  `eval\pi\run_evals.py`, and `eval\pi\test_agent_eval.py`; can create
  `eval\common\policy_rules.v1.json`.
- **Depends on:** none; the required rule list is specified by this plan.
- **Spec:** Define required policy version/rules once for tests, not runtime
  imports. Assert each native prompt surface contains the version and required
  semantic rules. Assert Pi's generated/forced prompt path carries the same
  policy version or required-rule set; Pi has no separate prompt file.
  Include negative checks for missing refusal and unsafe siting wording. Keep
  test helpers independent of live credentials.
- **Anchors:** `eval\common\dataset.py`; `tests\test_prompts.py`;
  app `tests\test_agent_config.py`.
- **Reference:** `eval\common\matching.py`; app prompt-loading tests.
- **Do not touch:** production prompt text, MCP tools, frontend.
- **Checklist (8 steps max):** define version/rules; add shared helper;
  assert live prompt; assert FastMCP prompts; assert Databricks prompts;
  assert Pi prompt construction; add negative fixture; run app/prompt tests.
- **Acceptance:** helper tests pass and identify a deliberately incomplete
  policy fixture. Command:
  `uv run pytest tests\test_prompts.py apps\agent-fpac-soil-openai-sdk\tests\test_agent_config.py eval\pi\test_agent_eval.py -q`.

### 46.2.1 — Add adversarial case corpus and status schema

- **Repo:** `D:\workspace\fpac-soil-mcp`
- **Files in scope:** `eval\eval_cases.v1.json`,
  `eval\prompt_test_cases.json`, `eval\common\dataset.py`,
  `eval\common\test_common_dataset.py`, and
  `eval\fpac_soil_mcp_harness\lib\evalCases.js`.
- **Depends on:** prompt policy gate.
- **Spec:** Add versioned cases for unrelated work, official forms,
  non-prime inference, relocation, corridor choice, urban exemption,
  conditional classes, missing values, tool outages, partial upstream failure,
  malformed geometry, prompt injection, privacy non-echo, and performance
  budgets. Add `expected_status`, required/prohibited behaviors, source
  disclosure, call/retry budgets, and latency budget fields without breaking
  existing cases.
- **Anchors:** `eval\eval_cases.v1.json`; `eval\prompt_test_cases.json`;
  `eval\common\dataset.py`; harness `lib\evalCases.js`.
- **Reference:** existing prohibited behavior names and malformed presets.
- **Do not touch:** scorer logic, production prompts, MCP tools.
- **Checklist (8 steps max):** extend schema; add out-of-scope cases; add
  authority cases; add non-prime/urban cases; add outage/partial cases; add
  injection/privacy cases; add performance metadata; run dataset tests.
- **Acceptance:** dataset parsing remains backward-compatible and new cases
  load deterministically. Command:
  `uv run pytest eval\common eval\contract -q`.

### 46.2.2 — Add deterministic safety and reliability scorers

- **Repo:** `D:\workspace\fpac-soil-mcp`
- **Files in scope:** common matching and its tests, Databricks scorers and
  their tests, harness assertions and tests, and Pi result/test handling
  listed in the wave table.
- **Depends on:** 46.2.1.
- **Spec:** Add negation-aware prohibited-claim checks, required behavior/status
  checks, provenance/disclosure checks, privacy non-echo, max tool/retry
  calls, and latency budgets. Preserve current runner health statuses and
  separate semantic status. Unknown harness predicates must continue to fail
  closed.
- **Anchors:** `eval\common\matching.py`; `eval\databricks\scorers.py`;
  `eval\pi\run_evals.py`; `lib\evalAssertions.js`.
- **Reference:** existing keyword/numeric scorers and timeout result schema.
- **Do not touch:** prompt files, MCP implementations, deployment settings.
- **Checklist (8 steps max):** add negation matcher; add prohibited-claim
  scorer; add required-status scorer; add provenance/privacy scorer; add
  call/retry budget checks; add latency budget; add harness predicates; run
  focused scorer tests.
- **Acceptance:** scorer tests cover affirmative forbidden claims and properly
  negated safety statements. Command:
  `uv run pytest eval\common eval\databricks\test_databricks_scorers.py eval\pi\test_agent_eval.py -q`;
  from `eval\fpac_soil_mcp_harness`, `npm test` and `npm run check`.

### 46.3.1 — Harden public MCP input/error contracts

- **Repo:** `D:\workspace\fpac-soil-mcp`
- **Files in scope:** only public tool modules/models/tests required for
  geometry, LESA, exemption, interpretation, and site-assessment validation.
- **Depends on:** prompt policy gate.
- **Spec:** Inventory these ten public MCP tools: `get_farmland_classification_by_point`,
  `get_farmland_classification_by_mukey`, `analyze_farmland_by_polygon`,
  `calculate_preliminary_lesa`, `get_soil_polygons_by_geometry`,
  `check_urban_area_exemption`, `get_soil_interpretations`,
  `analyze_corridor_fppa`, `explain_fppa_screening_scope`, and
  `list_farmland_classes`. Review each name, description,
  input schema, output/status semantics, and whether it is a meaningful
  agent-facing action rather than a thin REST/client wrapper. Record the full
  inventory and any deferred wrapper in
  `planning\evidence\46.3.1-tool-surface-review.md`. Then replace
  safety-critical raw dictionaries/arbitrary strings with
  strict Pydantic models/enums/bounds where existing patterns support it.
  Reject unknown criteria and malformed combinations. Normalize expected
  failures into structured, source-aware envelopes without changing valid
  result shapes unnecessarily.
- **Anchors:** public signatures in `tools\spatial_analysis_tools.py`,
  `tools\lesa_tools.py`, `tools\exemption_tools.py`,
  `tools\soil_lookup_tools.py`; models and authority validators.
- **Reference:** `integration_models.py`, `authority.py`, existing geometry
  validation tests.
- **Checklist (8 steps max):** inventory public signatures; define input
  models; validate enums/bounds; reject unknown fields/criteria; define
  structured error fields; update tool metadata descriptions; add malformed
  input tests; run exact contract tests.
- **Do not touch:** prompts, eval runners, frontend, external API clients
  unless a narrowly required error type is already established.
- **Acceptance:** the tool-surface review lists every public tool, confirms
  non-empty action-oriented metadata, identifies any deferred thin wrapper with
  owner and trigger, and malformed nested input/unknown field/invalid
  enum-value/upstream failure tests pass with no contract regression.
  Command: `uv run pytest tests\test_tools.py tests\test_models.py tests\test_server.py eval\contract\test_contract.py -q`.

### 46.3.2 — Preserve map uncertainty and non-prime semantics

- **Repo:** `D:\workspace\fpac-soil-mcp`
- **Files in scope:** app `geo.py`, frontend `farmlandClasses.ts`, related map
  tests only.
- **Depends on:** adversarial corpus gate.
- **Spec:** Ensure unknown/unrecognized/absent classifications never fall
  through to `not_prime`; preserve server status and labels in chat summaries
  and identify UI. Add explicit non-prime limitation text where a result is
  presented. Keep map-only calls untraced, geometry-free summaries, body
  limits, allowlists, and AOI substitution unchanged.
- **Anchors:** `geo.py` summary allowlist; frontend class mapping and identify
  popup; `test_geo_screen.py`, `test_geo_map.py`.
- **Reference:** ADR 0016/0017 and existing privacy tests.
- **Do not touch:** MCP server tool implementations, basemap/overlay catalog,
  AOI session architecture.
- **Checklist (8 steps max):** inspect server classification states; remove
  unsafe frontend fallback; preserve unknown/unmapped labels; update summary
  limitation text; add unknown tests; add partial tests; run map tests; run
  app check.
- **Acceptance:** unknown/unmapped/unrecognized, partial, and not-prime cases
  render distinctly; privacy and map route tests remain green.
  Command: `make app-check`.

### 46.4.1 — Instrument reproducible Criterion 2 benchmarks

- **Repo:** `D:\workspace\fpac-soil-mcp`
- **Files in scope:** `eval\criterion2_benchmark.py`,
  `tests\test_criterion2_benchmark.py`,
  `tests\fixtures\criterion2_benchmark.v1.json`, and `Makefile`.
- **Depends on:** adversarial and MCP/map safety gates.
- **Spec:** Add benchmark metadata for commit, prompt/case version, model,
  transport, timeout, retries, concurrency, inputs, response status, tool
  calls, latency, response size, and memory method. Support repeated runs and
  bounded concurrency without changing default offline test behavior. Create
  the canonical manifest at `tests\fixtures\criterion2_benchmark.v1.json`
  with fixture IDs `CORR-MULTI-2COUNTY`, `CORR-MULTI-3COUNTY`,
  `POLY-PARTIAL`, and `URBAN-PARTIAL`. Each record must include `geometry`,
  `county_fips`, `county_count`, `expected_coverage_class`, and
  `expected_status`; every aggregate records the manifest version and county
  identifiers/count.
- **Anchors:** Pi elapsed/result handling; Databricks runner worker settings;
  existing eval case loaders and evidence reports.
- **Reference:** `eval\pi\run_evals.py`, `eval\databricks\run_mlflow_eval.py`,
  `planning\evidence\45.4.2-evaluation.md`.
- **Do not touch:** production prompts, public tool behavior, deployment
  credentials.
- **Checklist (8 steps max):** define result schema; create canonical
  multi-county fixture manifest; capture environment;
  capture per-case timing; capture tool/retry counts; add repeated-run mode;
  add bounded concurrency; add aggregate percentiles/failure fields; add dry
  run tests.
- **Acceptance:** deterministic benchmark dry run emits a complete schema,
  aggregate p50/p95/p99/failure/retry fields, and multi-county identifiers.
  The canonical fixture manifest is owned by this task and must be consumed
  verbatim by 46.4.2.
  Commands: `uv run pytest tests\test_criterion2_benchmark.py -q`;
  `uv run python eval\criterion2_benchmark.py --fixture-manifest tests\fixtures\criterion2_benchmark.v1.json --runs 1`;
  then `make test-eval`.

### 46.4.2 — Run repeated, bounded-load, and deployed evidence

- **Repo:** `D:\workspace\fpac-soil-mcp`
- **Files in scope:** `planning\evidence\46.4.2-performance.md` and
  `planning\evidence\46.4.2-performance.json`; no source changes unless a
  benchmark defect is discovered and re-planned.
- **Depends on:** 46.4.1.
- **Spec:** Consume `tests\fixtures\criterion2_benchmark.v1.json` verbatim;
  execute it repeatedly, under bounded concurrency, including named
  multi-county corridor fixtures, and against
  deployed `/mcp` when credentials/environment are
  available. Separate deterministic, model-assisted, and deployed results.
  Record unavailable external measurements rather than fabricating them.
- **Anchors:** benchmark output schema from 46.4.1; T2/deployment instructions
  in existing evaluation docs.
- **Reference:** ADR 0011 and current evidence report conventions.
- **Do not touch:** application/source code, credentials, `.env`, generated
  dependency files.
- **Checklist (8 steps max):** select fixture IDs; record county identifiers;
  run repeated offline cases; run bounded concurrency; run deployed cases if
  available; collect percentiles; classify failures/unavailable targets; write
  evidence report.
- **Acceptance:** evidence report contains exact inputs, settings, commit SHA,
  county coverage, percentiles, failure/retry counts, limitations, and explicit
  unavailable fields where a target environment was not accessible. Command:
  `uv run python eval\criterion2_benchmark.py --fixture-manifest tests\fixtures\criterion2_benchmark.v1.json --runs 5 --max-workers 2 --output planning\evidence\46.4.2-performance.json`;
  deployed runs use the exact command
  `uv run python eval\criterion2_benchmark.py --fixture-manifest tests\fixtures\criterion2_benchmark.v1.json --runs 5 --max-workers 2 --transport http --mcp-url $env:MCP_URL --output planning\evidence\46.4.2-performance.json`;
  no default-suite substitution.

### 46.5.1 — Synchronize planning and submission documentation

- **Repo:** `D:\workspace\fpac-soil-mcp`
- **Files in scope:** `planning\GOALS.md`, `planning\MASTER_PLAN.md`,
  `README.md`, `eval\databricks\README.md`,
  `apps\agent-fpac-soil-openai-sdk\README.md`,
  `eval\fpac_soil_mcp_harness\README.md`, and
  `planning\evidence\46.5.1-closeout.md`.
- **Depends on:** gates for Waves 2–4.
- **Spec:** Record the new track in the master plan, preserve the current
  PR #79/CDL dependency and adjacency deferral, document the reproducible
  evaluation setup/results, and keep deterministic/model/deployed evidence
  separate. Do not claim completion for unexecuted work.
- **Anchors:** existing Track E/Track A sections; `STATE_45.md`;
  `planning\evidence\45.4.2-evaluation.md`.
- **Reference:** `EXECUTION_PLAN_45.md` and `STATE_45.md`.
- **Do not touch:** feature source files, credentials, prior state reports.
- **Checklist (8 steps max):** update goals; update master-plan track;
  document prompt policy; document adversarial setup; document benchmark setup;
  link evidence; record unexecuted/deferred items; run documentation checks.
- **Acceptance:** documentation cross-links resolve, scope/deferrals are
  explicit, and the final serial validation commands are recorded.
  Command: `make check`; `make app-check`; `make test-eval`.

## Addendum — PR #83 deferred work and current Pi CLI

This addendum was requested after the original Waves 1–5 closeout. It does not
reopen completed work. DB45-E4/WKT work remains explicitly out of scope per
user direction; do not duplicate or inspect its Plan 44 follow-up.

### 46.6.1 — Correct unavailable Site Assessment completion status

- **Repo:** `D:\workspace\fpac-soil-mcp`
- **Files in scope:** `src\fpac_soil_mcp\lesa.py`; `tests\test_lesa.py`.
- **Depends on:** completed 46.3.1 MCP-contract gate.
- **Spec:** PR #83 defers DB45-10: `evaluate_site_assessment(None, ...)` can
  report `complete` even though 11 criteria are unavailable. Ensure completion
  status reflects unavailable criteria for the no-input path. Preserve the
  existing Criterion 7 machine estimate when acreage inputs are supplied and
  do not change valid explicit-criteria scoring or public result shapes.
- **Anchors:** `evaluate_site_assessment`; the `evaluation_status` derivation;
  `test_missing_site_assessment_is_incomplete` and
  `test_complete_factual_criterion_seven_remains_scored`.
- **Reference:** PR #83 body, DB45-10; `planning\evidence\46-pr83-followup-research.md`.
- **Checklist (5 steps max):** reproduce the direct-call status; define the
  status invariant; fix status derivation; add regression assertions for
  unavailable criteria and Criterion 7; run targeted LESA tests.
- **Acceptance:** a `None`-input assessment with only Criterion 7 estimated
  cannot report `complete`; explicit complete inputs retain their current
  behavior. Command: `uv run pytest tests\test_lesa.py -q`.

### 46.6.2 — Characterize DB45-E3 judge noise and null scores

- **Repo:** `D:\workspace\fpac-soil-mcp`
- **Files in scope:** `eval\databricks\test_databricks_scorers.py` and
  `tests\eval\test_phase4_databricks_contract.py`; scorer implementation and
  the case dataset are read-only references.
- **Can create:** `planning\evidence\46.6.2-judge-followup.md`.
- **Depends on:** completed Wave 2 adversarial-evaluation gate.
- **Spec:** Add offline synthetic contract coverage for the DB45-E3 compliant
  response that received a false-negative `fppa_compliance` judge result, and
  clarify why correctness/guideline scores are null when expected facts are
  absent. Do not change judge guidance or the evaluation corpus based on this
  one observation. Keep judge outputs model-assisted observations, separate
  from deterministic safety checks; do not hide genuine failures or claim a
  deterministic result from one model-judge observation.
- **Anchors:** `FPPA_COMPLIANCE_GUIDELINE`, `judge_scorers`,
  `test_phase4_databricks_contract.py`, and existing SA-MA cases.
- **Reference:** PR #83 body and DB45-E3 review finding;
  `planning\evidence\46-pr83-followup-research.md`.
- **Checklist (6 steps max):** trace expected-fact/null mapping; add a
  synthetic response fixture in the test; assert it aligns with the constructed
  rubric and evidence tier; test absent expectation semantics; record the
  model-assisted limitation; run targeted tests.
- **Acceptance:** offline tests preserve the compliant-disclaimer case and
  explicit null-score semantics without invoking a judge or changing
  deterministic gates. Commands:
  `uv run pytest eval\databricks\test_databricks_scorers.py tests\eval\test_phase4_databricks_contract.py -q`;
  `uv run pytest eval\pi\test_agent_eval.py -m "not agent_eval" -q`.

### 46.7.1 — Migrate Pi evaluation runner to built-in MCP

- **Repo:** `D:\workspace\fpac-soil-mcp`
- **Files in scope:** `eval\pi\run_evals.py`; `eval\pi\test_agent_eval.py`.
- **Depends on:** completed 46.5 final-validation gate.
- **Spec:** Pi 1.5.2 rejects the runner's legacy `--mcp-config` argument. Use
  Pi's built-in MCP configuration in the isolated temporary sandbox (project
  `.pi\mcp.json`) and trust only that runner-controlled project config. Keep
  the server on stdio via `uv run fpac-soil-mcp`; do not rely on or reinstall
  `pi-mcp-adapter`, and do not modify global Pi configuration or persist
  credentials.
- **Anchors:** `create_sandbox`, `run_case` argument construction, and
  `sandbox_env`/`test_pi_point_screening_evaluation`.
- **Reference:** `pi --help`, `pi mcp --help`, and existing temporary-sandbox
  invariants in `eval\pi\test_agent_eval.py`.
- **Checklist (6 steps max):** update isolated config layout; use built-in MCP
  CLI options; retain stdio server command; update command-construction tests;
  assert no legacy flag; run offline Pi tests.
- **Acceptance:** tests assert the temporary `.pi\mcp.json` configuration and
  current Pi invocation without the removed `--mcp-config` flag. Command:
  `uv run pytest eval\pi\test_agent_eval.py -m "not agent_eval" -q`.

### 46.8.1 — Re-test Pi authentication and evaluation

- **Repo:** `D:\workspace\fpac-soil-mcp`
- **Files in scope:** evidence report only.
- **Can create:** `planning\evidence\46.8.1-pi-auth-eval.md`.
- **Depends on:** completed 46.7 Pi native-MCP gate.
- **Spec:** Check the catalog-qualified provider/model without printing or
  retaining credentials. Run `POINT-01` with the repository Pi runner and
  `--no-show-output`, without capture. If it passes, run `make test-eval`;
  otherwise stop after recording sanitized startup/tool diagnostics and do not
  retry with guessed providers or model names.
- **Reference:** `pi-mcp-eval` execution rules; current Pi auth check and
  single-case diagnostics recorded at the addendum start.
- **Checklist (5 steps max):** record Pi version; check
  `github-copilot/gpt-5.6-luna` readiness; run one case without output capture;
  run full eval only if the case passes; record sanitized results and limits.
- **Acceptance:** evidence includes exact commands, auth readiness, per-case
  status and tool-evidence classification, and whether the full opt-in suite
  ran; no credentials, prompt text, coordinates, geometry, or raw artifacts.
  Commands: `pi auth check --model github-copilot/gpt-5.6-luna --json --no-refresh`;
  `uv run python eval\pi\run_evals.py --case-id POINT-01 --no-show-output`;
  then `make test-eval` only if POINT-01 passes.

### 46.8.2 — Diagnose representative Pi evaluation failures

- **Repo:** `D:\workspace\fpac-soil-mcp`
- **Files in scope:** this task checklist, `planning\STATE_46.md`, and a
  sanitized evidence report; code/tests only if captured evidence establishes
  a reproducible repository defect.
- **Can create:** `planning\evidence\46.8.2-pi-failure-diagnostics.md`;
  `planning\tasks\46.8.2.todo.md`.
- **Depends on:** 46.8.1 Pi auth/evaluation evidence.
- **Spec:** Individually rerun only `PROMPT-03`, `SA-MA-01`,
  `ADV-INJECTION-01`, `ADV-OUTAGE-01`, and `ADV-PRIVACY-01` with artifact
  capture enabled, qualified model `github-copilot/gpt-5.6-luna`, and a new
  timestamped external artifact root. Inspect each case's structured events
  and diagnostics; distinguish observations from hypotheses. Do not rerun
  passing reruns unless needed to verify a code fix.
- **Reference:** `planning\evidence\46.8.1-pi-auth-eval.md`; Pi eval skill and
  the runner's `--help`. Preserve privacy: keep artifacts outside the repo,
  never expose raw prompts, responses, coordinates, geometry, credentials, or
  producer data in committed content, filenames, or metadata.
- **Checklist (5 steps max):** verify capture options and clean branch context;
  run the five listed cases individually into a fresh external root; inspect
  captured events/diagnostics locally; make and test a minimal fix only if a
  repository defect is established; write sanitized evidence and update state.
- **Acceptance:** report exact commands, per-case outcomes, observed causes
  versus hypotheses, artifact location and retention limits; no full eval or
  unrelated cases are run, and the report does not claim full-eval success.

## Hazard Notes

- Prompt files are intentionally duplicated across projects; policy-version
  assertions are the drift control.
- `models.py`, `run_evals.py`, `geo.py`, and prompt modules are large; workers
  must use the named anchors and not read/rewrite entire files by default.
- Do not turn a negated safety sentence into a prohibited-claim match.
- Do not classify unknown/unmapped/unrecognized farmland text as `not_prime`.
- Do not expose AOI geometry in map summaries, logs, or new artifacts.
- Do not add live tests to the default path or claim deployed performance when
  the target environment was unavailable.
- Do not supersede ADR 0003, 0011, 0016, or 0017 implicitly.
