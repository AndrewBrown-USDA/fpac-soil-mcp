# EXECUTION PLAN 19: PR #9 Code Review Remediation - Security, Sentinel Precision, LESA & Corridor Routing

## Goal & Scope

### Goal
Remediate all 10 code review findings on PR #9 (`feat/phase-4-part-1-land-evaluation`) across SQL injection prevention, sentinel float precision, LESA score consistency validation, multi-index productivity preservation, opt-out gating, dynamic SDV allowlist cleanup, county max query integration for NCCPI, and corridor LineString routing in `calculate_preliminary_lesa`.

### In Scope
1. **SQL Injection Remediation & Query Builder Sanitization (`sda_client.py`)**:
   - `build_dynamic_sdv_query`: Validate that each mukey in `mukeys` / `mukeys_csv` consists strictly of positive numeric digits before interpolating into the `IN` clause. Accept either `list[str | int]` or validated comma-separated strings with strict regex/integer verification.
   - `build_dynamic_sdv_county_max_query`: Enforce strict survey-area symbol sanitization (`validate_survey_area_symbol(areasymbol)`) before formatting into the `WHERE` clause.
   - `ALLOWED_SDV_TABLES`: Prune unjoined/unsupported table entries (`cocropyld`, `corestrictions`) from `ALLOWED_SDV_TABLES` so that requests cannot fail downstream against incorrect table schemas or fall through to non-existent component columns.
2. **Sentinel Precision & Unrated Screening (`lesa.py` & `polygon_analysis.py`)**:
   - Unconditional Sentinel Handling (`lesa.py`): Treat `99.0`, `999.0`, `-99.0`, `-999.0` as unconditional unrated sentinels across all productivity indexes, regardless of `county_max`.
   - String & Float Sentinel Matching (`polygon_analysis.py`): In NCCPI parsing, normalize ratings numerically (e.g. converting float/str and screening `{99, 999, 99.0, 999.0}`) before adding to `rating_map` and setting `is_rated`.
3. **LESA Score Consistency & Index Normalization (`models.py` & `lesa.py`)**:
   - Model Consistency Validator (`models.py`): Add a model validator on `PreliminaryLESAResponse` ensuring `mandatory_alternatives_required == (total_lesa_score >= 160.0)`.
   - Productivity Index Preservation (`lesa.py`): In `evaluate_lesa`, normalize string productivity index inputs (e.g. `"CSR2"`, `"cpi"`, `"storie"`) to `ProductivityIndexType` before constructing fallback `LandEvaluationSummary` instances so the evaluated response accurately reflects the requested index.
4. **Polygon Analysis & NCCPI County Benchmark Integration (`polygon_analysis.py`)**:
   - Opt-Out Flag Gating: Gate the NCCPI query path such that when `include_nccpi=False` and no non-default productivity index is explicitly requested, NCCPI queries and rating calculations are skipped.
   - Live NCCPI County Benchmark: Fetch live county maximum ratings for NCCPI via `sda_client.get_county_max_productivity_rating(areasymbol, index_type="nccpi")` (falling back to `1.0` if unavailable or <= 0).
5. **Corridor LineString Routing in Preliminary LESA (`tools/soil_tools.py`)**:
   - Detect `project_type == "corridor"` and/or `LineString` / `MultiLineString` geometries in `calculate_preliminary_lesa`.
   - Route corridor geometries through `CorridorAnalyzer` / corridor buffering routines to produce valid candidate LE scores and acreage summaries rather than failing in `PolygonAnalyzer`.
6. **Verification & Regression Test Suite (`tests/`)**:
   - Add targeted tests in `tests/test_sda_client.py`, `tests/test_lesa.py`, `tests/test_polygon_analysis.py`, and `tests/test_tools.py` directly exercising all 10 fixes.

### Out of Scope
- Full interactive GIS polygon editing UI or vector tile map servers (deferred to Phase 6).
- Document rendering for PDF Form AD-1006 / NRCS-CPA-106 (Phase 5).

