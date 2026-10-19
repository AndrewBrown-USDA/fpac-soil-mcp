# PR Review Fixes — Orchestration 27 (feat/phase-4-part-2-sdv-routing)

You are working on the `fpac-soil-mcp` repository, branch `feat/phase-4-part-2-sdv-routing`.
This branch adds CSR2, CPI, and Storie as validated public productivity indexes alongside
the existing NCCPI. A code review identified the issues below. Fix them all in a single
commit appended to this branch.

## Repository conventions

- Entry points: `src/fpac_soil_mcp/app.py`, `main.py`
- Tests: `uv run pytest -m "not live_network"` (offline), `uv run pytest -m live_network` (live)
- Lint: `uv run ruff check .` then `uv run ruff format .`
- Conventional commits, domain scopes (e.g. `fix(sda):`, `test(sda):`). **No wave numbers in commits.**
- Existing 59 EXE002 lint warnings are pre-existing — ignore them.

## Green baseline (before fixes)

- 317 passed, 1 skipped, 21 deselected (offline)
- 21 passed (live)

---

## BUGS (correctness — must fix)

### B1. STORIE missing from polygon_analysis.py guard

**File:** `src/fpac_soil_mcp/polygon_analysis.py` ~line 110  
**Problem:** The guard allows `NCCPI, CSR2, CPI` but NOT `STORIE`. The error message
claims storie is supported. Passing `productivity_index="storie"` to `analyze_polygon`
will raise a confusing ValueError even though the downstream SDA client handles it fine.  
**Fix:** Add `ProductivityIndexType.STORIE` to the guard tuple.

### B2. STORIE missing from corridor_analysis.py guard

**File:** `src/fpac_soil_mcp/corridor_analysis.py` ~line 156  
**Problem:** Same as B1 — guard allows `NCCPI, CSR2, CPI` but not `STORIE`.  
**Fix:** Add `ProductivityIndexType.STORIE` to the guard tuple.

### B3. Rounding inconsistency in `get_productivity_ratings`

**File:** `src/fpac_soil_mcp/sda_client.py` ~line 1200  
**Problem:** The rating rounding in `get_productivity_ratings` uses:
```python
numeric_rating = round(r_val, 3 if norm_idx == "nccpi" else 2)
```
This rounds CSR2 and CPI to 2 decimals, but they should round to 0 (integer scale).
Storie should round to 3 decimals (like NCCPI), but this rounds it to 2.
Meanwhile, `get_county_max_productivity_rating` (~line 1078) correctly uses:
```python
if idx.startswith("nccpi") or idx in ("storie",):
    return round(val_float, 3)
elif idx in ("csr2", "cpi"):
    return round(val_float, 0)
else:
    return round(val_float, 2)
```
**Fix:** Replace the single-line rounding at ~line 1200 with the same per-index logic
used in `get_county_max_productivity_rating`. Use `norm_idx` (not `idx`) since that's
the variable in scope. The cleanest approach is to extract a helper like
`_round_for_index(value, norm_idx)` and call it from both places.

### B4. Sentinel filtering inconsistency: `<= 0` vs `< 0`

**File:** `src/fpac_soil_mcp/sda_client.py`  
**Problem:** County max (~line 1076) rejects `val_float <= 0` (zero is excluded),
but ratings (~line 1193) only rejects `r_val < 0` (zero is allowed). A zero rating
is meaningless for all four indexes. Make them consistent.  
**Fix:** Use `<= 0` in both places (match county max behavior).

### B5. CPI SQL templates missing `compkind != 'miscellaneous area'` filter

**File:** `src/fpac_soil_mcp/sda_client.py`  
**Problem:** `SQL_PRODUCTIVITY_CPI` (~line 279) and `SQL_PRODUCTIVITY_COUNTY_MAX_CPI`
(~line 299) join the `component` table but don't exclude miscellaneous area components.
The NCCPI templates DO filter this (`AND c.compkind != 'miscellaneous area'`).
Without the filter, CPI averages can be diluted by water/rubble/rock components
that happen to have a cropprodindex value.  
**Fix:** Add `AND c.compkind != 'miscellaneous area'` to the WHERE clause of both
`SQL_PRODUCTIVITY_CPI` and `SQL_PRODUCTIVITY_COUNTY_MAX_CPI`.

