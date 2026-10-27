# EXECUTION PLAN 38: Refactor Tool Modules by Domain

## Goal & Scope

**Goal:** Refactor the MCP tool implementation layout described by issue #25 so the current monolithic `soil_tools.py` is organized into cohesive domain-oriented modules without forcing a one-tool-per-file structure. Preserve all public MCP tool names and behavior, keep registration centralized, and update the import/test surface to match the new modules.

**In scope:**

- Evaluate the practical alternatives (leave the two files as-is, one-tool-per-file,
  or cohesive domain modules) and document the selected tradeoff before extraction.
- Split the eight soil tools into the agreed domain modules:
  `soil_lookup_tools.py`, `spatial_analysis_tools.py`, `lesa_tools.py`, and
  `exemption_tools.py`.
- Keep `fppa_tools.py` for the two FPPA explanation/class-list tools.
- Update package exports, registration, and affected tests/imports.
- Remove the obsolete implementation monolith after all callers are migrated.
- Validate with targeted tool/server tests, Ruff, and the full offline suite.

**Out of scope:**

- One source file for every MCP tool.
- Changes to tool names, schemas, descriptions, response models, domain algorithms, HTTP clients, or regulatory behavior.
- New dependencies, public documentation changes, manifest/server metadata changes, or live-network testing.
- Backward-compatible Python imports from `soil_tools.py` or `fppa_tools.py`; the user selected allowing internal import-path changes.

**Verbatim constraints from the request:**

- “Refactor: migrate to ‘one-tool-per-file’ structure”
- “One-tool-per-file might be a bit too granular, since we have different tiers of tool access”
- “this issue is to evaluate options to organize a bit better”

## Reconnaissance Log

- `src\fpac_soil_mcp\tools\soil_tools.py` is 703 lines and contains eight tools plus registration; `fppa_tools.py` is 57 lines and contains two tools plus registration.
- `tools\__init__.py` is the centralized export/registration boundary consumed by `app.py`.
- Relevant tests are concentrated in `tests\test_tools.py`, `tests\test_server.py`, `tests\test_phase2_contracts.py`, and `tests\test_phase3_contracts.py`.
- Baseline on 2026-10-27: `uv run pytest -m "not live_network"` -> 476 passed, 3 skipped, 22 deselected; `uv run ruff check .` passed; `uv run ruff format --check .` passed (461 files).
- ADR 0001 requires modular registration but does not require one-file-per-tool. ADR 0003 requires preserving the preliminary-screening authority boundary.
- `app.py` registers only through `tools.register_tools`; no direct module imports were found there.
- The issue's “different tiers of tool access” concern is addressed by domain cohesion
  and registration boundaries, not by creating a file for each individual tool.

## Options Considered

| Option | Assessment | Decision |
|---|---|---|
| Keep `soil_tools.py` and `fppa_tools.py` | Lowest churn, but leaves the growing soil module as a monolith. | Not selected |
| One MCP tool per file | Maximum isolation, but too granular for the current ten-tool surface and creates unnecessary registration/import overhead. | Not selected |
| Cohesive domain modules | Reduces monolith size, preserves related workflows together, and leaves room for future tier-specific registration. | Selected |

## Decision Log

1. **2026-10-27 — Granularity:** use domain-oriented modules, not one-tool-per-file, because the issue explicitly questions excessive granularity and the existing architecture already has domain registration boundaries.
2. **2026-10-27 — Module split:** use `soil_lookup_tools.py`, `spatial_analysis_tools.py`, `lesa_tools.py`, `exemption_tools.py`, and retain `fppa_tools.py`.
3. **2026-10-27 — Python import compatibility:** internal imports may change; do not add compatibility re-exports from the removed `soil_tools.py`.
4. **2026-10-27 — Execution:** serial waves with at most two workers per wave; same-file extraction work is sequenced.
5. **2026-10-27 — Acceptance:** targeted tests plus Ruff and the full offline suite are required; live-network tests remain deferred.

