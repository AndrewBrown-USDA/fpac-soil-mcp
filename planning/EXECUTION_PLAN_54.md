# EXECUTION PLAN 54: Agent-App Map Usability and Corridor Workflow

## Goal & Scope

### Goal

Make the agent-app map more compact and interpretable, then support corridor workflows that users can screen from the map or hand off to chat. Preserve the existing polygon AOI workflow, preliminary-screening boundary, stateless app/server design, fixed service URLs, and server-owned map-result symbology.

### In scope

- G42: compact icon-only map controls with accessible hover/focus labels, a crosshair cursor for drawing/measurement, and miles as the default measurement unit.
- G43: a compact map-pane legend for the current server-provided screening map block, plus an accessible CDL code/color key using the official USDA NASS legend.
- G49: replace the existing fixed USGS NAIP context source with the user's fixed USDA FPAC `conus_naip` ImageServer URL; keep the fixed export request and record the service metadata caveat.
- G44: ensure returned SSURGO farmland-result polygons are visible by default when new screening results arrive; keep the separate SSURGO context overlay independent.
- G45–G48: amend ADR 0016 for corridor context separate from polygon AOI; validated stateless direct map corridor screening and chat handoff; draw/edit a primary centerline, alternatives, and indirect/staging polygons; submit a required buffer distance (blank initially) in feet by default, clearly defined as distance on each side. Keep map screening preliminary and do not collect Site Assessment inputs.
- User requested both direct map screening and the current-style per-conversation chat handoff for corridor inputs.

### Out of scope

- Changes to the MCP server tool/schema, corridor calculations, regulatory rules, or official FPPA/LESA determinations.
- Site Assessment interviews or inputs in the map corridor workflow; alternatives/staging calculations remain the existing tool's responsibility.
- A polygon AOI being replaced by, or silently converted into, corridor geometry; corridor context remains separate.
- Any user-configurable/dynamic service URL, any NAIP endpoint other than the specifically requested fixed USDA FPAC URL, guessed CDL colors, browser reconstruction of server screening layers, new dependencies, deployment/trial, or remote Git actions.
- Work outside the agent-app map/UI and the explicitly required app-server corridor route/context and ADR updates.

### User-stated constraints

> “the buttons are too large and take up too much space.”

> “we need to switch to a different mouse cursor icon like a two-perpendicular line + symbol type instead of a dragging hand.”

> “it would be good to support drawing line features and buffering them.”

> “the results tab works but it appears the ssurgo polygons are not on by default when they return.”

> “i think we need to do something that makes a legend visibble on the map pane it does not help to have it in results.”

> “similarly we do not seem to have any way to identify what the CDL colors are.”

> “it would be nice to reduce button size with each having just an icon and a hover.”

> “default measure distance is miles.”

The user confirmed usability-first ordering; chose returned SSURGO result polygons (not the context overlay); approved amending ADR 0016; chose corridor mode separate from polygon AOI; selected primary centerline, alternatives, and staging geometry; wants both direct map screening and chat handoff; chose automatic per-chat corridor attachment with a separate detach control; selected a blank buffer distance with feet selected, where distance is on each side; map corridor screening stays preliminary and excludes Site Assessment inputs.

> “can we replace NAIP imageserver with https://apps.geo.fpac.usda.gov/geo-imagery/rest/services/naip/conus_naip/ImageServer”

The user approved using this exact endpoint despite the service metadata's `Purpose: test:202407180638 naip service` label; retain that as a deployment/availability caveat.

## Decision Log

