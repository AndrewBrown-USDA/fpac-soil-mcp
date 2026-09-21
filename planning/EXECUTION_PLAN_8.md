# EXECUTION PLAN 8: Code Review Remediation (Standards & Spec Refinements)

## Goal & Scope

Remediate all 6 findings identified in the two-axis code review (`512e351...HEAD`) across Standards compliance, Spec completeness, and architecture hygiene:
1. Centralize all statutory regulatory texts, CPA-106 criteria definitions, and point limits in `constants.py` per `AGENTS.md` rules.
2. Introduce typed domain model `CountyPartitionGeometry` in `integration_models.py` for TIGERweb county partitioning.
3. Refactor 7 CFR § 658.5(c) corridor scoring into modular strategy evaluators with centralized constants.
4. Calculate area-weighted composite Land Evaluation ($RR_{\text{composite}}$) ratings for alternative corridor alignments.
5. Calculate area-weighted composite NASS average farm sizes across traversed counties for Criterion 7.
6. Enforce explicit reconciliation warnings in response `limitations` and structured logging when county partition discrepancy exceeds 0.1%.
7. Verify all contract and regression tests pass cleanly.

### In Scope
- `src/fpac_soil_mcp/constants.py`
- `src/fpac_soil_mcp/integration_models.py`
- `src/fpac_soil_mcp/tigerweb_client.py`
- `src/fpac_soil_mcp/corridor_scoring.py`
- `src/fpac_soil_mcp/corridor_analysis.py`
- `src/fpac_soil_mcp/tools/soil_tools.py`
- `tests/test_corridor_scoring.py`
- `tests/test_corridor_analysis.py`
- `tests/test_tigerweb_client.py`
- `tests/test_tools.py`
- `tests/test_phase3_contracts.py`

### Out of Scope
- Upstream USDA SDA schema or endpoint changes.
- Changes to Point or Polygon screening logic (Phase 1 / Phase 2 tools).

---

## Decision Log

- **2026-09-18**: Include all 6 code review findings across Standards and Spec axes in Orchestration 8.
- **2026-09-18**: Set maximum concurrent workers to 2.
- **2026-09-18**: Use `gemini-3.7-flash` model tier for wave execution.

---

## Wave Table

| Wave | Task ID | Title | Files in Scope | Depends On |
| :--- | :--- | :--- | :--- | :--- |
| **Wave 1** | `8.1.1` | Centralize Regulatory Constants & Types | `src/fpac_soil_mcp/constants.py`, `src/fpac_soil_mcp/integration_models.py` | Baseline |
| **Wave 2** | `8.2.1` | Refactor Corridor Scoring & Strategy Evaluators | `src/fpac_soil_mcp/corridor_scoring.py`, `tests/test_corridor_scoring.py` | `8.1.1` |
| **Wave 2** | `8.2.2` | Typed TIGERweb County Partitioning | `src/fpac_soil_mcp/tigerweb_client.py`, `tests/test_tigerweb_client.py` | `8.1.1` |
| **Wave 3** | `8.3.1` | Alternative Composite LE & Reconciliation Warnings | `src/fpac_soil_mcp/corridor_analysis.py`, `tests/test_corridor_analysis.py` | `8.2.2` |
| **Wave 4** | `8.4.1` | Multi-County Criterion 7 Weighting & Tool Integration | `src/fpac_soil_mcp/tools/soil_tools.py`, `tests/test_tools.py` | `8.2.1`, `8.3.1` |
| **Wave 5** | `8.5.1` | End-to-End Phase 3 Contract Suite & Verification | `tests/test_phase3_contracts.py`, `README.md` | `8.4.1` |

---

## Task Specifications

### Task 8.1.1: Centralize Regulatory Constants & Types
- **ID**: `8.1.1`
- **Repo**: `fpac-soil-mcp`
- **Files in Scope**: `src/fpac_soil_mcp/constants.py`, `src/fpac_soil_mcp/integration_models.py`
- **Depends on**: Baseline
- **Spec**:
  - Add statutory 7 CFR § 658.5(c) corridor criteria metadata dictionaries to `constants.py`: names, statutory point maximums, and statutory determinations under § 658.4(c).
  - Add `CountyPartitionGeometry` Pydantic model to `src/fpac_soil_mcp/integration_models.py` representing partitioned county geometries with `state_fips`, `county_fips`, `county_name`, optional `state_name`, `geometry` (Any/Shapely), and `calculated_acres` (float).
- **Anchors**: `src/fpac_soil_mcp/constants.py`, `src/fpac_soil_mcp/integration_models.py`
- **Acceptance**: `uv run pytest tests/test_tigerweb_client.py -q`

