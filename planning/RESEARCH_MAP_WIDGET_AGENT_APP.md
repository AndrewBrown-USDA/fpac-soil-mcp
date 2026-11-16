# Research: Map Widget for the `agent-fpac-soil-openai-sdk` Chat App

Status: folded into `MASTER_PLAN.md` by Plan 37 (2026-10-24). Answered questions: see `EXECUTION_PLAN_37.md` D1-D7 and D12; remaining open items are listed in the master plan tracks.

Date: 2026-10-24. App inspected: `/Workspace/Users/andrew.g.brown@usda.gov/fpac-soil-mcp/apps/agent-fpac-soil-openai-sdk/` (personal clone; branch and commit not recorded because no compute was available to run git). The folder holds `agent_server/`, `scripts/`, `tests/`, `app.yaml`, `databricks.yml`, `manifest.yaml`, `pyproject.toml`, `uv.lock`, and docs. It has no frontend folder and no `package.json`. Input to `planning/MASTER_PLAN.md`; builds on `planning/SPATIAL_VISUALIZATION_STRATEGY.md`.

## Question

How can the agent chat app get a map widget, built on open-source tools such as MapLibre, that is integrated with the chat? Requirements from the user:

1. Accept a sensible set of spatial input files: `.json` / `.geojson` at minimum, more formats if practical.
2. A drawing interface to create or select an Area of Interest (AOI).
3. Arbitrary basemaps.
4. Vector overlays, including a continuous soil map unit service, and anything the agent fetches back (Census urban areas, counties, soils).

## Source quality note

* Databricks and MLflow claims cite docs retrieved this session ([^d-*], [^m-*]).
* Repo claims cite files read this session ([^r-*]).
* Third-party library and federal map-service claims ([^x-*]) cite the official project or agency URL, but **this session could not fetch external sites** (the sandbox blocks outbound HTTP). Those rows are marked **(verify)**. Check versions, licenses, layer names, and CORS headers before any of them is written into an execution plan.

## Summary

1. **The app's Python backend is in this repo, but its chat UI is not.** The app folder (`apps/agent-fpac-soil-openai-sdk/`) contains only the agent server and launcher. At app start, `scripts/start_app.py` clones `databricks/app-templates/e2e-chatbot-app-next` from the `main` branch at app start, then runs `npm install`, `npm run build`, and `npm run start`[^r-start]. Nothing pins the commit. Databricks now labels this chat UI page **Legacy**[^d-chatapp]. A map cannot be added to a UI that is re-downloaded unpinned on each start. **Step zero is to vendor and pin the frontend into the repo**, whatever map design is chosen.
2. **The backend can host map support routes.** The MLflow Agent Server is a FastAPI app, and Databricks documents adding routes to it the usual FastAPI way[^d-agentserver][^m-agentserver]. `start_server.py` exposes `app = agent_server.app` with `enable_chat_proxy=True`[^r-startserver]. That makes room for a file-conversion endpoint and an allowlisted tile/feature proxy next to `/invocations`. Route ordering against the chat proxy's catch-all is **unverified**.
3. **Chat-to-map wiring has two documented hooks.** `ResponsesAgentRequest.custom_inputs` carries data that is not chat text (the active AOI). `custom_outputs` returns data that is not chat text (map layers)[^d-custominputs][^m-responses]. Tool outputs also stream to the UI as function-call output items. The template already renders tool calls[^d-chatapp].
4. **Do not make the LLM copy coordinates.** The agent (`agent.py`) exposes MCP tools straight to the model, `tools=[]`[^r-agent]. Pasting a drawn polygon into the prompt costs tokens, can corrupt vertices, and writes geometry into model-visible inputs and traces. The recommended pattern is **explicit backend pre-dispatch**: a user clicks **Run screening**, the backend resolves the active AOI and calls the deployed MCP tool directly, and only a sanitized result summary is made available to chat. Raw AOI geometry must not pass through traced `/invocations` until an M1 spike proves pre-trace redaction and history exclusion. See section 4.2.
5. **Recommended stack (verify):** MapLibre GL JS (map), Terra Draw (drawing), Turf (client-side previews labeled as estimates), and a tiered file-import set. Tier 1 is GeoJSON and WKT in the browser. Tier 2 is KML/KMZ, GPX, zipped Shapefile, and CSV in the browser. Tier 3 is GeoPackage and File Geodatabase on the backend via `pyogrio`/GDAL.
6. **Soil overlay:** NRCS Soil Data Mart publishes the SSURGO map unit polygons as WMS/WFS (verify). Show the WMS as a continuous raster overlay at large map scales. Use the existing MCP tool `get_soil_polygons_by_geometry` for authoritative, clipped AOI polygons[^r-notebook]. Census TIGERweb ArcGIS services provide counties and 2020 Urban Areas. The MCP server already queries `TIGERweb/Urban/MapServer/0`[^r-config].
7. **The server stays authoritative.** Browser geometry previews, areas, and buffers are labeled estimates. Acreage, farmland class, LE/SA, and exemptions come only from MCP tool output. This keeps the split in `SPATIAL_VISUALIZATION_STRATEGY.md` section 3 and the preliminary-screening limit in ADR 0003.

