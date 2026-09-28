# EXECUTION PLAN 17: Phase 4 Implementation - Land Evaluation & Unified LESA Engine

## Goal & Scope

### Goal
Implement Phase 4 Part 1 (Land Evaluation & Unified LESA Engine) of the FPAC Soil MCP Server roadmap, delivering dynamic Soil Data Viewer (`sdvattribute`) productivity index query routing (supporting NCCPI v3, Iowa CSR2, Minnesota CPI, California Storie Index, and county rating overrides), relative rating normalization ($RR_i = \text{Rating}_i / \text{Max County Rating}$), area-weighted candidate Land Evaluation scoring ($0\text{--}100$), null rating screening, unified LESA data models and calculation architecture for both site (Form AD-1006) and corridor (Form NRCS-CPA-106) projects, and standalone plus polygon-integrated MCP tools (`calculate_preliminary_lesa` and `analyze_farmland_by_polygon` enhancements).

### In Scope
1. **Dynamic Soil Data Viewer (SDV) Productivity Routing (`sda_client.py`)**:
   - Query `sdvattribute` metadata to dynamically resolve table and column names (`cointerp`, `component`, `cocropyld`, etc.) for productivity indexes.
   - Built-in support for standard national rating schedules (NCCPI v3 / `National Commodity Crop Productivity Index`) and state-specific productivity indexes:
     - Iowa Corn Suitability Rating 2 (`CSR2` / `iacsr2`)
     - Minnesota Crop Productivity Index (`CPI` / `cpi`)
     - California Revised Storie Index (`storie` / `storie_index`)
   - Support user-supplied and SDA-retrieved county maximum rating overrides (`max_county_rating_override`).
   - Null and unrated soil map unit detection and filtering (`[99, 999, None, '']`) with explicit notices rather than mathematical distortion.
2. **Relative Land Evaluation (LE) Normalization & Scoring Algorithm (`lesa.py`)**:
   - Calculate normalized relative ratings for each soil map unit $i$:
     $$RR_i = \frac{\text{Rating}_i}{\text{Max Rating}_{\text{county}}}$$
   - Calculate area-weighted relative rating across the AOI:
     $$RR_{\text{AOI}} = \sum_{i=1}^{n} \left( RR_i \times \frac{A_i}{A_{\text{total}}} \right)$$
     $$\text{Candidate LE Score} = \text{round}(RR_{\text{AOI}} \times 100)$$
   - Calculate county farmland comparison percentile (% of qualifying county farmland with relative rating $\ge RR_{\text{AOI}}$):
     $$\text{Percent Higher} = \left( \frac{A_{\text{qualifying}}}{A_{\text{county\_farmland}}} \right) \times 100$$
3. **Unified LESA Domain Models & Engine Refactoring (`lesa.py`, `models.py`)**:
   - Establish a unified LESA module (`src/fpac_soil_mcp/lesa.py`) providing shared data structures and calculators for both site projects (AD-1006) and corridor projects (CPA-106).
   - Re-export and preserve backwards compatibility with existing `corridor_scoring.py` symbols.
   - Define Pydantic models for `LandEvaluationResult`, `MapUnitRelativeRating`, `SiteAssessmentInput`, and `TotalLESAResult`.
   - Enforce the statutory 160-point mandatory alternatives threshold flag under 7 CFR § 658.4(c)(2).
4. **FastMCP Tool Integration (`src/fpac_soil_mcp/tools/soil_tools.py`, `fppa_tools.py`)**:
   - Add new tool `calculate_preliminary_lesa` for dedicated candidate LE-SA score generation.
   - Extend `analyze_farmland_by_polygon` to optionally accept productivity index parameters and return preliminary Land Evaluation summaries in the response envelope.
5. **Testing, Benchmarking & Fixtures (`tests/`)**:
   - Add comprehensive unit and mocked tests covering CSR2, CPI, Storie index queries, county normalization, null handling, and scoring.
   - Add offline benchmark test fixtures verifying precision within 0.01 tolerance against known soil profiles.
   - Run complete test suite and linter verification.

### Out of Scope
- Full automated spatial perimeter adjacency / buffer geometry clipping for Site Assessment criteria 2 and 3 (Phase 4 Part 2 / Site Assessment automation).
- Form AD-1006 / CPA-106 DOCX/PDF document rendering and clearance letters (Phase 5).
- SQLite case database persistence and Form CPA-2 annual rollup (Phase 6).

