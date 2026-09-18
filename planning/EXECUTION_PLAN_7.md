# EXECUTION PLAN 7: Phase 3 Multi-County Corridor Analysis (CPA-106)

## Goal & Scope

### Goal
Implement geodesic linear corridor centerline ingestion, automated equal-area buffering, direct vs. indirect impact polygon separation (with automated topological erasure to prevent double-counting), true multi-county segment partitioning via Census TIGERweb county boundaries, independent per-segment SSURGO soil and USDA NASS agricultural baseline queries, strict sum reconciliation (within 0.1% acreage tolerance), 7 CFR § 658.5(c) corridor Site Assessment scoring rules, and FastMCP tool exposure (`analyze_corridor_fppa`) with non-binding preliminary screening notices.

### In Scope
1. **Corridor Centerline Ingestion & Geodesic Buffering**:
   - Ingest GeoJSON `LineString`, `MultiLineString`, or WKT centerlines with user-specified buffer widths (`buffer_distance` with explicit units: `feet`, `meters`, `miles`).
   - Automate geodesic buffering in equal-area projection space (EPSG:6933 / local equal-area CRS) to generate direct right-of-way conversion polygons.
2. **Impact Area Separation (Direct vs. Indirect vs. Alternatives)**:
   - Track direct corridor conversion (buffered centerline) and indirect impact areas (e.g. construction staging, access roads) as distinct geometries.
   - Automatically erase indirect impact polygons against direct corridor polygons to prevent double-counting of converted farmland.
   - Support up to three named alternative corridor alignments (Corridor Alternatives B, C, and D) matching the Form NRCS-CPA-106 specification.
3. **Census TIGERweb County Partitioning & USDA NASS QuickStats Client**:
   - Expand `TigerwebClient` or add county spatial boundary querying (TIGERweb Geography/County layer) to dynamically partition corridors into discrete county segments ($S_1, S_2, \dots, S_k$).
   - Implement `NassClient` (`src/fpac_soil_mcp/nass_client.py`) to query USDA NASS QuickStats REST API (`/api_GET/`) for county-level baseline demographics (land in farms, cropland, average farm size), returning `CountyAgProfile` records with graceful `unavailable` status handling.
4. **True Multi-County Segment Partitioning & Sum Reconciliation Engine**:
   - Process each county segment independently against USDA SDA for soil map unit intersections and USDA NASS for agricultural baselines.
   - Calculate composite acreage-weighted relative Land Evaluation ratings ($RR_{\text{composite}} = \sum (RR_{\text{county\_k}} \times \text{Area}_k / \text{Total Area})$).
   - Enforce rigorous sum reconciliation ensuring segment direct, indirect, prime, and converted acreages sum exactly to total corridor project dimensions within 0.1% tolerance.
5. **Corridor Site Assessment Rules Engine (7 CFR § 658.5(c))**:
   - Implement statutory CPA-106 Site Assessment rules:
     - Criterion 5 (Severance of farm infrastructure) and Criterion 6 (Agricultural support services) are **zeroed out** (0 points).
     - Criterion 8 (Off-farm investments) and Criterion 11 (Alternative corridor routes) are adjusted from 15 to **25 points each** (maintaining the 160-point SA maximum).
6. **FastMCP Corridor Tools & Registration**:
   - Expose `analyze_corridor_fppa` on the FastMCP server, accepting centerline/buffer, indirect polygons, and alternative alignments.
   - Update `models.py` with `CorridorFarmlandAnalysisResponse`, `CorridorCountySegment`, and summary models.
7. **Testing & Benchmark Verification**:
   - Multi-county synthetic and real-world corridor test fixtures traversing 2+ and 5+ counties / state lines.
   - Offline mocked tests for NASS, TIGERweb county queries, and SDA corridor intersections.
   - Opt-in live tests marked `@pytest.mark.live_sda`.