## Wave & Dependency Table

| Wave | Task | Title | Files in scope | Depends on |
|---|---|---|---|---|
| 1 | 38.1.1 | Capture refactor baseline and dependency map | `planning/STATE_38.md`, `planning/tasks/38.1.1.todo.md` | none |
| 2 | 38.2.1 | Extract lookup and exemption tools | `src\fpac_soil_mcp\tools\soil_lookup_tools.py`, `src\fpac_soil_mcp\tools\exemption_tools.py`, `src\fpac_soil_mcp\tools\soil_tools.py`, `planning/tasks/38.2.1.todo.md` | 38.1.1 |
| 3 | 38.3.1 | Extract spatial and LESA tools | `src\fpac_soil_mcp\tools\spatial_analysis_tools.py`, `src\fpac_soil_mcp\tools\lesa_tools.py`, `src\fpac_soil_mcp\tools\soil_tools.py`, `planning/tasks/38.3.1.todo.md` | 38.2.1 |
| 4 | 38.4.1 | Rewire registration and test imports | `src\fpac_soil_mcp\tools\__init__.py`, `tests\test_tools.py`, `tests\test_server.py`, `tests\test_phase2_contracts.py`, `tests\test_phase3_contracts.py`, `planning/tasks/38.4.1.todo.md` | 38.3.1 |
| 5 | 38.5.1 | Remove monolith and validate | `src\fpac_soil_mcp\tools\soil_tools.py`, `planning/STATE_38.md`, `planning/tasks/38.5.1.todo.md` | 38.4.1 |

Tasks in each wave are intentionally serial where they touch `soil_tools.py`; no parallel task may edit the same file.

## Hazards

- Preserve exact decorator names, descriptions, signatures, and registration behavior while moving functions.
- Keep shared imports local to the new module that needs them; do not create a new catch-all utility module as part of this refactor.
- `tools\__init__.py` is a shared registration boundary and must be changed only after extraction is complete.
- Tests may import implementation modules directly; update them deliberately rather than adding compatibility shims.
- Do not alter authority notices, response models, or domain calculations while moving code.

## Task Specifications

### 38.1.1 — Capture refactor baseline and dependency map

**Repository:** `D:\workspace\fpac-soil-mcp`

**Files in scope:** must edit `planning/STATE_38.md`; can create `planning/tasks/38.1.1.todo.md`; no scratch files.

**Depends on:** none.

**Spec:** Record branch/status, baseline commands and counts, tool-to-function mapping, direct imports of the two current tool modules, and the intended module split. Confirm no active ADR conflicts and identify tests requiring import updates.

**Do not touch:** production code, tests, manifests, ADRs, or prior plan artifacts.

**Grep anchors:** `tools\soil_tools.py`, `register_tools`, `from fpac_soil_mcp.tools`, `tests\test_tools.py`.

**Reference implementations:** `planning\STATE_37.md` Baseline; `docs\decisions\0001-fastmcp-server-framework-and-package-layout.md`.

**Acceptance:** `STATE_38.md` contains the baseline commands/results and a complete ten-tool mapping; `uv run pytest -m "not live_network"` remains green.

### 38.2.1 — Extract lookup and exemption tools

**Repository:** `D:\workspace\fpac-soil-mcp`

**Files in scope:** `soil_lookup_tools.py`, `exemption_tools.py`, `soil_tools.py`, and `planning/tasks/38.2.1.todo.md`.

**Depends on:** 38.1.1.

**Spec:** Move point/mukey classification, soil interpretations, and geometry polygon lookup functions into `soil_lookup_tools.py`; move `check_urban_area_exemption` into `exemption_tools.py`. Preserve signatures, decorators/registration metadata, docstrings, imports, and behavior. Leave remaining functions in `soil_tools.py` until the next task.

