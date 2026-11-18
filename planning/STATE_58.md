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
| 58.3.1 | Polygon analyzer | done | f088519 |
| 58.3.2 | Corridor analyzer | done | da02e61 |
| 58.3.3 | LESA domain and `_lesa_coverage_status` | done | c408c5b |
| 58.4.1 | Type every coverage field; output schemas | done (D21) | b80177a |
| 58.4.2 | Agent app and frontend consumers | done | 6f5848f |
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

## 58.3.1
- Status: done (f088519, `fix(polygon)!`).
- Files: `domain/polygon_analyzer.py` (constants; `spatial_failed`/`rating_failed` flags; mapping `error`/`unmapped`/`partial`/`covered`; LE `error` on spatial or rating failure, else `unknown`/`unmapped`/`unrated`/`rated`/`partial`; new `_unit_rating_coverage` sets `productivity_coverage_status` per D17; NCCPI-primary rating failure marks baseline `error`); `tests/test_polygon_analysis.py` (renamed values + 5 new failure/D17 tests); `tests/test_polygon_map.py` (`invalid_request` -> `error`).
- Tests: `pytest tests/test_polygon_analysis.py tests/test_polygon_map.py tests/test_phase2_contracts.py` 51 passed; ruff clean. Mutation check: 7 tests fail against the pre-change analyzer.
- Deviations: also fixed the 58.2.3 discovered gap (NCCPI-primary failure -> baseline `error`) in the analyzer, since the analyzer owns the failure flag.

## 58.3.2
- Status: done (da02e61, `fix(corridor)!`).
- Files: `domain/corridor_analyzer.py` (constants; per-segment `seg_spatial_failed`/`seg_rating_failed`; rating failure adds deduped `Productivity rating error (<idx>) for <county>: <exc>` limitation; map unit `error` on rating failure, fallback `no_coverage` folded into `unrated`; segment mapping/rating `error`; reconciliation `error` if any segment failed (D9); NCCPI baseline `error` on NCCPI-primary failure); `tests/test_corridor_analysis.py` (helper gains `spatial_side_effect`/`primary_side_effect`; 3 new tests); `tests/test_phase3_contracts.py` (`partial`).
- Tests: corridor set (5 files) 93 passed; ruff clean. Mutation check: 5 tests fail against the pre-change analyzer. Alternatives path untouched (no coverage fields).

## 58.3.3
- Status: done (c408c5b, `fix(lesa)!`).
- Files: `domain/lesa.py` (`RATING_*` constants, `covered` -> `rated`); `mcp/tools/lesa_tools.py` (`_lesa_coverage_status` returns `RatingCoverage`, `error` if any source status is `error`; corridor sources add segment `productivity_coverage_status`; polygon sources add the manifest LE `coverage_status` so a rating failure with covered mapping reports `error`); `tests/test_tools.py` (`rated`; parametrized `_lesa_coverage_status` test; polygon rating-error LESA test).
- Tests: `pytest tests/test_lesa.py tests/test_tools.py` 133 passed; ruff clean.
- Wave 3 gate: root offline suite 1073 passed / 3 skipped / 45 deselected.

## 58.4.1
- Status: done (b80177a, `feat(models)!`).
- Files: `models/soil.py` (`FarmlandClassificationResponse.coverage_status: SoilMappingCoverage`; `SoilMapUnitAcreage.productivity_coverage_status: RatingCoverage`; `nccpi_baseline_coverage_status: RatingCoverage | None`); `models/spatial.py` (polygon and segment mapping `SoilMappingCoverage`, segment rating `RatingCoverage`); `models/lesa.py` (D19 widening removed); `tests/test_coverage_vocab.py` (LE rejects `covered`; every public model rejects a retired value; baseline null allowed); `tests/test_server.py` (exact enum lists in `list_tools()` output schemas; corridor segment enums on the response model).
- Tests: `pytest tests/test_coverage_vocab.py tests/test_server.py tests/test_map_contract.py` 76 passed; `git grep "coverage_status: str" -- src` empty; root suite 1091 passed / 3 skipped / 45 deselected; ruff clean.
- Deviation (resolved by user as D21, option A, 2026-11-18): `analyze_corridor_fppa` returns `dict[str, Any]`, so its MCP output schema is `{"additionalProperties": true, "type": "object"}` and cannot list the enums. The corridor check was done on `CorridorFarmlandAnalysisResponse.model_json_schema()` instead. Typing the corridor tool's return (or giving it an explicit output schema) is outside 58.4.1's file list.
- `test_map_contract.py` needed no change (it constructs with `covered`, still valid).

## 58.4.2
- Status: done (6f5848f, `refactor(app)`).
- Files: `frontend/client/src/components/map/useScreening.ts` (`coverage_status?: 'covered' | 'partial' | 'unmapped' | 'error' | null`); `tests/test_geo_map.py` (2 fixtures `partial`); `tests/test_geo_screen.py` (fixture + assert `partial`). `test_geo_corridor.py`, `geo.py`, `test_aoi_context.py` unchanged (values still valid / out of scope).
- Tests: `git grep partially_covered -- apps` empty. App pytest 310 passed (= baseline); app ruff check + format clean (21 files); frontend `npm ci`, biome 0 errors / 10 warnings (= baseline), build OK. All run on a `/tmp/l58` working-tree copy.
- Note: the frontend build has no typecheck, so the new TS literal type is not compiler-checked.
- Gotcha (environment): serverless restarted, `/tmp` was wiped. Running `uv run` inside the app dir in the workspace created an untracked, gitignored `apps/agent-fpac-soil-openai-sdk/.venv` (Python 3.12, created 23:22 UTC by this session, slow on the workspace FS). Deleted with user approval 2026-11-18. Use `UV_PROJECT_ENVIRONMENT=/tmp/app-venv` on a `/tmp` copy instead.
