# EXECUTION PLAN 5: Exact SSURGO Spatial Clipping, Live Integration & Manifest Alignment

## Goal & Scope

### Goal
Implement exact server-side SSURGO spatial polygon clipping (`STIntersection` with geodesic acreage calculation) matching `soilDB::SDA_spatialQuery` patterns, expose a dedicated soil polygon geometry retrieval tool (`get_soil_polygons_by_geometry`), support live SSURGO interpretation rule catalog verification with arbitrary rule queries, add opt-in live service integration tests (`@pytest.mark.live_sda`), and complete execution manifest and registry synchronization across `server.json`, `manifest.yaml`, and documentation.

### In Scope
1. **Server-Side Spatial Clipping & Geometry Extraction**:
   - Update `sda_client.py` with parameterized T-SQL spatial intersection templates (`WITH geom_data ... STIntersection ... MakeValid().STArea() * 0.000247105 AS area_ac`) supporting both clipped acreage calculation and optional geometry extraction.
   - Implement `get_spatial_intersection(wkt, clip=True, geom_acres=True, return_geom=False)` in `SDAClient`.
2. **Dedicated Soil Geometry Retrieval Tool**:
   - Expose `get_soil_polygons_by_geometry` tool in `src/fpac_soil_mcp/tools/soil_tools.py` returning GeoJSON FeatureCollection with clipped or overlapping SSURGO map unit geometries and attributes.
3. **Exact Soil Interpretation Rule Catalog & Arbitrary Rule Support**:
   - Fix default NCCPI rule to `'NCCPI - National Commodity Crop Productivity Index (Ver 3.0)'` in `sda_client.py`, `config.py`, and `polygon_analysis.py`.
   - Implement live/cached rule verification against SDA `cointerp` (`SELECT DISTINCT mrulename FROM cointerp WHERE ruledepth = 0`) to allow arbitrary valid SSURGO interpretations safely.
4. **Polygon Screening Engine Integration & Manifests**:
   - Update `polygon_analysis.py` to aggregate exact server-side clipped acreages instead of equal-share estimates.
   - Embed full execution metadata/manifest in `PolygonFarmlandAnalysisResponse`.
5. **Live Integration Test Suite**:
   - Create dedicated live test files `tests/test_live_sda.py` and `tests/test_live_tigerweb.py` marked with `@pytest.mark.live_sda`.
6. **Registry & Metadata Synchronization**:
   - Sync `server.json`, `manifest.yaml`, and `README.md` with all registered MCP tools.

### Out of Scope
- Linear corridor segmentation and multi-county partitioning (Phase 3).
- Full Land Evaluation & Site Assessment (LE-SA) scoring workbench (Phase 4).
- Draft AD-1006 / CPA-106 form population and alternatives comparison (Phase 5).
- SQLite audit persistence and CPA-2 annual summary generation (Phase 6).

### Verbatim Constraints
- "Preserve the preliminary-screening limitation in every soil-query response: this service does not produce an official FPPA determination, LESA score, Form AD-1006, or NRCS-CPA-106."
- "Accept only validated coordinates or numeric positive mukey values. Do not add user-supplied SQL passthrough."
- "We need to actually fetch the overlapping polygons (using a spatial query; as supported in R/python SDA implementations) not just the ratings for overlapping mukeys."
- "The live service test would have caught issues like the incorrect rule name."
- "I like using NCCPI as a default, but otherwise want to support arbitrary strict full names for any soil interpretation."
- "Dedicated live test files."

---

## Decision Log

