# TODO

## Goal
Refactor state-specific soil productivity queries (Storie, CSR2, CPI) in `sda_client.py` to use standard SSURGO tables (`cointerp` / `sdvattribute`) instead of non-existent table views, harden unrated/sentinel handling across state interpretations, and verify full offline and live network test suites.

## Tasks

### 1. Refactor SQL Templates & Query Builders in `sda_client.py`
- [x] Remove legacy non-existent table aliases (`cstorie`, `coiacsr2`, `iacsr2`, `cocpi`, `cpi`) from SQL templates and `ALLOWED_SDV_TABLES`.
- [x] Refactor `SQL_PRODUCTIVITY_STORIE`, `SQL_PRODUCTIVITY_CSR2`, `SQL_PRODUCTIVITY_CPI`, and their county max queries to standard `cointerp` rules or dynamic SDV queries.
- [x] Update `ALLOWED_SDV_TABLES` to standard SSURGO tables (`mapunit`, `component`, `cointerp`, `sdvattribute`).

### 2. Update Tests & Fixtures
- [x] Update mocked unit tests in `tests/test_sda_client.py` to match the refactored SQL templates and cointerp rules.
- [x] Verify handling of unrated out-of-state mukeys and water/urban components in both unit and live tests.

### 3. Verification & Quality Gates
- [x] Run full offline test suite (`uv run pytest -m "not live_network"`).
- [x] Run live network test suite (`uv run pytest tests/test_live_sda.py -m live_network`).
- [x] Run Ruff linting and format checking (`uv run ruff check .` and `uv run ruff format --check .`).

## Notes
- Live SDA supports standard SSURGO tables; custom state tables do not exist in the public tabular endpoint.
- Sentinel values (99, 999, -99, -999) must be consistently excluded from area-weighted calculations and county max queries.