### Verbatim Constraints
- "Relative LE scoring, county maximum normalization, and comparison percentile calculations match verified benchmark fixtures within 0.01 precision."
- "Null and unrated soil map units are cleanly caught, reported in data caveats, and excluded from mathematical skew."
- "Dynamic SDV attribute routing retrieves valid state-specific productivity ratings (CSR2, CPI, Storie) from SDA without hardcoded table schema assumptions."
- "Combined Scoring & Mandatory Alternatives Threshold (7 CFR § 658.4(c)(2)): Sum preliminary LE (0–100) and SA (0–160) scores to compute preliminary Total LESA Score (0–260 max). Statutorily flag projects where Total LESA Score >= 160 points."
- "Preserve preliminary-screening limitation in every response."

---

## Decision Log

- **2026-09-28**: Architecture decision: unified LESA module (`src/fpac_soil_mcp/lesa.py`) housing both site and corridor scoring logic while maintaining backwards compatibility with `corridor_scoring.py`.
- **2026-09-28**: Scope decision: Focus Phase 4 Wave 17 on Land Evaluation normalization, multi-index SDV routing (NCCPI, CSR2, CPI, Storie), null screening, and unified LESA evaluation structures, paving the way for automated spatial SA in subsequent tasks.
- **2026-09-28**: Tool exposure decision: Expose `calculate_preliminary_lesa` as a standalone MCP tool and integrate candidate LE evaluation directly into `analyze_farmland_by_polygon`.
- **2026-09-28**: Worker concurrency set to 3 parallel workers per wave.

---

## Technical Reconnaissance

- **Key Existing Files**:
  - `src/fpac_soil_mcp/sda_client.py` (528 lines) - contains `SQL_INTERPRETATION_*` queries and SDA tabular HTTP communication.
  - `src/fpac_soil_mcp/corridor_scoring.py` (533 lines) - contains corridor-specific 7 CFR § 658.5(c) rules and `calculate_composite_le`.
  - `src/fpac_soil_mcp/polygon_analysis.py` (440 lines) - handles AOI screening, SDA spatial intersection, and farmland summary aggregation.
  - `src/fpac_soil_mcp/tools/soil_tools.py` (515 lines) - registers MCP tools for point, polygon, and corridor analysis.
  - `src/fpac_soil_mcp/models.py` (338 lines) - Pydantic models for responses.
- **Baseline Status**:
  - `uv run pytest -m "not live_network and not agent_eval" -q` -> `192 passed, 12 deselected`.
  - `uv run ruff check .` -> clean.
  - `uv run ruff format --check .` -> clean.

---

## Wave Table

| Wave | Task ID | Title | Files in Scope | Dependencies |
| --- | --- | --- | --- | --- |
| 1 | `17.1.1` | SDV Metadata & Dynamic Productivity Index Queries in SDA Client | `src/fpac_soil_mcp/sda_client.py` | None |
| 1 | `17.1.2` | Unified LESA Domain Models & Score Structures | `src/fpac_soil_mcp/models.py` | None |
| 1 | `17.1.3` | Test Fixtures for State Productivity Ratings & LE Calculations | `tests/fixtures/le_benchmarks.json` | None |
| 2 | `17.2.1` | Unified Land Evaluation & LESA Calculation Engine | `src/fpac_soil_mcp/lesa.py`, `src/fpac_soil_mcp/corridor_scoring.py` | `17.1.1`, `17.1.2`, `17.1.3` |
| 2 | `17.2.2` | Polygon Analysis Engine Integration with Dynamic LE Scoring | `src/fpac_soil_mcp/polygon_analysis.py` | `17.1.1`, `17.1.2` |
| 3 | `17.3.1` | MCP Tool Registration for `calculate_preliminary_lesa` & Polygon Integration | `src/fpac_soil_mcp/tools/soil_tools.py`, `src/fpac_soil_mcp/tools/__init__.py` | `17.2.1`, `17.2.2` |
| 3 | `17.3.2` | Unit & Mocked Test Suite for LE Scoring & SDV Routing | `tests/test_lesa.py`, `tests/test_sda_client.py` | `17.2.1`, `17.2.2` |
| 4 | `17.4.1` | Benchmark Eval Fixture Suite Expansion for LESA Scoring | `eval/prompt_test_cases.json` | `17.3.1`, `17.3.2` |
| 4 | `17.4.2` | End-to-End Verification, Documentation & Plan 17 State Finalization | `README.md`, `planning/STATE_17.md`, `planning/tasks/17.4.2.todo.md` | `17.4.1` |

