# Orchestration 27 — Metadata-Driven Rating & Property Query Engine (Phase 4 Part 2)

## Goal & Scope

Implement the Metadata-Driven Rating & Property Query Engine from Phase 4 item 2 of the Master Plan. This orchestration extracts the SDV routing infrastructure into a dedicated module, researches actual SDA storage patterns for three state-specific productivity indexes, then implements and validates each index sequentially (CSR2, CPI, Storie) with offline benchmark fixtures and live_network SDA contract tests.

**In scope:**
1. SDV Discovery & Table Expansion — extract `sdv_query.py` from `sda_client.py`, expand `ALLOWED_SDV_TABLES` to include `chorizon` and `cocropyld`, harden dynamic query builders for non-`cointerp` table paths.
2. State Index Validation — implement and validate CSR2 (Iowa), CPI (Minnesota), and Storie Index (California) through the full stack: `ProductivityIndexType` enum, SDV routing, SDA client methods, domain wiring (polygon, corridor, tools, LESA), offline benchmark fixtures, unit tests, and live_network SDA contract tests.

**Out of scope (deferred to a later orchestration):**
- Regional Scoring Configuration Engine (populating `regional_scoring.v1.json` with state-to-index mappings and auto-selection logic).
- County Maximum Override Pathways beyond the existing `max_county_rating_override` parameter.
- Criterion 2 (perimeter agricultural adjacency ratio).
- NASS QuickStats baseline integration improvements.

**Verbatim constraints from the user:**
- "Support generalized Soil Data Viewer (`sdvattribute`) dynamic query routing across USDA SDA source tables (`cointerp`, `component`, `chorizon`, `cocropyld`) based on `sdvattribute.attributetablename` and `sdvattribute.attributecolumnname`."
- "Support standard national rating schedules (NCCPI v3) and state-specific productivity indexes: Iowa CSR2, Minnesota CPI, California Revised Storie Index."
- "State-approved local LE schedules with user-supplied or SDA-retrieved county maximum rating overrides (`max_county_rating_override`)."

## Decision Log

| Date | Decision | Rationale |
| --- | --- | --- |
| 2026-10-14 | ADR 0008 will be amended in-place to reflect the expanded validated multi-index contract. | User chose amendment over supersession; the ADR's decision drivers remain valid but the outcome expands from NCCPI-only to include CSR2, CPI, Storie as each is validated. |
| 2026-10-14 | State indexes validated sequentially: CSR2 first, then CPI, then Storie. Each must fully pass (including live_network tests) before the next begins. | Earlier batch attempt (EPs 17-23) failed when all three were implemented together; each index requires its own SDA pattern discovery and per-state benchmark fixtures. |
| 2026-10-14 | Validation uses both offline benchmark fixtures (unit tests) and live_network tests (SDA contract validation). | Matches the existing NCCPI pattern in `tests/fixtures/le_benchmarks.json` and `tests/test_live_sda.py`. |
| 2026-10-14 | SDV routing engine extracted to a dedicated `sdv_query.py` module. | The routing logic has grown beyond what `sda_client.py` should hold; a dedicated module clarifies the metadata-driven routing contract. |
| 2026-10-14 | Branch: `feat/phase-4-part-2-sdv-routing` (branched from `origin/main`). | Tracks Phase 4 Part 2 work separately from the merged Part 1. |
| 2026-10-14 | Research all three SDA storage patterns in one discovery wave before any implementation. | The user wants to understand all three index patterns before touching code, avoiding the trial-and-error that plagued EPs 20-23. |

## Reconnaissance Notes

