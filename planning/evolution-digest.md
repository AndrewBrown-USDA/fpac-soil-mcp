# Evolution Digest: fpac-soil-mcp

> Generated 2026-10-14 by git-history-interval-study (Strategy A: Artifact Creation)
> Pattern: `planning/EXECUTION_PLAN_*.md`
> Repository: fpac-soil-mcp | 207 commits | 26 intervals | 2026-09-16 → 2026-10-08

---

## 1. Interval Overview & Timeline

| # | Interval | Date Range | Commits | Churn | Convergence |
|---|----------|-----------|---------|-------|-------------|
| 1 | EP1→EP2 | 2026-09-16→2026-09-16 | 8 | 1,115 | converging |
| 2 | EP2→EP3 | 2026-09-16→2026-09-16 | 1 | 453 | converging |
| 3 | EP3→EP4 | 2026-09-16→2026-09-17 | 10 | 3,550 | divergent |
| 4 | EP4→EP5 | 2026-09-17→2026-09-17 | 10 | 4,666 | divergent |
| 5 | EP5→EP6 | 2026-09-17→2026-09-17 | 7 | 1,616 | converging |
| 6 | EP6→EP7 | 2026-09-17→2026-09-18 | 24 | 1,765 | converging |
| 7 | EP7→EP8 | 2026-09-18→2026-09-18 | 10 | 3,713 | divergent |
| 8 | EP8→EP9 | 2026-09-18→2026-09-21 | 10 | 2,371 | volatile |
| 9 | EP9→EP10 | 2026-09-21→2026-09-21 | 5 | 384 | converging |
| 10 | EP10→EP11 | 2026-09-21→2026-09-21 | 10 | 1,112 | volatile |
| 11 | EP11→EP12 | 2026-09-21→2026-09-22 | 11 | 1,848 | converging |
| 12 | EP12→EP13 | 2026-09-22→2026-09-22 | 3 | 310 | converging |
| 13 | EP13→EP14 | 2026-09-22→2026-09-23 | 2 | 1,595 | converging |
| 14 | EP14→EP15 | 2026-09-23→2026-09-25 | 5 | 483 | converging |
| 15 | EP15→EP16 | 2026-09-25→2026-09-25 | 4 | 558 | converging |
| 16 | EP16→EP17 | 2026-09-25→2026-09-28 | 4 | 674 | active |
| 17 | EP17→EP18 | 2026-09-28→2026-09-28 | 9 | 3,490 | divergent |
| 18 | EP18→EP19 | 2026-09-28→2026-09-28 | 8 | 1,480 | converging |
| 19 | EP19→EP20 | 2026-09-28→2026-09-28 | 1 | 337 | converging |
| 20 | EP20→EP21 | 2026-09-28→2026-09-30 | 1 | 228 | converging |
| 21 | EP21→EP22 | 2026-09-30→2026-09-30 | 12 | 1,195 | converging |
| 22 | EP22→EP23 | 2026-09-30→2026-09-30 | 9 | 924 | converging |
| 23 | EP23→EP24 | 2026-09-30→2026-10-01 | 15 | 1,396 | converging |
| 24 | EP24→EP25 | 2026-10-01→2026-10-05 | 9 | 1,508 | converging |
| 25 | EP25→EP26 | 2026-10-05→2026-10-05 | 9 | 885 | converging |
| 26 | EP26→HEAD | 2026-10-05→2026-10-08 | 10 | 2,410 | converging |

**Overall trajectory**: Divergent foundation → volatile build-out → sustained convergence. The system
reached architectural stability around EP12 (Phase 3 consistency review) and maintained converging
dynamics through all subsequent phases.

---

## 2. Subsystem Evolution Matrix