## 1. Current state

| Item | Fact | Source |
| --- | --- | --- |
| Process model | `uv run start-app` starts the Python backend (Agent Server, port 8000), plus a Node frontend on `CHAT_APP_PORT=3000`. `API_PROXY=http://localhost:8000/invocations`. | [^r-start][^r-appyaml] |
| Frontend source | Not in `apps/agent-fpac-soil-openai-sdk/`. It is a runtime sparse clone of `databricks/app-templates` `e2e-chatbot-app-next`, unpinned `main`. Falls back to backend-only when the clone fails. | [^r-start] |
| Frontend tech | NextJS, React, and chat SDK. Streams output, renders tool calls, uses Databricks auth, optional Lakebase chat history. | [^d-chatapp] |
| Frontend limitation | "No support for image or other multi-modal inputs." There is no file attachment path today. | [^d-chatapp] |
| Backend | `AgentServer("ResponsesAgent", enable_chat_proxy=True)`; `app = agent_server.app` is FastAPI. | [^r-startserver][^d-agentserver] |
| Agent | OpenAI Agents SDK `Agent(tools=[], mcp_servers=[fpac])`; history normalized in `history.py`; SP auth to `mcp-fpac-soil`. | [^r-agent] |
| App runtime | Ubuntu 22.04, Python 3.11, Node.js 22.16, npm or pnpm via `package.json`. Medium = 2 vCPU / 6 GB (deployed size). | [^d-sysenv][^d-compute] |
| Egress | Build and runtime egress are open unless a network policy applies. With restricted egress, `registry.npmjs.org` and every external API domain must be allowlisted. | [^d-network] |
| MCP geometry input | Server parses GeoJSON and recognizes WKT prefixes (`POINT`, `POLYGON`, `MULTIPOLYGON`, `LINESTRING`, `MULTILINESTRING`, `GEOMETRYCOLLECTION`); equal-area math in EPSG:6933. | [^r-geometry] |
| MCP spatial output | `get_soil_polygons_by_geometry` returns a GeoJSON FeatureCollection with `properties.mukey`, `muname`, and `area_ac`. Corridor and polygon tools return summaries keyed by tool. | [^r-notebook] |
| Prior design | `SPATIAL_VISUALIZATION_STRATEGY.md` already names MapLibre/Leaflet for production, a layer-descriptor envelope (section 4), and 508 symbology (section 5). It does not cover the agent app or file import. | [^r-strategy] |
| Related work | The JS harness has no `public/wkt.js` or repo-local WKT/file-upload plan. Treat parser sharing between the harness and map widget as a new proposal that requires explicit scope and ownership before execution. | [^r-harness] |

## 2. Integration options

