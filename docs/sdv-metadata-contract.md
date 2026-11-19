# SDV Metadata Rating Contract

This document is the field-level contract for productivity and property ratings
built from Soil Data Viewer (SDV) `sdvattribute` metadata. The decision record is
[ADR 0014](decisions/0014-registry-validated-sdv-metadata-contract.md); the code
lives in `src/fpac_soil_mcp/sda_client.py` (`SDV_RATING_REGISTRY` and the
per-strategy builders). Registry version: `SDV_REGISTRY_VERSION = "1"`.

Exit criterion this contract satisfies: a validated metadata record
deterministically produces the correct SDA query, aggregation behavior,
provenance, and caveats. `tests/fixtures/sdv_contract_cases.json` pins all four
for every registry record.

## Purpose and scope

- The contract is internal to `sda_client.py`. Public MCP tools still accept
  only the four fixed selectors `nccpi`, `csr2`, `cpi`, and `storie`; no public
  tool parameter, `manifest.yaml`, or `server.json` entry exposes metadata
  selection.
- Only the six records in the registry can be rated. Any other `sdvattribute`
  record is rejected before a query is built.
- Selecting public properties from a broader validated list is a possible
  future item, not part of this contract.

## Required `sdvattribute` fields

`SDV_CONTRACT_FIELDS` lists the 22 fields that `lookup_sdv_attribute` returns
(`SQL_SDV_ATTRIBUTE_LOOKUP`) and that a metadata record may carry. "Gate 1" and
"Gate 2" refer to the validation steps below. Fields marked "recorded" are not
read from the caller's record; the engine uses the registry value instead.

| Field | Meaning | Engine use |
|---|---|---|
| `attributekey` | SDV attribute key | Recorded only |
| `attributename` | SDV attribute display name | Gate 1 match key (case-insensitive) |
| `attributetablename` | SSURGO source table | Gate 1 match key; Gate 2 identifier pattern and strategy-table check |
| `attributecolumnname` | SSURGO source column | Gate 1 match key; Gate 2 identifier pattern |
| `attributelogicaldatatype` | Logical type (Float, Integer, ...) | Recorded only |
| `nasisrulename` | NASIS interpretation rule (cointerp only; empty otherwise) | Gate 1 match key; filters `cointerp.mrulename` |
| `ruledesign` | Interpretation rule design | Recorded only |
| `algorithmname` | SDV aggregation method across components | Gate 2: must be supported and equal the registry value; selects the strategy |
| `horzaggmeth` | Aggregation method across horizons | Gate 2 for `chorizon`: must be supported and equal the registry value |
| `tiebreakrule` | Tie direction for Dominant Condition (`1` higher wins, `-1` lower wins) | Gate 2: when present, must equal the registry value |
| `depthqualifiermode` | Depth selection mode (`Depth Range` for AWS) | Recorded; depth is pinned in the registry |
| `layerdepthtotop` | Top of depth range | Recorded; registry pins 0 cm for AWS |
| `layerdepthtobottom` | Bottom of depth range | Recorded; registry pins 100 cm for AWS |
| `layerdepthuom` | Depth unit | Recorded only |
| `interpnullsaszeroflag` | SDV "treat nulls as zero" flag | Recorded as `nulls_as_zero`; applied to `component` (CPI) and `cocropyld` (see null handling) |
| `nullratingreplacementvalue` | SDV replacement for null ratings | Recorded only |
| `primaryconcolname` | Primary constraint column (`cropname` for crop yields) | Recorded; the registry declares `cropname` as a required constraint |
| `secondaryconcolname` | Secondary constraint column (`yldunits` for crop yields) | Recorded; units are checked per map unit |
| `componentpercentcutoff` | Minimum component percent | Recorded only (null for all registry records) |
| `resultcolumnname` | SDV result column name | Recorded only |
| `notratedphrase` | SDV "not rated" label | Recorded only |
| `attributetype` | SDV attribute type | Recorded only |

For `cointerp` records SDV names the class column `interphrc`. Numeric ratings
come from `interphr`; the registry stores this as `value_column`.

## Selection: fixed selectors and explicit metadata

Both paths end in one registry spec (`SdvRatingSpec`) and then run the same
builders, aggregation, provenance, and caveat code (one engine).

