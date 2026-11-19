# STATE_59 -- Map geometry in MCP result `_meta` (issue #117)

Resume point for Plan 59. Plan: `planning/EXECUTION_PLAN_59.md`. Worker prompt: `planning/PROMPT_TEMPLATE_59.md`.

## Status

- Branch `feature/meta-map1` off `origin/main` 6a00e222. Local, no upstream.
- Plan: approved 2026-11-18 (D12). Wave 1 done (59.1.1-59.1.7 plus 59.1.3b); wave-1 gate green. Next: 59.2.1. User 2026-11-19: "keep working on all waves of 59 do not stop". From 59.1.3 on, micro-plans are self-approved by the orchestrator (user, 2026-11-18: "do not stop between tasks, proceed"); still one local commit per task, no push.

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
| 59.1.3b | FastMCP 4.2.2 bump (user request, inserted) | done |
| 59.1.4 | `_meta` wrapper and explicit schemas | done |
| 59.1.5 | Polygon map tests | done |
| 59.1.6 | Corridor map tests | done |
| 59.1.7 | Tool-layer map tests | done |
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
- Gotchas (59.1.3): `lesa_tools.py` has its own `CorridorAnalyzer` mock (`_mock_lesa_corridor`), untouched. The returned `map` is a validated copy of the analyzer's `MapBlock`; `_display` survives via the 59.1.1 validator.

## 59.1.3b
- Status: done. User asked (2026-11-18) to bump FastMCP to 4.2.x as part of Plan 59, before 59.1.4 builds on `ToolResult(meta=...)`.
- Files: `pyproject.toml` `fastmcp>=2.0.0` -> `fastmcp>=4.2.2`; `uv.lock` (`uv lock --upgrade-package fastmcp`): fastmcp 4.1.7 -> 4.2.2, fastmcp-slim 4.1.7 -> 4.2.2, uncalled-for 0.4.1 -> 0.6.2; nothing else moved. App lock has no fastmcp entry.
- 4.2.0 breaking notes checked (GitHub release): Python 3.11 required (we require >=3.11); 4.1 skills API deprecated (unused here); `gen_ai.operation.name` on tools/call spans; non-finite floats rejected at JSON serialization. 4.2.1/4.2.2 notes read (auth/skills fixes, middleware `CallToolResult` edits kept). 4.1.8 notes not reviewed (output cut off); the test run is the evidence for that step.
- Tests: full root pytest on 4.2.2: 25 failed, 1081 passed, 3 skipped, 45 deselected; failing test IDs identical to the 4.1.7 run after 59.1.3 (diff of sorted FAILED lines). No FastMCP deprecation warnings in the run.

## 59.1.4
- Status: done. Micro-plan `planning/tasks/59.1.4.todo.md` self-approved.
- Serialization finding (FastMCP 4.2.2): a returned Pydantic model became one `TextContent` holding compact JSON from `fastmcp.tools.base.default_serializer(model)`; `json.loads(text) == structured_content`. Probe on HEAD before the wrapper: only `manifest.execution_timestamp_utc` and `source.timestamp_utc` differed (per-call clock). The wrapper passes `content=body` so FastMCP's same serializer writes the text.
- Files: new `mcp/tools/results.py` (`meta_tool`); `mcp/tools/__init__.py` (imports; three map tools get `output_schema=<Model>.model_json_schema()` and `meta_tool(...)`); `tests/test_server.py` (2 corridor rows added, `test_corridor_segment_schema_lists_coverage_enums` deleted); new `tests/test_meta_results.py` (7 cases).
- Tests: `pytest tests/test_server.py tests/test_meta_results.py` -> 36 passed, 3 deselected (first run: 2 corridor cases failed on `manifest.generated_at_utc`, a per-call clock key; the normalizer now drops `timestamp*` and `generated_at*`). Ruff check clean; format fixed once.
- Mutation check: a wrapper that adds `map.bounds` to the body makes the 4 analyze cases with a display fail on assert 2 (`{'bounds'}`). The client did not reject the extra key, so the key scan is the guard.
- Full root pytest (info): 25 failed, 1088 passed; failing IDs identical to 59.1.3b (diff).
- Deviations: "corridor county failure" implemented as per-county SDA failure, not a TIGERweb failure.
- Gotchas: server `_meta` also carries `io.modelcontextprotocol/serverInfo`; only `gov.usda.fpac-soil/*` keys are ours. Importing `fpac_soil_mcp.mcp.tools` before `fpac_soil_mcp.mcp.app` in a fresh process hits a circular import (seen in a pytest plugin); tests import `app` first.

## 59.1.5
- Status: done. Micro-plan `planning/tasks/59.1.5.todo.md` self-approved.
- Files: `domain/polygon_analyzer.py` docstrings only (git diff shows only the two docstring hunks); `tests/test_polygon_map.py` (display reads moved to `result.map.display`, delivery `meta_geojson`, schema 2.0, new `test_body_dump_has_no_moved_keys` x2).
- Tests: `pytest tests/test_polygon_map.py` -> 11 passed (9 before, 5 of them red). Ruff check + format clean.
- Full root pytest (info): 20 failed, 1095 passed; remaining red: test_corridor_map 7, test_map_tool_contracts 10, test_soil_polygons_map 3 (59.1.6/59.1.7). Session compute restarted before this run, so /tmp failure lists from 59.1.4 were gone; compared by per-file counts (25 - 5 polygon = 20).
- Deviations: none. Gotchas: the size-cap test now measures layer sizes from `map.display.layers`.

## 59.1.6
- Status: done. Micro-plan `planning/tasks/59.1.6.todo.md` self-approved.
- Files: `domain/corridor_analyzer.py` (two docstrings; `footprint -> LayerBuild`; `MapLayer` import replaced by `LayerBuild` -- annotation/import only, no logic); `tests/test_corridor_map.py` (display reads moved to `map.display`, schema 2.0, `meta_geojson`, D10 size-cap checks, new `test_body_dump_has_no_moved_keys` x2).
- Tests: `pytest tests/test_corridor_map.py` -> 23 passed (21 before, 7 red). Ruff check + format clean.
- Full root pytest (info): 13 failed, 1104 passed; no new failing IDs vs 59.1.5 (comm); remaining red: test_map_tool_contracts 10, test_soil_polygons_map 3 (59.1.7).
- Warnings: only the existing shapely `ops.transform` deprecation and pytest-asyncio loop-scope notice; count grows with test count.

## 59.1.7
- Status: done. Micro-plan `planning/tasks/59.1.7.todo.md` self-approved.
- Files: `tests/test_map_tool_contracts.py` (docstring; `_call_full`/`_polygon_full`/`_corridor_full` return body + `result.meta[MAP_META_KEY]`; include_map description == `INCLUDE_MAP_DESCRIPTION`; delivery `meta_geojson`; geometry, bounds, display_crs, warnings read from `_meta`; schema 2.0; section-4 table test unchanged; size-margin comment re-measured), `tests/test_soil_polygons_map.py` (same move; D10 capped layer in `_meta`).
- Size margin: additive keys shrank to 1,879 B (polygon) and 2,261 B (corridor) from 2,163/2,657; `DEFAULT_SIZE_MARGIN_BYTES` kept at 4,000 (not loosened).
- Tests: 22 passed for the two files.

## Wave 1 gate
- Full root pytest: 1117 passed, 3 skipped, 45 deselected (baseline 1091 + 26 new tests). 0 failed.
- Root ruff check + format --check on a /tmp copy (830 files): clean (one I001 import order fixed in test_map_tool_contracts.py first).
