# State — Orchestration 28 (REVIEW_27_FIXES Remediation)

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
| 28.1.1 | Guards + DRY constants (D2, D3, B1, B2) | pending | — |
| 28.1.2 | SDA client internal fixes (D1, B3, B4, B5, D4, D5) | pending | — |

### Wave 2
| Task | Title | Status | Depends On |
|------|-------|--------|------------|
| 28.2.1 | Rounding precision unit tests (T1) | pending | 28.1.2 |
| 28.2.2 | Guard acceptance tests (T2) | pending | 28.1.1 |
| 28.2.3 | Live test fixes (B6, T3) | pending | — |
| 28.2.4 | ADR 0008 doc cleanup (DOC1, DOC2) | pending | — |

---

## Task Reports

(appended by workers as tasks complete)
