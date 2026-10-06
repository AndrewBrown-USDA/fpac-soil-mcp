# STATE 20: SSURGO Interpretation & Dynamic SDV Query Hardening

## Baseline Checklist
- [x] Python environment synchronized (`uv sync`)
- [x] Baseline offline test suite passing (252 passed)
- [x] Ruff lint & formatting checks clean

## Wave Board

| Wave | Task ID | Description | Status |
| --- | --- | --- | --- |
| 1 | 20.1.1 | Refactor SDA Productivity Query Templates & Tables | done |
| 1 | 20.1.2 | Update Mocked SDA Client Unit Tests | done |
| 2 | 20.2.1 | Expand & Verify Live SDA Integration Tests | done |
| 3 | 20.3.1 | Full Suite & Lint Verification | done |

## Task Reports
- **20.1.1**: Cleaned `ALLOWED_SDV_TABLES`, refactored Storie/CSR2/CPI templates to standard `cointerp` rules, added sentinel exclusions.
- **20.1.2**: Updated mock query request assertions in `tests/test_sda_client.py`.
- **20.2.1**: Verified live SDA queries for state indices (CA vs IA), dynamic SDV county maximum, and unrated water/urban components (7/7 passed).
- **20.3.1**: Verified 254 offline tests passed, 7 live tests passed, Ruff format & lint clean.
