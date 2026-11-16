# EXECUTION PLAN 40: Vendor the Agent UI and Validate Map Integration Boundaries

## Goal & Scope

**Goal:** Start customizing the Databricks FPAC Soil agent app so it can later host an interactive map, beginning with a repo-owned, pinned chat frontend and the integration/privacy evidence required before AOI geometry can safely flow between the map and the agent. This orchestration intentionally stops before implementing the map MVP or server map-result contract.

**In scope:**

- M0: vendor and pin the existing `e2e-chatbot-app-next` frontend under the agent app.
- Change `scripts/start_app.py` to use the pinned local frontend and preserve current startup behavior.
- Add reproducible frontend dependency/build checks and document the vendored-template decision.
- M1 spikes:
  - `custom_inputs` / `custom_outputs` round trip.
  - custom FastAPI route reachability through the Agent Server chat proxy.
  - CORS/egress feasibility for planned basemap and federal overlay services.
  - trace/history redaction and exclusion of raw AOI geometry.
- Record the AOI handoff pattern as explicit backend pre-dispatch, with session-only AOIs.
- Preserve the preliminary-screening authority boundary and separate-MCP-client boundary.

**Out of scope:**

- MapLibre, Terra Draw, drawing controls, split-pane map UI, layer toggles, legends, or result rendering (M2/M4).
- The server-side visualization `map` envelope for spatial MCP tools (M3 / Phase 8 server work).
- Backend GeoPackage/File Geodatabase conversion or `pyogrio`/GDAL (Tier 3).
- Browser import implementation, including shared WKT parser ownership and normalization rules; record this as a follow-up dependency for M2.
- AOI persistence in Lakebase or another durable store.
- Production deployment, custom basemap catalog implementation, or unrestricted external URL proxying.
- Workbench map features and a separate replacement SPA.
- Any superseding ADR; M0 and M1 create the ADRs identified by the master plan.

**Verbatim constraints from the request and decisions:**

- “vendor-template”
- “custom-urls”
- “browser-mvp”
- “session-only”
- “m0-m1”
- Maximum concurrent workers: `3`.
- “recommended” acceptance: automated app checks plus documented manual/integration evidence.
- Worker policy: use harness defaults and escalation ladder.

## Reconnaissance Log

Captured 2026-10-27 from `D:\workspace\fpac-soil-mcp`.

- `apps\agent-fpac-soil-openai-sdk\scripts\start_app.py` is 345 lines and currently clones `databricks/app-templates` at runtime, using an unpinned `main` checkout.
- `apps\agent-fpac-soil-openai-sdk\agent_server\agent.py` is 167 lines and currently uses `tools=[]` with a direct MCP server connection; it does not consume `custom_inputs` or emit map-oriented `custom_outputs`.
- `agent_server\start_server.py` is 25 lines and exposes `agent_server.app` with `enable_chat_proxy=True`; no custom map routes currently exist.
- The app has no repo-owned frontend or `package.json`; the app project uses `uv.lock`, while the runtime-cloned frontend installs npm dependencies dynamically.
- The app convention is `make app-check`; direct root-level `uv run pytest apps\...` is not a valid baseline because it does not activate the app project/import path.
- App tests are offline and mocked; `make app-test` uses the committed app lockfile. Frontend checks must be added to the app-owned validation path when frontend files become repo-owned.
- Accepted ADR 0012 requires the agent app to remain a separate MCP client. ADR 0003 requires preliminary-screening boundaries. ADR 0010 requires privacy-aware public-payload handling. ADR 0013 requires public PyPI as the default uv index.
- The current master plan Track A explicitly says M0 precedes M1; AOI integration is blocked until R6 proves pre-trace redaction and history exclusion.
- Existing plan/research references: `planning\MASTER_PLAN.md` Track A and Phase 8; `planning\RESEARCH_MAP_WIDGET_AGENT_APP.md` sections 2, 4, 8-11; `planning\SPATIAL_VISUALIZATION_STRATEGY.md` sections 3-6.
- Baseline attempt `uv run pytest apps\agent-fpac-soil-openai-sdk\tests -q` failed during collection with missing app import path and `ruamel` dependency; the canonical `make app-test` command remains the required baseline and acceptance command.

## Decision Log

1. **D1, 2026-10-27, UI architecture:** Vendor and pin the existing Databricks chat template. Do not replace it with a new SPA.
2. **D2, 2026-10-27, orchestration scope:** Plan 40 covers M0 and M1 only. M2/M3/M4 remain subsequent work after spike findings.
3. **D3, 2026-10-27, basemap direction:** The eventual map may support validated custom HTTPS XYZ/WMTS/WMS URLs in addition to a curated catalog. Plan 40 validates the security and networking implications but does not implement the feature.
4. **D4, 2026-10-27, import scope:** The first map release is browser GeoJSON/WKT. Backend GeoPackage/FileGDB conversion is deferred.
5. **D5, 2026-10-27, AOI lifecycle:** AOIs remain session-only. No Lakebase persistence is included.
6. **D6, 2026-10-27, AOI handoff:** Use explicit backend pre-dispatch; do not copy raw geometry into the LLM prompt or ordinary chat history.
7. **D7, 2026-10-27, validation:** Require `make app-check`, frontend lint/typecheck/build, focused offline tests, and documented integration evidence for route, service, and privacy spikes.
8. **D8, 2026-10-27, execution policy:** Maximum three concurrent workers; use default worker models and the wave-orchestration escalation ladder.