| Option | Description | Pros | Cons |
| --- | --- | --- | --- |
| **A. Fork the template UI (recommended)** | Vendor `e2e-chatbot-app-next` at a pinned commit into `apps/agent-fpac-soil-openai-sdk/frontend/`. Change `start_app.py` to use it instead of cloning. Add a split-pane `MapPanel` React component. | Keeps streaming, tool-call rendering, auth, and history. Map and chat share React state, so a drawn AOI is attached to the next message. | Owning a NextJS / chat SDK codebase. Upstream is Legacy, so fixes must be pulled by hand. Needs a `package-lock.json` for reproducible builds (same issue as harness H1). |
| B. Separate map page on the backend | Serve a static Vite/vanilla MapLibre page from FastAPI at `/map` and embed it beside or inside the chat with `postMessage`. | Small blast radius. The template can stay as is. | Two UIs, two state stores. Getting the AOI into the chat request still needs a UI change, or a server-side "active AOI" keyed by session. Iframe and CSP are uncertain inside Apps. |
| C. Own SPA | Replace the template with a repo-owned Vite + React app (chat + map), calling `/invocations` with streaming. | Full control, smaller dependency tree, no NextJS. | Rebuilds streaming parsing, tool-call display, auth identity, and history. Most work up front. |

Recommendation: **A**, with step zero (vendor + pin) as its own small plan so it can merge before any map work. If the vendored template proves too heavy to own, C is the fallback. B fits only a throwaway demo.

MLflow Agent Server routes needed in every option (FastAPI[^d-agentserver]):

* `POST /api/geo/convert`: Tier 3 file conversion (section 5).
* `GET /api/geo/proxy/{service}/...`: allowlisted proxy for overlay services that lack CORS or need egress control (section 6.3).
* `GET /api/geo/basemaps`: config-driven basemap and overlay catalog (section 6).

Verify that these routes take precedence over the chat proxy's catch-all.

## 3. Map client stack (verify)

| Need | Choice | License | Notes |
| --- | --- | --- | --- |
| Map renderer | MapLibre GL JS[^x-maplibre] | BSD-3-Clause | WebGL vector and raster. Raster sources take `{z}/{x}/{y}` and WMS `{bbox-epsg-3857}` URL templates. GeoJSON sources, style JSON, and `transformRequest` (to route through the proxy). React binding: `react-map-gl/maplibre` (MIT) or a thin custom hook. |
| Drawing / editing | Terra Draw[^x-terradraw] | MIT | Library-agnostic, has a MapLibre adapter. Modes: point, linestring, polygon, rectangle, circle, freehand, select/edit. Actively maintained. |
| Drawing (alt) | `@mapbox/mapbox-gl-draw` | ISC | Works with MapLibre after CSS class shims. Older API. Fallback only. |
| Client geometry ops | Turf.js[^x-turf] | MIT | `area`, `buffer`, `bbox`, `kinks` (self-intersection), `booleanValid`. Preview only, labeled as estimates. |
| Layer control / legend | Custom React component | n/a | Must render the section 5 symbology (color + pattern + text code) and a table equivalent. |
| Coordinate readout / entry | Custom | n/a | Keyboard and 508 path: type coordinates or paste WKT/GeoJSON instead of drawing. |

Why not Leaflet: Leaflet (BSD-2) is fine for raster plus small GeoJSON, but large SSURGO FeatureCollections and vector-tile basemaps run better on WebGL. `SPATIAL_VISUALIZATION_STRATEGY.md` already lists MapLibre for production[^r-strategy].

## 4. Chat and map integration

### 4.1 Map to agent (user AOI into the conversation)

Use `custom_inputs`, which `ResponsesAgentRequest` supports natively[^d-custominputs]:

```json
{
  "input": [{"role": "user", "content": "Screen my AOI for prime farmland"}],
  "custom_inputs": {
    "aois": [
      {"id": "aoi-1", "name": "Site A", "kind": "polygon", "source": "drawn",
       "geometry": {"type": "Polygon", "coordinates": [[[-93.65, 42.02], [-93.63, 42.02], [-93.63, 42.04], [-93.65, 42.02]]]}}
    ],
    "active_aoi_id": "aoi-1"
  }
}
```

This payload shape is a capability to test, not yet an approved production path. `custom_inputs` reaches the agent request handler and may be captured by automatic tracing before application code can sanitize it. Until M1 demonstrates pre-trace redaction and confirms that chat history excludes raw geometry, send AOIs only through the explicit screening path and keep ordinary chat turns geometry-free.

### 4.2 Explicit pre-dispatch pattern

Problem: MCP tools take `geojson` / `geometry` / `centerline` arguments that the LLM fills in. Passing a user polygon through the model:

* costs tokens in proportion to vertex count, on every turn;
* risks truncated or altered coordinates;
* writes the coordinates into MLflow traces (privacy, Section 1619; same concern as the Plan 34 AGENT span sanitization).

