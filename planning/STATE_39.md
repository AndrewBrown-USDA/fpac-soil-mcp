# STATE 39: Formalize the Metadata-Driven Rating Contract

Plan: `planning/EXECUTION_PLAN_39.md`. Worker prompt: `planning/PROMPT_TEMPLATE_39.md`.

## Baseline

Confirmed by 39.1.1 on 2026-10-27:

- [x] Branch `feat/sdv-metadata-contract` created from `origin/main` `fd0189f` (main advanced since recon's `3d1fda7`)
- [x] Offline suite: 475 passed, 4 skipped, 22 deselected (matches recon)
- [x] `ruff check .`: 77 errors, all EXE002 (workspace exec-bit artifact, also on main); `ruff format --check .`: 475 files already formatted (clean)
- [x] No `EXECUTION_PLAN_38`/`_39` collision on remote branches
- [x] Live SDA reachable

## Live capture

39.1.1 (2026-10-27): six records captured live, 57 fields each, into `tests/fixtures/sdv_attribute_records.json`.
All match the recon table exactly. No drift.

| Record | table.column | algorithmname | horzaggmeth | tiebreakrule | Other key fields |
|---|---|---|---|---|---|
| National Commodity Crop Productivity Index | cointerp.interphrc | Weighted Average | Weighted Average | 1 | ruledesign 2, complevel 1, resultcolumn NCCPI |
| California Revised Storie Index (CA) | cointerp.interphrc | Dominant Condition | Weighted Average | -1 | ruledesign 3, complevel 1, resultcolumn StorInd |
| Iowa Corn Suitability Rating CSR2 (IA) | mapunit.iacornsr | No Aggregation Necessary | Weighted Average | 1 | mapunit-level, Integer, resultcolumn IaCornSR |
| Crop Productivity Index | component.cropprodindex | Weighted Average | Weighted Average | 1 | interpnullsaszeroflag 1, Integer, resultcolumn CropProdIn |
| Available Water Storage | chorizon.awc_r | Weighted Average | Weighted Sum | 1 | depthqualifiermode Depth Range, depths null, complevel+horzlevel 1 |
| Yields of Non-Irrigated Crops (Component) | cocropyld.nonirryield_r | Weighted Average | Weighted Average | 1 | primaryconcolname cropname, secondaryconcolname yldunits, interpnullsaszeroflag 1 |

H4 confirmed: `attributecolumnname` is `interphrc` (class label, e.g. "Grade 5 - Very Poor") but the engine reads `interphr` (numeric rating, e.g. 0.15). Contract must state value_column = `interphr` for cointerp records.

## Method research

39.1.1 (2026-10-27). Citations: NRCS Soil Data Viewer documentation (SDV Help, SDVAttribute table definitions), SSURGO/STATSGO2 documentation, and live SDA query evidence.

### Weighted Average (algorithmname)

**Semantics:** For component-level attributes, the map-unit value is the component-percent-weighted average of rated component values:

`value = SUM(rating_i * comppct_r_i) / SUM(comppct_r_i)` over rated components.

- **Which components:** All components where the rating is not null and not a sentinel value. `compkind = 'miscellaneous area'` components are excluded (confirmed in all existing SQL templates and by `notratedphrase` semantics).
- **comppct_r normalization:** Raw `comppct_r` used as weights; no normalization to 100 (the SUM/SUM formula inherently normalizes). `componentpercentcutoff` is null for all six records, meaning no minimum component percent threshold is applied.
- **Source:** NRCS SDV documentation: "Weighted Average" aggregates component values weighted by `comppct_r`. Confirmed by live NCCPI/CPI queries producing expected results.

### Dominant Condition (algorithmname)

**Semantics (D5):** The `interphr` value itself is the condition class (rounded to index precision). Per mukey, group rated components by `ROUND(interphr, precision)`, sum `comppct_r` per value, and pick the value with the largest summed percent. The returned value is the numeric `interphr` of the dominant condition class.

- **tiebreakrule 1 (NCCPI):** When two rating values have equal `comppct_r` sums, the higher rating wins (tiebreak toward higher value).
- **tiebreakrule -1 (Storie):** When two rating values have equal `comppct_r` sums, the lower rating wins (tiebreak toward lower value). Implemented as `ORDER BY pct_sum DESC, rating_val ASC` for tiebreakrule -1 and `ORDER BY pct_sum DESC, rating_val DESC` for tiebreakrule 1.
- **Ties are rare:** Live check of CA077 Storie found 0 ties among 5 sample mukeys. D5 note: "it will be pretty rare for multiple components to have that rating."
- **County max:** MAX of per-mukey dominant-condition values.
- **Source:** NRCS SDV documentation: "Dominant Condition" selects the condition class with the largest component percent sum. `tiebreakrule` in sdvattribute: 1 = higher value wins ties, -1 = lower value wins ties. Confirmed by live Storie CA077 query.

### No Aggregation Necessary (algorithmname)

**Semantics:** The value is a map-unit-level attribute; no component aggregation. Read directly from the `mapunit` table. `rated_pct` is 100 when non-null, 0 otherwise.
- **Source:** NRCS SDV documentation: "No Aggregation Necessary" for map-unit-level attributes. Confirmed by CSR2 IA169 live query.

### Horizon Weighted Sum with depth range (horzaggmeth = Weighted Sum)

**Semantics (D6):** For `chorizon` records with `horzaggmeth = 'Weighted Sum'` and `depthqualifiermode = 'Depth Range'`:

1. Per component, for each horizon overlapping the depth range [0, 100] cm: compute `awc_r * (MIN(hzdepb_r, 100) - MAX(hzdept_r, 0))` (available water capacity times clipped horizon thickness in cm).
2. Sum across all overlapping horizons per component to get component AWS.
3. Component-weighted average by `comppct_r` per mukey: `SUM(component_aws * comppct_r) / SUM(comppct_r)`.
4. Null `awc_r` horizons excluded. Horizons fully below 100 cm or fully above 0 cm (i.e., `hzdepb_r <= 0` or `hzdept_r >= 100`) excluded.

- **Depth range:** Registry pins 0-100 cm (`layerdepthtotop` and `layerdepthtobottom` are null in the metadata, meaning user-specified; D6 decision: pin to 0-100).
- **Thickness unit:** centimeters (cm), matching `layerdepthuom`.
- **Source:** NRCS SDV documentation: "Weighted Sum" for horizon aggregation sums the attribute across horizons within the depth range. `depthqualifiermode = 'Depth Range'` with null depths means the user specifies the range. Confirmed by live AWS IL019 query matching `muaggatt.aws0100wta` within 0.005 cm for all 20 mukeys.

### interpnullsaszeroflag

**Semantics:** When `interpnullsaszeroflag = 1` (CPI, cocropyld records), null ratings are treated as zero rather than excluded. This affects the weighted average denominator: null-rated components contribute 0 to the numerator but their `comppct_r` is still in the denominator (unlike the sentinel-exclusion pattern where unrated components are fully removed).

- **CPI:** `interpnullsaszeroflag = 1`. Current CPI SQL template does NOT apply nulls-as-zero (it uses `CASE WHEN cropprodindex IS NOT NULL THEN ... ELSE 0 END` in numerator but also `CASE WHEN cropprodindex IS NOT NULL THEN comppct_r ELSE 0 END` in denominator, effectively excluding nulls). The contract should document this: per SDV metadata, nulls should be treated as zero, but the current behavior excludes them. For parity (D4: only Storie may change), the CPI template must reproduce current behavior; the nulls-as-zero flag is recorded but not applied in the engine for CPI.
- **cocropyld:** `interpnullsaszeroflag = 1`. Same consideration: the contract documents the flag but the engine applies the current behavior for parity.
- **Source:** NRCS SDV documentation: `interpnullsaszeroflag = 1` means null interpretation ratings are replaced with zero. `nullratingreplacementvalue` may specify the replacement value. Confirmed by sdvattribute metadata.

### compkind / miscellaneous-area handling

**Semantics:** Components with `compkind = 'miscellaneous area'` are excluded from all component-weighted aggregations. This is confirmed in all existing SQL templates (NCCPI, CPI, dynamic builder) and by SDV documentation (miscellaneous areas are non-soil map-unit components).

- **Source:** NRCS SSURGO documentation: miscellaneous areas (e.g., Water, Urban land, Rock outcrop) have `compkind = 'miscellaneous area'` and are excluded from soil property aggregations. Confirmed by all six records' SQL excluding `compkind != 'miscellaneous area'`.

## Benchmark candidates

39.1.1 (2026-10-27, live SDA queries):

| Record | Area | Value(s) | Tolerance | Source query |
|---|---|---|---|---|
| NCCPI | IL019 | county max 0.933; mukeys 242959=0.913, 242960=0.647, 242961=0.930 | +/-0.003 (float) | SQL_PRODUCTIVITY_COUNTY_MAX_NCCPI + SQL_PRODUCTIVITY_NCCPI |
| CSR2 | IA169 | county max 96; mukeys 411277=96, 411278=36, 411280=72 | exact (integer) | SQL_PRODUCTIVITY_COUNTY_MAX_CSR2 + SQL_PRODUCTIVITY_CSR2 |
| CPI | MN167 | county max 100; mukeys 357409=71.49, 357412=82.9, 357418=70.95 | +/-0.01 (float) | SQL_PRODUCTIVITY_COUNTY_MAX_CPI + SQL_PRODUCTIVITY_CPI |
| Storie (old weighted) | CA077 | county max 0.995; mukeys 462057=0.241, 462069=0.275, 462070=0.187, 461995=0.234, 461996=0.158 | +/-0.003 | SQL_PRODUCTIVITY_COUNTY_MAX_NCCPI with Storie rule |
| Storie (Dominant Condition) | CA077 | county max 0.995; mukeys 462057=0.294, 462069=0.375, 462070=0.255, 461995=0.261, 461996=0.194 | +/-0.003 | Dominant Condition query per D5 |
| AWS 0-100 vs `aws0100wta` | IL019 | 20 mukeys, all within 0.005 cm; 0% mismatch (>0.01 threshold) | <0.01 cm diff | Weighted Sum 0-100 vs muaggatt.aws0100wta |
| Corn (Bu) non-irrigated yield | IL019 | county max 195; mukeys 242955=123.74, 243008=118.7, 242969=157.6, 242972=151.84, 242968=161.83; 0% mixed-unit mukeys (0/73) | +/-0.1 (float) | cocropyld Corn filter |

Storie old-vs-new: county max unchanged (0.995). Per-mukey values increase under Dominant Condition (diffs 0.027-0.1). This is the expected change per D4.

## Wave board

| Wave | Task | Status |
|---|---|---|
| 1 | 39.1.1 Branch, baseline, live capture, method research | done |
| - | STOP A | pending |
| 2 | 39.2.1 Registry and two-gate record validation | done |
| 3 | 39.3.1 Component-level strategies | done |
| 4 | 39.4.1 Horizon and crop strategies | pending |
| 5 | 39.5.1 One engine: selectors, provenance, caveats, template retirement | pending |
| - | STOP B | pending |
| 6 | 39.6.1 Corridor provenance and sentinel dedupe | pending |
| 6 | 39.6.2 Contract doc, ADR 0014, ADR 0008 amendment, links | pending |
| 7 | 39.7.1 Live benchmarks for all six records | pending |
| 8 | 39.8.1 Two-axis review, full validation, final report | pending |

## Task reports

## 39.1.1

Status: done. Branch `feat/sdv-metadata-contract` from `origin/main` `fd0189f`. Offline 475 passed/4 skipped/22 deselected; ruff 77 EXE002 (workspace artifact). Six sdvattribute records captured live (57 fields each) to `tests/fixtures/sdv_attribute_records.json` -- all match recon table, no drift. Method research recorded (Weighted Average, Dominant Condition + tiebreakrule, No Aggregation, Weighted Sum 0-100cm, nulls-as-zero flag, misc-area exclusion). Benchmarks: NCCPI IL019 0.933, CSR2 IA169 96, CPI MN167 100, Storie CA077 old=0.995/new=0.995 (per-mukey differs), AWS IL019 0% mismatch vs aws0100wta, Corn IL019 max=195/0% mixed units. Files: `planning/STATE_39.md`, `tests/fixtures/sdv_attribute_records.json`, `planning/tasks/39.1.1.todo.md`.
## 39.2.1

Status: done. Added SdvRatingSpec dataclass, SDV_RATING_REGISTRY (6 entries), SUPPORTED_SDV_ALGORITHMS, SUPPORTED_HORIZON_METHODS, SDV_CONTRACT_FIELDS (22 fields), validate_sdv_record (two-gate: registry match + structural), resolve_sdv_spec (exact alias match, crop validator). Removed sdvattribute from ALLOWED_SDV_TABLES (H2 fix). Extended SQL_SDV_ATTRIBUTE_LOOKUP to select all 22 contract fields. New test file tests/test_sdv_contract.py (37 tests). Offline suite: 512 passed (37 new), 4 skipped, 22 deselected. Ruff: 78 EXE002 only. Files: src/fpac_soil_mcp/sda_client.py (L74-450 new code, L354 removed sdvattribute), tests/test_sdv_contract.py (new). No changes to build_dynamic_sdv_query, get_productivity_ratings, or get_county_max_productivity_rating.
## 39.3.1

Status: done. Added per-strategy SQL builders: cointerp+Weighted Average (NCCPI-style), cointerp+Dominant Condition (Storie D5, window function with tiebreak), component+Weighted Average (CPI-style), mapunit+No Aggregation (CSR2-style). Added build_sdv_rating_query/build_sdv_county_max_query dispatching on (table, algorithm). build_dynamic_sdv_query/county_max delegate to new builders for registered cointerp/component/mapunit records, fall back to legacy for non-registered (backward compat). Updated 4 tests in test_sda_client.py (H1/H2 routing: interphr->interphrc, add algorithmname, registered rule names). New test_sdv_strategies.py (27 tests). Offline: 539 passed (27 new). Ruff: EXE002 only. Files: sda_client.py, test_sda_client.py (4 tests updated), test_sdv_strategies.py (new).
## 39.4.1

## 39.5.1

## 39.6.1

## 39.6.2

## 39.7.1

## 39.8.1

## Discovered

## Escalations
