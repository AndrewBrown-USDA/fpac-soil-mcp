# Project Goals (`planning/GOALS.md`)

Last Updated: 2026-11-15
Source State: `planning/STATE_53.md`; `planning/MASTER_PLAN.md`; user-approved map/UI priorities

## Circled Goal (Active)

- **[G42]** Agent-app map controls use compact icon-only buttons with accessible hover/focus labels; drawing and measuring use a crosshair cursor; distance measurement defaults to miles.
  - Why now: User-selected usability-first bottleneck; improves the map workspace for every following map task and is independently verifiable.
  - Exit criteria: Focused frontend tests verify icon controls expose accessible names/tooltips, active drawing/measurement uses a crosshair rather than a hand cursor, and miles is the initial measure unit; frontend lint/build pass.
  - First action: Inspect MapPanel toolbar/button and cursor lifecycle anchors, current tooltip patterns, and test seams; draft the 54.1.1 micro-plan.

## Sequenced Goals (Dependency DAG)

- **[G25]** The preliminary LESA call is blocked unless its submitted Site Assessment answers match a confirmed conversation summary, and Criterion 7 farm-acre inputs match a confirmed registry band. *(Completed in Plan 52; retained as the prerequisite for G26.)*
- **[G26]** Automated acceptance evidence verifies interview sequencing, answer-to-band scoring, conservative missing-input handling, and the confirmation gate.
  - Depends on: G25, G28, G29, G30
- **[G27]** The approved dev-app trial confirms the guided interview, confirmed-summary gate, and preliminary-only result behavior.
  - Depends on: G26
- **[G2]** T2 reproduces applicable T1 cases through deployed `/mcp` and records transport-specific deviations.
  - Depends on: G1 (Blocked; see below)
- **[G3]** Criterion 2 performance and reliability claims are supported by repeatable measurements from the deployed service, including latency, retries, failures, and environment details.
  - Depends on: G2
- **[G4]** Public MCP tools expose strict Pydantic input contracts and structured, source-aware failure envelopes without changing the preliminary-authority boundary.
  - Depends on: G1 (Blocked; see below)
- **[G5]** The live map app preserves unknown/unmapped/partial/not-prime distinctions and prevents map/chat flows from implying suitability, exemption, clearance, or a preferred site.
  - Depends on: G1, G2 (Blocked; see below)
- **[G6]** Criterion 2 performance and reliability evidence reports reproducible inputs, environment, commit SHA, p50/p95/p99 latency, retries, failure rate, memory, repeated-run stability, bounded concurrency, and deployed transport results.
  - Depends on: G3, G4
- **[G7]** Evaluation and planning documentation publishes the test setup, inputs, results, limitations, and verification gates required for submission judging.
  - Depends on: G3, G5, G6
- **[G8]** PR #79 CDL integration is merged and validated before agricultural-land adjacency evaluation is expanded.
  - Depends on: existing PR #79 review/merge work
- **[G16]** An authority-safe evidence contract defines how the agent chat/map workflow collects AD-1006 Site Assessment judgments and presents distinct machine-derived CDL context, analyst responses, rationale, provenance, and verification state.
  - Depends on: G1 (Blocked; see below)
- **[G17]** The agent chat interviews users conversationally across all 12 AD-1006 Site Assessment criteria, allows unknown/partial answers, captures rationale, and confirms the summary before submitting supported facts to the existing preliminary LESA calculator.
  - Depends on: G16
- **[G18]** The AOI map displays a full CDL class distribution using the latest verified vintage, with coverage, provenance, and preliminary-use limitations; it does not default to a binary agricultural percentage.
  - Depends on: G16
- **[G19]** The map displays a separate CDL class distribution for the one-mile buffer-minus-AOI ring as nearby land-cover context, not as a perimeter-contact ratio.
  - Depends on: G18
- **[G20]** The map displays a full CDL class distribution in a 30 m exterior band as a non-authoritative near-perimeter proxy, not literal boundary contact or verified Criterion 2 evidence.
  - Depends on: G18
- **[G21]** The spatial response envelope meets the remaining Phase 8 contract for status, provenance, authority, and privacy metadata.
- **[G22]** Automated map-to-table checks enforce the 0.1% acreage-tolerance exit criterion.
  - Depends on: G21
- **[G23]** A validated-resource-backed Site Assessment tool records criterion questions, selected bands, evidence, comments, provenance, and unknown/skipped states as structured conversation items.
  - Depends on: G16, G17
- **[G24]** Site Assessment question and summary cards make registry-defined questions, choices, citations, and point schedules clear, and let users answer, edit, or confirm structured records.
  - Depends on: G23
- **[G28]** Missing, unknown, unavailable, and skipped Site Assessment inputs receive labelled conservative maximum points while the result remains undetermined and exposes a separate conservative bound.
  - Depends on: G17
- **[G29]** A CDL result cannot be shown on the map after its AOI has been replaced or detached.
  - Depends on: G18
- **[G30]** A LESA request screens first, offers Start/Skip before any interview-based LESA call, and requests combined CDL context at most once for an attached or pasted AOI.
  - Depends on: G23
