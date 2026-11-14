# Project Goals (`planning/GOALS.md`)

Last Updated: 2026-11-14
Source State: `planning/STATE_48.md`; `planning/MASTER_PLAN.md`

## Circled Goal (Active)

- **[G17]** `src/fpac_soil_mcp` is organized into layered subpackages (`core/`, `models/`, `spatial/`, `clients/`, `domain/`, `mcp/`) with zero circular-import workarounds, unified LESA/corridor scoring in `domain/lesa.py`, and all existing tests (`make check`, `make test-eval`) passing.
  - Why now: Eliminates circular-import workarounds (`map_contract.py`, `lesa_tools.py`), unifies duplicated LESA/SA logic, and creates the clean `mcp/context.py` + `mcp/tools/` seam needed for canonical MCP `_meta` / `ToolResult` adoption (`G18`) and tool interface normalization (`G19`).
  - Exit criteria: `make check` and `make test-eval` pass with 0 failures; zero lazy/mid-file circular-import workarounds in `src/fpac_soil_mcp`.
  - First action: Create `src/fpac_soil_mcp/core/` and `src/fpac_soil_mcp/models/` and move the zero-I/O base modules first.

## Sequenced Goals (Dependency DAG)

- **[G18]** Map-enabled tools (`analyze_farmland_by_polygon`, `analyze_corridor_fppa`, `get_soil_polygons_by_geometry`) read `include_map` from MCP request `_meta` via `Context` and return `ToolResult(structured_content=..., meta={"map": ...})`, removing `include_map` from LLM-facing tool schemas and updating `apps/agent-fpac-soil-openai-sdk` to use `_meta`.
  - Depends on: G17
- **[G19]** All 11 MCP tools use consistent `geometry` parameter naming, typed Pydantic/`ToolResult` returns, and uniform `ToolResult(is_error=True, ...)` error handling, with `manifest.yaml`, `server.json`, and `eval/contract/` updated to match.
  - Depends on: G17
- **[G20]** Large or deferred map layers are exposed via an MCP resource template (`fppa://map/{geometry_hash}/layers`) with `ResourceLink` references when `ToolResult.meta["map"]` truncates layers.
  - Depends on: G18
- **[G1]** The deployed MCP service has a documented, authenticated, and repeatable access path for T2 evaluation.
- **[G2]** T2 reproduces applicable T1 cases through deployed `/mcp` and records transport-specific deviations.
  - Depends on: G1
- **[G3]** Criterion 2 performance and reliability claims are supported by repeatable measurements from the deployed service, including latency, retries, failures, and environment details.
  - Depends on: G2
- **[G4]** The spatial response envelope meets the remaining Phase 8 contract for status, provenance, authority, and privacy metadata.
  - Depends on: G18
- **[G5]** Automated map-to-table checks enforce the 0.1% acreage-tolerance exit criterion.
  - Depends on: G4

## Independent Backlog

- **[G6]** Offline demonstration mode runs both benchmark testbeds with explicit fixture-mode provenance.
- **[G7]** The T1 model client uses AI Gateway and records non-null MLflow scores for every ground-truth case.
- **[G8]** The agent app has a separate, repeatable deployed evaluation for its `/invocations` interface and supported chat/map flows.
- **[G9]** The agent map supports the selected next geometry workflows, including corridor alternatives and labelled AOIs.
- **[G10]** Evaluation ground truth has domain-owner sign-off for its expected facts, behaviors, and scoring criteria.
- **[G11]** Deployment operations document health checks and least-privilege client grants.

## Deferred

- **[G12]** Production authorization, user identity/RBAC, official-system integrations, and agency security controls are established.
  - Trigger: An agency-approved production operating model and ATO path are available.
- **[G13]** Additional agricultural-land adjacency sources and derived Criterion 2 scoring are expanded.
  - Trigger: PR #79/CDL integration is merged and validated, and an authoritative adjacency source is approved.
- **[G14]** The deployed MCP service adopts stateless Streamable HTTP.
  - Trigger: A separately scoped compatibility check confirms stateless transport behavior for supported clients and deployment infrastructure.

## Blocked / Pruned

- **[G15]** Issue #88 is linked to and closed by the completed corpus consolidation.
  - Status: Blocked / External Watch
  - Reason: The corpus implementation is complete in the current branch, but issue closure depends on delivering the changes through the appropriate PR and updating the external tracker.
- **[G16]** The agent issues official FPPA/LESA determinations, signs AD-1006/CPA-106, grants legal exemptions, or selects preferred alternatives.
  - Status: Pruned
  - Reason: The repository's authority boundary permits preliminary screening and neutral comparison only.
