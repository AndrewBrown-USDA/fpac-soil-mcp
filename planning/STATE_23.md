# STATE 23: Correct Generic Productivity Ratings and LESA Routing

## Baseline Checklist

- [x] `uv sync` environment available
- [x] Offline baseline: `uv run pytest -m "not live_network"` — 280 passed,
  12 deselected, 0 failed in 32.83s
- [x] Targeted task tests pass
- [x] `uv run ruff check .` — passed after import-order correction
- [x] `uv run ruff format --check .` — passed; 288 files already formatted
- [x] Live-network tests remain opt-in and are not a completion gate
- [x] Intentional breaking change recorded: remove `nccpi_rating` and
  `nccpi_class`; replace with generic fields plus rating provenance

## Wave Board

| Wave | Task | Status | Retry/escalation |
|---|---|---|---|
| 1 | 23.1.1 Generalizing productivity response fields | done | 0 |
| 1 | 23.1.2 Defining rating provenance contract | done | 0 |
| 2 | 23.2.1 Scoring requested polygon productivity indexes | done | 0 |
| 2 | 23.2.2 Correcting LESA routing and normalization | done | 1 |
| 3 | 23.3.1 Testing generic polygon ratings | done | 0 |
| 3 | 23.3.2 Testing corridor routing and propagation | done | 0 |
| 3 | 23.3.3 Testing LESA fallback and invalid indexes | done | 0 |
| 3 | 23.3.4 Updating public rating documentation | done | 0 |
| 4 | 23.4.1 Running complete offline verification | done | 1 |

## Task Reports

<!-- Workers append reports here, each no more than 15 lines. -->

## 23.1.1
- Status: done; implementation committed as `f5e58da`.
- Changed `src/fpac_soil_mcp/models.py` lines 115-124.
- Replaced NCCPI-specific fields with generic rating, class, and provenance.
- Removed aliases and compatibility properties as specified.
- `uv run python -c "from fpac_soil_mcp.models import SoilMapUnitAcreage"` passed.
- Deviations: none.
- Gotcha: downstream consumers still require Wave 2 updates.

## 23.1.2
- Status: done; implementation committed as `a70d424`.
- Changed `src/fpac_soil_mcp/sda_client.py` approximately lines 1057-1190.
- Added truthful SDA rule/catalog provenance to rated and unrated results.
- Preserved SQL templates, validation, sentinels, and network behavior.
- `uv run pytest tests\test_sda_client.py` passed: 68 passed in 3.01s.
- Deviations: none.
- Gotcha: downstream consumers should read `productivity_rating_source`.

## 23.2.1
- Status: done; implementation committed as `7f5109f`.
- Changed `src/fpac_soil_mcp/polygon_analysis.py` approximately lines 171-434.
- Consolidated NCCPI and non-NCCPI ratings into generic rating/class/source
  fields and used requested-index values for LE weighting.
- Preserved partition benchmarks, sentinels, caveats, and CSV behavior with
  generic column names.
- Initial targeted run: 4 passed, 6 failed only on removed legacy field access.
- Deviations: none; downstream contract tests are Wave 3 scope.

## 23.2.2
- Status: done after one retry; implementation committed as `7de6992`.
- Changed `soil_tools.py` and `lesa.py` routing/normalization paths.
- Reused `_normalize_productivity_index`, propagated non-default index and
  benchmark parameters, and preserved buffered line/WKT routing.
- Explicit corridor polygon inputs now return a clear representability error;
  linework uses buffered corridor analysis.
- Final `uv run pytest tests\test_lesa.py tests\test_tools.py`: 66 passed.
- Retry reason: initial implementation failed two legacy parameter-shape tests.

## 23.3.1
- Status: done; implementation committed as `9f65010`.
- Changed `tests/test_polygon_analysis.py` and created `tests/test_models.py`.
- Added generic rating/class/source coverage for NCCPI, CSR2, CPI, and Storie,
  non-NCCPI LE scoring, sentinels, partitions, and removed aliases.
- `uv run pytest tests\test_models.py tests\test_polygon_analysis.py` passed:
  33 passed in 0.11s.
- Deviations: none; production code unchanged.

## 23.3.2
- Status: done; implementation committed as `d842bd6`.
- Changed `tests/test_tools.py` only.
- Added polygon-corridor representability, line/WKT buffers, non-NCCPI,
  benchmark, generic output, and CUSTOM normalization coverage.
- `uv run pytest tests\test_tools.py tests\test_phase3_contracts.py` passed:
  34 passed in 3.65s.
- Deviations: none; polygon corridor asserts the documented clear error.

## 23.3.3
- Status: done; implementation committed as `54fc21f`.
- Changed `tests/test_lesa.py` only.
- Added CUSTOM normalization, non-NCCPI fallback, sentinel, and unavailable
  acreage/LE regression coverage.
- `uv run pytest tests\test_lesa.py` passed: 47 passed in 0.07s.
- Deviations: none.

## 23.3.4
- Status: done; implementation committed as `0a6dade`.
- Changed `README.md` and `manifest.yaml` only.
- Documented generic rating/class/source fields, supported indexes, removed
  aliases, and corridor parameters/provenance.
- Manifest YAML parse passed; `uv run pytest tests\test_server.py` passed:
  15 passed, 3 deselected.
- Deviations: none.

## Verification Record

- Base/plan commit: `bd15891`; final verification commits recorded below.
- Full-suite owner: 23.4.1; workers must not run the full suite or
  repository-wide Ruff.
- Escalation rule: one targeted-test retry; second failure escalates to a
  mid-tier worker and increments the task's retry/escalation column.

## 23.4.1
- Status: done; verification executed serially in the approved order.
- Working tree prerequisite: only the pre-existing untracked
  `planning/tasks/23.4.1.todo.md` was present; all prerequisite Wave 3
  reports were present.
- `uv run pytest tests\test_models.py tests\test_polygon_analysis.py`:
  33 passed, 0 failed, 0 deselected, 0.10s.
- `uv run pytest tests\test_tools.py tests\test_phase3_contracts.py`:
  34 passed, 0 failed, 0 deselected, 3.65s.
- `uv run pytest tests\test_lesa.py`: 47 passed, 0 failed, 0 deselected,
  0.08s.
- `uv run pytest tests\test_sda_client.py`: 68 passed, 0 failed,
  0 deselected, 3.48s.
- `uv run pytest tests\test_server.py`: 15 passed, 0 failed,
  3 deselected, 0.48s.
- Initial `uv run pytest -m "not live_network"`: 308 passed, 1 failed,
  12 deselected; the failure was the stale removed-field assertion in
  `tests\test_phase2_contracts.py`.
- Corrective contract update committed as `6467c19`; the focused file passed:
  `uv run pytest tests\test_phase2_contracts.py` — 2 passed.
- Ruff import/format corrections committed as `b85d415`; `uv run ruff check .`
  passed and `uv run ruff format --check .` passed with 288 files formatted.
- Final `uv run pytest -m "not live_network"` passed: 309 passed,
  12 deselected in 28.32s.
- Live-network tests remained deselected and opt-in; deviations: one bounded
  corrective retry for the stale contract and formatting gate.
