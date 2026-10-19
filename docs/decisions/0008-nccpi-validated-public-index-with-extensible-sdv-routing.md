---
id: "0008"
title: "NCCPI, CSR2, CPI, and Storie as Validated Public Productivity Indexes"
status: "Accepted"
date: 2026-09-28
authors:
  - "Andrew G. Brown"
supersedes: null
superseded_by: null
source_context: "EXECUTION_PLAN_17, EXECUTION_PLAN_26, EXECUTION_PLAN_27"
---

# 8. NCCPI, CSR2, CPI, and Storie as Validated Public Productivity Indexes

## Context and Problem Statement

FPPA Land Evaluation scores require soil productivity ratings. The appropriate
productivity index varies by state: Iowa uses CSR2, Minnesota uses CPI,
California uses the Revised Storie Index, and most states default to NCCPI v3.
EP17 implemented dynamic Soil Data Viewer (SDV) attribute routing to support
multiple indexes. However, after implementation and remediation (EP20, EP22,
EP23), EP26 explicitly narrowed the validated public contract to NCCPI only,
retaining lower-level custom query paths for future extensibility.

## Decision Drivers

* Different states use different productivity indexes for FPPA Land Evaluation.
* SDA's `sdvattribute` metadata table can dynamically resolve storage locations
  for any named attribute.
* EP20 revealed that cointerp aggregation rules for state-specific indexes
  required non-trivial fixes; EP22-23 required further remediation.
* Validating each state index against real-world benchmarks requires index-specific
  test fixtures and domain expertise per state.
* Shipping unvalidated state indexes in the public tool API risks incorrect
  Land Evaluation scores.

## Considered Options

1. **NCCPI as the validated public contract, extensible lower-level SDV routing
   retained** — expose only `ProductivityIndexType.NCCPI` through the public
   MCP tool API. Retain lower-level SDA client methods that accept custom
   index metadata for future validated state indexes. Unsupported index
   requests are rejected before reaching SDA.
2. **Full multi-index public API** — expose CSR2, CPI, Storie, and NCCPI in the
   public enum without per-index validation.
3. **NCCPI only, no extensibility** — hardcode NCCPI everywhere and remove
   dynamic routing infrastructure.

## Decision Outcome

Chosen option: **Validated public indexes with extensible SDV routing
retained**. EP27 expanded the validated set to include CSR2 (Iowa Corn
Suitability Rating) alongside NCCPI, validating the extensibility claim of
the original design. Adding CSR2 required only:
1. A new `ProductivityIndexType.CSR2` enum value
2. Fixed SQL templates for `mapunit.iacornsr`
3. Routing branches in `get_productivity_ratings` / `get_county_max_productivity_rating`
4. Expanded NCCPI-only guards in polygon, corridor, and tool layers
5. Live-verified benchmark fixture (IA169 county max = 96)

No architectural changes were needed, confirming the extensible design.

### Consequences

* **Positive**: `ProductivityIndexType` enum contains `NCCPI`, `CSR2`, `CPI`, and `STORIE`.
  Unsupported index requests are rejected at the tool level before reaching
  SDA, preventing unvalidated scores from reaching users.
* **Positive**: The lower-level `sda_client.py` methods still support dynamic
  SDV attribute routing with explicit validated metadata, so adding a future
  state index requires adding the enum value and test fixtures, not architectural
  changes.
* **Positive**: Null/unrated screening with explicit notices prevents mathematical
  distortion and provides transparency in LE scoring.
* **Positive**: CSR2 is now available for Iowa-based Land Evaluation, using
  the direct `mapunit.iacornsr` column (integer scale 5-100). Non-Iowa counties
  correctly return None for CSR2.
* **Positive**: CPI is now available for ND/SD/MN-based Land Evaluation, using
  component-weighted `component.cropprodindex` (integer scale 1-100). Non-populated
  counties correctly return None.
* **Positive**: Storie is now available for California-based Land Evaluation,
  reusing the NCCPI cointerp SQL templates with rule name
  "AGR - California Revised Storie Index (CA)" (float scale 0-1).
  Non-California counties correctly return None.
* **Negative**: Three remediation waves (EP20 cointerp rules, EP22 productivity
  preservation, EP23 productivity ratings) were needed before EP26 could
  confidently narrow the public contract.

## Validation & Compliance

EP17 (2026-09-28) established dynamic SDV routing. EP20 (commit `9cbcc7ed`)
fixed cointerp aggregation rules. EP22-23 remediated productivity preservation.
EP26 (commit `cc822eaa`) narrowed the public contract: STATE_26 line 48
records "public and test contracts now expose validated national NCCPI only."
EP27 (2026-10-15 → 2026-10-19) validated and added all four state-specific productivity
indexes as public contract members:
* `ProductivityIndexType` enum: NCCPI, CSR2, CPI, STORIE
* CSR2: `SDA:MAPUNIT_IACORNSR` — fixed SQL, IA169 max = 96.0
* CPI: `SDA:COMPONENT_CROPPRODINDEX` — component-level, MN167 max = 100.0
* Storie: `SDA:COINTERP_STORIE_CA` — reuses NCCPI cointerp template,
  CA077 max ≈ 0.995
* Benchmark fixtures in `tests/fixtures/le_benchmarks.json`

EP28 (2026-10-19) code-review remediation of EP27:
* Extracted `VALIDATED_PRODUCTIVITY_INDEXES` (auto-all frozenset) and
  `SUPPORTED_INDEX_MSG` (dynamically generated) constants in `models.py`
* Consolidated inline guard tuples across 5 source files to use the frozenset
* Added `_round_for_index()` rounding helper and alias frozensets in `sda_client.py`
* Fixed CPI `compkind != 'miscellaneous area'` filter (B5) and zero-sentinel (B4)
* Added rounding-precision and guard-acceptance tests

