# EXECUTION PLAN 26: Correct SDA Productivity Contracts and Eval Semantics

## Goal & Scope

**Goal**: Resolve the evaluation findings around false zero productivity
ratings, ambiguous SDA productivity selectors, geometry/acreage mismatches, and
intermittent missing-tool reports. The implementation must map the public
productivity options only to deterministic SDA-backed behavior, represent
missing LE data as unavailable rather than zero, correct the 45-acre eval
fixture, and make the agent eval distinguish missing server tools from an agent
that failed to call an advertised tool.

**In scope**
- Restrict the fixed productivity selector contract to the currently reliable
  national NCCPI SDA interpretation.
- Remove silent generic CSR2/CPI/Storie query paths; reserve precise
  `sdvattribute` selection for a future feature.
- Prevent zero-rated coverage from producing a valid zero LE score or a
  below-threshold LESA determination.
- Correct LESA-02 geometry to represent the stated 45-acre project and add
  discrepancy regression coverage.
- Improve MCP tool-list assertions, structured diagnostics, and one bounded
  retry in the agent eval runner.
- Add deterministic mocked tests and opt-in live SDA rule-catalog coverage.

**Out of scope**
- Adding a new public `sdvattribute`/rule identifier parameter.
- Implementing CSR2, generic CPI, or generic Storie support.
- Selecting a preferred CPI state, crop, irrigation, or soil condition rule.
- Documentation or metadata that advertises unsupported productivity options.
- Making live-network or model-based evals part of the default offline suite.
- Unrelated geometry, regulatory, or tool-registration refactors.

**Verbatim constraints**
- “we absolutely should not be adding documentation changes for things that do not work.”
- “we need to make sure that our enum of options maps cleanly to the types of things we can readily get from SDA.”
- “we have been over this issue with the 45 acre project not matching the dimensions of the actual geometry.”
- “we should either not be saying it is 45 acres, use a different polygon, or use the correct acreage.”

## Reconnaissance Log

- Repository: `D:\workspace\fpac-soil-mcp`; Python 3.11+, `uv`, pytest, Ruff.
- Current green baseline before this orchestration: 328 passed, 12 deselected
  for `uv run pytest -m "not live_network"`; Ruff lint and format checks pass.
- `sda_client.py` is 1193 lines; use anchors around
  `_normalize_productivity_index`, `get_productivity_ratings`,
  `lookup_sdv_attribute`, and `get_available_interpretation_rules`.
- `lesa.py` is 792 lines; `evaluate_land_evaluation` currently converts no
  rated acreage to candidate score `0.0`; `corridor_scoring.py` already has
  the desired `threshold_exceeded=None` / LE-unavailable pattern.
- `soil_tools.py` registers `analyze_farmland_by_polygon`,
  `calculate_preliminary_lesa`, and `analyze_corridor_fppa`; all expected tools
  exist in source and are registered.
- `eval/run_evals.py` launches the repository through `uv --directory ... run
  fpac-soil-mcp`; its expected-tool check currently reports missing tools when
  the agent skips a call but does not assert the initialized MCP tool list.
- Live SDA rule discovery returned one national NCCPI rule, no CSR2 rule, many
  state/crop/condition-specific CPI rules, and one California Storie rule.
- Full suites must run serially; worker tasks run targeted tests only. Maximum
  two concurrent workers.

## Decision Log

- **2026-10-05**: Treat CSR2 as unsupported unless a future explicit,
  validated `sdvattribute` selector is introduced; do not use guessed
  `cointerp` name matching.
- **2026-10-05**: Generic CPI is ambiguous and must not select a rule
  automatically; precise CPI selection is deferred.
- **2026-10-05**: Zero rated acreage is unavailable/indeterminate, not a valid
  zero LE score; threshold status must be `None`/indeterminate.
- **2026-10-05**: Correct LESA-02 to a genuinely ~45-acre geometry and keep
  discrepancy handling as a separate regression concern.
- **2026-10-05**: If an expected tool is advertised but not called, retry once
  and then fail with structured diagnostics; if it is not advertised, fail
  immediately as an MCP/configuration defect.
