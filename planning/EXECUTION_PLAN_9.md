# EXECUTION PLAN 9: PR #4 Code Review Remediation (Geometry, LE Weighting, Fallback, & Config)

## Goal & Scope

Remediate all 9 unresolved review findings and comments identified in PR #4 code review:
1. **ESRI Ring Holes & MultiPolygons**: Correctly reconstruct Shapely geometries from ArcGIS REST polygon rings in `tigerweb_client.py` using hole and winding/containment semantics (distinguishing outer vs inner rings).
2. **Consistent Centerline Hashing**: Compute `direct_hash` from the validated input centerline (or LineString geometry) in `corridor_analysis.py`, ensuring changing buffer distance does not change the centerline identity hash.
3. **Indirect Geometry WKT Support**: Support WKT strings in addition to GeoJSON for `indirect_geometry_input` in `corridor_analysis.py` by checking prefix pattern and calling `validate_and_sanitize_polygon_wkt`.
4. **Transparent County Partitioning & Fallback Reporting**: When TIGERweb county lookup fails or returns empty partitions, avoid silent substitution; explicitly record `coverage_status` or fallback limitations and set partition reconciliation status without faking multi-county success.
5. **Acreage-Consistent LE Scoring**: Fix Land Evaluation ($RR$) scoring in `corridor_analysis.py` to aggregate LE products and weights consistently across mapped soil acreage and expose unmapped coverage properly without inflating corridor scores across unmapped acres.
6. **Partially Covered Segment Status**: Accurately assign `partially_covered` status to segments that contain both mapped soil map units and unmapped remainder acreage (aligning with `polygon_analysis.py`).
7. **Preserve Valid Zero LE Scores**: Distinguish a valid calculated LE score of 0.0 (e.g. 0 rating NCCPI soils) from `None` (missing/unrated soils) by checking `weight > 0` rather than `sum > 0`.
8. **Configured NASS Census Year and Enablement**: Pass `settings.nass_census_year` to `NassClient` queries in `corridor_analysis.py` and respect `settings.nass_enabled`.
9. **Update Tool Contract and Surface Tests**: Assert exact MCP tool inventories in `tests/test_phase2_contracts.py` (including `analyze_corridor_fppa`), and add comprehensive test coverage for all remediated items.

### In Scope
- `src/fpac_soil_mcp/tigerweb_client.py`
- `src/fpac_soil_mcp/corridor_analysis.py`
- `src/fpac_soil_mcp/nass_client.py`
- `tests/test_tigerweb_client.py`
- `tests/test_corridor_analysis.py`
- `tests/test_nass_client.py`
- `tests/test_phase2_contracts.py`
- `tests/test_phase3_contracts.py`

### Out of Scope
- Direct changes to USDA SDA SQL tabular query templates or server endpoints.
- Point query tool logic in `get_farmland_classification_by_point`.

---

## Decision Log

- **2026-09-18**: All 9 code review items from PR #4 will be resolved in Plan 9.
- **2026-09-18**: Centerline hash will be computed from the validated centerline geometry to uniquely identify the corridor route.
- **2026-09-18**: Land Evaluation scoring will use `segment_le_weight` and `total_le_weight` to prevent unmapped soil acreage from artificially inflating scores, and preserve valid 0.0 ratings when `le_weight > 0`.
- **2026-09-18**: Use 2 concurrent workers for independent tasks in Wave 2.

---

## Wave Table

| Wave | Task ID | Title | Files in Scope | Depends On |
| :--- | :--- | :--- | :--- | :--- |
| **Wave 1** | `9.1.1` | ArcGIS Rings Geometry Reconstruction & Tests | `src/fpac_soil_mcp/tigerweb_client.py`, `tests/test_tigerweb_client.py` | Baseline |
| **Wave 2** | `9.2.1` | NASS Client Config & Year Propagation | `src/fpac_soil_mcp/nass_client.py`, `tests/test_nass_client.py` | Baseline |
| **Wave 2** | `9.2.2` | Corridor Scoring, LE Basis, Hashing & WKT Support | `src/fpac_soil_mcp/corridor_analysis.py`, `tests/test_corridor_analysis.py` | `9.1.1` |
| **Wave 3** | `9.3.1` | Contract Verification & Tool Inventory Test Update | `tests/test_phase2_contracts.py`, `tests/test_phase3_contracts.py` | `9.2.1`, `9.2.2` |

---

## Task Specifications

