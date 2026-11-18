# STATE_57 -- include_nccpi removal and NCCPI national baseline (issue #85)

Branch: `feature/nccpi-baseline1` off `origin/main` e0c625e. Local only; ask before every push.
Plan approved by the user 2026-11-18 (D11). Next: lint baseline, then Wave 1.
Resume: read this file, then `git log --oneline origin/main..HEAD`, then the next pending wave in EXECUTION_PLAN_57.md.

## Baseline (recorded 2026-11-18 on e0c625e, before Wave 1)

- [x] Root offline pytest (`-m "not live_network and not agent_eval"`): 993 passed, 3 skipped, 45 deselected.
- [x] App pytest (`apps/agent-fpac-soil-openai-sdk`, `--frozen`): 310 passed.
- [x] JS harness (`node --test test/harness.test.js test/smoke.test.js`, `/tmp` archive copy + `npm ci`): 20/20.
- [x] `ruff check` + `ruff format --check` on a `/tmp` archive copy: all checks passed, 794 files formatted.
- [x] FastMCP 4.1.7 rejects unknown tool arguments with `ToolError` (probe with a throwaway tool).

## Wave board

| Task | Title | Status | Commit |
| --- | --- | --- | --- |
| 57.1.1 | NCCPI baseline model fields and helper | done | (this commit) |
| 57.2.1 | Remove from MCP tools and LESA call sites | pending | |
| 57.2.2 | Remove from agent app | pending | |
| 57.2.3 | Remove from JS eval harness | pending | |
| 57.2.4 | Remove from polygon analyzer | pending | |
| 57.2.5 | Remove from corridor analyzer | pending | |
| 57.3.1 | Wire baseline into polygon analysis | pending | |
| 57.3.2 | Wire baseline into corridor analysis | pending | |
| 57.4.1 | Tool descriptions, metadata, docs | pending | |
| 57.4.2 | SA-MA-04 eval prompt | pending | |
| 57.4.3 | Amend ADR 0008 | pending | |
| 57.5.1 | Final verification | pending | |
| 57.5.2 | Post-SDA checks (non-blocking) | pending | |

## Gate log

(one line per wave gate: suites, counts, date)

- Wave 1 (2026-11-18): root 1016 passed / 3 skipped (+23 new); ruff clean on touched files.

## Task reports

## 57.1.1
- Status: done.
- Files: `models/soil.py` (+6 fields after `productivity_coverage_caveats`); new `domain/nccpi_baseline.py` (`NCCPI_BASELINE_RULE`, `NCCPI_BASELINE_FIELDS`, `fetch_nccpi_baseline`, `nccpi_baseline_fields`); new `tests/test_nccpi_baseline.py`.
- Tests: `pytest tests/test_nccpi_baseline.py tests/test_models.py` 25 passed; root 1016 passed / 3 skipped.
- Deviations: none. Also treats bool / NaN / non-numeric ratings as null.
- Gotchas: `fetch_nccpi_baseline` takes `primary_rows` keyed by str mukey; for NCCPI primary pass the analyzer's rating map. Rows need `numeric_rating`, `rating_class`, `rated_pct`, `total_pct`; source falls back to the registry rule name. SDA `rated_pct=0` for misc units is kept (coverage data); rating/class stay null.