- **2026-10-05**: Do not add documentation describing unsupported CSR2/CPI/
  Storie behavior; the public fixed enum must reflect reliable SDA support.
- **2026-10-05**: Retain conditional agent eval and opt-in live-network tests;
  always require deterministic tests, offline pytest, and Ruff.
- **2026-10-05**: Use at most two concurrent workers; serialize same-file work
  and full-suite verification.

## Wave & Dependency Table

| Wave | Task | Title | Files in scope | Depends on |
|---|---|---|---|---|
| 1 | 26.1.1 | Align selectors and unavailable LE semantics | `src/fpac_soil_mcp/models.py`, `src/fpac_soil_mcp/integration_models.py`, `src/fpac_soil_mcp/sda_client.py`, `src/fpac_soil_mcp/lesa.py`, `src/fpac_soil_mcp/corridor_scoring.py`, `planning/tasks/26.1.1.todo.md` | none |
| 2 | 26.2.1 | Propagate selector validation through tools | `src/fpac_soil_mcp/polygon_analysis.py`, `src/fpac_soil_mcp/corridor_analysis.py`, `src/fpac_soil_mcp/tools/soil_tools.py`, `planning/tasks/26.2.1.todo.md` | 26.1.1 |
| 3 | 26.3.1 | Add productivity and LESA regression tests | `tests/test_sda_client.py`, `tests/test_corridor_scoring.py`, `tests/test_lesa.py`, `tests/test_polygon_analysis.py`, `tests/test_corridor_analysis.py`, `tests/test_tools.py`, `planning/tasks/26.3.1.todo.md` | 26.1.1, 26.2.1 |
| 3 | 26.3.2 | Correct the 45-acre evaluation fixture | `eval/prompt_test_cases.json`, `tests/test_geometry.py`, `planning/tasks/26.3.2.todo.md` | none |
| 3 | 26.3.3 | Diagnose and retry missing eval tools | `eval/run_evals.py`, `eval/test_agent_eval.py`, `planning/tasks/26.3.3.todo.md` | none |
| 4 | 26.4.1 | Add opt-in SDA rule catalog coverage | `tests/test_live_sda.py`, `planning/tasks/26.4.1.todo.md` | 26.1.1 |
| 5 | 26.5.1 | Run complete verification | `planning/STATE_26.md`, `planning/tasks/26.5.1.todo.md` | 26.3.1, 26.3.2, 26.3.3, 26.4.1 |
| 5 | 26.5.2 | Correct verification formatting failures | `eval/run_evals.py`, `eval/test_agent_eval.py`, `tests/test_geometry.py`, `planning/STATE_26.md`, `planning/tasks/26.5.2.todo.md` | 26.5.1 |
| 6 | 26.6.1 | Remove premature selector surfaces | `src/fpac_soil_mcp/models.py`, `src/fpac_soil_mcp/sda_client.py`, `src/fpac_soil_mcp/lesa.py`, `src/fpac_soil_mcp/tools/soil_tools.py`, `src/fpac_soil_mcp/corridor_analysis.py`, `README.md`, `manifest.yaml`, `server.json`, `eval/prompt_test_cases.json`, `tests/fixtures/le_benchmarks.json`, `tests/test_sda_client.py`, `tests/test_lesa.py`, `tests/test_corridor_analysis.py`, `tests/test_tools.py`, `tests/test_live_sda.py`, `planning/STATE_26.md`, `planning/tasks/26.6.1.todo.md` | 26.5.2 |
| 7 | 26.7.1 | Harden eval subprocess failure handling | `eval/run_evals.py`, `eval/test_agent_eval.py`, `planning/STATE_26.md`, `planning/tasks/26.7.1.todo.md` | 26.6.1 |

## Task Specifications

### 26.1.1 — Align selectors and unavailable LE semantics
- **Repo**: `AndrewBrown-USDA/fpac-soil-mcp`
- **Files in scope**: `src/fpac_soil_mcp/models.py`,
  `src/fpac_soil_mcp/integration_models.py`,
  `src/fpac_soil_mcp/sda_client.py`, `src/fpac_soil_mcp/lesa.py`,
  `src/fpac_soil_mcp/corridor_scoring.py`,
  `planning/tasks/26.1.1.todo.md`
