---
id: "0015"
title: "Vendor the Full Pinned Chat Template for the Agent App Frontend"
status: "Accepted"
date: 2026-10-28
authors:
  - "Andrew G. Brown"
supersedes: null
superseded_by: null
source_context: "EXECUTION_PLAN_40, EXECUTION_PLAN_41, EXECUTION_PLAN_42"
---

# 15. Vendor the Full Pinned Chat Template for the Agent App Frontend

> **Accepted 2026-10-31 (Plan 42).** The owned frontend with its listed local
> changes passed the parity check and the deployed trial; see
> [`planning/evidence/42.6.1-trial.md`](../../planning/evidence/42.6.1-trial.md).

## Context and Problem Statement

The agent app (`apps/agent-fpac-soil-openai-sdk`) serves the Databricks chat UI
from `databricks/app-templates`, folder `e2e-chatbot-app-next`. The original
launcher cloned that template from GitHub at startup, so every deploy could pick
up unreviewed upstream changes. Plan 40 vendored only `client/` with local type
shims and a client-only lockfile. Review found that layout cannot match
upstream: the client imports the `server/` and `packages/*` workspaces, the
upstream server serves `../../client/dist` relative to `server/dist`, and the
only valid lockfile is the upstream root `package-lock.json`.

## Decision Drivers

* Deploys must be reproducible and reviewable; nothing is fetched from GitHub at
  startup.
* The copy must start from a named upstream commit, and every difference from
  it must be listed, so updates are a re-copy, a re-apply of the listed local
  changes, and a diff.
* Python checks must keep running where npm is unavailable (Databricks
  serverless compute).
* Frontend checks must be read-only; they must not rewrite vendored files.
* The repo must be able to build product features (the map panel) into the
  frontend without forking a separate app.

## Considered Options

1. **Vendor the whole `e2e-chatbot-app-next` folder at one upstream base commit,
   with its own root lockfile, and own it from there with listed local
   changes.**
2. **Vendor `client/` only, with shims for the workspace packages** (the Plan 40
   layout) -- diverges from upstream and needs a hand-built lockfile.
3. **Keep cloning upstream at startup** -- unpinned and not reviewable.

## Decision Outcome

Chosen option: "Vendor the whole folder at one commit", because it is the only
layout that builds with a single workspace lockfile and stays hash-comparable
to upstream for every file this repo has not changed.

* **Base commit:** upstream `0e572976459aafa3d41047067382cb9a6c015d52`.
  `frontend/` is the upstream folder at that commit, including file modes,
  minus the excluded files below, and this repo now owns it. Files not in the
  local-changes list stay identical to the base.
* **Kept:** root `package.json` (npm workspaces `client`, `server`,
  `packages/*`), root `package-lock.json`, `client/`, `server/`,
  `packages/`, `scripts/`, `biome.jsonc`, `tsconfig.json`, `drizzle.config.ts`,
  `knip.json`, `.gitignore`, `.env.example`, `README.md`. `client/`, `server/`
  and `packages/` stay siblings.
* **Excluded:** `.claude/`, `CLAUDE.md`, `tests/`, `playwright.config.ts`,
  `app.yaml`, `databricks.yml`, `manifest.yaml`.
* **Lockfile:** npm regenerates the root `package-lock.json` when dependencies
  change; it is committed together with the matching `package.json`. CI and
  `make app-frontend-check` run `npm ci` against it.
* **Local changes:** allowed. Every modified upstream file and every added path
  is listed in `### Local changes` below, kept current by the task that makes
  the change. No shims for the workspace packages.
* **Launcher (`scripts/start_app.py`):** runs `npm ci`, `npm run build`,
  `npm run start` in `frontend/`, sets `API_PROXY`, and keeps the ports and
  readiness pattern. With `--no-ui`, or when `frontend/package.json` is missing,
  it runs the backend only.
* **Checks:** `make app-check` stays Python-only (`app-lint app-test`).
  `make app-frontend-check` runs `npm ci`, then
  `npx biome lint --skip=nursery/useSortedClasses --skip=style/useTemplate .`,
  then `npm run build`. The two skipped rules are the only error-level findings
  in unmodified upstream (39 and 1); upstream's own `lint` script autofixes them
  with `--write --unsafe`, which must never run here. There is no typecheck:
  upstream has no typecheck script, and `tsc --noEmit` fails at 0e57297 for
  `client` (TS7016, TS2305), `server` (TS2305, TS2322) and the composite
  `packages/*` projects. The Vite and tsdown builds do not typecheck.