| ID | Decision | Rationale / source |
|---|---|---|
| D1 | Continue on `feature/local-dev-trial`, clean at `d4fefd7`; Plan 54 follows Plan 53. | Current repository state and completed orchestration. |
| D2 | Start with G42 compact controls/cursor/miles, then map legends, then returned SSURGO visibility, then corridor foundations and UI. | User asked to start with G42 and prioritize usability. |
| D3 | SSURGO default means returned server farmland-result polygons; do not turn on the separate SSURGO context overlay automatically. | User selected returned result polygons. Existing `resultsVisible` starts true but is not reset for each new result, so reproduce and test the return path. |
| D4 | Corridor inputs are a separate per-chat context from polygon `active_aoi`; support primary centerline, alternatives, and indirect/staging Polygon or MultiPolygon geometry. | User approved ADR 0016 amendment, separate workflow, and all three input types. Existing MCP tool already accepts these inputs. |
| D5 | Support both direct map submission and automatic per-conversation chat handoff; show attach state and allow detach. | User said it should work “both ways like the current polygon workflow does” and approved mirroring its attachment behavior. |
| D6 | Corridor buffer is required (blank initially), unit defaults to feet; display that distance applies on each side. Measure tool independently defaults to miles. | User chose blank/feet for corridor buffer; tool docstring defines per-side semantics. |
| D7 | Direct map corridor call is stateless and untraced, sets `include_map=True`, and does not submit Site Assessment inputs. Preserve preliminary notice and use only the existing `analyze_corridor_fppa` tool. | ADRs 0003, 0016, 0017; user confirmed preliminary-only map screening. |
| D8 | CDL class names/codes/colors come from USDA NASS's published code/name/RGB table; no colors inferred from rendered raster pixels. | Official source verified: <https://nass.usda.gov/research-and-science/cropland/docs/cdl-legend-colors>. |
| D9 | Replace NAIP with fixed `https://apps.geo.fpac.usda.gov/geo-imagery/rest/services/naip/conus_naip/ImageServer/exportImage?...`; use dynamic exportImage, not cached XYZ tiles. | User supplied exact base URL; metadata and an image export probe verified compatibility. Metadata labels purpose `test:202407180638 naip service`; user approved proceeding with caveat. |
| D10 | At most two workers concurrently; same-file tasks are sequenced. | Carry forward the user-approved Plan 53 limit. |
| D11 | Track planning files and commit planning-only updates separately with `docs(planning):`; no implementation begins before plan approval. | User carried forward the Plan 53 convention. |
| D12 | Preserve ADR 0003 preliminary authority; update ADR 0015 local-change ledger for every vendored frontend path; amend ADR 0016; preserve ADR 0017 server-owned map block/legend contract and vector-over-raster ordering. | Accepted constraints and explicit scope. |

## Reconnaissance and Hazards

- Repo `/home/andrew/work/fpac-soil-mcp`; clean branch `feature/local-dev-trial` at `d4fefd7`. Plan 53 is the latest orchestration; Plan 54 is next. `planning/` is tracked and not ignored.
- Baseline at this exact commit is recorded in `STATE_53.md`: `make check` 993 passed/3 skipped/45 deselected; `make app-check` 266 passed; `make app-frontend-check` passed. Existing frontend warnings/advisories are listed in `STATE_53.md`; no baseline rerun needed before planning.
- Follow root `AGENTS.md` and `apps/agent-fpac-soil-openai-sdk/AGENTS.md`. The vendored frontend is under `apps/agent-fpac-soil-openai-sdk/frontend`; every modified/added frontend path must be recorded in ADR 0015.
- Hotspots: `MapPanel.tsx` 894 lines; `geo.py` 448; `aoi_context.py` 144; `OverlayControl.tsx` 152; `Legend.tsx` 153. Use grep anchors and sequence every task that edits `MapPanel.tsx`, `geo.py`, `agent.py`, `chat.tsx`, or ADR 0015.
- Existing focused frontend commands: `npm run test:map-identify`, `npm run test:map-tabs`, `npm run test:site-assessment`, `npm run test:chat-export`; Node helper tests use `node --import tsx --test <files>`. Playwright fixtures used so far mirror UI logic and may not mount production MapPanel; prefer testable helpers and document limits.
- Current `MapPanel.tsx` results visibility starts true, but remains user-toggle state across new screenings. It renders the server map block below `aoi-line`; task 54.3.1 must test a newly returned result and map revisit rather than conflate it with the SSURGO context overlay.
- `OverlayControl.tsx` owns fixed context overlays; `Legend.tsx` renders server-owned `MapBlock` legends. `mapLayers.ts` is the ADR 0017 renderer; never recreate analysis classes client-side.
- Official NASS CDL legend page supplies class codes, class names, and RGB/hex values; bundle a provenance note and keep the UI compact/searchable or collapsible. The CDL imagery remains contextual, not analysis evidence.
- Current NAIP overlay points to USGS National Map. The requested USDA FPAC ImageServer metadata reports currentVersion 10.91, CONUS extent, MosaicDataset source, 4 bands, dynamic image capability, and no cached `tileInfo`; its service description says “latest NAIP” but also labels purpose `test:202407180638 naip service`. A fixed EPSG:3857 `exportImage` GET returned HTTP 200 `image/png`; with an `Origin` header it returned `Access-Control-Allow-Origin` for that origin. Use fixed exportImage only and retain the test-purpose caveat; do not add a default live-network test.
- `analyze_corridor_fppa` in `src/fpac_soil_mcp/mcp/tools/spatial_analysis_tools.py` accepts `centerline`, positive `buffer_distance`, `buffer_units` (`feet`, `meters`, `miles`), optional `indirect_geometry`, alternatives, and `include_map`; distance is applied on each side. The MCP server is not in scope.
- App `geo.py` already has stateless untraced calls, `/api/geo/screen`, and `/api/geo/map`; the map tool allowlist includes corridor. `/api/geo/map` returns only map/status metadata, not a corridor screening summary, so a dedicated bounded corridor-screen route is required for the direct workflow.
- ADR 0016 currently restricts `active_aoi` to Polygon/MultiPolygon and substitution to `geojson`/`geometry`; do not widen or overload that contract. Introduce a separately validated active corridor reference and substitute only for `analyze_corridor_fppa`.
- Chat context transport is split across `client/src/components/chat.tsx`, `packages/core/src/schemas/chat.ts`, `packages/ai-sdk-providers/src/providers-server.ts`, and `server/src/routes/chat.ts`. Existing active AOI context is per-chat sessionStorage and sent through a request-scoped registry.
- Preserve privacy/log hygiene: route corridor geometry through the same no-body/no-payload-logging untraced map path; repository examples use synthetic coordinates only. Chat corridor geometry follows ADR 0016's existing operational-data/tracing caveat.
- No new dependencies; no pushes, deployments, PR operations, or live app trial.

