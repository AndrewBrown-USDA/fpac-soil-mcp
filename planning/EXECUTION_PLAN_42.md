# EXECUTION PLAN 42: Agent App Map Panel MVP with Out-of-Band AOI Screening

## Goal & Scope

**Goal:** Give the agent app a map panel to the left of the chat so a user can draw or paste an AOI, run a preliminary FPPA screening against the deployed MCP server, see the result on the map and in a table, and bring a geometry-free summary of that result into the chat. Build it on `feature/agent-app-map1` and try it end to end on the deployed app before the PR merges, so we can decide whether to commit to the vendored frontend and server (ADR 0015) and the AOI handoff pattern (ADR 0016).

**In scope:**

- Clarify ADR 0015: we own the vendored frontend from a pinned upstream base; local changes are allowed and listed; `package-lock.json` is regenerated when dependencies change. Status `Proposed`.
- Draft ADR 0016 (AOI handoff, the Track A M1 exit item). Status `Proposed`.
- Backend `POST /api/geo/screen`: calls the deployed MCP tools directly (no model), returns a browser-only `display` part and a server-built, geometry-free `chat_summary`.
- Frontend map panel (MapLibre GL JS + Terra Draw) left of the chat: one public USGS basemap, polygon and rectangle drawing with edit/delete/undo, GeoJSON paste/upload, one session-only AOI, Run screening, AOI outline plus clipped soil polygons coloured by farmland class, legend, results table, `regulatory_notice`, preliminary-screening label.
- Summary to chat: the panel puts `chat_summary` into the chat input; the user reviews and sends it. Superseded by D9-D12 (2026-10-31): the active AOI is session context sent with every chat turn, and the agent can run tools on it.
- Offline privacy tests, per-wave check gates, a deployed trial, and close-out (ADRs to `Accepted`, master plan Track A status).

**Out of scope (explicit deferrals):**

- M3 server `map` envelope and any MCP server change (D3). Likely the next plan if this goes well.
- Lines/corridors, points, freehand, WKT/KML/SHP/other formats, AOI list or alternatives, custom basemap URLs, overlay catalog, `/api/geo/proxy`, `/api/geo/convert` (D4).
- AOI persistence beyond the browser tab session, Lakebase, server-side AOI store (Plan 40 D5; D10).
- `custom_outputs`, span-processor redaction (D11). (`custom_inputs` is now in scope: D9.)
- Multiple or labelled AOIs; needs a drawing interface for several shapes (D12).
- A frontend unit-test framework; full Section 508 review (M7).
- Eval workbench integration (D1); agent-app eval against `/invocations`; per-user attribution.
- Guarding against a user typing coordinates into the chat themselves.

**Verbatim constraints from the user:**

- "map as a panel to the left of the chat UI"
- "we do need the AOI result in the Chat view/map"
- "I dont think we need to over engineer, option 1 should cover it"
- "for now we will build it all into frontend/ so we can kick the tires on a full map + agent integration interface to the MCP server intended for users"
- "we can prioritize full M3 for implementation soon if this goes well"
- "I think we will certainly have to regenerate the lockfile as we add features"
- "when I merge I want to have a working example we have kicked the tires on--before committing to accepting this vendored frontend and server"
- "set both to proposed"
- "we will just redirect the existing app rather than create another one"
- "we should check after each wave"
- "it seems to be untenable to completely hide the geometry from the traces or provide no way for the chat to look up aoi info as user requests may require that info" (2026-10-31)
- "fine for proof of concept but this needs to be more directly integrated into the session context" (2026-10-31)
- "per session/conversation is fine for now. multiple AOIs would be good but we would need an interface that could draw multiple and tag/label them which is future work" (2026-10-31)
- "I think geometry should generally be allowed ... ultimately there will have to be limits on the environments this is deployed in and guidelines for the user to not submit PII" (2026-10-31)
- "we will fold this all into plan 42" (2026-10-31)

## Reconnaissance Log

