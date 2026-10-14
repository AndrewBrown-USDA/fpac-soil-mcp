---
id: "0008"
title: "NCCPI as Validated Public Productivity Index with Extensible SDV Routing"
status: "Accepted"
date: 2026-09-28
authors:
  - "Andrew G. Brown"
supersedes: null
superseded_by: null
source_context: "EXECUTION_PLAN_17, EXECUTION_PLAN_26"
---

# 8. NCCPI as Validated Public Productivity Index with Extensible SDV Routing

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

Chosen option: **NCCPI as the validated public contract with extensible SDV
routing retained**, because it protects users from unvalidated index results
while preserving the infrastructure to add validated state indexes in the future
without architectural changes.

### Consequences

* **Positive**: `ProductivityIndexType` enum contains only `NCCPI`. Unsupported
  index requests are rejected at the tool level before reaching SDA, preventing
  unvalidated scores from reaching users.
* **Positive**: The lower-level `sda_client.py` methods still support dynamic
  SDV attribute routing with explicit validated metadata, so adding a future
  state index requires adding the enum value and test fixtures, not architectural
  changes.
* **Positive**: Null/unrated screening with explicit notices prevents mathematical
  distortion and provides transparency in LE scoring.
* **Negative**: State-specific indexes (CSR2, CPI, Storie) are not available
  through the public tool API until individually validated with state-specific
  benchmark fixtures. This limits Land Evaluation accuracy in states where NCCPI
  is not the locally preferred index.
* **Negative**: Three remediation waves (EP20 cointerp rules, EP22 productivity
  preservation, EP23 productivity ratings) were needed before EP26 could
  confidently narrow the public contract.

## Validation & Compliance

EP17 (2026-09-28) established dynamic SDV routing. EP20 (commit `9cbcc7ed`)
fixed cointerp aggregation rules. EP22-23 remediated productivity preservation.
EP26 (commit `cc822eaa`) narrowed the public contract: STATE_26 line 48
records "public and test contracts now expose validated national NCCPI only."
`ProductivityIndexType` enum: `models.py:318-321`.
