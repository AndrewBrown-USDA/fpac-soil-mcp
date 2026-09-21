# STATE 9: PR #4 Code Review Remediation

## Green Baseline Checklist

- [x] Orchestrations 1 through 8 complete.
- [x] Code review completed for PR #4 with 9 action items identified.
- [x] Initial worktree status recorded: clean baseline.
- [x] Baseline test suite verified: `uv run pytest -m "not live_sda" -q` -> `154 passed, 10 deselected`.
- [x] Baseline lint verified: `uv run ruff check .` -> clean.
- [x] Baseline formatting verified: `uv run ruff format --check .` -> clean.

## Wave Board

| Task ID | Wave | Title | Status | Worker | Assigned At | Completed At |
| --- | --- | --- | --- | --- | --- | --- |
| `9.1.1` | 1 | ArcGIS Rings Geometry Reconstruction & Tests | complete | Subagent 9.1.1 | 2026-09-21T08:14:41 | 2026-09-21T08:19:00 |
| `9.2.1` | 2 | NASS Client Config & Year Propagation | complete | Subagent 9.2.1 | 2026-09-21T08:16:21 | 2026-09-21T08:22:00 |
| `9.2.2` | 2 | Corridor Scoring, LE Basis, Hashing & WKT Support | complete | Subagent 9.2.2 | 2026-09-21T08:24:00 | 2026-09-21T08:28:00 |
| `9.3.1` | 3 | Contract Verification & Tool Inventory Test Update | pending | - | - | - |

## Wave Gates

- **Wave 1** depends on baseline. Task `9.1.1` runs solo.
- **Wave 2** depends on `9.1.1`. Tasks `9.2.1` and `9.2.2` touch disjoint files and can run in parallel.
- **Wave 3** depends on `9.2.1` and `9.2.2`. Task `9.3.1` runs solo.
- At every wave boundary, run serially:
  - `uv run pytest -m "not live_sda"`
  - `uv run ruff check .`
  - `uv run ruff format --check .`

---

## Task Reports

### 9.1.1
- **Status**: complete
- **Changes**:
  - Implemented `_esri_rings_to_geometry` in `src/fpac_soil_mcp/tigerweb_client.py` separating CW exterior rings from CCW interior hole rings and grouping nested holes by containment, with containment-based fallback for non-standard winding.
  - Refactored `get_intersecting_counties` to call `_esri_rings_to_geometry` instead of creating independent solid polygons per ring.
  - Added unit tests in `tests/test_tigerweb_client.py` covering single rings, single holes, multipart geometries with holes, non-standard winding fallbacks, malformed rings, and county responses with donut holes.
- **Verification**: `uv run pytest tests/test_tigerweb_client.py -q` passed (14 passed). Full suite `uv run pytest -m "not live_sda" -q` (160 passed) + `ruff check` + `ruff format --check` clean.

### 9.2.1
- **Status**: complete
- **Changes**:
  - Updated `NassClient.get_county_ag_profile` to accept `census_year: int | None = None` and resolve to `settings.nass_census_year` when omitted.
  - Added early check in `NassClient.get_county_ag_profile` for `settings.nass_enabled is False` or empty/blank `api_key`, returning `CountyAgProfile` with status `IntegrationStatus.UNAVAILABLE` and an informative message.
  - Added tests in `tests/test_nass_client.py` covering disabled settings, missing API key, default census year propagation from configuration, and verified all provenance metadata.
- **Verification**: `uv run pytest tests/test_nass_client.py -q` passed (6 passed). Full suite `uv run pytest -m "not live_sda" -q` (162 passed) + `ruff check .` + `ruff format --check .` clean.

### 9.2.2
- **Status**: complete
- **Changes**:
  - In `src/fpac_soil_mcp/corridor_analysis.py`:
    - Computed `geometry_hash` from the direct centerline geometry (`validate_and_sanitize_line_wkt` or `parse_geojson_geometry(allow_line=True)`) rather than the buffered footprint, making centerline hash invariant to buffer distance changes (for both main corridor and alternatives).
    - Enabled `indirect_geometry_input` to parse WKT strings (`validate_and_sanitize_polygon_wkt` + `shapely_wkt.loads`) in addition to GeoJSON and Polygon objects.
    - Added explicit limitation reporting when county intersection or partitioning fallbacks occur without masking failures.
    - Updated segment and composite LE scoring to use area-weighted mapped acreage basis (`segment_le_sum / segment_le_weight` and `total_le_sum / total_le_weight`), preserving valid 0.0 ratings by checking `weight > 0`.
    - Set `coverage_status` to `"partially_covered"` if `unit_models` is non-empty and `unmapped_rem > 0`.
    - Passed `census_year=settings.nass_census_year` to `self.nass_client.get_county_ag_profile`.
  - In `tests/test_corridor_analysis.py`:
    - Added test cases covering centerline hash buffer invariance, indirect WKT geometry parsing, 0.0 LE rating preservation, partial coverage status, and updated mock signatures for `census_year`.
- **Verification**: `uv run pytest tests/test_corridor_analysis.py -q` passed (9 passed). Full suite `uv run pytest -m "not live_sda" -q` (166 passed) + `uv run ruff check .` + `uv run ruff format --check .` clean.