---

### Task 8.2.1: Refactor Corridor Scoring & Strategy Evaluators
- **ID**: `8.2.1`
- **Repo**: `fpac-soil-mcp`
- **Files in Scope**: `src/fpac_soil_mcp/corridor_scoring.py`, `tests/test_corridor_scoring.py`
- **Depends on**: `8.1.1`
- **Spec**:
  - Refactor `src/fpac_soil_mcp/corridor_scoring.py` to import statutory texts, max point maps, and threshold determinations from `fpac_soil_mcp.constants`.
  - Replace raw integer branching switches with structured evaluator functions / classes for zeroed criteria (5 & 6), scaled farm size criterion (7), and standard/adjusted criteria (1-4, 8-12).
  - Ensure all existing unit tests in `tests/test_corridor_scoring.py` pass.
- **Anchors**: `src/fpac_soil_mcp/corridor_scoring.py:1-325`
- **Acceptance**: `uv run pytest tests/test_corridor_scoring.py -q`

---

### Task 8.2.2: Typed TIGERweb County Partitioning
- **ID**: `8.2.2`
- **Repo**: `fpac-soil-mcp`
- **Files in Scope**: `src/fpac_soil_mcp/tigerweb_client.py`, `tests/test_tigerweb_client.py`
- **Depends on**: `8.1.1`
- **Spec**:
  - Update `partition_geometry_by_counties` in `tigerweb_client.py` to return `list[CountyPartitionGeometry]`.
  - Ensure compatibility with existing county dictionary lookups or expose backward-compatible attributes / methods.
  - Update `tests/test_tigerweb_client.py` to validate typed partition responses.
- **Anchors**: `src/fpac_soil_mcp/tigerweb_client.py:350-410`
- **Acceptance**: `uv run pytest tests/test_tigerweb_client.py -q`

---

### Task 8.3.1: Alternative Composite LE & Reconciliation Warnings
- **ID**: `8.3.1`
- **Repo**: `fpac-soil-mcp`
- **Files in Scope**: `src/fpac_soil_mcp/corridor_analysis.py`, `tests/test_corridor_analysis.py`
- **Depends on**: `8.2.2`
- **Spec**:
  - In `CorridorAnalyzer.analyze_corridor`, compute area-weighted composite Land Evaluation ratings ($RR_{\text{composite}}$) across intersected county partitions for each supplied alternative alignment in `alternatives`.
  - In sum reconciliation checking, if `delta_pct > 0.1` (or `reconciliation_passed is False`), append an explicit reconciliation warning to the response limitations list and log a warning with detailed segment vs direct/indirect acreage metrics.
  - Consume `CountyPartitionGeometry` objects from `tigerweb_client.partition_geometry_by_counties`.
- **Anchors**: `src/fpac_soil_mcp/corridor_analysis.py:320-545`
- **Acceptance**: `uv run pytest tests/test_corridor_analysis.py -q`

---

### Task 8.4.1: Multi-County Criterion 7 Weighting & Tool Integration
- **ID**: `8.4.1`
- **Repo**: `fpac-soil-mcp`
- **Files in Scope**: `src/fpac_soil_mcp/tools/soil_tools.py`, `tests/test_tools.py`
- **Depends on**: `8.2.1`, `8.3.1`
- **Spec**:
  - In `analyze_corridor_fppa`, if `county_average_farm_acres` is not provided in `site_assessment_inputs`, calculate an area-weighted composite average farm size across all traversed county segments having valid NASS profiles (weighting each county's `farm_size_acres_avg` by its `total_segment_acres`).
  - Update `tests/test_tools.py` with multi-county weighted farm size verification.
- **Anchors**: `src/fpac_soil_mcp/tools/soil_tools.py:380-450`
- **Acceptance**: `uv run pytest tests/test_tools.py -q`

---

### Task 8.5.1: End-to-End Phase 3 Contract Suite & Verification
- **ID**: `8.5.1`
- **Repo**: `fpac-soil-mcp`
- **Files in Scope**: `tests/test_phase3_contracts.py`, `README.md`
- **Depends on**: `8.4.1`
- **Spec**:
  - Update `tests/test_phase3_contracts.py` to verify:
    - Alternative corridor alignments calculate composite LE scores.
    - Multi-county corridor Criterion 7 weighting across multiple county segments.
    - Sum reconciliation discrepancy warnings in limitations when acreage drifts >0.1%.
  - Run full offline test suite and linters to verify green status.
- **Anchors**: `tests/test_phase3_contracts.py:1-250`
- **Acceptance**: `uv run pytest -m "not live_sda" -q && uv run ruff check . && uv run ruff format --check .`
