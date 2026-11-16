# Project Goals (`planning/GOALS.md`)

Last Updated: 2026-11-15
Source State: `planning/STATE_52.md`; `planning/MASTER_PLAN.md`

## Circled Goal (Active)

- **[G25]** The preliminary LESA call is blocked unless its submitted Site Assessment answers match a confirmed summary in conversation history, and Criterion 7 farm-acre inputs match a confirmed registry band.
  - Why now: G25 is the only internal critical-path item that can finish within 24 hours. It unblocks G26 (acceptance evidence) and then G27 (dev-app trial). G1 is externally gated, so it cannot be the active focus.
  - Exit criteria: Root and agent-app test suites pass with the D12/D13 preflight rejection and the D14 coupled AOI-context fixes; root Ruff check and format pass. The Databricks-authenticated chat trial stays open until local auth is configured.
  - First action: Resume worker worktree `.worktrees\52.3.1` (branch `feature/sa-checklist2-52.3.1-worker`) and apply the D12/D13 preflight fix.

## Sequenced Goals (Dependency DAG)

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

## Independent Backlog

- **[G35]** Offline demonstration mode runs both benchmark testbeds with explicit fixture-mode provenance.
- **[G36]** The T1 model client uses model gateway and records non-null MLflow scores for every ground-truth case.
- **[G37]** The agent app has a separate, repeatable deployed evaluation for its `/invocations` interface and supported chat/map flows.
- **[G38]** The agent map supports the selected next geometry workflows, including corridor alternatives and labelled AOIs.
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