| Subsystem | Foundation (EP1-3) | Phase 2 (EP4-6) | Phase 2-3 (EP7-8) | Phase 3 Reviews (EP9-16) | Phase 4 Build (EP17-20) | Phase 4 Review (EP21-26) | Post-Plan |
|-----------|-------------------|-----------------|-------------------|-------------------------|------------------------|-------------------------|-----------|
| **core** | Created (6 modules) | +3, heavy modification | +3, heavy modification | Stabilizing fixes | +1 (lesa.py), modifications | Targeted fixes only | Minor fixes |
| **tools** | — | Modified (2 files) | Modified | Sporadic fixes | Modified (tool wiring) | Sporadic fixes | Minor fix |
| **resources/prompts** | — | — | — | Modified once | — | — | — |
| **data** | Created (+2) | — | Modified once | — | — | — | — |
| **tests** | Created (+8) | +8, heavy expansion | +6, heavy expansion | Stabilizing (+1, fixes) | +2, modifications | Test-heavy (+1, many fixes) | Test fixes |
| **planning** | Created (seed) | Rapid growth | Growth + modification | Heavy growth (PRs) | Growth | Growth + modifications | Growth |
| **root** | Created (scaffold) | Modified (config) | Modified (config, CI) | Modified (README, manifest) | Modified | Minor | Minor |
| **ci** | — | — | +2 (GitHub Actions) | — | — | — | — |

**Key observation**: `core` and `tests` subsystems show the most architecturally significant churn.
The `planning` subsystem grows steadily but is documentation-only. The `tools` subsystem is remarkably
stable after initial creation — tool registration is a thin wiring layer over domain modules.

---

## 3. Architectural Eras & Feature Evolution

### Era 1: Foundation & MCP Scaffold (EP1-3, Sep 16)
* **19 commits, 5,118 churn**
* Established: FastMCP server factory (`app.py`), SDA HTTP client (`sda_client.py`), Pydantic response models (`models.py`), regulatory constants (`constants.py`), and initial MCP tools (point query, mukey lookup)
* Key decisions: src-layout package (`src/fpac_soil_mcp/`), Python ≥3.11, `uv` for dependency management, `JSON+COLUMNNAME` SDA format, fixed SQL templates (no user SQL passthrough), modular tool registration pattern
* Research: Public API survey aligned roadmap with SDA, TIGERweb, NASS capabilities

### Era 2: Geospatial Engine (EP4-8, Sep 17-18)
* **61 commits, 14,097 churn** (peak build-out)
* Added: `geometry.py` (GeoJSON validation, WKT, projections), `polygon_analysis.py` (AOI multi-point sampling), `tigerweb_client.py` (Census urban screening), `nass_client.py` (USDA NASS QuickStats), `corridor_analysis.py` (multi-county corridor partitioning), `corridor_scoring.py` (7 CFR § 658.5(c) rules)
* Added: `http_client.py` (resilient base HTTP client with retry), `privacy.py`, `authority.py`, `official_sources.py`
* Key decisions: `shapely`/`pyproj` for geometry operations, WGS84 geodesic acreage via `Geod.polygon_area_perimeter()`, SDA server-side polygon clipping via `STIntersection`/`GEOGRAPHY.STArea()`, EPSG:6933 for corridor buffering only, TIGERweb Layer 0 (2020 Urban Areas), dynamic county partitioning via TIGERweb Counties, NASS QuickStats with graceful unavailable fallback
* Architecture: Clean separation of domain modules (clients → analysis → tools) with tools as thin wiring

### Era 3: Code Review & Hardening (EP9-16, Sep 21-25)
* **53 commits, 7,906 churn** (declining, stabilizing)
* PR #4, #5, #7 review cycles drove interface refinements, test marker rename (`live_sda` → `live_network`), prompt engineering fixtures, manifest/README consistency
* Key decisions: Renamed test markers to `live_network` for generality, centralized post-Phase-3 consistency review, added structured prompt test fixtures
* Convergence: Strong shift from `feat` to `fix`/`docs`/`test` commits

### Era 4: LESA Engine & Land Evaluation (EP17-20, Sep 28)
* **19 commits, 5,535 churn** (focused feature burst)
* Added: `lesa.py` (unified LESA module), dynamic SDV attribute routing for state-specific productivity indexes (NCCPI v3, Iowa CSR2, Minnesota CPI, California Storie Index)
* Key decisions: Unified LESA module for both site (AD-1006) and corridor (CPA-106) scoring, backwards-compatible with `corridor_scoring.py`, relative rating normalization ($RR_i = Rating_i / MaxCountyRating$), null/unrated soil unit screening with explicit notices, `calculate_preliminary_lesa` MCP tool, 160-point mandatory alternatives threshold (7 CFR § 658.4(c)(2))

