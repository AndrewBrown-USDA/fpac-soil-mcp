# EXECUTION PLAN 53: Map and Chat UI Enhancements

## Goal & Scope

### Goal

Improve the agent app's map and chat interface so users can navigate and annotate AOIs, control and understand map layers, inspect screening results without losing map access, measure line distances, exchange AOI GeoJSON, and export conversations in Markdown or JSON. Preserve the existing preliminary-screening boundary, out-of-band AOI contract, fixed service endpoints, and server-provided map-result/legend contract.

### In scope

- Chat export to Markdown and JSON, including user-visible messages and raw tool names, arguments, and results (including geometry); warn users that exports may contain sensitive coordinates and require an explicit user export action.
- Map controls for zoom-to-AOI and reset map view; visibility toggles for AOI and returned polygon boundaries.
- Fixed USGS NAIP ImageServer context layer at `https://imagery.nationalmap.gov/arcgis/rest/services/USGSNAIPImagery/ImageServer`.
- More usable layer ordering controls, persist user preference in browser local storage, and ensure vector result/AOI boundaries remain visible above CDL rasters.
- Better legends with clear layer names, symbology, source/authority, vintage and context-versus-analysis distinctions, without reconstructing server map results client-side.
- Map/Results tabs; switch to Results after a successful screening and keep a clear route back to Map.
- Line-distance measurement with user-selectable units.
- Copy and download the drawn AOI as GeoJSON; allow a user label that is browser-only, visible in AOI/map UI and included in exported GeoJSON, not sent to chat/MCP context.
- Remove “Preliminary machine estimate” from the map-unit identify popup only; retain required screening/authority notices elsewhere.
- Tighter UI wording and accessibility/usability refinements directly supporting these features.

### Out of scope

- Changes to server/MCP schemas, screening calculations, regulatory determinations, or AOI geometry handoff to the agent.
- Storing the user AOI label in chat/MCP context or server-side persistence.
- User-provided service URLs or dynamic endpoint construction.
- Arbitrary reordering that can put vector boundaries below rasters; vectors remain above raster layers.
- Exporting hidden model reasoning, credentials, server traces, or data not available in the current conversation's message/tool records.
- Pushes, deployments, PR actions, or other remote operations.

### User-stated constraints

> “zoom to AOI” “reset map” “toggle AOI/returned polygon lines”

> “add support for NAIP image server”

> “make sure that boundaries that are vector layers print on top of the CDL layer”

> “better control for changing the order of layers”

> “better legend information on the map”

> “making it so screening results do not appear off screen, add a tab”

> “add measurement tools for line distance, and buttons to copy or save as geoJSON the drawn AOI”

> “it also would be good to be able to accept a user -specified label.”

> “we also do not need text ‘preliminary machine estimate’ on the map unit result when clicking on an AOI.”

> “an export button for the chat that can do markdown and json output”

The user additionally specified that chat export includes raw tool data and geometry with a sensitivity warning and explicit export action; the NAIP URL above; selectable distance units; browser-local persistence of layer ordering; browser-only AOI label; auto-switch to Results after screening; raster/context reordering with vectors fixed on top; tracked planning artifacts; and at most two concurrent workers.

## Decision Log

| ID | Decision | Rationale / source |
|---|---|---|
| D1 | Continue on `feature/local-dev-trial`, clean at `757af9a`; plan number is 53 because 52 exists on this branch. | User selected this branch after correcting the apparent plan number. |
| D2 | Prioritize chat export early, then AOI/map interactions, layer stack, and results layout/copy polish. | User chose chat export ahead of map refinements; dependency order below keeps tightly coupled map controls together. |
| D3 | Export visible conversation messages plus available raw tool names/arguments/results, including geometry; do not include hidden reasoning or server traces. Show sensitivity warning and require explicit user action. | User selected raw tool data including geometry and warning. |
| D4 | Use fixed NAIP ImageServer URL `https://imagery.nationalmap.gov/arcgis/rest/services/USGSNAIPImagery/ImageServer`. | User supplied the exact endpoint. |
| D5 | AOI label is browser-only metadata, displayed in UI and GeoJSON export, not sent to agent/MCP context. | Avoids changing ADR 0016. |
| D6 | Results are a Map/Results tab view; switch to Results on successful screening and provide an obvious return to Map. | User selected this behavior. |
| D7 | Distance units are selectable. | User selected selectable units. |
| D8 | Persist layer order in browser local storage. Reorder optional raster/context layers only; keep AOI and returned vector boundaries above rasters/CDL. | User selected local persistence and raster-only reordering. |
| D9 | Use at most two concurrent workers, isolated in worktrees when running parallel tasks in this repository. | User approved this parallelism. |
| D10 | Track planning artifacts and commit planning-only changes separately with `docs(planning):`; no implementation starts until plan approval. | User selected tracked artifacts and approved a planning-only commit. |
| D11 | Preserve ADRs 0015, 0016, and 0017: record all vendored frontend local changes in ADR 0015; do not alter AOI-to-chat context; use server map blocks/legends as authoritative and keep vectors over rasters. | Existing accepted architecture constraints. |

