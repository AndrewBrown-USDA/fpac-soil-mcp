# Architecture Decision Records

This directory contains the Architecture Decision Records (ADRs) for the
`fpac-soil-mcp` project. Each ADR documents an enduring architectural decision
with its context, considered options, chosen outcome, and consequences.

ADRs follow the [MADR](https://adr.github.io/madr/) format with YAML frontmatter.
They are generated from the evolution digest produced by `git-history-interval-study`
and refined through `adr-distillation`.

## Decision Index

| ID | Title | Status | Date | Supersedes | Superseded By | Context |
|---|---|---|---|---|---|---|
| [0001](0001-fastmcp-server-framework-and-package-layout.md) | FastMCP Server Framework & src-Layout Package Structure | Accepted | 2026-09-16 | - | - | EXECUTION_PLAN_1 |
| [0002](0002-fixed-sql-templates-over-user-passthrough.md) | Fixed SQL Templates Over User SQL Passthrough | Accepted | 2026-09-16 | - | - | EXECUTION_PLAN_1 |
| [0003](0003-preliminary-screening-authority-boundary.md) | Preliminary Screening Authority Boundary | Accepted | 2026-09-16 | - | - | EXECUTION_PLAN_1 |
| [0004](0004-equal-area-projection-strategy.md) | Equal-Area Projection Strategy (EPSG:6933 / Local CRS) | Accepted | 2026-09-17 | - | - | EXECUTION_PLAN_4 |
| [0005](0005-multi-point-sampling-for-polygon-soil-analysis.md) | Multi-Point Sampling for Polygon Soil Analysis | Accepted | 2026-09-17 | - | - | EXECUTION_PLAN_4 |
| [0006](0006-dynamic-tigerweb-county-partitioning-for-corridors.md) | Dynamic TIGERweb County Partitioning for Corridors | Accepted | 2026-09-18 | - | - | EXECUTION_PLAN_7 |
| [0007](0007-unified-lesa-module-architecture.md) | Unified LESA Module Architecture | Accepted | 2026-09-28 | - | - | EXECUTION_PLAN_17 |
| [0008](0008-state-specific-productivity-index-routing-via-sdv.md) | State-Specific Productivity Index Routing via SDV | Accepted | 2026-09-28 | - | - | EXECUTION_PLAN_17 |
| [0009](0009-resilient-http-client-with-retry-architecture.md) | Resilient HTTP Client with Retry Architecture | Accepted | 2026-09-17 | - | - | EXECUTION_PLAN_4, 7 |
| [0010](0010-section-1619-privacy-and-coordinate-redaction.md) | Section 1619 Privacy & Coordinate Redaction | Accepted | 2026-09-17 | - | - | EXECUTION_PLAN_4 |
| [0011](0011-mocked-default-live-opt-in-test-architecture.md) | Mocked Default, Live Opt-In Test Architecture | Accepted | 2026-09-16 | - | - | EXECUTION_PLAN_1, 13 |

## Architectural Eras

The decisions cluster into distinct eras of the project lifecycle:

**Foundation (2026-09-16)**: ADRs 0001-0003 established the MCP framework,
SQL safety policy, and regulatory authority boundary. These three decisions
have never been revisited.

**Geospatial Engine (2026-09-17-18)**: ADRs 0004-0006, 0009-0010 defined the
projection strategy, spatial query approach, corridor partitioning, HTTP
resilience, and privacy enforcement.

**LESA Scoring (2026-09-28)**: ADRs 0007-0008 unified the Land Evaluation
and Site Assessment architecture and introduced dynamic productivity index
routing.

**Cross-Cutting (2026-09-16-22)**: ADR 0011 established the test architecture
that governed all 26 execution plans.

## Maintenance

When a future decision supersedes an existing ADR:
1. Create the new ADR with `supersedes: "NNNN"` in its frontmatter.
2. Update the superseded ADR: set `status: "Superseded"` and `superseded_by: "NNNN"`.
3. Update the table above to reflect the new status and links.
