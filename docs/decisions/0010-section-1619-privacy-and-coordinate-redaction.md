---
id: "0010"
title: "Section 1619 Privacy & Coordinate Redaction"
status: "Accepted"
date: 2026-09-17
authors:
  - "Andrew G. Brown"
supersedes: null
superseded_by: null
source_context: "EXECUTION_PLAN_4"
---

# 10. Section 1619 Privacy & Coordinate Redaction

## Context and Problem Statement

The Food, Conservation, and Energy Act of 2008 (Section 1619, codified at
7 U.S.C. § 8791) requires protection of information provided by agricultural
producers to USDA. While this MCP server operates on public soil survey data
(SSURGO) rather than producer-specific records, user-submitted coordinates and
AOI geometries could reveal the locations of agricultural operations. A privacy
module was needed to enforce data governance guardrails where sensitive locations
might be processed.

## Decision Drivers

* 7 U.S.C. § 8791 (Section 1619) is a federal statutory requirement.
* User-submitted coordinates and polygon geometries may identify agricultural
  producer locations.
* The server processes public soil data, but the combination of coordinates +
  soil analysis could reveal operational details.
* Privacy enforcement must be centralized and auditable, not scattered across
  tool implementations.

## Considered Options

1. **Dedicated `privacy.py` module** — centralize all data governance checks,
   coordinate redaction rules, and Section 1619 compliance logic in a single
   module referenced by tools and analysis pipelines.
2. **Per-tool privacy checks** — each tool implements its own privacy validation.
3. **No privacy module** — document the limitation in README only.

## Decision Outcome

Chosen option: **Dedicated `privacy.py` module**, because it makes privacy
enforcement centralized, auditable, testable, and impossible to accidentally
bypass when adding new tools.

### Consequences

* **Positive**: Single point of enforcement for all coordinate privacy and
  Section 1619 compliance checks.
* **Positive**: AGENTS.md Operational Rules reference `privacy.py` explicitly,
  ensuring future contributors are aware of the requirement.
* **Positive**: The module remained stable after initial creation — no
  remediation cycles required.
* **Negative**: Adds a compliance check to processing pipelines, introducing
  minimal latency. This is negligible and legally required.

## Validation & Compliance

Privacy module referenced in AGENTS.md Operational Rules: "Enforce Section 1619
and coordinate privacy protections via `privacy.py` where agricultural producer
data or sensitive locations are processed." Module created in the EP4-era
geospatial build-out and remained stable through all subsequent phases.
