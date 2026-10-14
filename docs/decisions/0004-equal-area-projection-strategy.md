---
id: "0004"
title: "Equal-Area Projection Strategy (EPSG:6933 / Local CRS)"
status: "Accepted"
date: 2026-09-17
authors:
  - "Andrew G. Brown"
supersedes: null
superseded_by: null
source_context: "EXECUTION_PLAN_4"
---

# 4. Equal-Area Projection Strategy (EPSG:6933 / Local CRS)

## Context and Problem Statement

FPPA screening requires calculating farmland acreage from WGS84 coordinate
geometries. Naive area calculations on geographic coordinates produce
systematically wrong results. The system needed a projection strategy that works
for CONUS, Alaska, and Hawaii sites while maintaining <0.1% acreage tolerance
against reviewed benchmark fixtures.

## Decision Drivers

* Accuracy: FPPA acreage calculations feed into Land Evaluation scores and
  Site Assessment criterion scoring; errors propagate into regulatory outputs.
* Coverage: Must handle CONUS, Alaska, Hawaii, and cross-state corridors.
* Reproducibility: Projection must be deterministic for test fixture benchmarking.
* Dependencies: `shapely` and `pyproj` were already in scope for geometry
  validation (GeoJSON parsing, WKT generation, ring closure, self-intersection
  checks).

## Considered Options

1. **EPSG:6933 (Cylindrical Equal Area) as primary, with local CRS fallback** —
   use a global equal-area projection for all acreage calculations, supplemented
   by local UTM/Albers projections where higher accuracy is needed.
2. **Albers Equal Area (EPSG:5070) for CONUS only** — standard USGS projection
   but does not cover Alaska/Hawaii without projection switches.
3. **Geodesic area via `pyproj.Geod`** — compute ellipsoidal area directly
   without projecting, avoiding projection distortion entirely.

## Decision Outcome

Chosen option: **EPSG:6933 as primary**, because it provides consistent global
coverage with acceptable accuracy for the <0.1% tolerance benchmark. `shapely`
and `pyproj` handle the coordinate transformations, and the same projection
serves point queries, polygon AOI analysis, and corridor buffering.

### Consequences

* **Positive**: The 0.1% acreage tolerance benchmark was established in EP4
  with 50 test fixtures and held through corridor analysis (EP7) and LESA
  scoring (EP17) without changing the projection strategy.
* **Positive**: Corridor geodesic buffering (EP7) reuses the same projection
  pipeline — `buffer_distance` in feet/meters/miles is converted to projection
  units before `shapely.buffer()`.
* **Negative**: EPSG:6933 introduces higher distortion at extreme latitudes
  (Alaska), but this is within the 0.1% tolerance for the test corpus.
* **Negative**: Two projection libraries (`shapely`, `pyproj`) add to the
  dependency footprint, but both are standard geospatial Python packages.

## Validation & Compliance

50 synthetic and real-world GeoJSON fixtures (CONUS, Alaska, Hawaii,
urban-fringe, multi-unit complexes) verified offline within 0.1% acreage
tolerance. Decision established in EXECUTION_PLAN_4 (2026-09-17), extended
in EXECUTION_PLAN_7 (corridor buffering, 2026-09-18). Commits: `a3eb38dc`,
`b8613a26`.
