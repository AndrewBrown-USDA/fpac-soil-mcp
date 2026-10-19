# Execution Plan 28 — REVIEW_27_FIXES Code-Review Remediation

## Goal & Scope

**Goal:** Fix all findings from `planning/REVIEW_27_FIXES.md` on the
`feat/phase-4-part-2-sdv-routing` branch — 6 correctness bugs (B1-B6),
5 DRY/maintainability refactors (D1-D5), 3 test-gap additions (T1-T3),
and 2 documentation cleanups (DOC1-DOC2) — then deliver a green, PR-ready
branch.

**In scope:**
- B1-B6: Storie guard omission, rounding precision, sentinel zero, CPI
  compkind filter, live-test misname
- D1-D5: Alias constants, guard frozenset, error-message constant,
  storie tuple syntax, CSR2 comment
- T1-T3: Rounding-precision tests, guard acceptance tests, missing CPI
  live ratings test
- DOC1-DOC2: ADR 0008 consolidation and line-reference updates

**Out of scope:**
- New productivity index additions beyond the existing 4
- PR merge to main, production deployment sync, shared-prod pull
- Eval harness updates (eval/ directory)
- Any changes to the Databricks App deployment

**Verbatim constraints from the review:**
- "All phases can be done in a single commit if you prefer" — overridden
  by user decision to use one commit per task.
- "Ignore EXE002 lint suppressions — they pre-date this review."

---

## Decision Log

| # | Date | Decision | Rationale |
|---|------|----------|-----------|
| 1 | 2026-10-19 | `VALIDATED_PRODUCTIVITY_INDEXES = frozenset(ProductivityIndexType)` (auto-all) | User: "I do not want to have to change a bunch of things and would like to provide options for other productivity indices easily in the future." |
| 2 | 2026-10-19 | One conventional commit per task (6 total) | Wave standard; bisectable history, clean reverts. |
| 3 | 2026-10-19 | `SUPPORTED_INDEX_MSG` dynamically generated from enum values | Stays in sync with auto-all; adding an enum member auto-updates the error message. |
| 4 | 2026-10-19 | `_round_for_index()` as module-level private function in sda_client.py | Pure logic, no instance state; matches codebase convention for SQL template helpers. |
| 5 | 2026-10-19 | Alias frozensets as private module-level constants in sda_client.py | Implementation detail of dispatch; not part of public API. |

---

## Wave Table

| Wave | Task ID | Title | Depends On | Files In Scope |
|------|---------|-------|------------|----------------|
| 1 | 28.1.1 | Guards + DRY constants (D2, D3, B1, B2) | — | models.py, polygon_analysis.py, corridor_analysis.py, tools/soil_tools.py, lesa.py |
| 1 | 28.1.2 | SDA client internal fixes (D1, B3, B4, B5, D4, D5) | — | sda_client.py |
| 2 | 28.2.1 | Rounding precision unit tests (T1) | 28.1.2 | tests/test_sda_client.py |
| 2 | 28.2.2 | Guard acceptance tests (T2) | 28.1.1 | tests/test_polygon_analysis.py, tests/test_corridor_analysis.py |
| 2 | 28.2.3 | Live test fixes (B6, T3) | — | tests/test_live_sda.py |
| 2 | 28.2.4 | ADR 0008 doc cleanup (DOC1, DOC2) | — | docs/decisions/0008-*.md |

File-disjointness: Wave 1 tasks share no files (28.1.1 touches 5 src files;
28.1.2 touches sda_client.py only). Wave 2 tasks each touch distinct test/doc
files.

---

## Hazard Notes

- **sda_client.py is 1230 lines.** Workers must use grep anchors, not
  whole-file reads. Key landmarks: SQL templates (lines 195-314),
  `ALLOWED_SDV_TABLES` (line 307), `get_county_max_productivity_rating`
  dispatch (lines 1039-1065), rounding (lines 1072-1083),
  `get_productivity_ratings` dispatch (lines 1117-1153), rating rounding
  (lines 1190-1203).
- **tools/soil_tools.py is 719 lines** with 3 identical guard blocks at
  lines 203, 409, 536. All three already include STORIE — the refactor
  replaces inline tuples with the frozenset import.
