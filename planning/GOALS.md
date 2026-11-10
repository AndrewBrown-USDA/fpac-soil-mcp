# Project Goals (`planning/GOALS.md`)

Last Updated: 2026-11-09
Source State: `planning/STATE_44.md`; `planning/MASTER_PLAN.md`

## Circled Goal (Active)

- **[G1]** PR #79 is merged and the NASS ImageServer cropland layer plus AOI histogram MCP tool are reproducibly integrated on `main`.
  - Why now: Plan 44 is complete, but PR #79 is the prerequisite for trustworthy CDL evaluation; its review fixes, merge, and post-merge validation must be complete before building evaluation coverage on top of it.
  - Exit criteria: PR #79 review fixes are complete; targeted tests and repository gates pass; the merged `main` commit exposes the cropland source and histogram tool; representative AOI results include provenance, coverage, privacy, and explicit unavailable/error behavior.
  - First action: finish the remaining review fixes on Brent's branch and run the focused PR #79 validation before merging.

## Sequenced Goals (Dependency DAG)

- **[G2]** The PR #79 CDL histogram behavior has GUI-free T1 evaluation cases with expected outputs, non-null MLflow scores, and documented deviations.
  - Depends on: G1
- **[G3]** The authoritative agricultural-land-use source, spatial schema, provenance identifiers, coverage limits, and privacy/compliance rules are documented and validated.
  - Depends on: G2
- **[G4]** Site and corridor perimeter intersections produce validated agricultural-adjacency evidence from the selected source.
  - Depends on: G3
- **[G5]** LESA Criterion 2 scoring consumes only validated agricultural evidence while preserving unavailable, not-provided, measured-zero, and explicit-override semantics.
  - Depends on: G4
- **[G6]** Criterion 2 regression, evaluation, and documentation contracts cover server and agent-facing surfaces.
  - Depends on: G5
- **[G7]** Phase 8 / Track A M3 server map-envelope support is implemented and integrated with the agent-app map panel.
  - Depends on: G6
- **[G8]** T2 evaluation against deployed `/mcp` reproduces applicable T1 cases.
  - Depends on: G6
- **[G9]** Agent-app evaluation against `/invocations` measures routing, correctness, efficiency, and notice compliance.
  - Depends on: G7
- **[G10]** The agent-app map backlog is reduced to a bounded next slice, with nonessential M2/M4 features explicitly deferred.
  - Depends on: G6

## Independent Backlog

- **[G11]** The agent-app map MVP remains deployable, tested, and documented with stable AOI session-context behavior.
- **[G12]** The deployed agent app passes the core chat/map acceptance cases with trace evidence and regulatory notices.
- **[G13]** The project planning artifacts remain consolidated into one current dependency-ordered goal graph.

Plan 44 / Track A M3-M5 is complete for prioritization. PR #79 remains the active prerequisite and is not treated as complete until merged and validated.

## Deferred

- **[G14]** Production-readiness decisions for map basemaps, formats, persistence, attribution, and authorization are resolved.
  - Trigger: M3 design and deployment hardening make one or more decisions operationally necessary.
- Multiple or labelled AOIs, persistence, custom basemaps, and other proposed map backlog items remain deferred until the M3 boundary and Phase 4 closure are stable.

## Blocked / Pruned

- **[G15]** Official FPPA/LESA determination output is provided by this server.
  - Status: Pruned
  - Reason: The repository's regulatory boundary limits this service to preliminary screening and excludes official determinations, Form AD-1006, and NRCS-CPA-106.
