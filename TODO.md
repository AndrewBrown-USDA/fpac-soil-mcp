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

---

# Follow-up TODO: Criterion 2 Test Hardening

## Goal
Add non-tautological regression coverage for the four remaining Criterion 2 test gaps without changing production behavior unless a test exposes a directly related defect.

## Tasks

### 1. Testing upstream request failures
- [x] Add focused tests for HTTP status failures and request exceptions through `TigerwebClient.get_perimeter_evidence`.
- [x] Assert explicit `error` status, unavailable ratio, verification state, and safe error metadata.

### 2. Testing invalid perimeter inputs
- [x] Add tests for invalid geometry input and zero-perimeter geometry.
- [x] Assert deterministic error-state behavior without uncaught failures or fabricated measurements.

### 3. Testing end-to-end evidence propagation
- [x] Add polygon analyzer coverage from mocked perimeter evidence through the final analysis response.
- [x] Add corridor analyzer coverage from mocked perimeter evidence through the final analysis response.
- [x] Assert measured, unavailable, and error states remain distinct at the public response boundary.

### 4. Testing boundary-contact geometry
- [x] Add non-tautological tests for boundary-only contacts and geometry collections containing lineal and point components.
- [x] Assert point-only contacts do not contribute perimeter length and lineal contacts do.

### 5. Validating and documenting the change
- [x] Run targeted Criterion 2 tests and the complete offline test suite.
- [x] Run Ruff checks, formatting checks, and `git diff --check`.
- [x] Review the final diff and summarize any production fix that was required.

## Notes
- ImageServer/CDL implementation is explicitly future work and is out of scope.
- Prefer existing `httpx.MockTransport` fixtures and current analyzer test patterns.
- Small production fixes are allowed only when directly exposed by the new tests.

---

# TODO — PR #83 Review Resolution

## Goal
Resolve all 20 open review threads on PR #83 and the two supplied LESA findings about missing evidence and post-scoring authority rewrites, with focused regression coverage.

## Tasks

### 1. Correct LESA scoring and evidence completeness
- [x] Preserve the productivity index's scale when a corridor county maximum is unavailable, including STORIE.
- [x] Make acreage-based and registry-based Criterion 7 scoring use one deduction schedule and verify parity at 5% boundaries.
- [x] Keep Criterion 2 unavailable when measured perimeter evidence lacks a normalized ratio.
- [x] Reject invalid/non-finite farm acreages and reject competing Criterion 7 acreage and explicit-input forms.
- [x] Prevent a caller-provided `is_automated` flag from making a missing standard criterion score available.
- [x] Keep a missing Criterion 10 category unavailable instead of treating it as the zero-point category.
- [x] Ensure missing Land Evaluation, incomplete or unstructured Site Assessment, and a bare-float Site Assessment never produce an evaluated LESA threshold.
- [x] Move registry fact authority, verification, justification, and provenance into the scored inputs; remove the post-evaluation rewrite that can contradict scored results.
- [x] Add regression tests for each evidence/authority edge case and preserve evaluated behavior for complete valid inputs.

### 2. Make evaluation contracts executable and consistent
- [x] Run gold-set contract cases against production outputs using `match_expected`, and align expected paths with actual response schemas.
- [x] Wire browser harness safety assertions into the pass predicate or remove assertions that are not implemented.
- [x] Emit evidence-tier classification from the Pi runner, honoring each case's explicit tier.
- [x] Require named Site Assessment prompt calls for SA-MA-01 and SA-MA-03 in the T1 and shared catalogs.
- [x] State the required project name and project type for SA-MA-02 in both catalogs, or revise the contract to avoid asserting undisclosed/defaulted arguments.

### 3. Preserve consistent coverage and provenance
- [x] Preserve component-level partial-rating coverage and caveats through corridor segment and summary results, separately from mapped-acreage coverage.
- [x] Apply reconciliation tolerance when deciding whether corridor coverage is complete.
- [x] Populate normalized coverage status in direct polygon results and Land Evaluation summaries.
- [x] Use the selected index's registry provenance ID in direct polygon responses.
- [x] Compute SDA crop-yield coverage after mixed-unit validation so coverage agrees with rating availability.

### 4. Correct eCFR refresh integrity
- [x] Make `--check` validate local XML files against their manifest hashes, including missing or modified files.
- [x] Preserve provenance for unselected CFR parts during partial refreshes, or otherwise prevent partial refreshes from corrupting the shared manifest.

### 5. Correct regulatory wording
- [x] Align the threshold description and citations with 7 CFR § 658.4(c), and update all cited wording locations and regression tests.

### 6. Validate and prepare review responses
- [x] Run focused tests for the changed areas, then the offline repository checks.
- [x] Review the final diff and map each resolved finding to its PR review thread.
- [x] Prepare concise replies for all 20 open PR review threads.

## Discovered Tasks
- [x] Refresh `docs/cfr` from eCFR because `make ecfr-check` found local XML files that do not match their manifest hashes; rerun the check before aligning regulatory wording.

## Notes
- Scope includes all 20 open review threads returned for PR #83, plus the two supplied LESA findings on missing/unstructured inputs and authority/provenance rewrites.
- The supplied shared coverage-vocabulary proposal and suspected Streamable HTTP stateless/session-mode issue are deferred; do not change these unless a scoped review fix makes it necessary, in which case stop and request approval.
- Preserve unrelated existing TODO content above. Do not push commits or modify remote PR review state.
