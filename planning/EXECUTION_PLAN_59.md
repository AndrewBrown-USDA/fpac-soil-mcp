# EXECUTION_PLAN_59 -- Map geometry in MCP result `_meta` (issue #117)

Branch `feature/meta-map1` off `origin/main` 6a00e222 (PR #119, issue #84, merged). Local, no upstream. Ships in 0.6.0 (unreleased).

## Goal & Scope

**Goal.** Keep `include_map`, but stop putting display geometry in the part of a tool result the model reads. When `include_map=true`, the three map tools return display geometry in the MCP result `_meta` (FastMCP `ToolResult(meta=...)`) under `gov.usda.fpac-soil/map`. The body (`content` + `structuredContent`) describes each layer and is the same for both flag values except `delivery`. `_meta` becomes the place for any later app-only data, one key per item. Output schemas are explicit and typed for all three tools. The agent app reads `_meta` and gives the browser the same map block it gets today.

**In scope**
- `analyze_farmland_by_polygon`, `analyze_corridor_fppa`, `get_soil_polygons_by_geometry`: map display data moves to `_meta`; explicit output schemas from Pydantic models; neutral `include_map` wording.
- Typed corridor output schema (closes Plan 58 D21) and a typed soil polygons schema covering success and error bodies.
- App: `geo.py` merges body + `_meta` into today's browser block; agent trace guard (`FpacMcpServer`).
- ADR 0017 dated amendment; README 0.6.0 note; app README/AGENTS.md; `.env.example` comment.

**Out of scope** (issue #117 plus decisions below)
- Removing `include_map`; always returning geometry; server-side result storage; new map layers.
- Moving `get_soil_polygons_by_geometry` top-level `features` geometry (D2).
- Frontend code, fixtures or Playwright changes (D5).
- Version bump, `server.json`, `manifest.yaml` (D8).
- Live SDA calls; AI Playground `_meta` behaviour (not verified; noted in ADR 0017).
- Other `_meta` items (export files, renderer hints): the key convention only.

**Constraints carried from issue #117 and the handoff (verbatim where quoted)**
- "For every flag value, the model-visible parts (content and structuredContent) contain no coordinates." (applies per D2)
- "The existing size cap (map_max_geojson_bytes) and the rule of dropping whole layers still apply."
- "Acreage, geometry_hash, tabular_csv and summaries are unchanged for both flag values."
- Coverage enums stay in the explicit schemas, built with `model_json_schema()`, never hand-written; `src/fpac_soil_mcp/models/coverage.py` is the source of truth.
- `test_tool_output_schemas_list_coverage_enums` keeps passing unchanged or extended; never weakened.
- No coverage behaviour change: a failed query is `error`; coverage values in `src/` use the `MAPPING_*` / `RATING_*` constants.
- No live SDA; mock with `httpx.MockTransport` or fakes.

**Comment for #117 (the user posts it)**

> Scope notes from planning (Plan 59):
> - `get_soil_polygons_by_geometry` keeps its top-level `features` geometry in the body: returning geometry is the tool's job. Only its `map.layers` geometry moves to `_meta`. The "no coordinates" criterion applies to the analyze tools and to the `map` block of all three tools.
> - Split rule: the body `map.layers[]` keeps `id`, `title`, `kind`, `authority`, `source`, `data_vintage`, `style_key`, `legend`, `delivery`. `_meta["gov.usda.fpac-soil/map"]` holds `display_crs`, `bounds`, `warnings` and per-layer `feature_collection`, `feature_count`, `simplified`, `simplify_tolerance_m`, `truncated`. `delivery` is `meta_geojson` or `omitted`. `MAP_SCHEMA_VERSION` goes to 2.0.

## Decision log

| ID | Date | Decision | Source |
| --- | --- | --- | --- |
| D1 | 2026-11-18 | Branch `feature/meta-map1` off `origin/main` 6a00e222; local until a push is approved. | user (Q1) |
| D2 | 2026-11-18 | `get_soil_polygons_by_geometry` keeps top-level `features` geometry in the body; only its `map.layers` geometry moves to `_meta`. | user (Q2, option A) |
| D3 | 2026-11-18 | Split rule: body describes the layer, `_meta` holds what was produced for display (field lists in Goal comment). Moved fields leave the body models; no null relics. Breaking: `feat(map)!:` + `BREAKING CHANGE:`. | user (Q3) |
| D4 | 2026-11-18 | One `_meta` key per app-data item; map key `gov.usda.fpac-soil/map`. Payload `{display_crs, bounds, warnings, layers: {<layer id>: {...}}}`; draw order from body `layers[]`. No key when `include_map=false`. `MAP_SCHEMA_VERSION` 1.0 -> 2.0. | user (Q4) |
| D5 | 2026-11-18 | Body `delivery: Literal["meta_geojson", "omitted"]`. `geo.py` sets `inline_geojson` back in the browser block; frontend unchanged. | user (Q5) |
| D6 | 2026-11-18 | Schemas from Pydantic only, `output_schema=Model.model_json_schema()` at registration. New `CorridorToolResponse` (closes D21 of Plan 58) and `SoilPolygonsResponse` (success + error bodies). Guard test: every branch x both flags through `fastmcp.Client`, which validates bodies against the schema. | user (Q6) |
| D7 | 2026-11-18 | App trace guard: `FpacMcpServer(McpServer)` records its own TOOL span with each `gov.usda.fpac-soil/*` `_meta` entry replaced by a stub (key, layer ids, byte count). | user (Q7, option A) |
| D8 | 2026-11-18 | Ship in 0.6.0, no bump. README note next to the coverage note. `server.json`, `manifest.yaml` unchanged (grep check). | user (Q8) |
| D9 | 2026-11-18 | Plan 58 execution model: one agent, tasks serially in id order, micro-plan approval per task, one local commit per task, offline, ask before every push. Gates below. | user (Q9) |
| D10 | 2026-11-18 | A size-capped layer keeps a `_meta` layers entry `{truncated: true}` without `feature_collection`/`feature_count`; body `delivery` is `omitted`; the warning names it. `geo.py` copies `truncated` to the browser layer. Amends D4 for capped layers. | user (Q10, option A) |
| D11 | 2026-11-18 | Display data rides a `PrivateAttr` on `MapBlock` (not in schema or `model_dump`). A `functools.wraps` wrapper turns the tool's model into `ToolResult(content, structured_content, meta)` at registration, so direct Python calls still return the model. Probed on FastMCP 4.1.7: input schema and descriptions kept, unknown args still rejected. | my rec (recon) |

## Gates

- Per task: the targeted tests in its spec.
- Wave end: full root pytest; plus app pytest when the wave touched `apps/`. Wave 1 is the server switch: its tasks are file-disjoint but ordered, and the full suite is expected red between 59.1.1 and 59.1.7. The wave-1 end gate is the first full-suite gate.
- 59.3.2: the full baseline table, greps, and a `list_tools()` probe.
- Optional manual: dev app trial (`agent-fpac-soil-dev`) after a user-approved push.

## Wave table

| Wave | Task | Title | Files (must edit / can create) | Depends on |
| --- | --- | --- | --- | --- |
| 1 | 59.1.1 | Map models and builder split | `models/map.py`, `spatial/map_builder.py`, `spatial/__init__.py`, `models/__init__.py`, `tests/test_map_contract.py` | -- |
| 1 | 59.1.2 | Tool response models | `models/spatial.py`; create `tests/test_tool_response_models.py` | 59.1.1 |
| 1 | 59.1.3 | Tool functions return models | `mcp/tools/spatial_analysis_tools.py`, `mcp/tools/soil_lookup_tools.py`, `tests/test_tools.py`, `tests/test_phase3_contracts.py` | 59.1.2 |
| 1 | 59.1.4 | `_meta` wrapper and explicit schemas | `mcp/tools/__init__.py`, `tests/test_server.py`; create `mcp/tools/results.py`, `tests/test_meta_results.py` | 59.1.3 |
| 1 | 59.1.5 | Polygon map tests | `domain/polygon_analyzer.py` (docstrings only), `tests/test_polygon_map.py` | 59.1.1 |
| 1 | 59.1.6 | Corridor map tests | `domain/corridor_analyzer.py` (docstrings only), `tests/test_corridor_map.py` | 59.1.1 |
| 1 | 59.1.7 | Tool-layer map tests | `tests/test_map_tool_contracts.py`, `tests/test_soil_polygons_map.py` | 59.1.4 |
| 2 | 59.2.1 | App merges `_meta` into the browser block | `apps/agent-fpac-soil-openai-sdk/agent_server/geo.py`, app `tests/test_geo_screen.py`, `tests/test_geo_map.py`, `tests/test_geo_corridor.py` | wave 1 |
| 2 | 59.2.2 | App trace guard | app `agent_server/agent.py`, app `tests/test_agent_mcp_wiring.py` | wave 1 |
| 3 | 59.3.1 | ADR 0017 amendment and docs | `docs/decisions/0017-server-map-result-contract.md`, `README.md`, app `README.md`, app `AGENTS.md`, `.env.example` | waves 1-2 |
| 3 | 59.3.2 | Final verification | `planning/STATE_59.md` only | 59.3.1 |

`src/` paths are under `src/fpac_soil_mcp/`. Files within each wave are pairwise disjoint (checked by script in review). One agent runs tasks serially in id order.

## Hazards (recon)

- `corridor_analyzer.py` is 1457 lines, `polygon_analyzer.py` 655: enter via grep anchors only.
- `MapBlock` has a `mode="wrap"` validator that re-dumps `MapBlock` instances (`_validate_map_block`). Re-dumping drops private attributes, so it must carry the display across, or the analyzers lose it when they build their response.
- `CorridorToolResponse` must be built from the corridor response's field values (keeping the same `MapBlock` instance), not from `model_dump()`, or the display is lost.
- The MCP Python client validates `structuredContent` against `outputSchema` and raises on mismatch (`mcp/client/session.py` `validate_tool_result`). Every error body must fit its schema.
- `tests/test_map_tool_contracts.py` parses the ADR 0017 `### Mapping to strategy section 4` table. The amendment must not change that table.
- `tests/test_tools.py` (13 `include_map` refs, mostly mocked forwarding) and `tests/test_phase3_contracts.py` index the corridor result as a dict; they move to model access in 59.1.3 only.
- `eval/contract/test_contract.py` lists `get_soil_polygons_by_geometry` and runs in root pytest; if it breaks at the wave-1 gate, re-scope (do not widen a task ad hoc).
- App `geo.py` calls MCP through `_call_tool_untraced`; keep it. App route tests run against the real `McpServer` class.
- Producers (polygon, corridor, soil tool) only pass `simplify_tolerance_m` into `build_layer` and never read moved fields; `build_layer`'s output is only appended to a list and passed to `build_map_block`.

## Plan review (2026-11-18)

- **Spec axis:** every #117 acceptance criterion maps to a task: no coordinates (59.1.4 assert 2); body equal across flags (59.1.4 assert 3, stricter than #117); one key + size cap (59.1.1); explicit schemas (59.1.4, 59.3.2); unchanged numbers (59.1.4 assert 5); app map panel + Show on map (59.2.1); traces (59.2.2); ADR (59.3.1). Neutral wording: 59.1.3. Every one of D1-D11 is reflected; no task adds work outside them.
- **Standards axis:** files within each wave are pairwise disjoint (script check: wave 1 has 21 files, wave 2 has 6, wave 3 has 6, no duplicates once root and app `README.md` are told apart). Every must-edit file is tracked, and no create target exists. Every task has a spec section with anchors and a targeted test command.
- **Judgment call:** wave 1 tasks are file-disjoint, but they are ordered (59.1.2 -> 59.1.3 -> 59.1.4 -> 59.1.7; 59.1.5 and 59.1.6 need only 59.1.1). The suite is red inside the wave. This breaks the usual "tasks in a wave are independent" rule, but it fits the serial model (D9) and avoids a transitional shim. The alternative is splitting it into 5 waves with no green gate between them.
- Coupling checked: `models/__init__.py` re-exports `spatial` models, so 59.1.2 does not add exports. `tests/test_phase2_contracts.py` and `eval/contract/test_contract.py` only list tool names and metadata, so they are not in scope.

## Task specs

### 59.1.1 -- Map models and builder split
- **Repo:** fpac-soil-mcp. **Depends on:** none.
- **Files:** must edit `src/fpac_soil_mcp/models/map.py`, `src/fpac_soil_mcp/spatial/map_builder.py`, `src/fpac_soil_mcp/spatial/__init__.py`, `src/fpac_soil_mcp/models/__init__.py`, `tests/test_map_contract.py`. Scratch: `/tmp/59.1.1/`.
- **Spec:**
  - `MAP_SCHEMA_VERSION = "2.0"`; add `MAP_META_KEY = "gov.usda.fpac-soil/map"`.
  - `LayerDelivery = Literal["meta_geojson", "omitted"]`.
  - `MapLayer` keeps only `id`, `title`, `kind`, `delivery` (default `omitted`), `authority`, `source`, `data_vintage`, `style_key`, `legend`. Update field descriptions (no "inline").
  - New `MapLayerDisplay`: `feature_collection: dict | None`, `feature_count: int | None`, `simplified: bool = False`, `simplify_tolerance_m: float | None`, `truncated: bool = False`.
  - New `MapDisplay`: `display_crs` (default `DISPLAY_CRS`), `bounds: list[float] | None`, `warnings: list[str]`, `layers: dict[str, MapLayerDisplay]`.
  - `MapBlock` keeps only `layers`. Add `PrivateAttr` `_display: MapDisplay | None` and a read-only `display` property. `_validate_map_block` keeps `_display` when it re-validates an instance.
  - `build_layer(...)` keeps its keyword arguments and returns a `LayerBuild` (frozen dataclass: `layer: MapLayer`, `display: MapLayerDisplay | None`). With `include_map=false`, `display` is None. Otherwise it is set and `layer.delivery = "meta_geojson"`.
  - `bounds_of` reads `MapDisplay` layers. `enforce_size_cap` works on display bytes, drops whole layers from the end, and leaves a capped layer as `MapLayerDisplay(truncated=True)` with no collection or count. The body layer becomes `omitted`, the warning text is unchanged, and bounds are recomputed (D10).
  - `build_map_block(builds, max_bytes) -> MapBlock`: the display is attached only if some layer was built with `include_map`; otherwise `display` is None.
  - Update both `__all__` lists. Export `MapDisplay`, `MapLayerDisplay`, `MAP_META_KEY`, `LayerBuild`.
- **Anchors:** `models/map.py` (91 lines: `class MapLayer`, `class MapBlock`, `_validate_map_block`); `map_builder.py` `def build_layer` ~130, `def bounds_of` ~181, `def enforce_size_cap` ~210, `def build_map_block` ~237, `__all__` ~330.
- **Do not touch:** legend, category, simplification maths; `features_from_sda_rows`, `with_productivity`, `productivity_by_mukey`.
- **Acceptance:** `test_map_contract.py` covers: `model_json_schema()` of `MapBlock` and `MapLayer` has no `feature_collection`, `bounds`, `display_crs`, `warnings`, `feature_count`, `simplified`, `simplify_tolerance_m`, `truncated`; descriptor-only build has `display is None`; include build puts geometry only in `display`; size cap gives `{truncated: true}` + `omitted` + warning; display survives `PolygonFarmlandAnalysisResponse(map=block)`-style re-validation (use a minimal model with a `MapBlock` field); body dump identical for both flags except `delivery`.
- **Test:** `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/tmp/fpac-venv uv run --group dev pytest tests/test_map_contract.py -q -p no:cacheprovider`

### 59.1.2 -- Tool response models
- **Depends on:** 59.1.1.
- **Files:** must edit `src/fpac_soil_mcp/models/spatial.py`; create `tests/test_tool_response_models.py`.
- **Spec:**
  - Update the `map` field descriptions on `PolygonFarmlandAnalysisResponse` and `CorridorFarmlandAnalysisResponse` (no "geometry only when include_map"; say geometry goes to `_meta` `gov.usda.fpac-soil/map`).
  - Add `CorridorToolResponse(CorridorFarmlandAnalysisResponse)` with `lesa_evaluation: LESAEvaluationResult | None = None` (from `fpac_soil_mcp.models.lesa`; check for import cycles).
  - Add `SoilPolygonsProperties` (`total_aoi_acres`, `feature_count`, `clipped`).
  - Add `SoilPolygonsResponse`, matching all three bodies built in `get_soil_polygons_by_geometry` (success, geometry validation error, SDA error): `type: Literal["FeatureCollection"]`, `features: list[dict[str, Any]]`, `properties: SoilPolygonsProperties | None = None`, `source: dict[str, Any]`, `limitations: list[str]`, `regulatory_notice: str`, `error: str | None = None`, `status: Literal["error"] | None = None`, `error_details: ToolError | None = None`, plus `schema_version`, `data_mode`, `authority`, `map` as in the other responses.
  - Do not add exports to `models/__init__.py` (owned by 59.1.1). Callers import the new models from `fpac_soil_mcp.models.spatial`.
- **Anchors:** `class PolygonFarmlandAnalysisResponse` ~29, `map: MapBlock` ~72 and ~258, `class CorridorFarmlandAnalysisResponse` ~207; `ToolError` (grep `class ToolError` in `models/`); `soil_lookup_tools.py` `def get_soil_polygons_by_geometry` ~312 (read only).
- **Acceptance:** new tests: each soil polygons body shape (copied literally from the three branches) validates. `CorridorToolResponse.model_json_schema()` lists `county_segments[].coverage_status` = mapping enum and `productivity_coverage_status` = rating enum (use `_enum`/`_field` style from `tests/test_server.py`). Schemas have no `_display`.
- **Test:** `... pytest tests/test_tool_response_models.py -q -p no:cacheprovider`

### 59.1.3 -- Tool functions return models
- **Depends on:** 59.1.2.
- **Files:** must edit `src/fpac_soil_mcp/mcp/tools/spatial_analysis_tools.py`, `src/fpac_soil_mcp/mcp/tools/soil_lookup_tools.py`, `tests/test_tools.py`, `tests/test_phase3_contracts.py`.
- **Spec:**
  - `analyze_corridor_fppa` returns `CorridorToolResponse`, built from the corridor response's field values plus `lesa_evaluation` (keep the same `MapBlock` instance; no `model_dump()` round trip). Update the return annotation and docstring.
  - `get_soil_polygons_by_geometry` returns `SoilPolygonsResponse` in all three branches; `_soil_map_fields` returns the `MapBlock` (not a dump).
  - `INCLUDE_MAP_DESCRIPTION` and the soil polygons `include_map` docstring become neutral: "Return display geometry for client apps in result `_meta` under `gov.usda.fpac-soil/map` (ADR 0017). The model-visible result is the same either way." No "Leave false".
  - Tests: move corridor dict indexing to attribute access (or `.model_dump()` where a dict is compared); soil polygons test reads the model. Do not change asserted values.
- **Anchors:** `spatial_analysis_tools.py` `INCLUDE_MAP_DESCRIPTION`, `IncludeMap` ~30, `def analyze_corridor_fppa` ~75, `result = corridor_response.model_dump()` ~147, `result["lesa_evaluation"]` ~214; `soil_lookup_tools.py` `def _soil_map_fields` ~265, `def get_soil_polygons_by_geometry` ~312; tests: `test_tools.py` ~619, ~880-1145; `test_phase3_contracts.py` ~538, ~698-725.
- **Do not touch:** corridor/LESA/site-assessment logic; polygon tool body.
- **Acceptance / test:** `... pytest tests/test_tools.py tests/test_phase3_contracts.py -q -p no:cacheprovider` passes; `git grep -n "Leave false\|Leave it false" -- src` is empty.

### 59.1.4 -- `_meta` wrapper and explicit schemas
- **Depends on:** 59.1.3.
- **Files:** must edit `src/fpac_soil_mcp/mcp/tools/__init__.py`, `tests/test_server.py`; create `src/fpac_soil_mcp/mcp/tools/results.py`, `tests/test_meta_results.py`.
- **Spec:**
  - `results.py`: `meta_tool(func)`, a `functools.wraps` wrapper for sync functions. It calls `func` and dumps the model with `model_dump(mode="json")`, then returns `ToolResult(content=<one text block, JSON>, structured_content=body, meta={MAP_META_KEY: display.model_dump(mode="json")} or None)`. The display is `result.map.display`.
  - Before writing the text block, check how FastMCP serialized the text of a Pydantic return before this change, and match it. Record the finding in STATE.
  - Register the three tools as `mcp.tool(name=..., description=..., output_schema=<Model>.model_json_schema())(meta_tool(func))`. Models: `PolygonFarmlandAnalysisResponse`, `CorridorToolResponse`, `SoilPolygonsResponse`. Descriptions are unchanged.
  - `tests/test_server.py`: add corridor rows to `test_tool_output_schemas_list_coverage_enums` (`county_segments[].coverage_status` mapping, `county_segments[].productivity_coverage_status` rating). Delete `test_corridor_segment_schema_lists_coverage_enums`. Existing rows unchanged.
  - `tests/test_meta_results.py` is the issue #117 guard. Through `fastmcp.Client(create_mcp_server())`, with `include_map` false and true, run polygon success, polygon SDA failure, corridor success, corridor county failure, soil polygons success, soil polygons validation error and soil polygons SDA error. Fake SDA/TIGERweb/NASS; reference: the fakes in `tests/test_map_tool_contracts.py`. Assert:
    1. The client call does not raise (schema validation passes).
    2. Analyze-tool `content` and `structuredContent` contain no `coordinates`, `feature_collection` or `bounds` keys anywhere. For soil polygons, the same holds outside top-level `features`.
    3. `structuredContent` is equal across flags except `map.layers[].delivery`.
    4. `_meta[MAP_META_KEY]` is present only when `include_map=true`, and other `_meta` keys are not ours.
    5. Acreage, `geometry_hash`, `tabular_csv` and summary fields are equal across flags.
- **Anchors:** `__init__.py` `def register_tools` ~47, registrations of the three tools (~61-97); `tests/test_server.py` ~525-572.
- **Acceptance / test:** `... pytest tests/test_server.py tests/test_meta_results.py -q -p no:cacheprovider`.

### 59.1.5 -- Polygon map tests
- **Depends on:** 59.1.1.
- **Files:** must edit `src/fpac_soil_mcp/domain/polygon_analyzer.py` (docstrings only), `tests/test_polygon_map.py`.
- **Spec:** reword the `include_map` docstrings (`analyze_polygon` ~157, `_polygon_map` ~576) to the D3/D4 contract. Change assertions that read moved fields to `result.map.display` (layer entries by id, bounds, warnings). Keep every acreage/category assertion. Add: the body dump has no moved keys for either flag.
- **Anchors:** `polygon_analyzer.py` `include_map: Include display geometry` ~157, `def _polygon_map` ~570.
- **Do not touch:** analyzer logic.
- **Test:** `... pytest tests/test_polygon_map.py -q -p no:cacheprovider`

### 59.1.6 -- Corridor map tests
- **Depends on:** 59.1.1.
- **Files:** must edit `src/fpac_soil_mcp/domain/corridor_analyzer.py` (docstrings only), `tests/test_corridor_map.py`.
- **Spec:** as 59.1.5 for the corridor (`include_map` docstring ~245, `_corridor_map` docstring ~1338).
- **Anchors:** `corridor_analyzer.py` ~245, `def _corridor_map` ~1327.
- **Test:** `... pytest tests/test_corridor_map.py -q -p no:cacheprovider`

### 59.1.7 -- Tool-layer map tests
- **Depends on:** 59.1.4.
- **Files:** must edit `tests/test_map_tool_contracts.py`, `tests/test_soil_polygons_map.py`.
- **Spec:** these tests call through FastMCP. Read geometry, bounds and warnings from `_meta["gov.usda.fpac-soil/map"]` (raw `call_tool_mcp`, or `result.meta` on the high-level client). Body layers have `delivery` `meta_geojson`/`omitted`. Keep the ADR section 4 table test as is. Update the module docstrings (no "inline"). Update `ADDITIVE_KEYS`/size-margin tests only if the body shrinks; never loosen a bound upward.
- **Anchors:** `test_map_tool_contracts.py` `MAP_TOOLS` ~42, `ADDITIVE_KEYS` ~51, `_adr_section_4_fields` ~337; `test_soil_polygons_map.py` (grep `include_map`).
- **Test:** `... pytest tests/test_map_tool_contracts.py tests/test_soil_polygons_map.py -q -p no:cacheprovider`
- **Wave 1 gate (orchestrator):** full root pytest + root ruff on a `/tmp` archive copy.

### 59.2.1 -- App merges `_meta` into the browser block
- **Depends on:** wave 1.
- **Files:** must edit `apps/agent-fpac-soil-openai-sdk/agent_server/geo.py`, `apps/agent-fpac-soil-openai-sdk/tests/test_geo_screen.py`, `tests/test_geo_map.py`, `tests/test_geo_corridor.py` (app tests dir).
- **Spec:**
  - `map_block(result, meta)` builds the browser block in today's shape: `{display_crs, bounds, warnings, layers: [...]}`. Each layer is the body descriptor plus `feature_collection`, `feature_count`, `simplified`, `simplify_tolerance_m`, `truncated` from `meta["gov.usda.fpac-soil/map"]["layers"][id]`.
  - `delivery` is `inline_geojson` when the entry has a `feature_collection`, else `omitted`. With no meta: all layers `omitted`, `bounds` null, `warnings` [], `display_crs` `EPSG:4326`.
  - Read meta from the raw `CallToolResult` (`.meta`; check the attribute name on mcp 1.30) at all three call sites (`screen_aoi`, `screen_corridor`, `map_for_tool`). Use the key string as a module constant.
  - The app does not import server code. Keep the AGENTS.md rules: untraced calls, no body logging, fixed error text.
  - Tests: fake MCP results move to the new shape (body `map.layers` descriptors + `_meta`). Assert the browser block equals the old fixture block, including a capped layer (`truncated: true`, `omitted`).
- **Anchors:** `geo.py` `def parse_tool_result` ~137, `def map_block` ~335, `screen_aoi` ~341, `screen_corridor` ~478, `def map_for_tool` ~555.
- **Test:** from the `/tmp` copy: `UV_PROJECT_ENVIRONMENT=/tmp/app-venv uv run --frozen --python 3.11 pytest tests/test_geo_screen.py tests/test_geo_map.py tests/test_geo_corridor.py -q`

### 59.2.2 -- App trace guard
- **Depends on:** wave 1.
- **Files:** must edit `apps/agent-fpac-soil-openai-sdk/agent_server/agent.py`, `apps/agent-fpac-soil-openai-sdk/tests/test_agent_mcp_wiring.py`.
- **Spec:**
  - `class FpacMcpServer(McpServer)` overrides `call_tool(self, tool_name, arguments, **kwargs)`. Inside `mlflow.start_span(name=tool_name, span_type=SpanType.TOOL)` it records inputs `{tool_name, arguments}` and awaits `MCPServerStreamableHttp.call_tool(self, tool_name, arguments, **kwargs)`.
  - It records outputs as the result dump with every `_meta` key starting `gov.usda.fpac-soil/` replaced by `{"omitted_from_trace": true, "layers": [ids], "bytes": n}`, and returns the result unchanged.
  - `init_fpac_mcp_server` returns `FpacMcpServer` (non-local branch). Check the parent `call_tool` signature in `databricks_openai` 0.17.1 first.
  - Tests: patch `MCPServerStreamableHttp.call_tool` to return a fake result whose `_meta` holds coordinates. Assert: the returned object is unchanged, the recorded span has no coordinates and has the stub, and `init_fpac_mcp_server` returns the subclass. Reference: existing patterns in `test_agent_mcp_wiring.py`.
- **Anchors:** `agent.py` `def init_fpac_mcp_server` ~287, `return McpServer(` ~299; `geo.py:332` (`_call_tool_untraced`, read only).
- **Test:** `... pytest tests/test_agent_mcp_wiring.py -q` (from the `/tmp` copy).
- **Wave 2 gate:** full root pytest; app ruff + app pytest; frontend biome + build (no frontend change expected: confirm `git diff --stat` is empty under `frontend/`).

### 59.3.1 -- ADR 0017 amendment and docs
- **Depends on:** waves 1-2.
- **Files:** must edit `docs/decisions/0017-server-map-result-contract.md`, `README.md`, `apps/agent-fpac-soil-openai-sdk/README.md`, `apps/agent-fpac-soil-openai-sdk/AGENTS.md`, `.env.example`.
- **Spec:**
  - ADR 0017: a dated `> **Amended 2026-11-18 (Plan 59, issue #117).**` block at the top, following the ADR 0016 amendment style. Cover D2-D7 and D10: the MCP contract, the `_meta` key convention for future items, the browser contract in `geo.py`, the trace guard, and the unverified AI Playground `_meta` handling. Do not edit the `### Mapping to strategy section 4` table.
  - README: a "Map geometry in `_meta` (0.6.0, breaking change)" note next to `README.md:233`.
  - App README and AGENTS.md (line 34): describe `_meta` reading and the trace guard.
  - `.env.example:19` comment: "display geometry in result `_meta`".
  - Plain, short text.
- **Test:** `... pytest tests/test_map_tool_contracts.py -q -p no:cacheprovider` (ADR table parse).

### 59.3.2 -- Final verification
- **Depends on:** 59.3.1. **Files:** `planning/STATE_59.md` only.
- **Checks:**
  1. The full baseline table (root pytest, root ruff, app ruff, app pytest, biome + build, JS harness 20/20).
  2. `git grep -n inline_geojson -- src` is empty.
  3. `git grep -n -i "leave false\|leave it false" -- src` is empty.
  4. `git diff origin/main -- server.json manifest.yaml` is empty.
  5. A `list_tools()` probe shows typed output schemas (with coverage enums) for all three tools.
  6. One in-memory call per tool with `include_map=true` shows `_meta` geometry and no coordinates in the body.
  Record results; propose the push.