Pattern:

1. The UI keeps raw AOI geometry in browser state and requires an explicit **Run screening** action.
2. A dedicated backend screening path resolves the selected AOI and calls the deployed MCP tool directly. It does not add local wrapper tools to the agent, preserving ADR 0012's tools-only client boundary.
3. The backend returns the authoritative MCP result and structured map layers to the UI. If the user continues in chat, only a bounded, sanitized analysis summary and opaque analysis/AOI identifiers enter the model context.
4. Before implementation, M1 must prove where `custom_inputs`, request bodies, MCP arguments, and outputs appear in MLflow traces and optional Lakebase history. The accepted path must redact geometry before trace capture, not merely after handler entry.
5. Sanitized telemetry may retain an opaque hash, geometry type, and vertex count. It must not retain coordinates, WKT/GeoJSON, bounding boxes, parcel properties, or other location-bearing values.

An MCP-side `aoi_id` input would require server state and conflicts with the stateless direction, so it is not recommended. Raw coordinate-based MCP tools remain available for ordinary explicit tool calls outside the map workflow.

### 4.3 Agent to map (results onto the map)

Two layers, both recommended:

1. **Server visualization contract.** Spatially enabled MCP tools must return the structured `map` envelope required by `SPATIAL_VISUALIZATION_STRATEGY.md` section 4, including bounded geometry, layer descriptors, legends, source, vintage, and authority metadata. The agent app passes that contract through in `custom_outputs.map_layers` or an equivalent non-model response path; it must not reconstruct authoritative layers from prose or tool-specific summary fields. **Verify** how the template's chat SDK stream adapter surfaces `custom_outputs`. If it drops them, the forked UI must add that path.
2. **UI rendering path.** The template already renders tool calls[^d-chatapp]. In the fork, add a renderer for the server-provided `map` envelope and a "Show on map" action next to the tool-call card. A generic GeoJSON renderer may remain a development aid, but it is not a substitute for the required source, authority, legend, and data-vintage contract.

Layer sources from current tools[^r-notebook]:

| Tool | Map layer |
| --- | --- |
| `get_soil_polygons_by_geometry` | Clipped SSURGO polygons; style by `farmlndcl` (needs a class join if not in properties); label `mukey`. |
| `analyze_farmland_by_polygon` | AOI outline, authoritative map-unit layers, and summary table through the required server `map` envelope. |
| `check_urban_area_exemption` | Intersecting urban geometry through the required server `map` envelope; a direct TIGERweb layer may provide context but cannot stand in for the agent-returned result. |
| `analyze_corridor_fppa` | Authoritative buffered corridor and per-county segment layers through the required server `map` envelope; any client-side Turf buffer remains a labeled preview only. |
| `get_farmland_classification_by_point` | Point marker + popup. |

Gap: most tools currently return summaries, not the geometry required for agent-returned overlays. Adding the strategy section 4 `map` envelope to every spatially enabled tool is a required Phase 8 prerequisite for the results-on-map milestone, bounded by vertex and feature limits. This is MCP surface work and requires response-model, README, `manifest.yaml`, `server.json`, and contract-test updates per root `AGENTS.md`.

## 5. Spatial file input

### 5.1 Format tiers (verify libraries)

| Tier | Formats | Where | Library | License |
| --- | --- | --- | --- | --- |
| 1 (MVP) | `.geojson`, `.json` (Feature, FeatureCollection, bare Geometry) | Browser | native `JSON.parse` + validation | n/a |
| 1 (MVP) | `.wkt`, `.txt`, paste box | Browser | a newly planned shared parser, or `wellknown`; assign cross-client ownership before selecting | n/a / BSD-2 |
| 2 | `.kml`, `.kmz` | Browser | `@tmcw/togeojson`[^x-togeojson] + `JSZip` for KMZ | BSD-2 / MIT or GPLv3 dual |
| 2 | `.gpx` | Browser | `@tmcw/togeojson` | BSD-2 |
| 2 | Zipped Shapefile (`.zip` with `.shp/.shx/.dbf/.prj`) | Browser | `shpjs`[^x-shpjs] (reprojects via `.prj` + proj4) | MIT |
| 2 | `.csv` with lat/lon or WKT column | Browser | `papaparse` | MIT |
| 2 | `.fgb` FlatGeobuf | Browser | `flatgeobuf` | BSD-2 |
| 3 | `.gpkg` GeoPackage | Backend | `pyogrio` (bundled GDAL wheels)[^x-pyogrio] | MIT (GDAL MIT/X) |
| 3 | `.gdb.zip` File Geodatabase (OpenFileGDB driver) | Backend | `pyogrio` | same |
| 3 | Any Tier 2 format the browser parser rejects | Backend | `pyogrio` | same |

