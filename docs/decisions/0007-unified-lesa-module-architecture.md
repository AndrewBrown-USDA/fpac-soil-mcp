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
  SA evaluator classes; replacing it entirely would break existing tests and
  callers.

## Considered Options

1. **Shared LE helpers in `lesa.py`, corridor-specific SA retained in
   `corridor_scoring.py`** — create `lesa.py` to provide shared LE calculators
   (`calculate_composite_le`, `calculate_criterion_7_score`), unified data
   models, and total LESA scoring. `corridor_scoring.py` imports these shared
   helpers but retains its own corridor Site Assessment evaluator classes and
   `evaluate_corridor_lesa()`.
2. **Merge everything into `corridor_scoring.py`** — expand the existing module
   to handle site projects too.
3. **Duplicate LE logic in both modules** — copy the normalization formulas into
   both polygon and corridor paths independently.

## Decision Outcome

Chosen option: **Shared LE helpers in `lesa.py` with corridor SA retained in
`corridor_scoring.py`**, because it centralizes the LE calculation logic that
both project types share while preserving the stable corridor-specific SA
implementation and its existing test coverage.

### Consequences

* **Positive**: Single source of truth for relative rating normalization,
  area-weighted LE scoring, and the criterion 7 (compatibility with zoning)
  calculation shared by both project types.
* **Positive**: `corridor_scoring.py` retains corridor Site Assessment evaluator
  classes, the statutory threshold calculation, and `evaluate_corridor_lesa()`.
  This preserves its stable interface and existing test coverage without
  forced migration.
* **Positive**: Both `analyze_farmland_by_polygon` and `analyze_corridor_fppa`
  tools share the same LE scoring path through `lesa.py`.
* **Negative**: The boundary between `lesa.py` (shared LE) and
  `corridor_scoring.py` (corridor SA + LESA orchestration) required three
  remediation waves (EP22, EP23, EP25) to fully stabilize, particularly around
  productivity index preservation through the corridor fallback path.
* **Negative**: `lesa.py` grew to 818 lines by EP22, making it one of the
  largest modules. Workers were instructed to use grep anchors rather than
  whole-file reads.

## Validation & Compliance

Decision established in EXECUTION_PLAN_17 (2026-09-28). Remediated through
EP22 (productivity preservation, commit `a8c26940`), EP23 (productivity
ratings, commit `bd158919`), EP25 (code review items, commit `7e7ebd9e`).
Final offline suite: 309+ tests passing.
