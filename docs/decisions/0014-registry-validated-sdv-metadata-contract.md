---
id: "0014"
title: "Registry-Validated SDV Metadata Rating Contract"
status: "Accepted"
date: 2026-10-27
authors:
  - "Andrew G. Brown"
supersedes: null
superseded_by: null
source_context: "EXECUTION_PLAN_39"
---

# 14. Registry-Validated SDV Metadata Rating Contract

## Context and Problem Statement

ADR 0008 kept lower-level SDV routing in `sda_client.py` so that future ratings
could be built from `sdvattribute` metadata. That path accepted any record, read
only the table, column, and rule name, and ignored the SDV aggregation method,
horizon method, depth range, null flag, and crop constraint. As a result, any
record with a rule name went to the `cointerp` path, Storie was
component-weighted although SDV specifies Dominant Condition, CPI excluded null
ratings although SDV says to treat them as zero, horizon and crop
ratings mixed depths, crops, and units, and metadata-selected results carried
the generic provenance `SDA:SDVATTRIBUTE`. The four public selectors meanwhile
used separate fixed `SQL_PRODUCTIVITY_*` templates, so two engines could drift
apart.

The question: how does a metadata record become a deterministic SDA query,
aggregation, provenance, and caveat set?

## Decision Drivers

* A validated record must produce the same SQL, values, provenance, and caveats
  every time.
* SDV metadata states the method for each attribute; the engine should follow it.
* Unreviewed records must not reach SDA.
* Public tool behavior for NCCPI and CSR2 must not change; Storie and CPI
  change only where needed to follow their SDV records.
* SQL must stay within fixed templates (ADR 0002).

## Considered Options

1. **Frozen in-code registry plus structural validation** - only exact,
   reviewed `sdvattribute` records can be rated; the record must also pass
   structural checks against its registry entry.
2. **Structural validation only** - accept any record whose table, column, and
   method are supported.
3. **Keep fixed templates and drop metadata routing** - remove the generic path.

## Decision Outcome

Chosen option: **Option 1, frozen registry plus structural validation.**

* **Registry (D2, D3).** `SDV_RATING_REGISTRY` holds six exact records: NCCPI
  and California Revised Storie (`cointerp`), CSR2 (`mapunit`), CPI
  (`component`), Available Water Storage 0-100 cm (`chorizon`), and Yields of
  Non-Irrigated Crops (`cocropyld`, crop required). A record must match an
  entry on `attributename`, table, column, and rule name (gate 1), then pass
  structural validation of method, horizon method, identifiers, and tie-break
  rule (gate 2). Unregistered records are rejected before any SQL is built.
* **SDV method is authoritative (D4, D5).** Query strategy is chosen by table
  and `algorithmname`. Supported methods are only those the six records use:
  Weighted Average, Dominant Condition, No Aggregation Necessary, horizon
  Weighted Sum over a depth range, and nulls-as-zero for CPI and crop yields. For
  Dominant Condition the rounded `interphr` value is the condition class; the
  class with the largest summed component percent wins, and `tiebreakrule`
  breaks ties. Storie therefore changes from a weighted average to Dominant
  Condition. All other methods are rejected.
* **Nulls as zero (D12).** CPI and crop yields have
  `interpnullsaszeroflag = 1`. For CPI, a null-rated component counts as 0
  when its map unit has at least one rated component; a map unit with no rated
  component stays unrated, so counties without CPI data are not scored as 0.
  Miscellaneous areas stay excluded.
* **Stable provenance (D8).** Each entry has a stable ID used in the public
  `productivity_rating_source` field, plus an internal structured
  `sdv_provenance` record (registry version, SDV fields, method, depth,
  tie-break, null handling, crop and units). No public schema changes.
* **One engine (D9).** The fixed selectors `nccpi`, `csr2`, `cpi`, and
  `storie` resolve to registry entries and run the same validation, builders,
  aggregation, provenance, and caveat code as explicit metadata. The
  `SQL_PRODUCTIVITY_*` templates were retired after parity tests showed the
  new SQL for NCCPI and CSR2, and the CPI county maximum, was equivalent to
  the old templates. CPI rating SQL differs on purpose because it applies
  nulls-as-zero.

The field-level contract, per-table behavior, caveat catalog, and the
checklist for adding a record are in
[docs/sdv-metadata-contract.md](../sdv-metadata-contract.md).

### Consequences

* **Positive**: A validated record deterministically produces SQL, values,
  provenance, and caveats; golden cases in
  `tests/fixtures/sdv_contract_cases.json` pin all four per record.
* **Positive**: One code path serves fixed selectors and metadata, so they
  cannot drift; corridor fallback provenance and sentinels now come from the
  registry.
* **Positive**: The ratings follow the SDV aggregation method, and crop yields
  can no longer mix crops or units.
* **Negative**: Public Storie values change (CA077 sample map units rose by
  0.027 to 0.100; the county maximum is unchanged at 0.995).
* **Negative**: Callers that passed arbitrary `sdvattribute` records to the
  lower-level methods now get `SDAValidationError`. No production caller did.
* **Negative**: Each new rating needs a registry entry, fixture, golden case,
  and live benchmark.
* **Negative**: Public CPI values change where a map unit mixes rated and
  null-rated components (MN167: 1 of 46 rated map units, 2800029 from 83 to
  79; the county maximum is unchanged at 100).

## Validation & Compliance

* ADR 0002: builders are fixed templates; only validated map unit keys, area
  symbols, registry values, and a validated crop name are interpolated. ADR
  0002 carries a dated amendment recording the retired `SQL_PRODUCTIVITY_*`
  constants.
* ADR 0008: routing stays in `sda_client.py`; the public selector set is
  unchanged. ADR 0008 carries a dated amendment pointing here.
* ADR 0011: golden, parity, and strategy tests run offline; live benchmarks
  are `live_network` opt-in.
* Parity: canonical SQL fingerprints (whitespace and sentinel-list order
  normalized) of the new NCCPI and CSR2 queries and the CPI county-maximum
  query match the retired templates, and live NCCPI IL019 (0.933), CSR2 IA169
  (96), and CPI MN167 (100) county maximums are identical to `main`.
* Live Storie CA077 comparison, approved by the user on 2026-10-27, is recorded
  in `planning/STATE_39.md` (task 39.5.1).
* CPI nulls-as-zero: an offline SQLite test runs the generated SQL (mixed
  map unit counts nulls as 0, all-null map unit stays NULL); live MN167
  2800029 is 79 and MN053 stays unrated. Recorded in `planning/STATE_39.md`.
