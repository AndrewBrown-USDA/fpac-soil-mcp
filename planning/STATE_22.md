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
| 2 | 22.2.1 Correcting LESA index propagation and simplifying aggregation | pending |
| 3 | 22.3.1 Completing corridor LESA routing and index propagation | pending |
| 3 | 22.3.2 Updating public metadata and planning history | pending |
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
