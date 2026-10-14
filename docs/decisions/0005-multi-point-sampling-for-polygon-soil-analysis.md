---
id: "0005"
title: "Multi-Point Sampling for Polygon Soil Analysis"
status: "Accepted"
date: 2026-09-17
authors:
  - "Andrew G. Brown"
supersedes: null
superseded_by: null
source_context: "EXECUTION_PLAN_4"
---

# 5. Multi-Point Sampling for Polygon Soil Analysis

## Context and Problem Statement

FPPA polygon screening requires determining which SSURGO soil map units
intersect an Area of Interest (AOI) and their relative acreages. SDA provides
spatial query functions (`SDA_Get_Mukey_from_intersection_with_WktWgs84`), but
complex polygon WKT strings can exceed SDA's practical query size and timeout
limits. The system needed a reliable spatial query strategy that works within
SDA's constraints while maintaining the fixed SQL template policy (ADR-0002).

## Decision Drivers

* SDA has practical limits on complex polygon WKT query sizes and response times.
* The fixed SQL template policy (ADR-0002) prohibits ad-hoc spatial SQL.
* Results must support acreage-weighted farmland classification breakdowns.
* Must work for both compact site polygons and elongated corridor buffers.

## Considered Options

1. **Deterministic multi-point sampling within polygons** — generate a regular
   grid of sample points within the AOI, query SDA for the map unit at each
   point, weight by Voronoi area or equal spacing to estimate acreage fractions.
2. **Server-side polygon intersection via SDA spatial queries** — pass the full
   WKT polygon to SDA and let the server compute intersecting map units with
   exact areas.
3. **Client-side intersection with downloaded SSURGO shapefiles** — download
   soil survey boundaries locally and compute intersections with `shapely`.

## Decision Outcome

Chosen option: **Deterministic multi-point sampling**, because it stays within
SDA's query size limits, works with the fixed SQL template architecture, and
produces results within the 0.1% acreage tolerance benchmark established in
ADR-0004.

### Consequences

* **Positive**: Sampling queries use the same `SDA_Get_Mukey_from_intersection_with_WktWgs84`
  point template used for single-point lookups, maintaining template consistency.
* **Positive**: The approach scaled to corridor segment analysis (EP7) without
  modification — corridor buffer polygons are sampled the same way as site AOIs.
* **Positive**: Acreage-weighted aggregation from sample points directly feeds
  the Land Evaluation relative rating calculation (EP17, ADR-0007/0008).
* **Negative**: Sampling resolution is a trade-off — too few points miss small
  map units, too many increase query count. The current grid density was tuned
  against the 50-fixture benchmark corpus.
* **Negative**: Very small or narrow polygons may under-sample, though this is
  mitigated by adaptive sampling density.

## Validation & Compliance

50-fixture benchmark corpus (EP4) verified within 0.1% acreage tolerance.
Extended to corridor segments in EP7. Evidence: `polygon_analysis.py` creation
(EP4, commit `a3eb38dc`); corridor adaptation (EP7, commit `b8613a26`).