### Verbatim Constraints
- "Dynamic SDV attribute routing retrieves valid state-specific productivity ratings (CSR2, CPI, Storie) and arbitrary sdvattribute records from SDA without hardcoded table schema assumptions."
- "Accept only validated coordinates or numeric positive mukey values. Do not add user-supplied SQL passthrough."
- "Null and unrated soil map units (including 99, 999, negative, and null values) are cleanly caught, reported in data caveats, and excluded from mathematical skew."
- "Preserve preliminary-screening limitation in every response."

---

## PR #9 Review Comment Traceability Matrix

| Comment ID | File & Line | Reviewer Finding | Remediation Strategy / Response | Task ID |
|---|---|---|---|---|
| `r4127352625` | `sda_client.py:434` | `build_dynamic_sdv_query` interpolates raw `mukeys_csv` without validating in builder. | Enforce strict regex/numeric digit validation for every mukey inside `build_dynamic_sdv_query`. | `19.1.1` |
| `r4127352683` | `sda_client.py:522` | `build_dynamic_sdv_county_max_query` interpolates `areasymbol` without validation. | Enforce `validate_survey_area_symbol(areasymbol)` in `build_dynamic_sdv_county_max_query`. | `19.1.1` |
| `r4127352951` | `sda_client.py:471` | `ALLOWED_SDV_TABLES` includes `cocropyld`/`corestrictions` which lack joins and fail on `component`. | Remove unsupported tables (`cocropyld`, `corestrictions`) from `ALLOWED_SDV_TABLES`. | `19.1.1` |
| `r4127352807` | `models.py:529` | `PreliminaryLESAResponse` allows contradictory `mandatory_alternatives_required` vs `total_lesa_score`. | Add `@model_validator(mode="after")` enforcing `mandatory_alternatives_required == (total_lesa_score >= 160.0)`. | `19.1.2` |
| `r4127352729` | `lesa.py:188` | `99.0` is only treated as sentinel when `county_max <= 1.0`; should be unconditional. | Treat `99.0`, `999.0`, `-99.0`, `-999.0` as unconditional unrated sentinels across all indices. | `19.2.1` |
| `r4127352771` | `lesa.py:752` | String index inputs (e.g. `"CSR2"`) fall back to `ProductivityIndexType.NCCPI` in `evaluate_lesa`. | Normalize string productivity index inputs to `ProductivityIndexType` in `evaluate_lesa`. | `19.2.1` |
| `r4127352850` | `polygon_analysis.py:163` | Default `productivity_index="nccpi"` ignores `include_nccpi=False` opt-out. | Gate query on `(include_nccpi or norm_idx != "nccpi")` and handle explicit disabling. | `19.2.2` |
| `r4127352879` | `polygon_analysis.py:183` | NCCPI parser compares `str(num_r)` to `"99"`/`"999"`, missing decimal float `99.0`. | Parse rating numerically and screen `{99, 999, 99.0, 999.0}` before setting `is_rated`. | `19.2.2` |
| `r4127352922` | `polygon_analysis.py:226` | NCCPI county benchmark hard-coded to `1.0` instead of fetching live SDA county maximum. | Call `get_county_max_productivity_rating(..., index_type="nccpi")`, falling back to `1.0`. | `19.2.2` |
| `r4127353024` | `soil_tools.py:496` | `calculate_preliminary_lesa` sends corridor LineStrings to `PolygonAnalyzer` which rejects them. | Route `project_type == "corridor"` / LineString geometries to `CorridorAnalyzer` / corridor buffering. | `19.3.1` |

---

## Decision Log

- **2026-09-28**: Query Builder Security: Both `build_dynamic_sdv_query` and `build_dynamic_sdv_county_max_query` will validate all inputs at the function boundary, refusing execution if mukeys or areasymbol do not match strict regex formats.
- **2026-09-28**: Schema Allowlist: `ALLOWED_SDV_TABLES` will only include tables with verified join and column semantics (`cointerp`, `component`, `mapunit`, `coiacsr2`, `iacsr2`, `cocpi`, `cpi`, `cstorie`).
- **2026-09-28**: Sentinel Policy: Values `99.0`, `999.0`, `-99.0`, `-999.0` will be unconditionally treated as unrated non-agricultural sentinels regardless of whether county benchmark is 1.0 or 100.0.
- **2026-09-28**: Statutory Consistency: `PreliminaryLESAResponse` will automatically derive or strictly validate `mandatory_alternatives_required` against the 160-point threshold under 7 CFR § 658.4(c)(2).
- **2026-09-28**: Corridor Integration: `calculate_preliminary_lesa` will check geometry type and project type, buffering linear corridor centerlines to produce valid polygon AOIs for soil intersection and LE scoring.