Tier 3 alternative: `gdal3.js` (GDAL in WebAssembly) in the browser. It avoids the backend, but the bundle is large (several MB, verify), so a backend endpoint is preferred. `pyogrio` must be added to the app's `pyproject.toml` + `uv.lock` (ADR 0013 PyPI pin applies). Wheels must exist for Linux and Python 3.11 (verify).

### 5.2 Normalization rules (all tiers)

1. Output one internal type: a GeoJSON FeatureCollection in EPSG:4326 (RFC 7946[^x-rfc7946]), with lon/lat order, right-hand winding, and properties kept as strings.
2. CRS: reproject when `.prj` / GPKG SRS / KML is not WGS84. Reject unknown CRS with a clear message; never guess.
3. Geometry types: points, lines, and polygons. Multi-part is allowed. Z/M dropped.
4. Feature selection: if more than one feature is uploaded, list them (with a properties preview) and let the user pick one AOI, or several as alternatives, or "dissolve all". The harness rule "multi-feature FeatureCollection = error" fits a single text field, not the map UI. Record this difference in the plan.
5. Limits (configurable): file size (for example 10 MB browser, 50 MB backend), feature count, vertex count per AOI. These should match server-side limits in `geometry.py` (check its validation constants).
6. Validation preview: Turf `kinks` / `booleanValid`, plus an area estimate. The server still repairs and validates authoritatively (`make_valid`)[^r-geometry].
7. Privacy: uploads should stay in browser and request scope, but this is a design requirement rather than a current guarantee. ADR 0010 states that `privacy.py` performs field-name PII detection and does not implement coordinate redaction. Do not enable the AOI request path until M1 proves raw geometry is absent from MLflow traces and Lakebase history. Uploaded parcels can be producer data under Section 1619.
8. Security: treat properties as untrusted text (no HTML injection in popups). Unzip with entry-count and size caps (zip bomb). Never pass file paths to GDAL from user input; write to a temp dir under the request.

## 6. Basemaps and overlays

### 6.1 Basemap catalog

Serve a JSON catalog from `GET /api/geo/basemaps` (sourced from a repo file, editable without a UI rebuild). Allow a user-supplied XYZ/WMTS/WMS URL in a "custom basemap" dialog. That covers the "arbitrary basemap" requirement.

| Basemap | Type | Notes (verify) |
| --- | --- | --- |
| USGS The National Map (USGSTopo, USGSImageryOnly, USGSImageryTopo, USGSShadedReliefOnly)[^x-tnm] | ArcGIS cached tiles / WMTS | US federal, public domain, no key. Good default for a USDA app. |
| OpenFreeMap or self-hosted Protomaps PMTiles[^x-protomaps] | Vector tiles | No key. PMTiles can be served from a UC Volume or the app (range requests; verify Apps support). |
| OpenStreetMap standard tiles | Raster XYZ | OSM tile usage policy forbids heavy app use. Do not make it the default. |
| Esri World Imagery / commercial | Raster | Terms and attribution, possibly a key. User-supplied only. |
| Custom (user URL) | XYZ / WMS / WMTS | Template placeholders validated (`{z}{x}{y}` or `{bbox-epsg-3857}`); https only; optional attribution field. |

### 6.2 Overlay catalog

