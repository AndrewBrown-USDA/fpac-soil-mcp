# Project Goals (`planning/GOALS.md`)

Last Updated: 2026-11-03
Source State: `planning/STATE_43.md`; `planning/MASTER_PLAN.md`

## Circled Goal (Active)

- **[G1]** Criterion 2 awards verified agricultural-adjacency points only when an authoritative spatial source confirms current agricultural land use along the project perimeter.
  - Why now: PR #74 delivers the non-urban screening scaffold and safety guardrails, but authoritative current agricultural land-use evidence remains the closure requirement.
  - Exit criteria: an authoritative source and provenance contract are integrated for site and corridor geometries; perimeter intersections produce explicit measured/unavailable/error states; LESA scoring accepts only validated agricultural evidence; privacy/compliance constraints are enforced; focused offline tests and repository checks pass.
  - First action: inventory candidate authoritative spatial agricultural-land-use datasets and select one with sufficient coverage, provenance, privacy posture, and deterministic testability.

## Sequenced Goals (Dependency DAG)

- **[G2]** The authoritative agricultural-land-use source, spatial schema, provenance identifiers, coverage limits, and privacy/compliance rules are documented and validated.
  - Depends on: G1
- **[G3]** Site and corridor perimeter intersections produce validated agricultural-adjacency evidence from the selected source.
  - Depends on: G2
- **[G4]** LESA Criterion 2 scoring consumes only validated agricultural evidence while preserving unavailable, not-provided, measured-zero, and explicit-override semantics.
  - Depends on: G3
- **[G5]** Criterion 2 regression, evaluation, and documentation contracts cover server and agent-facing surfaces.
  - Depends on: G4
- **[G6]** Phase 8 / Track A M3 server map-envelope support is implemented and integrated with the agent-app map panel.
  - Depends on: G5
- **[G7]** T2 evaluation against deployed `/mcp` reproduces applicable T1 cases.
  - Depends on: G6
- **[G8]** Agent-app evaluation against `/invocations` measures routing, correctness, efficiency, and notice compliance.
  - Depends on: G6
- **[G9]** The agent-app map backlog is reduced to a bounded next slice, with nonessential M2/M4 features explicitly deferred.
  - Depends on: G6

## Independent Backlog

- **[G10]** The agent-app map MVP remains deployable, tested, and documented with stable AOI session-context behavior.
- **[G11]** The deployed agent app passes the core chat/map acceptance cases with trace evidence and regulatory notices.
- **[G12]** The project planning artifacts remain consolidated into one current dependency-ordered goal graph.

## Deferred

- **[G13]** Production-readiness decisions for map basemaps, formats, persistence, attribution, and authorization are resolved.
  - Trigger: M3 design and deployment hardening make one or more decisions operationally necessary.
- Multiple or labelled AOIs, persistence, custom basemaps, and other proposed map backlog items remain deferred until the M3 boundary and Phase 4 closure are stable.

## Blocked / Pruned

- **[G14]** Official FPPA/LESA determination output is provided by this server.
  - Status: Pruned
  - Reason: The repository's regulatory boundary limits this service to preliminary screening and excludes official determinations, Form AD-1006, and NRCS-CPA-106.
