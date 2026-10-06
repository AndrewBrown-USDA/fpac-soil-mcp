# EXECUTION PLAN 23: Correct Generic Productivity Ratings and LESA Routing

## Goal & Scope

**Goal**: Resolve the code-review findings and comprehensively test their
validity. Replace NCCPI-specific output fields with generic productivity-rating
fields that identify the SDA interpretation/catalog provenance, make CSR2/CPI/
Storie scoring and corridor routing use the requested index consistently,
normalize invalid index inputs safely, complete public documentation, and
verify the result with focused offline tests plus the full offline/Ruff gates.

**In scope**
- Add generic productivity rating, class, and provenance fields to the public
  soil map-unit response model.
- Remove the confusing `nccpi_rating` and `nccpi_class` aliases.
- Make polygon scoring use the requested index's rating data and benchmark.
- Make corridor and explicit `project_type="corridor"` routing honor index,
  benchmark, buffer, and geometry semantics.
- Preserve normalized `ProductivityIndexType` in all LESA summaries and map
  unsupported strings to the repository's `CUSTOM` behavior.
- Update README and manifest documentation for the public schema/tool surface.
- Add regression and contract tests, then run targeted and full offline/Ruff
  verification.

**Out of scope**
- Live-network execution as a required gate.
- New statutory thresholds, new external dependencies, or broad LESA scoring
  redesign.
- Changing corridor algorithms in `corridor_analysis.py`.
- Reintroducing NCCPI aliases for compatibility; the user explicitly requested
  their removal to avoid future confusion.
- Implementing unrelated review findings already resolved by orchestration 21
  or 22 unless a regression test exposes one.

**Verbatim constraints**
- “we need generic probability fields with an additional field that identifies
  the provenance of the productivity rating i.e. name of interp or similar
  column source from sdv catalog”
- “I would like to hard-remove NCCPI aliases just to avoid confusion, retaining
  them will just cause problems as we try to pivot down the road”
- “comprehensively test their validity”
- Use targeted offline tests, the full offline suite, and Ruff; live tests
  remain opt-in.

## Reconnaissance Log

- Repository: `D:\workspace\fpac-soil-mcp`; Python 3.11+, `uv`, pytest, Ruff.
- Current baseline: `uv run pytest -m "not live_network"` — 280 passed,
  12 deselected, 0 failed in 32.83s.
- Relevant file sizes: `models.py` 540 lines, `polygon_analysis.py` 502,
  `lesa.py` 787, `soil_tools.py` 535, `tests/test_tools.py` 535,
  `tests/test_polygon_analysis.py` 302, `tests/test_lesa.py` 613.
  Workers must use grep anchors rather than whole-file reads.
- Conventions: `AGENTS.md` requires explicit validation/errors, centralized
  regulatory language, mocked tests, public README/manifest/server updates,
  and opt-in live tests. `pyproject.toml` sets Ruff line length 100 and pytest
  markers/defaults.
- Existing references: `polygon_analysis.py` index normalization and
  `get_productivity_ratings` branch; `lesa.py::_normalize_productivity_index`;
  `corridor_analysis.py::analyze_corridor`; `geometry.py` WKT/buffer helpers;
  `tests/test_lesa.py` fallback tests; `tests/test_tools.py` corridor routing
  tests; `tests/test_phase2_contracts.py` and `tests/test_phase3_contracts.py`
  public contracts.
- The current Plan 22 state records a green baseline but also documents that
  polygon-corridor routing was tested with a parser mock rather than the real
  geometry branch. This is a required regression gap.
- Full test suites must run serially; workers run only task-targeted tests.
  Limit orchestration concurrency to two workers.

## Decision Log

- **2026-09-30**: Use dependency-first order: schema/provenance, then polygon
  scoring and LESA routing, then docs/tests, then global verification.
- **2026-09-30**: Add generic `productivity_rating`,
  `productivity_rating_class`, and `productivity_rating_source` fields; remove
  `nccpi_rating` and `nccpi_class` rather than retaining aliases.
- **2026-09-30**: `productivity_rating_source` records the SDA interpretation
  rule/catalog provenance used for the rating; non-NCCPI paths must not be
  mislabeled as NCCPI.
- **2026-09-30**: Preserve existing public defaults where compatible, but the
  explicit NCCPI alias removal is an intentional breaking schema change.
