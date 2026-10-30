---
id: "0016"
title: "Out-of-Band AOI Screening with a User-Sent Chat Summary"
status: "Proposed"
date: 2026-10-30
authors:
  - "Andrew G. Brown"
supersedes: null
superseded_by: null
source_context: "EXECUTION_PLAN_40, EXECUTION_PLAN_42"
---

# 16. Out-of-Band AOI Screening with a User-Sent Chat Summary

## Context and Problem Statement

The agent app needs a map panel where a user draws or pastes an area of
interest (AOI), screens it against the deployed MCP server, and brings the
result into the chat. Plan 40 (R6) blocked AOI integration: the vendored chat
template has no `custom_inputs`/`custom_outputs` path, and handler-level
sanitizing protects model inputs and history but cannot prove that geometry is
redacted before MLflow captures the request in a trace
(`planning/evidence/40.2.1-aoi.md`, `planning/decisions/40.2.1-aoi.md`). ADR
0010 forbids raw coordinates, WKT/GeoJSON, bounding boxes and parcel
properties in prompts, history, traces and storage.

## Decision Drivers

* Raw geometry must never reach model context, chat history or traces, and
  this must be provable offline.
* The app stays a separate MCP client that calls the deployed tools; no
  wrapper tools (ADR 0012).
* Results are preliminary screening and carry the server `regulatory_notice`
  (ADR 0003).
* Minimal change to the vendored frontend and server (ADR 0015).
* The backend may run several worker processes.

## Considered Options

1. **Out-of-band `POST /api/geo/screen`** that calls the MCP tools directly and
   returns a server-built, geometry-free summary that the user reviews and
   sends as a normal chat turn.
2. **Template change to forward `custom_inputs`, plus an MLflow span processor
   that redacts geometry** -- the processor fails open if it errors, the timing
   of the request preview against the processor is unverified, and it breaks
   the upstream base in several places.
3. **Disable tracing for AOI turns** -- tracing and autologging are global, so
   this is unsafe under concurrent requests and hides normal chat turns.
4. **A separate map app** -- duplicates auth, deployment and UI, and does not
   put the result in the chat view.

## Decision Outcome

Chosen option: "Out-of-band `/api/geo/screen`", because geometry never enters
the agent invoke path at all, so there is nothing to redact before tracing.

* **Request:** one GeoJSON geometry of type `Polygon` or `MultiPolygon` and an
  optional short `name` (never echoed into the summary). App-side limits:
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
* **Handoff:** the panel puts `chat_summary_text` into the chat input. The user
  reviews, edits and sends it as an ordinary turn. There is no hidden
  injection, no agent-side lookup tool and no `custom_inputs`.
* **Privacy and lifecycle:** the route does not log request bodies or MCP
  payloads, creates no traces, and is stateless (no server-side AOI cache).
  The AOI lives only in browser session state.

### Consequences

* **Positive:** the privacy property is structural and testable offline;
  no change to the agent invoke path or the MCP server; the user sees exactly
  what the model receives.
* **Negative:** chat and screening are decoupled, so the model answers from the
  summary and does not re-run tools on the geometry; map results are labelled
  preliminary until the M3 server `map` envelope exists; a user can still type
  coordinates into the chat themselves, which this decision does not guard
  against.

### Scope boundary

Lines and corridors, points, other input formats, multiple AOIs, AOI
persistence, overlays, the M3 `map` envelope and `custom_inputs`/
`custom_outputs` are out of scope.

## Validation & Compliance

Required before `Accepted`:

* Offline tests (`apps/agent-fpac-soil-openai-sdk/tests/test_geo_screen.py`):
  route registered ahead of the chat proxy; happy-path response shape; a
  marker string planted in geometry, `geometry_hash`, `tabular_csv`,
  `manifest` and properties is absent from `chat_summary` and its text, and no
  geometry-like key appears; vertex, geometry-type and body-size limits return
  422 without the marker; MCP exceptions return 502 without the marker; a
  screening call creates zero traces in a local SQLite tracking store; DEBUG
  logs contain no marker.
* Deployed trial (Plan 42 task 42.5.1): draw and paste flows work, the sent
  summary is answered with preliminary-screening language, traces from the
  trial window contain no coordinate objects or coordinate-like values, and the
  screening calls themselves created no traces.
