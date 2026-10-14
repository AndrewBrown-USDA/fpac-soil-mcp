---
id: "0004"
title: "Geodesic Acreage Calculation & Equal-Area Buffering Strategy"
status: "Accepted"
date: 2026-09-17
authors:
  - "Andrew G. Brown"
supersedes: null
superseded_by: null
source_context: "EXECUTION_PLAN_4, EXECUTION_PLAN_7"
---

# 4. Geodesic Acreage Calculation & Equal-Area Buffering Strategy

## Context and Problem Statement

FPPA screening requires calculating farmland acreage from WGS84 coordinate
geometries in two contexts: client-side total AOI acreage and server-side
clipped map-unit acreage from SDA. Naive area calculations on geographic
coordinates produce systematically wrong results. Separately, corridor
analysis requires buffering centerlines by a specified distance, which needs
an equal-area projection. The system needed a strategy that works for CONUS,
Alaska, and Hawaii sites while maintaining <0.1% acreage tolerance.

## Decision Drivers

* Accuracy: FPPA acreage calculations feed into Land Evaluation scores and
  Site Assessment criterion scoring; errors propagate into regulatory outputs.
* Coverage: Must handle CONUS, Alaska, Hawaii, and cross-state corridors.
* Dual context: Client-side geometry acreage and server-side SDA clipped acreage
  use different computation paths but must agree within tolerance.
* Corridor buffering requires a projected coordinate system; geodesic area does
  not.

## Considered Options

1. **WGS84 geodesic area for acreage, EPSG:6933 for corridor buffering** —
   use `pyproj.Geod.polygon_area_perimeter()` on WGS84 coordinates for
   client-side acreage, SDA `GEOGRAPHY.STArea()` for server-side clipped
   acreage, and EPSG:6933 (Cylindrical Equal Area) projection space solely
   for corridor centerline buffering.
2. **EPSG:6933 for all area and buffering** — project to equal-area for both
   acreage calculation and corridor buffering.
3. **Albers Equal Area (EPSG:5070) for CONUS only** — standard USGS projection
   but does not cover Alaska/Hawaii without projection switches.

## Decision Outcome

Chosen option: **WGS84 geodesic area for acreage, EPSG:6933 for corridor
buffering**, because geodesic ellipsoidal area avoids projection distortion
entirely for acreage, while EPSG:6933 provides the projected coordinate space
needed for distance-based buffer operations on corridors.

### Consequences

* **Positive**: `geometry.calculate_acreage()` uses `Geod.polygon_area_perimeter()`
  directly on WGS84 coordinates, avoiding any projection distortion for area
  measurement. This is the most accurate approach for global coverage.
* **Positive**: SDA server-side clipped acreage uses `GEOGRAPHY.STArea()`,
  which also computes geodesic area on the WGS84 ellipsoid, ensuring agreement
  between client-side and server-side area calculations.
* **Positive**: Corridor buffering (`geometry.buffer_centerline()`) projects to
  EPSG:6933 for distance-based buffer generation, then reprojects back to WGS84.
  This cleanly separates the buffering concern from the acreage concern.
* **Positive**: The 0.1% acreage tolerance benchmark established in EP4 held
  through corridor analysis (EP7) and LESA scoring (EP17).
* **Negative**: Two `pyproj` code paths (geodesic area vs. projected buffering)
  require understanding when each applies. Mitigated by clear function names
  and docstrings.

## Validation & Compliance

50 synthetic and real-world GeoJSON fixtures (CONUS, Alaska, Hawaii,
urban-fringe, multi-unit complexes) verified offline within 0.1% acreage
tolerance. Decision established in EXECUTION_PLAN_4 (2026-09-17), extended
in EXECUTION_PLAN_7 (corridor buffering, 2026-09-18). Commits: `a3eb38dc`,
`b8613a26`.