- **2026-09-30**: Allow at most two concurrent workers; serialize tasks that
  touch the same file or depend on generated schema.
- **2026-09-30**: Use cheapest capable workers, one acceptance retry, then
  mid-tier escalation; no worker runs live-network tests.
- **2026-09-30**: Acceptance requires targeted tests, the full offline suite,
  `ruff check`, and `ruff format --check`.

## Finding-to-Task Traceability

| Finding / requirement | Task |
|---|---|
| Generic productivity fields and SDA provenance | 23.1.1, 23.1.2 |
| Non-NCCPI polygon scoring | 23.2.1, 23.3.1 |
| Explicit corridor project routing | 23.2.2, 23.3.2 |
| Normalized invalid-index handling and LESA fallbacks | 23.2.2, 23.3.3 |
| README/manifest public-surface documentation | 23.3.4 |
| Comprehensive offline and lint validation | 23.4.1 |
| Missing README and manifest updates | 23.3.4 |
| Unused benchmark override / speculative parameter | 23.2.2, 23.3.2 |
| Non-NCCPI corridor propagation | 23.2.2, 23.3.2 |
| Polygon corridor semantics | 23.2.2, 23.3.2 |
| Direct enum failure for unsupported indexes | 23.2.2, 23.3.3 |

## Wave & Dependency Table

| Wave | Task | Title | Files in scope | Depends on |
|---|---|---|---|---|
| 1 | 23.1.1 | Generalizing productivity response fields | `src/fpac_soil_mcp/models.py` | none |
| 1 | 23.1.2 | Defining rating provenance contract | `src/fpac_soil_mcp/sda_client.py` | none |
| 2 | 23.2.1 | Scoring requested polygon productivity indexes | `src/fpac_soil_mcp/polygon_analysis.py` | 23.1.1, 23.1.2 |
| 2 | 23.2.2 | Correcting LESA routing and normalization | `src/fpac_soil_mcp/tools/soil_tools.py`, `src/fpac_soil_mcp/lesa.py` | 23.1.1 |
| 3 | 23.3.1 | Testing generic polygon ratings | `tests/test_polygon_analysis.py`, `tests/test_models.py` | 23.2.1 |
| 3 | 23.3.2 | Testing corridor routing and propagation | `tests/test_tools.py` | 23.2.2 |
| 3 | 23.3.3 | Testing LESA fallback and invalid indexes | `tests/test_lesa.py` | 23.2.2 |
| 3 | 23.3.4 | Updating public rating documentation | `README.md`, `manifest.yaml` | 23.1.1, 23.2.1, 23.2.2 |
| 4 | 23.4.1 | Running complete offline verification | `planning/STATE_23.md` | 23.3.1, 23.3.2, 23.3.3, 23.3.4 |

## Task Specifications

### 23.1.1 — Generalizing productivity response fields
- **Repo**: `AndrewBrown-USDA/fpac-soil-mcp`
- **Files in scope**: `src/fpac_soil_mcp/models.py`
- **Depends on**: none
- **Spec**: Replace `SoilMapUnitAcreage.nccpi_rating` and `nccpi_class` with
  generic `productivity_rating`, `productivity_rating_class`, and
  `productivity_rating_source` fields. Use precise optional types and
  descriptions that cover SDA interpretation/catalog provenance. Do not add
  aliases or silently accept the removed names. Preserve all unrelated model
  fields and response serialization conventions.
- **Do not touch**: analysis code, tools, manifests, or dependencies. The
  focused model contract test is owned by task 23.3.1.
- **Grep anchors**: `class SoilMapUnitAcreage`, `nccpi_rating`, `nccpi_class`,
  `FarmlandCategoryBreakdown`.
- **Reference**: existing `Field` descriptions in `models.py` and
  `integration_models.py`.
- **Acceptance**: `uv run python -c "from fpac_soil_mcp.models import SoilMapUnitAcreage"`.