* **Runtime:** Node 22 (the Databricks Apps runtime is 22.16; CI uses 22).

### Local changes

* `client/src/components/map/MapPanel.tsx` and `resultVisibility.ts`: show result
  layers on each newly successful screening without changing context overlays or
  overriding later visibility choices. `resultVisibility.test.ts` covers the
  visibility transition and renderer with a mock map, not a browser panel.

* `client/src/components/map/MapPanel.tsx`, `Legend.tsx`, `OverlayControl.tsx`,
  `CDLLegend.tsx`, and `cdlLegend.ts`: accessible map-pane server legend and
  USDA NASS CDL context key, without changing server symbology.
* `client/map-legend-fixture.html`, `client/src/components/map/map-legend-fixture.tsx`,
  `playwright.map-legend.config.ts`, `tests/map-legend/legend.spec.ts`, and
  `package.json`: isolated legend browser coverage and test script.

* `client/src/components/map/MapPanel.tsx`: compact accessible AOI and corridor
  drawing/edit/screen/clear controls in the shared map toolbar; corridor
  alternatives, buffer settings, status, and feature removal in a compact
  options disclosure in place of the separate large-button corridor fieldset
  (corrective follow-up to Plan 55).
* `client/src/components/map/MapPanel.tsx`: explicit Area/Corridor tool modes,
  a shared mode-specific name input, map-anchored completed/live distance
  tooltip with double-click completion and explicit clearing, and an in-map
  collapsible legend overlay retaining the existing server legend components.
* `client/src/components/map/MapPanel.tsx`: combine Area drawing/editing controls
  into one “Area of interest” toolbar group; use Focus for the AOI outline
  toggle and Search for zoom-to-AOI.
* `tests/map-toolbar/toolbar.spec.ts`, `tests/corridor-map/corridor-map.spec.ts`,
  and `tests/map-legend/legend.spec.ts`: browser coverage for mode/name
  persistence, measurement completion/clear, corridor workflows, and legend
  rendering from the existing result contract.
* `client/map-toolbar-fixture.html`, `client/src/components/map/map-toolbar-fixture.tsx`,
  `playwright.map-toolbar.config.ts`, `tests/map-toolbar/toolbar.spec.ts`, and
  `package.json`: isolated production-panel toolbar browser coverage and test script.
* `client/src/components/map/MapPanel.tsx`: one expandable geometry transfer panel
  groups existing GeoJSON import/export actions; corridor attachment stays automatic
  and is no longer controlled by duplicate map-panel attach/detach buttons.
* `client/src/components/map/ActiveAoiChip.tsx`: shared chat chip reports and detaches
  the one mutually exclusive attached AOI or corridor without exposing coordinates.
* `tests/map-toolbar/toolbar.spec.ts`: covers the unified geometry panel and its
  accessible import/export actions.
* `client/src/components/map/IdentifyPopup.tsx`, `identify.ts`, and `MapPanel.tsx`:
  offer compact Exact/BBOX AOI actions for county and urban areas, with exact
  geometry disabled above the AOI vertex cap and county GEOID retained separately.
* `client/src/components/map/GeoJsonInput.tsx`, `MapPanel.tsx`,
  `tests/map-toolbar/toolbar.spec.ts`, and `tests/map-legend/legend.spec.ts`:
  replace the geometry-transfer disclosure with four compact horizontal actions;
  Paste reveals its editor inline.
* `client/src/components/map/corridor-map-fixture.tsx` and
  `tests/corridor-map/corridor-map.spec.ts`: mount both active-geometry providers
  and the shared chat chip; exercise real polygon/corridor attachment, AOI
  replacement, chip detachment, and session-storage cleanup (Plan 55.3.1).

Modified upstream files:

* `packages/db/migrations/0001_add_trace_id.sql` and
  `packages/db/migrations/meta/_journal.json`: add the MLflow trace ID column
  with replay-safe SQL and an execution-order timestamp.
* `client/index.html`: permit browser page zoom and set the browser title to
  “Farmland Protection Policy Act Agent”.
* `client/src/components/sidebar-toggle.tsx`: give the icon-only sidebar
  toggle an accessible name.