### Key files and sizes
| File | Lines | Role |
| --- | --- | --- |
| `src/fpac_soil_mcp/sda_client.py` | 1020 | SDA HTTP client + SDV routing (to be extracted) |
| `src/fpac_soil_mcp/lesa.py` | 809 | LE/SA scoring engine |
| `src/fpac_soil_mcp/models.py` | 554 | Pydantic models, `ProductivityIndexType` enum (line 318) |
| `src/fpac_soil_mcp/polygon_analysis.py` | 485 | Polygon AOI analysis, NCCPI-only guard at line 110 |
| `src/fpac_soil_mcp/tools/soil_tools.py` | 704 | MCP tool implementations, NCCPI-only guards at lines 203, 404, 526 |
| `src/fpac_soil_mcp/corridor_analysis.py` | 862 | Corridor analysis, NCCPI-only guard at line 156 |
| `tests/test_sda_client.py` | 724 | SDA client unit tests, imports from `sda_client` at line 8 |
| `tests/test_lesa.py` | 549 | LESA scoring tests |
| `tests/test_live_sda.py` | 131 | Live SDA contract tests, `pytestmark = pytest.mark.live_network` |
| `tests/test_polygon_analysis.py` | 398 | Polygon analysis tests, unsupported-index parametrize at line 229 |
| `tests/fixtures/le_benchmarks.json` | 116 | Offline LE benchmark fixtures (currently NCCPI only) |

### Architecture constraints (from ADRs)
- **ADR 0008**: NCCPI is the validated public contract; lower-level SDV routing retained for extensibility. This plan exercises that extensibility path. ADR 0008 will be amended as each state index is validated.
- **ADR 0003**: Preliminary screening authority boundary — all outputs remain estimates, not official determinations.
- **ADR 0009** (HTTP resilience): SDA queries use retry logic from `http_client.py`; new query paths must inherit this.

### Existing SDV routing infrastructure (to be extracted)
- `ALLOWED_SDV_TABLES` — `sda_client.py:250` — currently `{cointerp, component, mapunit, sdvattribute}`. Missing: `chorizon`, `cocropyld`.
- `build_dynamic_sdv_query()` — `sda_client.py:266` — builds SQL from `sdvattribute` metadata. Handles `cointerp` (with `nasisrulename`) and `mapunit`/`component` (with `attributecolumnname`). Does NOT handle `chorizon` or `cocropyld`.
- `build_dynamic_sdv_county_max_query()` — `sda_client.py:381` — dynamic county max query. Same table coverage gap.
- `lookup_sdv_attribute()` — `sda_client.py:820` — searches `sdvattribute` by name/rule pattern.
- `SQL_SDV_ATTRIBUTE_LOOKUP` — `sda_client.py:190` — metadata lookup template.
- `SQL_INTERPRETATION_CATALOG` — `sda_client.py:113` — lists all `cointerp` rule names.
- `PRODUCTIVITY_PROVENANCE` — `sda_client.py:30` — `{"nccpi": "SDA:NCCPI_V3"}`. Needs entries for CSR2, CPI, Storie.

### NCCPI-only guards (to be removed/expanded per index)
- `polygon_analysis.py:110` — `if idx_enum is not ProductivityIndexType.NCCPI: raise ValueError`
- `tools/soil_tools.py:203` — same guard in `analyze_farmland_by_polygon`
- `tools/soil_tools.py:404` — same guard in `analyze_corridor_fppa`
- `tools/soil_tools.py:526` — same guard in `calculate_preliminary_lesa`
- `corridor_analysis.py:156` — same guard in `CorridorAnalyzer.analyze_corridor`
- `lesa.py:68` — `_normalize_productivity_index` only accepts NCCPI

### Import sites that must update when extracting to `sdv_query.py`
- `tests/test_sda_client.py:8` — imports `ALLOWED_SDV_TABLES`, `build_dynamic_sdv_query`, `build_dynamic_sdv_county_max_query` from `sda_client`
- `tests/test_sda_client.py:614,659,675,686` — inline imports of `build_dynamic_sdv_query` from `sda_client`
- `src/fpac_soil_mcp/sda_client.py` — must re-export extracted symbols for backward compatibility

