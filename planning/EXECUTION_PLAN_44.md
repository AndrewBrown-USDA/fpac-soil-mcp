# EXECUTION PLAN 44: Server Map Results, Map Rendering and Context Overlays (Phase 8 M3-M5)

**Status:** Approved by the user 2026-11-04. Not started; begin with the pre-wave-1 baseline in `STATE_44.md`.

## Goal & Scope

**Goal:** Carry Phase 8 forward in the agent app. The two `analyze_*` MCP tools return a structured `map` result (Track A M3); the map panel and chat tool cards draw that result with server legends, sources and the regulatory notice (M4); and the map gains a fixed set of context overlays with click-to-identify and "Use as AOI" (M5). Build it on `feature/agent-app-map2`, try it on the deployed app against a dev MCP server, review it, then merge.

**In scope:**

- ADR 0017 (`Proposed`): server map result contract, mapped to `planning/SPATIAL_VISUALIZATION_STRATEGY.md` section 4.
- M3: `include_map: bool = False` on `analyze_farmland_by_polygon` and `analyze_corridor_fppa`; additive top-level `schema_version`, `data_mode`, `authority`, `map` fields; layers for the AOI, farmland classes, urban context, corridor footprints and county segments; display-only simplification and a per-response size cap.
- M4: `/api/geo/screen` draws from the `map` result (one tool call instead of two); new `/api/geo/map` route; generic layer renderer with server legends and partial/simplified notes; "Show on map" on tool cards for the two analyze tools.
- M5: fixed overlay catalog (SSURGO WMS, TIGERweb counties, TIGERweb 2020 urban areas) loaded directly by the browser; toggles and per-layer errors; identify popups; "Use as AOI" for counties and urban areas under the vertex cap.
- Deployed overlay probe, dev MCP server for trials, deployed trial, two-axis code review, close-out.

**Out of scope (explicit deferrals):**

- `map` on `calculate_preliminary_lesa`, `get_farmland_classification_by_point`, `get_soil_polygons_by_geometry` and every other tool (D3).
- Restructuring responses into the full strategy section 4 envelope (`analysis_id`, `status`, `summary`, `metrics`, `provenance`, `privacy` as new top-level objects) (D4).
- A server overlay-catalog endpoint (the catalog is a frontend constant, D5); a generic or user-URL proxy; user-supplied basemap or overlay URLs; a service-specific proxy unless the 44.1.2 probe fails (D5).
- Simplifying county or urban outlines to make them fit as an AOI (D6).
- M6 formats (KML/KMZ, GPX, SHP, CSV, GPKG, FGDB, `/api/geo/convert`), M7 hardening (508 review, CSP), offline testbeds (`demo_testbeds.gpkg`), line/corridor drawing on the map, multiple labelled AOIs, opt-in chat history.
- System prompt, FPPA sequence and SA scoring changes (separate track).

**Verbatim constraints from the user:**