### Out of Scope
- Full general Land Evaluation (LE) dynamic SDV attribute routing for state-specific productivity indexes (CSR2, Storie) on general site parcels (Phase 4).
- Watermarked Form AD-1006 / CPA-106 Word document generation and clearance letter generation (Phase 5).
- SQLite database persistence, case lifecycle state persistence, and annual CPA-2 multi-agency rollups (Phase 6).
- Issuing formal, legally binding NRCS Land Evaluation determinations or signed agency clearances.

### Verbatim Constraints
- "Multi-county test corridors split cleanly across county and soil survey boundaries without geographic gaps or overlaps."
- "Calculations strictly adhere to 7 CFR § 658.5(c) corridor scoring rules rather than AD-1006 parcel rules."
- "Direct, indirect, prime, and converted acreages across multi-county segments reconcile to the full corridor acreage within 0.1% tolerance."
- "Every intersected county receives an independent NASS agricultural baseline or explicit unavailable-data status with full provenance."
- "System gracefully handles multi-county corridors traversing 5+ counties and multi-state boundaries."
- "Preserve the preliminary-screening limitation in every soil-query response: this service does not produce an official FPPA determination, LESA score, Form AD-1006, or NRCS-CPA-106."
- "Accept only validated coordinates or numeric positive mukey values. Do not add user-supplied SQL passthrough."

---

## Decision Log

- **2026-09-18**: Ingest corridor centerlines as GeoJSON `LineString`, `MultiLineString`, or WKT, supporting buffer distances with explicit unit conversions (`feet`, `meters`, `miles`) transformed to equal-area projection space (EPSG:6933) before buffering.
- **2026-09-18**: Overcome desktop GIS single-county simplification by performing dynamic Census TIGERweb county intersection, partitioning corridors into discrete county segments ($S_1, \dots, S_k$), and enforcing mathematical sum reconciliation within 0.1% tolerance.
- **2026-09-18**: Implement live `NassClient` for USDA NASS QuickStats (`https://quickstats.nass.usda.gov/api/api_GET/`) with fallback to `IntegrationStatus.UNAVAILABLE` when `nass_api_key` is not configured or network requests fail.
- **2026-09-18**: Implement 7 CFR § 658.5(c) corridor Site Assessment scoring rules (Criteria 5 & 6 zeroed; Criteria 8 & 11 adjusted to 25 max points).
- **2026-09-18**: Expose `analyze_corridor_fppa` tool on the FastMCP server, wired through `src/fpac_soil_mcp/tools/soil_tools.py` and `tools/__init__.py`.
- **2026-09-18**: Max 3 concurrent workers in isolated worktrees. Shared test suites run serially at wave boundaries.

---

## Technical Reconnaissance

- **Current Repository State**: Phases 0, 1, and 2 complete. 120 offline tests passing. Lint clean.
- **Key Modules & Code References**:
  - `src/fpac_soil_mcp/geometry.py`: Contains `parse_geojson_geometry`, `calculate_acreage`, `compute_geometry_hash`, `validate_wkt_string`. Needs line buffering and polygon erasure (`difference`).
  - `src/fpac_soil_mcp/tigerweb_client.py`: Intersects 2020 Urban Areas MapServer. Can query TIGERweb County layer or accept county boundary geometries.
  - `src/fpac_soil_mcp/sda_client.py`: Spatial WKT intersection (`get_spatial_intersection`, `get_by_polygon`).
  - `src/fpac_soil_mcp/models.py`: Contains `PolygonFarmlandAnalysisResponse`, `SoilMapUnitAcreage`, `FarmlandCategoryBreakdown`.
  - `src/fpac_soil_mcp/tools/soil_tools.py`: Tool definitions for FastMCP.
- **File Sizes & Anchors**:
  - `geometry.py`: ~175 lines.
  - `tigerweb_client.py`: ~205 lines.
  - `sda_client.py`: ~450 lines.
  - `models.py`: ~210 lines.
  - `tools/soil_tools.py`: ~260 lines.

