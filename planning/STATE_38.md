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
| 2 | 38.2.1 | pending |
| 3 | 38.3.1 | pending |
| 4 | 38.4.1 | pending |
| 5 | 38.5.1 | pending |

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

## 38.3.1

## 38.4.1

## 38.5.1
