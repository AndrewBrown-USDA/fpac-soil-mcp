# TODO

## Goal
Compute urban-area overlap acreage for polygon-based FPPA exemption screening and propagate the value through polygon and corridor analyses, resolving issue #29.

## Tasks

### 1. Trace the urban screening and acreage contracts
- [x] Inspect `TigerwebClient.check_urban_exemption`, geometry helpers, response models, polygon analysis, corridor analysis, and existing mocked tests.
- [x] Identify the minimal interfaces needed to request urban polygon geometry and calculate clipped acreage while preserving `None` for point inputs.

### 2. Implement urban overlap acreage
- [x] Request urban polygon geometry for polygon inputs while retaining the existing point-query behavior.
- [x] Intersect returned urban polygons with the footprint using the project’s ADR 0004 acreage calculation method.
- [x] Return `0.0` for polygon inputs with no urban intersection and retain `None` for point inputs.
- [x] Propagate the computed acreage through polygon and corridor response payloads without adding `screened_pct`.

### 3. Add regression coverage
- [x] Add mocked tests for partial overlap acreage accuracy, no intersection, and point-input behavior.
- [x] Verify polygon and corridor responses carry the computed `screened_acreage`.
- [x] Update existing hard-coded expectations affected by the new behavior.

### 4. Update architectural documentation
- [x] Update ADR 0004 to document urban polygon clipping and acreage measurement.
- [x] Update ADR 0006 to document the corridor response propagation of urban overlap acreage.

### 5. Validate and finish
- [x] Run targeted urban, polygon, and corridor tests.
- [x] Run the repository validation target or the smallest equivalent checks required by the changes.
- [x] Mark all completed tasks in `TODO.md`.

## Notes
- Scope is limited to the required `screened_acreage`; do not add `screened_pct`.
- Use existing geometry and acreage helpers rather than introducing a parallel calculation method.
- Preserve explicit preliminary-screening limitations and point-input semantics.
