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
| - | STOP A | approved 2026-10-27 |
| 2 | 39.2.1 Registry and two-gate record validation | done |
| 3 | 39.3.1 Component-level strategies | done |
| 4 | 39.4.1 Horizon and crop strategies | done |
| 5 | 39.5.1 One engine: selectors, provenance, caveats, template retirement | done |
| - | STOP B | approved 2026-10-27 |
| 6 | 39.6.1 Corridor provenance and sentinel dedupe | done |
| 6 | 39.6.2 Contract doc, ADR 0014, ADR 0008 amendment, links | done |
| 7 | 39.7.1 Live benchmarks for all six records | done |
| 8 | 39.8.1 Two-axis review, full validation, final report | done |

## Task reports

## 39.1.1

Status: done. Branch `feat/sdv-metadata-contract` from `origin/main` `fd0189f`. Offline 475 passed/4 skipped/22 deselected; ruff 77 EXE002 (workspace artifact). Six sdvattribute records captured live (57 fields each) to `tests/fixtures/sdv_attribute_records.json` -- all match recon table, no drift. Method research recorded (Weighted Average, Dominant Condition + tiebreakrule, No Aggregation, Weighted Sum 0-100cm, nulls-as-zero flag, misc-area exclusion). Benchmarks: NCCPI IL019 0.933, CSR2 IA169 96, CPI MN167 100, Storie CA077 old=0.995/new=0.995 (per-mukey differs), AWS IL019 0% mismatch vs aws0100wta, Corn IL019 max=195/0% mixed units. Files: `planning/STATE_39.md`, `tests/fixtures/sdv_attribute_records.json`, `planning/tasks/39.1.1.todo.md`.
## 39.2.1

Status: done. Added SdvRatingSpec dataclass, SDV_RATING_REGISTRY (6 entries), SUPPORTED_SDV_ALGORITHMS, SUPPORTED_HORIZON_METHODS, SDV_CONTRACT_FIELDS (22 fields), validate_sdv_record (two-gate: registry match + structural), resolve_sdv_spec (exact alias match, crop validator). Removed sdvattribute from ALLOWED_SDV_TABLES (H2 fix). Extended SQL_SDV_ATTRIBUTE_LOOKUP to select all 22 contract fields. New test file tests/test_sdv_contract.py (37 tests). Offline suite: 512 passed (37 new), 4 skipped, 22 deselected. Ruff: 78 EXE002 only. Files: src/fpac_soil_mcp/sda_client.py (L74-450 new code, L354 removed sdvattribute), tests/test_sdv_contract.py (new). No changes to build_dynamic_sdv_query, get_productivity_ratings, or get_county_max_productivity_rating.
## 39.3.1

Status: done. Added per-strategy SQL builders: cointerp+Weighted Average (NCCPI-style), cointerp+Dominant Condition (Storie D5, window function with tiebreak), component+Weighted Average (CPI-style), mapunit+No Aggregation (CSR2-style). Added build_sdv_rating_query/build_sdv_county_max_query dispatching on (table, algorithm). build_dynamic_sdv_query/county_max delegate to new builders for registered cointerp/component/mapunit records, fall back to legacy for non-registered (backward compat). Updated 4 tests in test_sda_client.py (H1/H2 routing: interphr->interphrc, add algorithmname, registered rule names). New test_sdv_strategies.py (27 tests). Offline: 539 passed (27 new). Ruff: EXE002 only. Files: sda_client.py, test_sda_client.py (4 tests updated), test_sdv_strategies.py (new).
## 39.4.1

Status: done. Added chorizon + Weighted Sum (D6, 0-100cm depth clipping, awc_r*thickness) and cocropyld + Weighted Average (D7, crop filter, COALESCE nulls-as-zero, COUNT(DISTINCT yldunits) mixed-unit detection) builders. Registered both in _BUILDERS_RATING/_BUILDERS_COUNTY_MAX dispatch. _WAVE3_TABLES expanded to all 5 tables. Dynamic builders pass constraints for cocropyld. Missing crop raises SDAValidationError before SQL built. Updated 2 Wave 3 tests (AWS/cocropyld now supported). 9 new Wave 4 tests. Offline: 548 passed (9 new). Ruff: EXE002 only.
## 39.5.1

