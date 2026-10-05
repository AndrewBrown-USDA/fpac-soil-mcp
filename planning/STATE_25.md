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
| 1 | 25.1.1 Hardening corridor rating normalization | pending |
| 2 | 25.2.1 Restoring agent coordinate validation | pending |
| 2 | 25.2.2 Publishing the complete tool registry | pending |
| 3 | 25.3.1 Testing corridor review regressions | pending |
| 3 | 25.3.2 Testing metadata and agent contracts | pending |
| 4 | 25.4.1 Running complete review verification | pending |

## Task reports

<!-- Worker reports are appended below, one section per task, <=15 lines. -->