---

## Hazards and Guardrails

- **Double-Counting Converted Acres**: Direct corridor footprint and indirect staging areas can overlap. The engine must automatically erase direct geometry from indirect geometry (`indirect_clean = indirect.difference(direct)`).
- **Single-County Fallback Hazard**: Never collapse multi-county corridors into the single largest county. Every intersected county segment must be analyzed independently and reconciled into composite scores.
- **Acreage Reconciliation Tolerance**: The sum of segment direct, indirect, and classified farmland acreages must equal total project dimensions within 0.1% tolerance; differences >0.1% must raise a reconciliation warning or error.
- **Missing NASS Key Handling**: If `nass_api_key` is absent or NASS API fails, the tool must not crash; it must return `CountyAgProfile` with status `unavailable` and complete provenance.
- **Buffer Unit Errors**: Verify unit conversions (1 foot = 0.3048 m, 1 mile = 1609.344 m) before projecting to metric equal-area coordinates.

---

## Wave Dependency Graph

```text
7.1.1 Corridor Buffering & Geometry Primitives (geometry.py, pyproject.toml)
  ├── 7.2.1 USDA NASS QuickStats REST Client (nass_client.py, config.py) ──┐
  ├── 7.2.2 TIGERweb County Partitioning Engine (tigerweb_client.py)       ├── 7.3.1 Corridor Multi-County Partitioning & Reconciliation Engine (corridor_analysis.py, models.py)
  │                                                                        │      └── 7.4.1 7 CFR § 658.5(c) Corridor Site Assessment Rules Engine (corridor_scoring.py)
  └── 7.2.3 Multi-County Corridor Test Fixtures Corpus (fixtures/corridor/)│             └── 7.5.1 FastMCP Corridor Tools & Registration (tools/soil_tools.py, app.py)
                                                                           │                    └── 7.6.1 Phase 3 Contract, End-to-End & Regression Suite
```

---

## Wave Table

| Wave | Task ID | Title | Files in Scope | Depends On |
| --- | --- | --- | --- | --- |
| 1 | `7.1.1` | Corridor Geodesic Buffering & Geometry Primitives | `src/fpac_soil_mcp/geometry.py`, `tests/test_geometry.py` | Baseline |
| 2 | `7.2.1` | USDA NASS QuickStats REST Client | `src/fpac_soil_mcp/nass_client.py`, `src/fpac_soil_mcp/config.py`, `tests/test_nass_client.py` | Baseline |
| 2 | `7.2.2` | TIGERweb County Boundary & Partitioning Client | `src/fpac_soil_mcp/tigerweb_client.py`, `tests/test_tigerweb_client.py` | `7.1.1` |
| 2 | `7.2.3` | Multi-County Corridor Test Fixture Corpus | `tests/fixtures/corridor/*.json`, `tests/test_corridor_fixtures.py` | `7.1.1` |
| 3 | `7.3.1` | Multi-County Corridor Analysis & Reconciliation Engine | `src/fpac_soil_mcp/models.py`, `src/fpac_soil_mcp/corridor_analysis.py`, `tests/test_corridor_analysis.py` | `7.2.1`, `7.2.2`, `7.2.3` |
| 4 | `7.4.1` | 7 CFR § 658.5(c) Corridor Site Assessment Rules Engine | `src/fpac_soil_mcp/corridor_scoring.py`, `tests/test_corridor_scoring.py` | `7.3.1` |
| 5 | `7.5.1` | FastMCP Corridor Analysis Tools & Server Registration | `src/fpac_soil_mcp/tools/soil_tools.py`, `src/fpac_soil_mcp/tools/__init__.py`, `tests/test_tools.py` | `7.4.1` |
| 6 | `7.6.1` | Phase 3 Contract, End-to-End & Documentation Suite | `tests/test_phase3_contracts.py`, `README.md`, `manifest.yaml`, `server.json` | `7.5.1` |

