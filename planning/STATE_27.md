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
| 3 | 27.3.1 | pending | CSR2: live query → fixtures → impl → unit tests → live test → ADR |
| 4 | 27.4.1 | pending | CPI: live query → fixtures → impl → unit tests → live test |
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
