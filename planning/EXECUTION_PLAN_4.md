# EXECUTION PLAN 4: Phase 2 Polygon AOI Screening & Farmland Analysis

## Goal & Scope

### Goal
Implement polygon Area of Interest (AOI) ingestion and spatial soil analysis for FPPA screening. Deliver geospatial geometry validation, local equal-area acreage calculation, SSURGO map unit spatial queries via SDA WKT intersection, farmland classification breakdowns (prime, unique, statewide/local importance, not-prime, unmapped), Census 2020 TIGERweb urban area pre-screening (7 CFR § 658.2(a)), and component-weighted SDA soil interpretations (including NCCPI v3) while enforcing strict human authority boundaries and preliminary screening notices.

### In Scope
1. **Geometry Validation & Acreage Computation**:
   - Ingest GeoJSON `Polygon` and `MultiPolygon` inputs.
   - Validate coordinate bounds (WGS84 lat [-90, 90], lon [-180, 180]), vertex counts, ring closure, and planar validity/self-intersections using `shapely` (with optional `pyproj` / equal-area projection handling).
   - Calculate geodesic/planar acreage using standard equal-area projections (e.g. Albers Equal Area EPSG:5070 for CONUS / local UTM projections) with verified benchmark tolerance (<0.1%).
   - Generate deterministic geometry hashes (SHA-256) for all ingested footprints.
2. **SSURGO Spatial Querying & SDA Client Expansion**:
   - Query intersecting map units using parameterized WKT queries (`SDA_Get_Mukey_from_intersection_with_WktWgs84` / `mupolygon` spatial queries adapted from `py-soildb` / `soilDB` patterns).
   - Ingest component-weighted soil interpretations (NCCPI v3 non-irrigated/irrigated and crop submodels) using parameterized T-SQL templates and parse rating scores, rating classes, and limiting reasons into `SoilInterpretationRecord`.
3. **Census TIGERweb 2020 Urban Area Pre-Screening**:
   - HTTP client for Census TIGERweb 2020 Urban Areas MapServer (Layer 6) to screen project footprints against statutory urbanized boundaries (7 CFR § 658.2(a)).
   - Populate `UrbanExemptionRecord` with intersected urban area names, population, housing unit stats, and non-binding preliminary screening status without issuing formal agency exemption rulings.
4. **FastMCP Tools & Response Models**:
   - Expose `analyze_farmland_by_polygon` accepting GeoJSON polygon/multipolygon geometries, returning full acreage breakdowns by farmland classification, urban screening status, soil interpretation metrics, query source provenance, and FPPA regulatory notices.
   - Expose auxiliary specialized tools: `check_urban_area_exemption` and `get_soil_interpretations`.
   - Update `models.py` with `PolygonFarmlandAnalysisResponse`, `SoilMapUnitAcreage`, and summary schemas.
5. **Artifacts & Output Manifests**:
   - Generate structured JSON summary, tabular CSV map-unit acreage breakdown, and execution manifest.
6. **Testing & Test Fixtures**:
   - 50 reviewed test AOI fixtures matching ground truth benchmarks within 0.1% acreage tolerance.
   - Offline mocked tests for TIGERweb, SDA spatial queries, and NCCPI interpretation rules.
   - Opt-in live tests for network endpoints marked `@pytest.mark.live_sda`.

### Out of Scope
- Linear corridor segmentation and multi-county partitioning (Phase 3).
- Full Land Evaluation & Site Assessment (LE-SA) scoring workbench and 160-point threshold evaluation (Phase 4).
- Draft AD-1006 / CPA-106 form population and alternatives comparison (Phase 5).
- SQLite persistence, audit logs, and CPA-2 annual summary generation (Phase 6).
- Issuing formal, binding NRCS Land Evaluation determinations or legal FPPA exemption approvals.

### Verbatim Constraints
- "Preserve the preliminary-screening limitation in every soil-query response: this service does not produce an official FPPA determination, LESA score, Form AD-1006, or NRCS-CPA-106."
- "Accept only validated coordinates or numeric positive mukey values. Do not add user-supplied SQL passthrough."
- "50 test AOIs match reviewed test fixtures within 0.1% acreage tolerance."
- "Conditional prime classifications are reported accurately without silent conversions."
- "Response payloads include full geometry hashes and query metadata."
- "Reviewed urban-area fixtures produce the expected preliminary screening flags and preserve non-exempt acreage for soil analysis."
- "SDA interpretation and NCCPI results match verified offline benchmark fixtures."
- "Do not make live SDA tests part of the default offline test path."