- **lesa.py `_normalize_productivity_index` (line 68)** is the canonical
  normalizer imported by polygon_analysis.py and corridor_analysis.py
  (the latter as `_normalize_fixed_productivity_index` alias at line 39).
  The error message there (line 77-78) must also use the new constant.
- **Existing test baseline:** 317 passed, 1 skipped, 21 deselected
  (offline); 21 passed (live). No regressions permitted.

---

## Task Specs

### 28.1.1 — Guards + DRY Constants (D2, D3, B1, B2)

**Repo:** fpac-soil-mcp  
**Branch:** feat/phase-4-part-2-sdv-routing  
**Files must edit:**
- `src/fpac_soil_mcp/models.py`
- `src/fpac_soil_mcp/polygon_analysis.py`
- `src/fpac_soil_mcp/corridor_analysis.py`
- `src/fpac_soil_mcp/tools/soil_tools.py`
- `src/fpac_soil_mcp/lesa.py`

**Can create:** none  
**Do not touch:** sda_client.py, any test file, any doc file

**Spec:**
1. In `models.py`, after the `ProductivityIndexType` enum (line 324),
   add:
   ```python
   VALIDATED_PRODUCTIVITY_INDEXES: frozenset[ProductivityIndexType] = frozenset(ProductivityIndexType)
   ```
2. In `models.py`, add a dynamically-generated error message constant:
   ```python
   SUPPORTED_INDEX_MSG: str = (
       "Supported fixed selectors: "
       + ", ".join(f"'{v.value.lower()}'" for v in ProductivityIndexType)
       + "."
   )
   ```
3. Export both from `models.py` (add to `__all__` if one exists, or
   ensure they are importable).
4. In `polygon_analysis.py` (line 110-118): replace the inline tuple
   guard with `if idx_enum not in VALIDATED_PRODUCTIVITY_INDEXES:` and
   update the error message to use `SUPPORTED_INDEX_MSG`. Add import of
   both constants from models. **This fixes B1** (Storie was missing).
5. In `corridor_analysis.py` (line 156-164): same replacement.
   **This fixes B2.** Import `VALIDATED_PRODUCTIVITY_INDEXES` and
   `SUPPORTED_INDEX_MSG` from models.
6. In `tools/soil_tools.py` (lines 203-211, 409-417, 536-544): replace
   all three inline tuple guards + error messages with the frozenset
   constant and message constant. Add imports from models.
7. In `lesa.py` (lines 76-78): replace the error message string literal
   in `_normalize_productivity_index` with `SUPPORTED_INDEX_MSG`.
   Import it from models.

**Grep anchors:**
- models.py: `class ProductivityIndexType` (~line 318)
- polygon_analysis.py: `idx_enum not in` (~line 110)
- corridor_analysis.py: `normalized_index not in` (~line 156)
- soil_tools.py: `normalized_productivity_index not in` (~lines 203, 409, 536)
- lesa.py: `Supported fixed selectors` (~line 78)

**Reference implementation:** The existing guard pattern at
tools/soil_tools.py:203-211 (already has all 4 indexes) — but replace
with frozenset membership.

**Acceptance:**
```bash
pytest tests/test_polygon_analysis.py tests/test_corridor_analysis.py tests/test_lesa.py -x -q
```
All existing tests pass; the `test_unsupported_selector_rejected_before_sda`
tests (polygon line 229, corridor line 508) still reject `"custom"`.

**Commit:** `fix(models): extract VALIDATED_PRODUCTIVITY_INDEXES and SUPPORTED_INDEX_MSG constants`

---

### 28.1.2 — SDA Client Internal Fixes (D1, B3, B4, B5, D4, D5)

**Repo:** fpac-soil-mcp  
**Branch:** feat/phase-4-part-2-sdv-routing  
**Files must edit:**
- `src/fpac_soil_mcp/sda_client.py`

**Can create:** none  
**Do not touch:** models.py, polygon_analysis.py, corridor_analysis.py,
tools/soil_tools.py, lesa.py, any test file