- **2026-09-17**: Use server-side SDA spatial intersection with `STIntersection` and `STArea() * 0.000247105 AS area_ac` pattern-matched from `soilDB::SDA_spatialQuery`.
- **2026-09-17**: Expose both exact tabular screening via `analyze_farmland_by_polygon` and dedicated spatial geometry retrieval via `get_soil_polygons_by_geometry`.
- **2026-09-17**: Default to `'NCCPI - National Commodity Crop Productivity Index (Ver 3.0)'` for general productivity, while supporting arbitrary interpretation rule queries validated against SDA's `cointerp.mrulename` catalog.
- **2026-09-17**: Place live service tests in dedicated files (`tests/test_live_sda.py` and `tests/test_live_tigerweb.py`) marked with `@pytest.mark.live_sda`.
- **2026-09-17**: Synchronize `server.json`, `manifest.yaml`, and `README.md` to reflect all registered tools and response schemas.
- **2026-09-17**: Resolve PR #1 code review findings across WKT parsing safety, partial coverage reporting, TIGERweb interior rings & point support, live test assertions, and contract completeness via Waves 5 and 6.

---

## Hazard Notes from Reconnaissance

- **Spatial T-SQL in SDA**: Spatial methods like `.STIntersection` and `.STIntersects` require valid geometry in EPSG 4326. MultiPolygon WKTs must have consistent counter-clockwise orientation for outer rings; SDA T-SQL handles geometry conversion via `geometry::STGeomFromText('{wkt}', 4326)`.
- **GeomAcres calculation**: Geography conversion `GEOGRAPHY::STGeomFromWKB(geom.STUnion(geom.STStartPoint()).STAsBinary(), 4326).MakeValid().STArea()` safely avoids planar distortion in geographic coordinates.
- **Mock Transport Fixtures**: Existing unit tests in `tests/test_sda_client.py` and `tests/test_polygon_analysis.py` need updated mock payloads reflecting the new column structure (`mukey`, `musym`, `muname`, `farmlndcl`, `areasymbol`, `area_ac`, optional `geom`).

---

## Wave Dependency Table

```
Wave 1 (Client & Configuration)
  ├── 5.1.1: SDA Spatial Intersection & Rule Catalog Engine (sda_client.py, config.py)

Wave 2 (Orchestration & Tools)
  ├── 5.2.1: Polygon Analysis Spatial Aggregation & Manifests (polygon_analysis.py, models.py)
  ├── 5.2.2: Geometry Tool Registration & MCP Interface (tools/soil_tools.py, tools/__init__.py)

Wave 3 (Testing & Live Integration)
  ├── 5.3.1: Unit Test Suite & Mock Updates (tests/test_sda_client.py, tests/test_polygon_analysis.py)
  ├── 5.3.2: Dedicated Live Integration Suite (tests/test_live_sda.py, tests/test_live_tigerweb.py)

Wave 4 (Metadata & Registry Synchronization)
  ├── 5.4.1: Registry, Manifest & Documentation Sync (server.json, manifest.yaml, README.md)

Wave 5 (PR Review Hardening & Abstractions)
  ├── 5.5.1: WKT Parsing Hardening & Query Template Dispatch (sda_client.py, geometry.py)
  ├── 5.5.2: TIGERweb Interior Rings & Point Support (tigerweb_client.py)
  ├── 5.5.3: Coverage Status & Default Rule Alignment (polygon_analysis.py, tools/soil_tools.py)

Wave 6 (PR Review Test Hardening & Contract Sync)
  ├── 5.6.1: Contract Verification & Live Test Hardening (tests/test_live_tigerweb.py, tests/test_phase2_contracts.py, tests/test_sda_client.py)
  ├── 5.6.2: Documentation Example Synchronization (README.md)
```

