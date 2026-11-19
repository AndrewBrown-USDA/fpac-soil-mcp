# STATE_59 -- Map geometry in MCP result `_meta` (issue #117)

Resume point for Plan 59. Plan: `planning/EXECUTION_PLAN_59.md`. Worker prompt: `planning/PROMPT_TEMPLATE_59.md`.

## Status

- Branch `feature/meta-map1` off `origin/main` 6a00e222. Local, no upstream.
- Plan: approved 2026-11-18 (D12). Wave 1 in progress: 59.1.1 done. Next: 59.1.2.

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
| 59.1.2 | Tool response models | pending |
| 59.1.3 | Tool functions return models | pending |
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