- **Fixed selector.** `get_productivity_ratings(index_type=...)` and
  `get_county_max_productivity_rating(index_type=...)` normalize the selector
  by exact alias (`_normalize_productivity_index`). Only `nccpi`, `csr2`,
  `cpi`, and `storie` (and their registry aliases) are accepted here.
- **Explicit metadata.** Pass an `sdvattribute` record as `attribute_meta`.
  It takes precedence over `index_type` and is validated with both gates. A
  typical caller first fetches the record with `lookup_sdv_attribute`. This
  path can reach all six registry records, including AWS and crop yields.

`_resolve_productivity_spec` performs this routing. `resolve_sdv_spec` accepts
exactly one of `selector` or `record`.

## Validation

`validate_sdv_record` runs two gates.

1. **Registry match.** `attributename`, `attributetablename`,
   `attributecolumnname`, and `nasisrulename` must equal one registry entry
   (trimmed, case-insensitive). Otherwise:
   `Unregistered SDV record: attributename='...', table='...', column='...', rule='...'.`
2. **Structural validation** against the matched entry:
   - `algorithmname` not in `SUPPORTED_SDV_ALGORITHMS`:
     `Unsupported aggregation method: '...'. Supported: [...]`
   - `algorithmname` differs from the registry:
     `Malformed SDV record: algorithmname '...' does not match registry value '...' for <spec_id>.`
   - table not a strategy table:
     `Malformed SDV record: table '...' is not a supported strategy table.`
   - table or column not an identifier:
     `Malformed SDV record: <field> '...' does not match identifier pattern.`
   - `chorizon` `horzaggmeth` unsupported or different:
     `Unsupported horizon method: '...'` or
     `Malformed SDV record: horzaggmeth '...' does not match registry value '...'.`
   - `tiebreakrule` not an integer or different:
     `Malformed SDV record: tiebreakrule '...' is not an integer.` or
     `Malformed SDV record: tiebreakrule ... does not match registry value ....`

Selector errors: `Unsupported productivity index type '...'` (client entry
points) and `Unregistered SDV selector: '...'.` (`resolve_sdv_spec`). All errors
are `SDAValidationError` and are raised before any SQL is built or sent.

## Passing into the engine

- `resolve_sdv_spec(selector=None, record=None, constraints=None)` returns
  `(spec, resolved_constraints)`.
- Constraints are a mapping. The only constraint used today is `cropname`,
  required by `nonirr_crop_yield`. It is validated (non-empty, no `;` or `--`,
  1-80 characters from letters, digits, space and `,()-/'.`) and matched exactly
  against `cocropyld.cropname`. There is no default crop. Missing crop:
  `Constraint 'cropname' is required for nonirr_crop_yield.`
- For backward compatibility a `cropname` key on the `attribute_meta` record is
  merged into the constraints; an explicit `constraints` value wins.
- `build_sdv_rating_query(spec, mukeys, constraints)` and
  `build_sdv_county_max_query(spec, areasymbol, constraints)` dispatch on
  `(table, algorithm)`. `build_dynamic_sdv_query` and
  `build_dynamic_sdv_county_max_query` are thin wrappers that validate a record
  first. All builders are fixed templates; only validated map unit keys, area
  symbols, registry values, and the validated crop name are interpolated
  (ADR 0002).

## Per-table behavior

All strategies exclude components with `compkind = 'miscellaneous area'` and
weight by `comppct_r`. `rated_pct` is the summed percent of components that have
a usable value; `total_pct` is the summed percent of all non-miscellaneous
components considered.