### B6. Live test misnamed: calls county_max but named "ratings"

**File:** `tests/test_live_sda.py` ~line 179  
**Problem:** `test_live_cpi_productivity_ratings_minnesota` actually calls
`get_county_max_productivity_rating`, not `get_productivity_ratings`. The name
is misleading and there is no actual live CPI ratings test.  
**Fix:** Rename to `test_live_cpi_county_max_minnesota`. Add a separate
`test_live_cpi_productivity_ratings_minnesota` that actually calls
`get_productivity_ratings` with a real MN mukey (follow the pattern of
`test_live_csr2_productivity_ratings_iowa` and `test_live_storie_ratings_california`).

---

## DESIGN / DRY (maintainability — should fix)

### D1. Alias tuples duplicated between two dispatch methods

**File:** `src/fpac_soil_mcp/sda_client.py`  
**Problem:** The same alias tuples for CSR2, CPI, and Storie appear in both
`get_county_max_productivity_rating` and `get_productivity_ratings`. If an alias
is added to one but not the other, they'll silently diverge.  
**Fix:** Extract module-level constants:
```python
_NCCPI_ALIASES = frozenset({"nccpi", "nccpi_v3", "national commodity crop productivity index"})
_CSR2_ALIASES = frozenset({"csr2", "iowa corn suitability rating csr2"})
_CPI_ALIASES = frozenset({"cpi", "crop productivity index"})
_STORIE_ALIASES = frozenset({"storie", "california revised storie index", "agr - california revised storie index (ca)"})
```
Then use `idx in _CSR2_ALIASES` in both methods.

### D2. Guard tuple duplicated in 5 places

**Files:** `polygon_analysis.py`, `corridor_analysis.py`, `tools/soil_tools.py` (3x)  
**Problem:** The `not in (NCCPI, CSR2, CPI, STORIE)` check is copy-pasted 5 times.
Adding a 5th index means updating all 5 (and the bug in B1/B2 shows this already failed).  
**Fix:** Add a set or tuple to `models.py` next to the enum:
```python
VALIDATED_PRODUCTIVITY_INDEXES: frozenset[ProductivityIndexType] = frozenset(ProductivityIndexType)
```
Or if you want to keep it selective (not all enum members are necessarily validated),
define it as an explicit frozenset. Then import it and use
`if idx_enum not in VALIDATED_PRODUCTIVITY_INDEXES:` in all 5 guard sites.

### D3. Error message string duplicated 8 times

**Files:** `sda_client.py` (2x), `polygon_analysis.py`, `corridor_analysis.py`,
`tools/soil_tools.py` (3x), `lesa.py`  
**Problem:** `"Supported fixed selectors: 'nccpi', 'csr2', 'cpi', 'storie'."` is
hardcoded in 8 places.  
**Fix:** Define it once (e.g. in `models.py` or `constants.py`) and import it.
Or dynamically build it from the enum/frozenset:
```python
SUPPORTED_INDEX_MSG = f"Supported fixed selectors: {', '.join(repr(m.value.lower()) for m in ProductivityIndexType)}."
```

### D4. `idx in ("storie",)` — single-element tuple is awkward

**File:** `src/fpac_soil_mcp/sda_client.py` ~line 1078  
**Problem:** `idx in ("storie",)` is equivalent to `idx == "storie"`. The tuple
form suggests there should be more items.  
**Fix:** If you extract rounding into a helper (B3), this becomes moot. Otherwise,
use `idx == "storie"` or `idx in _STORIE_ALIASES`.

### D5. CSR2 `rated_pct` is synthetic — deserves a comment

