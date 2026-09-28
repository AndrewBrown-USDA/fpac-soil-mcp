# STATE 17: Phase 4 Implementation - Land Evaluation & Unified LESA Engine

## Green Baseline Checklist

- [ ] Baseline test suite verified: `uv run pytest -m "not live_network and not agent_eval" -q` -> `192 passed, 12 deselected`.
- [ ] Baseline lint verified: `uv run ruff check .` -> clean.
- [ ] Baseline formatting verified: `uv run ruff format --check .` -> clean.

## Wave Board

| Task ID | Wave | Title | Status | Worker | Assigned At | Completed At |
| --- | --- | --- | --- | --- | --- | --- |
| `17.1.1` | 1 | SDV Metadata & Dynamic Productivity Index Queries in SDA Client | pending | unassigned | - | - |
| `17.1.2` | 1 | Unified LESA Domain Models & Score Structures | pending | unassigned | - | - |
| `17.1.3` | 1 | Test Fixtures for State Productivity Ratings & LE Calculations | pending | unassigned | - | - |
| `17.2.1` | 2 | Unified Land Evaluation & LESA Calculation Engine | pending | unassigned | - | - |
| `17.2.2` | 2 | Polygon Analysis Engine Integration with Dynamic LE Scoring | pending | unassigned | - | - |
| `17.3.1` | 3 | MCP Tool Registration for `calculate_preliminary_lesa` & Polygon Integration | pending | unassigned | - | - |
| `17.3.2` | 3 | Unit & Mocked Test Suite for LE Scoring & SDV Routing | pending | unassigned | - | - |
| `17.4.1` | 4 | Benchmark Eval Fixture Suite Expansion for LESA Scoring | pending | unassigned | - | - |
| `17.4.2` | 4 | End-to-End Verification, Documentation & Plan 17 State Finalization | pending | unassigned | - | - |

## Wave Gates

- **Wave 1** runs 3 independent tasks (`17.1.1`, `17.1.2`, `17.1.3`) across disjoint files (`src/fpac_soil_mcp/sda_client.py`, `src/fpac_soil_mcp/models.py`, `tests/fixtures/le_benchmarks.json`).
- **Wave 2** depends on Wave 1 and runs 2 independent tasks (`17.2.1`, `17.2.2`) across disjoint files (`src/fpac_soil_mcp/lesa.py` / `src/fpac_soil_mcp/corridor_scoring.py`, `src/fpac_soil_mcp/polygon_analysis.py`).
- **Wave 3** depends on Wave 2 and runs 2 independent tasks (`17.3.1`, `17.3.2`) across disjoint files (`src/fpac_soil_mcp/tools/soil_tools.py`, `tests/test_lesa.py` / `tests/test_sda_client.py`).
- **Wave 4** depends on Wave 3 and runs 2 sequential/independent tasks (`17.4.1` on `eval/prompt_test_cases.json`, then `17.4.2` for docs/validation).
- At every wave boundary, run serially:
  - `uv run pytest -m "not live_network and not agent_eval" -q`
  - `uv run ruff check .`
  - `uv run ruff format --check .`

---

## Task Reports

### Task 17.1.1 Report: SDV Metadata & Dynamic Productivity Index Queries in SDA Client
- **Status**: pending
- **Files**: `src/fpac_soil_mcp/sda_client.py`
- **Verification**: Pending

### Task 17.1.2 Report: Unified LESA Domain Models & Score Structures
- **Status**: pending
- **Files**: `src/fpac_soil_mcp/models.py`
- **Verification**: Pending

### Task 17.1.3 Report: Test Fixtures for State Productivity Ratings & LE Calculations
- **Status**: pending
- **Files**: `tests/fixtures/le_benchmarks.json`
- **Verification**: Pending

### Task 17.2.1 Report: Unified Land Evaluation & LESA Calculation Engine
- **Status**: pending
- **Files**: `src/fpac_soil_mcp/lesa.py`, `src/fpac_soil_mcp/corridor_scoring.py`
- **Verification**: Pending

### Task 17.2.2 Report: Polygon Analysis Engine Integration with Dynamic LE Scoring
- **Status**: pending
- **Files**: `src/fpac_soil_mcp/polygon_analysis.py`
- **Verification**: Pending

### Task 17.3.1 Report: MCP Tool Registration for `calculate_preliminary_lesa` & Polygon Integration
- **Status**: pending
- **Files**: `src/fpac_soil_mcp/tools/soil_tools.py`, `src/fpac_soil_mcp/tools/__init__.py`
- **Verification**: Pending

### Task 17.3.2 Report: Unit & Mocked Test Suite for LE Scoring & SDV Routing
- **Status**: pending
- **Files**: `tests/test_lesa.py`, `tests/test_sda_client.py`
- **Verification**: Pending

### Task 17.4.1 Report: Benchmark Eval Fixture Suite Expansion for LESA Scoring
- **Status**: pending
- **Files**: `eval/prompt_test_cases.json`
- **Verification**: Pending

### Task 17.4.2 Report: End-to-End Verification, Documentation & Plan 17 State Finalization
- **Status**: pending
- **Files**: `README.md`, `planning/STATE_17.md`, `planning/tasks/17.4.2.todo.md`
- **Verification**: Pending