* `client/package.json`: exact pins for the map panel dependencies
  `maplibre-gl`, `terra-draw` and `terra-draw-maplibre-gl-adapter` (first
  pinned at 5.24.0, 1.39.0 and 1.5.0; Dependabot keeps them current).
  MapLibre 6 loads its worker from a file next to its own module, which the
  Vite build does not emit, so `components/map/maplibreWorker.ts` bundles the
  worker with `?worker&url` and passes it to `setWorkerUrl`.
* `package-lock.json`: regenerated by npm for those dependencies.
* `client/src/layouts/ChatLayout.tsx`: collapsible map panel column next to
  the chat, wrapped in the active-AOI provider (ADR 0016) and the map-result
  provider, which opens the panel when a tool card's "Show on map" is used
  (Plan 44, ADR 0017). The map toggle has an icon and a focus ring; when open,
  it appears inline with the map-panel header.
* `client/src/index.css`: "field atlas" app theme (warm surfaces, ink text,
  forest-green primary, `--atlas-*` tokens with `atlas-soil`/`atlas-leaf`
  colour utilities) in light and dark mode. Map data colours, chart and
  status tokens are unchanged
  (`planning/RESEARCH_AGENT_MAP_APP_VISUAL_DESIGN.md`).
* `client/src/components/message.tsx`: "Show on map" button on completed
  `analyze_farmland_by_polygon`, `analyze_corridor_fppa` and
  `get_soil_polygons_by_geometry` tool cards (Plan 44, ADR 0017), plus a
  "Show CDL on map" action that passes a completed `analyze_cdl_context`
  result directly to the existing map-result context (Plan 50.2.2).
* `client/src/components/multimodal-input.tsx`: shows the attached map AOI
  chip above the textarea (ADR 0016).
* `client/src/components/suggested-actions.tsx`: FPPA starter prompts
  (labelled, two columns on wider screens) in place of the two generic
  upstream suggestions. Each reuses an `eval/prompt_test_cases.json`
  `user_prompt` named by `caseId`, plus one map-AOI prompt.
* `client/src/components/chat.tsx`: tells the map panel the open chat id and
  sends the chat's AOI as `activeAoi` with each turn (ADR 0016).
* `packages/core/src/schemas/chat.ts`: optional, bounded `activeAoi` in the
  chat request; invalid values are dropped (ADR 0016).
* `packages/core/src/ai/providers.ts`: re-exports the AOI request helpers.
* `client/src/components/map/farmlandClasses.ts`: keeps unknown/unrecognized
  classification labels distinct from explicit not-prime farmland rather than
  defaulting unrecognized values to `not_prime`.
 * `client/src/components/map/MapPanel.tsx`: uses the NCSS acronym-only logo in
  the map-panel header, with the official color and white variants for light
  and dark themes (NCSS Visual Standards Guide, March 2018); Vite-managed
  imports ensure the assets are included in the frontend build. It also shows
  CDL class summaries received from a tool card without a map route or
  re-query (Plan 50.2.2); provides a browser-only AOI label and explicit
   GeoJSON copy/download actions (Plan 53.2.1); accessible Map/Results tabs,
   automatic Results selection on completed screening, and retained screening
    details while viewing tool results (Plan 53.4.1).
 * `client/src/components/map/IdentifyPopup.tsx`: removes “Preliminary machine
   estimate” from the map-unit identify popup only (Plan 53.4.2); screening
   authority notices elsewhere remain unchanged.
* `client/src/components/map/overlays.ts` and
  `client/src/components/map/OverlayControl.tsx`: fixed, toggleable CDL
  ImageServer raster context overlay, with attribution and vintage/context
  labels (Plan 50.2.2); fixed USDA FPAC NAIP ImageServer `exportImage` raster
  context overlay with variable-vintage caveat, source attribution, and default-off
  control. Its metadata labels the service purpose `test:202407180638 naip service`,
  so availability may change; this is not a production-readiness claim.
  `client/src/components/map/overlays.test.ts` covers the fixed request and
  catalog metadata; accessible raster/context ordering controls have
  browser-local persistence, keeping result vectors and AOI boundaries above
  rasters (Plan 53.3.2).
* `client/src/components/map/Legend.tsx` and
  `client/src/components/map/ScreeningResults.tsx`: clarify that fixed context
  overlays are geographic reference, add text alternatives for server legend
  symbols, constrain the legend card height on smaller viewports (Plan 53.3.3),
  prioritize the server farmland-class legend and CDL key, and remove the
  duplicate screening legend from Results; server legend values and the
  regulatory notice remain unchanged.