---

## Decision Log

- **2026-09-17**: Use `shapely` and `pyproj` (or standard ellipsoidal area calculations) for geometry parsing, validation, WKT generation, and equal-area acreage calculation. Replicate/incorporate robust query sanitization and spatial query patterns from `py-soildb` directly.
- **2026-09-17**: TIGERweb client uses ArcGIS REST query parameters (`inSR=4326`, `spatialRel=esriSpatialRelIntersects`, `f=json`) against Layer 6, returning `UrbanExemptionRecord` with `machine_estimate` authority.
- **2026-09-17**: SDA interpretation engine ports T-SQL CTEs from `soilDB::get_SDA_interpretation` for component-weighted and dominant-component aggregation, strictly validating rule names against `sda_interpretation_rules_allowed`.
- **2026-09-17**: `analyze_farmland_by_polygon` tool returns detailed acreage breakdowns (prime, unique, statewide, local, not_prime, unmapped) with percentage and total acreage summaries, paired with mandatory `REGULATORY_NOTICE` and limitations.
- **2026-09-17**: Benchmark test corpus includes 50 synthetic and real-world GeoJSON fixtures (CONUS, Alaska, Hawaii, urban-fringe, multi-unit complexes) tested offline against mocked HTTP responses.
- **2026-09-17**: Concurrency: Max 3 workers in parallel worktrees. Serial test runs at wave boundaries.

---

## Technical Reconnaissance

- **Current State**: Phase 0 (stateless point/mukey screening) and Phase 1 (domain, governance, authority, privacy, and integration models) are complete and green.
- **Dependencies**: `pyproject.toml` currently has `fastmcp`, `httpx`, `pydantic`, `pydantic-settings`. Adding `shapely>=2.0.0` and `pyproj>=3.6.0` provides standard equal-area and planar geometry processing.
- **Integration Models**: `UrbanExemptionRecord`, `SoilInterpretationRecord`, and `Provenance` are already implemented and validated in `integration_models.py` and `authority.py`.
- **Existing Files & Anchors**:
  - `src/fpac_soil_mcp/sda_client.py`: Anchor at `SDAClient._execute_query` and `_parse_table_response`.
  - `src/fpac_soil_mcp/config.py`: Anchor at `tigerweb_rest_url`, `sda_interpretation_rules_allowed`.
  - `src/fpac_soil_mcp/models.py`: Anchor at `FarmlandClassificationResponse`.
  - `src/fpac_soil_mcp/tools/soil_tools.py`: Anchor at `get_farmland_classification_by_point`.
  - `src/fpac_soil_mcp/tools/__init__.py`: Tool registration registry.

---

## Wave Dependency Graph

```text
4.1.1 Spatial Primitives & Dependencies (pyproject.toml, geometry.py)
  ├── 4.2.1 SDA Spatial & Interpretation Engine (sda_client.py) ──┐
  ├── 4.2.2 Census TIGERweb Client (tigerweb_client.py)          ├── 4.3.1 Polygon Analysis Engine (polygon_analysis.py, models.py)
  │                                                              │      └── 4.4.1 FastMCP Polygon Tools & Registration (tools/, app.py)
  └── 4.2.3 50-AOI Benchmark Fixture Corpus (fixtures/) ─────────┘            └── 4.5.1 Phase 2 End-to-End Contract & Regression Tests
```

---

## Wave Table