### 23.1.2 — Defining rating provenance contract
- **Repo**: `AndrewBrown-USDA/fpac-soil-mcp`
- **Files in scope**: `src/fpac_soil_mcp/sda_client.py`
- **Depends on**: none
- **Spec**: Trace `get_productivity_ratings` and related interpretation parsing.
  Ensure every returned rating can carry the source rule/catalog name without
  relabeling CSR2/CPI/Storie as NCCPI. Reuse existing SDA row keys and
  validation; do not add arbitrary SQL or network behavior. If the client
  already returns sufficient provenance, make the smallest normalization-only
  change and record the exact source key in the function docstring or typed
  return contract for downstream use.
- **Do not touch**: models, polygon analysis, tools, tests, or query templates
  except where the existing client contract requires a narrowly scoped helper.
- **Grep anchors**: `get_productivity_ratings`, `get_interpretations`,
  `rule_name`, `numeric_rating`, `rating_class`.
- **Reference**: `get_interpretations` catalog validation and existing SDA
  response parsing.
- **Acceptance**: `uv run pytest tests/test_sda_client.py`.

### 23.2.1 — Scoring requested polygon productivity indexes
- **Repo**: `AndrewBrown-USDA/fpac-soil-mcp`
- **Files in scope**: `src/fpac_soil_mcp/polygon_analysis.py`
- **Depends on**: 23.1.1, 23.1.2
- **Spec**: Use one generic rating representation for NCCPI and non-NCCPI
  paths. Populate the requested index's numeric value, class, and provenance;
  compute rated acreage, county-relative weighting, and candidate LE from that
  same representation. Preserve sentinel handling, area-symbol partitions,
  benchmark overrides, warnings, and response shape except for the intentional
  generic field rename. Ensure `include_nccpi=False` still avoids unnecessary
  NCCPI calls when the requested index is NCCPI, while non-NCCPI requests use
  their supported rating path.
- **Do not touch**: corridor algorithms, tools, models, tests, or SDA query
  templates.
- **Grep anchors**: `analyze_polygon`, `ratings_requested`, `rating_map`,
  `interp_map`, `partition_max`, `SoilMapUnitAcreage`, `candidate_le`.
- **Reference**: current `get_productivity_ratings` branch and
  `tests/test_polygon_analysis.py` partition/sentinel tests.
- **Acceptance**: `uv run pytest tests/test_polygon_analysis.py`.

### 23.2.2 — Correcting LESA routing and normalization
- **Repo**: `AndrewBrown-USDA/fpac-soil-mcp`
- **Files in scope**: `src/fpac_soil_mcp/tools/soil_tools.py`,
  `src/fpac_soil_mcp/lesa.py`
- **Depends on**: 23.1.1, 23.1.2
- **Spec**: Normalize supported and unsupported productivity strings using the
  repository's `ProductivityIndexType` behavior, including `CUSTOM` fallback,
  without direct enum exceptions for ordinary invalid input. Route every
  explicit `project_type="corridor"` through the existing buffered corridor
  path when geometry can be represented by that path, while preserving line
  and WKT handling. Pass requested index, benchmark override, buffer distance,
  and units consistently. Ensure every fallback and normal LESA summary uses
  the normalized enum. Do not alter corridor algorithms or statutory scoring.
- **Do not touch**: polygon algorithms, geometry helpers, models beyond task
  23.1.1, docs, or tests.
- **Grep anchors**: `calculate_preliminary_lesa`, `analyze_corridor_fppa`,
  `normalized_productivity_index`, `ProductivityIndexType`, `LandEvaluationSummary`,
  `_normalize_productivity_index`.
- **Reference**: `lesa.py::_normalize_productivity_index`,
  `corridor_analysis.py::analyze_corridor`, and current WKT validators.
- **Acceptance**: `uv run pytest tests/test_lesa.py tests/test_tools.py`.

### 23.3.1 — Testing generic polygon ratings
- **Repo**: `AndrewBrown-USDA/fpac-soil-mcp`
- **Files in scope**: `tests/test_polygon_analysis.py`, `tests/test_models.py`
- **Depends on**: 23.2.1
- **Spec**: Add offline tests for NCCPI and CSR2/CPI/Storie generic numeric
  fields, qualitative class, and SDA provenance. Prove non-NCCPI values affect
  LE scoring and county normalization, sentinels remain unrated, partitions
  retain separate benchmarks, and removed NCCPI aliases are absent from the
  serialized model. Add a source/serialization assertion that no production or
  test consumer still references the removed `nccpi_rating`/`nccpi_class`
  names. Use mocked clients and existing fixtures only.