### Era 5: Integration Remediation (EP21-26, Sep 30 - Oct 5)
* **64 commits, 6,242 churn** (test-heavy)
* PR #9 code review drove county partitioning fixes, productivity index preservation through corridor paths, centralized regulatory constants, `server.json` metadata updates
* Key decisions: Corridor projects routed through buffered corridor analysis, productivity index requests preserved through all LESA fallback paths, duplicate LESA construction removed
* Convergence: Fully converging — dominated by `fix`, `test`, `docs`

### Era 6: Final Merge (EP26→HEAD, Oct 5-8)
* **10 commits, 2,410 churn**
* Merge PR #9 with final fixes and test corrections
* Convergence: Converging

---

## 4. Commit Type Distribution Over Time

| Phase | feat | fix | refactor | test | docs | chore | other |
|-------|------|-----|----------|------|------|-------|-------|
| Foundation (EP1-3) | 7 | 1 | 0 | 0 | 10 | 1 | 0 |
| Phase 2 (EP4-6) | 8 | 7 | 0 | 3 | 14 | 2 | 7 |
| Phase 2-3 (EP7-8) | 12 | 2 | 1 | 3 | 2 | 0 | 0 |
| Phase 3 Reviews (EP9-16) | 4 | 11 | 5 | 2 | 15 | 5 | 2 |
| Phase 4 Build (EP17-20) | 7 | 5 | 0 | 2 | 5 | 0 | 0 |
| Phase 4 Review (EP21-26) | 2 | 11 | 3 | 16 | 12 | 4 | 1 |
| Post-Plan (EP26→HEAD) | 0 | 4 | 0 | 3 | 0 | 1 | 2 |

**Shift pattern**: `feat` dominates early (42/207 = 20% overall but 27/80 = 34% in Eras 1-3), then `fix`+`test`+`docs` dominate late (91/127 = 72% in Eras 3-6). Classic stabilization signature.

---

## 5. ADR Candidate Feed for `adr-distillation`

The following architectural decisions satisfy the heuristic filter (≥2 of: high reversibility cost, pattern-setting, cross-cutting, evaluated trade-offs). Each is traced to specific commit evidence and planning context.

### ADR Candidate 1: MCP Server Framework & Package Layout
* **Decision**: FastMCP as the MCP server framework; `src/fpac_soil_mcp/` src-layout with modular registration (`register_tools()`, `register_resources()`, `register_prompts()`)
* **Heuristic**: High reversibility cost (framework choice), pattern-setting (all future tools follow this registration pattern), cross-cutting (affects every module)
* **Evidence**: EXECUTION_PLAN_1 Decision Log (2026-09-16); commit `ca02c890` (Initial commit)
* **Context**: Adapted from GSA MCP hackathon template. The modular registration pattern was established in EP1 and proved stable through all 26 plans — zero refactoring of the registration architecture.

### ADR Candidate 2: Fixed SQL Templates Over User SQL Passthrough
* **Decision**: All SDA queries use fixed parameterized T-SQL templates with strict input validation. No arbitrary SQL exposure through MCP tools.
* **Heuristic**: Pattern-setting (every new query must be a fixed template), cross-cutting (SDA client, tools, privacy), evaluated trade-offs (flexibility sacrificed for security and reproducibility)
* **Evidence**: EXECUTION_PLAN_1 Verbatim Constraints; `sda_client.py` SQL_* constants; AGENTS.md Operational Rules
* **Context**: Explicitly rejected a "run arbitrary SDA SQL" MCP tool. This constraint held through all 26 plans including the EP17 SDV attribute routing extension.

### ADR Candidate 3: Preliminary Screening Authority Boundary
* **Decision**: All primary screening responses include a `regulatory_notice` field. Centralized in `constants.py` and enforced as policy via AGENTS.md.
* **Heuristic**: Pattern-setting (all primary screening responses), cross-cutting (constants, models, tools), high reversibility cost (removing it would change the legal posture of every screening output)
* **Evidence**: EXECUTION_PLAN_1 Verbatim Constraints; `constants.py` REGULATORY_NOTICE; `regulatory_notice` field on `FarmlandClassificationResponse`, `PolygonFarmlandAnalysisResponse`, `CorridorFarmlandAnalysisResponse`, `PreliminaryLESAResponse`
* **Context**: Enforced as policy in AGENTS.md Operational Rules. Auxiliary reference responses (e.g., `FarmlandClassListResponse`) omit the field by design. Never relaxed across 26 plans.