## Wave Table

| Wave | Theme | Tasks | Dependencies |
|---|---|---|---|
| 1 | Usability foundation | 54.1.1 compact icon controls, accessible labels, crosshair, miles default | None |
| 2 | Map interpretation and fixed NAIP source | 54.2.1 map-pane server legend/CDL key; then 54.2.2 fixed USDA FPAC NAIP endpoint | 54.1.1; 54.2.2 follows 54.2.1 because both edit OverlayControl/ADR 0015 |
| 3 | Returned soil visibility | 54.3.1 ensure new screening result polygons display by default | 54.2.1 |
| 4 | Corridor contract | 54.4.1 ADR 0016 amendment and validated corridor context model | 54.3.1 |
| 5 | App-server corridor pathways | 54.5.1 direct map corridor route; 54.5.2 chat agent corridor substitution | 54.4.1; disjoint implementation files |
| 6 | Chat transport | 54.6.1 per-chat browser corridor context and custom-input transport | 54.5.2 |
| 7 | Corridor drawing | 54.7.1 draw/edit primary and alternative lines, staging polygons, buffer settings, attach/detach | 54.6.1 |
| 8 | Map corridor screening | 54.8.1 direct submit, returned corridor map/result display, map/results navigation | 54.5.1, 54.7.1 |
| 9 | Integrated validation/handoff | Serial app/frontend gates, focused suites, ADR/privacy review | All implementation tasks |

At most two workers concurrently. Wave 5 tasks use disjoint files. All MapPanel edits are sequenced. Tasks 54.2.1 and 54.2.2 are sequential because they both edit `OverlayControl.tsx` and ADR 0015. If an out-of-scope file is required, amend this plan first.

## Task Specifications

### 54.1.1 — Compact accessible map controls and cursor defaults

