# TODO

## Goal
Relocate the Pi agent evaluation harness into `eval/pi/` while preserving the shared top-level test-case dataset and keeping all repository commands and references functional.

## Tasks

### 1. Relocate the Pi harness
- [x] Create `eval/pi/` and move the Pi runner and Pi agent-evaluation test module into it.
- [x] Update the relocated modules' imports and path resolution so they continue to load shared helpers and the top-level `eval/prompt_test_cases.json`.
- [x] Remove the obsolete top-level Pi harness files after the new paths are wired.

### 2. Update repository integration
- [x] Update Makefile targets, pytest configuration, documentation, and repository guidance that reference the old Pi harness paths.
- [x] Preserve the existing Pi evaluation command-line behavior and artifact-output behavior through the new `eval/pi/` entry point.

### 3. Validate the relocation
- [x] Run the existing offline test suite, including the relocated evaluation tests selected by pytest.
- [x] Run Ruff lint and format checks, resolving only issues caused by or exposed by this relocation.
- [x] Confirm no repository references remain that require the removed top-level Pi harness paths.

## Notes
- This is a hard move; no compatibility wrappers remain at the old paths.
- `eval/prompt_test_cases.json` remains top-level because it is now shared beyond the Pi harness.
- `eval/common/`, `eval/contract/`, and `eval/databricks/` remain in their current locations.
- Do not add new tests; existing tests must continue to pass.
