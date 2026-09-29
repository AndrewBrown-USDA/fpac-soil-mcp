# EXECUTION PLAN 20: SSURGO Interpretation & Dynamic SDV Query Hardening

## Goal & Scope
- **Goal**: Refactor state-specific soil productivity queries (Storie, CSR2, CPI) in `sda_client.py` to use standard SSURGO tables (`cointerp` / `sdvattribute`) instead of non-existent table aliases (`cstorie`, `coiacsr2`, `iacsr2`, `cocpi`, `cpi`), ensure robust sentinel/unrated value filtering, align mocked unit test expectations, and verify full green status across offline and live network test suites.
- **In Scope**:
  - `src/fpac_soil_mcp/sda_client.py`: Clean table allowlist and replace static non-SSURGO table templates with standard `cointerp` rules / dynamic SDV attribute queries.
  - `tests/test_sda_client.py`: Update unit test fixtures and assertions to match refactored query templates.
  - `tests/test_live_sda.py`: Add and verify live SDA network test cases for dynamic SDV lookups, state interpretations, out-of-state mukeys, and water/urban unrated components.
  - Full offline suite and live test suite execution.
- **Out of Scope**:
  - Changes to LESA scoring math in `lesa.py` or GIS corridor polygon buffering in `soil_tools.py`.
  - Non-SDA clients (`nass_client.py`, `tigerweb_client.py`).

## Verbatim Constraints
- Do not reference non-existent tables `cstorie`, `coiacsr2`, `iacsr2`, `cocpi`, `cpi` in SDA queries.
- Retain strict SQL sanitization and input validation on survey area symbols and numeric `mukey` values.
- Exclude sentinel values (`99`, `999`, `-99`, `-999`) across all SQL rating queries and aggregation passes.
- Maintain full compatibility with Python 3.11+ and Ruff formatting/linting standards.

## Decision Log
- **2026-09-28**: State-specific indices (California Storie, Iowa CSR2) use standard `cointerp` rules (`California Revised Storie Index (CA)` and `Iowa Corn Suitability Rating 2 (CSR2)` / `cointerp.mrulename LIKE '%CSR2%'`).
- **2026-09-28**: Minnesota CPI and arbitrary regional indices resolve dynamically via `sdvattribute` or fall back to dynamic lookup.
- **2026-09-28**: `ALLOWED_SDV_TABLES` strictly limited to standard SSURGO tables: `{"cointerp", "component", "mapunit", "sdvattribute"}`.

## Wave & Dependency Table

| Wave | Task ID | Task Title | Files in Scope | Depends On |
| --- | --- | --- | --- | --- |
| 1 | 20.1.1 | Refactor SDA Productivity Query Templates & Tables | `src/fpac_soil_mcp/sda_client.py` | None |
| 1 | 20.1.2 | Update Mocked SDA Client Unit Tests | `tests/test_sda_client.py` | None |
| 2 | 20.2.1 | Expand & Verify Live SDA Integration Tests | `tests/test_live_sda.py` | 20.1.1, 20.1.2 |
| 3 | 20.3.1 | Full Suite & Lint Verification | `planning/STATE_20.md`, `TODO.md` | 20.2.1 |

---

## Task Specifications

### Task 20.1.1: Refactor SDA Productivity Query Templates & Tables
- **Repo**: `AndrewBrown-USDA/fpac-soil-mcp`
- **Files in Scope**: `src/fpac_soil_mcp/sda_client.py`
- **Depends On**: None
- **Spec**:
  - Update `ALLOWED_SDV_TABLES` to `{ "cointerp", "component", "mapunit", "sdvattribute" }`.
  - Refactor `SQL_PRODUCTIVITY_STORIE` and `SQL_PRODUCTIVITY_COUNTY_MAX_STORIE` to join only `cointerp` on `ci.ruledepth = 0 AND (ci.mrulename LIKE '%Storie%' OR ci.mrulename LIKE '%storie%')`.
  - Refactor `SQL_PRODUCTIVITY_CSR2` and `SQL_PRODUCTIVITY_COUNTY_MAX_CSR2` to join `cointerp` on `ci.ruledepth = 0 AND (ci.mrulename LIKE '%CSR2%' OR ci.mrulename LIKE '%csr2%' OR ci.mrulename LIKE '%Corn Suitability Rating%')`.
  - Refactor `SQL_PRODUCTIVITY_CPI` and `SQL_PRODUCTIVITY_COUNTY_MAX_CPI` to route through dynamic SDV attribute lookup or cointerp rule matching.
  - Ensure all queries filter out `rating IS NOT NULL AND rating NOT IN (99, 999, -99, -999)`.
- **Grep Anchors**: `ALLOWED_SDV_TABLES`, `SQL_PRODUCTIVITY_STORIE`, `SQL_PRODUCTIVITY_CSR2`, `get_productivity_ratings`, `get_county_max_productivity_rating`
- **Acceptance Command**: `uv run pytest tests/test_sda_client.py`

### Task 20.1.2: Update Mocked SDA Client Unit Tests
- **Repo**: `AndrewBrown-USDA/fpac-soil-mcp`
- **Files in Scope**: `tests/test_sda_client.py`
- **Depends On**: None
- **Spec**:
  - Update test fixtures and mock query strings that check for Storie, CSR2, and SDV queries to align with the new standard SSURGO cointerp query structure.
  - Verify invalid tables in `build_dynamic_sdv_query` raise `SDAValidationError` when encountering disallowed table names.
- **Grep Anchors**: `test_get_productivity_ratings_storie`, `test_get_productivity_ratings_csr2`, `test_build_dynamic_sdv_query`
- **Acceptance Command**: `uv run pytest tests/test_sda_client.py`

### Task 20.2.1: Expand & Verify Live SDA Integration Tests
- **Repo**: `AndrewBrown-USDA/fpac-soil-mcp`
- **Files in Scope**: `tests/test_live_sda.py`
- **Depends On**: 20.1.1, 20.1.2
- **Spec**:
  - Test live queries for Storie index in California (rated) and Iowa (unrated/None).
  - Test live queries for CSR2 in Iowa (rated) and California (unrated/None).
  - Test live queries for dynamic NCCPI county maximums.
  - Verify water/urban area unrated components return None or valid non-sentinel handling.
- **Grep Anchors**: `TestLiveSDA`, `test_live_out_of_state_productivity_indices`, `test_live_dynamic_sdv_queries_and_unrated_water_urban`
- **Acceptance Command**: `uv run pytest tests/test_live_sda.py -m live_network`

### Task 20.3.1: Full Suite & Lint Verification
- **Repo**: `AndrewBrown-USDA/fpac-soil-mcp`
- **Files in Scope**: `planning/STATE_20.md`, `TODO.md`
- **Depends On**: 20.2.1
- **Spec**:
  - Execute full offline test suite (`uv run pytest -m "not live_network"`).
  - Execute live network test suite (`uv run pytest tests/test_live_sda.py -m live_network`).
  - Execute formatting and lint checks (`uv run ruff check .` and `uv run ruff format --check .`).
  - Update `TODO.md` and `planning/STATE_20.md` with final verification results.
- **Acceptance Command**: `uv run pytest -m "not live_network" ; if ($?) { uv run ruff check . }`