* `client/src/components/map/MapPanel.tsx`, `Legend.tsx`, `OverlayControl.tsx`,
  and `ResultsTable.tsx`, plus `client/src/layouts/ChatLayout.tsx`: synchronize
  AOI visibility across the outline and editable geometry, expose tooltips for
  disabled toolbar actions, remove the measurement popup halo, widen the
  desktop map pane and horizontally scroll long map-unit tables, move the CDL
  key from Layers into the map legend, and compact/right-align corridor options.
* `tests/map-toolbar/toolbar.spec.ts`, `tests/map-legend/legend.spec.ts`,
  `tests/corridor-map/corridor-map.spec.ts`, and
  `client/src/components/map/map-legend-fixture.tsx`: cover the control,
  results, legend, and corridor layout behavior above.
* `client/src/components/map/MapPanel.tsx`, `Legend.tsx`, and
  `farmlandClasses.ts`: keep the core farmland legend available without map
  results, render a restrained two-stroke AOI boundary above result polygons,
  and match the server's diagonal farmland hatch styles. Corridor actions stay
  inline after measurement and are disabled outside Corridor mode.
* `tests/map-legend/legend.spec.ts` and `tests/map-toolbar/toolbar.spec.ts`:
  cover the no-result and AOI-cleared core legend, farmland hatch direction,
  AOI boundary visibility, and inline/mode-dependent corridor actions.
* `client/src/components/map/IdentifyPopup.tsx`, `MapPanel.tsx`,
  `OverlayControl.tsx`, `overlays.ts`, `geojson.ts`, and `identify.test.ts`,
  plus `tests/map-toolbar/toolbar.spec.ts`: validate returned county geometry
  before popup area calculations; Exact/BBOX actions retry outline retrieval on
  selection, sit beside name/GEOID, remove context disclaimers, report
  exact-outline size limits after selection, and cover Hamilton County identify
  with synthetic TIGERweb Polygon and AOI replacement.
* `client/src/components/map/MapPanel.tsx`,
  `client/src/components/map/map-toolbar-fixture.tsx`, and
  `tests/map-toolbar/toolbar.spec.ts`: decouple result-layer visibility from
  camera fitting, re-fit the AOI only when the Map tab is visible, and cover
  map-center stability and AOI recentering after Results. The isolated fixture
  exposes a camera probe for these browser assertions; its Firefox stress case
  captures console/page errors and network status while cycling CDL and retrying
  a failed/delayed screening request.
* `client/src/components/map/MapResultContext.tsx` and
  `client/src/components/map/ShowOnMapButton.tsx`: pass the original CDL tool
  result through the existing map-result context without requesting it again
  (Plan 50.2.2); reject CDL map context storage when the active AOI is absent
  or its reference/geometry no longer matches the AOI captured for the result
  (Plan 51.2.2).
* `client/src/components/message.tsx`: render resource-backed
  `get_site_assessment_question` output as a distinct interview card and
  structured `site_assessment_confirmed_summary` text as a separate review
  card. Card actions send the exact `site_assessment_answer` and confirmed
  summary records as JSON chat messages (Plan 51.2.2).
* `client/src/components/message.tsx`,
  `client/src/components/elements/tool.tsx`, and
  `client/src/components/map/ShowOnMapButton.tsx`: collapse regular tool
  details by default while retaining MCP approval behavior, and put the
  map-capable tool action in the tool-call header with accessible tool/AOI
  context (Plan 55.2.1).
* `package.json`: add the test-only `test:site-assessment` Playwright script;
  no dependencies or lockfile changes (Plan 51.2.2).
* `server/src/routes/chat.ts`: registers the request's AOI and passes its key
  to the provider call (ADR 0016).
* `client/src/components/chat.tsx`, `client/src/layouts/ChatLayout.tsx`,
  `packages/core/src/schemas/chat.ts`,
  `packages/ai-sdk-providers/src/providers-server.ts`, and
  `server/src/routes/chat.ts`: transport
  bounded per-chat active-corridor context independently of AOI through a
  request-scoped provider registry into `custom_inputs.active_corridor` (Plan
  54.6.1).
* `client/src/components/map/ActiveCorridorContext.tsx`,
  `client/src/components/map/corridorSession.ts`, and
  `client/src/components/map/corridorSession.test.ts`: per-chat corridor session
  storage/provider and focused persistence validation (Plan 54.6.1).