**Spec:**
1. **D1 — Alias constants.** Near the top of sda_client.py (after
   `ALLOWED_SDV_TABLES` at line 314), add module-level frozensets:
   ```python
   _NCCPI_ALIASES = frozenset({"nccpi", "nccpi_v3", "national commodity crop productivity index"})
   _CSR2_ALIASES = frozenset({"csr2", "iowa corn suitability rating csr2"})
   _CPI_ALIASES = frozenset({"cpi", "crop productivity index"})
   _STORIE_ALIASES = frozenset({
       "storie", "california revised storie index",
       "agr - california revised storie index (ca)",
   })
   ```
2. Update `get_county_max_productivity_rating` dispatch chain
   (lines 1042-1059): replace inline string tuples with the alias
   constants (e.g. `elif idx in _CSR2_ALIASES:`).
3. Update `get_productivity_ratings` dispatch chain (lines 1122-1147):
   same replacement.
4. **B3 — Rounding helper.** Add a private helper near the alias
   constants:
   ```python
   def _round_for_index(value: float, norm_idx: str) -> float:
       """Round a productivity rating to the precision appropriate for its index type."""
       if norm_idx in ("nccpi", "storie"):
           return round(value, 3)
       elif norm_idx in ("csr2", "cpi"):
           return round(value, 0)
       return round(value, 2)
   ```
5. Replace the rounding logic in `get_county_max_productivity_rating`
   (lines 1078-1083) with `return _round_for_index(val_float, idx)`.
   **This also fixes D4** (the `idx in ("storie",)` singleton becomes
   moot).
6. Replace the rounding logic in `get_productivity_ratings`
   (line 1200) with:
   `numeric_rating = _round_for_index(r_val, norm_idx)`.
   **This fixes B3** (CSR2/CPI now round to 0 decimals, Storie to 3).
7. **B4 — Sentinel zero.** In `get_productivity_ratings` (line 1193),
   change `r_val < 0` to `r_val <= 0` so zero is treated as unrated,
   consistent with `get_county_max_productivity_rating` (line 1076
   `val_float <= 0`).
8. **B5 — CPI compkind filter.** Add
   `AND c.compkind != 'miscellaneous area'` to `SQL_PRODUCTIVITY_CPI`
   (insert after line 293, before `GROUP BY`) and
   `SQL_PRODUCTIVITY_COUNTY_MAX_CPI` (insert after line 303, before
   the closing `"""`).
9. **D3 (partial) — sda_client error messages.** Import
   `SUPPORTED_INDEX_MSG` from models. Update the two error messages in
   `get_county_max_productivity_rating` (line 1062-1064) and
   `get_productivity_ratings` (line 1150-1152) to use
   `f"{SUPPORTED_INDEX_MSG}; explicit attribute metadata is required for custom SDV queries."`
   (these have a different suffix from the other 6 sites, which task
   28.1.1 handles).
10. **D5 — CSR2 comment.** Add a one-line comment above
   `SQL_PRODUCTIVITY_CSR2` (line 255) explaining:
   `# CSR2 is a mapunit-level attribute (not component-aggregated); rated_pct is synthetic.`

**Grep anchors:**
- `ALLOWED_SDV_TABLES` (~line 307) — insert alias constants after
- `def get_county_max_productivity_rating` (~line 1014)
- `idx in ("nccpi", "nccpi_v3"` (~lines 1042, 1122) — dispatch chains
- `round(val_float, 3)` (~line 1079) — county_max rounding
- `round(r_val, 3 if norm_idx` (~line 1200) — ratings rounding
- `r_val < 0` (~line 1193) — sentinel zero bug
- `SQL_PRODUCTIVITY_CPI` (~line 278) — missing compkind filter
- `SQL_PRODUCTIVITY_COUNTY_MAX_CPI` (~line 297) — missing compkind filter
- `SQL_PRODUCTIVITY_CSR2` (~line 255) — needs comment

**Reference implementation:** The existing `SQL_PRODUCTIVITY_NCCPI` CTE
(line 226: `AND c.compkind != 'miscellaneous area'`) is the pattern for
B5. The existing `SQL_PRODUCTIVITY_COUNTY_MAX_NCCPI` (line 252:
`AND c.compkind != 'miscellaneous area'`) is the county-max pattern.

**Acceptance:**
```bash
pytest tests/test_sda_client.py -x -q
```
All existing 30+ SDA client tests pass. The existing CSR2/CPI/Storie
tests may now see slightly different rounding but use pre-rounded mock
data (92.0, 100.0, 0.95) so they remain stable.