## Reconnaissance and Hazards

- Repository is `/home/andrew/work/fpac-soil-mcp`; branch `feature/local-dev-trial`, clean at `757af9a` before plan drafting. Plans 50, 51, and 52 exist; 53 is next.
- Planning paths are tracked; `planning/tasks/` contains prior task TODOs. Plan/prompt/state files must be committed separately from implementation.
- Frontend is the vendored app under `apps/agent-fpac-soil-openai-sdk/frontend`; read root and app `AGENTS.md`, plus ADRs 0015–0017 before work.
- Central UI files: `MapPanel.tsx` (746 lines), `message.tsx` (564), `mapLayers.ts` (376), `overlays.ts` (131), `Legend.tsx` (138), `IdentifyPopup.tsx` (153), `ActiveAoiContext.tsx` (129), `OverlayControl.tsx` (95), `ScreeningResults.tsx` (88), and `ChatLayout.tsx` (94). Large files require grep-anchor navigation.
- Existing Playwright config/fixture: `frontend/playwright.site-assessment.config.ts`, `frontend/tests/site-assessment/cards.spec.ts`, and `frontend/client/src/components/map/identify.test.ts`. Existing scripts include `test:site-assessment` and `test:map-identify`; extend or add focused browser coverage without introducing dependencies or production routes.
- `overlays.ts` uses a fixed catalog and `addOverlay` inserts rasters before result layers/AOI. NAIP needs service-specific ArcGIS ImageServer tile/export URL handling verified against the supplied endpoint; preserve attribution, error/loading status, CORS behavior, zoom limits, and `overlayIdForSource` coverage.
- `MapPanel.tsx` owns MapLibre/Terra Draw lifecycle, the current AOI, screening state, and map result display. Avoid parallel tasks editing it; sequence its major integration points. `mapLayers.ts` draws server result blocks. Existing `overlayBeforeId` is the stacking seam, but dynamic reorder must preserve result/AOI vector placement.
- AOI state lives in `ActiveAoiContext.tsx` and is sent as session context (ADR 0016). Keep label strictly local and do not alter `ActiveAoi` geometry/summary payload contract or request plumbing.
- Chat messages are SDK `ChatMessage` records rendered through `message.tsx`; export must use records available to the current chat, preserve structured tool inputs/outputs where available, and avoid hidden/internal data. Do not create object URLs until explicit action; revoke generated URLs and handle clipboard failure.
- Map results and their legend/source/authority metadata come from server map blocks (ADR 0017); enrich presentation without inventing or replacing server values.
- Baseline on this branch: `make check` passed (952 passed, 3 skipped, 45 deselected); `make app-check` passed (177 tests); `make app-frontend-check` passed with 10 existing lint warnings and successful build. Frontend check reported 10 existing warnings and npm audit 10 advisories; do not auto-fix dependencies or unrelated warnings. Re-run baseline as applicable before wave 1 because branch has advanced since prior summary; the committed plan 52 state reports newer suites but is not a substitute for this branch's current verification.
- There is no request for a remote trial. All validation is local; no push or deployment.

## Wave Table