* `client/src/components/map/MapPanel.tsx`, `corridorGeometry.ts`, and
  `corridorGeometry.test.ts`: separate corridor line/staging drawing controls,
  buffer validation and per-chat attachment, without changing polygon AOI state
  (Plan 54.7.1).
* `client/src/components/map/MapPanel.tsx` and `MapResultContext.tsx`: direct
  corridor screening from the map panel, server map/legend handoff, and active
  result navigation while preserving polygon and tool results (Plan 54.8.1).
* `client/src/components/map/useCorridorScreening.ts` and
  `CorridorScreeningResults.tsx`: direct `/api/geo/corridor` request lifecycle,
  allowlisted preliminary summary, and regulatory notice (Plan 54.8.1).
* `client/src/components/map/corridorScreening.test.ts`,
  `client/corridor-map-fixture.html`,
  `client/src/components/map/corridor-map-fixture.tsx`,
  `playwright.corridor-map.config.ts`, `tests/corridor-map/corridor-map.spec.ts`,
  and `package.json`: focused direct corridor request and browser-panel coverage
  (Plan 54.8.1; no new dependencies).
* `server/src/middleware/auth.ts`: provides a synthetic local-only session when
  `FPAC_LOCAL_DEV=1` and the request socket is loopback; normal requests retain
  the Databricks session lookup. `server/src/middleware/auth.test.ts` covers
  disabled, non-loopback, and enabled loopback cases.
* `packages/ai-sdk-providers/src/providers-server.ts`: request-scoped AOI
  registry; `databricksFetch` adds the AOI to the agent request as
  `custom_inputs.active_aoi` (ADR 0016); local mode uses loopback placeholders
  and a dummy bearer value because the request is routed to the local agent
  proxy, without resolving Databricks host or credentials.

Added paths:

* `client/src/components/tool-card-fixture.tsx`,
  `client/tool-card-fixture.html`, and
  `tests/site-assessment/tool-card.spec.ts`: isolated Playwright regression
  coverage for collapsed tool details and the top-bar map action (Plan 55.2.1;
  no new dependencies).
* `client/src/lib/chatExport.ts` and `client/src/lib/chatExport.test.ts`:
  deterministic current-chat Markdown and JSON serializers that retain visible
  text and available raw tool names, inputs and outputs (including geometry),
  exclude hidden/non-exportable content, and expose a sensitivity warning
  contract for explicit user-initiated exports (Plan 53.1.1).
* `client/src/components/chat-export-actions.tsx` and
  `client/src/components/chat.tsx`: explicit Markdown/JSON export controls with
  a sensitivity warning and confirmation before download (Plan 53.1.2).
* `client/src/components/chat-export-fixture.tsx`,
  `client/chat-export-fixture.html`, `playwright.chat-export.config.ts`,
  `tests/chat-export/export.spec.ts`, and `package.json`: isolated Playwright
  coverage for warning cancellation, confirmed exports, geometry, and hidden
  data exclusion (Plan 53.1.2; no new dependencies).
* `client/src/components/map/**`: map panel (MapLibre and Terra Draw AOI
  drawing, GeoJSON paste and file input, `/api/geo/screen` client, farmland
  class mapping, legend, results table, regulatory notice, error states, the
  per-chat active-AOI context and the AOI chip). Plan 44 added the server
  map-layer renderer with server legends (`mapLayers.ts`, ADR 0017), the
  shown-result context and tool-card button (`MapResultContext.tsx`,
  `ShowOnMapButton.tsx`, calling `/api/geo/map`), the fixed context-overlay
  catalog and toggles (`overlays.ts`, `OverlayControl.tsx`), and identify
  popups with "Use as AOI" (`identify.ts`, `IdentifyPopup.tsx`). The visual
  refresh added the panel header, grouped draw/edit tools, the
  `StatusMessage.tsx` message bar and the screening summary strip. AOI import
  keeps file upload prominent and collapses pasted GeoJSON behind a disclosure.
  Plan 50.2.2 adds `client/src/components/map/CDLContextSummary.tsx` to show the
  complete server-returned class distributions, source, vintage, status,
  coverage and limitations for the AOI and both exterior zones.
* `client/src/components/map/aoiExport.ts` and
  `client/src/components/map/aoiExport.test.ts`: serialize the current AOI as
  labeled GeoJSON and sanitize download filenames (Plan 53.2.1).
 * `client/src/components/map/MapPanel.tsx`: map navigation/reset, independent
  AOI and returned-result visibility controls, and line measurement UI (Plan
   53.2.2).
 * `client/src/components/map/identify.test.ts`: verifies the identify popup
   omits the estimate phrase while screening retains its authority notice (Plan
   53.4.2).
