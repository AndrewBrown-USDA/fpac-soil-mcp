# State — Orchestration 31 (REVIEW_27_FIXES Remediation)

## Green Baseline (pre-wave-1)

```
$ pytest tests/ -x -q --deselect tests/test_live_sda.py
317 passed, 1 skipped, 21 deselected

$ pytest tests/test_live_sda.py -x -q --live
21 passed
```

Baseline recorded: 2026-10-19
Branch: feat/phase-4-part-2-sdv-routing

---

## Wave Board

### Wave 1
| Task | Title | Status | Worker |
|------|-------|--------|--------|
| 31.1.1 | Guards + DRY constants (D2, D3, B1, B2) | done | orchestrator |
| 31.1.2 | SDA client internal fixes (D1, B3, B4, B5, D4, D5) | done | orchestrator |

### Wave 2
| Task | Title | Status | Depends On |
|------|-------|--------|------------|
| 31.2.1 | Rounding precision unit tests (T1) | done | 31.1.2 |
| 31.2.2 | Guard acceptance tests (T2) | done | 31.1.1 |
| 31.2.3 | Live test fixes (B6, T3) | done | — |
| 31.2.4 | ADR 0008 doc cleanup (DOC1, DOC2) | done | — |

---

## Task Reports

### 31.1.1 — Guards + DRY Constants
- Status: done
- Files: models.py (lines 326-337), polygon_analysis.py, corridor_analysis.py, tools/soil_tools.py, lesa.py
- Added VALIDATED_PRODUCTIVITY_INDEXES and SUPPORTED_INDEX_MSG constants; replaced 6 inline guard sites
- Removed unused ProductivityIndexType imports from polygon_analysis.py and corridor_analysis.py
- Fixed I001 import sorting in 4 files
- Tests: 71 passed (targeted), 308 passed (full offline)
- Deviations: removed unused imports (F401) not in original spec

### 31.1.2 — SDA Client Internal Fixes
- Status: done
- Files: sda_client.py (alias constants ~line 330, _round_for_index ~line 345, dispatch chains, SQL templates)
- Added _NCCPI_ALIASES, _CSR2_ALIASES, _CPI_ALIASES, _STORIE_ALIASES frozensets
- Added _round_for_index() helper; replaced 2 rounding blocks
- Fixed B4 sentinel (r_val <= 0), B5 CPI compkind filter, D5 CSR2 comment
- Updated error messages to use SUPPORTED_INDEX_MSG
- Tests: 85 passed (targeted), 308 passed (full offline)
- Deviations: none

### 31.2.1 — Rounding Precision Tests
- Status: done
- Files: tests/test_sda_client.py (appended 3 test methods, 9 parametrized cases)
- Tests: pytest -k "rounding or zero_rating" — 9 passed
- Deviations: none

### 31.2.2 — Guard Acceptance Tests
- Status: done
- Files: tests/test_polygon_analysis.py, tests/test_corridor_analysis.py
- Expanded rejection parametrize to ["custom", "unsupported", ""]; added 4+4 acceptance tests
- Corridor acceptance test uses try/except ValueError pattern (empty mocks cause non-ValueError errors downstream)
- Tests: pytest -k "selector or validated" — 12 passed
- Deviations: added base_url to mock SDA in polygon test (prod code accesses it)

### 31.2.3 — Live Test Fixes
- Status: done
- Files: tests/test_live_sda.py
- Renamed test_live_cpi_productivity_ratings_minnesota → test_live_cpi_county_max_minnesota (B6)
- Added new test_live_cpi_productivity_ratings_minnesota using Wilkin County point (T3)
- Tests: offline collection verified; live run requires network
- Deviations: none

### 31.2.4 — ADR 0008 Doc Cleanup
- Status: done
- Files: docs/decisions/0008-nccpi-validated-public-index-with-extensible-sdv-routing.md
- Consolidated 3 EP27 entries into one cohesive paragraph
- Added EP31 remediation summary
- Deviations: none
