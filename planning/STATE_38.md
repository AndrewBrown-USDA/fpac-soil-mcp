# Orchestration 38 State

## Baseline

- **Repository:** `D:\workspace\fpac-soil-mcp`
- **Purpose:** domain-oriented refactor of MCP tool modules for issue #25; one-tool-per-file is explicitly not the target.
- **Tool inventory:** 10 MCP tools: 8 currently in `soil_tools.py`, 2 in `fppa_tools.py`.
- **Baseline:** `uv run pytest -m "not live_network"` -> 476 passed, 3 skipped, 22 deselected; `uv run ruff check .` passed; `uv run ruff format --check .` passed (461 files).
- **Baseline identity:** working tree inspected on 2026-10-27; branch/HEAD and unrelated dirty-file status must be refreshed by task 38.1.1 before edits.
- **Architecture constraints:** centralized registration through `tools\__init__.py`; preserve MCP names/behavior; ADR 0001 modular registration and ADR 0003 authority boundary remain active.
- **Decisions:** domain-oriented five-module split; internal Python import-path breaks allowed; serial waves with max two workers; offline suite required, live tests deferred.

## Wave board

| Wave | Task | Status |
|---|---|---|
| 1 | 38.1.1 | done |
| 2 | 38.2.1 | done |
| 3 | 38.3.1 | done |
| 4 | 38.4.1 | done |
| 5 | 38.5.1 | done |

## Task reports

<!-- Append one concise report under each task heading. Include status, changed files/line ranges, exact validation commands and results, deviations, and dependent-task gotchas. -->

## 38.1.1

