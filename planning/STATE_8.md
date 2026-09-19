# STATE 8: Code Review Remediation (Standards & Spec Refinements)

## Green Baseline Checklist

- [x] Orchestrations 1 through 7 complete.
- [x] Code review completed for `512e351...HEAD` with 6 action items identified.
- [x] Initial worktree status recorded: clean baseline.
- [x] Baseline test suite verified: `uv run pytest -m "not live_sda" -q` -> `148 passed, 10 deselected`.
- [x] Baseline lint verified: `uv run ruff check .` -> clean.
- [x] Baseline formatting verified: `uv run ruff format --check .` -> clean.

## Wave Board

| Task ID | Wave | Title | Status | Worker | Assigned At | Completed At |
| --- | --- | --- | --- | --- | --- | --- |
| `8.1.1` | 1 | Centralize Regulatory Constants & Types | completed | worker-8.1.1 | 2026-09-18 16:30 | 2026-09-18 16:35 |
| `8.2.1` | 2 | Refactor Corridor Scoring & Strategy Evaluators | completed | worker-8.2.1 | 2026-09-18 16:40 | 2026-09-18 16:45 |
| `8.2.2` | 2 | Typed TIGERweb County Partitioning | completed | worker-8.2.2 | 2026-09-18 16:40 | 2026-09-18 16:45 |
| `8.3.1` | 3 | Alternative Composite LE & Reconciliation Warnings | completed | worker-8.3.1 | 2026-09-18 17:08 | 2026-09-18 17:12 |
| `8.4.1` | 4 | Multi-County Criterion 7 Weighting & Tool Integration | completed | worker-8.4.1 | 2026-09-18 17:13 | 2026-09-18 17:16 |
| `8.5.1` | 5 | End-to-End Phase 3 Contract Suite & Verification | pending | — | — | — |

## Wave Gates

- **Wave 1** depends on baseline. Task `8.1.1` runs solo.
- **Wave 2** depends on `8.1.1`. Tasks `8.2.1` and `8.2.2` touch disjoint files and run in parallel.
- **Wave 3** depends on `8.2.2`. Task `8.3.1` runs solo.
- **Wave 4** depends on `8.2.1` and `8.3.1`. Task `8.4.1` runs solo.
- **Wave 5** depends on `8.4.1`. Task `8.5.1` runs solo.
- At every wave boundary, run serially:
  - `uv run pytest -m "not live_sda"`
  - `uv run ruff check .`
  - `uv run ruff format --check .`

---

## Task Reports

### Task 8.1.1 Report: Centralize Regulatory Constants & Types
- **Status**: Completed
- **Changes**:
  - Added statutory corridor criteria point maximums (`CORRIDOR_CRITERIA_MAX_POINTS`), names (`CORRIDOR_CRITERIA_NAMES`), scoring maximums (`MAX_SITE_ASSESSMENT_SCORE`, `MAX_LAND_EVALUATION_SCORE`, `MAX_TOTAL_LESA_SCORE`, `LESA_THRESHOLD_SCORE`), and determination templates (`STATUTORY_DETERMINATIONS`) under 7 CFR § 658.5(c) and § 658.4(c) in `constants.py`.
  - Added `CountyPartitionGeometry` Pydantic model with validation for FIPS codes, non-negative acreage, and geometry to `integration_models.py`.
- **Verification**: `tests/test_tigerweb_client.py` passed (8/8). Full suite `uv run pytest -m "not live_sda"` passed (148 passed). Ruff check and format clean.

### Task 8.2.1 Report: Refactor Corridor Scoring & Strategy Evaluators
- **Status**: Completed
- **Changes**:
  - Refactored `corridor_scoring.py` to import regulatory constants and statutory determination templates from `constants.py` while maintaining re-exports.
  - Implemented `CriterionEvaluator` hierarchy (`ZeroedCriterionEvaluator`, `FarmSizeCriterionEvaluator`, `StandardCriterionEvaluator`) and `CRITERION_EVALUATORS` registry.
  - Updated `evaluate_corridor_site_assessment` and `evaluate_corridor_lesa` to use the strategy evaluators and centralized determination templates.
  - Added strategy evaluator dispatch test in `tests/test_corridor_scoring.py`.
- **Verification**: `tests/test_corridor_scoring.py` passed (7/7). Full suite `uv run pytest -m "not live_sda"` passed (149 passed). Ruff check and format clean.


### Task 8.2.2 Report: Typed TIGERweb County Partitioning
- **Status**: Completed
- **Changes**:
  - Updated `partition_geometry_by_counties` in `src/fpac_soil_mcp/tigerweb_client.py` to return typed `list[CountyPartitionGeometry]`.
  - Added dictionary key (`__getitem__`) and `.get()` compatibility to `CountyPartitionGeometry` in `src/fpac_soil_mcp/integration_models.py` for backward compatibility with existing callers.
  - Updated `tests/test_tigerweb_client.py` to assert instances of `CountyPartitionGeometry`, validate attributes and dictionary access fallback.
- **Verification**: `tests/test_tigerweb_client.py` passed (8/8). Full suite `uv run pytest -m "not live_sda"` passed (149 passed, 10 deselected). Ruff check and format clean.

### Task 8.3.1 Report: Alternative Composite LE & Reconciliation Warnings
- **Status**: Completed
- **Changes**:
  - Updated alternatives processing in `corridor_analysis.py` to partition alternative footprints across intersected counties, query segment soils and NCCPI interpretations, and calculate area-weighted composite LE rating.
  - Enhanced sum reconciliation audit to log structured warning and append explicit reconciliation notice to response `limitations` when variance exceeds 0.1% tolerance.
  - Added unit test in `tests/test_corridor_analysis.py` validating alternative composite LE score computation and reconciliation failure warning emission.
- **Verification**: `tests/test_corridor_analysis.py` passed (5/5). Full test suite `uv run pytest -m "not live_sda"` passed (150 passed, 10 deselected). Ruff check and format clean.

### Task 8.4.1 Report: Multi-County Criterion 7 Weighting & Tool Integration
- **Status**: Completed
- **Changes**:
  - Updated `analyze_corridor_fppa` in `soil_tools.py` to calculate the area-weighted composite average farm size across all traversed county segments when `county_average_farm_acres` is not explicitly provided in `site_assessment_inputs`.
  - Added unit test `test_analyze_corridor_fppa_multi_county_weighted_farm_size` in `tests/test_tools.py` verifying multi-county area-weighted farm size integration with Criterion 7 scoring.
- **Verification**: `tests/test_tools.py` passed (16/16). Full test suite `uv run pytest -m "not live_sda"` passed (151 passed, 10 deselected). Ruff check and format clean.