* `client/src/components/map/distance.ts` and
  `client/src/components/map/distance.test.ts`: geodesic line-distance
  calculation and unit conversions (Plan 53.2.2).
* `client/src/components/map/mapControls.ts` and
  `client/src/components/map/mapControls.test.ts`: testable bounds, initial
  view, visibility, and measurement-cancellation seams (Plan 53.2.2).
* `client/src/components/site-assessment-cards.tsx`: resource-driven question
  choices, evidence/comment/provenance, verification, source, and justification
  fields, explicit unknown/skipped records, and a distinct
  assumptions/Confirm/Edit review card (Plan 51.2.2).
* `client/site-assessment-fixture.html` and
  `client/src/components/site-assessment-fixture.tsx`: isolated browser
  fixture for card and AOI interaction tests (Plan 51.2.2), including the
  answer verification and provenance fields.
* `playwright.site-assessment.config.ts` and
  `tests/site-assessment/cards.spec.ts`: isolated Playwright configuration and
  coverage for emitted answer/confirmation records and stale CDL refusal
  (Plan 51.2.2).
* `client/map-tabs-fixture.html`, `client/src/components/map/map-tabs-fixture.tsx`,
  `playwright.map-tabs.config.ts`, `tests/map-tabs/tabs.spec.ts`, and
  `package.json`: focused isolated browser coverage for Map/Results tab selection,
  empty state, and preserving screening details when switching to tool results
  (Plan 53.4.1; no new dependencies).
* `client/src/assets/ncss-acronym-color.png` and
  `client/src/assets/ncss-acronym-white.png`: official NCSS acronym-only logo
  variants prepared from the
  [NCSS Visual Standards Guide](https://www.nrcs.usda.gov/sites/default/files/2022-09/NCSS_logo_style_guide.pdf)
  for light and dark map-panel headers.
* `client/aoi-state-fixture.html`,
  `client/src/components/map/aoi-state-fixture.tsx`,
  `playwright.aoi-state.config.ts`, `tests/aoi-state/aoi-state.spec.ts`, and
  `package.json` (`test:aoi-state`): isolated browser fixture for AOI and
  corridor chat state with a switchable fake chat id (`?chat=none` starts
  without one), a hidden state probe, and faked `/api/geo/*` and TIGERweb
  responses with controllable delay and failure, so the issue #89 hardening is
  tested without SDA (no new dependencies).

### Update procedure

1. Re-copy the upstream folder at the new commit, applying the same exclusions.
2. Re-apply the changes listed in `### Local changes`.
3. Reconcile `client/package.json` and the other workspace `package.json` files
   with the local dependency additions, then let npm regenerate the root
   `package-lock.json`.
4. Compare `git ls-tree` hashes with upstream only for `frontend/` entries not
   in the local-changes list.
5. Re-run `make app-frontend-check`. If new error-level lint rules appear in
   upstream, update the skip list and this ADR rather than editing upstream
   files to satisfy them.
6. Update the base commit here and in the app `README.md` and `AGENTS.md`.

### Consequences

* **Positive:** deploys are reproducible; parity with upstream is checkable by
  hash for unchanged files; product features live in the same app.
* **Negative:** owning local changes turns upstream updates into a re-apply
  step, and the lockfile drifts from upstream once dependencies are added;
  about 600 vendored files; no typecheck gate; two upstream lint
  rules are skipped; frontend checks need Node 22 and npm, which Databricks
  serverless compute does not provide by default.

### Scope boundary

This decision covers how the chat UI is vendored and changed. The map panel and
AOI handoff are local changes made under Plan 42 (map code lives under
`client/src/components/map/`); the handoff contract is ADR 0016.
`custom_inputs`/`custom_outputs` handling stays out of scope.

## Validation & Compliance

* Parity: `git ls-tree HEAD apps/agent-fpac-soil-openai-sdk/frontend/` hashes
  equal upstream 0e57297 for every kept entry not in `### Local changes`.
* `make app-frontend-check` passes (CI `agent-app` job, Node 22).
* `make app-check` passes without npm.
* Deployed check: Plan 41 task 41.4.1; Plan 42 deployed trial before
  `Accepted`.