- **Repo:** `/home/andrew/work/fpac-soil-mcp`
- **Must edit:** `apps/agent-fpac-soil-openai-sdk/frontend/client/src/components/map/MapPanel.tsx`, `docs/decisions/0015-vendored-agent-app-frontend.md`.
- **Can create:** `apps/agent-fpac-soil-openai-sdk/frontend/client/src/components/map/mapToolbar.test.ts`, `apps/agent-fpac-soil-openai-sdk/frontend/client/src/components/map/map-toolbar-fixture.tsx`, `apps/agent-fpac-soil-openai-sdk/frontend/client/map-toolbar-fixture.html`, `apps/agent-fpac-soil-openai-sdk/frontend/playwright.map-toolbar.config.ts`, `apps/agent-fpac-soil-openai-sdk/frontend/tests/map-toolbar/toolbar.spec.ts`, and the test-script entry in `apps/agent-fpac-soil-openai-sdk/frontend/package.json`; temp files only under `/tmp/opencode/`.
- **Depends on:** none.
- **Specification:** Convert space-consuming map action buttons to compact icon-only controls with accessible names and hover/focus labels; retain keyboard operation and visible focus. Use a crosshair cursor during drawing and measurement, restoring the normal cursor on exit. Set measurement unit initial state to miles, preserving selectable units. Avoid changing AOI or server contracts.
- **Do not touch:** server files, corridor behavior, layer URLs/order, screening calculations, or unrelated chat UI.
- **Grep anchors:** toolbar `toolButton`, `chooseMode`, TerraDraw mode effects, measurement mode, distance unit selector, and map container in `MapPanel.tsx`.
- **Reference implementations:** existing `lucide-react` toolbar icons, `components/ui/tooltip.tsx` and its use in `chat-header.tsx`, accessible `OverlayControl` buttons, existing `distance.ts` unit type.
- **Acceptance:** focused tests assert accessible labels/tooltips, crosshair activation/restoration, and miles default; run `npm run test:map-toolbar` and `npm run test:map-identify`. Orchestrator runs frontend lint/build.

### 54.2.1 — Show server and CDL legends in the map pane

- **Repo:** `/home/andrew/work/fpac-soil-mcp`
- **Must edit:** `apps/agent-fpac-soil-openai-sdk/frontend/client/src/components/map/MapPanel.tsx`, `apps/agent-fpac-soil-openai-sdk/frontend/client/src/components/map/Legend.tsx`, `apps/agent-fpac-soil-openai-sdk/frontend/client/src/components/map/OverlayControl.tsx`, `docs/decisions/0015-vendored-agent-app-frontend.md`.
- **Can create:** `apps/agent-fpac-soil-openai-sdk/frontend/client/src/components/map/CDLLegend.tsx`, `apps/agent-fpac-soil-openai-sdk/frontend/client/src/components/map/cdlLegend.ts`, `apps/agent-fpac-soil-openai-sdk/frontend/client/src/components/map/cdlLegend.test.ts`, `apps/agent-fpac-soil-openai-sdk/frontend/client/src/components/map/map-legend-fixture.tsx`, `apps/agent-fpac-soil-openai-sdk/frontend/client/map-legend-fixture.html`, `apps/agent-fpac-soil-openai-sdk/frontend/playwright.map-legend.config.ts`, `apps/agent-fpac-soil-openai-sdk/frontend/tests/map-legend/legend.spec.ts`, and a named script in `apps/agent-fpac-soil-openai-sdk/frontend/package.json`.
- **Depends on:** 54.1.1.
- **Specification:** Add a compact, accessible, collapsible map-pane legend for the active screening/tool result, using the existing server `MapBlock` values unchanged. Add a CDL key that identifies official NASS code/name/color values and is available when CDL context is shown. Keep context/analysis distinction explicit; do not derive classes or colors from pixels. Preserve attribution and support narrow viewports.
- **Do not touch:** backend map data, server legend values, CDL analysis, service URLs, regulatory copy, or raster/vector ordering.
- **Grep anchors:** `MapLegend` and `LegendSwatch` in `Legend.tsx`; `shown`, `screeningMap`, map container and overlay controls in `MapPanel.tsx`; `OVERLAYS` and CDL toggle in `OverlayControl.tsx`.
- **Reference implementations:** ADR 0017 server map block; NASS official CDL legend at `https://nass.usda.gov/research-and-science/cropland/docs/cdl-legend-colors`.
- **Acceptance:** focused tests verify server legend entries are passed/rendered unchanged, representative and edge CDL code/name/hex records match the official table, and legend is available in the map pane with accessible names. Run `npm run test:map-legend` and `npm run test:map-identify`.

### 54.2.2 — Replace NAIP with the fixed USDA FPAC ImageServer