**Do not touch:** `tools\__init__.py`, tests, domain modules, models, clients, and public metadata.

**Grep anchors:** `def get_farmland_classification_by_point`, `def get_farmland_classification_by_mukey`, `def get_soil_interpretations`, `def get_soil_polygons_by_geometry`, `def check_urban_area_exemption`.

**Reference implementations:** existing function bodies and `fppa_tools.py` registration style.

**Acceptance:** new modules import successfully; `uv run pytest tests\test_tools.py -k "classification or interpretation or polygon or urban"` passes; no moved function remains duplicated in `soil_tools.py`.

### 38.3.1 — Extract spatial and LESA tools

**Repository:** `D:\workspace\fpac-soil-mcp`

**Files in scope:** `spatial_analysis_tools.py`, `lesa_tools.py`, `soil_tools.py`, and `planning/tasks/38.3.1.todo.md`.

**Depends on:** 38.2.1.

**Spec:** Move `analyze_farmland_by_polygon` and `analyze_corridor_fppa` into `spatial_analysis_tools.py`; move `calculate_preliminary_lesa` into `lesa_tools.py`. Preserve all validation, privacy handling, response construction, notices, and registration metadata. Remove the now-empty implementation portions from `soil_tools.py`.

**Do not touch:** `tools\__init__.py`, tests, domain algorithms, models, clients, and public metadata.

**Grep anchors:** `def analyze_farmland_by_polygon`, `def analyze_corridor_fppa`, `def calculate_preliminary_lesa`.

**Reference implementations:** existing function bodies; `lesa.py` shared scoring path; `corridor_analysis.py` and `polygon_analysis.py` call patterns.

**Acceptance:** each moved tool has one implementation; `uv run pytest tests\test_tools.py -k "farmland or corridor or lesa"` passes; imports of each new module succeed.

### 38.4.1 — Rewire registration and test imports

**Repository:** `D:\workspace\fpac-soil-mcp`

**Files in scope:** `tools\__init__.py`, `tests\test_tools.py`, `tests\test_server.py`, `tests\test_phase2_contracts.py`, `tests\test_phase3_contracts.py`, and `planning/tasks/38.4.1.todo.md`.

**Depends on:** 38.3.1.

**Spec:** Update exports and registration to import the five domain modules plus `fppa_tools.py`; preserve the ten MCP tool names and centralized `register_tools`. Update direct test imports to the new module paths. Do not add compatibility re-exports from `soil_tools.py`.

**Do not touch:** `app.py`, production domain logic, manifests, or unrelated tests.

**Grep anchors:** `__all__`, `register_tools`, `register_soil_tools`, `register_fppa_tools`, direct `soil_tools` imports in the named tests.

**Reference implementations:** current `tools\__init__.py`; `tests\test_server.py` tool discovery assertions.

**Acceptance:** `uv run pytest tests\test_tools.py tests\test_server.py tests\test_phase2_contracts.py tests\test_phase3_contracts.py` passes and server discovery reports all ten names.

### 38.5.1 — Remove monolith and validate

**Repository:** `D:\workspace\fpac-soil-mcp`

**Files in scope:** `tools\soil_tools.py`, `planning/STATE_38.md`, and `planning/tasks/38.5.1.todo.md`.

**Depends on:** 38.4.1.

**Spec:** Delete the obsolete `soil_tools.py` once no references remain, run the required offline validation, and record exact results and any deviations in `STATE_38.md`.

**Do not touch:** any source/test file beyond the obsolete module, prior plans, manifests, or unrelated worktree changes.

**Grep anchors:** repository-wide `soil_tools`, `register_soil_tools`, `from fpac_soil_mcp.tools`.

**Reference implementations:** `AGENTS.md` validation workflow; `planning\STATE_37.md` final validation report.

**Acceptance:** no executable source or test references the removed module; `uv run ruff check .`, `uv run ruff format --check .`, and `uv run pytest -m "not live_network"` pass.