- **Depends on**: none
- **Spec**: Make the fixed productivity enum and SDA client contract match the
  live catalog. Keep deterministic national NCCPI support. Remove or reject
  generic CSR2, CPI, and Storie paths rather than issuing broad `LIKE` queries
  that return empty ratings. Preserve a future seam for explicit
  `sdvattribute` selection without adding that public parameter now. The
  internal seam is the existing `attribute_meta`/`build_dynamic_sdv_query`
  path: it must remain explicit, metadata-validated, and separate from fixed
  selector normalization; no public caller is added in this task. Also make
  zero rated acreage unavailable/indeterminate and route threshold evaluation
  through the existing LE-unavailable semantics.
- **Constraints**: Do not add unsupported documentation; do not choose a
  state/crop CPI rule automatically; do not add arbitrary SQL; preserve valid
  NCCPI behavior and existing response provenance.
- **Grep anchors**: `_normalize_productivity_index`,
  `get_productivity_ratings`, `lookup_sdv_attribute`,
  `get_available_interpretation_rules`, `productivity_index`.
- **Reference implementations**: exact NCCPI branch in
  `SDAClient.get_productivity_ratings`; existing `CUSTOM` rejection and
  `corridor_analysis._normalize_productivity_index`.
- **Acceptance**: `uv run pytest tests\test_sda_client.py tests\test_lesa.py tests\test_corridor_scoring.py -q` passes; unsupported selectors fail before SDA retrieval; zero coverage yields `threshold_exceeded=None`; valid zero ratings remain scoreable. Tests preserve the existing explicit `attribute_meta` query seam. Public metadata/documentation is audited and intentionally unchanged because unsupported options are not advertised.

### 26.2.1 — Propagate selector validation through tools
- **Repo**: `AndrewBrown-USDA/fpac-soil-mcp`
- **Files in scope**: `src/fpac_soil_mcp/polygon_analysis.py`,
  `src/fpac_soil_mcp/corridor_analysis.py`,
  `src/fpac_soil_mcp/tools/soil_tools.py`,
  `planning/tasks/26.2.1.todo.md`
- **Depends on**: 26.1.1
- **Spec**: Route polygon, corridor, and LESA tool entry points through the
  shared fixed-selector validator. Every public entry point must reject the
  same unsupported CSR2/CPI/Storie values before any SDA productivity query,
  while preserving NCCPI behavior and partial coverage.
- **Constraints**: Do not weaken partial-coverage results; do not change the
  statutory threshold value; do not duplicate divergent determination text.
- **Grep anchors**: `evaluate_land_evaluation`, `evaluate_lesa_threshold`,
  `combine_lesa_scores`, `threshold_exceeded`, `candidate_le_score`.
- **Reference implementations**: `corridor_scoring.combine_lesa_scores`
  handling of `land_evaluation is None` and existing LE-unavailable constants.
- **Acceptance**: `uv run pytest tests\test_polygon_analysis.py tests\test_corridor_analysis.py tests\test_tools.py -q` passes; all three entry-point families reject unsupported selectors consistently and do not invoke SDA for rejected values.

### 26.3.1 — Add productivity and LESA regression tests
- **Repo**: `AndrewBrown-USDA/fpac-soil-mcp`
- **Files in scope**: `tests/test_sda_client.py`,
  `tests/test_polygon_analysis.py`, `tests/test_corridor_analysis.py`,
  `tests/test_corridor_scoring.py`, `tests/test_lesa.py`,
  `tests/test_tools.py`, `planning/tasks/26.3.1.todo.md`
- **Depends on**: 26.1.1, 26.2.1
- **Spec**: Add deterministic mocked coverage for selector rejection,
  exact NCCPI support, zero rated acreage, valid zero ratings, partial
  coverage, and indeterminate LESA threshold output across site and corridor
  paths. Assert the SDA query does not run for rejected generic selectors.
- **Constraints**: Offline mocks only; preserve existing supported NCCPI and
  partial-coverage assertions; do not encode current live SDA responses as
  brittle unit fixtures.
