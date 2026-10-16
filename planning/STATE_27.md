# STATE_27 — Orchestration 27 State Tracker

## Baseline (recorded before Wave 1)

### Green baseline check
- [x] `uv run pytest -m "not live_network"` — 295 passed, 1 skipped, 12 deselected (16.55s)
- [x] `uv run ruff check .` — clean (61 pre-existing EXE002 warnings, no new issues)
- [x] `uv run ruff format --check .` — clean (336 files formatted)
- [x] Branch `feat/phase-4-part-2-sdv-routing` exists, rebased onto origin/main (e2a4ea2)
- [x] Working tree clean

### Key facts at baseline
- `ProductivityIndexType` enum contains only `NCCPI` (models.py:318)
- `ALLOWED_SDV_TABLES` = `{cointerp, component, mapunit, sdvattribute}` (sda_client.py:250)
- `regional_scoring.v1.json` is empty `[]`
- NCCPI-only guards at: polygon_analysis.py:110, corridor_analysis.py:156, soil_tools.py:203/404/526, lesa.py:68
- `test_polygon_analysis.py:229` parametrizes `['csr2', 'cpi', 'storie', 'custom']` expecting rejection
- ADR 0008 status: Accepted; decision: NCCPI-only validated public contract
- No module extraction — all SDV infrastructure stays in sda_client.py
- Shapely 2.2.0 reinstall required on serverless compute (bundled GEOS)

## Wave Board

| Wave | Task | Status | Notes |
| --- | --- | --- | --- |
| 1 | 27.1.1 | done | Research complete. See SDV_STATE_INDEX_RESEARCH.md |
| 2 | 27.2.1 | done | chorizon + cocropyld table paths, col validation fix |
| 3 | 27.3.1 | done | CSR2 validated: enum + routing + SQL templates + tests + ADR 0008 |
| 4 | 27.4.1 | done | CPI validated: enum + routing + SQL templates + tests + ADR 0008 |
| 5 | 27.5.1 | pending | Storie: live query → fixtures → impl → unit tests → live test → final ADR |

## Task Reports

### 27.1.1 — Research SDA Storage Patterns (Wave 1)
**Status:** done
**Output:** `planning/SDV_STATE_INDEX_RESEARCH.md`

**Key findings:**
- CSR2: `mapunit.iacornsr` (Integer, 5-100). Iowa-only. Existing mapunit query path.
- CPI: `component.cropprodindex` (Integer, 1-100). ND/SD/MN. Existing component query path.
  - Not populated in all MN counties (missing in metro areas like Hennepin)
  - Fixture county: MN167 (Wilkin, 202 components, max=100)
- Storie: `cointerp` via "AGR - California Revised Storie Index (CA)" (Float, 0-1).
  Identical to NCCPI routing pattern, different rule name. CA-only.
- All three route through existing `build_dynamic_sdv_query()` table paths.
- No new tables needed in ALLOWED_SDV_TABLES for these three indexes.
- Wave 2 may add `chorizon`/`cocropyld` for future extensibility only.

**Decision:** Task 27.1.1 (extraction) eliminated — no module extraction, SDV infra stays in sda_client.py.

### 27.2.1 — Expand ALLOWED_SDV_TABLES and Harden Query Builders (Wave 2)
**Status:** done

**Changes:**
- Added `chorizon` and `cocropyld` to `ALLOWED_SDV_TABLES` (sda_client.py:250)
- Added `chorizon` branch to `build_dynamic_sdv_query()`: depth-weighted horizon average,
  then component-weighted aggregation. Uses `SUM(val * thickness) / SUM(thickness)` per component.
- Added `cocropyld` branch to `build_dynamic_sdv_query()`: optional `cropname` filter from
  `attribute_meta`, component-weighted aggregation. Returns `cropname` and `yldunits` in output.
- Added matching `chorizon` and `cocropyld` branches to `build_dynamic_sdv_county_max_query()`.
- Fixed column name validation: `col.isalnum()` → `re.fullmatch(r"[a-zA-Z][a-zA-Z0-9_]*", col)`
  to allow underscored SDA column names (e.g., `awc_r`, `nonirryield_r`).
- 6 new unit tests: chorizon query, cocropyld query, cocropyld-no-cropname query,
  chorizon county max, cocropyld county max, updated allowlist test.