Status: done; STOP B approved by the user 2026-10-27 (Storie Dominant Condition values accepted). Fixed selectors and explicit metadata now resolve through `_resolve_productivity_spec` -> `resolve_sdv_spec` -> per-strategy builders (one engine, D9); unregistered records raise before any SQL (D2), legacy inline dynamic SQL and helpers removed. Added optional `constraints` argument, `SDV_CAVEATS` catalogue, `sdv_provenance` (D8, incl. `null_handling`, crop, per-mukey `yldunits`), D7 mixed-unit -> unrated. Deleted the six `SQL_PRODUCTIVITY_*` templates; `grep "SQL_PRODUCTIVITY_\|SDA:SDVATTRIBUTE" src/` empty. Golden fixture `tests/fixtures/sdv_contract_cases.json` (6 cases) with fingerprint/value/provenance/caveat/county-max tests; legacy parity tests hash origin/main templates (canonical SQL). Mocked main-vs-branch client comparison for NCCPI/CSR2/CPI: all pre-existing keys identical (values, rounding, source, caveats, sentinel and not-found rows, county max); only new keys added. Live check found the Wave 3 Dominant Condition SQL invalid on SDA (select alias `rating` in its own WHERE -> HTTP 400, also dropped unrated components from totals); rewritten per D5 with regression test. Error text for bad selectors restored to main's. Offline 585 passed/4 skipped/22 deselected; ruff clean except EXE002; live productivity subset 12 passed/3 skipped.

Live Storie CA077 (2026-10-27), origin/main Weighted Average vs branch Dominant Condition:

| mukey | old WA | new DC | delta | new rated/total % |
|---|---|---|---|---|
| 462057 | 0.241 | 0.294 | +0.053 | 92/92 |
| 462069 | 0.275 | 0.375 | +0.100 | 85/95 |
| 462070 | 0.187 | 0.255 | +0.068 | 85/92 |
| 461995 | 0.234 | 0.261 | +0.027 | 85/100 |
| 461996 | 0.158 | 0.194 | +0.036 | 85/100 |
| county max | 0.995 | 0.995 | 0 | - |

New values equal the 39.1.1 Dominant Condition benchmarks exactly. Live NCCPI IL019 (max 0.933), CSR2 IA169 (96), CPI MN167 (100): origin/main and branch identical.

## 39.6.1

Status: done. `corridor_analysis.py` sentinels, fallback sources, and NCCPI rule now come from `PRODUCTIVITY_SEMANTICS`, `PRODUCTIVITY_PROVENANCE`, and `SDV_RATING_REGISTRY` (H9). Fallback IDs are now the D8 IDs (`SDA:MAPUNIT_IACORNSR`, `SDA:COMPONENT_CROPPRODINDEX`, `SDA:COINTERP_STORIE_CA`); sentinel values and rule text unchanged (pinned by test). No public payload test referenced the drifted IDs. 5 new tests; corridor + phase3 41 passed; offline 590 passed/4 skipped/22 deselected; ruff clean except EXE002.

## 39.6.2

Status: done. New `docs/sdv-metadata-contract.md` (fields, selection, two-gate validation with exact messages, constraints, per-table behavior, null handling, provenance, caveat order and text, registry, add-a-record checklist, deferrals) and ADR 0014 (Accepted, EXECUTION_PLAN_39). ADR 0008 got a dated EP39 amendment (Storie Dominant Condition; routing governed by 0014; templates and `_round_for_index()` retired); decisions README has the 0014 row, amended 0008 status, and a "Rating Contract" era; one AGENTS.md References line; one README Storie sentence. Ad hoc check: 22/22 `SDV_CONTRACT_FIELDS`, 6/6 provenance IDs, 10/10 `SDV_CAVEATS` keys and texts, all `sdv_provenance` keys present; relative links resolve; diff in scope; offline 590 passed. Follow-up resolved at the user's request (2026-10-27): ADR 0002 got a dated EP39 amendment (constants retired, per-strategy builders, still Option 1 because identifiers come only from the registry); decisions README marks 0002 amended and updates the Foundation era line; ADR 0014 Validation points to it.