- **Do not touch**: production code, shared fixtures, or live tests.
- **Grep anchors**: `analyze_polygon`, `get_productivity_ratings`,
  `test_analyze_polygon`, `SoilMapUnitAcreage`.
- **Reference**: existing partition and sentinel tests.
- **Acceptance**: `uv run pytest tests/test_models.py tests/test_polygon_analysis.py`.

### 23.3.2 — Testing corridor routing and propagation
- **Repo**: `AndrewBrown-USDA/fpac-soil-mcp`
- **Files in scope**: `tests/test_tools.py`
- **Depends on**: 23.2.2
- **Spec**: Add mocked offline coverage proving polygon geometry with
  `project_type="corridor"` uses buffered corridor analysis, line and WKT
  inputs preserve buffer distance/units, CSR2/CPI/Storie remain the requested
  index, benchmark overrides are passed, and the response contains generic
  productivity fields without NCCPI aliases. Exercise both valid and
  unsupported index strings.
- **Do not touch**: production code, live tests, or shared fixtures.
- **Grep anchors**: `calculate_preliminary_lesa`,
  `test_calculate_preliminary_lesa`, `analyze_corridor_fppa`,
  `corridor_buffer_distance`.
- **Reference**: current corridor routing tests and Phase 3 tool contracts.
- **Acceptance**: `uv run pytest tests/test_tools.py tests/test_phase3_contracts.py`.

### 23.3.3 — Testing LESA fallback and invalid indexes
- **Repo**: `AndrewBrown-USDA/fpac-soil-mcp`
- **Files in scope**: `tests/test_lesa.py`
- **Depends on**: 23.2.2
- **Spec**: Add regression coverage for normalized CSR2/CPI/Storie fallback
  summaries, unsupported-string `CUSTOM` behavior, numeric/unavailable
  fallback construction, and existing sentinel behavior. Assert exact enum
  values and preserve numerical results where the implementation is unchanged.
- **Do not touch**: production code, shared fixtures, or live tests.
- **Grep anchors**: `evaluate_lesa`, `_normalize_productivity_index`,
  `ProductivityIndexType`, `fallback`, `sentinel`.
- **Reference**: existing fallback and normalization tests in this file.
- **Acceptance**: `uv run pytest tests/test_lesa.py`.

### 23.3.4 — Updating public rating documentation
- **Repo**: `AndrewBrown-USDA/fpac-soil-mcp`
- **Files in scope**: `README.md`, `manifest.yaml`
- **Depends on**: 23.1.1, 23.2.1, 23.2.2
- **Spec**: Document the generic productivity rating fields, provenance
  semantics, supported index values, intentional removal of NCCPI-specific
  aliases, and corridor tool parameters. Keep regulatory limitations and
  existing tool descriptions accurate. Do not duplicate divergent statutory
  wording or rewrite unrelated documentation.
- **Do not touch**: source code, server algorithms, tests, or planning files
  beyond the final state task.
- **Grep anchors**: `calculate_preliminary_lesa`, `analyze_farmland_by_polygon`,
  `NCCPI`, `productivity`, `LESA`.
- **Reference**: current README MCP interface and `manifest.yaml` tool list.
- **Acceptance**: `uv run python -c "import yaml; yaml.safe_load(open('manifest.yaml', encoding='utf-8'))"`
  and `uv run pytest tests/test_server.py`.

### 23.4.1 — Running complete offline verification
- **Repo**: `AndrewBrown-USDA/fpac-soil-mcp`
- **Files in scope**: `planning/STATE_23.md`
- **Depends on**: 23.3.1, 23.3.2, 23.3.3, 23.3.4
- **Spec**: Run targeted tests serially, then the complete offline suite and
  both Ruff checks. Record exact counts, failures, deselections, and any
  intentional schema-break notes in STATE_23. Update the wave-board status and
  append one bounded report per task. Live-network tests remain explicitly
  opt-in and are not a completion gate.
- **Do not touch**: source, tests, manifests, or generated caches.
- **Grep anchors**: `Baseline Checklist`, `Wave Board`, `Task Reports`.
- **Acceptance**: `uv run pytest -m "not live_network"`;
  `uv run ruff check .`; `uv run ruff format --check .`.