---

## Task Specifications

### Task 17.1.1: SDV Metadata & Dynamic Productivity Index Queries in SDA Client
- **Task ID**: `17.1.1`
- **Files in Scope**: `src/fpac_soil_mcp/sda_client.py`
- **Dependencies**: None
- **Spec Prose**:
  1. In `src/fpac_soil_mcp/sda_client.py`, define query templates for Soil Data Viewer (`sdvattribute`) routing:
     - Query to look up table and column mappings for productivity rules (e.g. `NCCPI`, `CSR2`, `CPI`, `Storie`).
     - Query templates for retrieving mapunit-level and component-level ratings for CSR2 (Iowa `iacsr2`), CPI (Minnesota `cpi`), Storie Index (California `storie_index`), and NCCPI v3.
     - Query template to retrieve county maximum baseline rating for a given productivity index and county (`areasymbol`).
  2. Implement method `get_productivity_ratings(mukeys: list[int], index_type: str = "nccpi", areasymbol: str | None = None)` in `SDAClient`.
  3. Filter and flag null/unrated values (`99`, `999`, `None`, empty strings) and return structured rating results with rated component percentages and data quality caveats.
- **Constraints**: Do not break existing SQL templates or `get_soil_interpretations` contracts.
- **Grep Anchors**: `SQL_INTERPRETATION_WEIGHTED_AVG` in `src/fpac_soil_mcp/sda_client.py`
- **Acceptance Command**: `uv run pytest tests/test_sda_client.py -q`

---

### Task 17.1.2: Unified LESA Domain Models & Score Structures
- **Task ID**: `17.1.2`
- **Files in Scope**: `src/fpac_soil_mcp/models.py`
- **Dependencies**: None
- **Spec Prose**:
  1. In `src/fpac_soil_mcp/models.py`, define Pydantic models for Land Evaluation and unified LESA:
     - `ProductivityIndexType` Enum: `NCCPI`, `CSR2`, `CPI`, `STORIE`, `CUSTOM`.
     - `MapUnitProductivityRating`: `mukey`, `musym`, `muname`, `raw_rating`, `normalized_relative_rating`, `county_max_rating`, `is_rated`, `unrated_reason`.
     - `LandEvaluationSummary`: `productivity_index`, `aoi_relative_rating` (0.0–1.0), `candidate_le_score` (0–100), `county_farmland_percentile_higher` (float | None), `rated_acreage`, `unrated_acreage`, `total_acreage`, `coverage_percent`, `notices`.
     - `SiteAssessmentCriterion`: `criterion_number` (1–12), `name`, `max_points`, `awarded_points`, `justification`, `is_automated`, `is_statutorily_zeroed`.
     - `PreliminaryLESAResponse`: `project_name`, `project_type` (`site` | `corridor`), `land_evaluation` (`LandEvaluationSummary`), `site_assessment` (total points 0–160, criteria breakdown), `total_lesa_score` (0–260), `mandatory_alternatives_required` (bool; true if $\ge 160$), `regulatory_notice`, `limitations`.
- **Constraints**: Follow Pydantic v2 conventions; use field validators for bounds checking.
- **Grep Anchors**: `class FarmlandClassificationResponse` in `src/fpac_soil_mcp/models.py`
- **Acceptance Command**: `python -c "from fpac_soil_mcp.models import LandEvaluationSummary, PreliminaryLESAResponse; print('Models valid')"`

---

### Task 17.1.3: Test Fixtures for State Productivity Ratings & LE Calculations
- **Task ID**: `17.1.3`
- **Files in Scope**: `tests/fixtures/le_benchmarks.json`
- **Dependencies**: None
- **Spec Prose**:
  1. Create `tests/fixtures/le_benchmarks.json` containing verified benchmark cases for:
     - Iowa Story County CSR2 parcel evaluation (e.g. Clarinda, Clarion, Webster soils, county max CSR2 = 100).
     - Minnesota CPI parcel evaluation (e.g. Nicollet, Webster soils, county max CPI = 100).
     - California Fresno County Storie Index evaluation (e.g. Hanford, San Joaquin soils, county max = 100).
     - Standard NCCPI v3 parcel evaluation with mixed rated and unrated map units (verifying null filtering).
     - Corridor vs Site 160-point threshold triggers ($< 160$ vs $\ge 160$).