---

## Task Specifications

### Wave 1

#### Task 7.1.1: Corridor Geodesic Buffering & Geometry Primitives
- **ID**: `7.1.1`
- **Repo**: `.`
- **Files in Scope**:
  - *Must edit*: `src/fpac_soil_mcp/geometry.py`, `tests/test_geometry.py`
  - *Must create*: `planning/tasks/7.1.1.todo.md`
  - *May edit for report only*: `planning/STATE_7.md`
  - *Temp/scratch*: `.development/`
- **Depends on**: Green baseline
- **Spec Prose**: Extend `geometry.py` with capabilities for linear corridor processing:
  1. `buffer_centerline(centerline_input, buffer_distance, distance_unit="feet") -> Polygon | MultiPolygon`: accepts GeoJSON `LineString`, `MultiLineString`, or WKT string; converts distance from specified units (`feet`, `meters`, `miles`) to meters; reprojects to equal-area projection space (EPSG:6933 / local equal-area projection) for geodesic accuracy, applies standard buffer with flat/round end-caps, and transforms back to WGS84 (`EPSG:4326`).
  2. `erase_geometries(base_geom, erase_geom) -> Polygon | MultiPolygon`: performs clean topological difference (`base_geom.difference(erase_geom)` with `make_valid` repair) to prevent double-counting between direct right-of-way and indirect staging areas.
  3. Support line geometries in `parse_geojson_geometry` and update WKT validators.
- **Constraints / Do Not Touch**:
  - Preserve all existing polygon and point parsing behavior.
  - Do not introduce heavy C-dependencies beyond `shapely` and `pyproj`.
- **Grep Anchors**:
  - `src/fpac_soil_mcp/geometry.py`: `def calculate_acreage`, `def parse_geojson_geometry`.
- **Acceptance & Targeted Test Command**:
  - `uv run pytest tests/test_geometry.py -q` passes with tests for line buffering, unit conversions, geometry erasure, and geometry hashing.

---

### Wave 2

#### Task 7.2.1: USDA NASS QuickStats REST Client
- **ID**: `7.2.1`
- **Repo**: `.`
- **Files in Scope**:
  - *Must create*: `src/fpac_soil_mcp/nass_client.py`, `tests/test_nass_client.py`, `planning/tasks/7.2.1.todo.md`
  - *Must edit*: `src/fpac_soil_mcp/config.py`
  - *May edit for report only*: `planning/STATE_7.md`
  - *Temp/scratch*: `.development/`
- **Depends on**: Green baseline
- **Spec Prose**: Implement `NassClient` in `src/fpac_soil_mcp/nass_client.py` for querying the USDA NASS QuickStats REST API (`https://quickstats.nass.usda.gov/api/api_GET/`).
  - Query parameters: `source_desc=CENSUS`, `sector_desc=ECONOMICS`, `agg_level_desc=COUNTY`, `year={census_year}`, `state_alpha={state}`, `county_name={county}` or FIPS codes.
  - Parse demographic indicators: land in farms (`AG LAND - ACRES`), harvested cropland (`AG LAND, CROPLAND, HARVESTED - ACRES`), farm operations count (`FARM OPERATIONS - NUMBER OF OPERATIONS`), and average farm size (`FARM OPERATIONS - ACRES / OPERATION`).
  - Return `CountyAgProfile` (defined in `integration_models.py`) with complete `Provenance`.
  - If `nass_api_key` is not configured or an HTTP error occurs, gracefully return `CountyAgProfile` with `status=IntegrationStatus.UNAVAILABLE` or `ERROR`, preserving error messages and provenance without throwing unhandled exceptions.
  - Include optional `http_client` injection for deterministic offline unit testing.
- **Constraints / Do Not Touch**:
  - Do not make live network calls in standard offline tests.
  - Retain `nass_enabled` and `nass_api_key` configuration rules in `config.py`.