| Wave | Task ID | Title | Files in Scope | Depends On |
| --- | --- | --- | --- | --- |
| 1 | `4.1.1` | Spatial Primitives & Geometry Engine | `pyproject.toml`, `src/fpac_soil_mcp/geometry.py`, `tests/test_geometry.py` | Baseline |
| 2 | `4.2.1` | SDA Spatial & Interpretation Engine | `src/fpac_soil_mcp/sda_client.py`, `tests/test_sda_client.py` | `4.1.1` |
| 2 | `4.2.2` | Census TIGERweb Urban Area Client | `src/fpac_soil_mcp/tigerweb_client.py`, `tests/test_tigerweb_client.py` | `4.1.1` |
| 2 | `4.2.3` | 50-AOI Benchmark Fixtures & Validation | `tests/fixtures/aoi/*.json`, `tests/test_aoi_fixtures.py` | `4.1.1` |
| 3 | `4.3.1` | Polygon Analysis Engine & Response Models | `src/fpac_soil_mcp/models.py`, `src/fpac_soil_mcp/polygon_analysis.py`, `tests/test_polygon_analysis.py` | `4.2.1`, `4.2.2`, `4.2.3` |
| 4 | `4.4.1` | FastMCP Polygon Screening Tools | `src/fpac_soil_mcp/tools/soil_tools.py`, `src/fpac_soil_mcp/tools/__init__.py`, `tests/test_tools.py` | `4.3.1` |
| 5 | `4.5.1` | Phase 2 Contract & Regression Suite | `tests/test_phase2_contracts.py`, `README.md`, `manifest.yaml`, `server.json` | `4.4.1` |

---

## Task Specifications

### Task 4.1.1: Spatial Primitives & Geometry Engine
- **ID**: `4.1.1`
- **Repo**: `.`
- **Files in Scope**:
  - *Must edit*: `pyproject.toml` (add `shapely>=2.0.0`, `pyproj>=3.6.0`)
  - *Must create*: `src/fpac_soil_mcp/geometry.py`, `tests/test_geometry.py`, `planning/tasks/4.1.1.todo.md`
  - *May edit for report only*: `planning/STATE_4.md`
  - *Temp/scratch*: `.development/`
- **Depends on**: Green baseline
- **Spec Prose**: Add `shapely` and `pyproj` to `pyproject.toml`. Implement `geometry.py` with utilities to validate GeoJSON `Polygon` and `MultiPolygon` inputs, check vertex count and bounding box limits, repair self-intersections/topological validity (`shapely.validation.make_valid`), calculate geodesic equal-area acreage (using Albers Equal Area EPSG:5070 / local equal-area projections), convert GeoJSON to WKT strings safely (incorporating `validate_wkt_geometry` from `py-soildb`), and compute deterministic SHA-256 geometry hashes.
- **Constraints / Do Not Touch**:
  - Do not introduce GDAL, Fiona, or C-library wrappers beyond Shapely/pyproj wheels.
  - Do not touch existing `sda_client.py`, `authority.py`, or `models.py`.
- **Grep Anchors / References**:
  - `RESEARCH_PUBLIC_APIS_AND_INTERPRETATIONS.md` Section 3 & 4.
  - `src/fpac_soil_mcp/authority.py` for provenance hashing conventions.
- **Acceptance & Targeted Test Command**:
  - `uv sync` succeeds.
  - `uv run pytest tests/test_geometry.py -q` passes (verifying acreage calculation accuracy, invalid geometry rejection, WKT conversion, and hashing).

### Task 4.2.1: SDA Spatial & Interpretation Engine
- **ID**: `4.2.1`
- **Repo**: `.`
- **Files in Scope**:
  - *Must edit*: `src/fpac_soil_mcp/sda_client.py`, `tests/test_sda_client.py`
  - *Must create*: `planning/tasks/4.2.1.todo.md`
  - *May edit for report only*: `planning/STATE_4.md`
  - *Temp/scratch*: `.development/`
- **Depends on**: `4.1.1`
- **Spec Prose**: Extend `SDAClient` with spatial and interpretation capabilities. Add parameterized SQL templates for polygon intersection (`SDA_Get_Mukey_from_intersection_with_WktWgs84` and `mupolygon` spatial queries) and component-weighted interpretation queries (porting `soilDB::get_SDA_interpretation` T-SQL CTEs for weighted average and dominant component aggregation). Implement `get_by_polygon(wkt_polygon)` and `get_interpretations(mukeys, rule_name, aggregation_method)`. Validate rule names against `settings.sda_interpretation_rules_allowed`. Map outputs to dictionaries compatible with `SoilInterpretationRecord`.
- **Constraints / Do Not Touch**:
  - Do not allow raw SQL injection; sanitize WKT and numeric keys strictly.
  - Do not break existing `get_by_point` or `get_by_mukey`.
