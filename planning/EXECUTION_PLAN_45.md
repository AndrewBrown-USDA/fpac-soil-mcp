# EXECUTION PLAN 45: Phase 4 LESA Closeout

## Goal & Scope

**Goal:** Close issue #14 by completing the remaining Phase 4 correctness,
authority-boundary, aggregation, evidence, and documentation work. The plan
formalizes a deterministic, user-facing Site Assessment workflow for subjective
criteria using versioned multiple-choice/semi-quantitative bands; preserves
explicit incomplete states when required human inputs are absent; verifies
metadata-driven property selection across multi-county polygon and corridor
aggregation; produces a reproducible deterministic gold-set evidence package;
and synchronizes the milestone documentation and verification record. The
agricultural-land adjacency data stream is explicitly deferred.

**In scope:**

- Site Assessment subjective-criteria contract, question wording, banded
  inputs, point mappings, rationale/verification fields, and incomplete-result
  semantics.
- A versioned bundled scoring registry and a read-only MCP question resource,
  plus fact-based input handling in `calculate_preliminary_lesa`.
- Existing factual Site Assessment inputs that can be supported without the
  deferred adjacency source, including farm-size comparison where available.
- Explicit unavailable/indeterminate handling; no fabricated subjective scores.
- Metadata-driven selected-property preservation through county partitioning,
  county-specific maxima, area-weighted aggregation, and reconciliation across
  polygon, corridor, and unified LESA paths.
- Deterministic gold-set fixtures for scoring, source-table strategies,
  coverage states, urban overlap, missing subjective inputs, provenance, and
  failure semantics.
- Retained Pi artifacts for parser/diagnostic regression fixtures; separate
  reporting of deterministic contract results and model-assisted results.
- Synchronization of `MASTER_PLAN.md`, `README.md`, `manifest.yaml`,
  `server.json`, active ADR references, and the issue-closeout evidence.
- Targeted tests, serial full offline gates, relevant opt-in live tests, and
  exact verification results.

**Out of scope (explicit deferrals):**

- Building, querying, or simulating the agricultural-land adjacency data
  stream. The perimeter-adjacency criterion remains unavailable unless supplied
  by an approved source or explicitly provided by an analyst.
- Reintroducing a public NCCPI-only restriction. ADR 0014's generic,
  registry-validated metadata routing remains authoritative.
- Official FPPA/NRCS determinations, signed AD-1006 or CPA-106 forms, agency
  approval, or legal exemption decisions.
- Recommending sites, footprints, or preferred alternatives. The system may
  report the regulatory consequence of a score and compare alternatives
  supplied by the user, but does not choose them.
- New long-tail spatial sources for farm history, easements, wetlands,
  flooding, hydric soils, or agricultural support services unless required to
  represent an explicit unavailable state.
- Frontend redesign, new map capabilities, and unrelated Phase 8 work.

**Verbatim constraints from the user:**

- “so, we are in the process of getting a data stream set up for agricultral
  land adjacency. so ideally we can keep that out of this workplan.”
- “im thinking of a robust system for handling the site assessment subjective
  criteria/in lieu of a spatial authoriative source we provide a multiple
  choice ranking system where users semi-quantiatively estimate the relevant
  subjective criteria based on percentage classes and then we assign points
  based on that.”
- Issue #14: “Ensure unavailable measurements are not silently converted to
  zero.”
- Issue #14: “Prevent the system from fabricating subjective scores.”
- Issue #14: “Return an incomplete or indeterminate result when required human
  inputs are missing.”
- Issue #14: “Verify metadata-driven property selection across multi-county
  aggregation.”
- Issue #14: “Separate deterministic contract-test results from model-judge
  results.”

## Reconnaissance Log

- Current repository is `D:\workspace\fpac-soil-mcp`; highest existing
  orchestration is 44, so this set is 45.
- Baseline on 2026-11-09: `uv run pytest -q -m "not live_network and not
  agent_eval"` -> 705 passed, 3 skipped, 45 deselected. Pytest emitted the
  existing asyncio configuration warning and Shapely deprecation warnings.
- Entry-point sizes: `src\fpac_soil_mcp\lesa.py` 889 lines;
  `src\fpac_soil_mcp\corridor_scoring.py` 468; `models.py` 654;
  `tools\lesa_tools.py` 175; `tests\test_lesa.py` 709;
  `eval\prompt_test_cases.json` 583.
