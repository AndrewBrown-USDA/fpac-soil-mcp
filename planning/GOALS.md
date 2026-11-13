# Project Goals (`planning/GOALS.md`)

Last Updated: 2026-11-12
Source State: `planning/STATE_48.md`; `planning/MASTER_PLAN.md`

## Circled Goal (Active)

- **[G1]** The deployed MCP service has a documented, authenticated, and repeatable access path for T2 evaluation.
  - Why now: T2 is the main bridge from offline/in-process evaluation to deployed behavior. Proving access and session handling unblocks transport-level evaluation and reproducible service evidence.
  - Exit criteria: Dedicated service-principal M2M and the current Streamable HTTP session behavior are documented; a smoke run initializes deployed `/mcp`, discovers tools, calls `explain_fppa_screening_scope`, and records sanitized source and commit metadata.
  - First action: Provision a dedicated T2 evaluation service principal with only `CAN_USE` on `mcp-fpac-soil` and configure the Databricks run-as identity.

## Sequenced Goals (Dependency DAG)

- **[G2]** T2 reproduces applicable T1 cases through deployed `/mcp` and records transport-specific deviations.
  - Depends on: G1
- **[G3]** Criterion 2 performance and reliability claims are supported by repeatable measurements from the deployed service, including latency, retries, failures, and environment details.
  - Depends on: G2
- **[G4]** The spatial response envelope meets the remaining Phase 8 contract for status, provenance, authority, and privacy metadata.
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