### Test conventions
- Offline tests: `uv run pytest -m "not live_network"`
- Live tests: `uv run pytest tests/test_live_sda.py -m live_network`
- Lint: `uv run ruff check .` and `uv run ruff format --check .`
- Benchmark fixtures: `tests/fixtures/le_benchmarks.json` — JSON with `cases` array.
- Existing test at `test_polygon_analysis.py:229` parametrizes `['csr2', 'cpi', 'storie', 'custom']` to verify they are **rejected** — must be updated to expect acceptance instead.

## Wave Table

| Wave | Task | Title | Depends on | Key files |
| --- | --- | --- | --- | --- |
| 1 | 27.1.1 | Extract sdv_query.py module from sda_client.py | — | `sdv_query.py` (new), `sda_client.py`, `test_sda_client.py` |
| 1 | 27.1.2 | Research SDA storage patterns for CSR2, CPI, Storie | — | `planning/SDV_STATE_INDEX_RESEARCH.md` (new) |
| 2 | 27.2.1 | Expand ALLOWED_SDV_TABLES and harden query builders | 27.1.1, 27.1.2 | `sdv_query.py`, `test_sda_client.py` |
| 3 | 27.3.1 | CSR2: live query, routing, fixtures, unit tests, live test, ADR amendment | 27.2.1 | `models.py`, `sdv_query.py`, `sda_client.py`, `polygon_analysis.py`, `corridor_analysis.py`, `soil_tools.py`, `lesa.py`, `le_benchmarks.json`, `test_sda_client.py`, `test_lesa.py`, `test_polygon_analysis.py`, `test_live_sda.py`, `0008-*.md` |
| 4 | 27.4.1 | CPI: live query, routing, fixtures, unit tests, live test | 27.3.1 | same as 27.3.1 pattern (CPI) |
| 5 | 27.5.1 | Storie: live query, routing, fixtures, unit tests, live test, final ADR amendment | 27.4.1 | same as 27.3.1 pattern (Storie) |

**Rationale for merged live-first structure:** Each index implementation task starts with a live SDA query to retrieve actual rating values and county maxima for known mukeys. The offline benchmark fixtures are then constructed from this real data, ensuring they reflect realistic SDA response patterns. Unit tests run against the fixtures offline; a final live_network test confirms the SDA contract holds end-to-end. The live query informs fixture construction rather than serving as post-hoc validation only.

**Hazards:**
- `sda_client.py` is 1020 lines — workers must use grep anchors, never read the whole file.
- `test_sda_client.py` is 724 lines — same rule.
- `test_live_sda.py` live tests require network access; if a worker cannot reach SDA, it should STOP and report.
- The `test_unsupported_selector_rejected_before_sda` test at `test_polygon_analysis.py:229` will break when CSR2 is added — must be updated in the same task.
- `sda_client.py` must re-export extracted symbols so existing imports don't break during extraction.
- Each state index may store data differently (cointerp rule, component column, chorizon column, or cocropyld). Research wave 27.1.2 must confirm actual storage pattern before implementation.

---

## Task Specs

### Task 27.1.1 — Extract sdv_query.py module from sda_client.py

**Repo:** fpac-soil-mcp
**Files in scope:**
- Must edit: `src/fpac_soil_mcp/sda_client.py`, `tests/test_sda_client.py`
- Can create: `src/fpac_soil_mcp/sdv_query.py`
**Depends on:** none

**Spec:** Extract the SDV metadata-driven routing infrastructure from `sda_client.py` into a new `sdv_query.py` module. Move these symbols:
- `ALLOWED_SDV_TABLES` (sda_client.py:250)
- `validate_survey_area_symbol` (sda_client.py:258)
- `build_dynamic_sdv_query` (sda_client.py:266)
- `build_dynamic_sdv_county_max_query` (sda_client.py:381)
- `SQL_SDV_ATTRIBUTE_LOOKUP` (sda_client.py:190)
- `SQL_INTERPRETATION_CATALOG` (sda_client.py:113)
- `PRODUCTIVITY_PROVENANCE` (sda_client.py:30)