## Wave & Dependency Table

| Wave | Task | Title | Files in scope | Depends on |
|---|---|---|---|---|
| 1 | 40.1.1 | Vendor and pin the chat frontend | `apps\agent-fpac-soil-openai-sdk\frontend\`, `scripts\start_app.py`, app package/CI docs, one new ADR | none |
| 2 | 40.2.1 | Prove request/output and privacy boundaries | `agent_server\agent.py`, `agent_server\history.py`, `frontend\`, app tests, `planning\evidence\40.2.1-aoi.md`, `planning\decisions\40.2.1-aoi.md` | 40.1.1 |
| 2 | 40.2.2 | Prove custom route reachability | `agent_server\start_server.py`, `tests\test_custom_routes.py`, `planning\evidence\40.2.2-routes.md` | 40.1.1 |
| 2 | 40.2.3 | Verify map-service networking constraints | `planning\evidence\40.2.3-networking.md` | none |
| 3 | 40.3.1 | Review, validate, and freeze M1 findings | `planning\STATE_40.md` and fixes to Plan 40 files only | 40.2.1, 40.2.2, 40.2.3 |

Wave 2 tasks have pairwise-disjoint files. Shared app checks and any live/browser checks run serially at the wave gate. Each task writes only its own evidence file; `STATE_40.md` is reserved for Wave 3.

## Hazards

- The vendored template is legacy and potentially large; pin its upstream commit and keep map-specific code isolated in new components.
- The template may require Node/npm versions or environment variables not currently documented; preserve the existing startup contract and record deviations.
- The chat proxy may shadow custom FastAPI routes; route verification must use the actual app path, not only unit tests.
- `custom_inputs` may be captured by tracing before handler code can sanitize it; a handler-level sanitizer alone is insufficient evidence.
- Federal map services may lack CORS or require egress allowlists. No service should be silently replaced with a blank layer.
- User-supplied basemap URLs create SSRF and attribution risks; this plan validates constraints only and does not authorize an unrestricted proxy.
- Do not add raw AOI coordinates to prompt text, ordinary history, logs, traces, or persistent storage.
- Do not touch frozen plans, unrelated MCP server code, the workbench, or untracked planning artifacts.

## Task Specifications

### 40.1.1 — Vendor and pin the chat frontend

**Repository:** `D:\workspace\fpac-soil-mcp`

**Files in scope**

- Must edit: `apps\agent-fpac-soil-openai-sdk\scripts\start_app.py`, `apps\agent-fpac-soil-openai-sdk\README.md`, `apps\agent-fpac-soil-openai-sdk\AGENTS.md`, `Makefile`, `.github\workflows\ci.yml`.
- Can create: `apps\agent-fpac-soil-openai-sdk\frontend\**`, frontend lockfile, `docs\decisions\0014-vendored-agent-app-frontend.md`, `planning\tasks\40.1.1.todo.md`.
- Temp/scratch: an explicitly named untracked staging directory under `apps\agent-fpac-soil-openai-sdk\.development\`; remove it before reporting.

**Depends on:** none.

**Specification:** Vendor the exact upstream chat template currently used by `start_app.py`, record its commit SHA, make startup use the repo-owned copy without runtime cloning, preserve `API_PROXY`, ports, auth, streaming, and backend-only fallback behavior where applicable, and add reproducible frontend checks (`npm ci`, lint/typecheck/build or the closest template-supported equivalents). Do not add map behavior yet.

**Grep anchors:** `clone_frontend_if_needed`, `API_PROXY`, `CHAT_APP_PORT`, frontend `package.json` scripts, app README deployment/local-development sections, ADR 0012.

**Acceptance:** `make app-check`; `cd apps\agent-fpac-soil-openai-sdk\frontend && npm ci && npm run lint && npm run typecheck && npm run build` (or exact scripts discovered in the pinned package); startup path inspection confirms no runtime clone; pinned SHA and ownership decision are documented; no map behavior is introduced.

### 40.2.1 — Prove request/output and privacy boundaries

**Repository:** `D:\workspace\fpac-soil-mcp`

**Files in scope**

- Must edit: `apps\agent-fpac-soil-openai-sdk\agent_server\agent.py`, `apps\agent-fpac-soil-openai-sdk\agent_server\history.py`, `apps\agent-fpac-soil-openai-sdk\frontend\`, `apps\agent-fpac-soil-openai-sdk\tests\test_aoi_handoff.py`.
- Can create: `planning\tasks\40.2.1.todo.md`, `planning\evidence\40.2.1-aoi.md`, `planning\decisions\40.2.1-aoi.md`.
- Do not touch: MCP server tools, `privacy.py`, frontend components, deployment resources.

**Depends on:** 40.1.1.

**Specification:** Spike the end-to-end UI-to-handler handling of `custom_inputs` and handler-to-UI handling of `custom_outputs`, including whether the chat SDK adapter preserves a non-model `map_layers`/equivalent field. Determine where request data enters tracing/history, and implement or document only the minimum safe boundary needed to prove raw AOI geometry is excluded from ordinary model context, traces, and history. The accepted design must use explicit backend pre-dispatch, opaque identifiers/metadata where telemetry is needed, session-only AOIs, and no raw coordinates in prompts. Do not implement M3's authoritative map envelope.

**Grep anchors:** `invoke_handler`, `stream_handler`, `ResponsesAgentRequest`, `ResponsesAgentResponse`, `normalize_history_items`, MLflow autologging setup.

**Acceptance:** `cd apps\agent-fpac-soil-openai-sdk && uv run --frozen --python 3.11 pytest tests\test_aoi_handoff.py -q`; a frontend/template integration probe sends `custom_inputs` and observes `custom_outputs.map_layers` or records the exact adapter loss; documented evidence demonstrates the capture order and absence of coordinates, WKT/GeoJSON, bounding boxes, and parcel properties; the AOI-handoff decision record identifies the explicit backend pre-dispatch path and pass/fail blockers. If the platform cannot prove pre-trace redaction, stop and mark AOI integration blocked rather than weakening the constraint.

### 40.2.2 — Prove custom route reachability

**Repository:** `D:\workspace\fpac-soil-mcp`

**Files in scope**

- Must edit: `apps\agent-fpac-soil-openai-sdk\agent_server\start_server.py`, `apps\agent-fpac-soil-openai-sdk\tests\test_custom_routes.py`.
- Can create: `planning\tasks\40.2.2.todo.md`, `planning\evidence\40.2.2-routes.md`.
- Do not touch: `scripts\start_app.py`, frontend files, MCP server routes.

**Depends on:** 40.1.1.

**Specification:** Add the smallest safe health/probe endpoint needed to determine whether custom FastAPI routes are reachable through the Agent Server chat proxy. Do not implement file conversion, tile proxying, basemap catalogs, or unrestricted forwarding. Verify route ordering and document compatibility with future `/api/geo/basemaps` and constrained `/api/geo/proxy/{service}` boundaries.

**Grep anchors:** module-level `app = agent_server.app`, `AgentServer("ResponsesAgent", enable_chat_proxy=True)`, existing app route/test conventions.

**Acceptance:** `cd apps\agent-fpac-soil-openai-sdk && uv run --frozen --python 3.11 pytest tests\test_custom_routes.py -q`; a documented local or deployed probe reaches the custom route without being swallowed by the chat proxy; failure is explicit and leaves future map routes blocked.

### 40.2.3 — Verify map-service networking constraints

**Repository:** `D:\workspace\fpac-soil-mcp`

**Files in scope**

- Must edit: none.
- Can create: `planning\tasks\40.2.3.todo.md`, `planning\evidence\40.2.3-networking.md`.
- Do not touch: production map components, unrestricted proxy code, deployment networking policy.

**Depends on:** none.

**Specification:** Test the planned USGS basemap, USDA SSURGO service, and Census TIGERweb service from the intended browser/app context where available. Record CORS behavior, HTTPS/URL-template requirements, attribution requirements, egress domains, and whether a constrained proxy is required. Include the security implications of validated custom basemap URLs; do not approve arbitrary forwarding.

**Grep anchors:** map research sections 6.1-6.3; app networking configuration; existing live-network test markers.

**Acceptance:** `planning\evidence\40.2.3-networking.md` records an explicit available/unavailable/unknown result with evidence and next action for each service; no service is represented as usable solely from documentation; custom URL constraints include HTTPS, allowlisting/validation, attribution, and SSRF considerations.

### 40.3.1 — Review, validate, and freeze M1 findings

**Repository:** `D:\workspace\fpac-soil-mcp`

**Files in scope**

- Must edit: `planning\STATE_40.md`; fixes only to Plan 40 artifacts or files changed by tasks 40.2.1-40.2.3 when required by verification.
- Can create: `planning\tasks\40.3.1.todo.md`.

**Depends on:** 40.2.1, 40.2.2, 40.2.3.

**Specification:** Apply independent spec and standards reviews to the completed M0/M1 work. Confirm every user decision is represented, wave file scopes are disjoint, acceptance commands are reproducible, and AOI work remains blocked unless R6 passes. Run the required app checks and document any environment-limited evidence without converting unknowns into success.

**Grep anchors:** Plan 40 Goal & Scope, Decision Log, Wave Table, all task acceptance sections, Track A in `MASTER_PLAN.md`.

**Acceptance:** `make app-check` passes from the repository root or the exact baseline blocker is recorded; frontend checks pass; changed-file scope is clean; STATE_40 has concise reports, no unresolved silent failures, and a clear handoff to the next orchestration.
