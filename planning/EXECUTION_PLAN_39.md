# EXECUTION PLAN 39: Formalize the Metadata-Driven Rating Contract

## Goal & Scope

**Goal (user's terms):** Formalize the metadata-driven rating contract. Document the required `sdvattribute` metadata fields; define how metadata is selected, validated, and passed into the query engine; document behavior for `cointerp`, `chorizon`, `cocropyld`, `component`, and `mapunit` properties; define stable provenance for metadata-selected ratings; add fixture coverage for each source-table strategy; and distinguish fixed convenience selectors from explicit metadata-driven property selection.

**Exit criterion (verbatim):** "A validated metadata record deterministically produces the correct SDA query, aggregation behavior, provenance, and caveats."

**In scope:**

- A frozen, versioned registry of validated `sdvattribute` records in `src/fpac_soil_mcp/sda_client.py` (D2, D3): NCCPI, Storie (`cointerp`), CSR2 (`mapunit`), CPI (`component`), Available Water Storage (`chorizon`), Yields of Non-Irrigated Crops (Component) (`cocropyld`).
- Two-gate validation: registry match, then strict structural validation (D2).
- Query strategies keyed on table plus SDV `algorithmname`, with the SDV method authoritative (D4, D5), limited to the methods the six records use.
- One engine: fixed selectors (`nccpi`, `csr2`, `cpi`, `storie`) resolve to registry entries; `SQL_PRODUCTIVITY_*` templates retired after parity tests (D9).
- Stable provenance IDs plus an internal structured provenance record (D8); caveat catalog.
- Fixture coverage per source-table strategy, plus golden contract cases (record to SQL, aggregation, provenance, caveats).
- Corridor fallback provenance/sentinel maps replaced by the `sda_client` source of truth (stable provenance).
- Docs: `docs/sdv-metadata-contract.md`, ADR 0014, a dated clarifying amendment to ADR 0008, `docs/decisions/README.md` index, `AGENTS.md` link, one `README.md` line on the Storie method change (D10, D11).
- Live benchmarks for all six records, including the Storie old-vs-new comparison (D3, D6, D7, D11).

**Out of scope (explicit deferrals):**

- Any public MCP property-selection parameter or tool; public tool signatures, `manifest.yaml`, `server.json` unchanged (D1). Future: public selection from a broader validated list.
- SDV methods no registered record uses: Dominant Component, Most Limiting, Least Limiting, Percent Present, and any other `algorithmname`; they are rejected (D5).
- Caller-selectable AWS depth ranges (D6); a fixed crop allowlist (D7).
- Other `sdvattribute` tables (`muaggatt`, `comonth`, `coecoclass`, `mucropyld`, ...). `muaggatt.aws0100wta` is read only as a benchmark cross-check (D6), never as an engine source.
- The public `get_soil_interpretations` tool (`rule_name` + `aggregation_method` path, `SQL_INTERPRETATION_*`); unchanged.
- Exposing the structured provenance record in a public schema (D8).
- Extracting a separate routing module (ADR 0008 boundary: routing stays in `sda_client.py`).
- Pushing the branch or opening a PR (D11).

**Verbatim constraints from the user:**

- "A only for now. some day we might allow property selection (from a broader list of validated cases) but for now we just want the core cases allowed" (D1).
- "I really think this is the opportunity to make sure our methods align with what the algorithm SDV says to use is, so I am not opposed to enforcing that here, though I suppose it expands the scope somewhat" (D4).
- "dominant condition may actually be using the interp class rather than the fuzzy rating ... just treat the number as a class (and recognize it will be pretty rare for multiple components to have that rating)." (D5)
- "agree an amendment to clarify is best here" (D10).
- Commits allowed on a feature branch; conventional commits; no wave numbers in commit messages (standing preference).

## Reconnaissance Log

Captured 2026-10-27 in `/Workspace/Users/andrew.g.brown@usda.gov/fpac-soil-mcp` (shell `sh`; `uv run --frozen` with `UV_PROJECT_ENVIRONMENT=/tmp/fpac-venv`).

- Git: `main` = `origin/main` = `3d1fda7`. Highest plan on any remote branch: 37 (user chose 39).
- Baseline: `uv run --frozen pytest -q -p no:cacheprovider -m "not live_network"` = 475 passed, 4 skipped, 22 deselected; `ruff check .` clean. Live SDA reachable from workspace shell.
- `sda_client.py` is 1,332 lines. Anchors: `PRODUCTIVITY_PROVENANCE` L31, `PRODUCTIVITY_SEMANTICS` L38, `SQL_SDV_ATTRIBUTE_LOOKUP` L233, `SQL_PRODUCTIVITY_NCCPI` L247 ... `SQL_PRODUCTIVITY_COUNTY_MAX_CPI` L337, `ALLOWED_SDV_TABLES` L348, `_dynamic_index_name` L388, `build_dynamic_sdv_query` L424, `build_dynamic_sdv_county_max_query` L621, `lookup_sdv_attribute` L1117, `get_county_max_productivity_rating` L1141, `get_productivity_ratings` L1202.
- `attribute_meta` is used only inside `sda_client.py`; no tool, polygon, corridor, or LESA caller passes it.
- Live `sdvattribute` has 57 columns. Engine reads only table, column, `nasisrulename`, `cropname` (not an SDV field).
- Live records (2026-10-27):

| Record | table.column | `algorithmname` | `horzaggmeth` | Other relevant fields |
|---|---|---|---|---|
| National Commodity Crop Productivity Index | `cointerp.interphrc`, rule `NCCPI - National Commodity Crop Productivity Index (Ver 3.0)` | Weighted Average | Weighted Average | `tiebreakrule` 1, `ruledesign` 2 |
| California Revised Storie Index (CA) | `cointerp.interphrc`, rule `AGR - California Revised Storie Index (CA)` | Dominant Condition | Weighted Average | `tiebreakrule` -1 |
| Iowa Corn Suitability Rating CSR2 (IA) | `mapunit.iacornsr` (Integer) | No Aggregation Necessary | n/a | `tiebreakrule` 1 |
| Crop Productivity Index | `component.cropprodindex` (Integer) | Weighted Average | n/a | `tiebreakrule` 1 |
| Available Water Storage | `chorizon.awc_r` (Float, cm) | Weighted Average | Weighted Sum | `depthqualifiermode` Depth Range, depths null |
| Yields of Non-Irrigated Crops (Component) | `cocropyld.nonirryield_r` (Float) | Weighted Average | n/a | `primaryconcolname` cropname, `secondaryconcolname` yldunits, `interpnullsaszeroflag` 1 |

- Algorithm distribution in allowed tables: `cointerp` 579 Dominant Condition / 34 Dominant Component / 18 Weighted Average / 6 Most Limiting / 2 Least Limiting; `chorizon` 28 Dominant Component; `component` 24 Dominant Condition; `mapunit` 6 No Aggregation.
- Hazards found in current engine:
  - H1 routing `table == "cointerp" or rule_name`: any record with a rule name goes to the cointerp template.
  - H2 `sdvattribute` is in `ALLOWED_SDV_TABLES` and falls into the default component branch; no explicit `component` branch.
  - H3 `algorithmname` ignored: Storie is weighted though SDV says Dominant Condition.
  - H4 cointerp metadata names `interphrc`; engine reads `interphr`. Contract must state that numeric ratings come from `interphr`.
  - H5 chorizon ignores `horzaggmeth` and depth; averages all horizons.
  - H6 cocropyld without crop mixes crops and units; nulls-as-zero ignored.
  - H7 provenance for metadata path is the generic `SDA:SDVATTRIBUTE`.
  - H8 `_dynamic_index_name` uses substring alias matching.
  - H9 `corridor_analysis.py` L59-L71 duplicates sentinels and fallback sources with drifted IDs (`SDA:CSR2`, `SDA:CPI`, `SDA:STORIE_CA`).
- Tests touching the engine: `tests/test_sda_client.py` (L16-17 imports, L96-131 validation, L610-L900 dynamic builders), `tests/test_live_sda.py` (L111 dynamic, L133-L282 CSR2/CPI/Storie), `tests/test_corridor_analysis.py` (provenance asserts), `tests/fixtures/le_benchmarks.json` (case `CA_STORIE_SAN_JOAQUIN_SITE` L222).
- ADRs 0001-0013 Accepted. Relevant: 0002 (fixed SQL templates; complied with), 0008 (amended, not superseded), 0011 (mocked default, live opt-in).

## Decision Log

1. **D1, 2026-10-27, Consumer:** internal-only contract in `sda_client.py`. Public tools keep only the four fixed selectors. Public property selection from a broader validated list is a future item.
2. **D2, 2026-10-27, Validation:** "validated" means a frozen in-code registry of exact records matched on `attributename`, table, column, and rule name. Unregistered records are rejected before any query is built. Strict structural validation always runs as the second gate.
3. **D3, 2026-10-27, Registry seed:** NCCPI, Storie, CSR2, CPI, plus Available Water Storage (`chorizon.awc_r`) and Yields of Non-Irrigated Crops (Component) (`cocropyld.nonirryield_r`, crop required), each with a live-verified benchmark.
4. **D4, 2026-10-27, Method authority:** SDV `algorithmname` (plus `horzaggmeth`, depth mode, null flag, tie-break) is authoritative. Storie becomes Dominant Condition; public Storie numbers change. Scope expansion accepted.
5. **D5, 2026-10-27, Method scope:** support only Weighted Average, Dominant Condition, No Aggregation Necessary, horizon Weighted Sum with a depth range, and nulls-as-zero. Reject all other methods. Dominant Condition numeric: the `interphr` value itself is the condition class (rounded to index precision, 3 decimals for Storie); sum `comppct_r` per value; pick the largest; break ties with `tiebreakrule`. Ties are expected to be rare.
6. **D6, 2026-10-27, AWS depth:** registry pins 0-100 cm, not caller-selectable. Live benchmark cross-checks against `muaggatt.aws0100wta`.
7. **D7, 2026-10-27, Crop:** caller supplies the required `cropname` (safe-character check, exact match on `cocropyld.cropname`, no default). Each result must have a single `yldunits`, otherwise unrated with a caveat. Crop and units are in provenance. Benchmark: Corn (Bu).
8. **D8, 2026-10-27, Provenance:** stable string ID per registry entry feeds the public `productivity_rating_source`: `SDA:NCCPI_V3`, `SDA:MAPUNIT_IACORNSR`, `SDA:COMPONENT_CROPPRODINDEX`, `SDA:COINTERP_STORIE_CA` (unchanged), `SDA:CHORIZON_AWC_R_0_100`, `SDA:COCROPYLD_NONIRRYIELD_R` (new). Internal structured provenance record: ID, registry version, `attributename`, table, column, rule, `algorithmname`, `horzaggmeth`, depth range, `tiebreakrule`, null handling, crop/units. No public schema change.
9. **D9, 2026-10-27, One engine:** fixed selectors are named aliases to registry entries and run the same validate, build, aggregate, provenance path. `SQL_PRODUCTIVITY_*` and `SQL_PRODUCTIVITY_COUNTY_MAX_*` are removed after NCCPI/CSR2/CPI parity tests pass. Complies with ADR 0002 (SQL only from fixed per-strategy templates filled with registry-pinned, validated values).
10. **D10, 2026-10-27, Docs and ADRs:** new ADR 0014 "Registry-validated SDV metadata contract"; ADR 0008 stays Accepted with a dated clarifying amendment (Storie method, pointer to 0014); field-level contract in new `docs/sdv-metadata-contract.md`, linked from `AGENTS.md`, ADR 0014, and the `sda_client.py` module docstring.
11. **D11, 2026-10-27, Execution:**
    - Branch `feat/sdv-metadata-contract` from `origin/main` `3d1fda7`; commits allowed with domain scopes (`feat(sda)`, `test(sda)`, `docs(decisions)`, `docs(planning)`), no wave numbers; no push/PR.
    - Serial, single executor. Stop A after wave 1; stop B after the Storie change (old vs new CA077).
    - Escalate on: live record drift from this recon; AWS 0-100 vs `muaggatt.aws0100wta` differing by more than 0.01 cm on more than 5% of benchmark map units; any NCCPI/CSR2/CPI parity failure.
    - Per wave: offline pytest green with at least 475 passing (count may only grow, net of removed constant-only tests that are recorded), `ruff check` clean, targeted tests. End: full live run and `make check`.
    - Public surface unchanged except one `README.md` line about the Storie method change.
12. **D12, 2026-10-28, CPI nulls-as-zero (post-review follow-up):** after the final review, the user confirmed CPI's live `sdvattribute` record has `interpnullsaszeroflag = 1` and chose to apply it (Option A): a null-rated CPI component counts as 0 when its map unit has at least one rated component; a map unit with no rated component stays unrated. Miscellaneous areas stay excluded; `rated_pct` stays the non-null percent. Supersedes the CPI parity carve-out in D4/D9 (CPI rating SQL may differ from the retired template; CPI county-max SQL still matches). One more `README.md` sentence allowed. Live MN167: 2800029 83 to 79, county max 100 and benchmark map units unchanged; MN053 stays unrated.

## Wave & Dependency Table

| Wave | Task | Title | Files in scope | Depends on |
|---|---|---|---|---|
| 1 | 39.1.1 | Branch, baseline, live capture, method research | `planning/STATE_39.md`, `tests/fixtures/sdv_attribute_records.json` (new), `planning/tasks/39.1.1.todo.md` | none |
| - | STOP A | User confirms method semantics and benchmark values | - | 39.1.1 |
| 2 | 39.2.1 | Registry and two-gate record validation | `src/fpac_soil_mcp/sda_client.py`, `tests/test_sdv_contract.py` (new), `tests/test_sda_client.py` (allowlist tests only) | STOP A |
| 3 | 39.3.1 | Component-level strategies (cointerp, component, mapunit) | `src/fpac_soil_mcp/sda_client.py`, `tests/test_sdv_strategies.py` (new), `tests/test_sda_client.py` (routing asserts only) | 39.2.1 |
| 4 | 39.4.1 | Horizon and crop strategies (chorizon, cocropyld) | `src/fpac_soil_mcp/sda_client.py`, `tests/test_sdv_strategies.py`, `tests/test_sda_client.py` (chorizon/cocropyld tests only) | 39.3.1 |
| 5 | 39.5.1 | One engine: selectors, provenance, caveats, template retirement | `src/fpac_soil_mcp/sda_client.py`, `tests/test_sda_client.py`, `tests/test_sdv_contract.py`, `tests/fixtures/sdv_contract_cases.json` (new) | 39.4.1 |
| - | STOP B | User reviews Storie old vs new (CA077) | - | 39.5.1 |
| 6 | 39.6.1 | Corridor provenance and sentinel dedupe | `src/fpac_soil_mcp/corridor_analysis.py`, `tests/test_corridor_analysis.py` | STOP B |
| 6 | 39.6.2 | Contract doc, ADR 0014, ADR 0008 amendment, links | `docs/sdv-metadata-contract.md` (new), `docs/decisions/0014-registry-validated-sdv-metadata-contract.md` (new), `docs/decisions/0008-nccpi-validated-public-index-with-extensible-sdv-routing.md`, `docs/decisions/README.md`, `AGENTS.md`, `README.md` | STOP B |
| 7 | 39.7.1 | Live benchmarks for all six records | `tests/test_live_sda.py`, `tests/fixtures/sdv_contract_cases.json` (benchmark values only) | 39.6.1, 39.6.2 |
| 8 | 39.8.1 | Two-axis review, full validation, final report | `planning/STATE_39.md` (fixes to a W2-W7 file only when a check fails) | 39.7.1 |

Waves 2-5 all edit `sda_client.py` and are strictly serial. Wave 6 tasks have pairwise-disjoint files but run serially (single executor, D11). Every task also writes its own `planning/tasks/39.x.y.todo.md` and appends its report to `planning/STATE_39.md`.

## Hazards

- **Long file.** `sda_client.py` is 1,332 lines. Workers navigate by grep anchors named in each spec; never rewrite the whole file.
- **Hidden coupling.** Review grep (2026-10-27): `polygon_analysis.py` and `corridor_analysis.py` import only `SDAClient`/`SDAClientError`; `ALLOWED_SDV_TABLES`, `build_dynamic_sdv_*`, `SQL_PRODUCTIVITY_*`, and `PRODUCTIVITY_*` are imported only by `tests/test_sda_client.py`. `lesa._normalize_productivity_index` (enum, used by tools) is a different function from `sda_client._normalize_productivity_index`; do not merge them. Keep `PRODUCTIVITY_PROVENANCE` and `PRODUCTIVITY_SEMANTICS` importable with current values; 39.6.1 is the only task that changes a non-`sda_client` source file.
- **Public numbers.** Only Storie may change. NCCPI, CSR2, CPI output (values, classes, provenance, rounding, sentinels) must be byte-identical on existing fixtures; any difference is an escalation (D11).
- **SQL injection surface.** All interpolated values come from the registry or pass existing validators (`validate_mukey`, `validate_survey_area_symbol`, new crop validator). No caller-provided table, column, or method string reaches SQL (ADR 0002).
- **Live variability.** SDA data refreshes can move benchmark values. Live tests assert tolerances recorded in STATE_39 from 39.1.1, not exact floats, except integers (CSR2, CPI).
- **Git folder side effects.** The workspace Git folder can pull, switch HEAD, or stage files between commands. Run `git status -sb` and `git diff --cached --name-only` immediately before every commit.

## Task Specifications

### 39.1.1 - Branch, baseline, live capture, method research

**Repository:** `/Workspace/Users/andrew.g.brown@usda.gov/fpac-soil-mcp`

**Files in scope**

- Must edit: `planning/STATE_39.md` (Baseline, Live capture, Method research sections)
- Can create: `tests/fixtures/sdv_attribute_records.json`, `planning/tasks/39.1.1.todo.md`
- Temp/scratch: shell output only

**Depends on:** none.

**Specification:**

1. Create `feat/sdv-metadata-contract` from `origin/main`; record SHA, status; re-run offline baseline and ruff; record counts.
2. Confirm no `EXECUTION_PLAN_39` or `_38` collision on any remote branch.
3. Live-capture all 57 `sdvattribute` columns for the six registry records (exact `attributename` match) into `tests/fixtures/sdv_attribute_records.json` (`{"captured": "<date>", "records": [...]}`), sorted keys. Compare against the recon table; any difference is ESCALATE.
4. Research and record, with citations (SDV/SSURGO documentation URLs or SDA query evidence), the exact semantics of: Dominant Condition including `tiebreakrule` 1 vs -1; Weighted Average component weighting (which components, `comppct_r` normalization, `componentpercentcutoff` null); horizon Weighted Sum with a 0-100 cm depth range (horizon clipping, thickness unit); `interpnullsaszeroflag`; `compkind`/miscellaneous-area handling.
5. Compute candidate benchmark values with ad hoc live SQL (not committed):
   - Storie CA077: current weighted county max and Dominant Condition county max per D5; 5 sample mukeys old vs new.
   - AWS 0-100 for 20 mukeys in one county (choose IL019 unless coverage is poor) vs `muaggatt.aws0100wta`; record the share differing by more than 0.01 cm.
   - Corn (Bu) non-irrigated yield for 5 mukeys and county max in IL019; count map units with mixed `yldunits` for Corn.
   - NCCPI IL019, CSR2 IA169, CPI MN167 current values for later parity checks.
6. Commit in two commits: the Plan 39 artifacts plus the task todo (`docs(planning): plan metadata-driven rating contract`), then the fixture (`test(sda): capture live sdvattribute records for registered ratings`).

**Constraints:** no `src/` or test code edits.

**Grep anchors:** `SQL_SDV_ATTRIBUTE_LOOKUP`, `SQL_PRODUCTIVITY_COUNTY_MAX_NCCPI`, `def get_county_max_productivity_rating`.

**Reference implementations:** `planning/STATE_37.md` 37.1.1 (baseline capture style); `planning/SDV_STATE_INDEX_RESEARCH.md` (live-probe write-up style).

**Acceptance:** STATE_39 Baseline, Live capture, and Method research sections filled with commands and results; fixture has exactly six records with 57 keys each (`python -c` check recorded); AWS mismatch share recorded; `git show --stat HEAD` lists only allowed files.

**Escalate when:** any record differs from the recon table; AWS mismatch exceeds the D11 threshold; Dominant Condition semantics cannot be pinned from documentation and SDA evidence; mixed Corn units are common (more than 5% of IL019 map units).

### STOP A

Orchestrator presents the method research, benchmark candidates, and the Storie old-vs-new sample to the user. Continue only on explicit approval; record approval in STATE_39.

### 39.2.1 - Registry and two-gate record validation

**Files in scope**

- Must edit: `src/fpac_soil_mcp/sda_client.py`; `tests/test_sda_client.py` (allowlist tests L124-L131 only, if step 6 applies)
- Can create: `tests/test_sdv_contract.py`, `planning/tasks/39.2.1.todo.md`
- Read-only: `tests/fixtures/sdv_attribute_records.json`

**Depends on:** STOP A.

**Specification:**

1. Add a frozen dataclass `SdvRatingSpec` near `PRODUCTIVITY_SEMANTICS` with fields: `spec_id` (e.g. `"nccpi"`, `"storie"`, `"csr2"`, `"cpi"`, `"aws_0_100"`, `"nonirr_crop_yield"`), `provenance_id` (D8), `attributename`, `table`, `column` (SDV column as published), `value_column` (column the engine reads; `interphr` for cointerp per H4), `rule_name`, `algorithm`, `horizon_method`, `depth_top_cm`/`depth_bottom_cm`, `tiebreak_rule`, `nulls_as_zero`, `required_constraints` (e.g. `("cropname",)`), `scale`, `precision`, `sentinels`, `aliases`.
2. Add `SDV_REGISTRY_VERSION = "1"` and `SDV_RATING_REGISTRY: Mapping[str, SdvRatingSpec]` (use `types.MappingProxyType`) with the six entries; values for NCCPI/CSR2/CPI/Storie scale, precision, sentinels, aliases must equal `PRODUCTIVITY_SEMANTICS`.
3. Add `SUPPORTED_SDV_ALGORITHMS`, `SUPPORTED_HORIZON_METHODS` frozensets (D5) and `SDV_CONTRACT_FIELDS` (the required metadata fields documented in 39.6.2).
4. Add `validate_sdv_record(record) -> SdvRatingSpec`: gate 1 registry match on normalized `attributename`, table, column, rule; gate 2 structural checks (required fields present; table in the five strategy tables; `algorithmname` in supported set; `horzaggmeth` supported when table is `chorizon`; identifier columns match `^[a-z_][a-z0-9_]*$`; record method fields equal the spec). Raise `SDAValidationError` with distinct messages: `unregistered SDV record`, `unsupported aggregation method`, `malformed SDV record`.
5. Add `resolve_sdv_spec(selector: str | None, record: Mapping | None, constraints: Mapping | None) -> tuple[SdvRatingSpec, dict]`: exactly one of selector/record; selector resolves via exact alias match (replacing H8 substring logic); validates required constraints (crop: non-empty, `^[A-Za-z0-9 ,()\-/'.]{1,80}$`, no `;`/`--`).
6. Remove `sdvattribute` from `ALLOWED_SDV_TABLES` (H2) only if no test or caller depends on it beyond the allowlist tests; otherwise record under Discovered.
7. Extend `SQL_SDV_ATTRIBUTE_LOOKUP` to select every field in `SDV_CONTRACT_FIELDS`.
8. Tests in `tests/test_sdv_contract.py`: each fixture record validates to its spec; altered `algorithmname` raises unsupported or malformed as appropriate; unregistered record raises; selector aliases resolve; crop required/validated; injection strings rejected.

**Constraints:** do not change query builders or `get_productivity_ratings` behavior; do not touch other `src/` files.

**Grep anchors:** `PRODUCTIVITY_SEMANTICS = {`, `ALLOWED_SDV_TABLES = {`, `def _dynamic_index_name`, `SQL_SDV_ATTRIBUTE_LOOKUP`.

**Reference implementations:** `validate_survey_area_symbol` (L416) for validator style; `PRODUCTIVITY_SEMANTICS` for registry shape.

**Acceptance:** `uv run --frozen pytest -q -p no:cacheprovider tests/test_sdv_contract.py tests/test_sda_client.py` green; offline suite count at least baseline; ruff clean.

**Escalate when:** a registry value cannot be made equal to `PRODUCTIVITY_SEMANTICS` without changing NCCPI/CSR2/CPI behavior.

### 39.3.1 - Component-level strategies (cointerp, component, mapunit)

**Files in scope**

- Must edit: `src/fpac_soil_mcp/sda_client.py`; `tests/test_sda_client.py` (step 6 only)
- Can create: `tests/test_sdv_strategies.py`, `planning/tasks/39.3.1.todo.md`

**Depends on:** 39.2.1.

**Specification:**

1. Add fixed per-strategy SQL templates (rating and county max) keyed by `(table, algorithm)`: `cointerp`+Weighted Average, `cointerp`+Dominant Condition, `component`+Weighted Average, `mapunit`+No Aggregation Necessary. Values interpolated only from the spec and validated mukeys/areasymbol.
2. Weighted Average templates must reproduce the current NCCPI and CPI SQL semantics exactly (sentinel predicate, `compkind != 'miscellaneous area'` for CPI, `comppct_r` weighting, `is_rated` flag).
3. Dominant Condition (D5): per mukey, group rated components by `ROUND(interphr, precision)`, sum `comppct_r`, choose the largest; ties resolved by `tiebreakrule` (semantics from STATE_39 Method research); return the chosen value and its summed percent. County max = max of map-unit dominant-condition values.
4. Add `build_sdv_rating_query(spec, mukeys, constraints)` and `build_sdv_county_max_query(spec, areasymbol, constraints)` dispatching on `(spec.table, spec.algorithm)`; unknown pair raises `unsupported aggregation method`. Keep `build_dynamic_sdv_query` / `build_dynamic_sdv_county_max_query` as thin wrappers that call `validate_sdv_record` then the new builders (signatures unchanged).
5. Tests in `tests/test_sdv_strategies.py`, one class per strategy: generated SQL contains the expected table, value column, rule, weighting/grouping clauses; mocked SDA rows produce the expected aggregated value, including a Dominant Condition tie case for each `tiebreakrule` sign and a sentinel case.
6. Update existing `tests/test_sda_client.py` dynamic-builder tests only where they assert the old H1/H2 routing; list each change in the report.

**Constraints:** do not change `get_productivity_ratings` routing yet; chorizon and cocropyld paths keep current behavior until 39.4.1.

**Grep anchors:** `def build_dynamic_sdv_query`, `def build_dynamic_sdv_county_max_query`, `SQL_PRODUCTIVITY_NCCPI`, `SQL_PRODUCTIVITY_CPI`, `def _sentinel_sql_predicate`.

**Reference implementations:** `SQL_PRODUCTIVITY_NCCPI`, `SQL_PRODUCTIVITY_CPI`, `SQL_PRODUCTIVITY_CSR2` (templates to match); `SQL_INTERPRETATION_DOMINANT_COMP` (window-function style).

**Acceptance:** `uv run --frozen pytest -q -p no:cacheprovider tests/test_sdv_strategies.py tests/test_sdv_contract.py tests/test_sda_client.py` green; offline suite at least baseline; ruff clean.

**Escalate when:** the Weighted Average template cannot reproduce current NCCPI/CPI results on the existing mocked fixtures.

### 39.4.1 - Horizon and crop strategies (chorizon, cocropyld)

**Files in scope**

- Must edit: `src/fpac_soil_mcp/sda_client.py`, `tests/test_sdv_strategies.py`; `tests/test_sda_client.py` (existing chorizon/cocropyld builder tests near L701-L811 only)
- Can create: `planning/tasks/39.4.1.todo.md`

**Depends on:** 39.3.1.

**Specification:**

1. `chorizon` + Weighted Average + horizon Weighted Sum (D6): per component, sum `awc_r * (MIN(hzdepb_r, 100) - MAX(hzdept_r, 0))` over horizons overlapping 0-100 cm, null `awc_r` excluded per Method research; then component-weighted average by `comppct_r` per mukey. County max template uses the same mukey value.
2. `cocropyld` + Weighted Average (D7): filter `cropname = '<validated crop>'`; nulls as zero per `nulls_as_zero` and Method research; component-weighted by `comppct_r`; return `yldunits` aggregate (`MIN`/`MAX` or `COUNT(DISTINCT)`) so the client can mark mixed-unit map units unrated.
3. Register both templates in the `(table, algorithm)` dispatch; missing crop constraint raises before SQL is built.
4. Replace the old chorizon and cocropyld branches in the dynamic builders; delete dead code.
5. Tests: horizon clipping at 0 and 100 cm, horizon fully below 100 excluded, null horizon handling; crop filter present, nulls-as-zero arithmetic, mixed-unit detection, missing/invalid crop rejected.

**Constraints:** no `get_productivity_ratings` changes yet.

**Grep anchors:** `chorizon`, `cocropyld`, `cropname` within `build_dynamic_sdv_query`.

**Reference implementations:** 39.3.1 templates.

**Acceptance:** targeted tests green (`tests/test_sdv_strategies.py tests/test_sda_client.py`); offline suite at least baseline; ruff clean.

**Escalate when:** Method research semantics for Weighted Sum or nulls-as-zero are contradicted by SDA evidence encountered while testing.

### 39.5.1 - One engine: selectors, provenance, caveats, template retirement

**Files in scope**

- Must edit: `src/fpac_soil_mcp/sda_client.py`, `tests/test_sda_client.py`, `tests/test_sdv_contract.py`
- Can create: `tests/fixtures/sdv_contract_cases.json`, `planning/tasks/39.5.1.todo.md`

**Depends on:** 39.4.1.

**Specification:**

1. Route `get_productivity_ratings` and `get_county_max_productivity_rating` through `resolve_sdv_spec` for both `index_type` selectors and `attribute_meta` (plus new optional `constraints`); public method signatures stay backward compatible.
2. Each per-mukey result keeps existing keys and adds `sdv_provenance` (D8 structured record, including `registry_version`). `productivity_rating_source` = `spec.provenance_id` for every path (removes `SDA:SDVATTRIBUTE`, H7).
3. Add a caveat catalog constant (`SDV_CAVEATS`) with fixed strings: method caveat per algorithm (e.g. Dominant Condition value-as-class), unrated/sentinel, mixed yield units, AWS fixed depth 0-100 cm, crop-specific yield. Results carry the applicable caveats in a deterministic order.
4. Parity: before deleting templates, add a parity test that runs old `SQL_PRODUCTIVITY_*` and new builders against the same mocked SDA responses for NCCPI, CSR2, CPI (rating and county max) and asserts identical outputs. Then delete `SQL_PRODUCTIVITY_*` and `SQL_PRODUCTIVITY_COUNTY_MAX_*`; keep the parity expectations as frozen expected values in `tests/fixtures/sdv_contract_cases.json`.
5. Golden contract cases in `tests/fixtures/sdv_contract_cases.json`, one per registry record: input record (from `sdv_attribute_records.json` by name) plus constraints, expected normalized SQL fingerprint (whitespace-collapsed SHA-256), mocked SDA rows, expected value(s), `productivity_rating_source`, `sdv_provenance`, caveats. Test in `tests/test_sdv_contract.py` asserts all four outputs per case (exit criterion).
6. Update `PRODUCTIVITY_PROVENANCE` / `PRODUCTIVITY_SEMANTICS` to be derived from the registry (names stay importable).
7. Add the `sda_client.py` module docstring paragraph pointing to `docs/sdv-metadata-contract.md`.
8. Ad hoc live run (not committed) of Storie CA077 county max and the 5 sample mukeys; record old vs new in STATE_39.

**Constraints:** no edits to `polygon_analysis.py`, `corridor_analysis.py`, `lesa.py`, `tools/`, `models.py`.

**Grep anchors:** `def get_productivity_ratings`, `def get_county_max_productivity_rating`, `productivity_rating_source = "SDA:SDVATTRIBUTE"`, `SQL_PRODUCTIVITY_`.

**Reference implementations:** current `get_productivity_ratings` result dict construction (L1260-L1330).

**Acceptance:** `uv run --frozen pytest -q -p no:cacheprovider -m "not live_network"` green and at least baseline; `grep -n "SQL_PRODUCTIVITY_\|SDA:SDVATTRIBUTE" src/` empty; ruff clean; STATE_39 has the Storie comparison.

**Escalate when:** any NCCPI/CSR2/CPI parity difference; any polygon/corridor/LESA test change needed beyond Storie expectations.

### STOP B

Orchestrator presents the Storie old-vs-new values to the user. Continue only on explicit approval.

### 39.6.1 - Corridor provenance and sentinel dedupe

**Files in scope**

- Must edit: `src/fpac_soil_mcp/corridor_analysis.py`, `tests/test_corridor_analysis.py`
- Can create: `planning/tasks/39.6.1.todo.md`

**Depends on:** STOP B.

**Specification:** replace `_UNRATED_SENTINELS`, `_INDEX_SENTINELS`, `_INDEX_SOURCES` (L59-L71) with values from `sda_client` (`PRODUCTIVITY_SEMANTICS` / `PRODUCTIVITY_PROVENANCE` or registry). Fallback source IDs become the D8 IDs (H9). Add a test that the corridor fallback for each selector equals the registry provenance ID.

**Constraints:** no behavior change other than fallback source strings.

**Grep anchors:** `_INDEX_SOURCES`, `_INDEX_SENTINELS`, `_NCCPI_RULE`.

**Acceptance:** `uv run --frozen pytest -q -p no:cacheprovider tests/test_corridor_analysis.py tests/test_phase3_contracts.py` green; offline suite at least baseline; ruff clean.

**Escalate when:** a public corridor payload test expects the old drifted IDs.

### 39.6.2 - Contract doc, ADR 0014, ADR 0008 amendment, links

**Files in scope**

- Must edit: `docs/decisions/0008-nccpi-validated-public-index-with-extensible-sdv-routing.md`, `docs/decisions/README.md`, `AGENTS.md`, `README.md`
- Can create: `docs/sdv-metadata-contract.md`, `docs/decisions/0014-registry-validated-sdv-metadata-contract.md`, `planning/tasks/39.6.2.todo.md`

**Depends on:** STOP B.

**Specification:**

1. `docs/sdv-metadata-contract.md` sections:
   - Purpose and scope (internal contract, D1)
   - Required `sdvattribute` fields (table of `SDV_CONTRACT_FIELDS`, meaning, how the engine uses each)
   - Selection: fixed selectors vs explicit metadata selection (D9)
   - Validation: two gates and error messages (D2)
   - Passing into the engine: `resolve_sdv_spec`, constraints
   - Per-table behavior for `cointerp`, `chorizon`, `cocropyld`, `component`, `mapunit` (method, value column, weighting, sentinels, nulls, depth, crop/units)
   - Provenance (IDs and structured record, D8)
   - Caveats catalog
   - Registry entries (six-row table)
   - Adding a record (checklist: live capture, fixture, golden case, live benchmark)
   - Unsupported methods and deferrals
2. ADR 0014 in the repo ADR format (front matter like ADR 0008), recording D2, D4, D5, D8, D9, source context `EXECUTION_PLAN_39`, linking the contract doc.
3. ADR 0008: a dated `### Amendment (2026-10-27, EP39)` section: Storie aggregation now follows SDV Dominant Condition; generic routing is governed by ADR 0014; status stays Accepted; no other text rewritten.
4. `docs/decisions/README.md`: add the 0014 row; note the 0008 amendment.
5. `AGENTS.md`: one link line to the contract doc in the existing references/find-things area.
6. `README.md`: one sentence in the generic productivity contract bullet (L116) stating Storie uses the SDV Dominant Condition method.

**Constraints:** documentation only; values cited must match `sda_client.py` and STATE_39.

**Grep anchors:** `## Validation & Compliance` (ADR 0008), `Generic productivity contract` (README), `0013` (decisions README).

**Reference implementations:** ADR 0008 and ADR 0013 format; `planning/SDV_STATE_INDEX_RESEARCH.md` record tables.

**Acceptance:** an ad hoc check that every `SDV_CONTRACT_FIELDS` entry, every registry `provenance_id`, and every `SDV_CAVEATS` key appears in the contract doc (script output recorded); links resolve to existing paths; `git diff --stat` shows only in-scope files.

**Escalate when:** documentation would have to describe behavior that differs from code.

### 39.7.1 - Live benchmarks for all six records

**Files in scope**

- Must edit: `tests/test_live_sda.py`, `tests/fixtures/sdv_contract_cases.json` (add `live_benchmark` blocks only)
- Can create: `planning/tasks/39.7.1.todo.md`

**Depends on:** 39.6.1, 39.6.2.

**Specification:** add `live_network` tests:

- One per registry record: live record still validates (drift guard); county max and 3 sample mukeys within recorded tolerance.
- Storie CA077 new Dominant Condition value; update existing Storie live expectations.
- AWS 0-100 vs `muaggatt.aws0100wta` within D11 threshold.
- Corn (Bu) IL019 yields; mixed-unit map units marked unrated.
- NCCPI/CSR2/CPI unchanged versus 39.1.1 values.

**Constraints:** no `src/` edits.

**Grep anchors:** `def test_live_storie_county_max_california`, `def test_live_csr2_county_max_iowa`.

**Acceptance:** `uv run --frozen pytest -q -p no:cacheprovider -m live_network tests/test_live_sda.py` green; offline suite unaffected.

**Escalate when:** live values fall outside the 39.1.1 tolerances.

### 39.8.1 - Two-axis review, full validation, final report

**Files in scope:** `planning/STATE_39.md`; fixes to any W2-W7 file only when a check fails.

**Depends on:** 39.7.1.

**Specification:**

1. Spec axis: every Goal bullet and D1-D11 traces to code, tests, or docs; record a trace table.
2. Standards axis: ADR 0002 (no caller strings in SQL), ADR 0008 boundary (routing in `sda_client.py`), ADR 0011 (live opt-in), conventions in `AGENTS.md`.
3. Run `make check` and the full live suite; record counts.
4. Confirm public surface unchanged: `git diff origin/main...HEAD --stat -- src/fpac_soil_mcp/tools manifest.yaml server.json src/fpac_soil_mcp/models.py` empty.
5. Exit-criterion evidence: list each golden case and its four asserted outputs.

**Acceptance:** STATE_39 final report complete; all checks green; no ESCALATE open.

**Escalate when:** any check fails twice for the same reason.
