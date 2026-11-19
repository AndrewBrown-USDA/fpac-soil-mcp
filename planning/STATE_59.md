# STATE_59 -- Map geometry in MCP result `_meta` (issue #117)

Resume point for Plan 59. Plan: `planning/EXECUTION_PLAN_59.md`. Worker prompt: `planning/PROMPT_TEMPLATE_59.md`.

## Status

- Branch `feature/meta-map1` off `origin/main` 6a00e222. Local, no upstream.
- Plan: approved 2026-11-18 (D12). Wave 1 in progress: 59.1.1-59.1.3 done. Next: 59.1.4. From 59.1.3 on, micro-plans are self-approved by the orchestrator (user, 2026-11-18: "do not stop between tasks, proceed"); still one local commit per task, no push.

## Baseline (feature/meta-map1 @ 6a00e222, recorded 2026-11-18 on a `git archive` copy in /tmp/base59)

| Check | Result |
| --- | --- |
| Root pytest | 1091 passed, 3 skipped, 45 deselected |
| Root ruff | clean |
| App ruff | clean |
| App pytest | 310 passed |
| Frontend | biome 0 errors, 10 warnings (662 files); build OK |
| JS harness | 20/20 |

## Wave board

| Task | Title | Status |
| --- | --- | --- |
| 59.1.1 | Map models and builder split | done |
| 59.1.2 | Tool response models | done |
| 59.1.3 | Tool functions return models | done |
| 59.1.4 | `_meta` wrapper and explicit schemas | pending |
| 59.1.5 | Polygon map tests | pending |
| 59.1.6 | Corridor map tests | pending |
| 59.1.7 | Tool-layer map tests | pending |
| 59.2.1 | App merges `_meta` into the browser block | pending |
| 59.2.2 | App trace guard | pending |
| 59.3.1 | ADR 0017 amendment and docs | pending |
| 59.3.2 | Final verification | pending |

## Task reports

## 59.1.1
- Status: done. Micro-plan `planning/tasks/59.1.1.todo.md` approved by the user (answer: `footprint` annotation goes in 59.1.6).
- Files: `models/map.py` 7-104 (2.0, `MAP_META_KEY`, `meta_geojson`, trimmed `MapLayer`, new `MapLayerDisplay`/`MapDisplay`, `MapBlock.layers` + private `_display`/`display`, validator keeps `_display`); `spatial/map_builder.py` 3-36, 148-260, `__all__` (frozen `LayerBuild`, `build_layer` -> `LayerBuild`, `bounds_of(MapDisplay)`, size cap on display, `build_map_block(builds, ...)`); both `__init__.py` exports; `tests/test_map_contract.py` (15 tests ported, inline test renamed to geometry-only-in-display, 4 new: body schemas, body equal across flags, display survives re-validation, size cap no-op without display).
- Tests: `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/tmp/fpac-venv uv run --group dev pytest tests/test_map_contract.py -q -p no:cacheprovider` -> 19 passed. Ruff check + format on a /tmp copy (exec bits cleared): clean.
- Full root pytest (info, expected red per D12): 24 failed, 1071 passed, 3 skipped, 45 deselected. Failures only in `test_corridor_map.py` (7), `test_map_tool_contracts.py` (9), `test_polygon_map.py` (5), `test_soil_polygons_map.py` (3), all owned by 59.1.5-59.1.7.
- Deviations: none.
- Gotchas: `build_layer` now returns `LayerBuild` (`.layer`, `.display`); read display via `block.display` (None when `include_map=false`). A capped layer is `MapLayerDisplay(truncated=True)` in `display.layers[id]`. `model_copy()` and re-validation into a parent model keep the display; `MapBlock.model_validate(block.model_dump())` drops it (by design). 59.1.6: change `corridor_analyzer.py` `footprint(...) -> MapLayer` (~1351) to `LayerBuild`. Ruff on a tar copy reports false EXE002 unless `chmod -x` first.

## 59.1.2
- Status: done. Micro-plan approved by the user (answer: import `LESAEvaluationResult` from `domain/lesa.py`).
- Files: `models/spatial.py` 11-27 (imports, `MAP_FIELD_DESCRIPTION` from `MAP_META_KEY`), 86 + 322 (both `map` descriptions), 90-137 (`SoilPolygonsProperties`, `SoilPolygonsResponse`), 326-332 (`CorridorToolResponse`); new `tests/test_tool_response_models.py` (11 tests).
- Tests: `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/tmp/fpac-venv uv run --group dev pytest tests/test_tool_response_models.py tests/test_map_contract.py -q -p no:cacheprovider` -> 30 passed (first run 2 failed: test compared schema enum order to the unordered `*_COVERAGE_VALUES` frozensets; fixed to `get_args(SoilMappingCoverage/RatingCoverage)`). Ruff check + format clean.
- Full root pytest (info): 24 failed, 1082 passed; same 24 failures as after 59.1.1 (59.1.5-59.1.7 files).
- Deviations: spec said `models.lesa`; class is in `fpac_soil_mcp.domain.lesa` (first `models` -> `domain` import; no cycle, probed).
- Gotchas: import new models from `fpac_soil_mcp.models.spatial` (not re-exported). `SoilPolygonsResponse.source` is `dict[str, Any]` (success adds `endpoint`). Coverage enum order comes from the `Literal`s, not the frozensets.

## 59.1.3
- Status: done. Micro-plan `planning/tasks/59.1.3.todo.md` self-approved (see Status).
- Files: `mcp/tools/spatial_analysis_tools.py` (neutral `INCLUDE_MAP_DESCRIPTION` + both docstrings; `analyze_corridor_fppa -> CorridorToolResponse`, built from `CorridorFarmlandAnalysisResponse.model_fields` values plus `lesa_evaluation`, no `model_dump`); `mcp/tools/soil_lookup_tools.py` (`_soil_map_fields -> MapBlock`; all three branches return `SoilPolygonsResponse`; dropped `MAP_SCHEMA_VERSION`/`ResultAuthority` imports); `tests/test_tools.py` and `tests/test_phase3_contracts.py` (real `CorridorFarmlandAnalysisResponse`/`CorridorCountySegment` via `_corridor_response`/`_segment` helpers instead of `MagicMock`; attribute access).
- Tests: `pytest tests/test_tools.py tests/test_phase3_contracts.py tests/test_tool_response_models.py tests/test_map_contract.py` -> 114 passed. `git grep "Leave false\|Leave it false" -- src` empty. Ruff check + format clean (one format fix applied).
- Full root pytest (info): 25 failed, 1081 passed. New vs 59.1.2: `test_map_tool_contracts.py::test_include_map_only_on_the_map_tools` asserts the description `startswith("Leave false.")`; expected from the wording change, fix in 59.1.7.
- Deviations: `test_analyze_corridor_fppa_basic` dropped the `productivity_rating`/`productivity_rating_class` passthrough asserts (keys only existed in the old mock dict, not on the response model) and now checks `reconciliation_summary`; `"composite_relative_rating" in result` became `== 82.5`.
- Gotchas: `lesa_tools.py` has its own `CorridorAnalyzer` mock (`_mock_lesa_corridor`), untouched. The returned `map` is a validated copy of the analyzer's `MapBlock`; `_display` survives via the 59.1.1 validator.