In `sda_client.py`, replace the extracted code with `from fpac_soil_mcp.sdv_query import ...` re-exports so existing import sites continue to work. Update `tests/test_sda_client.py` import block (line 8) to import from `fpac_soil_mcp.sdv_query`. Also update inline imports at lines 614, 659, 675, 686.

**Constraints:** Do NOT change any query logic, SQL templates, or validation behavior. This is a pure extraction/refactor. Do NOT touch any other source files.

**Grep anchors:**
- `ALLOWED_SDV_TABLES = {` at sda_client.py:250
- `def build_dynamic_sdv_query(` at sda_client.py:266
- `def build_dynamic_sdv_county_max_query(` at sda_client.py:381
- `SQL_SDV_ATTRIBUTE_LOOKUP = ` at sda_client.py:190
- `PRODUCTIVITY_PROVENANCE = {` at sda_client.py:30
- `from fpac_soil_mcp.sda_client import (` at test_sda_client.py:8

**Reference implementation:** The extraction pattern of `corridor_scoring.py` importing from `lesa.py` shows how this repo separates modules with re-exports.

**Acceptance:**
- `uv run pytest -m "not live_network"` — all existing tests pass with no import errors
- `uv run ruff check .` — no lint errors
- `uv run ruff format --check .` — no format issues
- Targeted: `uv run pytest tests/test_sda_client.py -m "not live_network"`

---

### Task 27.1.2 — Research SDA storage patterns for CSR2, CPI, Storie

**Repo:** fpac-soil-mcp
**Files in scope:**
- Can create: `planning/SDV_STATE_INDEX_RESEARCH.md`
**Depends on:** none

**Spec:** Query the live USDA SDA `sdvattribute` table to discover the actual storage pattern for each state-specific productivity index. For each index (CSR2, CPI, Storie), determine:
1. The `attributename` value(s) in `sdvattribute`
2. The `attributetablename` (which SSURGO table stores the ratings)
3. The `attributecolumnname` (which column holds the rating value)
4. The `nasisrulename` (if the table is `cointerp`, what rule name)
5. The `attributelogicaldatatype`
6. The sentinel/null values that indicate unrated soils
7. The expected rating value range (e.g., CSR2 is 0-100, NCCPI is 0-1)
8. Known reference values from Iowa, Minnesota, and California soil survey areas

Use `SDAClient.lookup_sdv_attribute()` with search patterns like `'CSR'`, `'suitability'`, `'productivity'`, `'Storie'`, `'crop productivity'`. Also query `SDAClient.get_interpretation_catalog()` to check if CSR2/CPI/Storie appear as `cointerp` rule names.

Document all findings in `planning/SDV_STATE_INDEX_RESEARCH.md` as a structured reference for downstream implementation tasks. Include exact `sdvattribute` metadata records for each index.

**Constraints:** This is research only — do NOT modify any source code or test files. Do NOT create or modify any Python modules.

**Grep anchors:**
- `def lookup_sdv_attribute` at sda_client.py:820
- `SQL_SDV_ATTRIBUTE_LOOKUP` at sda_client.py:190
- `SQL_INTERPRETATION_CATALOG` at sda_client.py:113

**Reference implementation:** `planning/RESEARCH_PUBLIC_APIS_AND_INTERPRETATIONS.md` section 4.2 documents the NCCPI cointerp pattern — follow this format.

**Acceptance:**
- `planning/SDV_STATE_INDEX_RESEARCH.md` exists with, for each of CSR2, CPI, and Storie: the `sdvattribute` metadata record, storage table, rating column or rule name, sentinel values, and at least one known reference value with soil survey area symbol.
- Targeted: `uv run pytest tests/test_live_sda.py -m live_network` (existing live tests pass — confirms SDA connectivity)

---

### Task 27.2.1 — Expand ALLOWED_SDV_TABLES and harden query builders

**Repo:** fpac-soil-mcp
**Files in scope:**
- Must edit: `src/fpac_soil_mcp/sdv_query.py`, `tests/test_sda_client.py`
**Depends on:** 27.1.1, 27.1.2