- **Grep anchors**: existing productivity parametrization, no-rated map-unit
  tests, `combine_lesa_scores`, `evaluate_land_evaluation`, tool mocks.
- **Reference implementations**: `tests/test_corridor_scoring.py` LE-unavailable
  cases and `tests/test_lesa.py` coverage cases.
- **Acceptance**: `uv run pytest tests\test_sda_client.py tests\test_corridor_scoring.py tests\test_lesa.py tests\test_polygon_analysis.py tests\test_corridor_analysis.py tests\test_tools.py -q` passes with assertions proving zero coverage is not a below-threshold result.

### 26.3.2 — Correct the 45-acre evaluation fixture
- **Repo**: `AndrewBrown-USDA/fpac-soil-mcp`
- **Files in scope**: `eval/prompt_test_cases.json`, `tests/test_geometry.py`,
  `planning/tasks/26.3.2.todo.md`
- **Depends on**: none
- **Spec**: Replace LESA-02’s approximately 909-acre polygon with a valid
  approximately 45-acre polygon while retaining the stated project facts.
  Add deterministic geometry coverage for the corrected acreage. A separate
  discrepancy regression must assert that geometry acreage remains the
  evaluated AOI acreage, while any stated affected-farm acreage remains
  separate and does not silently clip or override the geometry.
- **Constraints**: Do not silently reinterpret affected-farm acreage as AOI
  acreage; do not change unrelated eval cases; do not add an intentional
  mismatch to the normal LESA-02 case.
- **Grep anchors**: `LESA-02`, `sample_geometry`, polygon acreage helpers,
  `calculate_preliminary_lesa`.
- **Reference implementations**: `tests/test_aoi_fixtures.py` acreage tolerance
  and existing geometry validation tests.
- **Acceptance**: `uv run pytest tests\test_geometry.py -q` passes; the corrected polygon is within 0.1% or 0.05 acre of 45 acres; discrepancy coverage proves geometry acreage is not overridden by a separate farm-acreage input.

### 26.3.3 — Diagnose and retry missing eval tools
- **Repo**: `AndrewBrown-USDA/fpac-soil-mcp`
- **Files in scope**: `eval/run_evals.py`, `eval/test_agent_eval.py`,
  `planning/tasks/26.3.3.todo.md`
- **Depends on**: none
- **Spec**: Capture the initialized MCP tool list from the structured
  initialization event when present, with tool-list output as the only
  fallback. If neither is captured, classify the case as configuration/
 diagnostic failure, not as an agent skip. Distinguish an unadvertised tool
  from an advertised tool that the agent skipped, and retry the latter once.
  On final failure, include tool-list, expected-tool, and structured-event
  diagnostics without accepting prose as a substitute for execution.
- **Constraints**: Do not weaken exact tool-name matching; do not parse tool
  names from flattened assistant prose; keep retries bounded to one; preserve
  existing pi event compatibility.
- **Grep anchors**: `extract_structured_tool_names`, `run_case`,
  `missing_tools`, `parse_pi_events`, agent-eval assertions.
- **Reference implementations**: existing structured event extraction and
  POINT-01 argument validation from orchestration 25.
- **Acceptance**: `uv run pytest eval\test_agent_eval.py -m "not agent_eval" -q` passes; deterministic tests cover advertised-but-skipped, unadvertised, unknown-tool-list, and successfully-called cases with no infinite retry.

### 26.4.1 — Add opt-in SDA rule catalog coverage
- **Repo**: `AndrewBrown-USDA/fpac-soil-mcp`
- **Files in scope**: `tests/test_live_sda.py`,
  `planning/tasks/26.4.1.todo.md`
- **Depends on**: 26.1.1
- **Spec**: Add live-network tests that verify the national NCCPI rule is
  discoverable and that the fixed public selector rejects CSR2 without
  requiring CSR2 to be absent from the live SDA catalog. Keep assertions
  tolerant of catalog additions.
- **Constraints**: Mark all tests `live_network`; do not make external
  availability part of the default suite; do not assert unstable full catalog
  contents.
