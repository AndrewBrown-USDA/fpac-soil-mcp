# STATE 12: Production Dockerfile Hardening & FastMCP Prompt Suite Expansion

## Green Baseline Checklist

- [x] Orchestrations 1 through 11 complete.
- [x] Baseline test suite verified: `uv run pytest -m "not live_sda" -q` -> `184 passed, 10 deselected`.
- [x] Baseline lint verified: `uv run ruff check .` -> clean.
- [x] Baseline formatting verified: `uv run ruff format --check .` -> clean.

## Wave Board

| Task ID | Wave | Title | Status | Worker | Assigned At | Completed At |
| --- | --- | --- | --- | --- | --- | --- |
| `12.1.1` | 1 | Production Dockerfile Enhancement & .dockerignore | done | coordinator | 2026-09-22T09:48:10Z | 2026-09-22T09:51:00Z |
| `12.1.2` | 1 | FastMCP Prompt Suite Expansion | done | coordinator | 2026-09-22T09:48:10Z | 2026-09-22T09:51:00Z |
| `12.2.1` | 2 | Comprehensive FastMCP Prompt & Server Test Suite | done | coordinator | 2026-09-22T09:51:30Z | 2026-09-22T09:53:30Z |
| `12.2.2` | 2 | Manifest & Documentation Synchronization | done | coordinator | 2026-09-22T09:51:30Z | 2026-09-22T09:53:30Z |

## Wave Gates

- **Wave 1** depends on baseline. Tasks `12.1.1` and `12.1.2` touch disjoint files and run in parallel (max 2 workers).
- **Wave 2** depends on Wave 1 completion. Tasks `12.2.1` and `12.2.2` touch disjoint files and run in parallel (max 2 workers).
- At every wave boundary, run serially:
  - `uv run pytest -m "not live_sda"`
  - `uv run ruff check .`
  - `uv run ruff format --check .`

---

## Task Reports

### Task 12.2.1 Report: Comprehensive FastMCP Prompt & Server Test Suite
- **Files Modified**: `tests/test_server.py`, `planning/tasks/12.2.1.todo.md`
- **Accomplishments**:
  - Expanded `TestResourcesAndPrompts` in `tests/test_server.py` to comprehensively test all 4 FastMCP prompts (`fppa_screening_assistant`, `fppa_corridor_screening_assistant`, `fppa_urban_exemption_assistant`, and `fppa_site_assessment_assistant`).
  - Added assertions checking tool references across all 9 tools, statutory rule references (7 CFR § 658.5(c), 7 CFR § 658.2(a), 7 CFR § 658.4 thresholds), Form AD-1006 / NRCS-CPA-106 selections, and regulatory resource links.
  - Added test checking prompt registration on `create_mcp_server()`.
  - Verified with `pytest` and `ruff`.

### Task 12.2.2 Report: Manifest & Documentation Synchronization
- **Files Modified**: `manifest.yaml`, `README.md`, `planning/tasks/12.2.2.todo.md`
- **Accomplishments**:
  - Updated `manifest.yaml` with prompt definitions and argument specs for all 4 prompts.
  - Updated `README.md` architecture diagram (4 Prompts Registry), multi-stage Docker container documentation, and detailed Prompts documentation section.
  - Verified full test suite (`188 passed, 10 deselected`) and formatting checks.
