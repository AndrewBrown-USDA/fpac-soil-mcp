# STATE_27 — Orchestration 27 State Tracker

## Baseline (recorded before Wave 1)

### Green baseline check
- [ ] `uv run pytest -m "not live_network"` — all offline tests pass
- [ ] `uv run ruff check .` — no lint errors
- [ ] `uv run ruff format --check .` — no format issues
- [ ] `git branch feat/phase-4-part-2-sdv-routing` — branch exists from origin/main
- [ ] `git checkout feat/phase-4-part-2-sdv-routing` — on the working branch

### Key facts at baseline
- `ProductivityIndexType` enum contains only `NCCPI` (models.py:318)
- `ALLOWED_SDV_TABLES` = `{cointerp, component, mapunit, sdvattribute}` (sda_client.py:250)
- `regional_scoring.v1.json` is empty `[]`
- NCCPI-only guards at: polygon_analysis.py:110, corridor_analysis.py:156, soil_tools.py:203/404/526, lesa.py:68
- `test_polygon_analysis.py:229` parametrizes `['csr2', 'cpi', 'storie', 'custom']` expecting rejection
- ADR 0008 status: Accepted; decision: NCCPI-only validated public contract

## Wave Board

| Wave | Task | Status | Notes |
| --- | --- | --- | --- |
| 1 | 27.1.1 | pending | Extract sdv_query.py |
| 1 | 27.1.2 | pending | Research SDA patterns (live) |
| 2 | 27.2.1 | pending | Expand SDV tables |
| 3 | 27.3.1 | pending | CSR2: live query → fixtures → impl → unit tests → live test → ADR |
| 4 | 27.4.1 | pending | CPI: live query → fixtures → impl → unit tests → live test |
| 5 | 27.5.1 | pending | Storie: live query → fixtures → impl → unit tests → live test → final ADR |

## Task Reports

(Worker reports appended below as waves complete.)
