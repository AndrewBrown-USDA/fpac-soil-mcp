# Orchestration 25 State

## Baseline

- Repository: `D:\workspace\fpac-soil-mcp`
- Prior baseline: `uv run pytest -m "not live_network"` — 316 passed,
  12 deselected.
- Prior lint baseline: `uv run ruff check .` passed.
- Prior format baseline: `uv run ruff format --check .` passed.
- Live-network tests are opt-in and excluded from this orchestration.
- `pi` availability must be checked before the conditional POINT-01 agent eval.

## Wave board

| Wave | Task | Status |
|---|---|---|
| 1 | 25.1.1 Hardening corridor rating normalization | done |
| 2 | 25.2.1 Restoring agent coordinate validation | done |
| 2 | 25.2.2 Publishing the complete tool registry | done |
| 3 | 25.3.1 Testing corridor review regressions | done |
| 3 | 25.3.2 Testing metadata and agent contracts | done |
| 4 | 25.4.1 Running complete review verification | pending |

## Task reports

<!-- Worker reports are appended below, one section per task, <=15 lines. -->

## 25.1.1
- Status: done after one bounded retry.
- Changed `src/fpac_soil_mcp/corridor_analysis.py`: shared sentinel normalization
  for direct and alternative scoring, explicit CUSTOM rejection, and exact
  `SDA:NCCPI_V3` fallback provenance.
- Validation: `uv run python -m compileall -q
  src\fpac_soil_mcp\corridor_analysis.py` passed.
- Verification: corridor tests pass 14/15; the only failure is the stale
  pre-existing CUSTOM propagation expectation, superseded by task 25.3.1.
- Deviation: one permitted retry for missing `is_rated` compatibility.
- Gotcha: task 25.3.1 must replace the stale CUSTOM test with rejection coverage.

## 25.2.1
- Status: done.
- Changed `eval/test_agent_eval.py` and its task TODO.
- Restored structured argument extraction across direct, nested, message, and
  content-block pi event shapes, including JSON-string arguments.
- POINT-01 now asserts latitude `41.8781` and longitude `-93.0977` within
  `1e-5`, without flattened event-text fallback.
- Validation: `uv run pytest eval\test_agent_eval.py -m "not agent_eval"` —
  1 passed, 2 deselected.
- Deviations: none.

## 25.2.2
- Status: done.
- Changed `server.json` and its task TODO.
- Published all 10 manifest tools with exact matching names and descriptions;
  preserved unrelated server metadata.
- Validation: JSON parsed; 10 unique tool names matched `manifest.yaml`.
- Deviations: none.

## 25.3.1
- Status: done.
- Changed `tests/test_corridor_analysis.py` and its task TODO.
- Replaced stale CUSTOM propagation with explicit rejection/no-SDA coverage;
  added direct and alternative sentinel filtering, valid-zero, and exact
  `SDA:NCCPI_V3` provenance assertions.
- Validation: `uv run pytest tests\test_corridor_analysis.py` — 23 passed.
- Deviations: none.

## 25.3.2
- Status: done.
- Changed `tests/test_server.py`, `eval/test_agent_eval.py`, and its TODO.
- Added exact server/manifest tool metadata equality and deterministic POINT-01
  structured coordinate contract coverage.
- Validation: combined targeted suite — 44 passed, 2 deselected.
- Deviations: none.
