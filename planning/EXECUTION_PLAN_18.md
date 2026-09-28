# EXECUTION PLAN 18: Code Review Remediation - Generalized Dynamic SDV Routing, Null Screening, Model Bounds & Registration

## Goal & Scope

### Goal
Remediate code review findings from Phase 4 Part 1 review by generalizing dynamic Soil Data Viewer (`sdvattribute`) query generation to resolve arbitrary SDV attribute records into component/mapunit queries, fixing unrated sentinel screening (including explicit handling of `99` and `999`), scoping county farmland percentile calculations strictly to rated qualifying agricultural acreage, adding comprehensive validation bounds to `SiteAssessmentCriterion`, eliminating dead/mysterious code branches in `lesa.py`, and registering `calculate_preliminary_lesa` in `server.json`.

### In Scope
1. **Generalized Dynamic SDV Attribute Query Engine (`sda_client.py`)**:
   - Build consistent query generation routines that inspect `sdvattribute` records (`attributetablename`, `attributecolumnname`, `attributelogicaldatatype`, `nasisrulename`, `attributekey`) and dynamically construct SQL queries for any requested attribute (cointerp rules, component table columns, mapunit columns, etc.).
   - Support both known aliases (`nccpi`, `csr2`, `cpi`, `storie`) and arbitrary user/SDA-provided `sdvattribute` keys or names.
   - Maintain validated sanitization of SQL identifiers while generating dynamic queries without static table schema assumptions.
2. **Robust Unrated Sentinel Screening & Percentile Calculation (`lesa.py`)**:
   - Ensure sentinel and unrated indicators (`99`, `999`, `-999`, negative values, empty/null values) are consistently screened and reported across all productivity indexes, preventing `99` from being erroneously scored as `0.99` when `county_max = 100`.
   - Update `calculate_county_farmland_percentile()` to calculate percentile strictly over rated qualifying agricultural acreage ($A_{\text{qualifying}} / A_{\text{rated\_county\_farmland}}$), excluding unrated/null acreage from diluting the comparison denominator.
   - Clean up dead/mysterious branches and eliminate boilerplate in `lesa.py`.
3. **Model Validation Bounds (`models.py`)**:
   - Add field validators on `SiteAssessmentCriterion` to enforce `awarded_points <= max_points`, `max_points > 0`, and `0 <= awarded_points`.
4. **Standards & Registry Compliance (`server.json`)**:
   - Update `server.json` to include the `calculate_preliminary_lesa` MCP tool metadata matching `manifest.yaml` and `README.md`.
5. **Testing & Benchmark Verification (`tests/`)**:
   - Expand unit and mocked tests in `tests/test_sda_client.py` and `tests/test_lesa.py` verifying dynamic query generation for arbitrary SDV attributes, sentinel `99` unrated exclusion, strict qualifying percentile calculations, and criterion model boundary validation.
   - Confirm 100% green status on full offline test suite and Ruff linters.

### Out of Scope
- Full automated spatial perimeter adjacency / buffer geometry clipping for Site Assessment criteria 2 and 3 (Phase 4 Part 2 / Plan 19).
- Document generation for Form AD-1006 / CPA-106 (Phase 5).

### Verbatim Constraints
- "Dynamic SDV attribute routing retrieves valid state-specific productivity ratings (CSR2, CPI, Storie) and arbitrary sdvattribute records from SDA without hardcoded table schema assumptions."
- "Null and unrated soil map units (including 99, 999, negative, and null values) are cleanly caught, reported in data caveats, and excluded from mathematical skew."
- "Update README.md, manifest.yaml, and server.json when the public MCP surface changes."
- "Preserve preliminary-screening limitation in every response."

---

## Decision Log

- **2026-09-28**: Architecture decision: SDV query engine will inspect `sdvattribute` metadata (`attributetablename`, `attributecolumnname`, `nasisrulename`, `attributelogicaldatatype`) to dynamically build component-weighted and dominant-component queries for arbitrary productivity attributes, with well-known alias shortcuts for standard indexes.
- **2026-09-28**: Mathematical decision: `calculate_county_farmland_percentile` will calculate percentile over qualifying rated acreage divided by total rated county farmland acreage to prevent unrated tracts from distorting the distribution.
- **2026-09-28**: Standards compliance: `server.json` updated with `calculate_preliminary_lesa` tool registration.
- **2026-09-28**: Worker concurrency set to 2 parallel workers per wave.

