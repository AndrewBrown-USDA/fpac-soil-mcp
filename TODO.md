# TODO

## Goal
Resolve the three remaining PR #74 review issues by enforcing verified Criterion 2 evidence, integrating corridor evidence through the shared LESA evaluator, and correcting the Phase 4 roadmap wording.

## Tasks

### 1. Gate automated Criterion 2 scoring
- [x] Require both `is_agricultural=True` and `is_verified=True` before automated Criterion 2 points can be awarded.
- [x] Preserve the explicit manual `awarded_points` override path without applying the automated evidence gate.
- [x] Add regression tests for measured agricultural evidence with and without verification.

### 2. Route corridor LESA through the shared evaluator
- [x] Change the public corridor LESA path to use the shared perimeter-aware evaluator selected by the user.
- [x] Ensure computed `criterion_2_perimeter_evidence` is consumed and exposed in the public corridor response.
- [x] Add focused corridor tests covering ratio, provenance, evidence status, and awarded points.

### 3. Correct Phase 4 roadmap documentation
- [x] Revise `planning/MASTER_PLAN.md` to describe Criterion 2 as a preliminary non-urban screening scaffold.
- [x] State that authoritative current agricultural-land-use integration remains required before verified agricultural-adjacency points can be awarded.
- [x] Preserve the existing regulatory limitation that the server does not produce official FPPA or LESA determinations.

### 4. Validate and prepare review responses
- [x] Run focused LESA, corridor, and planning-related tests.
- [x] Run Ruff lint and format checks plus the offline repository validation target.
- [x] Review the final diff and prepare response text for all three open PR threads.

## Notes
- Scope is limited to the three currently open PR #74 review issues.
- Do not add a new agricultural data source in this change; the goal is to enforce the evidence boundary and correct the public corridor integration.
- Do not push or modify remote PR review state unless explicitly requested.