## 39.7.1

Status: implemented, live acceptance pending. `live_benchmark` blocks added to all six golden cases (39.1.1 values; engine output re-confirmed live in 39.5.1). 19 new `live_network` tests in `tests/test_live_sda.py`: drift guard (6), county max (5), sample map units (5), Storie new-vs-legacy, AWS vs `muaggatt.aws0100wta` (D11 thresholds), Corn county-wide mixed units (D7). Existing Storie live tests now assert Dominant Condition and the 0.995 county max. Tests skip only on network errors. Offline 590 passed (unchanged), ruff clean. Known-answer check against a fake SDA: 19/19 pass on benchmark values; a +1.0 change to a Storie, Corn, or NCCPI map unit fails the matching test. Live run not possible: `sdmdataaccess.nrcs.usda.gov` did not resolve from this compute 03:15-03:24 UTC (other USDA hosts did). Unverified until live: Corn `yldunits` = `Bu` and engine Corn county max = 195.

Live acceptance (2026-10-28 04:05 UTC, SDA resolving again): `uv run --frozen pytest -q -p no:cacheprovider -m live_network tests/test_live_sda.py -rs` -> 36 passed, 0 skipped (19 new + 17 existing). Direct engine check: Corn IL019 county max 195.0, sample rows `yldunits` `Bu` (242955 = 123.74). Both match the fixture; no fixture or src change. Status: done.

## 39.8.1

Status: done (2026-10-28). Review range `fd0189f..HEAD`. One standards fix committed (849733a): three `SDV_CAVEATS` strings ended in planning labels "(D5)", "(D6)", "(D7)"; `polygon_analysis.py` forwards row caveats into public responses, so Storie users would have seen them. Labels removed from `sda_client.py`, `docs/sdv-metadata-contract.md`, the golden fixture, and `tests/test_live_sda.py`. Plan labels remain only in docstrings and comments.

Validation (after the fix):

- `make check`: lint step fails on 79 EXE002 only (workspace exec-bit artifact, also on main); `ruff check . --extend-ignore EXE002` clean; `ruff format --check` 485 files formatted; `make test` 589 passed, 3 skipped, 43 deselected.
- Plan offline command (`-m "not live_network"`): 590 passed, 4 skipped, 41 deselected (baseline 475; +115). The 1-pass difference from `make test` is one `agent_eval` test that `make test` deselects.
- Full live suite (`-m live_network`): 41 passed, 3 skipped (the 3 are `eval/databricks` tests needing the optional mlflow group). `tests/test_live_sda.py`: 36 passed, 0 skipped.
- Public surface: `git diff origin/main...HEAD --stat -- src/fpac_soil_mcp/tools manifest.yaml server.json src/fpac_soil_mcp/models.py` empty. `productivity_rating`, `productivity_rating_class`, `productivity_rating_source` and the `nccpi`/`csr2`/`cpi`/`storie` selectors unchanged; README has the one Storie sentence. Only Storie values and its new Dominant Condition caveat change, as approved at STOP B.

Standards axis:

| Check | Result |
|---|---|
| ADR 0002: no caller strings in SQL | Pass. Table, column, rule, method, depth come only from `SDV_RATING_REGISTRY`; mukey and areasymbol through existing validators; `cropname` through `_validate_crop` (allowlist regex, no `;`/`--`) plus quote doubling. ADR 0002 amended. |
| ADR 0008: routing stays in `sda_client.py` | Pass. Builders and dispatch live only there; `corridor_analysis.py` imports registry constants (rule name, sentinels, provenance) but builds no SQL. |
| ADR 0011: live opt-in | Pass. `pytestmark = pytest.mark.live_network`; default path offline. |
| AGENTS.md conventions | Pass after 849733a. Ruff clean (EXE002 aside), no `.env`/caches committed, contract doc linked from References. |
| Commit messages | Pass. Conventional, domain scopes, no wave/task/orchestration numbers. |

Spec axis (D1-D11 trace):

