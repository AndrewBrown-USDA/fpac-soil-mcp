---
id: "0019"
title: "Shared Soil Mapping and Rating Coverage Vocabularies"
status: "Accepted"
date: "2026-11-18"
authors:
  - "Andrew G. Brown"
supersedes: null
superseded_by: null
source_context: "EXECUTION_PLAN_58"
---

# 19. Shared Soil Mapping and Rating Coverage Vocabularies

## Context and Problem Statement

Issue #84: each producer of a `coverage_status` field used its own words.
Soil mapping coverage used `covered`, `partially_covered`, `unmapped`,
`no_data`, and `invalid_request`. Rating coverage used `covered`, `rated`,
`partial`, `unrated`, `no_coverage`, `not_found`, and `unknown`. Most fields
were plain strings, so the MCP output schemas did not list the allowed values.

Worse, a failed SDA query was reported as missing data. During an SDA outage
a polygon or corridor screen reported `unmapped` and `unrated`, with only a
limitation line to show the query had failed. A corridor rating failure added
no limitation at all. A reader could take an outage for land with no soil
survey.

## Decision Drivers

* A failed query must never look like missing or unrated soil.
* One value set per meaning, shared by every tool, so clients can rely on it.
* Output schemas must publish the allowed values.
* Keep field names, so existing clients only need to change values.

## Considered Options

1. **Keep per-tool strings and document them** — no client change, but the
   outage misreport stays and the schemas stay untyped.
2. **One vocabulary for all coverage fields** — simple, but mixes two
   different questions (is the soil mapped? is it rated?) that can disagree.
3. **Two shared vocabularies, each with an explicit `error` value** — one for
   soil mapping, one for rating coverage.

## Decision Outcome

Chosen option: **Two shared vocabularies with an explicit `error` value**,
defined once in `src/fpac_soil_mcp/models/coverage.py` as `Literal` types with
matching constants:

| Vocabulary | Values | Used by |
| --- | --- | --- |
| `SoilMappingCoverage` | `covered`, `partial`, `unmapped`, `error` | point and mukey lookup, polygon AOI, corridor county segment |
| `RatingCoverage` | `rated`, `partial`, `unrated`, `unmapped`, `unknown`, `error` | map unit productivity and NCCPI baseline coverage, corridor segment and reconciliation, Land Evaluation |

Rules:

* `error` means a query failed or the input was invalid. A failed query is
  never reported as `unmapped`, `unrated`, or `unknown`.
* If the soil (spatial) query fails, both mapping and rating coverage are
  `error`. If only the rating query fails, mapping coverage is computed as
  usual and rating coverage is `error`. A failed county maximum query adds a
  limitation only.
* A corridor reconciliation is `error` if any county segment query failed;
  each segment keeps its own status. A corridor rating failure now adds a
  limitation line.
* A failed NCCPI national baseline query gives each map unit baseline coverage
  `error`. A map unit with no SDA row keeps a null baseline.
* Polygon map units now carry their productivity rating coverage from the
  rating row.
* Values are renamed outright, with no aliases, and ship in 0.6.0. Field
  names do not change. Renames: mapping `partially_covered` -> `partial`,
  `no_data` and `invalid_request` -> `error`; rating `covered` -> `rated`,
  `no_coverage` -> `unrated`, `not_found` -> `unknown`.
* SDV caveat and reason keys (`no_coverage`, `not_found`) are unchanged; only
  the status values derived from them change.

## Consequences

* **Positive**: An SDA outage reads as `error`, not as unmapped or unrated land.
* **Positive**: Every public coverage field is typed, and the tool output
  schemas list the exact allowed values.
* **Positive**: The typed fields reject any other value when a response is
  built, so a producer cannot emit an unlisted value unnoticed.
* **Negative**: Breaking change for clients that match on the old values.
* **Negative**: `analyze_corridor_fppa` returns a plain dict, so its MCP output
  schema stays untyped; the corridor values are checked on the response model
  instead.

## Deferred

* A structured error field on polygon and corridor responses (only the point
  and mukey lookups have one); failures are described in `limitations`.
* Typed or explicit output schemas for `analyze_corridor_fppa`, and moving map
  geometry into the MCP result `_meta`. That follow-on plan's explicit output
  schemas must keep these enums.

## Validation & Compliance

Decision established in EXECUTION_PLAN_58. Tests check the exact value sets,
that every public model rejects retired values, that failed spatial, rating,
and NCCPI baseline queries report `error`, and that the tool output schemas
list the enums.
