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
| [0004](0004-geodesic-acreage-and-equal-area-buffering-strategy.md) | Geodesic Acreage Calculation & Equal-Area Buffering Strategy | Accepted | 2026-09-17 | - | - | EXECUTION_PLAN_4, 7 |
| [0005](0005-sda-server-side-polygon-clipping.md) | SDA Server-Side Polygon Clipping for Spatial Soil Analysis | Accepted | 2026-09-17 | - | - | EXECUTION_PLAN_4, 7 |
| [0006](0006-dynamic-tigerweb-county-partitioning-for-corridors.md) | Dynamic TIGERweb County Partitioning for Corridors | Accepted | 2026-09-18 | - | - | EXECUTION_PLAN_7 |
| [0007](0007-unified-lesa-module-architecture.md) | Unified LESA Module Architecture | Accepted | 2026-09-28 | - | - | EXECUTION_PLAN_17 |
| [0008](0008-nccpi-validated-public-index-with-extensible-sdv-routing.md) | NCCPI as Validated Public Productivity Index with Extensible SDV Routing | Accepted | 2026-09-28 | - | - | EXECUTION_PLAN_17, 26 |
| [0009](0009-shared-http-request-helper-with-retry-composition.md) | Shared HTTP Request Helper with Retry Composition | Accepted | 2026-09-21 | - | - | EXECUTION_PLAN_10 |
| [0010](0010-public-payload-pii-detection-and-sanitization.md) | Public Payload PII Detection & Sanitization | Accepted | 2026-09-17 | - | - | EXECUTION_PLAN_4 |
| [0011](0011-mocked-default-live-opt-in-test-architecture.md) | Mocked Default, Live Opt-In Test Architecture | Accepted | 2026-09-16 | - | - | EXECUTION_PLAN_1, 13 |
| [0012](0012-databricks-agent-app-as-separate-mcp-client.md) | Databricks Agent App as a Separate MCP Client Project | Accepted | 2026-10-22 | - | - | EXECUTION_PLAN_35 |
| [0013](0013-pin-pypi-default-index-in-every-uv-project.md) | Pin PyPI as the Default uv Index in Every uv Project | Accepted | 2026-10-22 | - | - | Commits bcf6626, f27eb3b |

## Architectural Eras

The decisions cluster into distinct eras of the project lifecycle:

**Foundation (2026-09-16)**: ADRs 0001-0003 established the MCP framework,
SQL safety policy, and regulatory authority boundary. These three decisions
have never been revisited.

**Geospatial Engine (2026-09-17-21)**: ADRs 0004-0006, 0009-0010 defined the
acreage calculation strategy, spatial query approach, corridor partitioning,
HTTP resilience, and PII detection.

**LESA Scoring (2026-09-28)**: ADRs 0007-0008 unified the Land Evaluation
and Site Assessment architecture and established the NCCPI-validated
productivity index contract.

**Cross-Cutting (2026-09-16-22)**: ADR 0011 established the test architecture
that governed all 26 execution plans.

**Databricks Delivery (2026-10-22)**: ADR 0012 set the boundary for the
Databricks chat agent app as a separate MCP client project, and ADR 0013 made
lock files portable off Databricks compute.

## Maintenance

When a future decision supersedes an existing ADR:
1. Create the new ADR with `supersedes: "NNNN"` in its frontmatter.
2. Update the superseded ADR: set `status: "Superseded"` and `superseded_by: "NNNN"`.
3. Update the table above to reflect the new status and links.