- Existing LESA logic already has strategy evaluators, criterion maxima,
  criterion 7 farm-size scoring, justification checks, and preliminary
  authority models. `calculate_preliminary_lesa` currently accepts
  `criteria_inputs` with analyst-provided `awarded_points`; it must not be
  treated as a deterministic answer contract without the new fact mode.
- `planning\RESEARCH_GUIDED_LESA_SITE_ASSESSMENT.md` records the key hazards:
  model-selected points, non-regulatory answer bands, Part V/VI wording
  drift, incomplete SA appearing as a threshold result, missing breakdown,
  and prohibited siting recommendations.
- Accepted ADR constraints: ADR 0003 preserves preliminary authority
  boundaries; ADR 0007 keeps shared LE logic in `lesa.py`; ADR 0008 and ADR
  0014 require validated metadata-driven rating routing; ADR 0011 keeps
  mocked tests default and live tests opt-in; ADR 0002 forbids user SQL.
- Existing reference implementations: `tests\test_lesa.py`,
  `src\fpac_soil_mcp\lesa.py`, `src\fpac_soil_mcp\corridor_scoring.py`,
  `src\fpac_soil_mcp\map_contract.py`, `tests\test_sdv_contract.py`,
  `tests\test_sdv_strategies.py`, `eval\common\dataset.py`, and
  `eval\databricks\scorers.py`.
- Canonical validation commands: `make check`, `uv run pytest -m
  live_network`, `make test-eval`, and `make eval-databricks`. Live tests are
  opt-in and must not enter the default offline gate.

## Decision Log

1. **D1 — 2026-11-09 — adjacency boundary:** Defer the agricultural-land
   adjacency data stream. The plan may represent that criterion as unavailable
   or analyst-provided, but it must not create a replacement spatial source or
   convert unavailable data to zero.
2. **D2 — 2026-11-09 — subjective scoring:** Implement a robust
   multiple-choice/semi-quantitative ranking system. Users provide percentage
   classes or defined qualitative choices; the server applies versioned point
   mappings and returns the rule, points, rationale status, and verification
   state.
3. **D3 — 2026-11-09 — scoring storage:** Store the bands and point mappings
   in a versioned bundled registry, validated before use, rather than scattering
   the contract through Python constants.
4. **D4 — 2026-11-09 — public contract:** Add a read-only
   `fppa://site-assessment-criteria` resource and a fact-based input mode on
   `calculate_preliminary_lesa`. Explicit point overrides remain possible only
   as analyst-proposed values with mandatory rationale and are labeled as such.