- **Constraints**: Ensure JSON schema validity with exact expected numeric scores and relative ratings within 0.01 precision.
- **Grep Anchors**: `tests/fixtures/le_benchmarks.json`
- **Acceptance Command**: `python -c "import json; data=json.load(open('tests/fixtures/le_benchmarks.json')); assert len(data['cases']) >= 4; print('Fixtures valid')"`

---

### Task 17.2.1: Unified Land Evaluation & LESA Calculation Engine
- **Task ID**: `17.2.1`
- **Files in Scope**: `src/fpac_soil_mcp/lesa.py`, `src/fpac_soil_mcp/corridor_scoring.py`
- **Dependencies**: `17.1.1`, `17.1.2`, `17.1.3`
- **Spec Prose**:
  1. Create `src/fpac_soil_mcp/lesa.py` implementing the complete Land Evaluation and unified LESA calculation engine:
     - Function `calculate_relative_ratings(ratings: list[dict], county_max: float) -> list[MapUnitProductivityRating]`.
     - Function `calculate_area_weighted_le(mapunit_ratings: list[tuple[float, float]]) -> tuple[float, int]`: area-weighted relative rating and integer candidate LE score (0–100).
     - Function `calculate_county_farmland_percentile(aoi_relative_rating: float, county_farmland_distribution: list[dict]) -> float | None`.
     - Unified evaluation router supporting Site (AD-1006 rules: 12 criteria, 160 max SA) and Corridor (CPA-106 rules: Criteria 5 & 6 zeroed, Criteria 8 & 11 max 25).
     - Threshold evaluator applying 7 CFR § 658.4(c)(2) ($\ge 160$ points flags mandatory alternatives).
  2. Refactor `src/fpac_soil_mcp/corridor_scoring.py` to import and wrap `lesa.py` functions while maintaining complete backwards compatibility for existing imports and tests.
- **Constraints**: Maintain 100% passing tests in `tests/test_corridor_scoring.py`.
- **Grep Anchors**: `def calculate_composite_le` in `src/fpac_soil_mcp/corridor_scoring.py`
- **Acceptance Command**: `uv run pytest tests/test_corridor_scoring.py -q`

---

### Task 17.2.2: Polygon Analysis Engine Integration with Dynamic LE Scoring
- **Task ID**: `17.2.2`
- **Files in Scope**: `src/fpac_soil_mcp/polygon_analysis.py`
- **Dependencies**: `17.1.1`, `17.1.2`
- **Spec Prose**:
  1. In `src/fpac_soil_mcp/polygon_analysis.py`, extend `PolygonAnalyzer`:
     - Allow callers to pass optional `productivity_index: str = "nccpi"` and `max_county_rating_override: float | None = None`.
     - In `analyze_polygon_sync` and `analyze_polygon_async`, retrieve productivity ratings for intersecting map units using `SDAClient.get_productivity_ratings`.
     - Compute the area-weighted Land Evaluation score and attach a structured `LandEvaluationSummary` to the polygon response.
     - Filter unrated units and include informative data caveats when coverage is partial.
- **Constraints**: Preserve backwards compatibility of existing `PolygonFarmlandAnalysisResponse` fields.
- **Grep Anchors**: `class PolygonAnalyzer` in `src/fpac_soil_mcp/polygon_analysis.py`
- **Acceptance Command**: `uv run pytest tests/test_polygon_analysis.py -q`

---

### Task 17.3.1: MCP Tool Registration for `calculate_preliminary_lesa` & Polygon Integration
- **Task ID**: `17.3.1`
- **Files in Scope**: `src/fpac_soil_mcp/tools/soil_tools.py`, `src/fpac_soil_mcp/tools/__init__.py`
- **Dependencies**: `17.2.1`, `17.2.2`
- **Spec Prose**:
  1. In `src/fpac_soil_mcp/tools/soil_tools.py`:
     - Add tool function `calculate_preliminary_lesa(project_name: str, geometry: dict[str, Any] | str, project_type: str = "site", productivity_index: str = "nccpi", max_county_rating_override: float | None = None, site_assessment_inputs: dict[str, Any] | None = None) -> PreliminaryLESAResponse`.
     - Update `analyze_farmland_by_polygon` tool signature to accept optional `productivity_index` and include candidate LE scoring in output.
     - Register `calculate_preliminary_lesa` with clear descriptions and regulatory citations in `register_soil_tools(mcp)`.
  2. In `src/fpac_soil_mcp/tools/__init__.py`, export the new tool function.