| Table | Method | Value | Weighting and aggregation | Sentinels | Nulls | Depth | Constraints |
|---|---|---|---|---|---|---|---|
| `cointerp` | Weighted Average (NCCPI) | `cointerp.interphr`, rule filter, `ruledepth = 0` | Sum of rating x pct over rated pct; rounded to precision in SQL | Excluded in SQL (99, 999, -99, -999) | Excluded | n/a | none |
| `cointerp` | Dominant Condition (Storie) | `cointerp.interphr` rounded to precision is the condition class | Sum pct per class; largest wins; ties by `tiebreakrule` (-1 lower, 1 higher). Returns `dominant_pct` (winning class percent) | Excluded in SQL | Excluded; map units with no rated component return a row with NULL rating | n/a | none |
| `component` | Weighted Average (CPI) | `component.cropprodindex` | Sum of value x pct over all non-miscellaneous pct | Screened in the engine (999, -99, -999); `99` stays rated | Count as 0 when the map unit has at least one rated component; a map unit with none stays unrated (see null handling) | n/a | none |
| `mapunit` | No Aggregation Necessary (CSR2) | `mapunit.iacornsr` | Map unit value as is; `rated_pct` 100 when non-null, `total_pct` 100 | Screened in the engine (999, -99, -999); `99` stays rated | NULL means unrated | n/a | none |
| `chorizon` | Weighted Average + horizon Weighted Sum (AWS) | `chorizon.awc_r` | Per component: sum of awc_r x horizon thickness clipped to the depth range (cm); then pct-weighted average across components | none | Horizons with NULL `awc_r` excluded | Fixed 0-100 cm (registry; not caller-selectable) | none |
| `cocropyld` | Weighted Average (crop yields) | `cocropyld.nonirryield_r` | Sum of yield x pct over pct of components with the crop | none | NULL yield counts as 0 (nulls-as-zero) | n/a | `cropname` required; one `yldunits` per map unit |

Engine post-processing (all strategies): a value equal to a registry sentinel or
`<= 0` is unrated with the `unrated_sentinel` caveat; a positive value with
`rated_pct <= 0` is unrated (`no_coverage`); otherwise the value is rounded to the
registry precision. County maximums use the same strategy, ignore unrated values,
and return `None` for sentinel or non-positive results. For Dominant Condition
the county maximum is the largest per-map-unit dominant class.

**Null handling.** SDV publishes `interpnullsaszeroflag = 1` (with no
`nullratingreplacementvalue`, so the replacement is 0) for CPI and crop yields,
and the engine applies it to both. For CPI, a null-rated component counts as 0
in the weighted average only when the map unit has at least one rated
component; a map unit whose components are all null stays unrated, so counties
where CPI is not populated (for example MN053) are reported as unrated rather
than as CPI 0. `rated_pct` is still the percent of components with a value, so
the partial-rating caveat still appears. Miscellaneous areas stay excluded. The
provenance record shows both: `nulls_as_zero` echoes the SDV flag and
`null_handling` (`nulls_as_zero` or `exclude_nulls`) shows what the engine did.

## Provenance

Every result carries a stable ID in the public `productivity_rating_source`
field and an internal structured record in `sdv_provenance`. The structured
record is not part of any public schema.

| Spec | Provenance ID |
|---|---|
| `nccpi` | `SDA:NCCPI_V3` |
| `storie` | `SDA:COINTERP_STORIE_CA` |
| `csr2` | `SDA:MAPUNIT_IACORNSR` |
| `cpi` | `SDA:COMPONENT_CROPPRODINDEX` |
| `aws_0_100` | `SDA:CHORIZON_AWC_R_0_100` |
| `nonirr_crop_yield` | `SDA:COCROPYLD_NONIRRYIELD_R` |

`sdv_provenance` fields: `id`, `registry_version`, `spec_id`, `attributename`,
`table`, `column`, `value_column`, `rule_name`, `algorithm`, `horizon_method`,
`depth_top_cm`, `depth_bottom_cm`, `tiebreak_rule`, `nulls_as_zero`,
`null_handling`, `scale`, `precision`. Crop yield records add `cropname` and the
per-map-unit `yldunits` (`None` when units are mixed). Result rows also carry
`spec_id`, `algorithm`, `table`, `rule_name`, and `value_column`.

`PRODUCTIVITY_PROVENANCE` and `PRODUCTIVITY_SEMANTICS` are derived from the
registry for the four public selectors; `corridor_analysis.py` reads its
fallback sources and sentinels from them.

## Caveats catalog

Caveat text comes only from `SDV_CAVEATS`. Order per row: rating status
(`unrated_sentinel`, `no_coverage`, `unparseable`, or `no_rating`), then
`partial_rating`, `mixed_units`, `dominant_condition`, `aws_fixed_depth`,
`crop_specific`. Map units missing from the SDA result get only `not_found`.
Caveat keys are reason codes, not coverage values: a row with reason `no_coverage`
has `coverage_status` `unrated`, and a `not_found` map unit has `coverage_status`
`unknown` (vocabulary in
[`models/coverage.py`](../src/fpac_soil_mcp/models/coverage.py)).

