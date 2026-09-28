# STATE 18: Code Review Remediation & Generalized SDV Routing

## Green Baseline Checklist

- [x] Baseline test suite verified: `uv run pytest -m "not live_network and not agent_eval" -q` -> `235 passed, 12 deselected`.
- [x] Baseline lint verified: `uv run ruff check .` -> clean.
- [x] Baseline formatting verified: `uv run ruff format --check .` -> clean.

## Wave Board

| Task ID | Wave | Title | Status | Worker | Assigned At | Completed At |
| --- | --- | --- | --- | --- | --- | --- |
| `18.1.1` | 1 | Generalized Dynamic SDV Attribute Query Engine in SDA Client | pending | unassigned | - | - |
| `18.1.2` | 1 | Model Bounds Enforcement & Server Registry Sync | pending | unassigned | - | - |
| `18.2.1` | 2 | Sentinel Null Screening, Strict Percentile Math & LESA Engine Cleanup | pending | unassigned | - | - |
| `18.2.2` | 2 | Unit, Mocked & Benchmark Verification Suite Expansion | pending | unassigned | - | - |
| `18.3.1` | 3 | End-to-End Test Suite Verification, State & Documentation Finalization | pending | unassigned | - | - |

## Wave Gates

- **Wave 1** runs 2 independent tasks (`18.1.1`, `18.1.2`) across disjoint files (`src/fpac_soil_mcp/sda_client.py` and `src/fpac_soil_mcp/models.py` / `server.json`).
- **Wave 2** depends on Wave 1 and runs 2 independent tasks (`18.2.1`, `18.2.2`) across disjoint files (`src/fpac_soil_mcp/lesa.py` and `tests/test_sda_client.py` / `tests/test_lesa.py`).
- **Wave 3** depends on Wave 2 and finalizes end-to-end verification and state documentation.
- At every wave boundary, run serially:
  - `uv run pytest -m "not live_network and not agent_eval" -q`
  - `uv run ruff check .`
  - `uv run ruff format --check .`

---

## Task Reports

<!-- Task reports will be appended here as tasks complete -->