- **Grep Anchors**:
  - `src/fpac_soil_mcp/integration_models.py`: `class CountyAgProfile`.
  - `planning/RESEARCH_PUBLIC_APIS_AND_INTERPRETATIONS.md`: Section 2 `USDA-NASS Quick Stats API Integration`.
- **Acceptance & Targeted Test Command**:
  - `uv run pytest tests/test_nass_client.py -q` passes with mocked HTTP responses covering success, missing key, unavailable fields, and network errors.

#### Task 7.2.2: TIGERweb County Boundary & Partitioning Client
- **ID**: `7.2.2`
- **Repo**: `.`
- **Files in Scope**:
  - *Must edit*: `src/fpac_soil_mcp/tigerweb_client.py`, `tests/test_tigerweb_client.py`
  - *Must create*: `planning/tasks/7.2.2.todo.md`
  - *May edit for report only*: `planning/STATE_7.md`
  - *Temp/scratch*: `.development/`
- **Depends on**: `7.1.1`
- **Spec Prose**: Extend `TigerwebClient` in `src/fpac_soil_mcp/tigerweb_client.py` with county boundary querying:
  - Add method `get_intersecting_counties(geometry_input) -> list[dict]`: queries Census TIGERweb State and County Boundaries MapServer (`https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer/1` or configured Geography endpoint) with `inSR=4326`, `spatialRel=esriSpatialRelIntersects`, `outFields=GEOID,NAME,STATE,BASENAME`, and `returnGeometry=true`.
  - Parse returned county polygon features into Shapely geometries with State/County FIPS codes and county names.
  - Add utility `partition_geometry_by_counties(geometry, county_features) -> list[dict]`: spatially intersects the input corridor polygon with each county boundary polygon (`geom.intersection(county_geom)`), calculates segment acreage, and returns partitioned segment records with geometry, state FIPS, county FIPS, and county name.
- **Constraints / Do Not Touch**:
  - Retain existing `check_urban_exemption` behavior and Layer 0 screening.
- **Grep Anchors**:
  - `src/fpac_soil_mcp/tigerweb_client.py`: `class TigerwebClient`.
- **Acceptance & Targeted Test Command**:
  - `uv run pytest tests/test_tigerweb_client.py -q` passes with mocked county intersection tests.

#### Task 7.2.3: Multi-County Corridor Test Fixture Corpus
- **ID**: `7.2.3`
- **Repo**: `.`
- **Files in Scope**:
  - *Must create*: `tests/fixtures/corridor/multi_county_corridors.json`, `tests/test_corridor_fixtures.py`, `planning/tasks/7.2.3.todo.md`
  - *May edit for report only*: `planning/STATE_7.md`
  - *Temp/scratch*: `.development/`
- **Depends on**: `7.1.1`
- **Spec Prose**: Create a gold-set corpus of synthetic and real-world linear corridor test fixtures in `tests/fixtures/corridor/`:
  - Fixtures representing 2-county, 3-county, 5-county, and cross-state border utility and pipeline corridors.
  - Include centerline coordinates (LineString/MultiLineString), buffer widths (e.g., 50 ft, 100 ft, 0.25 miles), indirect staging polygon footprints, and alternative alignments (Alternatives B and C).
  - Include ground-truth benchmark segment acreages, expected county splits, and expected total project acreage.
  - Implement `tests/test_corridor_fixtures.py` verifying geometry validity, buffer calculations, and segment partition consistency.
- **Constraints / Do Not Touch**:
  - Do not modify existing `tests/fixtures/aoi/benchmark_50_aois.json`.
- **Grep Anchors**:
  - `tests/fixtures/aoi/benchmark_50_aois.json`.
  - `tests/test_aoi_fixtures.py`.
- **Acceptance & Targeted Test Command**:
  - `uv run pytest tests/test_corridor_fixtures.py -q` passes.