| Key | Text |
|---|---|
| `unrated_sentinel` | Map unit contains unrated placeholder/sentinel code ({value}). |
| `no_coverage` | Map unit has 0% rated component coverage. |
| `unparseable` | Unparseable rating value '{value}'. |
| `no_rating` | Map unit has no numeric productivity rating. |
| `partial_rating` | Partially rated map unit: {rated}% rated out of {total}% total component coverage. |
| `mixed_units` | Mixed yield units: {min_unit} and {max_unit}. |
| `dominant_condition` | Rating uses Dominant Condition aggregation. |
| `aws_fixed_depth` | Available water storage computed for fixed depth range 0-100 cm. |
| `crop_specific` | Crop-specific yield for '{crop}'. |
| `not_found` | Map unit not found in SDA query results. |

`partial_rating` is added only for rated rows with `rated_pct < total_pct`. A
map unit with more than one `yldunits` value for the crop is unrated with
`mixed_units`.

## Registry entries

| Spec | `attributename` | Table.column (value column) | Rule | Algorithm / horizon | Tiebreak | Scale, precision | Sentinels | Constraints |
|---|---|---|---|---|---|---|---|---|
| `nccpi` | National Commodity Crop Productivity Index | `cointerp.interphrc` (`interphr`) | NCCPI - National Commodity Crop Productivity Index (Ver 3.0) | Weighted Average | 1 | 0-1, 3 | 99, 999, -99, -999 | none |
| `storie` | California Revised Storie Index (CA) | `cointerp.interphrc` (`interphr`) | AGR - California Revised Storie Index (CA) | Dominant Condition | -1 | 0-1, 3 | 99, 999, -99, -999 | none |
| `csr2` | Iowa Corn Suitability Rating CSR2 (IA) | `mapunit.iacornsr` | none | No Aggregation Necessary | 1 | 5-100, 0 | 999, -99, -999 | none |
| `cpi` | Crop Productivity Index | `component.cropprodindex` | none | Weighted Average | 1 | 1-100, 0 | 999, -99, -999 | none |
| `aws_0_100` | Available Water Storage | `chorizon.awc_r` | none | Weighted Average / Weighted Sum, 0-100 cm | 1 | 0-100 cm, 3 | none | none |
| `nonirr_crop_yield` | Yields of Non-Irrigated Crops (Component) | `cocropyld.nonirryield_r` | none | Weighted Average, nulls-as-zero | 1 | varies, 2 | none | `cropname` |

Only `nccpi`, `storie`, `csr2`, and `cpi` have public selector aliases. Captured
live records: `tests/fixtures/sdv_attribute_records.json`.

## Adding a record

1. Live-capture the `sdvattribute` record with `lookup_sdv_attribute` and add
   it to `tests/fixtures/sdv_attribute_records.json`.
2. Confirm its `algorithmname` (and `horzaggmeth` for `chorizon`) is supported.
   If not, the method must be designed and approved first; do not map it to a
   nearby method.
3. Add an `SdvRatingSpec` to `SDV_RATING_REGISTRY` with a new stable provenance
   ID, and bump `SDV_REGISTRY_VERSION` if an existing entry changes.
4. Add a golden case to `tests/fixtures/sdv_contract_cases.json` (SQL
   fingerprints, mocked rows, expected values, provenance, caveats).
5. Add a `live_network` benchmark in `tests/test_live_sda.py` with recorded
   county maximum and sample map unit values.
6. Update this document's registry table and, if behavior changes, ADR 0014.

Exposing a new record through a public tool is a separate decision (ADR 0008).

## Unsupported methods and deferrals

- Rejected methods: Dominant Component, Most Limiting, Least Limiting, Percent
  Present, and any other `algorithmname` outside `SUPPORTED_SDV_ALGORITHMS`;
  horizon methods outside `SUPPORTED_HORIZON_METHODS`.
- Caller-selectable AWS depth ranges and a fixed crop allowlist are deferred.
- Other `sdvattribute` tables (`muaggatt`, `comonth`, `coecoclass`,
  `mucropyld`, ...) are not engine sources. `muaggatt.aws0100wta` is used only as
  a live benchmark cross-check for AWS.
- The public `get_soil_interpretations` tool (`rule_name` +
  `aggregation_method`) is separate and unchanged.
- `componentpercentcutoff`, `nullratingreplacementvalue`, and `notratedphrase`
  are recorded but not applied.