---

## Wave Table

| Wave | Task ID | Title | Files in Scope | Dependencies |
| --- | --- | --- | --- | --- |
| 1 | `19.1.1` | SQL Injection Hardening, Query Builder Validation & Allowlist Cleanup | `src/fpac_soil_mcp/sda_client.py` | None |
| 1 | `19.1.2` | LESA Response Model Statutory Consistency Validation | `src/fpac_soil_mcp/models.py` | None |
| 2 | `19.2.1` | Sentinel Float Precision, Unconditional Screening & Index Normalization | `src/fpac_soil_mcp/lesa.py` | `19.1.1`, `19.1.2` |
| 2 | `19.2.2` | Polygon Analysis NCCPI Opt-Out Gating, Float Sentinel Parsing & SDA Benchmark Lookup | `src/fpac_soil_mcp/polygon_analysis.py` | `19.1.1`, `19.1.2` |
| 3 | `19.3.1` | Preliminary LESA Tool Corridor LineString Buffering & Routing | `src/fpac_soil_mcp/tools/soil_tools.py` | `19.2.1`, `19.2.2` |
| 3 | `19.3.2` | Comprehensive Unit, Mocked & Regression Test Suite Verification | `tests/test_sda_client.py`, `tests/test_lesa.py`, `tests/test_polygon_analysis.py`, `tests/test_tools.py` | `19.2.1`, `19.2.2` |
| 4 | `19.4.1` | End-to-End Test Suite Verification, State & PR Comment Matrix Finalization | `planning/STATE_19.md`, `planning/tasks/19.4.1.todo.md` | `19.3.1`, `19.3.2` |

---

## Task Specifications

### Task 19.1.1: SQL Injection Hardening, Query Builder Validation & Allowlist Cleanup
- **Repo**: `fpac-soil-mcp`
- **Files in Scope**: `src/fpac_soil_mcp/sda_client.py`
- **Dependencies**: None
- **Spec**:
  - In `build_dynamic_sdv_query`, validate each mukey against `^\d+$` (or parse as positive integer). If `mukeys_csv` string is provided, parse and validate all comma-separated tokens before interpolating into `IN (...)`.
  - In `build_dynamic_sdv_county_max_query`, call `validate_survey_area_symbol(areasymbol)` to sanitize the survey area symbol before inserting into SQL.
  - In `ALLOWED_SDV_TABLES`, remove `"cocropyld"` and `"corestrictions"` from the allowed set since they lack the necessary component/mapunit join infrastructure.
- **Constraints**:
  - Do not touch `lesa.py` or `models.py`.
  - Maintain all existing helper signatures.
- **Acceptance Command**: `uv run pytest tests/test_sda_client.py -q`

---

### Task 19.1.2: LESA Response Model Statutory Consistency Validation
- **Repo**: `fpac-soil-mcp`
- **Files in Scope**: `src/fpac_soil_mcp/models.py`
- **Dependencies**: None
- **Spec**:
  - In `PreliminaryLESAResponse`, add a `@model_validator(mode="after")` that checks `mandatory_alternatives_required == (self.total_lesa_score >= 160.0)`. If inconsistent, raise `ValueError` (or automatically correct/sync if requested, while validating).
- **Constraints**:
  - Do not touch `sda_client.py` or `lesa.py`.
- **Acceptance Command**: `uv run pytest tests/test_lesa.py -q`

---

### Task 19.2.1: Sentinel Float Precision, Unconditional Screening & Index Normalization
- **Repo**: `fpac-soil-mcp`
- **Files in Scope**: `src/fpac_soil_mcp/lesa.py`
- **Dependencies**: `19.1.1`, `19.1.2`
- **Spec**:
  - In `evaluate_map_unit_productivity()`, unconditionally screen sentinels: `num_raw in (99.0, 999.0, -99.0, -999.0) or num_raw < 0` must always set `is_sentinel = True`, regardless of `county_max`.
  - In `evaluate_lesa()`, normalize string arguments for `productivity_index` (e.g. `"CSR2"`, `"cpi"`, `"storie"`) to `ProductivityIndexType` before constructing `LandEvaluationSummary` fallbacks.
