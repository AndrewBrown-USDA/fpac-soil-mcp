# TODO

## Goal
Correct the eight issues raised in review on PR #74 while preserving the intended Criterion 2 perimeter-adjacency behavior and updating the planning state to match the delivered implementation.

## Tasks

### 1. Correct TIGERweb response-shape handling
- [x] Require a present, list-valued `features` field before treating a TIGERweb response as a valid empty result.
- [x] Treat explicit `geometry: null` values as unusable geometry and return the established unavailable evidence result.
- [x] Handle point-only and geometry-collection boundary contacts by extracting lineal components and treating point-only contacts as zero-length adjacency.
- [x] Add focused regression tests for missing `features`, null geometry, point contacts, and mixed geometry contacts.

### 2. Correct LESA Criterion 2 evidence semantics
- [x] Distinguish omitted perimeter evidence (`not_provided`) from explicitly unavailable evidence (`unavailable`).
- [x] Prevent non-urban TIGERweb screening evidence from being passed directly into verified agricultural Criterion 2 scoring.
- [x] Preserve measured-zero behavior and explicit agricultural/manual evidence overrides.
- [x] Add focused LESA regression tests covering evidence status and scoring behavior.

### 3. Integrate corridor perimeter evidence
- [x] Read `criterion_2_perimeter_evidence` from the corridor result manifest when processing a LineString input.
- [x] Add or update a corridor LESA regression test proving computed perimeter evidence reaches Criterion 2 inputs.

### 4. Synchronize planning artifacts
- [x] Update `planning/GOALS.md` to reference `planning/STATE_43.md`.
- [x] Replace the stale pre-implementation active-goal wording with the delivered Criterion 2 status and correct next dependency.

### 5. Validate the corrections
- [x] Run focused tests for TIGERweb, LESA, polygon, and corridor behavior.
- [x] Run Ruff lint and format checks.
- [x] Run the offline repository validation target and record any relevant result.

## Notes
- Scope is limited to the eight review comments on PR #74.
- Preserve explicit unavailable/error states and the project's preliminary-screening and regulatory-boundary language.
- Do not infer agricultural use from non-urban status; agricultural evidence must remain distinct from urban exemption screening.
