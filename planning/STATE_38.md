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
| 1 | 38.1.1 | pending |
| 2 | 38.2.1 | pending |
| 3 | 38.3.1 | pending |
| 4 | 38.4.1 | pending |
| 5 | 38.5.1 | pending |

## Task reports

<!-- Append one concise report under each task heading. Include status, changed files/line ranges, exact validation commands and results, deviations, and dependent-task gotchas. -->

## 38.1.1

## 38.2.1

## 38.3.1

## 38.4.1

## 38.5.1