- **Status:** complete (2026-10-27).
- **Repository baseline:** branch `v040`, HEAD `d69a6ef3f02351da0137836293a72b1ecee0488a`; initial status was `## v040` with one pre-existing untracked file, `planning/tasks/38.1.1.todo.md`. No tracked files were modified.
- **Validation:** `uv run pytest -m "not live_network"` -> `476 passed, 3 skipped, 22 deselected` (498 collected; 104 warnings; 33.48s). `uv run ruff check .` -> `All checks passed!`. `uv run ruff format --check .` -> `465 files already formatted`.
- **Current tool-to-module map:** `get_farmland_classification_by_point` -> `soil_tools.py` (planned `soil_lookup_tools.py`); `get_farmland_classification_by_mukey` -> `soil_tools.py` (planned `soil_lookup_tools.py`); `get_soil_interpretations` -> `soil_tools.py` (planned `soil_lookup_tools.py`); `get_soil_polygons_by_geometry` -> `soil_tools.py` (planned `soil_lookup_tools.py`); `check_urban_area_exemption` -> `soil_tools.py` (planned `exemption_tools.py`); `analyze_farmland_by_polygon` -> `soil_tools.py` (planned `spatial_analysis_tools.py`); `analyze_corridor_fppa` -> `soil_tools.py` (planned `spatial_analysis_tools.py`); `calculate_preliminary_lesa` -> `soil_tools.py` (planned `lesa_tools.py`); `explain_fppa_screening_scope` -> `fppa_tools.py` (retained); `list_farmland_classes` -> `fppa_tools.py` (retained).
- **Registration:** `tools\__init__.py` is the centralized public export and `register_tools(mcp)` boundary; it currently calls `register_soil_tools(mcp)` and `register_fppa_tools(mcp)`. `app.py` imports only `register_tools`.
- **Direct imports and affected import surface:** `tests\test_tools.py` directly imports all eight soil functions and patches `fpac_soil_mcp.tools.soil_tools` collaborators; `tests\test_server.py` directly imports `get_farmland_classification_by_point`; `tests\test_phase3_contracts.py` directly imports `analyze_corridor_fppa` and patches `soil_tools.SDAClient`/`CorridorAnalyzer`; `eval\contract\test_contract.py` patches `soil_tools.SDAClient`. `tests\test_phase2_contracts.py` and `tests\test_phase3_contracts.py` import `register_tools`; `app.py` imports `register_tools`. These are the known updates for wave 38.4.1 (plus patch targets moved with implementations).
- **ADR confirmation:** ADR 0001 requires FastMCP with modular registration and a `src\` package layout; the planned cohesive modules comply and do not conflict. ADR 0003 requires the preliminary-screening authority boundary and regulatory notices on screening responses; extraction must preserve those response fields and notices. No active ADR conflict found.
- **Dependent-task gotchas:** preserve decorators, signatures, docstrings, imports, patchable collaborators, ten public MCP names, and centralized registration. Do not add compatibility re-exports from `soil_tools.py`; live-network tests remain deferred.

## 38.2.1

- **Status:** complete (2026-10-27).
- **Changes:** extracted four lookup tools to `soil_lookup_tools.py` and the urban exemption tool to `exemption_tools.py`; removed duplicate implementations from `soil_tools.py`; preserved temporary imports for the later registration rewiring.
- **Validation:** repository search found exactly one implementation per moved function. Targeted command `uv run pytest tests\test_tools.py -k "classification or interpretation or polygon or urban"` -> 10 failed, 4 passed, 11 deselected because tests still patch `soil_tools.SDAClient`; this is the planned wave 4 import/patch-target update.
- **Deviations:** targeted tests cannot pass until task 38.4.1 rewires registration and test patch targets; no broader tests were run.
- **Gotchas:** new modules own the moved collaborators; dependent tasks must update direct imports and patches without changing public MCP names.

## 38.3.1

- **Status:** complete (2026-10-27).
- **Changes:** extracted polygon/corridor analysis to `spatial_analysis_tools.py` and preliminary LESA to `lesa_tools.py`; removed duplicate implementations from `soil_tools.py`.
- **Validation:** focused imports/compilation passed. `uv run pytest tests\test_tools.py -k "farmland or corridor or lesa"` -> 5 passed, 16 failed, 4 deselected because tests still patch collaborators on `soil_tools`; task 38.4.1 owns those updates.
- **Deviations:** corrected an accidental duplicate `analyze_farmland_by_polygon` found during review; it now exists only in `spatial_analysis_tools.py`.
- **Gotchas:** task 38.4.1 must rewire centralized registration and all direct imports/patch targets while preserving the ten MCP names.

## 38.4.1

- **Status:** complete (2026-10-27).
- **Changes:** rewired `tools\__init__.py` registration and exports for all five domain modules; updated direct test imports and collaborator patch targets in the scoped tests.
- **Validation:** `uv run pytest tests\test_tools.py tests\test_server.py tests\test_phase2_contracts.py tests\test_phase3_contracts.py` -> 54 passed, 3 deselected.
- **Deviation:** restored the existing `ProductivityIndexType` import in `lesa_tools.py`, a tightly coupled extraction omission discovered by the targeted suite.
- **Gotchas:** final wave must verify the removed `soil_tools.py` has no executable/test references and run the full offline suite.

## 38.5.1

- **Status:** complete (2026-10-27).
- **Changes:** updated `eval\contract\test_contract.py` collaborator patches from `fpac_soil_mcp.tools.soil_tools.SDAClient` to the owning `fpac_soil_mcp.tools.soil_lookup_tools.SDAClient`; deleted `src\fpac_soil_mcp\tools\soil_tools.py`; updated this state report and the task todo.
- **Reference gate:** post-update searches found no executable source or test/evaluation references to `soil_tools.py`, `soil_tools`, or `register_soil_tools`. The deleted path is absent. `tools\__init__.py` retains the eight extracted soil tools plus the two FPPA tools, preserving all ten public MCP tool registrations through `register_tools`.
- **Validation:** `uv run ruff check .` -> exit 0, `All checks passed!`; `uv run ruff format --check .` -> exit 0, `472 files already formatted`; `uv run pytest -m "not live_network"` -> exit 0, 498 collected, 22 deselected, 3 skipped, 476 passed, 0 failed, 104 warnings (32.47s).
- **Changed files:** `src\fpac_soil_mcp\tools\__init__.py`, `src\fpac_soil_mcp\tools\lesa_tools.py`, `src\fpac_soil_mcp\tools\soil_lookup_tools.py`, `src\fpac_soil_mcp\tools\spatial_analysis_tools.py`, `src\fpac_soil_mcp\tools\soil_tools.py` (deleted), `tests\test_tools.py`, `eval\contract\test_contract.py`, `planning\STATE_38.md`, and `planning\tasks\38.5.1.todo.md`. The pre-existing `planning\EXECUTION_PLAN_38.md` modification was left untouched.
- **Deviations:** none. Live-network tests were not run.