- **Grep Anchors / References**:
  - `src/fpac_soil_mcp/sda_client.py` at `SQL_POINT_LOOKUP`.
  - `RESEARCH_PUBLIC_APIS_AND_INTERPRETATIONS.md` Section 4.3.
- **Acceptance & Targeted Test Command**:
  - `uv run pytest tests/test_sda_client.py -q` passes with mocked responses for polygon intersection and NCCPI queries.

### Task 4.2.2: Census TIGERweb Urban Area Client
- **ID**: `4.2.2`
- **Repo**: `.`
- **Files in Scope**:
  - *Must create*: `src/fpac_soil_mcp/tigerweb_client.py`, `tests/test_tigerweb_client.py`, `planning/tasks/4.2.2.todo.md`
  - *May edit for report only*: `planning/STATE_4.md`
  - *Temp/scratch*: `.development/`
- **Depends on**: `4.1.1`
- **Spec Prose**: Implement `TigerwebClient` to query the Census 2020 Urban Areas MapServer Layer 6 endpoint via ArcGIS REST query API (`/query`). Accept GeoJSON polygon/multipolygon geometries or points, perform spatial intersection requests with `spatialRel=esriSpatialRelIntersects`, `inSR=4326`, and parse responses into `UrbanExemptionRecord` instances (from `integration_models.py`). Include robust retry and timeout handling. Handle offline/mocked modes gracefully with clear `UNAVAILABLE` or `ERROR` statuses on failure.
- **Constraints / Do Not Touch**:
  - Do not claim legal exemption determinations; enforce preliminary screening limitations in all outputs.
  - Do not edit `integration_models.py` or `case_models.py`.
- **Grep Anchors / References**:
  - `src/fpac_soil_mcp/integration_models.py` at `class UrbanExemptionRecord`.
  - `RESEARCH_PUBLIC_APIS_AND_INTERPRETATIONS.md` Section 3.4.
- **Acceptance & Targeted Test Command**:
  - `uv run pytest tests/test_tigerweb_client.py -q` passes with mocked Urban Area intersection fixtures.

### Task 4.2.3: 50-AOI Benchmark Fixtures & Validation
- **ID**: `4.2.3`
- **Repo**: `.`
- **Files in Scope**:
  - *Must create*: `tests/fixtures/aoi/*.json`, `tests/test_aoi_fixtures.py`, `planning/tasks/4.2.3.todo.md`
  - *May edit for report only*: `planning/STATE_4.md`
  - *Temp/scratch*: `.development/`
- **Depends on**: `4.1.1`
- **Spec Prose**: Construct a benchmark fixture corpus of 50 diverse GeoJSON AOIs (covering standard agricultural parcels, urban-fringe areas, irregular multi-polygons, complex topology, CONUS, Alaska, and Hawaii). Record ground-truth acreage benchmarks, expected farmland classification breakdowns, and Census Urban Area intersection statuses. Build automated tests verifying that the geometry engine computes acreage matching benchmark ground truth within 0.1% tolerance.
- **Constraints / Do Not Touch**:
  - Keep fixtures clean, validated JSON without proprietary or sensitive GIS attributes.
- **Grep Anchors / References**:
  - `MASTER_PLAN.md` Phase 2 Exit Criteria ("50 test AOIs match reviewed test fixtures within 0.1% acreage tolerance").
- **Acceptance & Targeted Test Command**:
  - `uv run pytest tests/test_aoi_fixtures.py -q` passes on all 50 fixtures.

### Task 4.3.1: Polygon Analysis Engine & Response Models
- **ID**: `4.3.1`
- **Repo**: `.`
- **Files in Scope**:
  - *Must edit*: `src/fpac_soil_mcp/models.py`
  - *Must create*: `src/fpac_soil_mcp/polygon_analysis.py`, `tests/test_polygon_analysis.py`, `planning/tasks/4.3.1.todo.md`
  - *May edit for report only*: `planning/STATE_4.md`
  - *Temp/scratch*: `.development/`