- "do M3 to M5." (2026-11-04)
- "this seems like a good boundary for the analyze_* tools to take include_map and the rest to not" (2026-11-04)
- "id like to be able to upgrade but if we have to pin back older version of maplibre i suppose that is opk" (2026-11-03; MapLibre stays on 6.x, fixed in PR #75)

## Reconnaissance Log

- **Branch:** `feature/agent-app-map2` off `origin/main` 06525de (PR #75 maplibre worker fix and PR #74 Plan 43 merged). Plan 44 is unused on every branch. Next ADR: 0017.
- **Agent app:** `agent-fpac-soil-openai-sdk` deploys from git `main`, `auto_deploy: true`, active deployment at 06525de, RUNNING (`apps get`, 2026-11-04). `app.yaml` hard-codes `FPAC_MCP_URL=https://mcp-fpac-soil-7474654188777746.aws.databricksapps.com/mcp`; `tests/test_deploy_config.py` asserts that URL in `app.yaml` and `databricks.yml` (`resources.apps.agent_openai_agents_sdk`), and the `mcp_server` resource `{name: mcp-fpac-soil, permission: CAN_USE}`.
- **MCP server app:** `mcp-fpac-soil` is not git-backed. Active deployment from `/Workspace/Users/Groups/team-03/fpac-soil-mcp`, created 2026-10-21, so it predates Plan 43. Root `app.yaml` runs `python main.py` with `MCP_TRANSPORT=http`.
- **Server tools:** `tools/spatial_analysis_tools.py` (181 lines): `analyze_farmland_by_polygon` (L21, returns `PolygonFarmlandAnalysisResponse` from `PolygonAnalyzer.analyze_polygon`) and `analyze_corridor_fppa` (L57, returns `corridor_response.model_dump()` plus optional `lesa_evaluation`). Response models in `models.py` (599 lines): `PolygonFarmlandAnalysisResponse` L162, `CorridorFarmlandAnalysisResponse` L275; both already carry `source`, `manifest`, `limitations`, `regulatory_notice`, `tabular_csv`.
- **Geometry already in hand:** `polygon_analysis.py` (487 lines) calls `sda_client.get_spatial_intersection(..., return_geom=False)` at L154-158; `corridor_analysis.py` (929 lines) does the same at L374-378 and L734-735 and holds `direct_poly` (L200), `project_footprint` (L256), `alt_footprint` (L673) and county segments (L285). `tigerweb_client.py` (703 lines) `check_urban_exemption` (L268) requests urban geometry (L312) and builds `urban_geometries` (L345-353), then drops it. `UrbanExemptionRecord` lives in `integration_models.py` L100. `get_spatial_intersection(return_geom=True)` returns WKT in `geom` (`sda_client.py` L1591-1620); `get_soil_polygons_by_geometry` (`soil_lookup_tools.py` L176) is the reference for turning those rows into GeoJSON features.
- **Projection helpers:** `geometry.py` `_TO_EQUAL_AREA` / `_TO_WGS84` (L55-56, EPSG:4326 <-> EPSG:6933).
- **Settings:** `config.py` `Settings(BaseSettings)` with `Field` defaults and validators (L7-130); pattern for new map settings.
- **App backend:** `agent_server/geo.py` (349 lines): `screen_aoi` (L308) calls `analyze_farmland_by_polygon` and `get_soil_polygons_by_geometry` untraced via `_call_tool_untraced` (L298) and returns `display.analysis`, `display.soil_polygons`, `display.regulatory_notice`, `chat_summary`. `MAX_BODY_BYTES = 256 KB`, `DEFAULT_MAX_VERTICES = 2000`. Routes in `start_server.py` (`/api/geo/health` L26, `/api/geo/screen` L32). `aoi_context.py` has `parse_active_aoi` (L44) and `substitute_arguments` (L116), which swap an `aoi_ref` string for the active geometry.
- **Tool results in the browser:** `utils.py` `process_agent_stream_events` emits `tool_call_output_item` as `response.output_item.done`; `client/src/components/message.tsx` (489 lines) renders MCP tools with `McpTool` at ~L401 (`elements/mcp-tool.tsx`, 246 lines). Tool-card arguments are the model's arguments, before agent-side `aoi_ref` substitution.
- **Map panel:** `components/map/MapPanel.tsx` (343 lines): sources `soil` (L108) and `aoi` (L121), Terra Draw (L129), soil layer fill from `screening.result.display.soil_polygons` (L219-220). `farmlandClasses.ts` (128 lines) holds class colours, hatch hints and text codes matching strategy section 5. `useScreening.ts` (116 lines) types `ScreeningResponse`. MapLibre 6.4.1 with the worker fix in `maplibreWorker.ts`.
- **Overlay evidence:** `planning/evidence/40.2.3-networking.md`: SSURGO `https://SDMDataAccess.sc.egov.usda.gov/Spatial/SDM.wms` and WFS capabilities and TIGERweb Urban `MapServer/0` and `State_County/MapServer/1` metadata returned CORS headers from a non-browser client; layer names, scale limits, query limits and deployed-origin browser behaviour are unverified.
- **Tests and checks:** root `make check` (ruff, format-check, `pytest -m "not live_network and not agent_eval"`); `make test-live`; `make app-check` (ruff on `APP_LINT_PATHS` then app pytest); `make app-frontend-check` (`npm ci`, biome lint with two skips, build). Contract-test references: `tests/test_phase3_contracts.py`, `tests/test_tools.py`, `tests/test_polygon_analysis.py`, `tests/test_corridor_analysis.py`, `tests/test_tigerweb_client.py`; app references `tests/test_geo_screen.py` (fake MCP fixture), `tests/test_aoi_context.py`, `tests/test_custom_routes.py`.
- **ADRs:** 0003 (preliminary screening; render server `regulatory_notice`), 0004 (geodesic acreage, EPSG:6933), 0010 (geometry is operational data), 0011 (mocked default, live opt-in tests), 0012 (separate MCP client, no wrapper tools), 0015 (vendored frontend, local-changes list), 0016 (map AOI as chat session context; geometry allowed in traces).
- **Environment:** one Genie Code session, no sub-agents. Edit and commit in the workspace clone; `/tmp` only for gate clones and caches. `source databricks/bootstrap-serverless.sh` before node/npm/npx in every shell. Shell `mv` mentioning workspace paths is blocked by the safety checker; reinstall with `npm ci` in `/tmp`. New workspace files are executable: commit with `git add --chmod=-x`. App logs and browser checks are the user's (the app rejects PAT auth).

## Decision Log

1. **D1, 2026-11-04, scope:** Plan 44 covers Track A M3, M4 and M5.
2. **D2, 2026-11-04, geometry delivery:** Option A. The two analyze tools take `include_map: bool = False`. By default the `map` block lists layers, legends, sources and vintages with `delivery: "omitted"` and no geometry, so model context stays small. App routes (`/api/geo/screen`, `/api/geo/map` behind "Show on map") call the tool again with `include_map=True` and the tool-card arguments. Server stays stateless.
3. **D3, 2026-11-04, tools:** Only `analyze_farmland_by_polygon` and `analyze_corridor_fppa` take `include_map`. LESA, point lookup and `get_soil_polygons_by_geometry` are unchanged. The map panel stops calling `get_soil_polygons_by_geometry`.
4. **D4, 2026-11-04, contract shape:** Additive. Existing response fields stay as they are. New top-level fields: `schema_version` (`"1.0"`), `data_mode` (`"live"`), `authority` (`level: machine_estimate`, `label`, `official_filing: false`), `map` (`display_crs`, `bounds`, `layers[]`). ADR 0017 records how existing `source`/`manifest`/`limitations` cover section 4's `provenance`, `privacy` and `warnings`.
5. **D5, 2026-11-04, overlays:** Option A. Fixed catalog (SSURGO WMS, TIGERweb counties, TIGERweb urban areas), browser loads them directly, no user URLs. Wave 1 probes from the deployed app origin. A service-specific proxy is added only if the probe fails (and would then be a plan amendment).
6. **D6, 2026-11-04, identify and Use as AOI:** Identify popups for all three overlays. "Use as AOI" for counties and urban areas loads the exact outline; above the existing 2000-vertex cap it shows a clear message and does not simplify.
7. **D7, 2026-11-04, payload bounds:** Option A. Acreage and scoring always use exact geometry. The display copy is simplified with topology preserved at about 1 m in EPSG:6933; each layer records `simplified` and `simplify_tolerance_m`. A per-response GeoJSON cap (default 2 MB) cuts layers with `truncated: true` and a warning. Both are settings.
8. **D8, 2026-11-04, execution and acceptance:** Option C. One Genie Code session runs tasks serially in the workspace clone, one commit per task. Gates per wave as in the wave table. Push and deploy need user approval. Deployed overlay probe (44.1.2) and deployed trials (44.8.1, 44.10.1). A two-axis code review (standards and spec) of the branch runs before close-out.
9. **D9, 2026-11-04, trial targets:** Option A. A new `mcp-fpac-soil-dev` app is deployed from the personal workspace clone on this branch. For trials the agent app tracks `feature/agent-app-map2` and points at the dev server. After merge both go back to `main` and `mcp-fpac-soil`. Refreshing the team-03 clone and redeploying `mcp-fpac-soil` after merge is part of close-out, each step with user approval (confirmed when the user approved this plan, 2026-11-04).

10. **A1, 2026-11-04, amendment (user direction):** both analyzers always call `check_urban_exemption_with_geometries` (with and without `include_map`) instead of branching to the old method; existing tests are amended or added rather than kept on `check_urban_exemption` mocks. `check_urban_exemption` stays for `exemption_tools.py` and the live tests. Polygon tests use a real `TigerwebClient` over `httpx.MockTransport`, so 44.3.1 needs no scope change; corridor tests use `MagicMock(spec=TigerwebClient)`, so 44.3.2 also edits the urban mocks in `tests/test_corridor_analysis.py` and `tests/test_phase3_contracts.py`.

11. **A2, 2026-11-04, amendment (user direction):** the 44.4.1 contract test file is `tests/test_map_tool_contracts.py`, not `tests/test_phase8_contracts.py` (name says what it covers). 44.4.1 also adds `map_simplify_tolerance_m` and `map_max_geojson_bytes` to the README configuration reference, since 44.2.1 added them without docs. The tool layer always passes `include_map` to the analyzers; existing call assertions in `tests/test_tools.py` are amended.

12. **A3, 2026-11-04, amendment (user direction), replaces the trial wiring in D9:** trials use two dev apps and leave both production apps alone. `mcp-fpac-soil-dev` (MEDIUM, no resources) deploys from git, repo root, branch `feature/agent-app-map2`. A dev agent app (proposed name `agent-fpac-soil-dev`, user's choice) deploys from git, `apps/agent-fpac-soil-openai-sdk`, same branch, with resources `mcp_server` -> `mcp-fpac-soil-dev` (CAN_USE), `llm-endpoint` and `experiment` (user's choice of experiment). The agent app picks its MCP server from its `mcp_server` resource: `app.yaml` sets `FPAC_MCP_APP` with `valueFrom: mcp_server` (resolves to the app name), and `config.py` resolves the URL once per process with `WorkspaceClient().apps.get(name).url` + `/mcp`; an explicit `FPAC_MCP_URL` still wins (local runs, tests), then `FPAC_MCP_APP`, then the default. `app.yaml` is the same on every branch, so nothing is reverted at close-out and the production agent app keeps `mcp-fpac-soil` through its own resource. A later dev branch only re-points both dev apps. Unverified: that CAN_USE lets the agent app's service principal call `apps.get` on the server app; the 44.5.2 smoke call checks it (fallback: also grant CAN_VIEW).

13. **A4, 2026-11-05, amendment (user direction, trial 44.8.1):** corridor alternatives report the same farmland class breakdown as the primary alignment (additive fields on `CorridorAlternativeComparison`). With `include_map=true` the `farmland_classes` layer also covers each alternative, clipped to ground outside the primary footprint and earlier alternatives (pieces carry `alignment`, no `area_ac`). Alternative SDA calls follow `include_map` for `return_geom`; numbers are the same with or without the map. Details in `STATE_44.md`.

14. **A5, 2026-11-07, review decisions (user, `REVIEW_44.md`):** fix R1-R3 and R8 in 44.11.2 (docs). Fix R12 in 44.11.3: run the POLY-01 and POLY-02 eval cases ("i do want to make sure those eval cases work"). Accept R4-R6, R9-R11 and R13. Defer R7 (serve the AOI vertex limit from the server), R14 and R15 to `MASTER_PLAN.md` follow-ups at close-out.

15. **A6, 2026-11-07, amendment (user direction: "add show on map"), revises D3 for one tool:** `get_soil_polygons_by_geometry` also takes `include_map: bool = False` (same "Leave false." description) so POLY-02 tool cards get "Show on map". Its existing FeatureCollection keys stay as they are; it gains the same additive `schema_version`, `data_mode`, `authority` and `map` keys, with descriptor-only layers by default, on success and on error. Layers are `aoi` and `farmland_classes` (same id, `style_key` and legend as the analyze tools, so the renderer needs no change); `farmland_classes` is built from the rows already fetched (`features_from_sda_rows`), with simplification and the size cap. No extra upstream call. The app adds the tool to `geo.MAP_TOOLS` and the frontend `MAP_TOOLS`. LESA and point/mukey lookups stay unchanged.

16. **A7, 2026-11-09, amendment (user approved):** result polygons get a click popup from `include_map` data. The `farmland_classes` features of both analyze tools also carry the map unit's `productivity_rating`, `productivity_rating_class` and `productivity_rating_source` (the generic names the response's map units use), copied from the ratings the analyzers already fetch; no new upstream call. Present only when ratings were fetched; `get_soil_polygons_by_geometry` adds none. The map panel opens the identify popup on a click on a drawn farmland polygon (no drawing tool active), with a "Result" section (map unit name, symbol, farmland class, acres, productivity when present) from the feature properties, above any overlay sections. The no-layer hint shows only when a click hits neither. Deferred to `MASTER_PLAN.md` at close-out: component summary (drainage, hydric rating, slope; needs a new SDA query, which `include_map` must not add) and richer SSURGO overlay identify outside a result.

## Wave & Dependency Table

Paths under `frontend/`, `agent_server/` and `tests/` (app) are relative to `apps/agent-fpac-soil-openai-sdk/`; `src/` and root `tests/` are the MCP server.

| Wave | Executor | Task | Title | Files in scope | Depends on |
|---|---|---|---|---|---|
| 1 | Genie Code | 44.1.1 | Draft ADR 0017 map result contract | `docs/decisions/0017-server-map-result-contract.md` (new), `docs/decisions/README.md` | none |
| 1 | User + Genie Code | 44.1.2 | Overlay probe from the deployed app origin | `planning/evidence/44.1.2-overlays.md` (new), `planning/STATE_44.md` | none |
| 2 | Genie Code | 44.2.1 | Map contract module, settings and response fields | `src/fpac_soil_mcp/map_contract.py` (new), `src/fpac_soil_mcp/config.py`, `src/fpac_soil_mcp/models.py`, root `tests/test_map_contract.py` (new) | 44.1.1 |
| 2 | Genie Code | 44.2.2 | TIGERweb urban geometries on request | `src/fpac_soil_mcp/tigerweb_client.py`, root `tests/test_tigerweb_client.py` | none |
| 3 | Genie Code | 44.3.1 | Polygon analyzer map layers | `src/fpac_soil_mcp/polygon_analysis.py`, root `tests/test_polygon_map.py` (new) | 44.2.1, 44.2.2 |
| 3 | Genie Code | 44.3.2 | Corridor analyzer map layers | `src/fpac_soil_mcp/corridor_analysis.py`, root `tests/test_corridor_map.py` (new), root `tests/test_corridor_analysis.py` and `tests/test_phase3_contracts.py` (urban mocks only, amendment A1) | 44.2.1, 44.2.2 |
| 4 | Genie Code | 44.4.1 | Tool parameters, MCP contract tests, tool docs | `src/fpac_soil_mcp/tools/spatial_analysis_tools.py`, root `tests/test_tools.py`, root `tests/test_map_tool_contracts.py` (new), root `README.md` (`## Tool Reference`, L260, and the two map settings in `## Configuration Reference`, A2) | 44.3.1, 44.3.2 |
| 5 | Genie Code | 44.5.1 | App routes: screening from `map`, `/api/geo/map` | `agent_server/geo.py`, `agent_server/start_server.py`, app `tests/test_geo_screen.py`, app `tests/test_geo_map.py` (new) | 44.4.1 |
| 5 | User + Genie Code | 44.5.2 | Dev apps and MCP server lookup (A3) | app `app.yaml`, app `databricks.yml`, `agent_server/config.py`, `agent_server/agent.py`, app `tests/test_deploy_config.py`, app `tests/test_agent_config.py`, app `tests/test_agent_mcp_wiring.py`, app `README.md` (configuration table), `planning/STATE_44.md` | 44.4.1 |
| 6 | Genie Code | 44.6.1 | Generic map layer renderer | `frontend/client/src/components/map/mapLayers.ts` (new), `MapPanel.tsx`, `Legend.tsx`, `useScreening.ts`, `ScreeningResults.tsx`, `ResultsTable.tsx` (all under `components/map/`); `agent_server/geo.py` and app `tests/test_geo_screen.py` (remove `soil_polygons` only) | 44.5.1, 44.5.2 |
| 7 | Genie Code | 44.7.1 | "Show on map" on tool cards | `frontend/client/src/components/message.tsx`, `frontend/client/src/layouts/ChatLayout.tsx`, `components/map/MapResultContext.tsx` (new), `components/map/ShowOnMapButton.tsx` (new), `components/map/MapPanel.tsx` | 44.6.1 |
| 8 | User + Genie Code | 44.8.1 | M4 deployed trial | `planning/evidence/44.8.1-trial.md` (new), `planning/STATE_44.md` | 44.7.1 |
| 8 | Genie Code | 44.8.2 | Overlay catalog and toggles | `components/map/overlays.ts` (new), `components/map/OverlayControl.tsx` (new), `components/map/MapPanel.tsx` | 44.1.2, 44.7.1 |
| 9 | Genie Code | 44.9.1 | Identify popups and Use as AOI | `components/map/identify.ts` (new), `components/map/IdentifyPopup.tsx` (new), `components/map/MapPanel.tsx`, `components/map/geojson.ts` | 44.8.1, 44.8.2 |
| 9 | Genie Code | 44.9.2 | Docs: ADR 0015 local changes, app docs | `docs/decisions/0015-vendored-agent-app-frontend.md`, app `README.md`, app `AGENTS.md` | 44.8.2 |
| 10 | User + Genie Code | 44.10.1 | Final deployed trial (M4 + M5) | `planning/evidence/44.10.1-trial.md` (new), `planning/STATE_44.md` | 44.9.1, 44.9.2 |
| 11 | Genie Code | 44.11.1 | Two-axis code review of the branch | `planning/REVIEW_44.md` (new), `planning/STATE_44.md` | 44.10.1 |
| 11 | Genie Code | 44.11.2 | Review doc fixes | app `AGENTS.md`, `docs/decisions/0016-out-of-band-aoi-screening-handoff.md`, root `.env.example`, `planning/STATE_44.md` | 44.11.1 |
| 11 | Genie Code | 44.11.4 | Map result on `get_soil_polygons_by_geometry` (A6) | `src/fpac_soil_mcp/tools/soil_lookup_tools.py`, root `tests/test_map_tool_contracts.py`, root `tests/test_soil_polygons_map.py` (new), root `README.md` (tool row), ADR 0017 | 44.11.1 |
| 11 | Genie Code | 44.11.5 | "Show on map" for soil polygon cards (A6) | `agent_server/geo.py`, app `tests/test_geo_map.py`, `components/map/ShowOnMapButton.tsx`, app `AGENTS.md`, app `README.md`, ADR 0015 (`message.tsx` entry), ADR 0016 (the 2026-11-07 amendment) | 44.11.4 |
| 11 | Genie Code | 44.11.6 | Productivity on farmland features (A7) | `src/fpac_soil_mcp/map_contract.py`, `polygon_analysis.py`, `corridor_analysis.py`, root `tests/test_map_tool_contracts.py`, ADR 0017 | 44.11.4 |
| 11 | Genie Code | 44.11.7 | Result polygon popup (A7) | `components/map/MapPanel.tsx`, `components/map/IdentifyPopup.tsx`, app `README.md` | 44.11.6 |
| 11 | User + Genie Code | 44.11.3 | POLY-01 and POLY-02 eval cases | `planning/evidence/44.11.3-eval.md` (new), `planning/STATE_44.md` | 44.11.5 |
| 12 | Genie Code + User | 44.12.1 | Close-out | ADR 0017, `docs/decisions/README.md`, `planning/MASTER_PLAN.md`, `planning/SPATIAL_VISUALIZATION_STRATEGY.md` (status note only), `planning/STATE_44.md` | 44.11.1-44.11.7 |
| 13 | Genie Code | 44.13.1 | Code review fix: prioritize checkout src on sys.path | `main.py`, root `tests/test_main_entrypoint.py`, `planning/REVIEW_44.md`, `planning/STATE_44.md` | 44.12.1 |

Same-file tasks are in different waves (`MapPanel.tsx`: 44.6.1, 44.7.1, 44.8.2, 44.9.1; `geo.py`: 44.5.1, 44.6.1; `spatial_analysis_tools.py`: 44.4.1 only), and no task depends on another task in its own wave. Execution is serial anyway (D8); file scopes are disjoint within each wave so a worker-capable tool could run them in parallel. Review findings that need code become numbered fix tasks (44.11.2, 44.11.3, ...) added to this table before close-out.

**Check gates** (serial, fresh `/tmp` clone of the branch head; record in `STATE_44.md`):

- Every wave: root `make check`; `make app-check`.
- Waves 6-9 (frontend) and close-out: `make app-frontend-check`.
- Waves 2-4 (server waves): `make test-live`. The pre-existing SDA "session is in the kill state" failure (`test_live_dynamic_sdv_queries_and_unrated_water_urban`, STATE_43) is recorded, not fixed.

## Hazards

- **Model context (D2):** with `include_map=False` (the default and what the model calls), `map.layers[*]` must have `delivery: "omitted"` and no `feature_collection`. A contract test asserts the default response size stays within a small margin of today's (44.4.1).
- **Exact vs display geometry (D7):** acreage, percentages, LE/SA scores, `geometry_hash` and `tabular_csv` must be identical with `include_map=True` and `False`. Simplification and truncation only touch the display copy. 44.3.1 and 44.3.2 assert this.
- **No extra upstream queries:** `include_map=True` flips `return_geom` on the existing SDA call and reuses the TIGERweb urban geometries already fetched. Do not add SDA or TIGERweb calls. Mocked tests count calls.
- **Additive only (D4):** do not rename, remove or reshape existing response fields. `geo.py` `select_display_analysis`/`build_chat_summary`, the eval cases (`eval/prompt_test_cases.json`) and LESA's use of the corridor result must keep working unchanged.
- **Regulatory notice (ADR 0003):** every rendered result shows the server `regulatory_notice` and authority label; the map never shows "official".
- **Deploy config tests:** `tests/test_deploy_config.py` pins the production MCP resource. After 44.5.2 (A3) it pins `FPAC_MCP_APP` `valueFrom: mcp_server` and the production resource name in `databricks.yml`; the dev apps set their own resources in the UI, so no dev name or URL is committed.
- **Auto-deploy:** while the agent app tracks this branch, every approved push redeploys it. Push only at 44.5.2, 44.8.1, 44.10.1 and close-out unless the user asks. The dev MCP server deploys from the workspace clone path, so redeploy it after server changes; it does not auto-deploy.
- **`aoi_ref` in tool-card arguments:** the model passes the active `aoi_ref` string; substitution happens in the agent server. `/api/geo/map` must accept the browser's active AOI and reuse `aoi_context.substitute_arguments`; never trust a geometry argument the browser did not send.
- **Route allowlist:** `/api/geo/map` accepts only the two analyze tool names, forces `include_map=True`, enforces `MAX_BODY_BYTES`, and returns bounded 4xx/502 errors that never echo arguments.
- **Overlay egress (D5):** URLs come from the fixed catalog in `overlays.ts`; no URL from users, tool output or query strings. If the 44.1.2 probe shows a service cannot be loaded from the app origin, stop and amend the plan (proxy decision) rather than improvising.
- **Vertex cap (D6):** "Use as AOI" counts vertices with the same rule as `geo.py` `count_vertices`; do not simplify.
- **Vendored frontend (ADR 0015):** `message.tsx` and `ChatLayout.tsx` are upstream files; keep edits minimal, enter via grep anchors, and list them in ADR 0015 (44.9.2). Never run upstream `npm run lint`/`lint:fix`. No typecheck gate (upstream fails `tsc`), but new files must not add `tsc` errors.
- **Lockfile:** no new npm dependencies are expected. If one is needed, stop and report.
- **Privacy:** tests use synthetic geometry (`[[0,0],[1,0],[1,1],[0,0]]` style) and the marker `R6-MARKER`; no real coordinates or parcel data in commits, tests, planning or evidence.
- **Large files:** `sda_client.py` (1944), `corridor_analysis.py` (929), `lesa.py` (889), `tigerweb_client.py` (703), `models.py` (599), `message.tsx` (489): enter via grep anchors only.

## Task Specifications

### 44.1.1 -- Draft ADR 0017 map result contract

- **Executor:** Genie Code. **Depends on:** none.
- **Files in scope:** must edit `docs/decisions/README.md`; can create `docs/decisions/0017-server-map-result-contract.md`.
- **Spec:** Write ADR 0017 (`Proposed`, dated, context EXECUTION_PLAN_44) recording D2, D3, D4 and D7: `include_map` default false; which tools; the additive fields; layer schema (`id`, `title`, `kind` polygon/line/point, `delivery` inline_geojson/omitted, `authority`, `source`, `data_vintage`, `style_key`, `legend[]` with `value`/`label`/`color`/`pattern`/`code`, `simplified`, `simplify_tolerance_m`, `truncated`, `feature_count`, `feature_collection`); layer ids (`aoi`, `farmland_classes`, `urban_context`, `corridor_direct`, `corridor_indirect`, `corridor_alternative_<id>`, `county_segments`); a table mapping strategy section 4 fields to existing or new fields; consequences (second query on Show on map; legend colours owned by the server). Add the README index row.
- **Anchors:** `SPATIAL_VISUALIZATION_STRATEGY.md` sections 4-5; ADR 0016 for format; README index table.
- **Acceptance:** ADR renders; README row links resolve (`grep -n 0017 docs/decisions/README.md`); root `make check` unaffected.

### 44.1.2 -- Overlay probe from the deployed app origin

- **Executor:** User + Genie Code. **Depends on:** none.
- **Files in scope:** can create `planning/evidence/44.1.2-overlays.md`; must edit `planning/STATE_44.md`.
- **Spec:** Genie Code parses SSURGO WMS `GetCapabilities` and TIGERweb layer metadata from serverless (layer names, SRS/CRS including EPSG:3857, formats, scale limits, `maxRecordCount`, supported query formats) and writes them to the evidence file. It then writes a short browser-console snippet (fetch + `Image` load) for: one SSURGO `GetMap` tile in EPSG:3857, one SSURGO `GetFeatureInfo` (or WFS point query), one TIGERweb counties and one urban-areas `query` with `f=geojson` and `returnGeometry=true` using a synthetic point. The user runs it in the deployed app's devtools console and pastes the results. Record pass/fail per service, CORS headers and response sizes. If any service fails, stop and raise the proxy decision (D5).
- **Acceptance:** evidence file lists, per service, the exact URL template to use in `overlays.ts`, CORS outcome from the app origin, and limits.

### 44.2.1 -- Map contract module, settings and response fields

- **Executor:** Genie Code. **Depends on:** 44.1.1.
- **Files in scope:** can create `src/fpac_soil_mcp/map_contract.py`, `tests/test_map_contract.py`; must edit `src/fpac_soil_mcp/config.py`, `src/fpac_soil_mcp/models.py`.
- **Spec:** Pydantic models from ADR 0017 (`MapLegendItem`, `MapLayer`, `MapBlock`, `ResultAuthority`). Builders: `farmland_legend()` (colours, patterns and codes from strategy section 5, values matching `categorize_farmland_class` outputs); `build_layer(...)` that takes Shapely geometries plus properties and returns a layer with `delivery` set by `include_map`; `simplify_for_display(geoms, tolerance_m)` (project with `_TO_EQUAL_AREA`, `shapely.simplify(..., preserve_topology=True)` or coverage simplification, project back); `enforce_size_cap(block, max_bytes)` truncating the largest layers last-in-order with `truncated: true` and a warning; `bounds_of(...)`; `features_from_sda_rows(rows)` (WKT `geom` -> GeoJSON features with map-unit properties, ported from `get_soil_polygons_by_geometry`) so 44.3.1 and 44.3.2 share one converter. Settings `map_simplify_tolerance_m: float = 1.0` and `map_max_geojson_bytes: int = 2_000_000` with validators. Add optional fields `schema_version`, `data_mode`, `authority`, `map` to `PolygonFarmlandAnalysisResponse` and `CorridorFarmlandAnalysisResponse` with defaults so existing constructors still validate.
- **Anchors:** `models.py` L162, L275; `config.py` `Field` pattern L17-60 and validators L97-125; `geometry.py` L55-56; `polygon_analysis.py` `categorize_farmland_class` L57.
- **Acceptance:** `uv run pytest tests/test_map_contract.py tests/test_models.py tests/test_config.py -q` passes; tests cover omitted vs inline delivery, simplification flag/tolerance, truncation and warning, legend values, and that existing response constructors validate without the new fields.

### 44.2.2 -- TIGERweb urban geometries on request

- **Executor:** Genie Code. **Depends on:** none.
- **Files in scope:** must edit `src/fpac_soil_mcp/tigerweb_client.py`, `tests/test_tigerweb_client.py`.
- **Spec:** Add `check_urban_exemption_with_geometries(geometry_input) -> tuple[UrbanExemptionRecord, list[tuple[str, Polygon | MultiPolygon]]]` returning urban-area names with geometries from the same request; `check_urban_exemption` delegates and returns only the record. Point inputs return an empty list (no geometry requested today). No new HTTP calls; `UrbanExemptionRecord` unchanged.
- **Anchors:** `check_urban_exemption` L268-375 (`returnGeometry` L312, `urban_geometries` L345-353).
- **Acceptance:** `uv run pytest tests/test_tigerweb_client.py -q` passes; new tests assert one HTTP call, identical record from both methods, geometries returned for polygon input.

### 44.3.1 -- Polygon analyzer map layers

- **Executor:** Genie Code. **Depends on:** 44.2.1, 44.2.2.
- **Files in scope:** must edit `src/fpac_soil_mcp/polygon_analysis.py`; can create `tests/test_polygon_map.py`.
- **Spec:** `analyze_polygon(..., include_map: bool = False)` (and sync/async wrappers). Always set `schema_version`, `data_mode`, `authority`, and a `map` block with layer descriptors. When `include_map`: SDA call uses `return_geom=True`; build `aoi`, `farmland_classes` (per map-unit fragment with `mukey`, `musym`, `muname`, `farmlndcl`, class value, `area_ac`) and `urban_context` (from 44.2.2) layers; simplify and cap per settings; set `bounds`. Error paths keep their current shape plus descriptor-only `map`.
- **Anchors:** `analyze_polygon` L89; SDA call L154-158; urban check L146; response constructions L124 and L441; `get_soil_polygons_by_geometry` (`soil_lookup_tools.py` L176) for WKT -> feature conversion.
- **Acceptance:** `uv run pytest tests/test_polygon_map.py tests/test_polygon_analysis.py -q` passes; tests assert identical acreage/summary/hash/CSV for both flag values, one SDA and one urban call, omitted delivery by default, inline layers when requested.

### 44.3.2 -- Corridor analyzer map layers

- **Executor:** Genie Code. **Depends on:** 44.2.1, 44.2.2.
- **Files in scope:** must edit `src/fpac_soil_mcp/corridor_analysis.py`, `tests/test_corridor_analysis.py` and `tests/test_phase3_contracts.py` (urban mocks only, A1); can create `tests/test_corridor_map.py`.
- **Spec:** `analyze_corridor(..., include_map: bool = False)`. Layers: `corridor_direct`, `corridor_indirect` (if any), `corridor_alternative_<id>` per alternative, `county_segments` (county name/GEOID per segment), `farmland_classes` (direct footprint segments; `return_geom=True` on the existing per-segment SDA calls), `urban_context` (union of per-segment urban geometries from 44.2.2, de-duplicated by name). Simplify and cap. Same always-present fields as 44.3.1.
- **Anchors:** `analyze_corridor` L140; `direct_poly` L200; footprint L256; counties L268-285; per-segment urban L367 and SDA L374-378; alternatives L649-735; final response L911.
- **Acceptance:** `uv run pytest tests/test_corridor_map.py tests/test_corridor_analysis.py tests/test_phase3_contracts.py -q` passes; same invariants as 44.3.1 including call counts.

### 44.4.1 -- Tool parameters, MCP contract tests, tool docs

- **Executor:** Genie Code. **Depends on:** 44.3.1, 44.3.2.
- **Files in scope:** must edit `src/fpac_soil_mcp/tools/spatial_analysis_tools.py`, `tests/test_tools.py`, root `README.md` (tool reference section and the two map settings in the configuration reference, A2); can create `tests/test_map_tool_contracts.py`.
- **Spec:** Add `include_map: bool = False` to both tools with docstrings telling the model to leave it false. Contract tests through the MCP tool layer: descriptor-only by default; inline layers when true; `lesa_evaluation` still attached for corridor; default response JSON size within 10% (or a fixed small byte margin) of the pre-change fixture; strategy section 4 parity table from ADR 0017 asserted field by field. The M3 exit item "soil" fixtures is met by the `farmland_classes` layer (D3 keeps the soil lookup tools unchanged); say so in the test docstring.
- **Anchors:** `spatial_analysis_tools.py` L21, L57, L115, L179; `tests/test_phase3_contracts.py` for fixture style.
- **Acceptance:** root `make check` passes; then wave gate with `make test-live`.

### 44.5.2 -- Dev apps and MCP server lookup (A3)

- **Executor:** User + Genie Code. **Depends on:** 44.4.1.
- **Files in scope:** must edit app `app.yaml` (`FPAC_MCP_URL` -> `FPAC_MCP_APP` `valueFrom: mcp_server`), app `databricks.yml` (same env change; `mcp_server` resource stays `mcp-fpac-soil`), `agent_server/config.py` (lookup), `agent_server/agent.py` (passes the Apps API lookup; a failed lookup runs the turn without tools; scope added during 44.5.2 because `config.py` stays stdlib-only), app `tests/test_deploy_config.py`, app `tests/test_agent_config.py`, app `tests/test_agent_mcp_wiring.py`, app `README.md` (configuration table), `planning/STATE_44.md`.
- **Spec:** Genie Code: `fpac_mcp_url()` returns `FPAC_MCP_URL` when set; else, when `FPAC_MCP_APP` is set, the looked-up app URL + `/mcp` (cached per process; a failed lookup raises a bounded error naming only the env var, never falls back silently to production); else the default. One commit, `feat(agent-app): pick the MCP server from the app resource`. User: creates `mcp-fpac-soil-dev` and the dev agent app as in A3, holds the dev agent app's first deploy until the push, approves the push. Record app names, URLs, deployment ids and a direct `include_map` smoke call through the dev server.
- **Acceptance:** `make app-check` passes; `apps get` shows both dev apps RUNNING on the branch head; the dev agent app reaches `mcp-fpac-soil-dev` (smoke call returns a `map` block); the production agent app is unchanged.

### 44.5.1 -- App routes: screening from `map`, `/api/geo/map`

- **Executor:** Genie Code. **Depends on:** 44.4.1.
- **Files in scope:** must edit `agent_server/geo.py`, `agent_server/start_server.py`, app `tests/test_geo_screen.py`; can create app `tests/test_geo_map.py`.
- **Spec:** `screen_aoi` makes one call (`analyze_farmland_by_polygon` with `include_map=True`) and returns `display.map` (the server block, unchanged); `chat_summary` unchanged. Keep `display.soil_polygons`, now filled from the `farmland_classes` layer features, so the current frontend still works if 44.5.2 deploys before 44.6.1; 44.6.1 removes it. New `POST /api/geo/map`: body `{tool, arguments, active_aoi?}`; allowlist the two analyze tools; parse `active_aoi` with `parse_active_aoi` and apply `substitute_arguments`; force `include_map=True`; return `{tool, map, regulatory_notice, authority}`; bounded errors (400 invalid, 413 too large, 502 MCP failure) that never echo arguments.
- **Anchors:** `geo.py` `screen_aoi` L308, `_call_tool_untraced` L298, `parse_tool_result` L127, `MAX_BODY_BYTES` L25; `start_server.py` L32; `aoi_context.py` L44, L116; fake MCP fixture in `tests/test_geo_screen.py`.
- **Acceptance:** `make app-check` passes; tests cover single call, allowlist rejection, `aoi_ref` substitution, forced flag, size limit, and the `R6-MARKER` never appearing in error bodies.

### 44.6.1 -- Generic map layer renderer

- **Executor:** Genie Code. **Depends on:** 44.5.1, 44.5.2.
- **Files in scope:** can create `components/map/mapLayers.ts`; must edit `components/map/MapPanel.tsx`, `Legend.tsx`, `useScreening.ts`, `ScreeningResults.tsx`, `ResultsTable.tsx`, `agent_server/geo.py` (drop `display.soil_polygons` only), app `tests/test_geo_screen.py`.
- **Spec:** TypeScript types for the ADR 0017 block. `mapLayers.ts` adds/removes one MapLibre source and fill/line/circle layers per server layer, styled by `style_key` + legend (colour plus pattern/code per strategy section 5, reusing `farmlandClasses.ts` patterns), z-ordered AOI on top. Legend renders from server legends; show "simplified for display" and "partial layer" notes, source, vintage, authority label and `regulatory_notice`. Replace the hard-coded `soil` source path with the generic renderer, and remove `display.soil_polygons` from `geo.py` and `tests/test_geo_screen.py`. Omitted layers list as "not loaded".
- **Anchors:** `MapPanel.tsx` L108-127, L199-230; `Legend.tsx`; `useScreening.ts` `ScreeningResponse` L32.
- **Acceptance:** `make app-frontend-check` and `make app-check` pass; no new `tsc` errors in `components/map/**` (`npx tsc --noEmit -p client` filtered to the folder).

### 44.7.1 -- "Show on map" on tool cards

- **Executor:** Genie Code. **Depends on:** 44.6.1.
- **Files in scope:** must edit `frontend/client/src/components/message.tsx`, `frontend/client/src/layouts/ChatLayout.tsx`, `components/map/MapPanel.tsx`; can create `components/map/MapResultContext.tsx`, `components/map/ShowOnMapButton.tsx`.
- **Spec:** `MapResultContext` holds the result currently shown (screening or tool card) and is provided in `ChatLayout` next to the active-AOI provider. For completed MCP tool parts named `analyze_farmland_by_polygon` or `analyze_corridor_fppa`, render `ShowOnMapButton` in the tool card; it posts tool name, the card's arguments and the active AOI to `/api/geo/map`, opens the map panel if collapsed, and hands the block to `MapResultContext`; MapPanel renders it with the 44.6.1 renderer and fits bounds. Loading, error and "not available" states.
- **Anchors:** `message.tsx` ~L356 `ToolPartRenderer`, ~L401 `McpTool`; `ChatLayout.tsx` provider block; `ActiveAoiContext.tsx` as the context reference.
- **Acceptance:** `make app-frontend-check` passes; `make app-check` passes; no new `tsc` errors in touched files.

### 44.8.1 -- M4 deployed trial

- **Executor:** User + Genie Code. **Depends on:** 44.7.1.
- **Files in scope:** can create `planning/evidence/44.8.1-trial.md`; must edit `planning/STATE_44.md`.
- **Spec:** After an approved push and dev MCP redeploy, the user runs: draw AOI -> Run screening (farmland, urban layers, legend, notice); ask the agent for a polygon screening and a two-alternative corridor screening -> Show on map on each card. Genie Code checks traces in the experiment for tool calls with `include_map` false from the model and true from the app routes, and records trace ids and outcomes.
- **Acceptance:** M4 exit criterion met (polygon, urban and corridor results render from MCP output with legends, tables, source/vintage, authority and notice) or failures recorded as fix tasks.

### 44.8.2 -- Overlay catalog and toggles

- **Executor:** Genie Code. **Depends on:** 44.1.2, 44.7.1.
- **Files in scope:** can create `components/map/overlays.ts`, `components/map/OverlayControl.tsx`; must edit `components/map/MapPanel.tsx`.
- **Spec:** Fixed catalog from 44.1.2 URL templates: SSURGO WMS raster (with min zoom from capabilities), TIGERweb counties and urban areas (raster export or vector query per probe findings), each with title, attribution, source, vintage and "context layer, not an analysis result" label. Toggle control (keyboard accessible), off by default, per-layer loading and error state, overlays drawn below result layers.
- **Anchors:** `MapPanel.tsx` `BASE_STYLE` L27 and tile error handling L53; evidence file.
- **Acceptance:** `make app-frontend-check` passes; no new `tsc` errors in touched files; catalog URLs are string constants (grep shows no URL built from user input).

### 44.9.1 -- Identify popups and Use as AOI

- **Executor:** Genie Code. **Depends on:** 44.8.1, 44.8.2.
- **Files in scope:** can create `components/map/identify.ts`, `components/map/IdentifyPopup.tsx`; must edit `components/map/MapPanel.tsx`, `components/map/geojson.ts`.
- **Spec:** When an overlay is on and the map is in static (not drawing) mode, a click queries the visible overlays (SSURGO `GetFeatureInfo`/WFS per probe; TIGERweb `query` at the point) and shows name/symbol/class or name/GEOID/vintage. County and urban results show "Use as AOI": fetch the exact outline (`returnGeometry=true`, no `maxAllowableOffset`), count vertices with the `geo.py` rule (port to `geojson.ts`), and above 2000 show a clear message; otherwise set it as the active AOI via `replaceAoi`.
- **Anchors:** `MapPanel.tsx` `replaceAoi` L64, mode state L50; `geojson.ts` `toPolygonGeometry`; `geo.py` `count_vertices` L93.
- **Acceptance:** `make app-frontend-check` passes; no new `tsc` errors in touched files.

### 44.9.2 -- Docs: ADR 0015 local changes, app docs

- **Executor:** Genie Code. **Depends on:** 44.8.2.
- **Files in scope:** must edit `docs/decisions/0015-vendored-agent-app-frontend.md`, app `README.md`, app `AGENTS.md`.
- **Spec:** Add `message.tsx`, `ChatLayout.tsx` (provider) and the new map files to the local-changes list; document `/api/geo/map`, overlays, identify and Use as AOI, and the dev-server trial setup.
- **Acceptance:** root `make check` passes (docs only); links resolve.

### 44.10.1 -- Final deployed trial (M4 + M5)

- **Executor:** User + Genie Code. **Depends on:** 44.9.1, 44.9.2.
- **Files in scope:** can create `planning/evidence/44.10.1-trial.md`; must edit `planning/STATE_44.md`.
- **Spec:** Repeat 44.8.1 steps, plus: toggle each overlay; identify on each; Use as AOI on a small urban area (passes) and a large county (clear over-cap message); screen the selected AOI. Record outcomes and trace ids.
- **Acceptance:** M4 and M5 exit criteria met, or failures recorded as fix tasks.

### 44.11.1 -- Two-axis code review of the branch

- **Executor:** Genie Code. **Depends on:** 44.10.1.
- **Files in scope:** can create `planning/REVIEW_44.md`; must edit `planning/STATE_44.md`, this plan's wave table (fix tasks only).
- **Spec:** Review `origin/main...feature/agent-app-map2` on two independent passes: Standards (root and app `AGENTS.md`, ADRs 0003, 0010-0017, repo style) and Spec (this plan's Goal & Scope, D1-D9, master plan M3-M5 exit criteria). Report findings side by side with severity. Findings that need code become fix tasks 44.11.2+ with their own specs.
- **Acceptance:** review file exists; every finding is fixed, accepted by the user, or deferred with a reason.

### 44.11.2 -- Review doc fixes

- **Executor:** Genie Code. **Depends on:** 44.11.1.
- **Files in scope:** must edit app `AGENTS.md`, `docs/decisions/0016-out-of-band-aoi-screening-handoff.md`, root `.env.example`, `planning/STATE_44.md`.
- **Spec:** R1: the app `AGENTS.md` `geo.py` entry says `/api/geo/screen` makes one MCP call (`analyze_farmland_by_polygon` with `include_map=True`). R2: ADR 0016 gets a dated amendment (original text kept): the screening route makes that one call, and `display.map` (the ADR 0017 block) replaces `get_soil_polygons_by_geometry` and the clipped soil FeatureCollection. R3: `.env.example` lists `MAP_SIMPLIFY_TOLERANCE_M=1.0` and `MAP_MAX_GEOJSON_BYTES=2000000`, commented out like the other optional settings. R8 (A4 in the Decision Log) was recorded with A5.
- **Acceptance:** `grep -n "two MCP calls" apps/agent-fpac-soil-openai-sdk/AGENTS.md` empty; `grep -n MAP_ .env.example` shows both; root `make check` and `make app-check` pass.

### 44.11.3 -- POLY-01 and POLY-02 eval cases

- **Executor:** User + Genie Code. **Depends on:** 44.11.1.
- **Files in scope:** can create `planning/evidence/44.11.3-eval.md`; must edit `planning/STATE_44.md`.
- **Spec:** The M4 exit row names POLY-01 (`analyze_farmland_by_polygon`) and POLY-02 (`get_soil_polygons_by_geometry`) from `eval/prompt_test_cases.json`. (1) Genie Code runs the T1 eval for both cases (`make eval-databricks ARGS="--cases POLY-01,POLY-02"`) and records the run id and per-scorer results. (2) The user sends both prompts in the dev agent app. For POLY-01, "Show on map" on the tool card draws the `aoi`, `farmland_classes` and `urban_context` layers with legend, source, authority and notice. For POLY-02, "Show on map" (A6, 44.11.5) draws `aoi` and `farmland_classes` the same way. Record trace ids and outcomes.
- **Acceptance:** both cases pass the T1 scorers or failures are recorded as fix tasks; both cards render on the map.

### 44.11.4 -- Map result on `get_soil_polygons_by_geometry` (A6)

- **Executor:** Genie Code. **Depends on:** 44.11.1.
- **Files in scope:** must edit `src/fpac_soil_mcp/tools/soil_lookup_tools.py`, root `tests/test_map_tool_contracts.py` (move the tool from `UNCHANGED_TOOLS` to the schema check, fix the module docstring), root `README.md` (tool reference row), `docs/decisions/0017-server-map-result-contract.md` (fold A6 into the main text; the ADR is still Proposed on this branch); can create root `tests/test_soil_polygons_map.py`.
- **Spec:** As A6. `include_map: IncludeMap = False` (reuse `spatial_analysis_tools.IncludeMap`). One SDA call, as now. The `farmland_classes` title says when polygons are full survey polygons (`clip=False`). Error paths return descriptor-only `map`.
- **Anchors:** `soil_lookup_tools.py` `get_soil_polygons_by_geometry`; `polygon_analysis.py` `_polygon_map` (reference); `map_contract.py` `build_layer`, `build_map_block`, `features_from_sda_rows`, `ResultAuthority`, `MAP_SCHEMA_VERSION`.
- **Acceptance:** `uv run pytest tests/test_soil_polygons_map.py tests/test_map_tool_contracts.py tests/test_tools.py -q` passes; tests cover descriptors by default, inline layers when true, one SDA call, existing keys and features unchanged for both flag values, error paths; root `make check` (fresh `/tmp` clone) and `make test-live` pass.

### 44.11.5 -- "Show on map" for soil polygon cards (A6)

- **Executor:** Genie Code. **Depends on:** 44.11.4.
- **Files in scope:** must edit `agent_server/geo.py` (`MAP_TOOLS`, `MapRequest`), app `tests/test_geo_map.py`, `frontend/client/src/components/map/ShowOnMapButton.tsx` (`MAP_TOOLS`), app `AGENTS.md`, app `README.md`, `docs/decisions/0015-vendored-agent-app-frontend.md` (`message.tsx` entry), `docs/decisions/0016-out-of-band-aoi-screening-handoff.md` (the 2026-11-07 amendment written on this branch).
- **Spec:** Add `get_soil_polygons_by_geometry` to both allowlists; `/api/geo/map` substitutes `aoi_ref` in `geojson` and forces `include_map=True` as for the others. Docs say "the map tools" instead of "the two analyze tools" where they describe the allowlist.
- **Acceptance:** `make app-check` and `make app-frontend-check` pass (fresh `/tmp` clone); a test asserts the soil tool is accepted with substitution and the forced flag; no new `tsc` errors in `components/map/`.

### 44.11.6 -- Productivity on farmland features (A7)

- **Executor:** Genie Code. **Depends on:** 44.11.4.
- **Files in scope:** must edit `src/fpac_soil_mcp/map_contract.py` (`features_from_sda_rows` passes the three productivity keys through when a row has them; a `with_productivity(rows, ratings)` helper), `polygon_analysis.py`, `corridor_analysis.py` (primary segments and alternatives), root `tests/test_map_tool_contracts.py`, `docs/decisions/0017-server-map-result-contract.md` (feature properties).
- **Acceptance:** for both tools with `include_map=True`, each `farmland_classes` feature's productivity values equal the response map unit's for the same mukey; SDA call counts unchanged; default responses unchanged; root `make check` and `make test-live` pass (fresh `/tmp` clone).

### 44.11.7 -- Result polygon popup (A7)

- **Executor:** Genie Code. **Depends on:** 44.11.6.
- **Files in scope:** must edit `components/map/MapPanel.tsx`, `components/map/IdentifyPopup.tsx`, app `README.md`.
- **Spec:** query the rendered `result-farmland_classes-fill` features at the click; values shown as sent (no browser re-classification). One popup for result and overlay sections.
- **Acceptance:** `make app-frontend-check` passes; no new `tsc` errors in `components/map/`; user browser check.

### 44.12.1 -- Close-out

- **Executor:** Genie Code + User. **Depends on:** 44.11.1 and fix tasks.
- **Files in scope:** must edit ADR 0017, `docs/decisions/README.md`, `planning/MASTER_PLAN.md` (Phase 8 and Track A status), `planning/SPATIAL_VISUALIZATION_STRATEGY.md` (one status note pointing to ADR 0017), `planning/STATE_44.md`.
- **Spec:** ADR 0017 -> `Accepted`. Mark M3-M5 delivered and list remaining Phase 8 items. Final gate (all suites). User approves push and merges. After merge: the production agent app redeploys from `main` (its `mcp_server` resource already names `mcp-fpac-soil`); with user approval, refresh the team-03 clone to `main` and redeploy `mcp-fpac-soil`; the dev apps stay for the next dev branch or are stopped (user decision).
- **Acceptance:** `grep -n mcp-fpac-soil-dev` finds nothing outside planning and app docs; all gates green; `apps get` for both production apps shows the merged commit.

### 44.13.1 -- Code review fix: prioritize checkout src on sys.path

- **Executor:** Genie Code. **Depends on:** 44.12.1.
- **Files in scope:** must edit `main.py`, root `tests/test_main_entrypoint.py`, `planning/REVIEW_44.md`, `planning/STATE_44.md`.
- **Spec:** C1 (Copilot). `main.py` removes any existing occurrence of `SRC_DIR` from `sys.path` and inserts it at index 0 unconditionally when the directory exists, so a stale installed package ahead of the checkout never wins. Add a test that puts `SRC_DIR` on `sys.path` behind another path, runs `main.py`, and asserts it ends up at index 0; the existing no-duplicate test must still pass.
- **Acceptance:** new test fails before the fix and passes after; root `make check` (fresh `/tmp` clone) passes at baseline plus the new test.