---

## Wave Table

| Wave | Task ID | Title | Files in Scope | Dependencies |
| --- | --- | --- | --- | --- |
| 1 | `18.1.1` | Generalized Dynamic SDV Attribute Query Engine in SDA Client | `src/fpac_soil_mcp/sda_client.py` | None |
| 1 | `18.1.2` | Model Bounds Enforcement & Server Registry Sync | `src/fpac_soil_mcp/models.py`, `server.json` | None |
| 2 | `18.2.1` | Sentinel Null Screening, Strict Percentile Math & LESA Engine Cleanup | `src/fpac_soil_mcp/lesa.py` | `18.1.1`, `18.1.2` |
| 2 | `18.2.2` | Unit, Mocked & Benchmark Verification Suite Expansion | `tests/test_sda_client.py`, `tests/test_lesa.py` | `18.1.1`, `18.1.2` |
| 3 | `18.3.1` | End-to-End Test Suite Verification, State & Documentation Finalization | `planning/STATE_18.md`, `planning/tasks/18.3.1.todo.md` | `18.2.1`, `18.2.2` |

---

## Task Specifications

### Task 18.1.1: Generalized Dynamic SDV Attribute Query Engine in SDA Client
- **Task ID**: `18.1.1`
- **Files in Scope**: `src/fpac_soil_mcp/sda_client.py`
- **Dependencies**: None
- **Spec Prose**:
  1. In `src/fpac_soil_mcp/sda_client.py`, implement helper `build_dynamic_sdv_query(attribute_meta: dict[str, Any], mukeys: list[str]) -> str`:
     - Inspect `attributetablename` (e.g. `cointerp`, `component`, `mapunit`, `cocropyld`), `attributecolumnname`, `nasisrulename`, and `attributelogicaldatatype`.
     - When `attributetablename == 'cointerp'`, construct a query joining `component` and `cointerp` filtering on `mrulename = '{nasisrulename}'` and `ruledepth = 0`.
     - When `attributetablename == 'component'`, construct a query selecting `c.{attributecolumnname}` and computing component-weighted averages (`SUM(c.{col} * c.comppct_r) / NULLIF(SUM(CASE WHEN c.{col} IS NOT NULL THEN c.comppct_r END), 0)`).
     - When `attributetablename == 'mapunit'`, construct a query directly selecting `m.{attributecolumnname}`.
  2. Implement helper `build_dynamic_sdv_county_max_query(attribute_meta: dict[str, Any], areasymbol: str) -> str`.
  3. Update `get_productivity_ratings()` and `get_county_max_productivity_rating()` to use the dynamic query builder when an attribute metadata record or custom attribute name/key is supplied, while preserving fast standard alias routing for `nccpi`, `csr2`, `cpi`, `storie`.
- **Constraints**: Sanitize all dynamic table and column identifiers against an allowlist of valid SSURGO tables (`cointerp`, `component`, `mapunit`, `cocropyld`, `corestrictions`) and alphanumeric column names to prevent SQL injection.
- **Grep Anchors**: `class SDAClient` in `src/fpac_soil_mcp/sda_client.py`
- **Acceptance Command**: `uv run pytest tests/test_sda_client.py -q`

---

### Task 18.1.2: Model Bounds Enforcement & Server Registry Sync
- **Task ID**: `18.1.2`
- **Files in Scope**: `src/fpac_soil_mcp/models.py`, `server.json`
- **Dependencies**: None
- **Spec Prose**:
  1. In `src/fpac_soil_mcp/models.py`:
     - Add field validators on `SiteAssessmentCriterion`:
       - Validate `max_points > 0.0`.
       - Validate `0.0 <= awarded_points <= max_points`.
  2. In `server.json`:
     - Update server capabilities / metadata to list `calculate_preliminary_lesa` and ensure tool registry sync matches `manifest.yaml`.