| Overlay | Service (verify exact URLs and layer names) | Render mode | Use |
| --- | --- | --- | --- |
| SSURGO soil map units (continuous) | NRCS Soil Data Mart / SDA spatial services: WMS (layer such as `mapunitpoly`) and WFS[^x-sdmspatial] | WMS raster at zoom >= ~12; WFS GeoJSON for small bboxes only | Context while drawing; click to identify `mukey` -> `get_farmland_classification_by_mukey`. |
| SSURGO soils (authoritative AOI) | MCP `get_soil_polygons_by_geometry`[^r-notebook] | GeoJSON, styled by farmland class | Result layer for the AOI. |
| 2020 Census Urban Areas | TIGERweb `TIGERweb/Urban/MapServer` (server uses layer 0)[^r-config][^x-tigerweb] | ArcGIS `export` raster or `query?f=geojson` by bbox | Context; click to turn into an exemption check AOI. |
| Counties | TIGERweb `State_County` MapServer or `tigerWMS_Current` WMS[^x-tigerweb] | Same | Context; corridor county segments; "select county as AOI". |
| PLSS / parcels (optional) | BLM CadNSDI (PLSS); parcels are state-specific | WMS / ArcGIS | Out of scope for MVP. |
| Agent results | `custom_outputs.map_layers` (section 4.3) | GeoJSON | Analysis output. |

### 6.3 CORS and the proxy

MapLibre loads raster tiles with `fetch` / image bitmaps, so a cross-origin tile host must send CORS headers or the tiles fail. Whether NRCS SDM and TIGERweb send `Access-Control-Allow-Origin` is **unverified**. Test each service from the browser first.

The backend proxy route (section 2) gives:

* CORS-free access for services without headers;
* one egress point, so Enterprise network policies only allowlist the app, plus a domain list for `system.access.outbound_network` review[^d-network];
* response caching and rate limiting toward federal services (SDA has a nightly maintenance window, during which it returns HTML with HTTP 200; see the project memory note on `SDAClient`).

Rule: the proxy only forwards to hosts in the overlay/basemap catalog (no open proxy). User-supplied custom basemaps load directly from the browser and are never proxied.

### 6.4 Selecting an AOI from an overlay

* Click a county or urban-area feature -> backend `query?f=geojson&outFields=...&returnGeometry=true` (via proxy) -> becomes an AOI (`source: "tigerweb"`).
* Click a soil polygon (WFS) -> AOI or `mukey` lookup.
* Large geometries (counties) need simplification before they are sent as AOIs. Warn on vertex count.

## 7. Drawing and AOI interactions

* Draw: point, line (corridor centerline), polygon, rectangle. Edit vertices; delete; undo.
* Corridor helper: buffer distance and units next to a drawn line, with a Turf buffer preview labeled "estimate; server computes in EPSG:6933"[^r-geometry].
* AOI list panel: name, kind, source (drawn / uploaded / selected / agent), estimated acres, toggle visibility, "use as alternative", export as GeoJSON.
* Alternatives: two or more line AOIs map to `analyze_corridor_fppa(alternatives=[...])` (CORR-02 pattern)[^r-notebook].
* Chat hooks: "Attach AOI to message" chip; quick actions ("Screen this AOI", "Soil polygons", "Urban exemption check", "Preliminary LESA") that pre-fill a prompt and set `active_aoi_id`.
* Agent-suggested geometry: when a tool response returns geometry, "Add to AOIs" turns a result into a new input.

## 8. Accessibility, authority, and UX guardrails

* Section 508: the map canvas is not accessible by itself. Give every layer a table view, keyboard paths for every action (coordinate entry, file upload, AOI list), visible focus, and color + pattern + text codes (strategy section 5)[^r-strategy].
* Authority banner on the map: render the `regulatory_notice` returned by the authoritative MCP screening response. Do not define a shorter client-owned substitute; a missing notice is a response-contract failure under ADR 0003.
* Data vintage and source attribution per layer (SSURGO vintage, TIGER 2020).
* Partial-failure states: overlay or tool unavailable is shown per layer, never silently blank.

## 9. Dependencies and risks