- **Depends on**: `4.2.1`, `4.2.2`, `4.2.3`
- **Spec Prose**: In `models.py`, add response models: `SoilMapUnitAcreage`, `FarmlandCategoryBreakdown` (acres and percentage for prime, unique, statewide, local, not_prime, unmapped), and `PolygonFarmlandAnalysisResponse`. In `polygon_analysis.py`, orchestrate full polygon screening: validate geometry, compute total acreage and hash, check Census Urban Area exemption via `TigerwebClient`, query intersecting map units via `SDAClient`, fetch NCCPI/interpretation records, group and summarize acreages by farmland class, generate CSV table strings and JSON manifests, and bundle authoritative provenance with `REGULATORY_NOTICE`.
- **Constraints / Do Not Touch**:
  - Do not drop conditional prime farmland classifications (e.g. "Prime farmland if drained" must be preserved as prime or conditional without silent truncation).
  - Always include `REGULATORY_NOTICE` and limitations.
- **Grep Anchors / References**:
  - `src/fpac_soil_mcp/constants.py` at `FARMLAND_CLASS_MAP`.
  - `src/fpac_soil_mcp/models.py` at `FarmlandClassificationResponse`.
- **Acceptance & Targeted Test Command**:
  - `uv run pytest tests/test_polygon_analysis.py -q` passes.

### Task 4.4.1: FastMCP Polygon Screening Tools
- **ID**: `4.4.1`
- **Repo**: `.`
- **Files in Scope**:
  - *Must edit*: `src/fpac_soil_mcp/tools/soil_tools.py`, `src/fpac_soil_mcp/tools/__init__.py`, `src/fpac_soil_mcp/tools/fppa_tools.py`, `tests/test_tools.py`
  - *Must create*: `planning/tasks/4.4.1.todo.md`
  - *May edit for report only*: `planning/STATE_4.md`
  - *Temp/scratch*: `.development/`
- **Depends on**: `4.3.1`
- **Spec Prose**: Expose new MCP tools: `analyze_farmland_by_polygon(geojson: dict | str)` (executing full screening), `check_urban_area_exemption(geojson: dict | str)` (executing Census 2020 urban screening), and `get_soil_interpretations(mukeys: list[str], rule_name: str, aggregation_method: str = "Weighted Average")`. Register tools in `tools/__init__.py` and verify `app.py` exposes them without breaking existing point/mukey tools. Add thorough tool tests with valid and invalid inputs.
- **Constraints / Do Not Touch**:
  - Keep tool signatures clean, well-documented with docstrings and type hints.
  - Do not break existing tools `get_farmland_classification_by_point` or `get_farmland_classification_by_mukey`.
- **Grep Anchors / References**:
  - `src/fpac_soil_mcp/tools/soil_tools.py` at `register_soil_tools`.
  - `src/fpac_soil_mcp/app.py` at `create_mcp_server`.
- **Acceptance & Targeted Test Command**:
  - `uv run pytest tests/test_tools.py -q` passes with new tool invocations tested.

### Task 4.5.1: Phase 2 Contract & Regression Suite
- **ID**: `4.5.1`
- **Repo**: `.`
- **Files in Scope**:
  - *Must edit*: `README.md`, `manifest.yaml`, `server.json`
  - *Must create*: `tests/test_phase2_contracts.py`, `planning/tasks/4.5.1.todo.md`
  - *May edit for report only*: `planning/STATE_4.md`
  - *Temp/scratch*: `.development/`
- **Depends on**: `4.4.1`
- **Spec Prose**: Implement comprehensive Phase 2 contract tests in `test_phase2_contracts.py` validating end-to-end polygon workflows, acreage reconciliation across classifications, urban screening integration, NCCPI interpretations, offline error recovery, and strict non-official disclaimer enforcement. Update documentation (`README.md`), `manifest.yaml`, and `server.json` to describe the new polygon analysis, urban screening, and soil interpretation capabilities.
- **Constraints / Do Not Touch**:
  - Verify all offline tests pass (`uv run pytest -m "not live_sda"`).
  - Code and docs must pass `ruff check .` cleanly.
- **Grep Anchors / References**:
  - `README.md` MCP Tools section.
  - `manifest.yaml` tools schema.
- **Acceptance & Targeted Test Command**:
  - `uv run pytest tests/test_phase2_contracts.py -q` passes.
  - `uv run pytest -m "not live_sda"` passes completely.
  - `uv run ruff check .` passes.
