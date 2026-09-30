# STATE 22: Resolve Local Review Findings After PR #9 Remediation

## Baseline Checklist
- [x] `uv sync` environment available
- [x] Offline verification: `uv run pytest -m "not live_network"` — 269 passed, 12 deselected
- [x] `uv run ruff check .` — passed
- [x] `uv run ruff format --check .` — passed; 275 files already formatted
- [x] Live-network tests remain opt-in and are not a completion gate

## Wave Board

| Wave | Task | Status |
|---|---|---|
| 1 | 22.1.1 Centralizing LESA regulatory constants | done |
| 2 | 22.2.1 Correcting LESA index propagation and simplifying aggregation | done |
| 3 | 22.3.1 Completing corridor LESA routing and index propagation | done |
| 3 | 22.3.2 Updating public metadata and planning history | done |
| 4 | 22.4.1 Testing LESA core corrections | pending |
| 4 | 22.4.2 Testing public corridor and metadata behavior | pending |
| 5 | 22.5.1 Running final offline and lint verification | pending |

## Task Reports

<!-- Workers append reports here, each no more than 15 lines. -->

## 22.1.1
- Added typed site LESA criterion maximum-point constants.
- Added typed site LESA criterion name constants.
- Added the two cited LESA action-guidance string constants.
- Preserved all existing statutory values and wording.
- Verified `fpac_soil_mcp.constants` imports successfully.
- `uv run ruff check src/fpac_soil_mcp/constants.py` passed.

## 22.2.1
- Imported site criterion definitions and action guidance from centralized constants.
- Preserved `SITE_CRITERIA_MAX_POINTS` and `SITE_CRITERIA_NAMES` public exports.
- Centralized numeric and unavailable Land Evaluation fallback construction.
- Preserved normalized productivity index propagation and existing summary defaults.
- Retained area-weighted aggregation shape and rounding/clamping behavior.
- `uv run pytest tests/test_lesa.py` passed: 37 tests.

## 22.3.1
- Routed line and multiline LESA inputs through buffered corridor analysis.
- Propagated requested productivity-index semantics into corridor and polygon paths.
- Kept NCCPI retrieval enabled only for the NCCPI index.
- Preserved corridor buffer defaults, explicit buffer options, and response shape.
- Retained county benchmark override propagation without changing corridor algorithms.
- Existing working-tree changes outside the task files were left untouched.
- `uv run pytest tests/test_tools.py` passed: 19 tests.

## 22.3.2
- Added public LESA and corridor capability metadata to `server.json`.
- Kept descriptions synchronized with `manifest.yaml`.
- Corrected Plan 19 history to state that removed SDV table entries remain excluded.
- Parsed `server.json` successfully.
- `uv run ruff check .` failed on pre-existing errors in `src/fpac_soil_mcp/lesa.py:748` (F841) and `src/fpac_soil_mcp/tools/soil_tools.py:38` (F401); neither file was in scope.