| # | Risk | Mitigation |
| --- | --- | --- |
| R1 | Vendored template is large and Legacy[^d-chatapp] | Pin commit, track upstream SHA in README, keep map code in separate components/folders to ease rebases; fallback option C. |
| R2 | Unknown whether chat SDK adapter passes `custom_inputs` / `custom_outputs` | Spike first (Plan task 1): send `custom_inputs` from UI and read `custom_outputs` back end to end. |
| R3 | Chat proxy may shadow new FastAPI routes | Spike: register `/api/geo/health` and confirm it is reachable through the Apps URL. |
| R4 | CORS / egress to NRCS and Census services | Browser test per service; proxy; record required domains for network policy. |
| R5 | Token cost and coordinate corruption | Explicit backend pre-dispatch (section 4.2); never route raw coordinates through the LLM. |
| R6 | Privacy of uploaded parcels in traces/history | Blocking M1 spike: identify trace capture order, prove pre-trace redaction, and inspect MLflow/Lakebase artifacts for coordinate, WKT/GeoJSON, bounding-box, and parcel-property leakage. Current `privacy.py` is insufficient for this path. |
| R7 | npm supply chain / reproducibility | Commit lockfile; `npm ci`; Dependabot npm entry; license check in CI. |
| R8 | Root CI excludes `apps/` (ADR 0012) | Add frontend `lint`, `typecheck`, `test` to `make app-check` and the `agent-app` CI job. |
| R9 | Federal service availability (SDA nightly window, TIGERweb outages) | Per-layer error states; cache; optional fixture layers (strategy section 6). |

## 10. Suggested phasing for the master plan

| Phase | Scope | Exit criteria |
| --- | --- | --- |
| M0 Vendor and pin UI | Copy template at a pinned SHA into `frontend/`; `start_app.py` uses it; lockfile; CI build. No behavior change. | Deployed app identical to today; no runtime clone. |
| M1 Spikes | R2 (`custom_inputs`/`custom_outputs` round trip), R3 (FastAPI route through proxy), R4 (CORS for SDM WMS, TIGERweb), and R6 (trace/history capture order and pre-trace coordinate redaction). | Written findings appended to this note; captured trace/history evidence contains no raw coordinates, WKT/GeoJSON, bounding boxes, or parcel properties before AOI integration may proceed. |
| M2 Map MVP | Split pane MapLibre; USGS basemap + custom URL; Terra Draw polygon/line/point; GeoJSON + WKT upload; AOI list; explicit backend **Run screening** pre-dispatch. | User draws or uploads an AOI and receives an MCP screening result without coordinates entering the prompt, model context, trace, or chat history. |
| M3 Required server map contract | Add the strategy section 4 `map` envelope to every spatially enabled MCP tool, with bounded GeoJSON, legends, source/vintage, authority metadata, and the centralized `regulatory_notice`. | Polygon, soil, urban, and corridor contract fixtures expose complete map layers; metadata parity and MCP contract tests pass. |
| M4 Results on map | Pre-dispatch result handling; pass the server `map` envelope through `custom_outputs.map_layers` or an equivalent non-model response path; farmland-class symbology + table view; "Show on map" for tool cards. | POLY-01/POLY-02, urban, and corridor results render from authoritative MCP output with legends, tables, source/vintage, authority, and the returned notice. |
| M5 Context overlays | Catalog endpoint; proxy; SSURGO WMS; TIGERweb counties + urban areas; click-to-identify; select county/urban area as AOI. | Context overlays toggle, identify works, and failures are shown per layer without being mistaken for agent-returned result geometry. |
| M6 More formats | Tier 2 browser parsers; Tier 3 `/api/geo/convert` with `pyogrio`. | KML/KMZ, GPX, zipped SHP, CSV, GPKG, and FGDB fixtures pass tests. |
| M7 Hardening | 508 review, trace sanitization tests, CSP, limits, and eval cases for the explicit AOI screening path. | Accessibility checklist, privacy evidence, and eval cases pass. |

## 11. Open decisions for the user

1. Option A (fork template) vs C (own SPA). (open: Track A)
2. Allow user-supplied basemap URLs in production, or catalog only? (open: Track A)
3. Tier 3 formats on the backend (adds GDAL to the app image) in scope for the first release? (open: Track A)
4. Persist AOIs across sessions (Lakebase) or keep them session-only (privacy default)? (open: Track A)
5. Should required M3 server-map-contract work be its own orchestration before the agent-app M4 rendering work, or the first wave of one orchestration? (open: Track A)
6. Plan number: check for collisions before picking one (Plans 28-30 were taken by other work; latest seen here is 36). (resolved: Plan 37)

## Sources