- Updated exclusion test: `cocropyld` removed from exclusion assertion.

**Test results:** 301 passed, 1 skipped, 12 deselected (16.24s). Lint clean.
**Sanity-check indexes:** AWC (`chorizon.awc_r`), Non-Irrigated Crop Yields (`cocropyld.nonirryield_r`).

### 27.3.1 — CSR2 Implementation (Wave 3)
**Status:** done

**Changes:**
- Added `ProductivityIndexType.CSR2` enum value (models.py:322)
- Added `PRODUCTIVITY_PROVENANCE["csr2"] = "SDA:MAPUNIT_IACORNSR"` (sda_client.py)
- Added `SQL_PRODUCTIVITY_CSR2` and `SQL_PRODUCTIVITY_COUNTY_MAX_CSR2` fixed SQL templates
  using `mapunit.iacornsr` directly (no cointerp, no component joins)
- Added CSR2 routing in `get_productivity_ratings()` and `get_county_max_productivity_rating()`
  with aliases: "csr2", "iowa corn suitability rating csr2"
- CSR2 rounding: integer scale → round to 0 decimal places
- Expanded NCCPI-only guards in:
  - polygon_analysis.py: guard + dynamic `norm_idx` from enum value
  - corridor_analysis.py: guard + dynamic `norm_idx` from enum value
  - tools/soil_tools.py: 3 guards (polygon, corridor, LESA)
  - lesa.py: error message update (normalize already accepts any valid enum)
- Updated `test_polygon_analysis.py`: removed csr2 from rejected parametrize list
- 7 new unit tests in test_sda_client.py:
  - CSR2 ratings query (verifies iacornsr, no cointerp)
  - CSR2 alias resolution
  - CSR2 county max query (IA169)
  - CSR2 county max null (non-Iowa)
  - CSR2 SQL template content verification
- 2 new tests in test_lesa.py: normalize accepts CSR2, rejects unknown
- 3 new live_network tests in test_live_sda.py:
  - CSR2 ratings for Iowa mukey
  - CSR2 county max IA169 (verified 90-100 range, expected 96)
  - CSR2 county max IL019 returns None (Iowa-only column)
- CSR2 benchmark fixture added to le_benchmarks.json (IA_CSR2_STORY_COUNTY_SITE)
- ADR 0008 amended: CSR2 validated as second public index; design extensibility confirmed

**Test results:** 307 passed, 1 skipped, 15 deselected (offline). 15 passed (live). Lint clean.

### 27.4.1 — CPI Implementation (Wave 4)
**Status:** done

**Changes:**
- Added `ProductivityIndexType.CPI` enum value (models.py:323)
- Added `PRODUCTIVITY_PROVENANCE["cpi"] = "SDA:COMPONENT_CROPPRODINDEX"` (sda_client.py)
- Added `SQL_PRODUCTIVITY_CPI` and `SQL_PRODUCTIVITY_COUNTY_MAX_CPI` fixed SQL templates
  using component-weighted `component.cropprodindex` (integer scale 1-100)
- Added CPI routing in `get_productivity_ratings()` and `get_county_max_productivity_rating()`
  with aliases: "cpi", "crop productivity index"
- CPI rounding: integer scale → round to 0 decimal places (same as CSR2)
- Expanded guards to accept CPI in:
  - polygon_analysis.py, corridor_analysis.py, tools/soil_tools.py (3 guards), lesa.py
- Updated `test_polygon_analysis.py`: removed cpi from rejected parametrize list
- 6 new unit tests in test_sda_client.py:
  - CPI ratings query (verifies cropprodindex, component-weighted)
  - CPI alias resolution ("crop productivity index")
  - CPI county max query (MN167)
  - CPI county max null (non-populated county)
  - CPI SQL template content verification
- 1 new test in test_lesa.py: normalize accepts CPI
- 3 new live_network tests in test_live_sda.py:
  - CPI county max MN167 (verified 90-100 range, expected 100)
  - CPI county max MN053 Hennepin (may be null in metro)
  - CPI county max CA077 returns None (not a CPI state)
- CPI benchmark fixture added to le_benchmarks.json (MN_CPI_WILKIN_COUNTY_SITE)
- ADR 0008 amended: CPI validated as third public index

**Test results:** 312 passed, 1 skipped, 18 deselected (offline). 18 passed (live). Lint clean.
