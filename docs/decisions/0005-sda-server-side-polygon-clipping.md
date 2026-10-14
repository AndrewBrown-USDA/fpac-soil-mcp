---
id: "0005"
title: "SDA Server-Side Polygon Clipping for Spatial Soil Analysis"
status: "Accepted"
date: 2026-09-17
authors:
  - "Andrew G. Brown"
supersedes: null
superseded_by: null
source_context: "EXECUTION_PLAN_4, EXECUTION_PLAN_7"
---

# 5. SDA Server-Side Polygon Clipping for Spatial Soil Analysis

## Context and Problem Statement

FPPA polygon screening requires determining which SSURGO soil map units
intersect an Area of Interest (AOI) and their exact acreages within the AOI
boundary. The system needed a spatial query strategy that produces accurate
clipped acreages while working within the fixed SQL template policy (ADR-0002).

## Decision Drivers

* Acreage accuracy: FPPA Land Evaluation scoring requires precise per-map-unit
  acreage within the AOI, not approximations.
* Fixed SQL template policy (ADR-0002): Spatial queries must be named templates.
* Both polygon AOI analysis and corridor segment analysis share the same need.
* SDA provides T-SQL spatial functions (`STIntersection`, `STArea`) via the
  `GEOGRAPHY` type that can clip and measure server-side.

## Considered Options

1. **SDA server-side polygon clipping with geodesic area** — pass AOI WKT to
   SDA, use `STIntersection` to clip soil polygons to the AOI boundary, compute
   exact clipped acreage via `GEOGRAPHY.STArea()`, and return per-map-unit
   results with precise acreages.
2. **Multi-point sampling within polygons** — generate a grid of sample points,
   query SDA for the map unit at each point, estimate acreage fractions by
   sample density.
3. **Client-side intersection with downloaded SSURGO shapefiles** — download
   soil survey boundaries locally and compute intersections with `shapely`.

## Decision Outcome

Chosen option: **SDA server-side polygon clipping**, because it produces exact
clipped acreages without approximation, keeps spatial computation on the SDA
server (avoiding large data downloads), and integrates cleanly with the fixed
SQL template architecture via the `SQL_SPATIAL_INTERSECTION_CLIPPED` template.

### Consequences

* **Positive**: Both `polygon_analysis.py` and `corridor_analysis.py` call
  `sda_client.get_spatial_intersection(wkt, clip=True, geom_acres=True)`,
  producing exact clipped acreages per map unit via `GEOGRAPHY.STArea()`.
* **Positive**: No sampling resolution trade-offs — acreage is exact within
  SDA's geodesic precision, not an estimate from point density.
* **Positive**: Acreage-weighted aggregation from clipped results directly feeds
  the Land Evaluation relative rating calculation (EP17, ADR-0007/0008).
* **Positive**: The fixed SQL template `SQL_SPATIAL_INTERSECTION_CLIPPED`
  maintains the no-passthrough policy (ADR-0002).
* **Negative**: Complex AOI polygons with many vertices may produce large WKT
  strings that approach SDA query size limits or slow server-side computation.
* **Negative**: Server-side clipping depends on SDA availability and response
  time; mitigated by the resilient HTTP client (ADR-0009).

## Validation & Compliance

50-fixture benchmark corpus (EP4) verified total geometry acreage within 0.1%
tolerance. Extended to corridor segments in EP7. Evidence:
`polygon_analysis.py:153` and `corridor_analysis.py:359` both call
`get_spatial_intersection(clip=True, geom_acres=True)`. SDA template:
`sda_client.py` `SQL_SPATIAL_INTERSECTION_CLIPPED`.