- **Constraints**: Follow Pydantic v2 conventions with `@field_validator` and `@model_validator`.
- **Grep Anchors**: `class SiteAssessmentCriterion` in `src/fpac_soil_mcp/models.py`, `server.json`
- **Acceptance Command**: `python -c "from fpac_soil_mcp.models import SiteAssessmentCriterion; c = SiteAssessmentCriterion(criterion_number=1, name='test', max_points=10, awarded_points=5); print('Model validated')"`

---

### Task 18.2.1: Sentinel Null Screening, Strict Percentile Math & LESA Engine Cleanup
- **Task ID**: `18.2.1`
- **Files in Scope**: `src/fpac_soil_mcp/lesa.py`
- **Dependencies**: `18.1.1`, `18.1.2`
- **Spec Prose**:
  1. In `src/fpac_soil_mcp/lesa.py`:
     - In `calculate_relative_ratings()`:
       - Screen out all sentinel values where `num_raw in (99.0, 999.0, -999.0, -99.0)` or `num_raw < 0`, regardless of `county_max`.
       - Specifically treat raw rating `99.0` (standard NRCS/SSURGO unrated code) as unrated (`is_rated = False`), setting `normalized_relative_rating = None` and appropriate `unrated_reason`.
     - In `calculate_county_farmland_percentile()`:
       - Sum only acreage where rating is valid and positive into `total_county_rated_acres`.
       - Calculate `percentile_higher = round((qualifying_acres / total_county_rated_acres) * 100.0, 1)` if `total_county_rated_acres > 0` else `None`.
     - Clean up dead code branch `if rr is None and raw is not None: pass` in `evaluate_land_evaluation`.
     - Refactor criterion evaluation classes to use a shared factory helper for building `SiteAssessmentCriterion` results.
- **Constraints**: Preserve 100% backwards compatibility for `calculate_composite_le` and all exported functions.
- **Grep Anchors**: `def calculate_relative_ratings` in `src/fpac_soil_mcp/lesa.py`
- **Acceptance Command**: `uv run pytest tests/test_lesa.py -q`

---

### Task 18.2.2: Unit, Mocked & Benchmark Verification Suite Expansion
- **Task ID**: `18.2.2`
- **Files in Scope**: `tests/test_sda_client.py`, `tests/test_lesa.py`
- **Dependencies**: `18.1.1`, `18.1.2`
- **Spec Prose**:
  1. In `tests/test_sda_client.py`:
     - Add unit tests for `build_dynamic_sdv_query` with various attribute tables (`cointerp`, `component`, `mapunit`).
     - Add test querying arbitrary `sdvattribute` definitions and verifying dynamic query generation.
  2. In `tests/test_lesa.py`:
     - Add test verifying that raw rating `99.0` with `county_max = 100.0` is treated as unrated (`is_rated=False`).
     - Add test verifying `calculate_county_farmland_percentile` excludes unrated rows from the denominator.
     - Add test verifying `SiteAssessmentCriterion` raises `ValidationError` when `awarded_points > max_points` or `max_points <= 0`.
- **Constraints**: Fast mocked execution under `pytest -m "not live_network"`.
- **Grep Anchors**: `tests/test_sda_client.py`, `tests/test_lesa.py`
- **Acceptance Command**: `uv run pytest tests/test_lesa.py tests/test_sda_client.py -q`

---

### Task 18.3.1: End-to-End Test Suite Verification, State & Documentation Finalization
- **Task ID**: `18.3.1`
- **Files in Scope**: `planning/STATE_18.md`, `planning/tasks/18.3.1.todo.md`
- **Dependencies**: `18.2.1`, `18.2.2`
- **Spec Prose**:
  1. Run complete offline test suite: `uv run pytest -m "not live_network and not agent_eval" -q`.
  2. Run linters: `uv run ruff check .` and `uv run ruff format --check .`.
  3. Create `planning/STATE_18.md` and mark all wave tasks ready for execution.
- **Constraints**: 100% clean test suite and linter check.
- **Grep Anchors**: `planning/STATE_18.md`
- **Acceptance Command**: `uv run pytest -m "not live_network and not agent_eval" -q`