---

### Wave 3

#### Task 7.3.1: Multi-County Corridor Analysis & Reconciliation Engine
- **ID**: `7.3.1`
- **Repo**: `.`
- **Files in Scope**:
  - *Must create*: `src/fpac_soil_mcp/corridor_analysis.py`, `tests/test_corridor_analysis.py`, `planning/tasks/7.3.1.todo.md`
  - *Must edit*: `src/fpac_soil_mcp/models.py`
  - *May edit for report only*: `planning/STATE_7.md`
  - *Temp/scratch*: `.development/`
- **Depends on**: `7.2.1`, `7.2.2`, `7.2.3`
- **Spec Prose**: Implement `CorridorAnalyzer` in `src/fpac_soil_mcp/corridor_analysis.py` and response models in `models.py`:
  - Models: `CorridorCountySegment`, `CorridorFarmlandAnalysisResponse`, `CorridorImpactBreakdown`.
  - Process:
    1. Ingest centerline and buffer distance/units; generate direct conversion polygon.
    2. Ingest optional indirect impact areas; erase direct geometry from indirect areas to prevent double counting.
    3. Ingest optional alternative corridor centerlines/buffers (Alternatives B, C, D).
    4. Intersect project footprint with Census TIGERweb county boundaries to partition into discrete county segments ($S_1, \dots, S_k$).
    5. Query SDA spatial intersection per segment for SSURGO soil map units and farmland classification breakdowns.
    6. Query NASS QuickStats per county for agricultural baselines (or return unavailable record).
    7. Query TIGERweb Urban Areas for urban corridor segmentation.
    8. Calculate composite relative Land Evaluation ratings ($RR_{\text{composite}}$) and enforce mathematical sum reconciliation across all segment acreages (direct, indirect, prime, converted) within 0.1% tolerance.
- **Constraints / Do Not Touch**:
  - Do not break existing single-polygon `PolygonAnalyzer` or `analyze_farmland_by_polygon`.
- **Grep Anchors**:
  - `src/fpac_soil_mcp/polygon_analysis.py`: `class PolygonAnalyzer`.
  - `src/fpac_soil_mcp/models.py`: `class PolygonFarmlandAnalysisResponse`.
- **Acceptance & Targeted Test Command**:
  - `uv run pytest tests/test_corridor_analysis.py -q` passes with multi-county mocked scenarios and sum reconciliation checks.

---

### Wave 4

#### Task 7.4.1: 7 CFR § 658.5(c) Corridor Site Assessment Rules Engine
- **ID**: `7.4.1`
- **Repo**: `.`
- **Files in Scope**:
  - *Must create*: `src/fpac_soil_mcp/corridor_scoring.py`, `tests/test_corridor_scoring.py`, `planning/tasks/7.4.1.todo.md`
  - *May edit for report only*: `planning/STATE_7.md`
  - *Temp/scratch*: `.development/`
- **Depends on**: `7.3.1`
- **Spec Prose**: Implement the statutory CPA-106 Site Assessment rules engine in `src/fpac_soil_mcp/corridor_scoring.py`:
  - Implement 7 CFR § 658.5(c) scoring rules:
    - Criteria 1–4: Standard site assessment parameters.
    - Criteria 5 and 6: Statutory **zeroed out** (0 points) for corridor projects.
    - Criterion 7: Farm size comparison ratio against NASS county average farm size.
    - Criteria 8 and 11: Adjusted from 15 to **25 points maximum each** (maintaining the 160-point SA maximum).
    - Criteria 9, 10, 12: Standard corridor parameter bounds.
  - Calculate preliminary total LESA score (LE + SA = 260 max) and evaluate the 160-point mandatory alternatives threshold (§ 658.4(c)(2)).
  - Require explicit human justification rationale for subjective Part VI criteria without fabricating automated scores.
- **Constraints / Do Not Touch**:
  - Retain regulatory notices and human-authority boundaries.