### Task 9.1.1: ArcGIS Rings Geometry Reconstruction & Tests
- **ID**: `9.1.1`
- **Repo**: `fpac-soil-mcp`
- **Files in Scope**: `src/fpac_soil_mcp/tigerweb_client.py`, `tests/test_tigerweb_client.py`
- **Depends on**: Baseline
- **Spec**:
  - In `tigerweb_client.py:get_intersecting_counties`, reconstruct Shapely `Polygon` and `MultiPolygon` geometries from ArcGIS JSON `rings` respecting outer/inner ring relationships:
    - Group CW exterior rings with their nested CCW interior hole rings (or use `LinearRing.is_ccw` / containment test) to construct proper Shapely `Polygon(exterior, holes)`.
    - Combine multiple exterior polygons into a `MultiPolygon`.
  - Update `tests/test_tigerweb_client.py` with test cases verifying multi-ring counties with holes are parsed correctly without losing hole semantics.
- **Anchors**: `src/fpac_soil_mcp/tigerweb_client.py:270-330`
- **Acceptance**: `uv run pytest tests/test_tigerweb_client.py -q`

---

### Task 9.2.1: NASS Client Config & Year Propagation
- **ID**: `9.2.1`
- **Repo**: `fpac-soil-mcp`
- **Files in Scope**: `src/fpac_soil_mcp/nass_client.py`, `tests/test_nass_client.py`
- **Depends on**: Baseline
- **Spec**:
  - In `nass_client.py`:
    - Default `census_year` parameter in `get_county_ag_profile` to `settings.nass_census_year` when not explicitly supplied.
    - If `settings.nass_enabled` is `False` or `api_key` is blank, return `CountyAgProfile` with status `UNAVAILABLE` and informative error message.
  - Update `tests/test_nass_client.py` to test configured census year propagation and disabled setting behavior.
- **Anchors**: `src/fpac_soil_mcp/nass_client.py:40-90`
- **Acceptance**: `uv run pytest tests/test_nass_client.py -q`

---

### Task 9.2.2: Corridor Scoring, LE Basis, Hashing & WKT Support
- **ID**: `9.2.2`
- **Repo**: `fpac-soil-mcp`
- **Files in Scope**: `src/fpac_soil_mcp/corridor_analysis.py`, `tests/test_corridor_analysis.py`
- **Depends on**: `9.1.1`
- **Spec**:
  - In `corridor_analysis.py`:
    - Compute `geometry_hash` from the direct centerline input (using `validate_and_sanitize_line_wkt` / parsed line geometry) rather than the buffered polygon.
    - Parse `indirect_geometry_input` supporting WKT strings (`validate_and_sanitize_polygon_wkt`) as well as GeoJSON strings/dicts.
    - In county fallback (when TIGERweb returns no counties or partition fails), append an explicit notice/limitation explaining fallback occurred and mark status clearly.
    - In LE scoring, compute segment relative rating as `segment_le_sum / segment_le_weight` when `segment_le_weight > 0`. Aggregate across corridor as `total_le_sum / total_le_weight` to maintain a consistent mapped-acreage basis.
    - Preserve valid 0.0 LE scores by checking `weighted_le_weight > 0` or tracking presence rather than `weighted_le_sum > 0` (for both primary and alternatives).
    - Set `coverage_status` to `"partially_covered"` if `unit_models` is non-empty and `unmapped_rem > 0`.
    - Pass `census_year=settings.nass_census_year` to `self.nass_client.get_county_ag_profile`.
  - Update `tests/test_corridor_analysis.py` with test coverage for WKT indirect geometries, centerline hash invariance with buffer changes, 0.0 LE scores, and partial coverage status.
- **Anchors**: `src/fpac_soil_mcp/corridor_analysis.py:80-180`, `src/fpac_soil_mcp/corridor_analysis.py:360-420`, `src/fpac_soil_mcp/corridor_analysis.py:580-620`
- **Acceptance**: `uv run pytest tests/test_corridor_analysis.py -q`

---

### Task 9.3.1: Contract Verification & Tool Inventory Test Update
- **ID**: `9.3.1`
- **Repo**: `fpac-soil-mcp`
- **Files in Scope**: `tests/test_phase2_contracts.py`, `tests/test_phase3_contracts.py`
- **Depends on**: `9.2.1`, `9.2.2`
- **Spec**:
  - In `tests/test_phase2_contracts.py:test_mcp_tool_registration_surface`, update the expected tool inventory list to include `analyze_corridor_fppa` and assert exact tool surface match (9 tools).
  - In `tests/test_phase3_contracts.py`, add assertions for WKT indirect geometry parsing, centerline hashing, and partial-coverage status in end-to-end corridor screening.
  - Run the complete offline test suite and Ruff lint/formatting.
- **Anchors**: `tests/test_phase2_contracts.py:150-180`, `tests/test_phase3_contracts.py:1-580`
- **Acceptance**: `uv run pytest -m "not live_sda" -q && uv run ruff check . && uv run ruff format --check .`