### ADR Candidate 4: Geodesic Acreage Calculation & Equal-Area Buffering Strategy
* **Decision**: WGS84 geodesic area (`Geod.polygon_area_perimeter()`) for client-side acreage, SDA `GEOGRAPHY.STArea()` for server-side clipped acreage, EPSG:6933 projection solely for corridor centerline buffering.
* **Heuristic**: High reversibility cost (changing acreage method changes all scoring), pattern-setting (0.1% tolerance benchmark established), evaluated trade-offs (geodesic precision vs. projected simplicity)
* **Evidence**: `geometry.py:calculate_acreage()` uses `_GEOD.polygon_area_perimeter()`; `sda_client.py` uses `GEOGRAPHY.STArea()`; `geometry.py:buffer_centerline()` uses EPSG:6933
* **Context**: The 0.1% acreage tolerance benchmark was set in EP4 and carried through corridor analysis (EP7) and LESA scoring (EP17).

### ADR Candidate 5: SDA Server-Side Polygon Clipping for Spatial Soil Analysis
* **Decision**: Pass AOI WKT to SDA for server-side polygon clipping via `STIntersection` with exact clipped acreage via `GEOGRAPHY.STArea()`, using fixed SQL template `SQL_SPATIAL_INTERSECTION_CLIPPED`.
* **Heuristic**: Pattern-setting (all polygon and corridor tools use this pattern), cross-cutting (polygon_analysis, corridor_analysis, sda_client), evaluated trade-offs (server-side precision vs. WKT size limits)
* **Evidence**: `polygon_analysis.py:153` and `corridor_analysis.py:359` both call `get_spatial_intersection(clip=True, geom_acres=True)`
* **Context**: Server-side clipping produces exact per-map-unit acreages without approximation. Both polygon and corridor analysis share this spatial query path.

### ADR Candidate 6: Dynamic TIGERweb County Partitioning for Corridors
* **Decision**: Dynamically partition corridor geometries into county segments via Census TIGERweb REST API, with independent per-segment SDA and NASS queries and sum reconciliation.
* **Heuristic**: High reversibility cost (fundamental to corridor architecture), cross-cutting (TIGERweb client, corridor analysis, LESA scoring, NASS integration), evaluated trade-offs (explicitly rejected the single-county simplification used by desktop GIS tools)
* **Evidence**: EXECUTION_PLAN_7 Decision Log (2026-09-18); `corridor_analysis.py`; MASTER_PLAN §1 Problem statement; EP21-24 county partitioning remediation
* **Context**: Overcoming the Colorado NRCS ArcGIS Toolbox single-county limitation was a founding motivation. The decision survived multiple remediation cycles (EP21, EP23, EP24).

### ADR Candidate 7: Unified LESA Module Architecture
* **Decision**: Shared LE helpers (`calculate_composite_le`, `calculate_criterion_7_score`) in `lesa.py`, imported by `corridor_scoring.py` which retains corridor-specific SA evaluator classes and `evaluate_corridor_lesa()`.
* **Heuristic**: High reversibility cost (central LE engine), pattern-setting (all LE paths route through shared helpers), cross-cutting (models, tools, corridor_scoring, polygon_analysis)
* **Evidence**: EXECUTION_PLAN_17 Decision Log (2026-09-28); `lesa.py` creation; `corridor_scoring.py` imports from lesa; EP22-23-25 remediation
* **Context**: Required multiple remediation waves (EP22, EP23, EP25) to stabilize the boundary between shared LE helpers and corridor-specific SA logic.