| Task ID | Wave | Title | Files in Scope | Depends On |
| --- | --- | --- | --- | --- |
| `5.1.1` | 1 | SDA Spatial Intersection & Rule Catalog Engine | `src/fpac_soil_mcp/sda_client.py`, `src/fpac_soil_mcp/config.py` | None |
| `5.2.1` | 2 | Polygon Analysis Spatial Aggregation & Manifests | `src/fpac_soil_mcp/polygon_analysis.py`, `src/fpac_soil_mcp/models.py` | `5.1.1` |
| `5.2.2` | 2 | Geometry Tool Registration & MCP Interface | `src/fpac_soil_mcp/tools/soil_tools.py`, `src/fpac_soil_mcp/tools/__init__.py` | `5.1.1` |
| `5.3.1` | 3 | Unit Test Suite & Mock Updates | `tests/test_sda_client.py`, `tests/test_polygon_analysis.py`, `tests/test_phase2_contracts.py` | `5.2.1`, `5.2.2` |
| `5.3.2` | 3 | Dedicated Live Integration Suite | `tests/test_live_sda.py`, `tests/test_live_tigerweb.py` | `5.2.1`, `5.2.2` |
| `5.4.1` | 4 | Registry, Manifest & Documentation Sync | `server.json`, `manifest.yaml`, `README.md` | `5.3.1`, `5.3.2` |
| `5.5.1` | 5 | WKT Parsing Hardening & Query Template Dispatch | `src/fpac_soil_mcp/sda_client.py`, `src/fpac_soil_mcp/geometry.py` | `5.4.1` |
| `5.5.2` | 5 | TIGERweb Interior Rings & Point Support | `src/fpac_soil_mcp/tigerweb_client.py` | `5.4.1` |
| `5.5.3` | 5 | Coverage Status & Default Rule Alignment | `src/fpac_soil_mcp/polygon_analysis.py`, `src/fpac_soil_mcp/tools/soil_tools.py` | `5.4.1` |
| `5.6.1` | 6 | Contract Verification & Live Test Hardening | `tests/test_live_tigerweb.py`, `tests/test_phase2_contracts.py`, `tests/test_sda_client.py` | `5.5.1`, `5.5.2`, `5.5.3` |
| `5.6.2` | 6 | Documentation Example Synchronization | `README.md` | `5.5.1`, `5.5.2`, `5.5.3` |

---

## Task Specifications

### Task 5.1.1: SDA Spatial Intersection & Rule Catalog Engine
- **Files in scope**: `src/fpac_soil_mcp/sda_client.py`, `src/fpac_soil_mcp/config.py`
- **Depends on**: None
- **Spec**:
  1. In `sda_client.py`, define `SQL_SPATIAL_INTERSECTION` query template utilizing `WITH geom_data AS (...)` with `mupolygongeo.STIntersection(geometry::STGeomFromText('{wkt}', 4326))` and `GEOGRAPHY::STGeomFromWKB(geom.STUnion(geom.STStartPoint()).STAsBinary(), 4326).MakeValid().STArea() * 0.000247105 AS area_ac`.
  2. Implement `get_spatial_intersection(wkt: str, clip: bool = True, geom_acres: bool = True, return_geom: bool = False) -> list[dict[str, Any]]` in `SDAClient`.
  3. Implement `get_available_interpretation_rules(refresh: bool = False) -> list[str]` in `SDAClient` with an in-memory cache querying `SELECT DISTINCT mrulename FROM cointerp WHERE ruledepth = 0 ORDER BY mrulename`.
  4. In `get_interpretations`, validate `rule_name` against the rule catalog (falling back to strict safe-character checking if catalog check is offline/bypassed) and update default rule name to `'NCCPI - National Commodity Crop Productivity Index (Ver 3.0)'`.
  5. In `config.py`, update `sda_interpretation_rules_allowed` with official SSURGO `mrulename` strings.
- **Constraints**: Do not allow unvalidated string concatenation in SQL queries. Always validate WKT prefix.
- **Grep Anchors**: `SQL_SPATIAL_INTERSECTION`, `get_spatial_intersection`, `get_available_interpretation_rules`.
- **Acceptance Command**: `uv run pytest tests/test_sda_client.py -q -m "not live_sda"`

