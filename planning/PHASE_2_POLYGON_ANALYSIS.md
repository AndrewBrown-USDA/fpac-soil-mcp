# Phase 2: Polygon AOI Screening & Farmland Analysis

This document records the architectural deliverables, component designs, and operational contracts completed in Phase 2 for Area of Interest (AOI) polygon screening, spatial clipping, Census urban area screening, and soil interpretations.

---

## 1. Scope & Core Deliverables

Phase 2 expanded `fpac-soil-mcp` from point and `mukey` queries to full polygon geometry analysis, spatial intersections with USDA SDA, Census TIGERweb urban boundary overlays, and soil interpretation retrieval:

1. **Geometry Parsing & Geodesic Calculations (`src/fpac_soil_mcp/geometry.py`)**:
   - Ingests GeoJSON `Polygon`, `MultiPolygon`, `Feature`, and `FeatureCollection` structures.
   - Validates coordinates, vertex bounds, ring closure, and self-intersections.
   - Computes geodesic ellipsoidal surface acreage on WGS84 using equal-area projections (EPSG:6933 and local equal-area projections).
   - Generates deterministic SHA-256 geometry hashes for auditability and caching.

2. **Census TIGERweb Integration (`src/fpac_soil_mcp/tigerweb_client.py`)**:
   - Implements async and sync querying against the Census Bureau TIGERweb MapServer REST API (2020 Urban Areas, Layer 6).
   - Supports Point, Polygon, and MultiPolygon spatial intersections.
   - Identifies intersecting urban area names, GEOIDs, and population attributes for preliminary statutory exemption checks under 7 CFR § 658.2(a).

3. **Spatial SDA Queries & Server-Side Clipping (`src/fpac_soil_mcp/sda_client.py`)**:
   - Implements spatial intersection queries with server-side polygon clipping using SDA's geometry operators (`STIntersection` and `STArea`).
   - Retrieves exact clipped soil polygon geometries and calculated acreages.
   - Supports component-weighted soil interpretations via the SDA `sdvattribute` / `comp_interp` metadata catalog.

4. **Polygon Analysis Engine (`src/fpac_soil_mcp/polygon_analysis.py`)**:
   - Coordinates end-to-end evaluation pipelines: geometry validation, geodesic surface area calculation, Census urban area screening, and SDA spatial queries.
   - Groups intersecting map units and calculates exact acreage and percentage breakdowns across standard farmland categories:
     - Prime Farmland
     - Conditional Prime Farmland (e.g., if drained, if irrigated)
     - Farmland of Statewide Importance
     - Farmland of Local Importance / Unique Farmland
     - Not Prime Farmland
   - Evaluates survey coverage status (`covered`, `partially_covered`, `unmapped`).
   - Merges component-weighted NCCPI v3 crop productivity indices.
   - Produces structured JSON, CSV table exports, geometry provenance metadata, and mandatory 7 CFR Parts 657/658 regulatory notices.

5. **MCP Tool Suite (`src/fpac_soil_mcp/tools/soil_tools.py`)**:
   - `analyze_farmland_by_polygon`: Full preliminary FPPA screening for project polygons.
   - `get_soil_polygons_by_geometry`: SSURGO soil polygon geometries as GeoJSON `FeatureCollection` (with optional boundary clipping).
   - `check_urban_area_exemption`: Standalone Census 2020 Urban Area boundary screening.
   - `get_soil_interpretations`: Component-weighted interpretation lookup by map unit keys.

---

## 2. Verification & Exit Criteria

All Phase 2 exit criteria defined in `planning/MASTER_PLAN.md` have been met and verified:

- **Benchmark Fixture Corpus**: Validated against 50 reviewed AOI geometries (`tests/fixtures/aoi/benchmark_50_aois.json`) ensuring surface acreage calculation within 0.1% tolerance.
- **Contract & Integration Tests**: Comprehensive mocked test coverage across all tools, geometries, spatial clipping logic, and urban screening (`tests/test_phase2_contracts.py`, `tests/test_polygon_analysis.py`, `tests/test_geometry.py`, `tests/test_tigerweb_client.py`).
- **Live Integration Tests**: Opt-in live test suite verifying real-world SDA and Census TIGERweb network queries (`tests/test_live_sda.py`, `tests/test_live_tigerweb.py`).
- **Code Quality**: Clean formatting and linting across the codebase via `ruff`.

---

## 3. Relationship to Subsequent Phases

Phase 2 establishes the spatial and analytical foundation for subsequent roadmap phases:
- **Phase 3 (Multi-County Corridor Analysis / CPA-106)**: Builds on `geometry.py` and `tigerweb_client.py` to add linear corridor buffering, direct vs. indirect impact partitioning, and multi-county segment reconciliation.
- **Phase 4 (Preliminary LE & SA Workbench)**: Consumes Phase 2 map unit breakdowns, NCCPI interpretations, and acreage summaries to compute preliminary relative Land Evaluation (LE) ratings and Site Assessment (SA) criterion models.