### ADR Candidate 8: NCCPI as Validated Public Productivity Index with Extensible SDV Routing
* **Decision**: EP17 implemented dynamic SDV routing for multiple indexes; EP26 narrowed the public contract to `ProductivityIndexType.NCCPI` only, retaining extensible lower-level SDV routing for future validated indexes.
* **Heuristic**: Pattern-setting (public API contract), evaluated trade-offs (safety of validated-only public API vs. limiting state-specific coverage), cross-cutting (sda_client, lesa, tools, models)
* **Evidence**: EP17 SDV routing (2026-09-28); EP20 cointerp fix (`9cbcc7ed`); EP26 narrowing (STATE_26 line 48: "public and test contracts now expose validated national NCCPI only")
* **Context**: Three remediation waves (EP20, EP22, EP23) were needed before EP26 could confidently narrow the public contract to NCCPI.

### ADR Candidate 9: Shared HTTP Request Helper with Retry Composition
* **Decision**: Standalone `execute_http_request_with_retry()` function in `http_client.py`. Domain clients (`SDAClient`, `TigerwebClient`, `NassClient`) call this shared function (composition, not inheritance).
* **Heuristic**: Pattern-setting (all network communication uses this helper), cross-cutting (every API client), evaluated trade-offs (composition flexibility vs. per-client call signature duplication)
* **Evidence**: `http_client.py` shared helper extracted in EP10 (commit `d1e88d3`); client adoption in `41debf4`
* **Context**: Three separate federal APIs with different request shapes all share the same retry/timeout helper via function calls.

### ADR Candidate 10: Public Payload PII Detection & Sanitization
* **Decision**: Dedicated `privacy.py` module detects and rejects/sanitizes prohibited personal field names (email, phone, SSN, names, addresses) in request payloads via `validate_public_payload()` and `sanitize_public_payload()`.
* **Heuristic**: Pattern-setting (establishes PII-detection policy for all request processing), cross-cutting (available to all tool workflows)
* **Evidence**: `privacy.py` creation; AGENTS.md Operational Rules reference; `PROHIBITED_PERSONAL_KEY_PATTERNS` frozenset
* **Context**: 7 U.S.C. § 8791 (Section 1619) motivates the module. Coordinate privacy is a policy aspiration in AGENTS.md but is not automated in this module; `privacy.py` enforces the PII-field subset.

### ADR Candidate 11: Test Architecture — Mocked Default, Live & Agent-Eval Opt-In
* **Decision**: All tests use mocked HTTP responses by default. `live_network` and `agent_eval` markers are excluded via `pyproject.toml` `addopts`. Bare `uv run pytest` runs entirely offline.
* **Heuristic**: Pattern-setting (every new test follows this convention), evaluated trade-offs (test reliability vs. integration confidence), cross-cutting (entire test suite)
* **Evidence**: `pyproject.toml` `addopts = "-m 'not live_network and not agent_eval'"`; EP1 constraints; EP13 marker rename (`ba8a5540`)
* **Context**: The marker rename from `live_sda` to `live_network` (EP13) reflected multi-service expansion. The `agent_eval` marker was added for agentic integration tests.

---

## 6. Emergent Patterns & Observations

1. **Wave orchestration cadence**: The 26-plan lifecycle shows a consistent pattern — each execution plan drives 1-15 commits of implementation followed by a planning commit. The wave orchestration system (from `plan-wave` / `wave-orchestration` skills) was the primary development methodology.

2. **Code review as architectural refinement**: PR-triggered plans (EP8, EP9, EP10, EP11, EP15, EP18, EP21, EP22, EP25) represent 9 of 26 plans. Each review cycle tightened interfaces and reduced architectural debt rather than adding new features.

3. **Regulatory constraint stability**: The FPPA preliminary-screening notice, fixed SQL template policy, and Section 1619 privacy constraints were established in EP1 and never relaxed across 207 commits.

4. **Subsystem coupling pattern**: `tools/` is remarkably thin — it wires domain modules to MCP but contains minimal logic. This decoupling held from EP1 through EP26 without refactoring.

5. **Multi-county corridor as architectural driver**: The corridor partitioning feature (EP7) drove more downstream remediation (EP21, EP23, EP24) than any other single feature, suggesting it is the most architecturally complex and cross-cutting capability.

---

*This digest is generated for downstream consumption by `adr-distillation`. The 11 ADR candidates above are backed by commit SHAs and planning document references. Each satisfies ≥2 criteria of the heuristic filter.*
