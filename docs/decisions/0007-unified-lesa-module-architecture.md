---
id: "0007"
title: "Unified LESA Module Architecture"
status: "Accepted"
date: 2026-09-28
authors:
  - "Andrew G. Brown"
supersedes: null
superseded_by: null
source_context: "EXECUTION_PLAN_17"
---

# 7. Unified LESA Module Architecture

## Context and Problem Statement

By EP17, the system had separate scoring engines: `corridor_scoring.py` for
7 CFR § 658.5(c) corridor Site Assessment rules (created in EP7) and the
polygon analysis path in `polygon_analysis.py`. Phase 4 introduced Land
Evaluation (LE) scoring with relative rating normalization, requiring shared
LE calculation logic for both site (Form AD-1006) and corridor (Form
NRCS-CPA-106) projects. Duplicating LE logic across two modules would create
maintenance burden and divergence risk.

## Decision Drivers

* Both site and corridor projects require the same relative rating normalization
  formula: $RR_i = Rating_i / MaxCountyRating$.
* Both require area-weighted LE scoring: $LE = round(RR_{AOI} \times 100)$.
* The 160-point mandatory alternatives threshold (7 CFR § 658.4(c)(2)) applies
  to both project types.
* `corridor_scoring.py` was already stable with 533 lines of corridor-specific
  rules; replacing it entirely would break existing tests and callers.

## Considered Options

1. **Unified `lesa.py` module with backwards-compatible `corridor_scoring.py`
   re-exports** — create a single LESA module providing shared LE calculators,
   SA structures, and total LESA scoring; maintain `corridor_scoring.py` as a
   re-export/adapter layer for corridor-specific 658.5(c) rules.
2. **Merge everything into `corridor_scoring.py`** — expand the existing module
   to handle site projects too.
3. **Duplicate LE logic in both modules** — copy the normalization formulas into
   both polygon and corridor paths independently.

## Decision Outcome

Chosen option: **Unified `lesa.py` with backwards-compatible re-exports**,
because it centralizes all LE-SA calculation logic while preserving the stable
corridor-specific interface and its existing test coverage.

### Consequences

* **Positive**: Single source of truth for relative rating normalization,
  area-weighted LE scoring, and the 160-point threshold flag.
* **Positive**: Backwards compatibility preserved — existing `corridor_scoring.py`
  callers continued to work without modification.
* **Positive**: Both `analyze_farmland_by_polygon` and `analyze_corridor_fppa`
  tools now share the same LE scoring path.
* **Negative**: The interaction between `lesa.py` and the existing corridor and
  polygon paths required three remediation waves (EP22: productivity preservation,
  EP23: productivity ratings, EP25: code review items) to fully stabilize.
  The backwards-compatibility constraint with `corridor_scoring.py` was
  non-trivial.
* **Negative**: `lesa.py` grew to 818 lines by EP22, making it one of the
  largest modules. Workers were instructed to use grep anchors rather than
  whole-file reads.

## Validation & Compliance

Decision established in EXECUTION_PLAN_17 (2026-09-28). Remediated through
EP22 (productivity preservation, commit `a8c26940`), EP23 (productivity
ratings, commit `bd158919`), EP25 (code review items, commit `7e7ebd9e`).
Final offline suite: 309+ tests passing.