5. **D5 — 2026-11-09 — missing inputs:** Missing required inputs produce an
   incomplete/indeterminate Site Assessment and `threshold_status:
   "not_evaluated"` (or the repository's equivalent typed state), not a
   success-shaped zero score.
6. **D6 — 2026-11-09 — evidence bar:** Deterministic contract tests are the
   release gate. Model-assisted/Pi/Databricks judge results are reported as a
   separate evidence tier; retained Pi artifacts may become parser and
   diagnostic regression fixtures.
7. **D7 — 2026-11-09 — execution:** Use four logical waves with pairwise
   disjoint files within a wave, serial full-offline gates, and relevant
   opt-in live tests only when upstream behavior changes.
8. **D8 — 2026-11-09 — architecture compliance:** Comply with ADR 0007,
   ADR 0014, and ADR 0011. No ADR is superseded by this plan. If a necessary
   implementation decision conflicts with an accepted ADR, stop and record a
   new decision before coding.
9. **D9 — 2026-11-10 — Databricks regulatory review:** Use the checked-in
   eCFR copies under `docs\cfr\` as the source for Site Assessment wording and
   point schedules. Keep criterion 2 spatial adjacency deferred, but accept an
   analyst-supplied percentage when its provenance is explicit. Registry facts
   requiring human judgment are analyst-proposed/user-provided inputs, not
   machine estimates, and must preserve rationale and verification state.
10. **D10 — 2026-11-10 — criterion 7 correction:** Align all criterion 7
    paths with the 7 CFR 658.5(b)(7) deduction schedule rather than preserving
    the legacy three-band approximation.
11. **D11 — 2026-11-10 — geometry/type validation:** Reject a LineString
    submitted with the default site project type; callers must explicitly
    declare corridor analysis rather than receiving mixed corridor LE and site
    SA semantics.

## Wave & Dependency Table

| Wave | Task | Title | Files in scope | Depends on |
|---|---|---|---|---|
| 1 | 45.1.1 | Define Site Assessment question and scoring registry | `src\fpac_soil_mcp\data\site_assessment.v1.json` (new), `src\fpac_soil_mcp\site_assessment.py` (new), `tests\test_site_assessment_contract.py` (new) | none |
| 1 | 45.1.2 | Add typed incomplete/authority result semantics | `src\fpac_soil_mcp\models.py`, `src\fpac_soil_mcp\lesa.py`, `tests\test_lesa.py` (focused additions) | none |
| 1 gate | - | Site Assessment contract gate | no feature files | 45.1.1, 45.1.2 |
| 2 | 45.2.1 | Wire fact-based Site Assessment inputs and resource | `src\fpac_soil_mcp\tools\lesa_tools.py`, `src\fpac_soil_mcp\resources\fppa_resources.py`, `src\fpac_soil_mcp\resources\__init__.py`, `src\fpac_soil_mcp\app.py`, `tests\test_tools.py`, `tests\test_site_assessment_resource.py` (new) | 45.1.1, 45.1.2 |
| 2 | 45.2.2 | Correct Site Assessment wording and close authority gaps | `src\fpac_soil_mcp\constants.py`, `src\fpac_soil_mcp\fppa.py`, `src\fpac_soil_mcp\prompts\fppa_prompts.py`, `tests\test_fppa.py`, `tests\test_prompts.py` | 45.1.1 |
| 2 gate | - | Site Assessment integration gate | no feature files | 45.2.1, 45.2.2 |
| 3 | 45.3.1 | Preserve selected metadata property through polygon/corridor aggregation | `src\fpac_soil_mcp\polygon_analysis.py`, `src\fpac_soil_mcp\corridor_analysis.py`, `src\fpac_soil_mcp\lesa.py`, `tests\test_polygon_analysis.py`, `tests\test_corridor_analysis.py`, `tests\test_multi_county_productivity.py` (new) | 45.1.1 |
| 3 | 45.3.2 | Reconcile coverage, county maxima, and provenance | `src\fpac_soil_mcp\sda_client.py`, `src\fpac_soil_mcp\models.py`, `tests\test_sdv_contract.py` | 45.3.1 |
| 3 gate | - | Aggregation and relevant live gate | no feature files | 45.3.1, 45.3.2 |
| 4 | 45.4.1 | Build deterministic Phase 4 gold-set evidence | `tests\fixtures\phase4_gold_set.json` (new), `eval\common\dataset.py`, `eval\common\matching.py`, `eval\contract\test_contract.py`, `tests\test_phase4_gold_set.py` (new) | 45.2.1, 45.3.2 |
| 4 | 45.4.2 | Separate model-assisted evidence and retain diagnostics | `eval\pi\test_agent_eval.py`, `eval\databricks\scorers.py`, `eval\eval_cases.v1.json`, `planning\evidence\45.4.2-evaluation.md` (new) | 45.4.1 |
| 4 | 45.4.3 | Synchronize milestone docs and closeout evidence | `planning\MASTER_PLAN.md`, `README.md`, `manifest.yaml`, `server.json`, `planning\STATE_45.md`, `planning\evidence\45.4.3-closeout.md` (new), `planning\REVIEW_45.md` (new) | 45.4.1, 45.4.2 |
| 4 gate | - | Final serial validation and review | no feature files | 45.4.3 |

Tasks in the same wave have pairwise-disjoint edit sets except where the table
explicitly assigns a later task to the next wave. Full gates run serially.

## Databricks Review Amendment — Remediation Waves 5-6

The Databricks review in `planning\REVIEW_45_DATABRICKS.md` supersedes the
earlier no-findings closeout review. The pulled review commit `6549d26` adds
the reusable eCFR fetch/check workflow and checked-in Part 657/658 reference
copies. These references are inputs to the remediation tasks below; generated
XML/Markdown files must not be edited by hand.

| Wave | Task | Title | Files in scope | Depends on |
|---|---|---|---|---|
| 5 | 45.5.1 | Correct registry mappings against eCFR | `src\fpac_soil_mcp\data\site_assessment.v1.json`, `src\fpac_soil_mcp\site_assessment.py`, `tests\test_site_assessment_contract.py`, `tests\fixtures\site_assessment_cfr_cases.json` (new) | 45.1.1 |
| 5 | 45.5.2 | Align LESA criterion 7 and unavailable LE semantics | `src\fpac_soil_mcp\lesa.py`, `src\fpac_soil_mcp\polygon_analysis.py`, `tests\test_lesa.py`, `tests\test_polygon_analysis.py` | 45.1.2, 45.3.1 |
| 5 | 45.5.3 | Enforce fact authority, conflicts, and corridor variants | `src\fpac_soil_mcp\tools\lesa_tools.py`, `src\fpac_soil_mcp\models.py`, `tests\test_tools.py` | 45.2.1, 45.5.1 |
| 6 | 45.5.4 | Reconcile coverage, provenance, and geometry/type validation | `src\fpac_soil_mcp\corridor_analysis.py`, `src\fpac_soil_mcp\tools\lesa_tools.py`, `src\fpac_soil_mcp\models.py`, `tests\test_corridor_analysis.py`, `tests\test_tools.py` | 45.5.3 |
| 6 | 45.5.5 | Repair Databricks evaluation coverage and evidence | `eval\common\dataset.py`, `eval\databricks\README.md`, `eval\eval_cases.v1.json`, `eval\prompt_test_cases.json`, `eval\databricks\scorers.py`, `tests\eval\test_phase4_databricks_contract.py` (new) | 45.5.3 |
| 6 gate | - | Databricks remediation validation | no feature files | 45.5.4, 45.5.5 |

### Wave 5 acceptance bar

- Run `make ecfr-check` before regulatory edits; use
  `docs\cfr\title-7-part-658.md` for wording and schedules.
- Correct criteria 1-12 mappings, including CFR endpoint direction,
  binary/multi-service/quantitative representations, and explicit
  representative-point conventions where the CFR gives a range.
- Keep criterion 2 spatial evidence unavailable until the planned adjacency
  stream is integrated, while accepting an analyst percentage with provenance.
- Never score zero-coverage LE as a valid zero or evaluate the threshold from
  an unavailable LE.
- Reject conflicting fact/override inputs and out-of-range analyst points;
  preserve explicit authority, rationale, verification, and provenance.
- Apply corridor statutory maxima/zeroing and reject geometry/project-type
  mismatches rather than mixing corridor and site semantics.
- Populate one documented coverage vocabulary and carry rating-source
  provenance into LESA summaries/notices.
- Ensure SA-MA cases are included in the Databricks dataset with geometry and
  expected facts sufficient to exercise the intended tools; keep judge evidence
  separate from deterministic contract evidence.
- Run `make check`; run `uv run pytest -m live_network` for changed upstream
  integration behavior; run the Databricks evaluation only where credentials
  are available, recording environment limitations without masking failures.

## Hazard Notes

- `lesa.py`, `models.py`, and `sda_client.py` are large or highly coupled;
  workers must use the anchors below and never read/rewrite entire files by
  default.
- Existing `awarded_points` behavior is an authority boundary. Do not silently
  reinterpret analyst overrides as machine estimates.
- The new registry must not encode unsupported regulatory assumptions as
  authoritative facts. Every band needs a citation/version and an explicit
  unavailable/unknown path.
- The adjacency criterion is intentionally unresolved. Any task that needs its
  source must preserve `unavailable`, not invent a proxy.
- Multi-county tests must distinguish selected-property values from NCCPI
  defaults and verify county-specific maxima independently.
- Do not add live network tests to the default path. Live SDA/NASS/TIGER tests
  must be marked `live_network` and use existing mock/live fixtures.
- Documentation must state that this remains preliminary screening and does
  not produce an official determination or signed form.

## Task Specifications

### 45.1.1 — Define Site Assessment question and scoring registry

**Repository:** `D:\workspace\fpac-soil-mcp`

**Files in scope**

- Must create: `src\fpac_soil_mcp\data\site_assessment.v1.json`,
  `src\fpac_soil_mcp\site_assessment.py`,
  `tests\test_site_assessment_contract.py`
- Can create: `planning\tasks\45.1.1.todo.md`
- Do not touch: public tools, prompts, models, existing scoring behavior

**Depends on:** none.

**Specification:** Define a versioned registry for the Site Assessment
criteria that includes regulatory wording, accepted answer type, percentage or
qualitative bands, point mappings, maximum points, citation, unavailable
semantics, and whether rationale/verification is required. Include an explicit
deferred adjacency criterion and ensure unknown/unavailable is not mapped to
zero. Add typed loaders/validators and focused tests for every criterion,
bounds, duplicate bands, missing citations, and deferred-source behavior.

**Grep anchors:** `SITE_CRITERIA_NAMES`, `CORRIDOR_CRITERIA_MAX_POINTS`,
`SiteAssessmentCriterion`, `evaluate_site_assessment`.

**Reference implementations:** `src\fpac_soil_mcp\data\regional_scoring.v1.json`,
`src\fpac_soil_mcp\official_sources.py`, `tests\test_sdv_contract.py`.

**Acceptance:** Registry loads deterministically; every criterion has a valid
max and citation; all mappings stay within statutory bounds; unknown and
adjacency-deferred inputs remain explicit unavailable states.

**Targeted test:** `uv run pytest tests\test_site_assessment_contract.py -q`

### 45.1.2 — Add typed incomplete/authority result semantics

**Files in scope**

- Must edit: `src\fpac_soil_mcp\models.py`, `src\fpac_soil_mcp\lesa.py`,
  `tests\test_lesa.py`, `tests\test_phase3_contracts.py` (dependent override
  fixture only)
- Can create: `planning\tasks\45.1.2.todo.md`
- Do not touch: registry JSON or MCP registration

**Depends on:** none.

**Specification:** Extend the Site Assessment/LESA result models and evaluator
so machine-estimated, analyst-proposed, unavailable, and verified states remain
distinct. Required missing subjective facts must yield an incomplete or
indeterminate result and a not-evaluated threshold state, never a zero-filled
complete result. Preserve criterion-specific limits and require rationale for
analyst-proposed overrides. Keep criterion 7 factual scoring compatible with
existing behavior where both farm sizes are present.

**Grep anchors:** `SiteAssessmentCriterion`, `SiteAssessmentSummary`,
`evaluate_site_assessment`, `evaluate_lesa`, `threshold_exceeded`.

**Reference implementations:** `authority.py`, `models.py` authority fields,
`_SiteAssessmentAggregator` in `corridor_scoring.py`.

**Acceptance:** Missing required inputs cannot produce a complete-looking
threshold determination; explicit unavailable is not converted to zero;
overrides without rationale fail validation; existing complete fixtures retain
their scores.

**Targeted test:** `uv run pytest tests\test_lesa.py -q -k "site or threshold or criterion"`

### 45.2.1 — Wire fact-based Site Assessment inputs and resource

**Files in scope**

- Must edit: `src\fpac_soil_mcp\tools\lesa_tools.py`,
  `src\fpac_soil_mcp\resources\fppa_resources.py`,
  `src\fpac_soil_mcp\resources\__init__.py`,
  `src\fpac_soil_mcp\app.py`, `tests\test_tools.py`,
  `manifest.yaml`, `eval\contract\test_contract.py`
- Must create: `tests\test_site_assessment_resource.py`
- Can create: `planning\tasks\45.2.1.todo.md`
- Do not touch: frontend or agent-app code

**Depends on:** 45.1.1, 45.1.2.

**Specification:** Add a read-only `fppa://site-assessment-criteria`
resource exposing the validated question/answer contract and add fact-based
Site Assessment inputs to `calculate_preliminary_lesa`. Route facts through
the registry scorer; return per-criterion rule, points, input authority,
rationale/verification state, and incomplete semantics. Keep explicit
point-based overrides labeled analyst-proposed and rationale-required.

**Grep anchors:** `calculate_preliminary_lesa`, `fppa://regulatory-notice`,
`register_resources`, `register_tools`.

**Reference implementations:** `resources\fppa_resources.py`,
`tools\lesa_tools.py`, `tests\test_map_tool_contracts.py`.

**Acceptance:** MCP resource and tool schemas are discoverable; representative
percentage and qualitative answers produce deterministic points; missing facts
return an indeterminate result; no siting recommendation is emitted.

**Targeted test:** `uv run pytest tests\test_site_assessment_resource.py tests\test_tools.py -q`

### 45.2.2 — Correct Site Assessment wording and close authority gaps

**Files in scope**

- Must edit: `src\fpac_soil_mcp\constants.py`,
  `src\fpac_soil_mcp\fppa.py`,
  `src\fpac_soil_mcp\prompts\fppa_prompts.py`,
  `tests\test_fppa.py`, `tests\test_prompts.py`, `tests\test_server.py`
- Can create: `planning\tasks\45.2.2.todo.md`
- Do not touch: scoring engine or data clients

**Depends on:** 45.1.1.

**Specification:** Align criterion names and Part VI language with the
regulation and registry. Remove language that suggests selecting sites,
footprints, or preferred alternatives. Preserve the preliminary-screening
notice and state the regulatory consequence of scores without proposing an
alternative. Ensure guided prompts instruct clients to use the question
resource, record unknowns, and never invent points.

**Grep anchors:** `SITE_CRITERIA_NAMES`, `Part V`, `Part VI`,
`fppa_site_assessment_assistant`, `LESA_ACTION_`.

**Reference implementations:** `planning\RESEARCH_GUIDED_LESA_SITE_ASSESSMENT.md`,
`constants.py` regulatory notices.

**Acceptance:** Wording tests reject stale Part V/site-selection language and
retain the authority disclaimer; prompt tests require unknown handling and
non-prescriptive alternatives language.

**Targeted test:** `uv run pytest tests\test_fppa.py tests\test_prompts.py -q`

### 45.3.1 — Preserve selected metadata property through polygon/corridor aggregation

**Files in scope**

- Must edit: `src\fpac_soil_mcp\polygon_analysis.py`,
  `src\fpac_soil_mcp\corridor_analysis.py`,
  `src\fpac_soil_mcp\lesa.py`, `tests\test_polygon_analysis.py`,
  `tests\test_corridor_analysis.py`
- Must create: `tests\test_multi_county_productivity.py`
- Can create: `planning\tasks\45.3.1.todo.md`
- Do not touch: metadata registry definitions

**Depends on:** 45.1.1.

**Specification:** Trace the selected validated productivity property from
input through county partitioning, map-unit rows, LE normalization, and
unified LESA results for polygon and corridor paths. Ensure no path silently
falls back to NCCPI, and preserve selected-property provenance and caveats.
Add synthetic multi-county fixtures for differing county maxima and partial
coverage.

**Grep anchors:** `productivity_index`, `get_productivity_ratings`,
`get_county_max_productivity_rating`, `county_segments`,
`evaluate_land_evaluation`.

**Reference implementations:** `sda_client.py` registry dispatch,
`tests\test_sdv_strategies.py`, corridor segment processing.

**Acceptance:** CSR2, CPI, Storie, and NCCPI synthetic cases retain their
selected property across polygon/corridor/unified paths; county maxima are
property-specific; provenance matches the selected registry entry.

**Targeted test:** `uv run pytest tests\test_multi_county_productivity.py tests\test_polygon_analysis.py tests\test_corridor_analysis.py -q`

### 45.3.2 — Reconcile coverage, county maxima, and provenance

**Files in scope**

- Must edit: `src\fpac_soil_mcp\sda_client.py`, `src\fpac_soil_mcp\models.py`,
  `tests\test_sdv_contract.py`
- Can create: `planning\tasks\45.3.2.todo.md`
- Do not touch: Site Assessment registry or prompts

**Depends on:** 45.3.1.

**Specification:** Verify and correct missing county metadata, missing county
maxima, partial rated coverage, direct/indirect/urban/unmapped/unrated
acreage reconciliation, and stable selected-property provenance. Keep all SQL
registry-derived and preserve explicit upstream error/coverage states.

**Grep anchors:** `build_sdv_county_max_query`, `get_county_max_productivity_rating`,
`rated_acreage`, `unrated_acreage`, `coverage_percent`, `reconciliation`.

**Reference implementations:** `docs\sdv-metadata-contract.md`,
`tests\fixtures\sdv_contract_cases.json`, `tests\test_corridor_map.py`.

**Acceptance:** Missing metadata/maxima and partial coverage produce explicit
statuses/caveats; acreage reconciliation is within the documented tolerance;
selected-property provenance remains stable; no user SQL reaches the builder.

**Targeted test:** `uv run pytest tests\test_sdv_contract.py tests\test_multi_county_productivity.py -q`

### 45.4.1 — Build deterministic Phase 4 gold-set evidence

**Files in scope**

- Must create: `tests\fixtures\phase4_gold_set.json`,
  `tests\test_phase4_gold_set.py`
- Must edit: `eval\common\dataset.py`, `eval\common\matching.py`,
  `eval\contract\test_contract.py`
- Can create: `planning\tasks\45.4.1.todo.md`
- Do not touch: model-judge configuration

**Depends on:** 45.2.1, 45.3.2.

**Specification:** Add versioned deterministic cases covering all supported
metadata source-table strategies, selected-property multi-county aggregation,
no-rated and partial coverage, urban partial overlap, missing subjective
inputs, authority/provenance, and failure semantics. Make contract results
machine-checkable and distinguish exact values from tolerances and expected
indeterminate states.

**Grep anchors:** dataset loader, matcher, contract test registration.

**Reference implementations:** `tests\fixtures\sdv_contract_cases.json`,
`eval\common\dataset.py`, `eval\contract\test_contract.py`.

**Acceptance:** Gold-set cases load deterministically, cover every issue #14
exit criterion, and fail if unavailable values become zero or subjective
points are fabricated. The deterministic contract suite is the release gate.

**Targeted test:** `uv run pytest tests\test_phase4_gold_set.py eval\contract\test_contract.py -q`

### 45.4.2 — Separate model-assisted evidence and retain diagnostics

**Files in scope**

- Must edit: `eval\pi\test_agent_eval.py`, `eval\databricks\scorers.py`,
  `eval\eval_cases.v1.json`
- Must create: `planning\evidence\45.4.2-evaluation.md`
- Can create: `planning\tasks\45.4.2.todo.md`
- Do not touch: deterministic gold-set fixtures

**Depends on:** 45.4.1.

**Specification:** Add or update model-assisted cases for guided Site
Assessment, missing-input handling, no-siting-recommendation behavior, and
selected-property explanations. Record deterministic contract results
separately from Pi/Databricks judge results. Retain sanitized parser and
diagnostic artifacts only, with reproducible commands and exact counts.

**Grep anchors:** eval case IDs, scorer registration, Pi artifact handling.

**Reference implementations:** `eval\databricks\scorers.py`,
`eval\pi\test_agent_eval.py`, `planning\RESEARCH_EVAL_FAILURES_30.md`.

**Acceptance:** Evidence report states which results are deterministic gates
and which are model-assisted; parser diagnostics are reproducible; no
evaluation case rewards a siting recommendation or fabricated score.

**Targeted test:** `uv run pytest eval\pi\test_agent_eval.py eval\databricks\test_databricks_scorers.py -q`

### 45.4.3 — Synchronize milestone docs and closeout evidence

**Files in scope**

- Must edit: `planning\MASTER_PLAN.md`, `README.md`, `manifest.yaml`,
  `server.json`, `planning\STATE_45.md`
- Must create: `planning\evidence\45.4.3-closeout.md`,
  `planning\REVIEW_45.md`
- Can create: `planning\tasks\45.4.3.todo.md`
- Do not touch: feature implementation files unless a documentation check
  identifies a direct stale reference

**Depends on:** 45.4.1, 45.4.2.

**Specification:** Synchronize Phase 4 status, public tool/resource contracts,
metadata-driven routing language, subjective scoring limitations, deferred
adjacency source, issue #29 urban-overlap completion, and remaining
limitations. Mark Plan 26 as superseded or historical context where it still
implies NCCPI-only behavior. Record exact targeted, offline, relevant live,
lint, format, and evaluation results. Perform independent spec and standards
reviews of this plan’s implementation tree.

**Grep anchors:** `Phase 4`, `cointerp-only`, `NCCPI-only`, `urban overlap`,
`preliminary`, `manifest`, `server`.

**Reference implementations:** `planning\STATE_44.md`,
`planning\REVIEW_44.md`, `docs\decisions\0014-registry-validated-sdv-metadata-contract.md`.

**Acceptance:** No stale cointerp-only/NCCPI-only claim remains in active
documentation; all public surfaces agree; closeout evidence contains exact
commands/results and explicit deferred items; review has no unresolved
spec/standards findings.

**Targeted test:** `make check` followed serially by relevant live/evaluation
commands recorded in `planning\evidence\45.4.3-closeout.md`.