| Wave | Theme | Tasks | Dependencies |
|---|---|---|---|
| 1 | Chat export contract and UI | 53.1.1 export serialization/safety tests | No dependencies. |
| 2 | Chat export actions and warning | 53.1.2 explicit Markdown/JSON export controls | 53.1.1. |
| 3 | AOI/map interaction foundations | 53.2.1 AOI label and GeoJSON copy/download; 53.2.2 map view, visibility, and line measurement controls | 53.2.1 and 53.2.2 are sequenced to prevent `MapPanel.tsx` overlap. |
| 4 | Layer stack and legend | 53.3.1 NAIP fixed overlay support; 53.3.2 local raster ordering and vector-on-top invariant; 53.3.3 improved legend/context copy | 53.3.1 then 53.3.2 because catalog/control overlap. 53.3.3 may run parallel with 53.3.1 if files remain disjoint. |
| 5 | Results navigation and wording | 53.4.1 Map/Results tabs and post-screening switch; 53.4.2 identify popup wording and UI copy/accessibility polish | 53.4.1 follows 53.2.2 and 53.3.3. 53.4.2 may run in parallel on disjoint files. |
| 6 | Integrated verification and handoff | Orchestrator integration, targeted browser checks, frontend lint/build, ADR 0015 ledger completion | All implementation tasks done; serial shared checks. |

At most two workers run concurrently. Use worktrees for parallel workers. Tasks that touch `MapPanel.tsx` are sequenced; do not parallelize those edits. If a task needs an out-of-scope file, amend the plan before execution.

## Task Specifications

### 53.1.1 — Define chat export serialization and privacy boundary

- **Repo:** `/home/andrew/work/fpac-soil-mcp`
- **Must edit:** `docs/decisions/0015-vendored-agent-app-frontend.md`.
- **Can create:** `apps/agent-fpac-soil-openai-sdk/frontend/client/src/lib/chatExport.ts`, `apps/agent-fpac-soil-openai-sdk/frontend/client/src/lib/chatExport.test.ts`.
- **Depends on:** none.
- **Specification:** Create deterministic Markdown and JSON serialization for current-chat user-visible messages and available raw tool names, arguments, and results, including geometry. Exclude hidden reasoning, server traces, credentials, and unrelated chat history. Include clear sensitivity metadata/warning copy in UI integration contract. Avoid exposing tool data merely by rendering it; export occurs only on explicit user action. Handle absent/partial/streaming values without fabricating data. Record both created frontend paths in ADR 0015's `### Local changes` ledger in the same task change, as required by the app guidance. This requirement was added after the initial implementation commit because the original task scope omitted the repository rule.
- **Do not touch:** server agent/history APIs, AOI context contract, dependency manifests, or map components. Do not edit files other than the two specified frontend files and ADR 0015.
- **Grep anchors:** `ChatMessage`, `message.parts`, `ToolPartRenderer`, `ToolPart` in `message.tsx`; node test scripts and `@playwright/test` in frontend package manifest.
- **Reference implementations:** current message-part parsing/rendering in `message.tsx`; `identify.test.ts` pure helper test pattern.
- **Acceptance:** unit tests assert deterministic Markdown/JSON, visible text and raw tool inputs/outputs retained, geometry preserved, hidden/non-exportable fields excluded, and empty/partial messages handled. Run from `frontend/`: `node --import tsx --test client/src/lib/chatExport.test.ts`.

### 53.1.2 — Add explicit chat export actions and warning

- **Repo:** `/home/andrew/work/fpac-soil-mcp`
- **Must edit:** `apps/agent-fpac-soil-openai-sdk/frontend/client/src/components/chat.tsx` and `docs/decisions/0015-vendored-agent-app-frontend.md`.
- **Can create:** focused export menu/dialog component under `client/src/components/` and an isolated Playwright fixture/spec under `frontend/tests/chat-export/` with config/script if needed.
- **Depends on:** 53.1.1.
- **Specification:** Provide explicit Markdown and JSON export choices for the current conversation. Before generating/downloading/copying any export, clearly warn that raw tool data may include AOI geometry/sensitive coordinates and require explicit confirmation/action. Use the serialization module; do not export hidden reasoning or traces. Support download and, if a copy action is offered, clipboard failure feedback. Update ADR 0015 local-change ledger.
- **Do not touch:** server conversation persistence, model prompts, map files, other export formats, or deployment configuration.
- **Grep anchors:** chat component message collection and toolbar/header actions; `PreviewMessage`/`Message` in `message.tsx`; existing Playwright fixture/config and scripts.
- **Reference implementations:** existing chat header/action patterns and `site-assessment-fixture.html`/`cards.spec.ts` isolated Playwright setup.
- **Acceptance:** Playwright verifies warning appears before export, cancel produces no download, confirmed Markdown/JSON exports have expected content and geometry, and hidden data is absent. Run focused export Playwright script; run frontend lint/build as orchestrator gate.

