# STATE_58 -- Shared coverage vocabularies and `error` status (issue #84)

Branch: `refactor/coverage-vocab1` off `origin/main` 9acfbd2 (Plan 57 merged via PR #118). Local only, no upstream; ask before every push.
Plan status: approved by the user 2026-11-18 (D20). Baseline recorded 2026-11-18 on 6a293a0. Waves 1-2 done. Next: Wave 3.
Resume: read this file, then `git log --oneline origin/main..HEAD`, then the next pending wave in EXECUTION_PLAN_58.md.

## Baseline (recorded 2026-11-18 on 6a293a0, serverless)

Matches STATE_57 final (5dec901); 9acfbd2 has the same tree as 8c5ade6.

- [x] Root offline pytest (`-m "not live_network and not agent_eval"`): 1031 passed, 3 skipped, 45 deselected.
- [x] App pytest (`apps/agent-fpac-soil-openai-sdk`, `--frozen`): 310 passed.
- [x] JS harness (`/tmp` archive + `npm ci`): 20/20.
- [x] `ruff check` + `ruff format --check` on a `/tmp` archive copy: clean (811 files formatted).
- [x] `make app-frontend-check` (on the `/tmp` archive): biome 0 errors, 10 warnings; build OK.
- [x] Probe: FastMCP 4.1.7 renders `Literal` as `{"enum": [...], "type": "string"}` and `Literal | None` as `anyOf[enum, null]`. Read `Tool.output_schema` (`outputSchema` is deprecated).

## Wave board

| Task | Title | Status | Commit |
| --- | --- | --- | --- |
| 58.1.1 | Coverage vocabulary module | done | ad8675b |
| 58.2.1 | SDA client rating rows | done | bc5ba5d |
| 58.2.2 | Soil lookup tools | done | 29510c9 |
| 58.2.3 | NCCPI baseline failure reports `error` | done | 33ae3c5 |
| 58.3.1 | Polygon analyzer | pending | |
| 58.3.2 | Corridor analyzer | pending | |
| 58.3.3 | LESA domain and `_lesa_coverage_status` | pending | |
| 58.4.1 | Type every coverage field; output schemas | pending | |
| 58.4.2 | Agent app and frontend consumers | pending | |
| 58.4.3 | README note and ADR 0019 | pending | |
| 58.5.1 | Final verification | pending | |
| 58.5.2 | Post-SDA checks (non-blocking) | pending | |

## Task reports

## 58.1.1
- Status: done (ad8675b). Micro-TODO `planning/tasks/58.1.1.todo.md`.
- Files: new `models/coverage.py` (types, `MAPPING_*`/`RATING_*` constants, `SOIL_MAPPING_COVERAGE_VALUES`/`RATING_COVERAGE_VALUES`, value table docstring); `models/__init__.py` exports; `models/lesa.py` import + `LandEvaluationSummary.coverage_status: RatingCoverage | Literal["covered"]` (transitional, D19); new `tests/test_coverage_vocab.py` (22 tests).
- Tests: `pytest tests/test_coverage_vocab.py tests/test_models.py tests/test_lesa.py` 86 passed. Root offline suite 1053 passed / 3 skipped / 45 deselected (+22 vs baseline). Ruff check + format clean (lint copy).
- Deviations: none.
- Gotchas: import constants from `fpac_soil_mcp.models.coverage`; the transitional widening also already accepts `rated`/`error`, so Wave 3 can switch LE values one module at a time. 58.4.1 must drop `| Literal["covered"]` and update `test_land_evaluation_summary_transitional_values`.
- Tooling: `/tmp/t58.sh <pytest args>` (targeted tests) and `/tmp/l58.sh <paths>` (ruff on a working-tree copy with exec bits cleared) are local helpers, rebuilt if `/tmp` is wiped.

## 58.2.1
- Status: done (bc5ba5d, `refactor(sda)!`).
- Files: `clients/sda/client.py` (imports; ~584 `RATING_UNKNOWN`; ~628 and ~654 status blocks, every non-rated row `RATING_UNRATED`); `tests/test_sda_client.py` (unknown/unrated asserts, new zero-coverage test); `tests/test_sdv_contract.py` (vocabulary assert); `docs/sdv-metadata-contract.md` (reason -> status sentence, ~190).
- Tests: `pytest tests/test_sda_client.py tests/test_sdv_contract.py` 183 passed; ruff clean.
- Deviations: none. Gotcha: corridor (~560) passes row statuses through, so it now sees `unknown`/`unrated` instead of `not_found`/`no_coverage`.

## 58.2.2
- Status: done (29510c9, `fix(soil)!`).
- Files: `mcp/tools/soil_lookup_tools.py` (import; 3x `MAPPING_ERROR`, 2x each `MAPPING_UNMAPPED`/`MAPPING_COVERED`); `tests/test_tools.py` (soil lookup only: `no_data` -> `error`, new mukey upstream-error test); `eval/contract/test_contract.py` (~449 `error` + `error` object).
- Tests: `pytest tests/test_tools.py eval/contract` 82 passed (eval/contract alone 20); `git grep no_data` on the tool file empty; ruff clean.
- Deviations: none.

## 58.2.3
- Status: done (33ae3c5, `fix(nccpi)`).
- Files: `domain/nccpi_baseline.py` (`BASELINE_ERROR_MARKER`, failure marker per mukey, marker -> `RATING_ERROR`, constants); `tests/test_nccpi_baseline.py` (failure markers, no-row null); `tests/test_polygon_analysis.py` (~566 `error`).
- Tests: `pytest tests/test_nccpi_baseline.py tests/test_polygon_analysis.py tests/test_corridor_analysis.py` 101 passed. Wave 2 gate: root suite 1056 passed / 3 skipped / 45 deselected; ruff clean.
- Deviations: none. Discovered: with primary index `nccpi` and a failed primary rating query the baseline stays null (reuses empty primary rows); see `tasks/58.2.3.todo.md`.