**Spec:** Expand `ALLOWED_SDV_TABLES` in `sdv_query.py` to include `chorizon` and `cocropyld`. Add query builder branches in `build_dynamic_sdv_query` and `build_dynamic_sdv_county_max_query` for these new table types.

For `chorizon`: join through `component` to `mapunit` (same as `component` path but with additional `chorizon` join on `cokey`). Apply sentinel filtering and component-weighted aggregation.

For `cocropyld`: this table stores crop yield data keyed by `cokey` with `cropname` and `yldunits` columns. Filter by `cropname` if `sdvattribute` metadata specifies it. Apply component-weighted aggregation.

Update `tests/test_sda_client.py` to add unit tests for new table types: verify `chorizon` and `cocropyld` are in `ALLOWED_SDV_TABLES`, verify `build_dynamic_sdv_query` generates valid SQL for each, verify injection prevention.

**Constraints:** Do NOT change existing `cointerp`, `component`, or `mapunit` query paths. Do NOT add `ProductivityIndexType` enum values. Do NOT touch `sda_client.py` SDAClient methods.

**Grep anchors:**
- `ALLOWED_SDV_TABLES = {` at sdv_query.py
- `def build_dynamic_sdv_query(` at sdv_query.py
- `if table == "mapunit":` at sdv_query.py (insert chorizon/cocropyld branches here)
- `test_dynamic_sdv_table_allowlist_excludes_unsupported_tables` at test_sda_client.py:123

**Reference implementation:** The existing `component` table branch in `build_dynamic_sdv_query` (the default return) shows the component-weighted aggregation pattern. The `chorizon` branch should add `INNER JOIN chorizon AS ch ON ch.cokey = c.cokey` and use `CAST(ch.{col} AS float)`.

**Acceptance:**
- `uv run pytest tests/test_sda_client.py -m "not live_network"` — all tests pass
- `uv run ruff check .` and `uv run ruff format --check .` — clean

---

### Task 27.3.1 — CSR2 implementation: routing, enum, wiring, fixtures, unit tests, ADR amendment

**Repo:** fpac-soil-mcp
**Files in scope:**
- Must edit: `src/fpac_soil_mcp/models.py`, `src/fpac_soil_mcp/sdv_query.py`, `src/fpac_soil_mcp/sda_client.py`, `src/fpac_soil_mcp/polygon_analysis.py`, `src/fpac_soil_mcp/corridor_analysis.py`, `src/fpac_soil_mcp/tools/soil_tools.py`, `src/fpac_soil_mcp/lesa.py`, `tests/fixtures/le_benchmarks.json`, `tests/test_sda_client.py`, `tests/test_lesa.py`, `tests/test_polygon_analysis.py`, `docs/decisions/0008-nccpi-validated-public-index-with-extensible-sdv-routing.md`
**Depends on:** 27.2.1

**Spec:** Implement Iowa CSR2 (Corn Suitability Rating 2) as a validated public productivity index. Start with a live SDA query to obtain real data, then build offline fixtures from it, then implement the full stack.