### 53.2.1 — Add browser-only AOI label and GeoJSON exchange

- **Repo:** `/home/andrew/work/fpac-soil-mcp`
- **Must edit:** `apps/agent-fpac-soil-openai-sdk/frontend/client/src/components/map/MapPanel.tsx`, `docs/decisions/0015-vendored-agent-app-frontend.md`.
- **Can create:** focused AOI export helper and unit test under `client/src/components/map/`.
- **Depends on:** none.
- **Specification:** Add an optional user-specified label associated with the current AOI, visible in the map/AOI UI and included as GeoJSON feature properties when copying or downloading. Copy and save the drawn/loaded AOI as valid GeoJSON. Handle clipboard errors and sanitize filename. Keep label local to browser UI/export; do not add it to ActiveAoi chat/MCP payload, summary, or server requests. Preserve geometry validation and existing AOI replacement/reset behavior.
- **Do not touch:** `agent_server/`, chat custom inputs, `ActiveAoi` geometry/summary contract, server routes, or map result schema. Record each changed/added vendored frontend path in ADR 0015's `### Local changes` ledger in the same task change.
- **Grep anchors:** `replaceAoi`, `onPasted`, `clear`, `aoi`, and AOI toolbar in `MapPanel.tsx`; `ActiveAoi` and storage functions in `ActiveAoiContext.tsx`; GeoJSON feature helpers in `geojson.ts`.
- **Reference implementations:** existing `featureCollection`/`toPolygonGeometry` in `geojson.ts`; browser clipboard/download patterns in frontend if present.
- **Acceptance:** unit/Playwright coverage proves label appears in UI and exported GeoJSON properties, exported geometry round-trips through existing validation, copy/download work, and label is absent from `activeAoi` request context. Focused test command to be added by task; run `npm run test:map-identify` as regression.

### 53.2.2 — Add map navigation, boundary visibility, and line measurement

- **Repo:** `/home/andrew/work/fpac-soil-mcp`
- **Must edit:** `apps/agent-fpac-soil-openai-sdk/frontend/client/src/components/map/MapPanel.tsx`, `docs/decisions/0015-vendored-agent-app-frontend.md`.
- **Can create:** focused distance/unit helper and tests, plus small testable map-control helpers/tests under `client/src/components/map/` if needed to verify fit/reset, visibility-vs-data, and measurement lifecycle without an isolated MapPanel browser fixture.
- **Depends on:** 53.2.1; tasks are sequenced because both may edit `MapPanel.tsx`. Never run two workers editing MapPanel concurrently.
- **Specification:** Add Zoom to AOI using geometry bounds, Reset map to initial extent/view, independent visibility toggles for AOI outline and returned polygon/vector boundaries, and line-distance measurement with selectable units. Measurement must be separate from AOI drawing/editing, visibly indicate active mode, support cancellation/clear, show measured distance, and use a documented geodesic or MapLibre distance method consistent with geometry helpers. Preserve vector-result rendering and AOI state regardless of visibility toggles.
- **Do not touch:** overlay catalog/order implementation, chat export, server contracts, or AOI persistence contract. Record every changed/added vendored frontend path in ADR 0015's `### Local changes` ledger in the same task change.
- **Grep anchors:** MapLibre initialization/load handlers; Terra Draw modes; `geometryBounds`; `renderMapBlock`, `clearMapBlock`; toolbar `toolButton`; map container controls.
- **Reference implementations:** existing polygon/rectangle/select Terra Draw modes; `geometryBounds` and geodesic helpers in map `geojson.ts`.
- **Acceptance:** focused tests verify bounds fit, reset extent, toggles only change visibility (not data), measurement computes known synthetic line lengths in selectable units, and mode cancellation. Add Playwright interaction coverage where the existing isolated fixture can host MapPanel; otherwise test pure helper and document browser limitation.

### 53.3.1 — Add the fixed NAIP imagery context layer