- **Repo:** `/home/andrew/work/fpac-soil-mcp`
- **Must edit:** `apps/agent-fpac-soil-openai-sdk/frontend/client/src/components/map/overlays.ts`, `apps/agent-fpac-soil-openai-sdk/frontend/client/src/components/map/OverlayControl.tsx`, `docs/decisions/0015-vendored-agent-app-frontend.md`.
- **Can create:** none; extend `apps/agent-fpac-soil-openai-sdk/frontend/client/src/components/map/overlays.test.ts`.
- **Depends on:** 54.2.1; sequential file ownership.
- **Specification:** Replace the NAIP source with the exact fixed base URL `https://apps.geo.fpac.usda.gov/geo-imagery/rest/services/naip/conus_naip/ImageServer`; construct a fixed `exportImage` URL using MapLibre's EPSG:3857 bbox placeholder, fixed bbox/output spatial references, size, PNG format, and image response. Update source, attribution, vintage/availability notes and retain default-off behavior, zoom/loading/error isolation, and source-ID mapping. Record ADR 0015 changes. Do not assert that a test-labeled service is production-ready.
- **Do not touch:** other overlay URLs, dynamic/user-configurable URLs, CDL analysis/symbology, `MapPanel.tsx`, server code, or dependencies.
- **Grep anchors:** `NAIP_TILES`, NAIP catalog record and `overlaySourceId` in `overlays.ts`; NAIP flag/control in `OverlayControl.tsx`; ADR 0015 local-change ledger.
- **Reference implementations:** existing fixed ImageServer request construction; USDA FPAC service metadata at the provided ImageServer `?f=pjson` and the fixed export request verified during planning.
- **Acceptance:** `overlays.test.ts` asserts exact endpoint/request shape, no `/tile/` assumption, source/attribution/vintage caveat and source-ID mapping; run `node --import tsx --test client/src/components/map/overlays.test.ts` and `git diff --check`. No live-network test is added; manual imagery verification remains separate because metadata marks the service purpose as test.

### 54.3.1 — Make returned SSURGO result polygons visible on new results

- **Repo:** `/home/andrew/work/fpac-soil-mcp`
- **Must edit:** `apps/agent-fpac-soil-openai-sdk/frontend/client/src/components/map/MapPanel.tsx`, `docs/decisions/0015-vendored-agent-app-frontend.md`.
- **Can create:** `apps/agent-fpac-soil-openai-sdk/frontend/client/src/components/map/resultVisibility.ts` and `resultVisibility.test.ts`.
- **Depends on:** 54.2.1.
- **Specification:** Reproduce the reported behavior using an ADR 0017 result block with inline `farmland_classes` geometry. Ensure result polygons are visible whenever a new successful screening result is returned and remain visible when the user returns to Map. A user may still hide them after return. Keep the fixed SSURGO context overlay off unless independently enabled. If current behavior already passes, add regression evidence and report that no behavior change was needed; do not make unrelated changes.
- **Do not touch:** server result generation/schema, SSURGO context URL, map symbology, or result data.
- **Grep anchors:** `resultsVisible`, `showScreening`, `renderMapBlock`, result layer visibility effect and Results/Map tabs in `MapPanel.tsx`.
- **Reference implementations:** `mapControls.ts` visibility seam and `mapControls.test.ts`; ADR 0017 inline/omitted delivery fields.
- **Acceptance:** focused test proves a new inline result's `result-*` layers are visible on return, that the context SSURGO overlay is not implicitly enabled, and that explicit hide still works; run named focused test and `npm run test:map-identify`.

### 54.4.1 — Amend ADR 0016 and define validated corridor context

