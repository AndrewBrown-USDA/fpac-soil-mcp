# Orchestration 28 State

## Baseline checklist

- [x] `git status --short` recorded before Wave 1: clean at reconnaissance time
- [x] `uv run pytest -m "not live_network and not agent_eval" -q`: 294 passed, 14 deselected
- [x] `uv run pytest eval\test_agent_eval.py -m "not agent_eval" -q`: 8 passed, 2 deselected
- [x] `uv run ruff check .`: all checks passed
- [x] `uv run ruff format --check .`: 335 files already formatted
- [x] PR #10 404/indexing limitation recorded; no unverifiable metadata treated as fact
- [x] Default eval transport confirmed as isolated stdio
- [x] SSE/HTTP shared-port hazard recorded; live/agent-eval gates remain opt-in
- [x] ADR-0010 privacy and ADR-0011 test constraints reviewed

## Baseline results

Recorded 2026-10-14 before Wave 1 from the current working tree. The working tree was clean at reconnaissance time. The default suite excludes `live_network` and `agent_eval`; Pi and external-service gates are opt-in. Network transports default to `127.0.0.1:8000` and must be serialized or assigned distinct ports.

## Orchestrator closure gates

Run serially after implementation waves:

```powershell
uv run pytest -m "not live_network and not agent_eval"
uv run ruff check .
uv run ruff format --check .
```

## Wave board

| Task | Wave | Status | Worker | Notes |
|---|---:|---|---|---|
| 28.1.1 | 1 | pending | — | Reconstruct evidence and establish baseline |
| 28.1.2 | 1 | pending | — | Define capture/privacy/artifact contract |
| 28.2.1 | 2 | pending | — | Implement opt-in runner capture |
| 28.3.1 | 3 | pending | — | Add sanitized parser/capture regression tests |
| 28.4.1 | 4 | pending | — | Validate privacy, cleanup, and boundaries |
| 28.5.1 | 5 | pending | — | Document and close verification |

## Task reports

<!-- Worker reports are appended below, one section per task, <=15 lines. -->
