---
id: "0002"
title: "Fixed SQL Templates Over User SQL Passthrough"
status: "Accepted"
date: 2026-09-16
authors:
  - "Andrew G. Brown"
supersedes: null
superseded_by: null
source_context: "EXECUTION_PLAN_1"
---

# 2. Fixed SQL Templates Over User SQL Passthrough

## Context and Problem Statement

The server queries USDA NRCS Soil Data Access (SDA), a public T-SQL endpoint
accepting arbitrary SQL. Exposing a general-purpose "run any SDA SQL" MCP tool
would give maximum flexibility but create injection risks, unpredictable query
costs, and outputs lacking regulatory context. The server needed to balance
query capability against safety and reproducibility.

## Decision Drivers

* Security: SDA accepts arbitrary SQL; unconstrained passthrough exposes the
  entire SSURGO/STATSGO2 schema surface to prompt injection.
* Reproducibility: Fixed templates produce auditable, deterministic queries
  that can be tested against mocked fixtures.
* Regulatory compliance: Each query's purpose and limitations must be
  documented; freeform SQL breaks this traceability.
* Extensibility: New soil attributes (SDV routing, state productivity indexes)
  must be queryable without opening arbitrary SQL.

## Considered Options

1. **Fixed parameterized T-SQL templates with strict input validation** —
   `SQL_FARMLAND_BY_POINT`, `SQL_FARMLAND_BY_MUKEY`, `SQL_INTERPRETATION_*`,
   `SQL_PRODUCTIVITY_*` constants in `sda_client.py`. All user-supplied values
   validated before interpolation.
2. **Parameterized query builder with allowlisted tables/columns** — accept
   user-specified table and column names but restrict to an allowlist.
3. **Full SQL passthrough MCP tool** — expose `run_sda_sql(query: str)`.

## Decision Outcome

Chosen option: **Fixed parameterized T-SQL templates**, because they eliminate
SQL injection surface, make every query auditable and testable, and enforce the
regulatory traceability requirement.

### Consequences

* **Positive**: Zero SQL injection vectors across the entire tool surface.
  Every query is a named constant with documented purpose and test coverage.
* **Positive**: When EP17 required dynamic SDV attribute routing for state
  productivity indexes (CSR2, CPI, Storie), the template approach extended
  cleanly — new `SQL_PRODUCTIVITY_*` templates were added without relaxing the
  no-passthrough constraint.
* **Negative**: Adding a new query type requires a code change (new template +
  validation + tests) rather than a runtime parameter. This is an intentional
  trade-off favoring safety over ad-hoc flexibility.
* **Negative**: Complex multi-CTE queries (e.g., component-weighted
  interpretations) are verbose as string constants. Addressed by clear naming
  and inline documentation.

## Validation & Compliance

Enforced as a verbatim constraint in EXECUTION_PLAN_1 and propagated through
all subsequent plans. Codified in AGENTS.md Operational Rules: "Do not add
user-supplied SQL passthrough." Validated by SDA client hardening in EP21
(commit `21.1.1`).

### Amendment (2026-10-27, EP39)

This amendment records how productivity SQL is now produced; the decision and
status are unchanged.

* The `SQL_PRODUCTIVITY_*` constants named above have been retired. Productivity
  and SDV property SQL now comes from fixed per-strategy builder functions in
  `sda_client.py` (`build_sdv_rating_query`, `build_sdv_county_max_query`), one
  template per source table and SDV aggregation method
  ([ADR 0014](0014-registry-validated-sdv-metadata-contract.md)). Parity tests
  showed the new NCCPI, CSR2, and CPI SQL is equivalent to the retired
  constants.
* This is still Option 1, not Option 2. Table, column, and rule names in the SQL
  come only from the frozen in-code registry (`SDV_RATING_REGISTRY`); a caller
  cannot name a table or column, and unregistered `sdvattribute` records are
  rejected before any SQL is built. Caller-supplied values interpolated into
  the templates are limited to validated map unit keys, survey area symbols, and
  a validated crop name.