- **Repo:** `/home/andrew/work/fpac-soil-mcp`
- **Must edit:** `docs/decisions/0016-out-of-band-aoi-screening-handoff.md`.
- **Can create:** `apps/agent-fpac-soil-openai-sdk/agent_server/corridor_context.py` and `apps/agent-fpac-soil-openai-sdk/tests/test_corridor_context.py`; update `docs/decisions/README.md` only if its conventions require it.
- **Depends on:** 54.3.1.
- **Specification:** Amend ADR 0016 to define an `active_corridor` separate from polygon `active_aoi`, per-conversation/session-scoped, automatically attached/detachable, and used only for `analyze_corridor_fppa`. Define a bounded, validated model for one primary LineString, optional alternative LineStrings, optional indirect Polygon/MultiPolygon geometry, positive buffer distance, and supported units. Provide fixed instruction/reference substitution semantics; do not put coordinates in model instructions. Keep examples synthetic and preserve stateless server behavior.
- **Do not touch:** MCP server/tool schema or calculation, existing polygon AOI contract/validation, frontend, or Site Assessment gate.
- **Grep anchors:** ADR 0016 `Decision Outcome`, `Substitution`, `Map screening route`, `Scope boundary`; app `AOI_REF_PATTERN`, `parse_active_aoi`, `instruction_note` in `aoi_context.py` (read-only reference).
- **Reference implementations:** existing `ActiveAoi` parsing/substitution and `geo.py` bounded request errors; corridor tool schema in `spatial_analysis_tools.py`.
- **Acceptance:** focused unit tests cover valid/malformed corridor references, geometry and limits, units/distance, alternatives/staging, deep-copy substitution only for the corridor tool; run `cd apps/agent-fpac-soil-openai-sdk && uv run pytest tests/test_corridor_context.py -q`.

### 54.5.1 — Add direct stateless corridor screening route

- **Repo:** `/home/andrew/work/fpac-soil-mcp`
- **Must edit:** `apps/agent-fpac-soil-openai-sdk/agent_server/geo.py`, `apps/agent-fpac-soil-openai-sdk/agent_server/start_server.py`.
- **Can create:** `apps/agent-fpac-soil-openai-sdk/tests/test_geo_corridor.py`.
- **Depends on:** 54.4.1.
- **Specification:** Add a dedicated `/api/geo/corridor` request/route using the validated corridor input contract and existing `analyze_corridor_fppa` only. Call untraced with `include_map=True`, never pass Site Assessment inputs, never log/echo geometry or MCP payloads, and return a bounded browser display result containing necessary corridor screening summary, server map block, and regulatory notice. Preserve bounded failure envelopes and preliminary status.
- **Do not touch:** MCP server, existing `/api/geo/screen` behavior, chat context binding, or frontend.
- **Grep anchors:** `ScreenRequest`, `screen_aoi`, `_call_tool_untraced`, `parse_tool_result`, `start_server.py` geo routes.
- **Reference implementations:** `/api/geo/screen` and `/api/geo/map`; tests in `tests/test_geo_screen.py` and `tests/test_geo_map.py`.
- **Acceptance:** route tests verify exact tool/arguments, include_map true, no Site Assessment inputs, response allowlist/map/notice, malformed input, MCP/tool failure, and no geometry logging. Run `cd apps/agent-fpac-soil-openai-sdk && uv run pytest tests/test_geo_corridor.py -q`.

### 54.5.2 — Bind corridor context to agent tool calls

- **Repo:** `/home/andrew/work/fpac-soil-mcp`
- **Must edit:** `apps/agent-fpac-soil-openai-sdk/agent_server/agent.py`.
- **Can create:** append focused agent-binding cases to `apps/agent-fpac-soil-openai-sdk/tests/test_corridor_context.py`.
- **Depends on:** 54.4.1.
- **Specification:** Read validated `active_corridor` independently of `active_aoi`; give the model a short coordinate-free instruction; substitute the corridor reference and its buffer, indirect geometry, and alternatives only into `analyze_corridor_fppa`. The corridor and polygon AOI may coexist. Invalid/missing corridor context is ignored safely; other tool calls and arguments remain unchanged.
- **Do not touch:** `geo.py` direct route, MCP server, polygon AOI behavior, frontend transport, or Site Assessment logic.
- **Grep anchors:** `_connect_fpac_agent`, `read_active_aoi`, `bind_active_aoi`, and tool call binding in `agent.py`.
- **Reference implementations:** `aoi_context.py`/`test_aoi_context.py` and ADR 0016 existing geometry substitution.
- **Acceptance:** focused agent tests verify corridor tool receives exact geometry/settings, unrelated tools are unchanged, no coordinates enter the instruction, and polygon AOI continues to work concurrently. Run `cd apps/agent-fpac-soil-openai-sdk && uv run pytest tests/test_corridor_context.py tests/test_agent_mcp_wiring.py -q`.