**Commit:** `fix(sda): extract alias constants, rounding helper, sentinel and compkind fixes`

---

### Wave boundary: lint + full suite

After both wave-1 tasks are committed, the orchestrator runs:
```bash
ruff check . && ruff format --check .
pytest tests/ -x -q --deselect tests/test_live_sda.py
```
Expect 317 passed, 1 skipped, 21 deselected (no regressions).

---

### 28.2.1 — Rounding Precision Unit Tests (T1)

**Repo:** fpac-soil-mcp  
**Branch:** feat/phase-4-part-2-sdv-routing  
**Depends on:** 28.1.2  
**Files must edit:**
- `tests/test_sda_client.py`

**Can create:** none  
**Do not touch:** any src/ file

**Spec:**
1. Add a parametrized test `test_get_productivity_ratings_rounding_precision`
   that exercises `get_productivity_ratings` with mock data containing
   non-round values for each index type:
   - NCCPI: raw 0.82567 → expect `round(0.82567, 3)` = 0.826
   - CSR2: raw 92.456 → expect `round(92.456, 0)` = 92.0
   - CPI: raw 87.654 → expect `round(87.654, 0)` = 88.0
   - Storie: raw 0.95678 → expect `round(0.95678, 3)` = 0.957
   Use mock HTTP transport returning appropriate `Table` responses with
   the non-round values. Assert `numeric_rating` matches expected.
2. Add a parametrized test `test_get_county_max_rounding_precision`
   exercising `get_county_max_productivity_rating` similarly:
   - NCCPI: raw 0.99567 → expect 0.996
   - CSR2: raw 96.456 → expect 96.0
   - CPI: raw 100.789 → expect 101.0
   - Storie: raw 0.99512 → expect 0.995
3. Add a test `test_get_productivity_ratings_zero_rating_is_unrated`
   verifying that a raw rating of 0.0 yields `is_rated=False` (B4 fix).

**Grep anchors:**
- `class TestProductivityRatings` or `test_get_productivity_ratings_nccpi`
  (~line 505) — insert new tests nearby
- `test_get_county_max_productivity_rating_nccpi` (~line 466) — insert
  county-max rounding test nearby

**Reference implementation:** `test_get_productivity_ratings_csr2`
(line 798) — follow its mock transport + assertion pattern.

**Acceptance:**
```bash
pytest tests/test_sda_client.py -x -q -k "rounding or zero_rating"
```

**Commit:** `test(sda): add rounding precision and zero-sentinel tests`

---

### 28.2.2 — Guard Acceptance Tests (T2)

**Repo:** fpac-soil-mcp  
**Branch:** feat/phase-4-part-2-sdv-routing  
**Depends on:** 28.1.1  
**Files must edit:**
- `tests/test_polygon_analysis.py`
- `tests/test_corridor_analysis.py`

**Can create:** none  
**Do not touch:** any src/ file, test_sda_client.py, test_live_sda.py

**Spec:**
1. In `test_polygon_analysis.py`, expand the existing rejection test
   at line 229 (`@pytest.mark.parametrize("index", ["custom"])`) to also
   include `"unsupported"` and `""` as invalid selectors.
2. Add a new positive acceptance test
   `test_all_validated_selectors_accepted` parametrized over
   `("nccpi", "csr2", "cpi", "storie")` that verifies
   `analyze_polygon(GEOJSON, productivity_index=index)` does NOT raise
   `ValueError`. Use a mock SDA client similar to `_analyzer()` at
   line 27. The test only needs to assert "no ValueError" — the
   downstream SDA calls can return empty/mock data.
3. In `test_corridor_analysis.py`, add a corresponding positive test
   `test_corridor_all_validated_selectors_accepted` parametrized over
   the same 4 indexes. Use the existing mock pattern from
   `test_corridor_unsupported_selector_rejected_before_sda_lookup`
   (line 508). Assert no ValueError on entry.

**Grep anchors:**
- test_polygon_analysis.py: `@pytest.mark.parametrize("index", ["custom"])` (~line 229)
- test_corridor_analysis.py: `test_corridor_unsupported_selector_rejected_before_sda_lookup` (~line 508)

**Reference implementation:** The existing rejection tests at
polygon line 229 and corridor line 508.