- **Repo:** `/home/andrew/work/fpac-soil-mcp`
- **Must edit:** `apps/agent-fpac-soil-openai-sdk/frontend/client/src/components/map/overlays.ts`, `OverlayControl.tsx`.
- **Can create:** `client/src/components/map/overlays.test.ts` if no suitable test exists.
- **Depends on:** none.
- **Specification:** Add NAIP imagery as a fixed context overlay using the user-supplied ImageServer URL. Verify and document the service's correct ArcGIS ImageServer tile/export request shape and CORS behavior; do not assume an XYZ endpoint if unsupported. Include source, vintage/availability caveat, attribution, opacity/zoom behavior, load/error status, and source ID mapping. Keep URL constant and distinct from analysis data.
- **Do not touch:** user-supplied/dynamic URLs, `MapPanel.tsx` except explicitly required integration (coordinate with task 53.3.2), CDL analysis, or server files.
- **Grep anchors:** `OverlayId`, `Overlay`, `OVERLAYS`, `overlayIdForSource`, `addOverlay`, `removeOverlay`; layer loop in `OverlayControl.tsx`.
- **Reference implementations:** existing CDL raster overlay and source loading/error handling; other fixed ArcGIS/TIGERweb context overlays.
- **Acceptance:** tests assert exact fixed endpoint, service URL construction/encoding, attribution and source-ID mapping; manual/browser test confirms NAIP tiles display at an appropriate zoom and errors remain isolated. Run overlay unit tests and `npm run test:map-identify`.

### 53.3.2 — Persist raster order while pinning vectors above rasters

- **Repo:** `/home/andrew/work/fpac-soil-mcp`
- **Must edit:** `apps/agent-fpac-soil-openai-sdk/frontend/client/src/components/map/overlays.ts`, `OverlayControl.tsx` (schedule after 53.3.1 if same file ownership), focused tests, and `docs/decisions/0015-vendored-agent-app-frontend.md`.
- **Can create:** focused ordering helper/test in map directory.
- **Depends on:** 53.3.1.
- **Specification:** Allow users to reorder optional raster/context layers (including CDL and NAIP), with accessible controls and browser-local persistence. Restore a valid default when storage is missing/corrupt or layer catalog changes. Reordering must update actual MapLibre layer order; keep returned vector layers and AOI boundaries above every raster, particularly CDL. Never permit a combined stack that violates the vector-over-raster invariant.
- **Do not touch:** chat export, AOI labeling, server map contract, or result vector styling. Record every changed/added vendored frontend path in ADR 0015's `### Local changes` ledger in the same task change.
- **Grep anchors:** `overlayBeforeId`, `addOverlay`, `removeOverlay` in `overlays.ts`; overlay controls and `OVERLAYS.map` in `OverlayControl.tsx`; `renderMapBlock` and AOI line insertion in `MapPanel.tsx` for integration review only.
- **Reference implementations:** current raster insertion before first `result-*` layer/AOI; stable local-storage patterns elsewhere in frontend.
- **Acceptance:** helper tests cover ordering/persistence/malformed storage/catalog changes; MapLibre-level or browser test proves raster reordering works while each result vector and AOI boundary remains above CDL/NAIP. Run focused overlay tests and frontend build.

### 53.3.3 — Improve map legend information and layer semantics

- **Repo:** `/home/andrew/work/fpac-soil-mcp`
- **Must edit:** `apps/agent-fpac-soil-openai-sdk/frontend/client/src/components/map/Legend.tsx`, `ScreeningResults.tsx`, and related focused tests if needed.
- **Can create:** none unless a focused legend test is warranted.
- **Depends on:** 53.3.1. Keep its files disjoint from the ordering-control task.
- **Specification:** Make legend labels, swatches/patterns, source, authority, vintage, and context-versus-analysis role easy to interpret. Use server-provided legend values and provenance; do not invent classifications or imply context imagery is analysis evidence. Explain visible overlays and their limitations with concise wording. Ensure accessible text alternatives for patterned/color-only symbols and useful compact behavior on smaller viewports.
- **Do not touch:** server map schemas/data, overlay URLs, screening calculations, or regulatory language in backend constants.
- **Grep anchors:** `MapLegend`, `LegendSwatch`, `AUTHORITY_LABELS`, `drawOrder` in `Legend.tsx`; `ScreeningResults` legend use and notice cards.
- **Reference implementations:** server legend pattern mapping and current context label/source text in `OverlayControl.tsx`; ADR 0017.
- **Acceptance:** focused tests or Playwright assertions verify labels/provenance and accessible names, that server legend entries render unchanged, and context layers are not described as analysis results. Run frontend lint/build and relevant browser tests.

