---
id: "0016"
title: "Map AOI as Chat Session Context"
status: "Accepted"
date: 2026-10-30
authors:
  - "Andrew G. Brown"
supersedes: null
superseded_by: null
source_context: "EXECUTION_PLAN_40, EXECUTION_PLAN_42"
---

# 16. Map AOI as Chat Session Context

> **Amended 2026-10-31 (Plan 42 D9-D12).** The first version of this ADR
> chose an out-of-band screening route whose geometry-free summary the user
> pasted into the chat with a button. Plan 42 built and deployed it. In the
> deployed check the user asked for a preliminary LESA on the screened AOI;
> the model had only the AOI reference, passed that string as the LESA
> `geometry` argument, and asked the user for the GeoJSON. Keeping geometry out
> of the chat entirely makes AOI follow-up questions impossible, and the button
> handoff is awkward. The decision below replaces the handoff; the screening
> route stays for the map display.

> **Accepted 2026-10-31 (Plan 42).** In the deployed trial the agent ran the
> preliminary FPPA workflow and LESA on drawn and pasted AOIs without any
> pasted geometry, and new chats had no AOI; see
> [`planning/evidence/42.6.1-trial.md`](../../planning/evidence/42.6.1-trial.md).

> **Amended 2026-11-07 (Plan 44, ADR 0017).** The screening route now makes
> one MCP call, `analyze_farmland_by_polygon` with `include_map=True`, and
> returns the server `map` block as `display.map`. That block replaces the
> `get_soil_polygons_by_geometry` call and the clipped soil FeatureCollection
> described under "Map screening route" below. The same rules apply to the new
> `POST /api/geo/map` route behind "Show on map": it is untraced, does not log
> bodies, and accepts only the tools that return a `map` block (the two
> analyze tools and `get_soil_polygons_by_geometry`). See
> [ADR 0017](0017-server-map-result-contract.md).

> **Amended 2026-11-15 (Plan 54).** Corridor inputs are a separate conversation
> context from polygon `active_aoi`. A corridor may be screened directly from
> the map or attached to chat; it never replaces or widens the AOI contract.

## Context and Problem Statement

The agent app needs a map panel where a user draws or pastes an area of
interest (AOI), screens it against the deployed MCP server, and brings the
result into the chat. Plan 40 (R6) blocked AOI integration: the vendored chat
template has no `custom_inputs`/`custom_outputs` path, and handler-level
sanitizing protects model inputs and history but cannot prove that geometry is
redacted before MLflow captures the request in a trace
(`planning/evidence/40.2.1-aoi.md`, `planning/decisions/40.2.1-aoi.md`). The
first version of this ADR read ADR 0010 as forbidding geometry in prompts,
history and traces. ADR 0010 in fact treats coordinates and geometry as
public, operational project fields; its concern is personal data and Section
1619 producer information, and it records coordinate privacy as a policy
aspiration without automated enforcement.

User requests about a drawn AOI (acreage by class, LESA, exemptions, a
different soil query) need the tools to run on that AOI from the chat.

## Decision Drivers

* The agent must be able to run MCP tools on the AOI the user drew, without the
  user pasting GeoJSON.
* The model should not copy coordinates: long shapes waste context and copied
  coordinates can be wrong.
* The AOI belongs to one conversation; a new chat starts without one.
* Geometry is operational project data (ADR 0010). Personal data and Section
  1619 producer data are controlled by where the app is deployed and by user
  guidance, not by redaction in the app.
* The app stays a separate MCP client that calls the deployed tools; no
  wrapper tools on the MCP server (ADR 0012).
* Results are preliminary screening and carry the server `regulatory_notice`
  (ADR 0003).
* Local changes to the vendored frontend are allowed and listed (ADR 0015).
* The backend may run several worker processes, so it keeps no AOI state.
* Corridor workflows need linear centerlines, alternatives, staging geometry,
  and a buffer without changing polygon AOI behavior.

## Considered Options

1. **Out-of-band screening with a user-sent summary** (the first version of
   this ADR): geometry never enters the chat, so the agent cannot run tools on
   the AOI. Built and tried in Plan 42; rejected after the deployed check.