### 54.6.1 — Transport per-chat corridor context to the agent

- **Repo:** `/home/andrew/work/fpac-soil-mcp`
- **Must edit:** `apps/agent-fpac-soil-openai-sdk/frontend/client/src/components/chat.tsx`, `apps/agent-fpac-soil-openai-sdk/frontend/client/src/layouts/ChatLayout.tsx`, `apps/agent-fpac-soil-openai-sdk/frontend/packages/core/src/schemas/chat.ts`, `apps/agent-fpac-soil-openai-sdk/frontend/packages/ai-sdk-providers/src/providers-server.ts`, `apps/agent-fpac-soil-openai-sdk/frontend/server/src/routes/chat.ts`, `docs/decisions/0015-vendored-agent-app-frontend.md`.
- **Can create:** `apps/agent-fpac-soil-openai-sdk/frontend/client/src/components/map/ActiveCorridorContext.tsx`, `apps/agent-fpac-soil-openai-sdk/frontend/client/src/components/map/corridorSession.ts`, and `apps/agent-fpac-soil-openai-sdk/frontend/client/src/components/map/corridorSession.test.ts`.
- **Depends on:** 54.5.2.
- **Specification:** Add a separate per-chat sessionStorage corridor context/provider, request schema and request-scoped server registry that forwards it as `custom_inputs.active_corridor`. Preserve activeAoi unchanged and allow both contexts on one turn. Provide set/detach/state APIs for MapPanel; validate/drop malformed client input at the existing schema boundary. Record all vendored changes in ADR 0015.
- **Do not touch:** map drawing, direct corridor route, app-server corridor substitution, upstream dependencies, or generated lockfiles.
- **Grep anchors:** `ActiveAoiProvider` in `ChatLayout.tsx`; `activeAoi` preparation in `chat.tsx`; `activeAoiSchema` in `schemas/chat.ts`; request-scoped registry and `custom_inputs` in `providers-server.ts`; `registerActiveAoi` in `server/src/routes/chat.ts`.
- **Reference implementations:** existing `ActiveAoiContext.tsx`, active-AOI schema/registry transport, and `test:site-assessment` fixture patterns.
- **Acceptance:** focused tests verify per-chat save/restore/detach, both contexts coexist, and request-scoped custom_inputs includes only valid corridor context; run `node --import tsx --test client/src/components/map/corridorSession.test.ts` and `npm run test:site-assessment`.

### 54.7.1 — Draw corridor centerlines, alternatives, and staging areas

- **Repo:** `/home/andrew/work/fpac-soil-mcp`
- **Must edit:** `apps/agent-fpac-soil-openai-sdk/frontend/client/src/components/map/MapPanel.tsx`, `docs/decisions/0015-vendored-agent-app-frontend.md`.
- **Can create:** `apps/agent-fpac-soil-openai-sdk/frontend/client/src/components/map/corridorGeometry.ts` and `apps/agent-fpac-soil-openai-sdk/frontend/client/src/components/map/corridorGeometry.test.ts`.
- **Depends on:** 54.6.1.
- **Specification:** Add a separate corridor drawing workflow without changing polygon AOI modes/state. Support one primary LineString, zero or more labelled alternative LineStrings, and one or more staging/access polygons encoded as Polygon/MultiPolygon. Provide edit/remove/clear behavior, required positive buffer distance (blank initially), unit selector defaulting to feet, and explicit “distance on each side” copy. When input is complete, attach it automatically to the current chat corridor context; expose attached state and detach independently from activeAoi. Do not submit Site Assessment inputs.
- **Do not touch:** backend schemas/routes, polygon AOI/context, server result styling, or MCP server.
- **Grep anchors:** TerraDraw mode registration/start/finish, `chooseMode`, `replaceAoi`, `clear`, tool button helper, measurement mode and MapPanel toolbar.
- **Reference implementations:** existing Terra Draw polygon/rectangle/select modes, `ActiveAoiContext`, and the line-distance helper.
- **Acceptance:** focused tests prove line/polygon geometries validate, alternatives and staging survive serialization, invalid/blank buffer cannot be submitted/attached, feet is default, per-side semantics are visible, and corridor edits do not mutate activeAoi. Run `node --import tsx --test client/src/components/map/corridorGeometry.test.ts`.

