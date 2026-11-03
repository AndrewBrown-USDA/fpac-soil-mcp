# Project Goals (`planning/GOALS.md`)

Last Updated: 2026-11-03
Source State: `planning/STATE_42.md`; `planning/MASTER_PLAN.md`

## Circled Goal (Active)

- **[G1]** Phase 4 Criterion 2 perimeter agricultural adjacency is implemented, verified, and documented as complete.
  - Why now: Phase 4 is explicitly partially complete, and Criterion 2 is the next server plan; closing it removes the main server-roadmap bottleneck before expanding Phase 8.
  - Exit criteria: bounded server implementation with explicit unavailable-data behavior; focused regression/evaluation coverage; offline repository checks pass; Phase 4 state and master-plan records no longer list Criterion 2 as open.
  - First action: inspect existing perimeter-adjacency research and spatial/client abstractions, then write the smallest executable Criterion 2 plan.

## Sequenced Goals (Dependency DAG)

- **[G8]** Phase 4 LESA and Site Assessment outputs have a complete regression/evaluation contract across server and agent surfaces.
  - Depends on: G1
- **[G2]** Phase 8 / Track A M3 server map-envelope support is implemented and integrated with the agent-app map panel.
  - Depends on: G1
- **[G4]** The agent-app map backlog is reduced to a bounded next slice, with nonessential M2/M4 features explicitly deferred.
  - Depends on: G2
- **[G6]** T2 evaluation against deployed `/mcp` reproduces applicable T1 cases.
  - Depends on: G2
- **[G7]** Agent-app evaluation against `/invocations` measures routing, correctness, efficiency, and notice compliance.
  - Depends on: G2

## Independent Backlog

- **[G3]** The agent-app map MVP remains deployable, tested, and documented with stable AOI session-context behavior.
- **[G5]** The deployed agent app passes the core chat/map acceptance cases with trace evidence and regulatory notices.
- **[G9]** The project planning artifacts have one current dependency-ordered goal graph instead of fragmented historical plan/state records.

## Deferred

- **[G10]** Production-readiness decisions for map basemaps, formats, persistence, attribution, and authorization are resolved.
  - Trigger: M3 design and deployment hardening make one or more decisions operationally necessary.
- Multiple or labelled AOIs, persistence, custom basemaps, and other proposed map backlog items remain deferred until the M3 boundary and Phase 4 closure are stable.

## Blocked / Pruned

- None. No candidate was externally blocked or pruned; deferred map items remain valid backlog.