1. **Live query first:** Query live SDA for CSR2 ratings using known Iowa mukeys (from research in 27.1.2). Use `SDAClient.lookup_sdv_attribute()` + `build_dynamic_sdv_query()` to retrieve actual component-weighted ratings. Also query county max for an Iowa soil survey area (e.g., IA169). Document the actual values returned.
2. Add `CSR2 = "CSR2"` to `ProductivityIndexType` enum (`models.py:318`).
3. Add CSR2 provenance entry to `PRODUCTIVITY_PROVENANCE` in `sdv_query.py`.
4. Add CSR2 SQL template(s) or metadata-driven routing in `sdv_query.py` — if CSR2 uses a `cointerp` rule, add a fixed SQL template mirroring `SQL_PRODUCTIVITY_NCCPI`. If it uses a `component`/`chorizon` column, wire the dynamic builder.
5. Update `sda_client.py` `get_productivity_ratings` (line ~896) to accept `index_type="csr2"`.
6. Update `sda_client.py` `get_county_max_productivity_rating` (line ~844) to accept `index_type="csr2"`.
7. Update `lesa.py` `_normalize_productivity_index` (line ~68) to accept `csr2`.
8. Remove or expand NCCPI-only guards in `polygon_analysis.py:110`, `corridor_analysis.py:156`, and `tools/soil_tools.py` at lines 203, 404, 526 to accept CSR2.
9. **Build fixtures from live data:** Add CSR2 benchmark fixture(s) to `tests/fixtures/le_benchmarks.json` using the actual Iowa ratings and county max values obtained in step 1.
10. Add CSR2 unit tests: `test_sda_client.py` (query builder/routing), `test_lesa.py` (LE scoring), `test_polygon_analysis.py` (update parametrize at line 229 to accept `csr2`).
11. Amend ADR 0008 to document CSR2 as a validated public index.
12. **Live test confirmation:** Add a live_network test to `test_live_sda.py` for CSR2 and run it to confirm the SDA contract holds end-to-end.

