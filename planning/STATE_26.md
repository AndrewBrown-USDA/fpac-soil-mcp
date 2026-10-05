# Orchestration 26 State

## Baseline

- Repository: `D:\workspace\fpac-soil-mcp`
- Prior baseline: `uv run pytest -m "not live_network"` — 328 passed,
  12 deselected.
- Prior lint baseline: `uv run ruff check .` passed.
- Prior format baseline: `uv run ruff format --check .` passed.
- Live SDA tests and pi agent evals are opt-in and must remain separate.
- Maximum two concurrent workers; full-suite verification is serial.

## Wave board

| Wave | Task | Status |
|---|---|---|
| 1 | 26.1.1 Align selectors and unavailable LE semantics | pending |
| 2 | 26.2.1 Propagate selector validation through tools | pending |
| 3 | 26.3.1 Add productivity and LESA regression tests | pending |
| 3 | 26.3.2 Correct the 45-acre evaluation fixture | pending |
| 3 | 26.3.3 Diagnose and retry missing eval tools | pending |
| 4 | 26.4.1 Add opt-in SDA rule catalog coverage | pending |
| 5 | 26.5.1 Run complete verification | pending |

## Task reports

<!-- Worker reports are appended below, one section per task, <=15 lines. -->