2. **Server-side AOI store** keyed by conversation: needs shared state across
   worker processes and a retention policy.
3. **Full geometry in the prompt:** the model must copy coordinates into tool
   calls; costs context on every turn and risks altered shapes.
4. **Session context with server-side substitution:** the browser keeps the
   active AOI for the conversation and sends it with each chat turn; the agent
   server tells the model the AOI reference and swaps the geometry into tool
   arguments.
5. **Span-processor redaction or disabling tracing for AOI turns:** not needed
   once geometry is allowed in traces; the processor could fail open and
   tracing is global.

## Decision Outcome

Chosen option: "Session context with server-side substitution", because the
agent can use the AOI in any tool without the model handling coordinates, and
the server stays stateless.

* **Where the AOI lives:** browser `sessionStorage`, one active AOI per
  conversation, keyed by the chat id that the server sends as
  `context.conversation_id`. The AOI is as ephemeral as the chat: without a
  chat history database (the default deployment) a reload starts a new chat
  with no AOI; with chat history on, reloading `/chat/:id` restores that
  chat's AOI from the tab. A new chat starts without one; closing the tab
  drops it. The user can detach it.
* **Chat request:** each turn with an attached AOI carries
  `custom_inputs.active_aoi = {aoi_ref, geometry, summary}` in the
  `/invocations` body. The agent server validates it with the same limits as
  the screening route; an absent or invalid AOI means no AOI for that turn,
  never an error shown to the user.
* **Model context:** the agent's instructions for that turn get a short note:
  the AOI reference, acres, the latest screening summary, and that tools run on
  the AOI when its reference is passed as the `geojson` or `geometry`
  argument. The note contains no coordinates.
* **Substitution:** before an MCP tool call, the agent server replaces a
  `geojson` or `geometry` argument equal to the active `aoi_ref` with the
  geometry. Other arguments and values are unchanged. The MCP server is not
  modified.
* **Geometry handling:** geometry may appear in chat traces, tool spans,
  request bodies and app logs. Deployments are limited to environments
  approved for the data users may submit, and users are told not to submit
  personal data or producer-supplied data covered by Section 1619 outside such
  environments. Repository files (tests, planning, evidence) keep synthetic
  coordinates only.

### Corridor context

`active_corridor` is a separate optional object in the chat request's
`custom_inputs`. The browser scopes it to the current conversation, attaches it
automatically when the corridor is complete, and can detach it independently of
`active_aoi`. The agent server validates it on each request and retains no
session state. Direct map screening is a separate stateless, untraced route; it
uses only `analyze_corridor_fppa`, requests the server map block, and submits no
Site Assessment inputs. Both pathways remain preliminary screening.

The bounded object contains a `corridor_ref` (`corridor-` plus 8 lowercase hex
characters), one primary `LineString`, up to 10 alternative `LineString`
geometries, optional indirect `Polygon`/`MultiPolygon` geometry, a finite
positive `buffer_distance`, and `buffer_units` of `feet`, `meters`, or `miles`.
The buffer distance is measured on each side of the line. Lines require at least
two finite numeric positions; polygon staging geometry uses the screening route's
body-size and vertex limits. The browser leaves distance blank until supplied.

The model receives the opaque reference and buffer description, never
coordinates. Only an `analyze_corridor_fppa` call whose `centerline` argument
exactly matches that reference receives the validated centerline, alternatives,
staging geometry, and buffer settings. Other tools and arguments are unchanged.
Corridor context can coexist with polygon AOI context; AOI substitution remains
limited to its existing `geojson`/`geometry` arguments. Corridor geometry may
appear in chat traces and logs under the same operational-data caveat above;
repository examples use synthetic coordinates only.

### Map screening route

`POST /api/geo/screen` stays for the map display and produces the summary
carried in `active_aoi`.

* **Request:** one GeoJSON geometry of type `Polygon` or `MultiPolygon`, an
  optional short `name` (never echoed into the summary) and an optional
  `aoi_ref` (`aoi-` plus 8 lowercase hex characters). The map panel sends the
  chat's active reference so the summary in `active_aoi` carries the same
  reference; without it the route mints one. App-side limits:
  total vertices at most `GEO_MAX_VERTICES` (default 2000) and a raw body of at
  most 256 KB. Other types or oversize input return 422 with a bounded message
  that contains no coordinates.