**Acceptance:**
```bash
pytest tests/test_polygon_analysis.py tests/test_corridor_analysis.py -x -q -k "selector or validated"
```

**Commit:** `test(analysis): add guard acceptance tests for all validated selectors`

---

### 28.2.3 — Live Test Fixes (B6, T3)

**Repo:** fpac-soil-mcp  
**Branch:** feat/phase-4-part-2-sdv-routing  
**Depends on:** none  
**Files must edit:**
- `tests/test_live_sda.py`

**Can create:** none  
**Do not touch:** any src/ file, other test files

**Spec:**
1. **B6 — Rename.** Rename `test_live_cpi_productivity_ratings_minnesota`
   (line 179) to `test_live_cpi_county_max_minnesota`. The body calls
   `get_county_max_productivity_rating`, not `get_productivity_ratings`,
   so the name is misleading.
2. **T3 — New live CPI ratings test.** Add a new test method
   `test_live_cpi_productivity_ratings_minnesota` that:
   - Uses `get_by_point(latitude=46.28, longitude=-96.58)` to fetch a
     real Wilkin County (MN167) mukey (follow pattern of
     `test_live_csr2_productivity_ratings_iowa` at line 133).
   - Calls `get_productivity_ratings(mukeys=[test_mukey], index_type="cpi")`.
   - Asserts `len(results) == 1`, `index_type == "cpi"`,
     `productivity_rating_source == "SDA:COMPONENT_CROPPRODINDEX"`.
   - If `is_rated`, asserts `0 < numeric_rating <= 100`.

**Grep anchors:**
- `test_live_cpi_productivity_ratings_minnesota` (~line 179)
- `test_live_csr2_productivity_ratings_iowa` (~line 133) — pattern to follow
- `test_live_storie_ratings_california` (~line 246) — another pattern

**Reference implementation:** `test_live_csr2_productivity_ratings_iowa`
(line 133) and `test_live_storie_ratings_california` (line 246).

**Acceptance:**
```bash
pytest tests/test_live_sda.py -x -q -k "cpi" --live
```
(Requires network access to SDA endpoint.)

**Commit:** `test(live): rename CPI county-max test, add CPI ratings test`

---

### 28.2.4 — ADR 0008 Documentation Cleanup (DOC1, DOC2)

**Repo:** fpac-soil-mcp  
**Branch:** feat/phase-4-part-2-sdv-routing  
**Depends on:** none  
**Files must edit:**
- `docs/decisions/0008-nccpi-validated-public-index-with-extensible-sdv-routing.md`

**Can create:** none  
**Do not touch:** any src/ or test file

**Spec:**
1. **DOC1 — Consolidate entries.** Replace the three separate EP27 wave
   entries (lines 94-112: "EP27 (2026-10-15) validated and added CSR2",
   "EP27 wave 4", "EP27 wave 5") with a single cohesive paragraph:
   ```
   EP27 (2026-10-15 → 2026-10-19) validated and added all four
   state-specific productivity indexes as public contract members:
   * `ProductivityIndexType` enum: NCCPI, CSR2, CPI, STORIE
   * CSR2: `SDA:MAPUNIT_IACORNSR` — fixed SQL, IA169 max = 96.0
   * CPI: `SDA:COMPONENT_CROPPRODINDEX` — component-level, MN167 max = 100.0
   * Storie: `SDA:COINTERP_STORIE_CA` — reuses NCCPI cointerp template,
     CA077 max ≈ 0.995
   * Benchmark fixtures in `tests/fixtures/le_benchmarks.json`
   ```
2. **DOC2 — Update references.** Update the enum line references
   (e.g. `models.py:318-322`) to reflect the post-refactor state:
   mention `VALIDATED_PRODUCTIVITY_INDEXES` and the consolidated enum.
   Add a note about EP28 review-remediation fixes (guard constants,
   rounding precision, CPI compkind filter).

**Grep anchors:**
- `EP27 (2026-10-15) validated and added CSR2` (~line 94)
- `EP27 wave 4` (~line 100)
- `EP27 wave 5` (~line 106)

**Acceptance:** Visual review — no automated test. Verify markdown
renders correctly and line references are accurate.

**Commit:** `docs(adr-0008): consolidate EP27 entries, add EP28 review fixes`
