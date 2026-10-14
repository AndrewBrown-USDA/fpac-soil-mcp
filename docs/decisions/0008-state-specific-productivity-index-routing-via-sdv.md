---
id: "0008"
title: "State-Specific Productivity Index Routing via SDV"
status: "Accepted"
date: 2026-09-28
authors:
  - "Andrew G. Brown"
supersedes: null
superseded_by: null
source_context: "EXECUTION_PLAN_17"
---

# 8. State-Specific Productivity Index Routing via SDV

## Context and Problem Statement

FPPA Land Evaluation scores require soil productivity ratings, but the
appropriate productivity index varies by state: Iowa uses CSR2 (Corn
Suitability Rating 2), Minnesota uses CPI (Crop Productivity Index),
California uses the Revised Storie Index, and most states default to NCCPI v3
(National Commodity Crop Productivity Index). Hardcoding table and column names
for each index would be brittle and difficult to extend. SDA provides Soil Data
Viewer (SDV) metadata that can dynamically resolve the correct table and column
for any named attribute.

## Decision Drivers

* Different states use different productivity indexes for FPPA Land Evaluation.
* SDA's `sdvattribute` metadata table maps attribute names to their storage
  locations (table, column, aggregation method).
* The fixed SQL template policy (ADR-0002) requires that all queries be named
  templates, not dynamic SQL construction.
* Null and unrated soil map units (sentinel values 99, 999, None, '') must be
  detected and excluded rather than distorting mathematical averages.

## Considered Options

1. **Dynamic SDV attribute routing** — query `sdvattribute` metadata at runtime
   to resolve table/column for the requested productivity index, then use fixed
   T-SQL templates parameterized by the resolved metadata. Support NCCPI v3,
   Iowa CSR2, Minnesota CPI, and California Storie Index with a standardized
   normalization path.
2. **Hardcoded table/column mappings per index** — maintain a static dictionary
   mapping index names to their SDA table and column locations.
3. **NCCPI v3 only** — use the national index exclusively and defer state-specific
   indexes to future phases.

## Decision Outcome

Chosen option: **Dynamic SDV attribute routing**, because it is self-describing
(new indexes can be added by name without schema changes), maintains the fixed
template policy, and handles the full diversity of state practices.

### Consequences

* **Positive**: Any productivity index registered in SDA's SDV metadata can be
  queried by name without code changes to the routing logic.
* **Positive**: Null/unrated screening with explicit notices prevents mathematical
  distortion and provides transparency in LE scoring.
* **Positive**: The routing feeds directly into the unified LESA module (ADR-0007)
  for relative rating normalization.
* **Negative**: SDV metadata queries add one extra SDA round-trip per unique
  index request. This is acceptable for the screening use case.
* **Negative**: The cointerp aggregation rules for state productivity queries
  required a specific fix in EP20 (commit `9cbcc7ed`: "use standard cointerp
  rules for state productivity queries and harden sentinel handling").
* **Negative**: Three remediation waves (EP20, EP22, EP23) were needed to fully
  stabilize the interaction between SDV routing, cointerp rules, and the LESA
  normalization pipeline.

## Validation & Compliance

Decision established in EXECUTION_PLAN_17 (2026-09-28). Cointerp rules fixed
in EP20 (commit `9cbcc7ed`). Productivity preservation validated in EP22
(commit `a8c26940`). Ratings remediation in EP23 (commit `bd158919`). Offline
benchmarks verified within 0.01 tolerance against known soil profiles.