- **Grep Anchors**:
  - `planning/MASTER_PLAN.md`: Phase 3 Deliverable 4 & Phase 4 Deliverables 3, 4, 5.
  - `planning/RESEARCH_PUBLIC_APIS_AND_INTERPRETATIONS.md`: Section 5 `7 CFR Part 658 LESA Scoring & Automation Rules`.
- **Acceptance & Targeted Test Command**:
  - `uv run pytest tests/test_corridor_scoring.py -q` passes with rule validation, point maximums, zeroed criteria, and threshold tests.

---

### Wave 5

#### Task 7.5.1: FastMCP Corridor Analysis Tools & Server Registration
- **ID**: `7.5.1`
- **Repo**: `.`
- **Files in Scope**:
  - *Must edit*: `src/fpac_soil_mcp/tools/soil_tools.py`, `src/fpac_soil_mcp/tools/__init__.py`, `tests/test_tools.py`
  - *Must create*: `planning/tasks/7.5.1.todo.md`
  - *May edit for report only*: `planning/STATE_7.md`
  - *Temp/scratch*: `.development/`
- **Depends on**: `7.4.1`
- **Spec Prose**: Expose and register the corridor screening tool on the FastMCP server:
  - Add `analyze_corridor_fppa` tool accepting `centerline` (GeoJSON / WKT), `buffer_distance` (float), `buffer_units` (str: `feet`, `meters`, `miles`), optional `indirect_geometry`, optional `alternative_centerlines`, and optional `site_assessment_inputs`.
  - Register `analyze_corridor_fppa` in `register_soil_tools` and export via `tools/__init__.py`.
  - Update `tests/test_tools.py` and `tests/test_server.py` to verify tool discovery, parameter schema validation, and tool invocation.
- **Constraints / Do Not Touch**:
  - Do not remove or alter existing tool names or signatures.
- **Grep Anchors**:
  - `src/fpac_soil_mcp/tools/soil_tools.py`: `def register_soil_tools`.
  - `src/fpac_soil_mcp/tools/__init__.py`: `__all__`.
- **Acceptance & Targeted Test Command**:
  - `uv run pytest tests/test_tools.py tests/test_server.py -q` passes.

---

### Wave 6

#### Task 7.6.1: Phase 3 Contract, End-to-End & Documentation Suite
- **ID**: `7.6.1`
- **Repo**: `.`
- **Files in Scope**:
  - *Must create*: `tests/test_phase3_contracts.py`, `planning/tasks/7.6.1.todo.md`
  - *Must edit*: `README.md`, `manifest.yaml`, `server.json`
  - *May edit for report only*: `planning/STATE_7.md`
  - *Temp/scratch*: `.development/`
- **Depends on**: `7.5.1`
- **Spec Prose**: Create comprehensive Phase 3 contract and end-to-end regression tests in `tests/test_phase3_contracts.py`. Verify:
  1. Multi-county corridors split cleanly across county boundaries without geographic gaps or overlaps.
  2. Direct, indirect, prime, and converted acreages reconcile to full project dimensions within 0.1% tolerance.
  3. 7 CFR § 658.5(c) corridor scoring rules are strictly applied.
  4. NASS baseline integration functions with live fallback.
  5. Update `README.md`, `manifest.yaml`, and `server.json` with the new tool description and capability specifications.
- **Constraints / Do Not Touch**:
  - Maintain all existing phase 1 and 2 contract tests.
- **Grep Anchors**:
  - `tests/test_phase1_contracts.py`, `tests/test_phase2_contracts.py`.
  - `manifest.yaml`, `server.json`, `README.md`.
- **Acceptance & Targeted Test Command**:
  - `uv run pytest tests/test_phase3_contracts.py -q` passes.
  - `uv run pytest -m "not live_sda"` passes with 100% green tests across all suites.
  - `uv run ruff check .` passes.