### Task 5.2.1: Polygon Analysis Spatial Aggregation & Manifests
- **Files in scope**: `src/fpac_soil_mcp/polygon_analysis.py`, `src/fpac_soil_mcp/models.py`
- **Depends on**: `5.1.1`
- **Spec**:
  1. In `polygon_analysis.py`, call `sda_client.get_spatial_intersection(wkt_str, clip=True, geom_acres=True, return_geom=False)`.
  2. Group returned pieces by `mukey`, summing `area_ac` as `calculated_acres`. Compute `percentage_of_aoi` as `(calculated_acres / total_acres) * 100.0`.
  3. Update NCCPI interpretation query call to use `'NCCPI - National Commodity Crop Productivity Index (Ver 3.0)'`.
  4. In `models.py`, add `manifest: dict[str, Any] = Field(default_factory=dict)` to `PolygonFarmlandAnalysisResponse` to encapsulate execution metadata, geometry hash, runtime parameters, and summary statistics.
- **Constraints**: Maintain accurate acreage totals. If clipped pieces sum to slightly less than total AOI due to boundary slivers or unmapped water/areas, record remainder in unmapped category.
- **Grep Anchors**: `get_spatial_intersection`, `categorize_farmland_class`, `PolygonFarmlandAnalysisResponse`.
- **Acceptance Command**: `uv run pytest tests/test_polygon_analysis.py -q -m "not live_sda"`

### Task 5.2.2: Geometry Tool Registration & MCP Interface
- **Files in scope**: `src/fpac_soil_mcp/tools/soil_tools.py`, `src/fpac_soil_mcp/tools/__init__.py`
- **Depends on**: `5.1.1`
- **Spec**:
  1. In `src/fpac_soil_mcp/tools/soil_tools.py`, implement and register `get_soil_polygons_by_geometry` tool taking `geojson_input: dict[str, Any] | str`, `clip: bool = True`, `buffer_meters: float = 0.0`.
  2. Parse and validate input geometry via `geometry.py`.
  3. Call `sda_client.get_spatial_intersection(wkt_str, clip=clip, geom_acres=True, return_geom=True)`.
  4. Convert returned WKT geometries into a GeoJSON `FeatureCollection` dictionary containing map unit attributes (`mukey`, `musym`, `muname`, `farmlndcl`, `areasymbol`, `area_ac`) and GeoJSON geometry.
  5. Export the new tool in `src/fpac_soil_mcp/tools/__init__.py`.
- **Constraints**: Ensure geometry errors return graceful structured responses with regulatory notices.
- **Grep Anchors**: `get_soil_polygons_by_geometry`, `register_tools`.
- **Acceptance Command**: `uv run pytest tests/test_phase2_contracts.py -q`

### Task 5.3.1: Unit Test Suite & Mock Updates
- **Files in scope**: `tests/test_sda_client.py`, `tests/test_polygon_analysis.py`, `tests/test_phase2_contracts.py`
- **Depends on**: `5.2.1`, `5.2.2`
- **Spec**:
  1. Update mocked SDA responses in `test_sda_client.py` and `test_polygon_analysis.py` to include `area_ac` columns for spatial intersection tests.
  2. Add unit tests for `get_spatial_intersection`, `get_available_interpretation_rules`, and `get_soil_polygons_by_geometry`.
  3. Verify exact acreage aggregation and percentage calculations in `test_polygon_analysis.py`.
  4. Ensure all 105+ unit tests pass cleanly offline.
- **Constraints**: Default test suite must remain completely offline with no real HTTP calls.
- **Grep Anchors**: `test_get_spatial_intersection`, `test_get_soil_polygons_by_geometry`.
- **Acceptance Command**: `uv run pytest -m "not live_sda" -q`