* **MCP calls:** `analyze_farmland_by_polygon` for the authoritative summary and
  notice, and `get_soil_polygons_by_geometry` with `clip=True` for the map
  layer. The MCP client is opened per request and closed. No model call, no
  `Runner`, no `@mlflow.trace`.
* **Response:** `aoi_ref` (opaque and random, `aoi-` plus 8 hex characters, not
  derived from the geometry); `display` (browser-only, may contain geometry:
  selected analysis fields, the clipped soil FeatureCollection, the notice);
  `chat_summary` and `chat_summary_text` (server-built, geometry-free). MCP
  failure returns 502 `screening_unavailable` without echoing the exception;
  a tool-level error returns 200 with `display.error` and a summary that says
  the screening failed.
* **`chat_summary` allowlist:** `aoi_ref`, `total_aoi_acres`,
  `coverage_status`, per-class `*_acres` and `*_pct` from `farmland_summary`,
  urban flag and urban acres (numbers and booleans only), up to 10 map units as
  `{musym, muname, farmlndcl, acres}` sorted by acres, the `source` service name
  and timestamp, and `regulatory_notice`. Excluded: `geometry_hash`,
  `tabular_csv`, `manifest`, free-text `limitations`, and any key containing
  `geom`, `coordinates`, `bbox` or `wkt`. Acres and percentages are rounded to
  one decimal; the text form is at most 2,000 characters.
* **Route lifecycle:** the route is stateless, does not log request bodies or
  MCP payloads (log hygiene), and creates no traces, so map-only screenings do
  not add traces without a chat session. `databricks_openai` decorates
  `McpServer.call_tool` with `@mlflow.trace`; the route calls the undecorated
  Agents SDK parent, `MCPServerStreamableHttp.call_tool`. Chat turns use the
  normal traced path.

### Consequences

* **Positive:** follow-up questions and other tools (LESA, exemptions, soil
  queries) work on the drawn AOI without pasting; the model never copies
  shapes; no server-side state; the MCP server is unchanged.
* **Negative:** geometry is in traces and app logs (the vendored provider logs
  the full `/invocations` body), so access to the experiment and logs must fit
  the deployment environment; the AOI (up to 256 KB) is sent with every turn;
  the vendored chat request path changes in four files (ADR 0015 lists them);
  one AOI per conversation; map results are labelled preliminary until the M3
  server `map` envelope exists.

### Scope boundary

Points, other input formats, multiple or labelled AOIs
(needs a multi-shape drawing and labelling interface), AOI persistence beyond
the browser tab session, overlays, the M3 `map` envelope and `custom_outputs`
are out of scope. Opt-in chat history and stored sessions (the template's chat
database, for example Lakebase), for users who choose it or for deployments in
approved secure environments, are deferred; that work decides whether the AOI
is stored with the chat.

## Validation & Compliance

Required before `Accepted`:

* Screening route tests
  (`apps/agent-fpac-soil-openai-sdk/tests/test_geo_screen.py`): route
  registered ahead of the chat proxy; response shape; `chat_summary` allowlist
  (a marker planted in geometry, `geometry_hash`, `tabular_csv`, `manifest`
  and properties is absent); vertex, type and body-size limits return 422;
  MCP exceptions return 502; a screening creates zero traces with the real
  `McpServer` class and a faked transport, with a control and a decorator
  guard.
* Session-context tests (`tests/test_aoi_context.py`, Plan 42 task 42.5.2):
  valid, absent, invalid and oversize `active_aoi`; bad `aoi_ref`; the
  instruction note has no coordinates; substitution on `geojson` and
  `geometry` only when the value equals the active reference; a LESA-shaped
  call reaches the MCP session with the geometry; requests without
  `custom_inputs` behave as before; the tests fail with substitution removed.
* Deployed trial (Plan 42 task 42.6.1): draw and paste flows work; without
  pasting, a question and a preliminary LESA on the AOI are answered with
  preliminary-screening language; a reload starts a new chat with no AOI, a
  new chat has none, detach removes it; the LESA tool call received a
  geometry, not the reference string.
