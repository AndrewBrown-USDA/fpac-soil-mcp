# STATE 21: Resolve Remaining PR #9 Review Findings

## Baseline Checklist
- [x] `uv sync` environment available
- [x] Offline baseline: `uv run pytest -m "not live_network"` — 254 passed, 12 deselected
- [x] `uv run ruff check .` — passed
- [x] `uv run ruff format --check .` — passed
- [ ] Live SDA tests remain opt-in and are not a completion gate

## Wave Board

| Wave | Task | Status |
|---|---|---|
| 1 | 21.1.1 Hardening SDA query builders and interpretation SQL | done |
| 1 | 21.1.2 Adding SDA regression coverage | done |
| 2 | 21.2.1 Partitioning polygon ratings by county | done |
| 2 | 21.2.2 Testing county partition and opt-out behavior | done |
| 3 | 21.3.1 Correcting LESA index fallback and sentinel behavior | pending |
| 3 | 21.3.2 Wiring WKT and configurable corridor buffers | pending |
| 4 | 21.3.3 Testing LESA and corridor public inputs | pending |
| 5 | 21.4.1 Running final offline and lint verification | pending |

## Task Reports

<!-- Workers append reports here, each no more than 15 lines. -->

## 21.1.1
- **Status**: done
- **Files**: `src/fpac_soil_mcp/sda_client.py`
- **Validation**: `uv run pytest tests/test_sda_client.py` — 68 passed
- **Changes**: hardened dynamic builder boundaries, negative sentinels, and CPI/NCCPI matching.
- **Deviations**: none.

## 21.1.2
- **Status**: done
- **Files**: `tests/test_sda_client.py`
- **Validation**: `uv run pytest tests/test_sda_client.py` — 68 passed after 21.1.1
- **Changes**: added injection, area-symbol, sentinel, and CPI/NCCPI regression coverage.
- **Deviations**: none.

## 21.2.1
- **Status**: done
- **Files**: `src/fpac_soil_mcp/polygon_analysis.py`
- **Validation**: `uv run pytest tests/test_polygon_analysis.py` — 9 passed, 1 initial test mismatch; combined suite passed after 21.2.2.
- **Changes**: added sentinel normalization, NCCPI opt-out gating, per-area benchmarks, and acreage-weighted scoring.
- **Deviations**: none in implementation; the initial failure referenced a test assertion added by the parallel test task.

## 21.2.2
- **Status**: done
- **Files**: `tests/test_polygon_analysis.py`
- **Validation**: `uv run pytest tests/test_polygon_analysis.py -q` — 10 passed.
- **Changes**: covered separate-area benchmarks, acreage weighting, opt-out request suppression, and all four sentinel forms.
- **Deviations**: none.