### Task 5.3.2: Dedicated Live Integration Suite
- **Files in scope**: `tests/test_live_sda.py`, `tests/test_live_tigerweb.py`
- **Depends on**: `5.2.1`, `5.2.2`
- **Spec**:
  1. Create `tests/test_live_sda.py` with `@pytest.mark.live_sda`:
     - Test live point lookup for known prime farmland coordinate (e.g. Story County, Iowa).
     - Test live spatial intersection with exact clipping for a known polygon AOI, verifying returned `mukey`, `muname`, and `area_ac`.
     - Test live interpretation query with `'NCCPI - National Commodity Crop Productivity Index (Ver 3.0)'`.
     - Test live catalog query for `cointerp` rule names.
     - Test live geometry retrieval via `get_spatial_intersection(..., return_geom=True)`.
  2. Create `tests/test_live_tigerweb.py` with `@pytest.mark.live_sda`:
     - Test live TIGERweb urban area query for an urban coordinate/polygon (e.g. Indianapolis, IN) verifying urban area detection.
     - Test live TIGERweb query for a rural coordinate/polygon verifying non-urban result.
- **Constraints**: Mark all tests with `@pytest.mark.live_sda`. Add graceful network exception skipping if USDA/Census endpoints are temporarily unreachable.
- **Grep Anchors**: `pytestmark = pytest.mark.live_sda`, `test_live_spatial_intersection_clipping`.
- **Acceptance Command**: `uv run pytest tests/test_live_sda.py tests/test_live_tigerweb.py -m live_sda -q`

### Task 5.4.1: Registry, Manifest & Documentation Sync
- **Files in scope**: `server.json`, `manifest.yaml`, `README.md`
- **Depends on**: `5.3.1`, `5.3.2`
- **Spec**:
  1. Update `manifest.yaml` to document all registered tools: `analyze_farmland_by_polygon`, `get_soil_polygons_by_geometry`, `check_urban_area_exemption`, `get_soil_interpretations`, and point/mukey tools.
  2. Update `server.json` to reflect current tool definitions and capabilities.
  3. Update `README.md` with descriptions and usage examples for the new spatial clipping and geometry retrieval tools.
- **Constraints**: Preserve all regulatory notices, citations, and disclaimer text.
- **Grep Anchors**: `get_soil_polygons_by_geometry`, `analyze_farmland_by_polygon`.
- **Acceptance Command**: `uv run ruff check .`

### Task 5.5.1: WKT Parsing Hardening & Query Template Dispatch
- **Files in scope**: `src/fpac_soil_mcp/sda_client.py`, `src/fpac_soil_mcp/geometry.py`
- **Depends on**: `5.4.1`
- **Spec**:
  1. In `geometry.py`, create reusable `validate_and_sanitize_polygon_wkt(wkt: str) -> str` that parses the input with Shapely (`shapely.wkt.loads`), validates that it is a non-empty `Polygon` or `MultiPolygon` within valid WGS84 coordinate bounds, and returns normalized `geom.wkt`.
  2. In `sda_client.py`, replace prefix/substring checking in `get_by_polygon` and `get_spatial_intersection` with `validate_and_sanitize_polygon_wkt`.
  3. In `sda_client.py`, update spatial intersection SQL templates and method logic to respect `geom_acres`. When `geom_acres=False`, omit the `GEOGRAPHY::...STArea()` computation and select `NULL AS area_ac` (or omit the column) to avoid expensive area calculations as advertised in the docstring.
- **Constraints**: Reject malformed WKT strings or WKT containing injection attempts before SQL interpolation.
- **Grep Anchors**: `validate_and_sanitize_polygon_wkt`, `geom_acres`, `SQL_SPATIAL_INTERSECTION_CLIPPED`.
- **Acceptance Command**: `uv run pytest tests/test_sda_client.py -q -m "not live_sda"`

### Task 5.5.2: TIGERweb Interior Rings & Point Support
- **Files in scope**: `src/fpac_soil_mcp/tigerweb_client.py`
- **Depends on**: `5.4.1`
- **Spec**:
  1. In `tigerweb_client.py`, update ESRI polygon formatting to include both exterior and all interior rings (`[list(p.exterior.coords)] + [list(ring.coords) for ring in p.interiors]`) for both `Polygon` and `MultiPolygon` objects.
  2. Support GeoJSON `Point` inputs: parse `Point` geometries (or coordinates) and format as ESRI `geometryType: "esriGeometryPoint"` (`{"x": lon, "y": lat}`) when querying TIGERweb.
