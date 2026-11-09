---
id: "0017"
title: "Server Map Result Contract for the Analyze Tools"
status: "Proposed"
date: 2026-11-04
authors:
  - "Andrew G. Brown"
supersedes: null
superseded_by: null
source_context: "EXECUTION_PLAN_44"
---

# 17. Server Map Result Contract for the Analyze Tools

## Context and Problem Statement

The agent app map panel (ADR 0016) draws a screened AOI with soil polygons from
a second tool, `get_soil_polygons_by_geometry`, and colours them with a legend
held in the frontend (`farmlandClasses.ts`). Chat tool cards show the JSON the
analyze tools return, but nothing in that JSON can be drawn: the tools compute
farmland fragments, urban areas, corridor footprints and county segments, then
drop the geometry. `planning/SPATIAL_VISUALIZATION_STRATEGY.md` section 4
describes a structured visualization envelope (Phase 8, Track A M3). Plan 44
adds a map result to the two analyze tools so the map panel and a
"Show on map" action on tool cards can draw what the server computed, with
server legends, sources and the regulatory notice.

Two limits apply. Model context: the model calls these tools, and inline
GeoJSON for a county-sized AOI can be megabytes. Compatibility: the app
(`geo.py` `select_display_analysis`, `build_chat_summary`), the eval cases and
LESA's use of the corridor result read the current response fields.

## Decision Drivers

* The default tool response the model sees must stay about as small as today
  and carry no coordinates.
* Numbers (acreage, percentages, LE/SA inputs, `geometry_hash`, `tabular_csv`)
  must come from exact geometry, whatever the map shows (ADR 0004).
* No extra SDA or TIGERweb queries: the geometry is already fetched or
  computed.
* The MCP server stays stateless; the app stays a separate MCP client with no
  wrapper tools (ADR 0012).
* Existing response fields keep their names and shapes.
* Every rendered result keeps the server `regulatory_notice` and a
  machine-estimate authority label (ADR 0003).
* Map symbology must not rely on colour alone (strategy section 5).

## Considered Options

Geometry delivery:

1. **Always inline GeoJSON:** simplest, but every model call pays for the
   geometry in context.
2. **Opt-in flag on the analyze tools:** `include_map=False` by default returns
   layer descriptors only; the app calls the tool again with
   `include_map=True` when it needs geometry.
3. **Server-side result store with a handle:** needs shared state across
   workers and a retention policy.
4. **Separate map tool:** duplicates the analysis inputs and adds tool surface
   the model may call by mistake.

Contract shape:

1. **Full section 4 envelope:** restructure responses into `analysis_id`,
   `status`, `summary`, `metrics`, `provenance`, `privacy`. Breaks every
   current consumer.
2. **Additive fields:** add `schema_version`, `data_mode`, `authority` and
   `map`; map the rest of section 4 onto fields that already exist.

## Decision Outcome

Chosen: opt-in flag (delivery option 2) with additive fields (shape option 2),
because the model context stays small, the server stays stateless and no
current consumer changes.

### Tools and flag

* `analyze_farmland_by_polygon` and `analyze_corridor_fppa` take
  `include_map: bool = False`. Their docstrings tell the model to leave it
  false.
* `get_soil_polygons_by_geometry` takes the same flag (Plan 44 A6), so its
  tool cards (eval case POLY-02) get "Show on map". Its FeatureCollection keys
  are unchanged; it gains the same additive keys with an `aoi` and a
  `farmland_classes` layer built from the rows it already fetches. When
  `clip=False` the `farmland_classes` title says the polygons are full survey
  polygons.
* `calculate_preliminary_lesa`, `get_farmland_classification_by_point`,
  `get_farmland_classification_by_mukey` and every other tool are unchanged.
* With `include_map=True` the existing SDA intersection calls request
  geometry (`return_geom=True`) and the urban check returns the urban-area
  geometries it already fetches. No other upstream call is added.
* The app routes that draw results (`/api/geo/screen`, `/api/geo/map`) call
  the tool with `include_map=True`. The map panel stops calling
  `get_soil_polygons_by_geometry`.

### Additive top-level fields

Both response models gain these fields, with defaults so existing
constructors validate; the `get_soil_polygons_by_geometry` FeatureCollection
gains the same keys:

| Field | Value |
|---|---|
| `schema_version` | `"1.0"` |
| `data_mode` | `"live"` (the server has no mock mode; tests mock HTTP) |
| `authority` | `{level: "machine_estimate", label: "Preliminary Machine Estimate", official_filing: false}` |
| `map` | map block below; present in every response, including error paths |

### Map block

| Field | Meaning |
|---|---|
| `display_crs` | `"EPSG:4326"` |
| `bounds` | `[min_lon, min_lat, max_lon, max_lat]` of the inline layers; `null` when no layer is inline, so the default response has no coordinates |
| `layers` | ordered list, drawn bottom to top |
| `warnings` | display warnings (simplification, truncation); empty by default |

### Layer schema

| Field | Type | Meaning |
|---|---|---|
| `id` | string | stable id (below) |
| `title` | string | display title |
| `kind` | `polygon` / `line` / `point` | geometry kind |
| `delivery` | `inline_geojson` / `omitted` | `omitted` when `include_map=False` or the layer was dropped by the size cap |
| `authority` | `user_input` / `machine_estimate` / `reference_data` | the AOI is user input; derived layers are machine estimates; Census boundaries are reference data |
| `source` | string | service name, e.g. `USDA NRCS Soil Data Access (SDA)` |
| `data_vintage` | string or null | e.g. `Census 2020 Urban Areas`; null when unknown without an extra query (SSURGO) |
| `style_key` | string or null | feature property the legend `value` matches (e.g. `farmland_class`) |
| `legend` | list of `{value, label, color, pattern, code}` | server-owned symbology |
| `simplified` | bool | display copy was simplified |
| `simplify_tolerance_m` | number or null | tolerance used |
| `truncated` | bool | features dropped by the size cap |
| `feature_count` | int or null | features in `feature_collection`; null when omitted |
| `feature_collection` | GeoJSON FeatureCollection or null | null when `delivery` is `omitted` |