- **[G31]** `src/fpac_soil_mcp` is organized into layered subpackages (`core/`, `models/`, `spatial/`, `clients/`, `domain/`, `mcp/`) with zero circular-import workarounds, unified LESA/corridor scoring in `domain/lesa.py`, and all existing tests (`make check`, `make test-eval`) passing.
  - Why now: Eliminates circular-import workarounds (`map_contract.py`, `lesa_tools.py`), unifies duplicated LESA/SA logic, and creates the clean `mcp/context.py` + `mcp/tools/` seam needed for canonical MCP `_meta` / `ToolResult` adoption (`G32`) and tool interface normalization (`G33`).
  - Exit criteria: `make check` and `make test-eval` pass with 0 failures; zero lazy/mid-file circular-import workarounds in `src/fpac_soil_mcp`.
  - First action: Create `src/fpac_soil_mcp/core/` and `src/fpac_soil_mcp/models/` and move the zero-I/O base modules first.
- **[G32]** Map-enabled tools (`analyze_farmland_by_polygon`, `analyze_corridor_fppa`, `get_soil_polygons_by_geometry`) read `include_map` from MCP request `_meta` via `Context` and return `ToolResult(structured_content=..., meta={"map": ...})`, removing `include_map` from LLM-facing tool schemas and updating `apps/agent-fpac-soil-openai-sdk` to use `_meta`.
  - Depends on: G31
- **[G33]** All 11 MCP tools use consistent `geometry` parameter naming, typed Pydantic/`ToolResult` returns, and uniform `ToolResult(is_error=True, ...)` error handling, with `manifest.yaml`, `server.json`, and `eval/contract/` updated to match.
  - Depends on: G31
- **[G34]** Large or deferred map layers are exposed via an MCP resource template (`fppa://map/{geometry_hash}/layers`) with `ResourceLink` references when `ToolResult.meta["map"]` truncates layers.
  - Depends on: G32
- **[G43]** The map pane displays the current server-provided screening legend and a CDL code/color key sourced from the official USDA NASS legend, without treating context imagery as analysis evidence.
  - Depends on: G42
- **[G49]** The fixed NAIP context overlay uses the user-selected USDA FPAC `conus_naip` ImageServer through a fixed `exportImage` request, with its test-purpose metadata caveat documented.
  - Depends on: G42, G43
- **[G44]** Returned SSURGO farmland-result polygons become visible when new screening results return, while the separate SSURGO context overlay remains an independent user-controlled layer.
  - Depends on: G42, G43
- **[G45]** ADR 0016 and the app's stateless session context support a corridor input distinct from polygon AOI, containing a primary centerline, alternatives, indirect/staging geometry, and buffer settings.
  - Depends on: G42
- **[G46]** The app exposes a validated, untraced map route that submits corridor inputs to the existing `analyze_corridor_fppa` tool and returns a bounded display result with its server map block and regulatory notice.
  - Depends on: G45
- **[G47]** Corridor inputs attach to chat as separate per-conversation context, can be detached, and are substituted only into the existing corridor tool call without requiring the model to copy coordinates.
  - Depends on: G45
- **[G48]** The map supports drawing/editing a primary corridor centerline, alternative centerlines, and indirect/staging polygons; a required per-side buffer distance and units feed both direct map screening and chat handoff, with screening kept preliminary.
  - Depends on: G45, G46, G47
- **[G38]** The agent map supports selected geometry workflows, including corridor alternatives and labelled AOIs.
  - Depends on: G42, G43, G44, G45, G46, G47, G48, G49

## Independent Backlog

- **[G35]** Offline demonstration mode runs both benchmark testbeds with explicit fixture-mode provenance.
- **[G36]** The T1 model client uses AI Gateway and records non-null MLflow scores for every ground-truth case.
- **[G37]** The agent app has a separate, repeatable deployed evaluation for its `/invocations` interface and supported chat/map flows.
- **[G39]** Evaluation ground truth has domain-owner sign-off for its expected facts, behaviors, and scoring criteria.
- **[G40]** Deployment operations document health checks and least-privilege client grants.

## Deferred

- **[G12]** Production authorization, user identity/RBAC, official-system integrations, and agency security controls are established.
  - Trigger: An agency-approved production operating model and ATO path are available.
- **[G13]** Additional agricultural-land adjacency sources and derived Criterion 2 scoring are expanded.
  - Trigger: PR #79/CDL integration is merged and validated, and an authoritative adjacency source is approved.
- **[G14]** The deployed MCP service adopts stateless Streamable HTTP.
  - Trigger: A separately scoped compatibility check confirms stateless transport behavior for supported clients and deployment infrastructure.

## Blocked / Pruned

- **[G1]** The deployed MCP service has a documented, authenticated, and repeatable access path for T2 evaluation.
  - Status: Blocked / External Watch
  - Reason: Its first action requires provisioning a dedicated T2 service principal with `CAN_USE` on `mcp-fpac-soil` and configuring the Databricks run-as identity. Those are external Databricks admin steps. Blocks G2, G4, G5, and G16. Revisit when the service principal is provisioned.
- **[G15]** Issue #88 is linked to and closed by the completed corpus consolidation.
  - Status: Blocked / External Watch
  - Reason: The corpus implementation is complete in the current branch, but issue closure depends on delivering the changes through the appropriate PR and updating the external tracker.
- **[G41]** The agent issues official FPPA/LESA determinations, signs AD-1006/CPA-106, grants legal exemptions, or selects preferred alternatives.
  - Status: Pruned
  - Reason: The repository's authority boundary permits preliminary screening and neutral comparison only.
