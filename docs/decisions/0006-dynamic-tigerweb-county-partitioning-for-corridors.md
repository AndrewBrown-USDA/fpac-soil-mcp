---
id: "0006"
title: "Dynamic TIGERweb County Partitioning for Corridors"
status: "Accepted"
date: 2026-09-18
authors:
  - "Andrew G. Brown"
supersedes: null
superseded_by: null
source_context: "EXECUTION_PLAN_7"
---

# 6. Dynamic TIGERweb County Partitioning for Corridors

## Context and Problem Statement

Linear infrastructure projects (pipelines, transmission lines, highways)
routinely cross multiple county and state boundaries. The Colorado NRCS ArcGIS
Python Toolbox — the prior reference implementation — collapsed multi-county
corridors to the single largest county by area, producing systematically
incorrect farmland assessments for cross-jurisdictional projects. The FPAC Soil
MCP Server needed to perform true multi-county corridor analysis with
independent per-segment soil and agricultural baseline queries.

## Decision Drivers

* Overcoming the desktop GIS single-county simplification was a founding project
  motivation (MASTER_PLAN §1 Problem statement).
* 7 CFR § 658.5(c) corridor Site Assessment rules require per-county agricultural
  baselines for relative rating normalization.
* USDA NASS QuickStats provides county-level agricultural statistics; accurate
  county FIPS codes are required for API queries.
* Census TIGERweb REST API provides authoritative 2020 county boundaries
  accessible without local data downloads.

## Considered Options

1. **Dynamic Census TIGERweb county intersection and partitioning** — query
   TIGERweb Counties layer at runtime to partition corridor geometries into
   discrete county segments, then query SDA and NASS independently per segment.
2. **Bundled county boundary shapefile** — ship a static county boundary dataset
   with the package and perform local intersection.
3. **Single-county approximation** — follow the existing ArcGIS toolbox pattern
   of assigning the corridor to its largest-area county.

## Decision Outcome

Chosen option: **Dynamic Census TIGERweb county intersection**, because it uses
authoritative, current census boundaries without bundled data maintenance,
enables true multi-county analysis, and integrates with the existing TIGERweb
client architecture (already used for urban area screening in EP4).

### Consequences

* **Positive**: Multi-county corridors traversing 5+ counties and state lines
  produce independent per-segment farmland analyses — a capability the reference
  ArcGIS toolbox lacks entirely.
* **Positive**: Sum reconciliation engine enforces that segment acreages sum to
  total corridor acreage within 0.1% tolerance, catching partitioning errors.
* **Positive**: NASS QuickStats integration (via `NassClient`) provides live
  county agricultural baselines with graceful `UNAVAILABLE` fallback when the
  API key is not configured.
* **Negative**: Runtime dependency on Census TIGERweb availability. Mitigated
  by the resilient HTTP client (ADR-0009) with retry logic.
* **Negative**: County partitioning proved the most architecturally complex
  feature — it drove 4 remediation plans (EP21, EP23, EP24, EP25) to resolve
  edge cases in segment intersection, rating propagation, and sum reconciliation.
* **Negative**: Adds network latency for TIGERweb + NASS queries per county
  segment, though queries are cacheable.

### Urban Overlap Propagation

Each county segment is independently screened against Census 2020 urban
boundaries. The segment response preserves the TIGERweb
`screened_acreage` value, allowing corridor consumers to distinguish partial
urban overlap from a boolean intersection alone while retaining the same
geodesic acreage method defined in ADR 0004.

## Validation & Compliance

Multi-county synthetic and real-world corridor test fixtures traversing 2+ and
5+ counties / state lines, verified offline with mocked TIGERweb/NASS/SDA
responses. Decision established in EXECUTION_PLAN_7 (2026-09-18), remediated
in EP21, EP23, EP24. Key commits: `b8613a26` (EP7), EP21 partitioning fixes,
EP24 corridor generalization (`8eea672`, `9184fb2`).
