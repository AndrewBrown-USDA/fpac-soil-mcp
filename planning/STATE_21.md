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
| 1 | 21.1.1 Hardening SDA query builders and interpretation SQL | pending |
| 1 | 21.1.2 Adding SDA regression coverage | pending |
| 2 | 21.2.1 Partitioning polygon ratings by county | pending |
| 2 | 21.2.2 Testing county partition and opt-out behavior | pending |
| 3 | 21.3.1 Correcting LESA index fallback and sentinel behavior | pending |
| 3 | 21.3.2 Wiring WKT and configurable corridor buffers | pending |
| 3 | 21.3.3 Testing LESA and corridor public inputs | pending |
| 4 | 21.4.1 Running final offline and lint verification | pending |

## Task Reports

<!-- Workers append reports here, each no more than 15 lines. -->
