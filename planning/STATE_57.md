# STATE_57 -- include_nccpi removal and NCCPI national baseline (issue #85)

Branch: `feature/nccpi-baseline1` off `origin/main` e0c625e. Local only; ask before every push.
Plan approved by the user 2026-11-18 (D11). Status: Waves 1-5 complete (57.5.1 green); not pushed. Next: user approval to push; 57.5.2 when SDA is reachable.
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
| 57.2.4 | Remove from polygon analyzer | done | 5250a21 |
| 57.2.5 | Remove from corridor analyzer | done | 95210f5 |
| 57.3.1 | Wire baseline into polygon analysis | done | 2a6bae7 |
| 57.3.2 | Wire baseline into corridor analysis | done | 829c4c1 |
| 57.4.1 | Tool descriptions, metadata, docs | done | 2e32d97 |
| 57.4.2 | SA-MA-04 eval prompt | done | 94b1f8e |
| 57.4.3 | Amend ADR 0008 | done | bcbd2da |
| 57.5.1 | Final verification | done | (this commit) |
| 57.5.2 | Post-SDA checks (non-blocking) | pending | |

## Gate log

(one line per wave gate: suites, counts, date)

- Wave 1 (2026-11-18): root 1016 passed / 3 skipped (+23 new); ruff clean on touched files.
- Wave 2 (2026-11-18): root 1018 passed / 3 skipped (-1 opt-out test, +3 TypeError tests); app 310 passed; harness 20/20; ruff clean (root files + `APP_LINT_PATHS`). `git grep include_nccpi -- ':!planning'` = only the 3 TypeError tests.
- Wave 3 (2026-11-18): root 1028 passed / 3 skipped (+6 polygon, +4 corridor); ruff clean on touched files.
- Wave 4 (2026-11-18): root 1031 passed / 3 skipped (+3 server); eval/common + eval/contract 178 passed; tests/eval 6 passed; harness 20/20.
- Wave 5 / 57.5.1 (2026-11-18, HEAD bcbd2da archive): root 1031 / 3 / 45; ruff check + format clean (807 files); app lint scope clean (21 files); app 310 passed; harness 20/20 (needs `databricks/bootstrap-serverless.sh` for npm). `git grep include_nccpi -- ':!planning'`: the 3 TypeError tests, 2 server tests, plus the breaking-change notes in README, QUICKSTART and ADR 0008 that 57.4.1/57.4.3 required. No function signature declares it. In-memory FastMCP Client smoke with fake SDA (csr2): polygon and corridor units carry CSR2 primary + NCCPI baseline (0.72 High rated); Water unit baseline null / `unrated`, empty CSV cells; LE, segment LE and composite identical to a no-baseline run; no baseline limitation.

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

## 57.2.5
- Status: done. `domain/corridor_analyzer.py` (signature, docstring, `ratings_requested` + 6 uses incl. 2 dead `unknown` branches); `tests/test_corridor_analysis.py` (+TypeError test).
- Tests: corridor_analysis + scoring + multi_county + corridor_map 73 passed; root 1018 / 3. Deviations: none.
- Gotcha for 57.3.2: segment loop `interp_map` is built at ~462 via `_get_corridor_ratings`; `SoilMapUnitAcreage(` at ~583.

## 57.3.1
- Status: done. `domain/polygon_analyzer.py`: baseline fetched right after the primary rating block (before county benchmark), limitation appended, `**nccpi_baseline_fields(...)` on each unit, CSV +2 columns at the end. `tests/test_polygon_analysis.py`: +6 tests (3 non-NCCPI selectors, NCCPI reuse, misc unit + CSV, SDA failure).
- Tests: polygon_analysis + polygon_map + phase2 46 passed; ruff clean.
- Deviations: none. 57.2.4's spec asked to fix the perimeter test mock; it already passed unchanged, so no fix was needed.
- Gotcha: if the NCCPI *primary* query fails, the baseline is empty with no extra limitation (the primary warning already covers it).

## 57.3.2
- Status: done. `domain/corridor_analyzer.py`: per segment, baseline fetched after `_get_corridor_ratings` (`interp_map` reused for NCCPI), limitation deduped, `**nccpi_baseline_fields(baseline_map.get(m_str))` on each unit. Alternatives untouched. `tests/test_corridor_analysis.py`: `_two_county_corridor` helper + 4 tests (two-county csr2 incl. Water misc unit, NCCPI reuse, failure in one or every segment).
- Tests: corridor_analysis + multi_county + scoring 56 passed; root 1028 / 3; ruff clean. Deviations: none.
- Gotcha: corridor NCCPI primary goes through `get_productivity_ratings` (not `get_interpretations`), so the reuse test asserts `get_interpretations` is never called.