### 53.4.1 — Keep screening results visible in Map/Results tabs

- **Repo:** `/home/andrew/work/fpac-soil-mcp`
- **Must edit:** `apps/agent-fpac-soil-openai-sdk/frontend/client/src/components/map/MapPanel.tsx`, `docs/decisions/0015-vendored-agent-app-frontend.md`, and a small tab component under map directory if needed.
- **Can create:** focused Playwright fixture/spec or component helper if existing map fixture can support it.
- **Depends on:** 53.2.2 and 53.3.3.
- **Specification:** Replace the current vertically stacked, scroll-to-results layout with Map and Results tabs. Keep the map reachable, show an appropriate empty state before screening, and automatically switch to Results after a successful screening; expose a clear return-to-Map action. Tool-result views must remain understandable and not silently replace or discard screening state. Preserve responsive sizing and screen-reader tab semantics.
- **Do not touch:** server screening endpoint/data contract, chat export, AOI state or screening calculations. Record every changed/added vendored frontend path in ADR 0015's `### Local changes` ledger in the same task change.
- **Grep anchors:** section return JSX, `screening.status`, `screeningMap`, `showScreening`, `ScreeningResults`, result origin header in `MapPanel.tsx`.
- **Reference implementations:** existing accessible tabs in the client UI (search before adding dependencies); current `MapPanel` result-origin and Back to screening controls.
- **Acceptance:** Playwright verifies initial Map selection, successful screening selects Results, result details remain in viewport/panel, return to Map works, and tool-result switching preserves screening data. Run focused map Playwright suite plus frontend lint/build.

### 53.4.2 — Tighten identify wording and UI accessibility

- **Repo:** `/home/andrew/work/fpac-soil-mcp`
- **Must edit:** `apps/agent-fpac-soil-openai-sdk/frontend/client/src/components/map/IdentifyPopup.tsx`, and other copy files only if explicitly listed after discovery; `docs/decisions/0015-vendored-agent-app-frontend.md`.
- **Can create:** update/add focused identify tests in existing `identify.test.ts` or popup-specific isolated fixture.
- **Depends on:** none; may run parallel with 53.4.1 because file scopes are disjoint.
- **Specification:** Remove the exact phrase “Preliminary machine estimate” from the map-unit identify result only. Preserve preliminary screening notices and other authority disclaimers. Review nearby UI labels touched by this feature for concise, plain-language, consistent units/statuses, keyboard operation, accessible names, and non-color-only states. Update ADR 0015 for each changed/added vendored frontend path.
- **Do not touch:** `ScreeningResults.tsx` authority notice, regulatory source text, server outputs, or unrelated app copy.
- **Grep anchors:** `Preliminary machine estimate` and popup content in `IdentifyPopup.tsx`; `resultInfo` and identify tests; ADR 0015 local-change ledger.
- **Reference implementations:** existing accessible identify test and status-message patterns.
- **Acceptance:** `npm run test:map-identify` passes and asserts phrase absent in identify UI; screening regulatory notice remains present. Focused Playwright/lint/build covered by integrated gate.

## Integrated Acceptance Gate

After all tasks are integrated, run serially from the repository root:

1. `make app-check`.
2. `make app-frontend-check` (includes `npm ci`, read-only Biome lint, and build); do not use write-mode lint, do not add a TypeScript-check gate, and do not auto-fix existing warnings/audit advisories.
3. `cd apps/agent-fpac-soil-openai-sdk/frontend && npm run test:map-identify && npm run test:site-assessment` plus the new chat-export and map interaction Playwright scripts.
4. `git diff --check`; review all ADR 0015 local-change ledger entries and confirm no chat/MCP AOI-label leakage, no dynamic service URLs, and vector-over-CDL ordering.

Record exact results and existing warnings in `STATE_53.md`. No dev trial, push, deployment, or remote action is in scope.