**File:** `src/fpac_soil_mcp/sda_client.py`, `SQL_PRODUCTIVITY_CSR2` template  
**Problem:** CSR2 is a mapunit-level column (not component-weighted), so `rated_pct`
is always 100% or 0%. The CASE expression is correct but conceptually different
from NCCPI/CPI's component-weighted rated_pct.  
**Fix:** Add a SQL comment explaining this is mapunit-level (no component weighting).

---

## TEST GAPS (should fix)

### T1. No unit test for per-index rounding in `get_productivity_ratings`

**File:** `tests/test_sda_client.py`  
**Problem:** Tests verify result values match mocked data but don't explicitly verify
that CSR2/CPI round to 0 decimals and Storie rounds to 3 in `get_productivity_ratings`.
The bug in B3 went undetected because mock data happened to already be rounded.  
**Fix:** Add parametrized tests with unrounded mock values (e.g. 92.456 for CSR2,
0.87654 for Storie) and assert the returned `numeric_rating` has correct precision.

### T2. No test that polygon/corridor accept STORIE

**File:** `tests/test_polygon_analysis.py`  
**Problem:** The parametrize was narrowed from `["csr2", "cpi", "storie", "custom"]`
to just `["custom"]` for the rejection test, but there's no positive test that
CSR2/CPI/STORIE pass the guard. The bug in B1/B2 went undetected because of this gap.  
**Fix:** Add a parametrized test that all 4 valid indexes are accepted by the polygon
and corridor guards (mock the SDA client, just verify no ValueError is raised at the
guard). Add corresponding test for corridor.

### T3. No live CPI ratings test (only county max)

**File:** `tests/test_live_sda.py`  
**Problem:** The misnamed test (B6) means there's no live test of actual CPI
`get_productivity_ratings` with real mukeys.  
**Fix:** Covered by B6 — the new test should call `get_productivity_ratings` with
a real MN mukey and verify index_type/provenance/range.

---

## DOCUMENTATION (should fix)

### DOC1. ADR 0008 references wave numbers

**File:** `docs/decisions/0008-nccpi-validated-public-index-with-extensible-sdv-routing.md`  
**Problem:** Lines 100 and 106 say "EP27 wave 4" and "EP27 wave 5". Wave numbers
are internal orchestration details that should not appear in documentation.  
**Fix:** Replace "EP27 wave 4 (2026-10-15)" with "EP27 (2026-10-15)" and merge
the two EP27 entries into one (or use "EP27 subsequently" for the second).

### DOC2. ADR 0008 has stale/incremental line references

**File:** `docs/decisions/0008-nccpi-validated-public-index-with-extensible-sdv-routing.md`  
**Problem:** The appendix lists three separate EP27 entries showing the enum
growing from `318-322` to `318-323` to `318-324`. These are written as if recording
history, but they're confusing in the final state — the reader doesn't need to see
the intermediate line ranges.  
**Fix:** Consolidate the three EP27 entries into one block that records the final
state: all 4 indexes validated, line range `318-324`, with all 4 benchmark fixtures.

---

## Execution checklist

1. Apply all fixes above
2. `uv run ruff format .`
3. `uv run ruff check .` (only pre-existing EXE002 expected)
4. `uv run pytest -m "not live_network" --tb=short -q` — expect >= 317 passed (likely more from new tests)
5. `uv run pytest -m live_network --tb=short -q -v` — expect >= 21 passed (likely 22+ from new CPI live test)
6. `git add -A && git commit -m "fix(sda): address PR review — guard consistency, rounding, DRY refactors, test gaps"`
7. `git push origin feat/phase-4-part-2-sdv-routing`

## Priority order

If you need to split this into phases:
- **Phase 1 (blocking bugs):** B1, B2, B3, B4, B5 — these are correctness issues
- **Phase 2 (test gaps):** T1, T2, B6/T3 — cover the bugs with tests
- **Phase 3 (DRY refactors):** D1, D2, D3, D4, D5 — maintainability
- **Phase 4 (docs):** DOC1, DOC2 — cleanup

All phases can be done in a single commit if you prefer.