- **Constraints**: Tool parameters must be JSON-serializable and validate coordinates/geometry cleanly.
- **Grep Anchors**: `def register_soil_tools` in `src/fpac_soil_mcp/tools/soil_tools.py`
- **Acceptance Command**: `python -c "from fpac_soil_mcp.tools import calculate_preliminary_lesa; print('Tool exported')"`

---

### Task 17.3.2: Unit & Mocked Test Suite for LE Scoring & SDV Routing
- **Task ID**: `17.3.2`
- **Files in Scope**: `tests/test_lesa.py`, `tests/test_sda_client.py`
- **Dependencies**: `17.2.1`, `17.2.2`
- **Spec Prose**:
  1. Create `tests/test_lesa.py`:
     - Test relative rating normalization across CSR2, CPI, Storie, and NCCPI.
     - Test area-weighting mathematics and rounding ($RR_{\text{AOI}} \times 100$).
     - Test null and unrated map unit filtering and notice generation.
     - Test Site (AD-1006) vs Corridor (CPA-106) scoring rules and zeroed criteria.
     - Test 160-point threshold evaluation (both $<160$ and $\ge 160$).
     - Validate against `tests/fixtures/le_benchmarks.json`.
  2. In `tests/test_sda_client.py`:
     - Add mocked tests for `get_productivity_ratings` covering NCCPI, CSR2, CPI, Storie index queries and error handling.
- **Constraints**: Fast mocked execution under `pytest -m "not live_network"`.
- **Grep Anchors**: `tests/test_lesa.py`
- **Acceptance Command**: `uv run pytest tests/test_lesa.py tests/test_sda_client.py -q`

---

### Task 17.4.1: Benchmark Eval Fixture Suite Expansion for LESA Scoring
- **Task ID**: `17.4.1`
- **Files in Scope**: `eval/prompt_test_cases.json`
- **Dependencies**: `17.3.1`, `17.3.2`
- **Spec Prose**:
  1. In `eval/prompt_test_cases.json`, add comprehensive evaluation prompt test cases covering the new Phase 4 LESA capabilities:
     - Candidate LE calculation prompts (testing `calculate_preliminary_lesa` and `analyze_farmland_by_polygon` with productivity indexes like NCCPI, CSR2, CPI).
     - Full LESA evaluation prompts verifying expected tool routing to `calculate_preliminary_lesa` and assertions for Land Evaluation, Site Assessment, and the 160-point statutory threshold flag.
     - Natural language queries requesting state-specific productivity ratings (e.g. CSR2 in Story County, IA).
  2. Verify JSON schema formatting and valid structure.
- **Constraints**: Valid JSON matching `eval/prompt_test_cases.json` schema; verify test cases with `--help` or runner discovery.
- **Grep Anchors**: `eval/prompt_test_cases.json`
- **Acceptance Command**: `python -c "import json; data=json.load(open('eval/prompt_test_cases.json')); assert any(c.get('target_name') == 'calculate_preliminary_lesa' for c in data['test_cases']); print('Eval fixtures valid')"`

---

### Task 17.4.2: End-to-End Verification, Documentation & Plan 17 State Finalization
- **Task ID**: `17.4.2`
- **Files in Scope**: `README.md`, `planning/STATE_17.md`, `planning/tasks/17.4.2.todo.md`
- **Dependencies**: `17.4.1`
- **Spec Prose**:
  1. Run complete offline test suite: `uv run pytest -m "not live_network and not agent_eval" -q`.
  2. Run linter: `uv run ruff check .` and `uv run ruff format --check .`.
  3. Update `README.md` documenting `calculate_preliminary_lesa`, supported productivity indexes (NCCPI, CSR2, CPI, Storie), and candidate LE score calculations.
  4. Create `planning/STATE_17.md` and task todo records verifying all Phase 4 Part 1 tasks are completed.
- **Constraints**: 100% clean test suite and linter check.
- **Grep Anchors**: `planning/STATE_17.md`
- **Acceptance Command**: `uv run pytest -m "not live_network and not agent_eval" -q`