**Constraints:** Do NOT break NCCPI routing. Do NOT add CPI or Storie support. CSR2 rating values are on a 0-100 scale (different from NCCPI's 0-1 scale) — county max normalization must handle this. The worker must have network access for steps 1 and 12; if SDA is unreachable, STOP and report.

**Acceptance:**
- `uv run pytest -m "not live_network"` — all offline tests pass (including new CSR2 unit tests built from live data)
- `uv run pytest tests/test_live_sda.py -m live_network` — live CSR2 test passes
- `uv run ruff check .` and `uv run ruff format --check .` — clean
- Targeted: `uv run pytest tests/test_sda_client.py tests/test_lesa.py tests/test_polygon_analysis.py -m "not live_network"`

**Grep anchors:**
- `class ProductivityIndexType` at models.py:318
- `PRODUCTIVITY_PROVENANCE = {` at sdv_query.py
- `def get_productivity_ratings(` at sda_client.py:896
- `def get_county_max_productivity_rating(` at sda_client.py:844
- `def _normalize_productivity_index(` at lesa.py:68
- `if idx_enum is not ProductivityIndexType.NCCPI:` at polygon_analysis.py:110
- `if normalized_index is not ProductivityIndexType.NCCPI:` at corridor_analysis.py:156
- `if normalized_productivity_index is not ProductivityIndexType.NCCPI:` at tools/soil_tools.py:203, 404, 526
- `@pytest.mark.parametrize("index", ["csr2", "cpi", "storie", "custom"])` at test_polygon_analysis.py:229
- `"cases":` at le_benchmarks.json

**Reference implementation:** The NCCPI implementation in `sda_client.py` (`SQL_PRODUCTIVITY_NCCPI` at line ~204) and the NCCPI benchmark case in `le_benchmarks.json` (`US_NCCPI_MIXED_RATED_UNRATED`).

**Acceptance:**
- `uv run pytest -m "not live_network"` — all tests pass
- `uv run ruff check .` and `uv run ruff format --check .` — clean
- Targeted: `uv run pytest tests/test_sda_client.py tests/test_lesa.py tests/test_polygon_analysis.py -m "not live_network"`

---

### Task 27.4.1 — CPI: live query, routing, fixtures, unit tests, live test

**Repo:** fpac-soil-mcp
**Files in scope:**
- Must edit: `src/fpac_soil_mcp/models.py`, `src/fpac_soil_mcp/sdv_query.py`, `src/fpac_soil_mcp/sda_client.py`, `src/fpac_soil_mcp/polygon_analysis.py`, `src/fpac_soil_mcp/corridor_analysis.py`, `src/fpac_soil_mcp/tools/soil_tools.py`, `src/fpac_soil_mcp/lesa.py`, `tests/fixtures/le_benchmarks.json`, `tests/test_sda_client.py`, `tests/test_lesa.py`, `tests/test_polygon_analysis.py`, `tests/test_live_sda.py`
**Depends on:** 27.3.1

**Spec:** Implement Minnesota CPI (Crop Productivity Index) following the same live-first pattern as CSR2 (task 27.3.1). Start with a live SDA query to obtain real Minnesota rating data, build offline fixtures from it, implement the full stack, then confirm with a live test.

1. **Live query first:** Query live SDA for CPI ratings using known Minnesota mukeys (from research in 27.1.2). Document actual values and county max.
2. Add `CPI = "CPI"` to `ProductivityIndexType` enum.
3. Add CPI provenance entry to `PRODUCTIVITY_PROVENANCE`.
4. Add CPI SQL template(s) or metadata-driven routing in `sdv_query.py`.
5. Update `sda_client.py` methods to accept `index_type="cpi"`.
6. Update `lesa.py` `_normalize_productivity_index` to accept `cpi`.
7. Expand guards in `polygon_analysis.py`, `corridor_analysis.py`, `tools/soil_tools.py` to accept CPI.
8. **Build fixtures from live data:** Add CPI benchmark fixture(s) to `le_benchmarks.json` using actual Minnesota ratings from step 1.
9. Add CPI unit tests in `test_sda_client.py`, `test_lesa.py`, `test_polygon_analysis.py`.
10. Add CPI live_network test to `test_live_sda.py` and run to confirm contract.

**Constraints:** Do NOT break NCCPI or CSR2 routing. Do NOT add Storie support. CPI rating values may use a different scale — verify from research. Worker must have network access for steps 1 and 10.

**Acceptance:**
- `uv run pytest -m "not live_network"` — all offline tests pass
- `uv run pytest tests/test_live_sda.py -m live_network` — live CPI test passes
- `uv run ruff check .` and `uv run ruff format --check .` — clean

---

### Task 27.5.1 — Storie: live query, routing, fixtures, unit tests, live test, final ADR amendment

**Repo:** fpac-soil-mcp
**Files in scope:**
- Must edit: `src/fpac_soil_mcp/models.py`, `src/fpac_soil_mcp/sdv_query.py`, `src/fpac_soil_mcp/sda_client.py`, `src/fpac_soil_mcp/polygon_analysis.py`, `src/fpac_soil_mcp/corridor_analysis.py`, `src/fpac_soil_mcp/tools/soil_tools.py`, `src/fpac_soil_mcp/lesa.py`, `tests/fixtures/le_benchmarks.json`, `tests/test_sda_client.py`, `tests/test_lesa.py`, `tests/test_polygon_analysis.py`
**Depends on:** 27.4.1

**Spec:** Implement Minnesota CPI (Crop Productivity Index) as a validated public productivity index, following the same pattern as CSR2 (task 27.3.1) but using the CPI SDA storage pattern from research task 27.1.2.

1. Add `CPI = "CPI"` to `ProductivityIndexType` enum.
2. Add CPI provenance entry to `PRODUCTIVITY_PROVENANCE`.
3. Add CPI SQL template(s) or metadata-driven routing in `sdv_query.py`.
4. Update `sda_client.py` methods to accept `index_type="cpi"`.
5. Update `lesa.py` `_normalize_productivity_index` to accept `cpi`.
6. Expand guards in `polygon_analysis.py`, `corridor_analysis.py`, `tools/soil_tools.py` to accept CPI.
7. Add CPI benchmark fixture(s) to `le_benchmarks.json` using Minnesota soil survey areas.
8. Add CPI unit tests.

**Constraints:** Do NOT break NCCPI or CSR2 routing. Do NOT add Storie support. CPI rating values may use a different scale — verify from research.

**Grep anchors:** Same as 27.3.1.

**Reference implementation:** The CSR2 implementation from task 27.3.1.

**Acceptance:**
- `uv run pytest -m "not live_network"` — all tests pass
- `uv run ruff check .` and `uv run ruff format --check .` — clean
- Targeted: `uv run pytest tests/test_sda_client.py tests/test_lesa.py tests/test_polygon_analysis.py -m "not live_network"`

---