- **Branch:** `feature/agent-app-map1` at 0823c7f (merge of main 6e730b8), 0 behind / 20 ahead of main, pushed. PR not merged.
- **App:** `agent-fpac-soil-openai-sdk` now has `default_git_source.branch = feature/agent-app-map1`, `auto_deploy: true` (verified 2026-10-30 `apps get`). Experiment 517983779529169; resources `mcp-fpac-soil` CAN_USE, `models.ai.gpt-5-6-luna`.
- **Frontend:** `apps/agent-fpac-soil-openai-sdk/frontend/` = upstream `e2e-chatbot-app-next` at 0e57297, 604 files, blob- and mode-identical. React + react-router-dom SPA built with Vite (`client/`), Express server (`server/`), workspaces `packages/*`. `client/src/App.tsx` (39 lines) routes `/` and `chat/:id` inside `ChatLayout`. `client/src/layouts/ChatLayout.tsx` (55 lines): `SidebarProvider` > `AppSidebar` + `SidebarInset` > `Outlet`. `client/src/components/multimodal-input.tsx` (381 lines) owns `input`/`setInput` and `submitForm` -> `sendMessage`. No CSP headers in `server/src` or `client/index.html`.
- **Backend:** `agent_server/start_server.py` builds `AgentServer("ResponsesAgent", enable_chat_proxy=True)` and registers `GET /api/geo/health`. MLflow 3.17.2 chat proxy serves registered routes first (`route.path_regex.match`), so new `/api/geo/*` routes are reached before the Node app. `agent_server/agent.py`: `init_fpac_mcp_server(WorkspaceClient())` returns `databricks_openai.agents.McpServer`; `connect_healthy_mcp_servers` shows the connect + `list_tools` pattern; `mlflow.openai.autolog()` at import; `set_trace_processors([])`. Traces open only in `AgentServer._handle_invoke_request`/stream via `mlflow.start_span` + `span.set_inputs(request)`.
- **MCP tools used:** `analyze_farmland_by_polygon(geojson, ...)` -> `PolygonFarmlandAnalysisResponse` (`geometry_hash`, `total_aoi_acres`, `coverage_status`, `urban_screening`, `farmland_summary` with `*_acres`/`*_pct` per class, `map_units`, `tabular_csv`, `manifest`, `source`, `limitations`, `regulatory_notice`). `get_soil_polygons_by_geometry(geojson, clip=True)` -> GeoJSON FeatureCollection with `mukey`, `musym`, `muname`, `farmlndcl`, `areasymbol`, `area_ac`, plus `error`/`limitations`/`regulatory_notice` on failure. No server-side vertex or acreage limit constants found.
- **Tests and checks:** app `make app-check` (ruff on `APP_LINT_PATHS` = `agent.py config.py history.py tests`, then 61 tests); `make app-frontend-check` (`npm ci`, biome lint with two skips, `npm run build`); root `make check` 597 passed / 3 skipped. Route-test reference: `tests/test_custom_routes.py` (module fixture patches `setup_mlflow_git_based_version_tracking`). Handler-test reference: `tests/test_aoi_handoff.py`, `tests/test_agent_mcp_wiring.py`.
- **Networking evidence:** `planning/evidence/40.2.3-networking.md` saw USGS National Map `USGSTopo` metadata with `Access-Control-Allow-Origin: *`; the exact MapLibre tile template and browser behavior from the app origin are unverified.
- **ADRs:** 0003 (preliminary screening; render the server `regulatory_notice`), 0010 (no raw coordinates/WKT/GeoJSON/bbox/parcel properties in prompts, history, traces, storage, commits, planning), 0012 (separate MCP client; no wrapper tools), 0013 (PyPI index), 0015 (vendored frontend; to be clarified). Next free ADR number: 0016.
- **Environment (Databricks agent):** no sub-agents; shell writes under `/Workspace` blocked; `/tmp` lost on compute restart; Node 22 at `/usr/local/bin/node` may lack npm, so use the `nodejs-wheel-binaries>=22,<23` wrappers in `/tmp/nbin`; npm registry reachable; GitHub API unauthenticated (404); the app rejects PAT auth, so browser and log checks are the user's.

## Decision Log