- **Grep anchors**: existing live interpretation tests and rule discovery.
- **Reference implementations**: current `tests/test_live_sda.py` markers and
  `SDAClient.get_available_interpretation_rules`.
- **Acceptance**: opt-in live tests pass when SDA is available and are excluded
  from the default command.

### 26.5.1 — Run complete verification
- **Repo**: `AndrewBrown-USDA/fpac-soil-mcp`
- **Files in scope**: `planning/STATE_26.md`,
  `planning/tasks/26.5.1.todo.md`
- **Depends on**: 26.3.1, 26.3.2, 26.3.3
- **Spec**: Run the targeted tests, full offline suite, Ruff lint/format, and
  conditional affected agent evals. Record exact counts, skipped live/model
  gates, and any deviations.
- **Constraints**: Full suite runs serially; do not require live SDA or pi when
  unavailable; no unrelated cleanup.
- **Grep anchors**: `STATE_26.md` baseline and wave board.
- **Reference implementations**: `planning/STATE_25.md` verification report.
- **Acceptance**: run serially and record exact results for:
  `uv run pytest -m "not live_network"`,
  `uv run ruff check .`, and `uv run ruff format --check .`.
  If `pi` is available, run `uv run pytest eval\test_agent_eval.py -m agent_eval -k "point_screening or affected_productivity_cases"`;
  otherwise record the agent gate as skipped. If network access is available,
  run `uv run pytest tests\test_live_sda.py -m live_network -k "rule or productivity"`;
  otherwise record the live gate as skipped. Task 26.4.1 is non-blocking when
  its live gate is unavailable.

### 26.5.2 — Correct verification formatting failures
- **Repo**: `AndrewBrown-USDA/fpac-soil-mcp`
- **Files in scope**: `eval/run_evals.py`, `eval/test_agent_eval.py`,
  `tests/test_geometry.py`, `planning/STATE_26.md`,
  `planning/tasks/26.5.2.todo.md`
- **Depends on**: 26.5.1
- **Spec**: Apply only Ruff-required import ordering and formatting changes
  identified by task 26.5.1. Preserve behavior and do not refactor.
- **Acceptance**: `uv run ruff check .`, `uv run ruff format --check .`, and
  affected deterministic tests pass.

### 26.6.1 — Remove premature selector surfaces
- **Repo**: `AndrewBrown-USDA/fpac-soil-mcp`
- **Files in scope**: the files listed in the wave table.
- **Depends on**: 26.5.2
- **Spec**: Simplify the public and test contract to the validated national
  NCCPI selector. Remove speculative CSR2/CPI/Storie/CUSTOM members, caller
  descriptions, provenance claims, eval prompts, and normal-path tests that
  treat those selectors as available features. Remove dead fixed-query
  templates/provenance branches that are no longer reachable, while retaining
  the explicit metadata-validated dynamic SDV seam for future support. Keep
  one narrow invalid-selector rejection test using a generic unsupported value,
  not invented product selectors. Do not change the NCCPI behavior or
  unrelated eval cases.
- **Acceptance**: targeted tests for models, SDA, LESA, polygon/corridor tools,
  and eval fixtures pass; `uv run pytest -m "not live_network"`,
  `uv run ruff check .`, and `uv run ruff format --check .` pass; public
  metadata contains no claims that CSR2/CPI/Storie are supported.

### 26.7.1 — Harden eval subprocess failure handling
- **Repo**: `AndrewBrown-USDA/fpac-soil-mcp`
- **Files in scope**: `eval/run_evals.py`, `eval/test_agent_eval.py`,
  `planning/STATE_26.md`, `planning/tasks/26.7.1.todo.md`
- **Depends on**: 26.6.1
- **Spec**: Ensure every `run_case` result has an elapsed duration even when
  subprocess startup or execution raises before normal completion. Preserve the
  existing failure status and diagnostic message; do not let one failed eval
  case crash the entire eval run. Add deterministic regression coverage.
- **Acceptance**: `uv run pytest eval\test_agent_eval.py -m "not agent_eval" -q`
  passes, and a direct failure-path check proves `run_case` returns a structured
  failure with `elapsed_sec` instead of raising `UnboundLocalError`.