- **Constraints**:
  - Do not touch `sda_client.py` or `polygon_analysis.py`.
- **Acceptance Command**: `uv run pytest tests/test_lesa.py -q`

---

### Task 19.2.2: Polygon Analysis NCCPI Opt-Out Gating, Float Sentinel Parsing & SDA Benchmark Lookup
- **Repo**: `fpac-soil-mcp`
- **Files in Scope**: `src/fpac_soil_mcp/polygon_analysis.py`
- **Dependencies**: `19.1.1`, `19.1.2`
- **Spec**:
  - Update the productivity querying condition in `analyze_polygon()`: if `include_nccpi=False` and `productivity_index` was not explicitly changed from `"nccpi"`, do not query NCCPI or build rating maps.
  - In NCCPI response parsing, parse numeric values safely and screen `{99, 999, 99.0, 999.0}` so float sentinels are not flagged as rated.
  - In NCCPI county benchmark determination, fetch live county maximum rating via `sda_client.get_county_max_productivity_rating(primary_areasymbol, index_type="nccpi")` when available, falling back to `1.0` only when unavailable.
- **Constraints**:
  - Do not touch `tools/soil_tools.py`.
- **Acceptance Command**: `uv run pytest tests/test_polygon_analysis.py -q`

---

### Task 19.3.1: Preliminary LESA Tool Corridor LineString Buffering & Routing
- **Repo**: `fpac-soil-mcp`
- **Files in Scope**: `src/fpac_soil_mcp/tools/soil_tools.py`
- **Dependencies**: `19.2.1`, `19.2.2`
- **Spec**:
  - In `calculate_preliminary_lesa()`, inspect the input geometry or `project_type`. If geometry is a `LineString` / `MultiLineString` or `project_type == "corridor"`, parse using geometry utilities, apply corridor buffer (e.g. using `buffer_centerline` or `CorridorAnalyzer`), and pass the buffered polygon to analysis to obtain the candidate LE score and map units.
- **Constraints**:
  - Preserve all existing parameter defaults and response structures.
- **Acceptance Command**: `uv run pytest tests/test_tools.py -q`

---

### Task 19.3.2: Comprehensive Unit, Mocked & Regression Test Suite Verification
- **Repo**: `fpac-soil-mcp`
- **Files in Scope**: `tests/test_sda_client.py`, `tests/test_lesa.py`, `tests/test_polygon_analysis.py`, `tests/test_tools.py`
- **Dependencies**: `19.2.1`, `19.2.2`
- **Spec**:
  - Add test cases verifying SQL injection rejection on invalid mukeys and areasymbol in SDA dynamic builders.
  - Add test verifying unallowed SDV tables (`cocropyld`, `corestrictions`) are rejected by allowlist validation.
  - Add test verifying `PreliminaryLESAResponse` consistency validator catches mismatched threshold flags.
  - Add test verifying `99.0` is screened as unrated even when `county_max=100.0`.
  - Add test verifying string index `"CSR2"` produces `ProductivityIndexType.CSR2` in `evaluate_lesa`.
  - Add test verifying `include_nccpi=False` skips NCCPI querying in `PolygonAnalyzer`.
  - Add test verifying corridor LineString geometry can be evaluated in `calculate_preliminary_lesa`.
- **Constraints**:
  - Do not include network calls in standard offline tests.
- **Acceptance Command**: `uv run pytest -m "not live_network and not agent_eval" -q`

---

### Task 19.4.1: End-to-End Test Suite Verification, State & PR Comment Matrix Finalization
- **Repo**: `fpac-soil-mcp`
- **Files in Scope**: `planning/STATE_19.md`, `planning/tasks/19.4.1.todo.md`
- **Dependencies**: `19.3.1`, `19.3.2`
- **Spec**:
  - Run full offline test suite and ruff checks.
  - Verify all 10 PR review items are marked as resolved in `STATE_19.md`.
- **Acceptance Command**: `uv run pytest -m "not live_network and not agent_eval" -q; uv run ruff check .`