[^r-start]: `apps/agent-fpac-soil-openai-sdk/scripts/start_app.py` L147-179 (clone), L224-272 (npm install/build/start, `API_PROXY`).
[^r-appyaml]: `apps/agent-fpac-soil-openai-sdk/app.yaml` (`API_PROXY`, `CHAT_APP_PORT=3000`, `FPAC_MCP_URL`).
[^r-startserver]: `apps/agent-fpac-soil-openai-sdk/agent_server/start_server.py` L18-20.
[^r-agent]: `apps/agent-fpac-soil-openai-sdk/agent_server/agent.py` L93-157.
[^r-geometry]: `src/fpac_soil_mcp/geometry.py` L1-80 (WKT prefixes, EPSG:6933 transformers, `make_valid`).
[^r-config]: `src/fpac_soil_mcp/config.py` L49-52 (`tigerweb_rest_url` = `https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Urban/MapServer/0`), L17-19 (SDA tabular URL).
[^r-notebook]: Notebook "Test fpac-soil-mcp MCP Server" cells POLY-01, POLY-02, CORR-01, CORR-02 (tool names, arguments, response keys).
[^r-strategy]: `planning/SPATIAL_VISUALIZATION_STRATEGY.md` sections 2-6.
[^r-harness]: `eval/fpac_soil_mcp_harness/` listing (no `public/wkt.js` and no repo-local WKT/file-upload plan).
[^d-chatapp]: Databricks, "Build and share a chat UI with Databricks Apps" (Legacy), https://docs.databricks.com/aws/en/agents/custom-agents/chat-app/
[^d-agentserver]: Databricks, "Agent Server: Add custom endpoints", https://docs.databricks.com/aws/en/agents/deploy/agent-server/
[^d-custominputs]: Databricks, "Run agents on Databricks Apps using the legacy agent server: Custom inputs and outputs", https://docs.databricks.com/aws/en/agents/custom-agents/author-agent/
[^d-sysenv]: Databricks, "Databricks Apps environment", https://docs.databricks.com/aws/en/dev-tools/databricks-apps/system-env/
[^d-compute]: Databricks, "Configure compute resources for a Databricks app", https://docs.databricks.com/aws/en/dev-tools/databricks-apps/compute-size/
[^d-network]: Databricks, "Configure networking for Databricks Apps", https://docs.databricks.com/aws/en/dev-tools/databricks-apps/networking/
[^m-agentserver]: MLflow, "MLflow Agent Server" (FastAPI server hosting `/invocations`), https://mlflow.org/docs/latest/genai/serving/agent-server
[^m-responses]: MLflow, "ResponsesAgent Introduction" (`custom_outputs`, output item helpers), https://mlflow.org/docs/latest/genai/flavors/responses-agent-intro/index.html
[^x-maplibre]: MapLibre GL JS, https://maplibre.org/maplibre-gl-js/docs/ and https://github.com/maplibre/maplibre-gl-js (verify).
[^x-terradraw]: Terra Draw, https://github.com/JamesLMilner/terra-draw (verify).
[^x-turf]: Turf.js, https://turfjs.org/ (verify).
[^x-togeojson]: `@tmcw/togeojson`, https://github.com/placemark/togeojson (verify).
[^x-shpjs]: `shpjs`, https://github.com/calvinmetcalf/shapefile-js (verify).
[^x-pyogrio]: pyogrio, https://pyogrio.readthedocs.io/ (verify wheels for Linux / Python 3.11 and driver list incl. OpenFileGDB, GPKG).
[^x-rfc7946]: IETF RFC 7946, The GeoJSON Format, https://datatracker.ietf.org/doc/html/rfc7946
[^x-tnm]: USGS The National Map basemap services, https://basemap.nationalmap.gov/arcgis/rest/services (verify).
[^x-protomaps]: Protomaps PMTiles, https://docs.protomaps.com/ ; OpenFreeMap, https://openfreemap.org/ (verify).
[^x-sdmspatial]: USDA NRCS Soil Data Access web services (WMS/WFS), https://sdmdataaccess.nrcs.usda.gov/WebServiceHelp.aspx (verify layer names, CORS, zoom limits).
[^x-tigerweb]: US Census Bureau TIGERweb REST and WMS services, https://tigerweb.geo.census.gov/tigerwebmain/TIGERweb_restmapservice.html (verify).