### 54.8.1 — Submit corridor screening and display returned results

- **Repo:** `/home/andrew/work/fpac-soil-mcp`
- **Must edit:** `apps/agent-fpac-soil-openai-sdk/frontend/client/src/components/map/MapPanel.tsx`, `apps/agent-fpac-soil-openai-sdk/frontend/client/src/components/map/MapResultContext.tsx`, `docs/decisions/0015-vendored-agent-app-frontend.md`.
- **Can create:** `apps/agent-fpac-soil-openai-sdk/frontend/client/src/components/map/useCorridorScreening.ts`, `apps/agent-fpac-soil-openai-sdk/frontend/client/src/components/map/CorridorScreeningResults.tsx`, `apps/agent-fpac-soil-openai-sdk/frontend/client/src/components/map/corridorScreening.test.ts`, `apps/agent-fpac-soil-openai-sdk/frontend/client/src/components/map/corridor-screening-fixture.tsx`, `apps/agent-fpac-soil-openai-sdk/frontend/client/corridor-screening-fixture.html`, `apps/agent-fpac-soil-openai-sdk/frontend/playwright.corridor-screening.config.ts`, `apps/agent-fpac-soil-openai-sdk/frontend/tests/corridor-screening/screening.spec.ts`, and a named script in `apps/agent-fpac-soil-openai-sdk/frontend/package.json`.
- **Depends on:** 54.5.1 and 54.7.1.
- **Specification:** Add explicit direct map submission to `/api/geo/corridor`; show running/error/success states and a corridor summary in Results while retaining the current polygon screening and tool-result navigation. Render the returned server map block on the map and reuse its server legend; do not reconstruct geometry/symbology. Map-pane legend follows the currently displayed map result. Extend `MapResultContext`'s result origin to distinguish corridor results from polygon screening and tool results. Keep required preliminary/regulatory notice visible and never present map screening as an official determination.
- **Do not touch:** backend route/schema, MCP server calculations, polygon screening logic, or chat corridor substitution.
- **Grep anchors:** `runScreening`, `showScreening`, `shown`, `renderMapBlock`, Map/Results tab panels and result-origin handling in `MapPanel.tsx`.
- **Reference implementations:** `useScreening.ts`, `ScreeningResults.tsx`, `MapResultContext.tsx`, `MapLegend`, and `/api/geo/screen` response.
- **Acceptance:** focused browser coverage verifies corridor inputs submit once to the direct route, success selects Results, returned map layers/legend render, return to Map works, errors are bounded, and polygon workflow remains unaffected. Run `npm run test:corridor-map` and `node --import tsx --test client/src/components/map/corridorScreening.test.ts`.

## Integrated Acceptance Gate

After all tasks are integrated, run serially from the repository root:

1. `make app-check`.
2. `make app-frontend-check` (read-only Biome lint and build; do not run write-mode lint, add a TypeScript check, or auto-fix unrelated warnings/advisories).
3. From the app project run focused Python tests `uv run pytest tests/test_corridor_context.py tests/test_geo_corridor.py tests/test_agent_mcp_wiring.py -q`.
4. From frontend run `npm run test:map-toolbar`, `npm run test:map-legend`, `npm run test:corridor-map`, `npm run test:map-identify`, `npm run test:map-tabs`, `npm run test:site-assessment`, and `npm run test:chat-export`; also run `node --import tsx --test client/src/components/map/overlays.test.ts client/src/components/map/cdlLegend.test.ts client/src/components/map/resultVisibility.test.ts client/src/components/map/corridorSession.test.ts client/src/components/map/corridorGeometry.test.ts client/src/components/map/corridorScreening.test.ts`.
5. `git diff --check`; inspect ADR 0015 ledger and ADR 0016 amendment; confirm activeAoi remains polygon-only, corridor context is separate, direct calls are untraced, server map legends remain authoritative, CDL colors match USDA NASS, and no map corridor path collects Site Assessment inputs.

No root `make check` is required for this app-scoped plan, but run it if implementation touches root Python source or if a targeted change warrants it. No dev trial, push, deployment, or remote action is in scope.