1. **D1, 2026-10-30, where the map lives:** Build the map panel directly into `frontend/`. ADR 0015's no-local-edits rule is replaced by an explicit local-changes list. Possible later overlap with the eval workbench is out of scope.
2. **D2, 2026-10-30, AOI result to chat:** Option 1. `POST /api/geo/screen` calls the MCP tools directly and returns `display` (browser-only, may contain geometry) and `chat_summary` (server-built from an allowlist, geometry-free). The panel puts the summary into the chat input; the user reviews and sends it as a normal turn. No hidden injection, no agent-side lookup tool, no `custom_inputs`.
3. **D3, 2026-10-30, map results:** Use existing MCP tools only (`analyze_farmland_by_polygon` for the authoritative summary and notice; `get_soil_polygons_by_geometry` with `clip=True` for the layer). Label the view preliminary. No MCP server changes; M3 deferred and likely next.
4. **D4, 2026-10-30, MVP scope:** MapLibre GL JS + Terra Draw; polygon and rectangle with edit/delete/undo; GeoJSON paste/upload; one session-only AOI; one public USGS basemap; results table and keyboard path; app-side size limits. Regenerating `package-lock.json` when dependencies change is expected; ADR 0015's "never regenerate" was an oversight.
5. **D5, 2026-10-30, branch:** Plan 42 runs on `feature/agent-app-map1`. ADR 0015 is clarified on this branch. The PR merges only after a working, tried-out map + agent example.
6. **D6, 2026-10-30, ADR status:** ADR 0015 -> `Proposed`; ADR 0016 drafted `Proposed`. Task 42.6.2 (was 42.5.2 before D9) sets both to `Accepted` after the deployed trial passes.
7. **D7, 2026-10-30, trial target:** No dev app. The existing `agent-fpac-soil-openai-sdk` (main version was only a vanilla SDK test; teammates not using it) points at `feature/agent-app-map1` for the trial, same experiment. Goal: merge the PoC today.
8. **D8, 2026-10-30, execution model:** One Databricks agent executes all tasks serially (no sub-workers). Each wave ends with a check gate. Work and commit in a `/tmp` clone, then fast-forward the personal workspace clone from it with git after every task. The user owns Apps deploys, browser checks, app logs, PR CI status, and push approvals. `PROMPT_TEMPLATE_42.md` is still written so a tool with workers could run the plan. Amended by the user 2026-10-30: edit and commit directly in the workspace clone; `/tmp` only for throwaway gate clones and caches.
9. **D9, 2026-10-31, AOI as session context (supersedes D2's handoff):** After the deployed check, the agent could not run LESA from the pasted summary: it had only `aoi_ref` and passed that string as the LESA `geometry` argument. The active AOI now goes with every chat turn as `custom_inputs.active_aoi` (`aoi_ref`, geometry, latest screening summary). The agent server adds a short note to the model's instructions (reference and summary, no geometry) and swaps the real geometry in when a tool's `geojson`/`geometry` argument equals the active `aoi_ref`. The MCP tools already accept a string there. The "Add result to chat" button and input prefill are removed; an AOI chip in the chat input shows what is attached and can detach it. `/api/geo/screen` stays for the map display.
10. **D10, 2026-10-31, where the AOI lives:** Browser `sessionStorage`, keyed by chat id (the conversation id), one active AOI per conversation. The server stays stateless. A new chat starts without an AOI; reloading the tab keeps it; closing the tab drops it.
11. **D11, 2026-10-31, geometry handling:** Geometry is operational project data (as ADR 0010's context already says; the Plan 42 recon note over-read ADR 0010) and may appear in traces, tool spans, request bodies and app logs. No redaction. The controls are where the app is deployed and user guidance not to submit PII or producer-supplied data covered by Section 1619 outside authorised environments. ADR 0016 is amended (still `Proposed`), not replaced.
12. **D12, 2026-10-31, AOI count:** One active AOI per conversation. Several labelled AOIs need a multi-shape drawing and labelling interface; future work.

## Wave & Dependency Table

| Wave | Executor | Task | Title | Files in scope | Depends on |
|---|---|---|---|---|---|
| 1 | Databricks | 42.1.1 | Clarify ADR 0015 and app frontend docs | `docs/decisions/0015-vendored-agent-app-frontend.md`, app `AGENTS.md`, app `README.md` | none |
| 1 | Databricks | 42.1.2 | Draft ADR 0016 AOI handoff and ADR index | `docs/decisions/0016-out-of-band-aoi-screening-handoff.md` (new), `docs/decisions/README.md` | none |
| 2 | Databricks | 42.2.1 | `/api/geo/screen` backend and privacy tests | `agent_server/geo.py` (new), `agent_server/start_server.py`, `tests/test_geo_screen.py` (new), root `Makefile` | 42.1.2 |
| 2 | Databricks | 42.2.2 | Map panel skeleton: deps, layout, draw/paste, Run screening, raw layers | `frontend/client/package.json`, `frontend/package-lock.json`, `frontend/client/src/layouts/ChatLayout.tsx`, `frontend/client/src/components/map/**` (new) | 42.1.1 |
| 2 | User + Databricks | 42.2.3 | Push gate and first deployed screening | `planning/STATE_42.md` only | 42.2.1, 42.2.2 |
| 3 | Databricks | 42.3.1 | Legend, results table, notice, preliminary label, error states | `frontend/client/src/components/map/**` | 42.2.3 |
| 3 | Databricks | 42.3.2 | Summary to chat input | `frontend/client/src/components/multimodal-input.tsx`, `frontend/client/src/components/map/**` | 42.3.1 |
| 4 | Databricks | 42.4.1 | Update local-changes list and frontend docs | `docs/decisions/0015-vendored-agent-app-frontend.md`, app `AGENTS.md` | 42.3.2 |
| 5 | Databricks | 42.5.1 | Amend ADR 0016: AOI as session context | `docs/decisions/0016-out-of-band-aoi-screening-handoff.md`, `docs/decisions/README.md`, root and app `AGENTS.md` | 42.4.1 |
| 5 | Databricks | 42.5.2 | Agent: active AOI from `custom_inputs`, instruction note, argument substitution | `agent_server/agent.py`, `agent_server/aoi_context.py` (new), `agent_server/geo.py`, `tests/test_aoi_context.py` (new), root `Makefile` | 42.5.1 |
| 5 | Databricks | 42.5.3 | Frontend: per-conversation AOI in sessionStorage, sent with each turn, AOI chip; remove the button | `frontend/client/src/components/chat.tsx`, `frontend/packages/core/src/schemas/chat.ts`, `frontend/server/src/routes/chat.ts`, `frontend/packages/ai-sdk-providers/src/providers-server.ts`, `frontend/client/src/components/multimodal-input.tsx`, `frontend/client/src/components/map/**`, ADR 0015 | 42.5.2 |
| 6 | User + Databricks | 42.6.1 | Deployed trial: chat uses the map AOI | `planning/STATE_42.md`, `planning/evidence/42.6.1-trial.md` (new) | 42.5.3 |
| 6 | Databricks | 42.6.2 | Close-out: ADRs Accepted, master plan Track A | ADRs 0015 and 0016, `docs/decisions/README.md`, `planning/MASTER_PLAN.md`, `planning/STATE_42.md` | 42.6.1 |

Paths under `frontend/`, `agent_server/` and `tests/` are relative to `apps/agent-fpac-soil-openai-sdk/`. 42.3.1 and 42.3.2 both touch `components/map/**` and therefore run in sequence. Execution is serial in this environment anyway (D8); file scopes are listed so a worker-capable tool could parallelize waves 1 and 2.

**Check gate after every wave** (serial, from a fresh `/tmp` clone of the branch head): `make app-check`; `make app-frontend-check` (from wave 2 on); root `make check`. Record results in `STATE_42.md` before starting the next wave. Live or deployed checks happen only in 42.2.3 and 42.5.1.

## Hazards

- **Auto-deploy on push:** the app tracks this branch with auto-deploy on, so every approved push redeploys the app. Push only at gates (42.2.3, 42.6.1) unless the user asks otherwise.
- **Privacy (ADR 0010):** never write real coordinates, WKT/GeoJSON, bounding boxes or parcel properties into commits, tests, planning or evidence files. Tests use a synthetic geometry built around a marker string (for example the property value `R6-MARKER`) and tiny synthetic coordinates like `[[0,0],[1,0],[1,1],[0,0]]`. The `/api/geo/screen` handler must not log request bodies or MCP payloads.
- **Tracing:** (D11 relaxes this for chat turns: geometry in chat traces is allowed; the rule below still holds for `/api/geo/screen`, to avoid session-less traces.) `mlflow.openai.autolog()` is global. `/api/geo/screen` must not run `Runner` or call the model, and must not use `@mlflow.trace`. 42.2.1 proves with a local SQLite tracking store that a screening call creates zero traces. If the MCP client turns out to emit spans outside a trace, stop and report.
- **Workers:** the agent server may run more than one worker process. Keep `/api/geo/screen` stateless; no server-side AOI cache.
- **MCP client lifecycle:** open the `McpServer` per request with `async with` (or an `AsyncExitStack`) and close it; reuse `init_fpac_mcp_server`. Do not modify `agent.py` beyond importing from it.
- **Tool result shape:** `McpServer.call_tool` returns an MCP `CallToolResult`. Parse structured content first, then JSON text content. Treat `error` keys and `isError` as failures. Never forward raw MCP exceptions (they may echo arguments) to the browser.
- **Frontend lint:** `make app-frontend-check` lints all of `frontend/`. New files must pass biome with the two skipped rules only. Never run upstream `npm run lint`/`lint:fix` (they `--write`). No typecheck gate exists (upstream fails `tsc`).
- **Lockfile:** add dependencies with `npm install <pkg> --workspace @databricks/chatbot-client --save-exact` in `frontend/` from the `/tmp` clone; commit `client/package.json` and the regenerated root `package-lock.json` together; then `npm ci` must pass from clean.
- **MapLibre CSS and workers:** import `maplibre-gl/dist/maplibre-gl.css` in the map component. Vite must bundle MapLibre; verify `npm run build` output size is reasonable and note it.
- **Layout:** the panel sits between `AppSidebar` and `SidebarInset`. On narrow screens (below the `md` breakpoint) hide the panel behind a toggle so the chat stays usable.
- **Large files:** `multimodal-input.tsx` (381 lines) and `chat.tsx` (342 lines): enter via grep anchors; do not restructure.
- **Transfer:** after each task, commit in `/tmp`, then in the workspace clone run `git fetch /tmp/<clone> feature/agent-app-map1` and `git merge --ff-only FETCH_HEAD`; confirm `git status -sb` and `git log -1` match. Never push from `/tmp`.
- **Compute restarts:** `/tmp` disappears. Re-clone from the workspace clone (`git clone /Workspace/.../fpac-soil-mcp /tmp/p42`), recreate `/tmp/nbin` and venvs, and resume from `STATE_42.md`.
- **Repository hygiene still applies (D11):** geometry may appear in traces and logs, but commits, tests, planning and evidence files keep synthetic coordinates only.
- **Request size and logs:** the active AOI (up to 256 KB) goes with every chat turn. Vendored `databricksFetch` logs the full `/invocations` body to the app console, so app logs will contain geometry (accepted, D11); check that the body limits on `/api/chat` and the agent server accept the size.
- **Model copying coordinates:** the instruction note never contains geometry; substitution keeps the model from copying shapes. A tool result that returns geometry can still reach the model; that is accepted.
- **Chat id:** with `chatHistory` off the chat id is generated in the browser and sent as `context.conversation_id`; the sessionStorage key must use the same id the server sends.

## Task Specifications

### 42.1.1 -- Clarify ADR 0015 and app frontend docs

**Executor:** Databricks.

**Files in scope**

- Must edit: `docs/decisions/0015-vendored-agent-app-frontend.md`, `apps/agent-fpac-soil-openai-sdk/AGENTS.md`, `apps/agent-fpac-soil-openai-sdk/README.md`.
- Can create: `planning/tasks/42.1.1.todo.md`.
- Do not touch: `frontend/**`, `docs/decisions/README.md` (42.1.2 owns it), code, tests.

**Depends on:** none.

**Specification:**

1. ADR 0015 front matter: `status: "Proposed"`; add `EXECUTION_PLAN_42` to `source_context`.
2. Retitle the decision in substance (title text may stay): `frontend/` is the upstream folder at base commit 0e57297 that this repo now owns. Replace "No local edits" with a **Local changes** rule: allowed; every modified upstream file and every added path is listed in a `### Local changes` section of this ADR, kept current by the task that makes the change.
3. Add `### Local changes` with an initial empty-state line ("None yet; Plan 42 adds the map panel."). 42.4.1 fills it.
4. Replace "root `package-lock.json` byte-for-byte" / "never regenerate it" with: the lockfile is regenerated by npm when dependencies change and committed with the matching `package.json`; CI and `make app-frontend-check` run `npm ci` against it.
5. Rewrite the update procedure: re-copy upstream at the new commit with the exclusions; re-apply the listed local changes; reconcile `package.json` and regenerate the lockfile; compare `git ls-tree` hashes only for upstream files not in the local-changes list; run `make app-frontend-check`; update the base commit in this ADR, the app `README.md` and `AGENTS.md`.
6. Keep Considered Options, the checks, Node 22 and the exclusions. Add a Consequences bullet: owning local changes turns upstream updates into a re-apply step.
7. App `AGENTS.md` Frontend workflow and `frontend/` Find-Things line: replace "no local edits, no map behavior" and "Do not edit files under `frontend/`" / "Do not add map or AOI behavior" with the local-changes rule, pointing to ADR 0015 and noting map code lives under `client/src/components/map/`.
8. App `README.md`: align any "no local edits" or byte-for-byte lockfile wording with the above.

**Grep anchors:** `No local edits`, `byte-for-byte`, `never regenerate`, `Update procedure`, `status:`, `Do not edit files under`, `no map behavior`, `Do not add map or AOI`.

**Acceptance:**

- `grep -nE 'No local edits|never regenerate|byte-for-byte|Do not add map' docs/decisions/0015-vendored-agent-app-frontend.md apps/agent-fpac-soil-openai-sdk/AGENTS.md apps/agent-fpac-soil-openai-sdk/README.md` returns nothing.
- `grep -n 'status: "Proposed"' docs/decisions/0015-vendored-agent-app-frontend.md` matches; `### Local changes` exists.
- Commit: `docs(agent-app): allow owned local changes to the vendored frontend`.

### 42.1.2 -- Draft ADR 0016 AOI handoff and ADR index

**Executor:** Databricks.

**Files in scope**

- Can create: `docs/decisions/0016-out-of-band-aoi-screening-handoff.md`, `planning/tasks/42.1.2.todo.md`.
- Must edit: `docs/decisions/README.md`.
- Do not touch: ADR 0015 (42.1.1), code, frontend, Plan 40 files.

**Depends on:** none.

**Specification:**

1. Create ADR 0016 using the front-matter and section layout of ADR 0015 (`id: "0016"`, `status: "Proposed"`, date 2026-10-30, `source_context: "EXECUTION_PLAN_40, EXECUTION_PLAN_42"`).
2. Context: Plan 40 R6 blocker (template has no `custom_inputs`/`custom_outputs`; handler sanitizing cannot prove pre-trace redaction); cite `planning/evidence/40.2.1-aoi.md` and `planning/decisions/40.2.1-aoi.md`.
3. Considered options: (1) out-of-band `/api/geo/screen` with a server-built summary the user sends; (2) template change to forward `custom_inputs` plus an MLflow span processor (fails open on processor errors; request-preview timing unverified; breaks the upstream base); (3) disabling tracing for AOI turns (global, concurrency-unsafe); (4) a separate map app.
4. Decision: option 1, with the D2 contract: request body (one Polygon/MultiPolygon GeoJSON geometry, app-side limits), MCP calls (`analyze_farmland_by_polygon`, `get_soil_polygons_by_geometry` clip), `display` vs `chat_summary`, the `chat_summary` allowlist (fields named in 42.2.1), opaque random `aoi_ref`, no logging of bodies, no traces, stateless, browser session-only AOI. Raw geometry never enters model context, chat history or traces; the user sends only the summary.
5. Consequences: chat and screening are decoupled (the model answers from the summary, not from re-running tools on geometry); results on the map are preliminary until M3; a user can still type coordinates into chat (out of scope, noted).
6. Validation: list the offline tests from 42.2.1 and the deployed check in 42.5.1 as the evidence required before `Accepted`.
7. `docs/decisions/README.md`: add the 0016 row (status `Proposed`, Context `EXECUTION_PLAN_40, 42`) and set the 0015 row status to `Proposed`; extend the Databricks Delivery era paragraph by one sentence about 0016.

**Grep anchors:** in README: `| [0015]`, `Databricks Delivery`; ADR 0015 front matter as layout reference.

**Acceptance:**

- ADR 0016 exists with `status: "Proposed"`; README rows for 0015 and 0016 both say `Proposed`.
- `grep -nE '[0-9]{1,3}\.[0-9]{4,}' docs/decisions/0016-out-of-band-aoi-screening-handoff.md` returns nothing (no coordinate-like values).
- Commit: `docs(decisions): propose out-of-band AOI screening handoff`.

### 42.2.1 -- `/api/geo/screen` backend and privacy tests

**Executor:** Databricks.

**Files in scope**

- Can create: `apps/agent-fpac-soil-openai-sdk/agent_server/geo.py`, `apps/agent-fpac-soil-openai-sdk/tests/test_geo_screen.py`, `planning/tasks/42.2.1.todo.md`.
- Must edit: `apps/agent-fpac-soil-openai-sdk/agent_server/start_server.py`, root `Makefile` (add `agent_server/geo.py` to `APP_LINT_PATHS`).
- Do not touch: `agent.py`, `history.py`, `utils.py`, `frontend/**`, MCP server `src/**`.

**Depends on:** 42.1.2 (the ADR states the contract implemented here).

**Specification:**

1. `geo.py` defines Pydantic models: `ScreenRequest` (`geometry`: a GeoJSON object whose `type` is `Polygon` or `MultiPolygon`; `name`: optional short label, max 80 chars, never echoed into `chat_summary`). Validate: total vertex count <= `GEO_MAX_VERTICES` (default 2000) and raw body <= 256 KB; reject other geometry types. Return 422 with a bounded message that never contains coordinates.
2. `async def screen_aoi(request: ScreenRequest) -> dict`: open `init_fpac_mcp_server(WorkspaceClient())` with `async with`; call `analyze_farmland_by_polygon` (`geojson=geometry`, `include_nccpi=True`) and `get_soil_polygons_by_geometry` (`geojson=geometry`, `clip=True`). Parse results (structured content, else JSON text). On MCP failure return 502 `{"error": "screening_unavailable"}`; on tool-level `error` return 200 with `display.error` set and a summary that says the screening failed.
3. Response: `{"aoi_ref": "aoi-<8 hex, random>", "display": {"analysis": <selected analysis fields>, "soil_polygons": <FeatureCollection>, "regulatory_notice": str}, "chat_summary": {...}, "chat_summary_text": str}`.
4. `build_chat_summary(analysis, aoi_ref)` uses an explicit allowlist: `aoi_ref`, `total_aoi_acres`, `coverage_status`, per-class `*_acres` and `*_pct` from `farmland_summary`, urban flag and urban acres if present in `urban_screening` (numbers/booleans only), up to 10 map units as `{musym, muname, farmlndcl, acres}` sorted by acres, `source` service name and timestamp, `regulatory_notice`. Never include `geometry_hash`, `tabular_csv`, `manifest`, `limitations` free text that could echo inputs, any key containing `geom`, `coordinates`, `bbox`, or `wkt`. Round acres to 0.1 and pct to 0.1.
5. `render_chat_summary_text(summary)`: a short plain-text block (heading "Map screening result (preliminary)", AOI ref, acres, class breakdown, top map units, notice). Max 2,000 chars.
6. `start_server.py`: register `@app.post("/api/geo/screen")` next to `geo_health`, delegating to `geo.screen_aoi`. No logging of the body.
7. `tests/test_geo_screen.py` (reuse the `start_server` fixture pattern from `test_custom_routes.py`; patch the MCP client with a fake async context manager):
   - route registered and served before the chat proxy;
   - happy path returns `aoi_ref`, `display`, `chat_summary`, `chat_summary_text`;
   - marker test: the fake MCP returns analysis and polygons whose geometry, `geometry_hash`, `tabular_csv`, `manifest` and properties contain `R6-MARKER`; assert the marker is absent from `json.dumps(chat_summary)` and `chat_summary_text`, and that no key named like `coordinates`, `bbox`, `wkt`, `geometry` appears in `chat_summary`;
   - limits: too many vertices, `Point`/`LineString`, oversize body -> 422 with no marker in the message;
   - MCP exception -> 502 with no marker in the body;
   - no-trace test: with `MLFLOW_TRACKING_URI=sqlite:///<tmp>` and a temp experiment, a screening call leaves `MlflowClient().search_traces(...)` empty;
   - `caplog` at DEBUG contains no marker after a screening call.

**Grep anchors:** `def geo_health`, `init_fpac_mcp_server`, `connect_healthy_mcp_servers`, `APP_LINT_PATHS`, `def start_server` (test fixture).

**Reference implementations:** `connect_healthy_mcp_servers` (MCP connect/list), `tests/test_custom_routes.py` (route fixture), `tests/test_agent_mcp_wiring.py` (fake MCP servers).

**Acceptance:**

- From `/tmp`: `UV_PROJECT_ENVIRONMENT=/tmp/appvenv PYTHONDONTWRITEBYTECODE=1 uv run --frozen --python 3.11 pytest -p no:cacheprovider tests/test_geo_screen.py tests/test_custom_routes.py -q` green.
- `make app-check` green (lint now includes `geo.py`).
- Commit: `feat(agent-app): add out-of-band AOI screening route`.

### 42.2.2 -- Map panel skeleton

**Executor:** Databricks.

**Files in scope**

- Must edit: `frontend/client/package.json`, `frontend/package-lock.json`, `frontend/client/src/layouts/ChatLayout.tsx`.
- Can create: `frontend/client/src/components/map/**`, `planning/tasks/42.2.2.todo.md`.
- Do not touch: other `frontend/` files, `frontend/server/**`, `frontend/packages/**`, Python code.

**Depends on:** 42.1.1.

**Specification:**

1. Add exact-pinned `maplibre-gl`, `terra-draw`, `terra-draw-maplibre-gl-adapter` to the client workspace (see the Lockfile hazard). Record versions and licenses in the task report.
2. `components/map/MapPanel.tsx`: MapLibre map with one raster basemap from USGS The National Map (confirm the tile URL template from service metadata; attribution "USGS The National Map"). Terra Draw with polygon and rectangle modes plus select mode for vertex editing and delete; a small toolbar (Polygon, Rectangle, Edit, Undo, Clear). One AOI at a time: drawing a new one replaces the old; Undo restores the previous AOI (one level, React state only).
3. `components/map/GeoJsonInput.tsx`: textarea + file input (`.geojson`, `.json`) accepting a Geometry, Feature or single-feature FeatureCollection of type Polygon/MultiPolygon; show a validation message otherwise. Parsed geometry replaces the drawn AOI and is shown on the map.
4. `components/map/useScreening.ts`: `POST /api/geo/screen` with `{geometry}`; state `idle | running | done | error`; keep the response in React state only (no `localStorage`, no `sessionStorage`).
5. Render the AOI outline and `display.soil_polygons` as a fill layer coloured by `farmlndcl` (simple match expression; a full legend comes in 42.3.1). Fit bounds to the AOI after screening.
6. `components/map/MapSummaryContext.tsx`: a React context with `pendingSummary: string | null`, `offerSummary(text)`, `consumeSummary()` and a provider component. Not used by the chat until 42.3.2.
7. `ChatLayout.tsx`: wrap the existing `SidebarProvider` children in `<MapSummaryProvider>` and insert `<MapPanel />` between `AppSidebar` and `SidebarInset` in a fixed-width column (about 40% on `md+`), with a toggle button to collapse it; hidden by default below `md`. Minimal diff; no other layout changes. This is the only `ChatLayout.tsx` change in Plan 42.
8. Keyboard: Run screening is a real `<button>`; the GeoJSON textarea is the keyboard path for entering an AOI.

**Grep anchors:** `SidebarInset`, `AppSidebar`, `"dependencies"` in `client/package.json`.

**Acceptance:**

- `make app-frontend-check` green from a fresh `/tmp` clone (`npm ci` from the regenerated lockfile, biome lint, build). Note bundle size from the build output.
- `git diff --stat` touches only the files in scope.
- Commit: `feat(agent-app): add map panel with AOI drawing and screening`.

### 42.2.3 -- Push gate and first deployed screening

**Executor:** user + Databricks.

**Files in scope:** `planning/STATE_42.md` only.

**Depends on:** 42.2.1, 42.2.2 and the wave 2 check gate.

**Specification:**

1. Agent: report the wave-2 gate results and the commits to push; ask for push approval.
2. User: push (or approve the agent pushing from the workspace clone). Auto-deploy should create a deployment; if none appears within about 5 minutes, the user clicks Deploy.
3. Agent: `apps list-deployments` shows a SUCCEEDED deployment whose `resolved_commit` equals the pushed head.
4. User, in the browser: `/` loads with the map panel; basemap tiles render; draw a small polygon; Run screening returns soil polygons on the map without an error; app logs show no traceback for `/api/geo/screen`.
5. Agent: MLflow traces in experiment 517983779529169 created during the screening window: expect none (no chat turn sent yet).
6. Record outcomes in STATE_42; any failure becomes a fix task before wave 3.

**Acceptance:** all five checks recorded as pass, or a fix task added.

### 42.3.1 -- Legend, results table, notice, preliminary label, error states

**Executor:** Databricks.

**Files in scope**

- Can create/edit: `frontend/client/src/components/map/**`, `planning/tasks/42.3.1.todo.md`.
- Do not touch: `ChatLayout.tsx` (done in 42.2.2), `multimodal-input.tsx`, Python.

**Depends on:** 42.2.3.

**Specification:**

1. `farmlandClasses.ts`: one mapping from `farmlndcl` values to colour, pattern hint and short label, covering prime, prime-if (conditional), statewide, local, unique, not prime and unmapped/other. Use it for both the map layer and the legend.
2. `Legend.tsx`: colour swatch + text for every class present in the result.
3. `ResultsTable.tsx`: class breakdown (acres, %) and map units (musym, muname, farmland class, acres), sortable by acres; this is the non-map way to read the result.
4. Show `display.regulatory_notice` verbatim above the table; if missing, show an explicit "notice missing - treat as invalid" error (ADR 0003).
5. A persistent label: "Preliminary screening view. Not an official NRCS determination."
6. Error states: invalid AOI, 422 message, 502 "screening unavailable", tool-level `display.error`, and basemap tile failure, each shown in the panel, never a silent blank map.

**Acceptance:** `make app-frontend-check` green. Commit: `feat(agent-app): show screening legend, table and notice on the map panel`.

### 42.3.2 -- Summary to chat input

**Executor:** Databricks.

**Files in scope**

- Must edit: `frontend/client/src/components/multimodal-input.tsx`.
- Can edit: `frontend/client/src/components/map/**` (the `MapSummaryContext` provider already mounted by 42.2.2).
- Do not touch: `ChatLayout.tsx`, `chat.tsx`, `ChatTransport`, `server/**`, `packages/**`.

**Depends on:** 42.3.1.

**Specification:**

1. Use the `MapSummaryContext` from 42.2.2.
2. After a successful screening, the panel shows "Add result to chat", which calls `offerSummary(response.chat_summary_text)`.
3. In `multimodal-input.tsx`, a minimal `useEffect` reads `pendingSummary`; when set, it calls `setInput` with the summary followed by a blank line and any existing input, focuses the textarea, and calls `consumeSummary()`. No other behaviour changes. If the provider is absent (context default), nothing happens.
4. The browser never puts `display` geometry into the input: only `chat_summary_text` from the server.

**Grep anchors:** `setInput`, `adjustHeight`, `localStorageInput`, `textareaRef`.

**Acceptance:** `make app-frontend-check` green; `git diff` of `multimodal-input.tsx` is under about 25 lines. Commit: `feat(agent-app): add map screening summary to the chat input`.

### 42.4.1 -- Update local-changes list and frontend docs

**Executor:** Databricks.

**Files in scope:** ADR 0015, app `AGENTS.md`, `planning/tasks/42.4.1.todo.md`.

**Depends on:** 42.3.2 and the wave 3 gate.

**Specification:**

1. Fill ADR 0015 `### Local changes` from a comparison of `git ls-tree -r HEAD apps/agent-fpac-soil-openai-sdk/frontend` with upstream `e2e-chatbot-app-next` at 0e57297 (blob-less fetch of `databricks/app-templates`, as in the 2026-10-30 audit): modified upstream files (`client/package.json`, `package-lock.json`, `ChatLayout.tsx`, `multimodal-input.tsx`, any others) with one line each on why; added paths (`client/src/components/map/**`).
2. Verify: every other `frontend/` file still matches upstream 0e57297 by blob and mode (same `git ls-tree` comparison as the Plan 41 audit); record the counts.
3. App `AGENTS.md`: map code location, `/api/geo/screen` in Find Things, and the `geo.py` privacy rule (no logging of bodies, allowlist summary).

**Acceptance:** the listed files equal the diff; parity count recorded in the task report. Commit: `docs(agent-app): record map panel local frontend changes`.

### 42.5.1 -- Amend ADR 0016: AOI as session context

**Executor:** Databricks.

**Files in scope:** ADR 0016 (same file name; new title "Map AOI as chat session context"), `docs/decisions/README.md` (row title), app `AGENTS.md` ("Change AOI Screening" workflow), root `AGENTS.md` (coordinate-privacy operational rule, if it conflicts with D11), `planning/tasks/42.5.1.todo.md`.

**Depends on:** 42.4.1 and the wave 4 gate.

**Specification:**

1. Status stays `Proposed`; add `2026-10-31` amendment note and keep the history: the out-of-band handoff (option 1) was built and tried; the deployed LESA turn showed the model needs the geometry (D9).
2. Decision: D9-D12. Request field `custom_inputs.active_aoi = {aoi_ref, geometry, summary}`; same parse limits as `/api/geo/screen` (Polygon/MultiPolygon, 256 KB, `GEO_MAX_VERTICES`); invalid or absent means no AOI note and no substitution, never an error to the user. Instruction note carries `aoi_ref`, acres and the latest screening summary only. Substitution applies to the `geojson` and `geometry` arguments of MCP tools when the value equals the active `aoi_ref`.
3. Geometry handling per D11: allowed in traces, request bodies and logs; deployment-environment limits and user guidance on PII and Section 1619 producer data. The `/api/geo/screen` route keeps its untraced MCP calls so map-only screenings do not create session-less traces (noise, not privacy).
4. Options considered: keep the button handoff (rejected after the trial); server-side AOI store (rejected: state, D10); full geometry in the prompt (rejected: token cost and coordinate copying by the model); session context with server-side substitution (chosen).
5. Update the app `AGENTS.md` workflow to match; reword the root `AGENTS.md` coordinate rule only if it contradicts D11.

**Acceptance:** `status: "Proposed"` still matches; no text says geometry must be kept out of traces; README row title matches. Commit: `docs(decisions): amend ADR 0016 to make the map AOI chat session context`.

### 42.5.2 -- Agent: active AOI from `custom_inputs`

**Executor:** Databricks.

**Files in scope:** `agent_server/aoi_context.py` (new), `agent_server/agent.py`, `agent_server/geo.py` (reuse the parser only), `tests/test_aoi_context.py` (new), root `Makefile` (`APP_LINT_PATHS`), `planning/tasks/42.5.2.todo.md`.

**Depends on:** 42.5.1.

**Specification:**

1. `aoi_context.py`: `read_active_aoi(request) -> ActiveAoi | None` from `request.custom_inputs["active_aoi"]`, validated with the `geo.py` parser and limits; `aoi_ref` must match `aoi-[0-9a-f]{8}`; summary is the allowlisted `chat_summary` shape, rendered with `render_chat_summary_text`.
2. `instruction_note(aoi)`: a short paragraph appended to the agent instructions for that request: the AOI reference, acres, the latest summary text, and "to run a tool on this AOI, pass `<aoi_ref>` as the `geojson` or `geometry` argument; the app substitutes the shape". No coordinates in the note.
3. Substitution: wrap the per-request `McpServer` so `call_tool` replaces a `geojson`/`geometry` argument equal to the active `aoi_ref` with the geometry before the call, and leaves every other argument unchanged. Keep the normal (traced) `call_tool` path for chat turns.
4. `agent.py`: both handlers read the AOI, build the agent with the note, and pass the wrapper. No AOI means today's behaviour exactly.
5. Tests: valid/absent/invalid/oversize AOI; bad `aoi_ref`; note content and no coordinates in it; substitution on `geojson` and `geometry`; no substitution for other values or other argument names; handlers without `custom_inputs` unchanged; a LESA-shaped call with `geometry="aoi-..."` reaches the fake MCP session with the real geometry.

**Acceptance:** `make app-check` green; new tests fail with the substitution removed (negative control). Commit: `feat(agent-app): give the agent the map AOI as session context`.

### 42.5.3 -- Frontend: AOI in sessionStorage, sent with each turn

**Executor:** Databricks.

**Files in scope:** `frontend/client/src/components/map/**`, `frontend/client/src/components/chat.tsx`, `frontend/client/src/components/multimodal-input.tsx`, `frontend/packages/core/src/schemas/chat.ts`, `frontend/server/src/routes/chat.ts`, `frontend/packages/ai-sdk-providers/src/providers-server.ts`, ADR 0015 `### Local changes`, `planning/tasks/42.5.3.todo.md`.

**Depends on:** 42.5.2.

**Specification:**

1. Map state per conversation: `MapSummaryContext` becomes an active-AOI context keyed by chat id; geometry, `aoi_ref` and the latest `chat_summary` persist in `sessionStorage` under one key per chat id; new chat starts empty; switching chats switches the AOI.
2. Request path: `chat.tsx` `prepareSendMessagesRequest` adds `activeAoi` when one is attached; `postRequestBodySchema` accepts it (optional, bounded); `routes/chat.ts` hands it to the provider; `databricksFetch` adds it to the `/invocations` body as `custom_inputs.active_aoi`. Headers are too small for 256 KB, so pick the per-request mechanism in recon (for example a request-scoped value read by `databricksFetch`) and record it.
3. Chat input: an AOI chip ("Map AOI <ref>, <acres> ac") above the textarea when an AOI is attached, with a detach control; remove the "Add result to chat" button and the summary prefill effect from 42.3.2, restoring `multimodal-input.tsx` as close to upstream as the chip allows.
4. Drawing a new AOI or rerunning the screening updates the attached AOI and summary; deleting the AOI detaches it.
5. ADR 0015 `### Local changes`: add the newly modified upstream files with one line each; re-run the 42.4.1 parity check.

**Acceptance:** `make app-frontend-check` green; `tsc` shows no new errors; parity check matches the ADR list. Commit: `feat(agent-app): send the map AOI with each chat turn`.

### 42.6.1 -- Deployed trial: chat uses the map AOI

**Executor:** user + Databricks.

**Files in scope:** `planning/STATE_42.md`, `planning/evidence/42.6.1-trial.md` (new; no coordinates).

**Depends on:** 42.5.3 and the wave 5 gate; push approved and deployment SUCCEEDED on the head commit.

**Specification (user in browser, agent verifying):**

1. Draw a polygon; Run screening; map shows soil polygons coloured by class, legend, table, notice, preliminary label; the chip shows the AOI.
2. Without pasting anything, ask about the AOI (for example, "What share of this AOI is prime farmland?") and then ask for a preliminary LESA; both answers use the AOI and keep the preliminary-screening language.
3. Paste a GeoJSON polygon instead of drawing; the chip updates; a question uses the new AOI.
4. Reload the tab: the AOI is still attached to that chat. New chat: no AOI. Detach: the next turn has no AOI.
5. POINT-01 still works in a fresh chat.
6. Agent: for the trial traces, confirm the session equals `context.conversation_id`, `custom_inputs.active_aoi` is present on AOI turns, and the LESA tool call received a geometry object rather than the `aoi_ref` string (span data where it loads; otherwise tool result shape). Geometry in traces is expected (D11).
7. Record pass/fail per step in the evidence file and STATE_42, with deployment ID and commit; the evidence file itself contains no coordinates.

**Acceptance:** all steps pass, or failures become fix tasks and the trial is repeated.

### 42.6.2 -- Close-out

**Executor:** Databricks.

**Files in scope:** ADR 0015, ADR 0016, `docs/decisions/README.md`, `planning/MASTER_PLAN.md`, `planning/STATE_42.md`.

**Depends on:** 42.6.1 passed.

**Specification:**

1. ADR 0015 and 0016: `status: "Accepted"`, add an acceptance note with the date and a pointer to `planning/evidence/42.6.1-trial.md`. README rows updated.
2. `MASTER_PLAN.md` Track A: Status (vendored, owned frontend with a map panel MVP; the map AOI is chat session context); Delivered (Plans 35, 40, 41, 42; ADRs 0012, 0015, 0016); Backlog: M0 delivered; M1 resolved by ADR 0016 (single AOI per conversation; multiple labelled AOIs backlog); M2 MVP delivered (polygon/rectangle, GeoJSON); M3 next; remaining M2 items (lines, WKT, AOI list, custom basemaps) listed as backlog. Follow Plan 37 D4: link plans and ADRs, no run IDs or counts.
3. STATE_42: final summary; note the user merges the PR and points the app back at `main` afterwards.

**Acceptance:** `grep -n 'status: "Accepted"'` matches in both ADRs; README rows match. Commit: `docs(planning): record map panel trial and accept frontend and AOI ADRs`.
