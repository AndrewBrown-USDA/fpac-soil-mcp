# SDV State Index Research — Orchestration 27, Task 27.1.1

**Date:** 2026-10-15
**Method:** Live SDA queries against sdvattribute catalog and actual data tables
**Source:** https://sdmdataaccess.nrcs.usda.gov/Tabular/post.rest

## Summary

| Index | Table | Column | Data Type | Scale | cointerp? | nasisrulename | County Max Query Pattern |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CSR2 | `mapunit` | `iacornsr` | Integer | 5-100 | No | n/a | `MAX(m.iacornsr)` with areasymbol filter |
| CPI | `component` | `cropprodindex` | Integer | 1-100 | No | n/a | `MAX(c.cropprodindex)` with areasymbol filter |
| Storie | `cointerp` | `interphr` | Float | 0-1 | Yes | `AGR - California Revised Storie Index (CA)` | Same as NCCPI pattern |

## CSR2 — Iowa Corn Suitability Rating 2

**sdvattribute record:**
- `attributekey`: 189
- `attributename`: "Iowa Corn Suitability Rating CSR2 (IA)"
- `attributetablename`: mapunit
- `attributecolumnname`: iacornsr
- `attributelogicaldatatype`: Integer
- `nasisrulename`: null

**Storage pattern:** Direct column on `mapunit` table. No join through `cointerp`.
The existing `build_dynamic_sdv_query()` already handles `attributetablename="mapunit"`.

**Value range:** 5-100 (integer). 12,485 total records nationally. Iowa-only.

**Sample data (IA169 = Story County, Iowa):**
| mukey | musym | muname | iacornsr |
| --- | --- | --- | --- |
| 411277 | 1178 | Waukee variant loam, 0-2% | 96 |
| 2800480 | L55 | Nicollet loam, 1-3% | 91 |
| 411328 | 52B | Bode clay loam, 2-6% | 91 |
| 2765547 | 138B | Clarion loam, 2-6% | 89 |
| 2800481 | 55 | Nicollet clay loam, 1-3% | 89 |

**County max (IA169):** 96

**Notes:**
- Integer scale 0-100 (NOT 0-1 like NCCPI/Storie)
- Column is `iacornsr` — Iowa-specific, will be NULL outside Iowa soil surveys
- No sentinel values observed (no 99/999 markers in this column)
- County max queries filter by `l.areasymbol` through legend→mapunit join

## CPI — Crop Productivity Index

**sdvattribute record:**
- `attributekey`: 190
- `attributename`: "Crop Productivity Index"
- `attributetablename`: component
- `attributecolumnname`: cropprodindex
- `attributelogicaldatatype`: Integer
- `nasisrulename`: null

**Storage pattern:** Column on `component` table. Requires component-weighted aggregation.
The existing `build_dynamic_sdv_query()` already handles `attributetablename="component"`.

**Value range:** 1-100 (integer). 106,335 total component records nationally.
Average: 51.2. Heavily concentrated in North Dakota and South Dakota; partial coverage
in Minnesota (41 of 87 counties, mostly western/rural).

**Geographic coverage note:** CPI is NOT populated in all Minnesota counties.
Hennepin County (MN053, Minneapolis metro) has no CPI data. Wilkin County (MN167)
has the best coverage (202 components). For fixtures, use a county with known data.

**Sample data (MN167 = Wilkin County, Minnesota):**
| mukey | compname | comppct_r | cropprodindex |
| --- | --- | --- | --- |
| 2800436 | LaDelle | 6 | 100 |
| 2800008 | Overly | 80 | 100 |
| 2800029 | LaDelle | 35 | 95 |
| 357467 | Darnen | 10 | 95 |

**County max (MN167):** 100

**Also discovered (not for implementation):**
- `attributekey` 2660: "Minnesota Crop Productivity Index" on `mutext.text` — narrative format, not numeric
- Many state-specific CPI interpretation rules exist (TN, WI, ID, WA, OR, AK) as `cointerp` rules.
  These are distinct from the generic `component.cropprodindex` column.

## Storie — California Revised Storie Index

**sdvattribute record:**
- `attributekey`: 194
- `attributename`: "California Revised Storie Index (CA)"
- `attributetablename`: cointerp
- `attributecolumnname`: interphrc
- `nasisrulename`: "AGR - California Revised Storie Index (CA)"
- `attributelogicaldatatype`: String (the rating class, e.g. "Grade 1 - Excellent")

**Storage pattern:** `cointerp` interpretation rule — **identical to NCCPI**.
Uses `interphr` (float 0-1) for numeric rating, `interphrc` (string) for class.
Same join pattern: legend → mapunit → component → cointerp (ruledepth=0, mrulename filter).

**Value range:** 0-1 (float, 3 decimal places). 49,142 component records. California-only.

**Rating class distribution:**
| Grade | interphr range | Count |
| --- | --- | --- |
| Grade 1 - Excellent | 0.801-1.000 | 4,874 |
| Grade 2 - Good | 0.601-0.800 | 5,634 |
| Grade 3 - Fair | 0.401-0.600 | 8,984 |
| Grade 4 - Poor | 0.201-0.400 | 15,235 |
| Grade 5 - Very Poor | 0.101-0.200 | 8,934 |
| Grade 6 - Nonagricultural | 0.001-0.100 | 5,160 |
| Not rated | 0.000 | 321 |

**Sample data (CA077 = San Joaquin County):**
| mukey | compname | comppct_r | interphr | interphrc |
| --- | --- | --- | --- | --- |
| 462148 | Tokay | 85 | 0.995 | Grade 1 - Excellent |
| 462004 | Bruella | 85 | 0.946 | Grade 1 - Excellent |
| 462067 | Honcut | 85 | 0.946 | Grade 1 - Excellent |
| 462145 | Stomar | 85 | 0.900 | Grade 1 - Excellent |

**County max (CA077):** 0.995

## Implementation Implications

### Routing through existing `build_dynamic_sdv_query()`
All three indexes route through table paths already supported:
- **CSR2:** `attributetablename="mapunit"` → existing mapunit path
- **CPI:** `attributetablename="component"` → existing component path
- **Storie:** `attributetablename="cointerp"` → existing cointerp path (identical to NCCPI)

### Scale normalization
The LE scoring in `lesa.py` expects 0-100 scale for the `relative_value` calculation.
- **CSR2:** Already 0-100. No normalization needed.
- **CPI:** Already 0-100. No normalization needed.
- **Storie:** 0-1 scale (like NCCPI). Must multiply by 100 or handle the same way NCCPI does.
- **NCCPI (existing):** 0-1 scale. Current code in `polygon_analysis.py` already handles this.

### County max differences
- **CSR2:** `MAX(m.iacornsr)` — mapunit-level, no component join needed
- **CPI:** `MAX(c.cropprodindex)` — component-level, same pattern as NCCPI but different column
- **Storie:** `MAX(ci.interphr)` — identical to NCCPI county max pattern, different rule name

### Wave 2 (ALLOWED_SDV_TABLES) update
`mapunit` and `component` are already in `ALLOWED_SDV_TABLES`. No new tables needed
for these three indexes. Wave 2 can still add `chorizon` and `cocropyld` for future
extensibility, but they are not exercised by CSR2, CPI, or Storie.

### Fixture counties for implementation waves
- **CSR2 (wave 3):** IA169 (Story County) — max 96, good diversity
- **CPI (wave 4):** MN167 (Wilkin County) — max 100, most components (202)
- **Storie (wave 5):** CA077 (San Joaquin County) — max 0.995, good diversity
