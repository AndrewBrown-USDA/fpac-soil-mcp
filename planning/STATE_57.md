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
| 57.1.1 | NCCPI baseline model fields and helper | done | c092783 |
| 57.2.1 | Remove from MCP tools and LESA call sites | done | 0c935dd |
| 57.2.2 | Remove from agent app | done | 85e1b6b |
| 57.2.3 | Remove from JS eval harness | done | ca66a5d |
| 57.2.4 | Remove from polygon analyzer | done | (next commit) |
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

## 57.2.1
- Status: done.
- Files: `mcp/tools/spatial_analysis_tools.py` (both signatures, docstrings, polygon call, `corridor_kwargs`; `productivity_index` docs now list four selectors + NCCPI baseline); `mcp/tools/lesa_tools.py` (2 kwargs + now-unused `ProductivityIndexType` import); `tests/test_tools.py` (7 lines); `tests/test_phase3_contracts.py` (4 lines); `tests/fixtures/criterion2_benchmark.v1.json` (4 keys).
- Tests: targeted 143 passed; root 1016 passed / 3 skipped; ruff clean.
- Deviations: removed the unused import (F401 after the kwarg went).
- Gotchas: analyzers still accept the kwarg until 57.2.4/57.2.5; registered descriptions in `tools/__init__.py` untouched (57.4.1).

## 57.2.2
- Status: done. `agent_server/geo.py` (tool args), `tests/test_geo_screen.py` (expected call, reformatted to one line).
- Tests: app pytest 310 passed (test_geo_screen 33); ruff on `APP_LINT_PATHS` clean. Deviations: none.
- Gotcha: ruff on whole `agent_server/` reports 7 pre-existing findings in template files outside `APP_LINT_PATHS`; use the Makefile scope.

## 57.2.3
- Status: done. `eval/fpac_soil_mcp_harness/lib/evalCases.js` deriver. Harness 20/20. No test asserted the key. Deviations: none.

## 57.2.4
- Status: done. `domain/polygon_analyzer.py` (3 signatures, 2 forwards, docstring, gate on ~184 and ~226); `tests/test_polygon_analysis.py` (opt-out test deleted, kwarg dropped, TypeError test x2); `tests/test_phase2_contracts.py:99`.
- Tests: test_polygon_analysis + phase2 + polygon_map + lesa 102 passed; ruff clean. Deviations: none.
