# TODO

## Goal
Resolve all remaining code review issues from PR #1 across SDA client validation, aggregation methods, and live test skip handling, committing each logical fix using conventional commits.

## Tasks

### 1. SDA Interpretation Aggregation & Catalog Validation
- [x] Refactor SDA interpretation aggregation handling in `src/fpac_soil_mcp/sda_client.py` and `src/fpac_soil_mcp/config.py`: restrict allowed aggregation methods to those explicitly implemented (`Weighted Average` and `Dominant Component`) and reject unsupported methods with `SDAValidationError`.
- [x] Fix catalog cache lookup in `src/fpac_soil_mcp/sda_client.py` so a fresh client (`_cached_rule_names is None`) triggers `get_available_interpretation_rules()` before falling back to rule format validation.
- [x] Add unit tests in `tests/test_sda_client.py` covering unsupported aggregation rejection and fresh client catalog rule validation.

### 2. Live Integration Test Error Handling
- [x] Update `tests/test_live_tigerweb.py` to ensure live tests cleanly skip when TIGERweb returns `status == "error"` or when network exceptions occur, avoiding assertion failures when external endpoints are down.
- [x] Update rural test assertion in `tests/test_live_tigerweb.py` to assert `is_urban_intersected is False` and `len(urban_area_names) == 0` without tautological checks.

### 3. Verification & Quality Gates
- [x] Run full test suite (`make test` or `uv run pytest -m "not live_sda"`) and ensure 100% pass rate.
- [x] Run linting and formatting check (`make lint` and `make format-check`).
- [x] Commit each discrete change using conventional commits (`fix(...)`, `test(...)`, `chore(...)`).

## Notes
- Conventional commits format: `fix(sda): ...`, `fix(tests): ...`, etc.
- No new runtime dependencies needed.
