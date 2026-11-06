# Handoff: efficiency review of server and model traffic

Paste the prompt below into a new agent session at the repository root
(`fpac-soil-mcp`, branch `feature/agent-app-map2` or its successor).

---

You are reviewing the FPAC soil MCP server (`src/fpac_soil_mcp/`) and its
Databricks agent app (`apps/agent-fpac-soil-openai-sdk/`) for efficiency: bytes
sent and received between browser, agent server, MCP server and the LLM, and
tokens the LLM processes per chat turn. The goal is the smallest traffic and
model context that keeps every current integration feature working. This is a
review: measure and recommend. Do not change behaviour, tool contracts or
deployed apps without the user's approval.

## Read first

- `AGENTS.md` (repo root) and `apps/agent-fpac-soil-openai-sdk/AGENTS.md`.
- ADR 0003 (preliminary screening boundary; the regulatory notice is verbatim),
  ADR 0016 (AOI handoff: reference not coordinates to the model, map routes
  untraced, no server-side AOI state), ADR 0017 (map result contract:
  `include_map`, layers, legends, 2 MB cap).
- `planning/STATE_44.md` (decisions D1-D9, A1-A4, open items) and
  `planning/evidence/44.8.1-trial.md`, `44.10.1-trial.md`.

## Features that must keep working

- Chat with the 10 MCP tools; tool cards; regulatory notice in every result.
- Map panel AOI: draw/paste, one AOI per chat, `custom_inputs.active_aoi`, the
  agent's AOI note, server-side reference substitution.
- `/api/geo/screen` (one `analyze_farmland_by_polygon` call with
  `include_map=true`), `/api/geo/map` ("Show on map" on polygon and corridor
  cards), server legends, corridor alternatives with class breakdown and
  farmland on the map.
- Context overlays, identify popups and "Use as AOI" (browser to public
  services; not through our servers).

## Known baselines (measure again; do not trust these blindly)

- Tool list: 10 tools, about 33.5 KB of JSON locally;
  `analyze_farmland_by_polygon` alone about 10.6 KB,
  `calculate_preliminary_lesa` about 7.2 KB. The dev MCP log shows a
  31,749-byte `tools/list` response twice per chat turn (agent connect health
  check and the agent runner).
- Each chat turn opens a new MCP session: initialize (578 B), notification,
  GET stream, `tools/list` x2, tool calls, DELETE.
- Model tool calls send `include_map=false`; the `map` descriptor still adds
  about 2-2.5 KB to each analyze result in model context. Full structured
  results (for example `tabular_csv`, `manifest`, `county_segments`,
  `impact_breakdown`, `alternatives`) go to the model.
- App routes with `include_map=true`: 0.2-1.2 MB per call for typical AOIs
  (CORR-01 corridor about 0.5 MB farmland layer; two-alternative Ames corridor
  428 KB); large AOIs hit the 2 MB cap and drop layers.
- `/api/geo/map` re-runs the whole analysis (all SDA, TIGERweb and NASS
  queries) instead of reusing the chat's result.
- AOI note and screening summary: summary capped at 2000 characters
  (`geo.py` `MAX_SUMMARY_TEXT_CHARS`).
- Dev agent traces are not saved (experiment table permission), so token
  counts need another method (local runs, response `usage`, or a fixed grant).

## Questions to answer

1. Per chat turn: how many bytes and tokens go to the LLM (system prompt, tool
   schemas, history, AOI note, tool results), and which parts dominate?
2. Tool schemas: which descriptions and input schemas can shrink without
   hurting tool choice (check with the eval cases in `eval/`)? Should `tools/list`
   be cached across turns or the duplicate call removed?
3. Tool results to the model: which fields does the model need to answer and
   to keep the regulatory notice, and which (for example `tabular_csv`, geometry
   hashes, manifests, the `map` descriptor) could be dropped, summarized, or
   moved to app-only paths? Keep tool outputs schema-compatible (additive or
   opt-in only).
4. Chat history: are earlier tool outputs replayed in full on every turn?
5. App routes: can "Show on map" avoid recomputing (for example by returning
   the map block once with an opt-in, or caching per tool call within ADR 0016's
   no-server-state rule)? Is 2 MB the right cap, and is ~1 m display
   simplification right for corridor and urban layers?
6. MCP sessions: is a session per turn needed, and what does it cost in
   latency?
7. Upstream services: duplicate SDA or TIGERweb requests within one analysis
   (for example urban checks on alternatives, county lookups)?

## How to measure

- Local, in process: `FastMCP` + `register_tools` (see
  `planning/evidence/44.8.1-trial.md` notes) to size tool lists and results.
  Use the repo's synthetic or eval inputs only; never put real parcel or
  producer data in the repo.
- Token estimates: a tokenizer if available, otherwise characters / 4, stated as
  an estimate.
- Deployed: `mcp-fpac-soil-dev` app logs show per-request response sizes;
  `agent-fpac-soil-dev` for end-to-end timing. Ask the user before pushing.
- Run `make check` and `make app-check` before and after any change you are
  allowed to make.

## Deliverable

`planning/evidence/efficiency-review.md`: method, measured baseline per path
(table), ranked opportunities with estimated savings, risk to features and
ADRs, and which tests or evals would prove no regression. End with a proposed
plan (task list) for the user to approve. Do not implement it in the same
session unless the user says so.