Layer ids:

| Id | Tool | Content |
|---|---|---|
| `aoi` | polygon | the screened AOI |
| `farmland_classes` | both | soil map-unit fragments clipped to the AOI or direct footprint; properties `mukey`, `musym`, `muname`, `farmlndcl`, `farmland_class`, `area_ac`; from the analyze tools also `productivity_rating`, `productivity_rating_class`, `productivity_rating_source` when ratings were fetched, copied from the ratings already queried (Plan 44 A7, for the map popup) |
| `urban_context` | both | Census 2020 urban areas that intersect the input; property `name` |
| `corridor_direct` | corridor | direct right-of-way footprint |
| `corridor_indirect` | corridor | indirect area, when present |
| `corridor_alternative_<id>` | corridor | one per alternative |
| `county_segments` | corridor | footprint per county; properties county name and GEOID |

### Legends

The server owns legend values, colours, patterns and text codes; the frontend
draws what it receives. `farmland_classes` uses the values
`categorize_farmland_class` returns:

| Value | Code | Colour | Pattern | Source |
|---|---|---|---|---|
| `prime` | P | `#2E7D32` | solid | strategy section 5 |
| `conditional_prime` | P* | `#81C784` | diagonal_hatch | deployed map (`farmlandClasses.ts`) |
| `statewide` | S | `#F9A825` | diagonal_hatch | strategy section 5 |
| `unique` | U | `#6A1B9A` | cross_hatch | strategy section 5 |
| `local` | L | `#0288D1` | dot_stipple | strategy section 5 |
| `not_prime` | NP | `#9E9E9E` | outline | strategy section 5 |
| `unmapped` | UM | `#FFFFFF` | diagonal_hatch | deployed map (`farmlandClasses.ts`) |

Other layers: `urban_context` `#5C6BC0` dashed outline; `corridor_direct`
`#E53935` solid outline; alternatives start at `#1E88E5` dashed outline;
`aoi`, `corridor_indirect` and `county_segments` use neutral outlines. A
renderer that cannot draw a pattern may fill solid, but must show the `code`.

### Display geometry and size cap

* Numbers always use exact geometry. Only the `map` copy is changed.
* Display copies are simplified with topology preserved at
  `map_simplify_tolerance_m` (default 1.0 m) in EPSG:6933, then projected back
  to EPSG:4326; each layer records `simplified` and `simplify_tolerance_m`.
* `map_max_geojson_bytes` (default 2,000,000) caps the serialized layers.
  Over the cap, whole layers are dropped from the end of the list until the
  block fits: the layer gets `delivery: "omitted"`, `truncated: true`, and a
  warning names it. A layer is never partly drawn, because missing fragments
  would look like missing farmland.

### Mapping to strategy section 4

| Section 4 field | This contract |
|---|---|
| `schema_version` | new `schema_version` |
| `analysis_id` | not provided: stateless; `geometry_hash` and the manifest timestamp identify a run |
| `analysis_type` | existing `query_type` |
| `status` | not provided: existing `coverage_status` and existing error responses |
| `data_mode` | new `data_mode` |
| `source_status` | not provided: services that fail raise errors; `source` and `manifest` list services used |
| `authority` | new `authority` |
| `summary` | existing `farmland_summary` (polygon); `impact_breakdown`, `reconciliation_summary` (corridor) |
| `metrics` | existing `map_units` (polygon); `county_segments`, `alternatives` (corridor) |
| `map` | new `map` |
| `provenance.analysis_timestamp` | existing `source.timestamp_utc` |
| `provenance.rule_version` | existing `manifest` (rules and parameters) |
| `provenance.sources` | existing `source` and `manifest`, plus layer `source` and `data_vintage` |
| `provenance.calculation_crs` | not provided: ADR 0004 fixes EPSG:6933; `map.display_crs` gives the display CRS |
| `privacy` | not provided: geometry is operational data, no redaction (ADR 0010, 0016) |
| `warnings` | existing `limitations` plus `map.warnings` |
| `disclaimer` | existing `regulatory_notice` |

### Consequences

* **Positive:** tool cards and the map panel draw what the server computed;
  legends and notices come from one place; model context is unchanged apart
  from a small descriptor block; no consumer breaks.
* **Negative:** "Show on map" and screening make a second tool call with
  `include_map=True`, so SDA and TIGERweb are queried again and the drawing
  can reflect data newer than the chat result. The map shows the numbers from
  its own call.
* **Negative:** the frontend legend (`farmlandClasses.ts`) gives way to the
  server legend; colour changes now need a server deploy.
* The Phase 8 M3 "soil" exit item is met by the `farmland_classes` layer,
  which `get_soil_polygons_by_geometry` also returns; that tool keeps its
  current FeatureCollection, so a soil-polygon result with `include_map=True`
  carries the geometry twice. Only the app's map route asks for that.

### Scope boundary

Out of scope: `map` on tools other than the three above; the full section 4
envelope; a server overlay catalog; simplifying overlay outlines for use as an
AOI.

## Validation & Compliance

* Contract tests through the MCP tool layer: descriptor-only by default,
  inline layers when requested, default response size within a small margin
  of the pre-change size, and the section 4 mapping asserted field by field.
* Analyzer tests: identical acreage, summaries, `geometry_hash` and
  `tabular_csv` for both flag values; one SDA and one urban call per run.
* Tests use synthetic geometry only.