| Decision | Evidence |
|---|---|
| D1 internal only | Public surface diff empty; `_PUBLIC_SELECTOR_IDS` = 4 fixed selectors; exact alias match. |
| D2 two gates | `validate_sdv_record` (registry match, then structural); unregistered records raise before SQL; `tests/test_sdv_contract.py`. |
| D3 six records | `SDV_RATING_REGISTRY` has nccpi, storie, csr2, cpi, aws_0_100, nonirr_crop_yield; each has a live benchmark (39.7.1 green). |
| D4 SDV method authoritative | Storie is Dominant Condition. Recorded deviation: CPI keeps null exclusion for parity, though its SDV null flag is 1 (39.1.1 research, contract doc, `_NULLS_AS_ZERO_TABLES`). |
| D5 method scope | `SUPPORTED_SDV_ALGORITHMS` = Weighted Average, Dominant Condition, No Aggregation Necessary; horizon Weighted Sum; others rejected (tests). DC by rounded `interphr` with `tiebreakrule`. |
| D6 AWS 0-100 | Registry pins 0.0/100.0; live cross-check vs `muaggatt.aws0100wta` passes. |
| D7 crop | Required, validated, exact match; mixed units -> unrated + caveat; live Corn `Bu`, county max 195. |
| D8 provenance | Six stable IDs; `sdv_provenance` record; corridor fallback IDs now match (39.6.1). |
| D9 one engine | `grep SQL_PRODUCTIVITY_ src/` empty; legacy parity tests for NCCPI/CSR2/CPI pass. |
| D10 docs | `docs/sdv-metadata-contract.md`, ADR 0014, ADR 0008 and 0002 amendments; linked from AGENTS.md, ADR 0014, module docstring. |
| D11 execution | Branch from `fd0189f` (main moved past recon's `3d1fda7`; recorded in Baseline); both STOPs approved; no push/PR; offline count only grew; live run and `make check` done. |

Exit criterion evidence (`TestGoldenContractCases`, 19 passed): for each case (nccpi, storie, csr2, cpi, aws_0_100, nonirr_crop_yield), `test_sql_fingerprints` pins the SDA query (rating and county-max SQL SHA-256), `test_rating_outputs` pins aggregation output (`numeric_rating`, `is_rated`), provenance (`productivity_rating_source` and the full `sdv_provenance` record), and caveats (exact list and order), and `test_county_max_output` pins the county max.

Totals: 13 commits on the branch (`fd0189f..HEAD`, including this report). Offline 475 -> 590 passed. Live SDV benchmarks: 19 new, all green.

Deferrals (unchanged from plan): public property selection; unsupported SDV methods; caller-selectable AWS depth; crop allowlist; other sdvattribute tables; public structured provenance; separate routing module; push/PR.

## Discovered

Out of scope; not fixed.

- Pre-existing: `TestLiveSDA::test_live_dynamic_sdv_queries_and_unrated_water_urban` does not catch network errors, so it fails instead of skipping when SDA is down.
- Pre-existing: `ALLOWED_SDV_TABLES` in `sda_client.py` also lists field names, not just table names.
- Pre-existing: older `TestLiveSDA` tests catch `SDAClientError`, which includes `SDAValidationError`, so a validation error shows up as a skip. The new tests use `_live()`, which catches only `SDAQueryError` and `httpx.HTTPError`.
- CPI does not apply its SDV `interpnullsaszeroflag` (kept for parity). Applying it would change public CPI numbers; needs a user decision.
- Live drift-guard and mixed-unit failure paths were never exercised end to end (only success paths run live; the fake-SDA failure check was blocked by a sandbox rule in 39.7.1).
- `planning/tasks/39.3.1.todo.md` and `39.4.1.todo.md` were never written; those tasks are documented only by their STATE reports.

## Escalations

- 2026-10-27 (39.7.1, infrastructure, not a value escalation): SDA hostname unresolvable from the workspace compute, so the live benchmark run is deferred. Rerun `uv run --frozen pytest -q -p no:cacheprovider -m live_network tests/test_live_sda.py` when it resolves.
  - Resolved 2026-10-28 04:02 UTC: hostname resolves; live run 36 passed. No value escalation needed.