- **Constraints**: Ensure polygon holes inside urban boundaries are not queried as filled solids.
- **Grep Anchors**: `esriGeometryPoint`, `interiors`, `check_urban_exemption`.
- **Acceptance Command**: `uv run pytest tests/test_tigerweb_client.py -q`

### Task 5.5.3: Coverage Status & Default Rule Alignment
- **Files in scope**: `src/fpac_soil_mcp/polygon_analysis.py`, `src/fpac_soil_mcp/tools/soil_tools.py`
- **Depends on**: `5.4.1`
- **Spec**:
  1. In `polygon_analysis.py`, update `coverage_status` evaluation: if `unit_models` is empty, set `"unmapped"`; if `unmapped_remainder > 0.0` (with mapped units present), set `"partially_covered"`; otherwise set `"covered"`.
  2. In `tools/soil_tools.py`, update `get_soil_interpretations` default `rule_name` to `'NCCPI - National Commodity Crop Productivity Index (Ver 3.0)'`.
  3. In `tools/soil_tools.py`, update docstrings across all tools for consistency with actual contracts (including Point support in urban screening).
- **Constraints**: Do not break existing response schema contracts.
- **Grep Anchors**: `partially_covered`, `NCCPI - National Commodity Crop Productivity Index (Ver 3.0)`.
- **Acceptance Command**: `uv run pytest tests/test_polygon_analysis.py tests/test_tools.py -q -m "not live_sda"`

### Task 5.6.1: Contract Verification & Live Test Hardening
- **Files in scope**: `tests/test_live_tigerweb.py`, `tests/test_phase2_contracts.py`, `tests/test_sda_client.py`
- **Depends on**: `5.5.1`, `5.5.2`, `5.5.3`
- **Spec**:
  1. In `tests/test_live_tigerweb.py`, check `res.status == IntegrationStatus.ERROR` or catch network failures and call `pytest.skip` before asserting success.
  2. In `tests/test_live_tigerweb.py`, replace tautological rural check with `assert res.is_urban_intersected is False` and `assert len(res.urban_area_names) == 0`.
  3. In `tests/test_phase2_contracts.py`, expand `test_mcp_tool_registration_surface` to assert all expected tool names (`get_farmland_classification_by_point`, `get_farmland_classification_by_mukey`, `analyze_farmland_by_polygon`, `get_soil_polygons_by_geometry`, `check_urban_area_exemption`, `get_soil_interpretations`, `explain_fppa_screening_scope`, `list_farmland_classes`) and their registered callables.
  4. In `tests/test_sda_client.py`, add unit test verifying WKT injection strings are rejected by `validate_and_sanitize_polygon_wkt` and `geom_acres=False` selects the lightweight template.
- **Constraints**: Keep default test suite completely offline.
- **Grep Anchors**: `test_mcp_tool_registration_surface`, `test_live_urban_area_screening_rural`.
- **Acceptance Command**: `uv run pytest -m "not live_sda" -q`

### Task 5.6.2: Documentation Example Synchronization
- **Files in scope**: `README.md`
- **Depends on**: `5.5.1`, `5.5.2`, `5.5.3`
- **Spec**:
  1. In `README.md`, update `get_soil_interpretations` example and parameter documentation to use `'NCCPI - National Commodity Crop Productivity Index (Ver 3.0)'`.
  2. Document `partially_covered` status and Point geometry support for `check_urban_area_exemption`.
- **Constraints**: Preserve all regulatory notices and citations.
- **Grep Anchors**: `NCCPI - National Commodity Crop Productivity Index (Ver 3.0)`.
- **Acceptance Command**: `uv run ruff check .`
