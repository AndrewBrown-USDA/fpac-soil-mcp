# STATE 11: PR #5 Code Review Findings Remediation

## Green Baseline Checklist

- [x] Orchestrations 1 through 10 complete.
- [x] Baseline test suite verified: `uv run pytest -m "not live_sda" -q` -> `172 passed, 10 deselected`.
- [x] Baseline lint verified: `uv run ruff check .` -> clean.
- [x] Baseline formatting verified: `uv run ruff format --check .` -> clean.

## Wave Board

| Task ID | Wave | Title | Status | Worker | Assigned At | Completed At |
| --- | --- | --- | --- | --- | --- | --- |
| `11.1.1` | 1 | HTTP Client Retry Disambiguation & Unit Tests | pending | unassigned | - | - |
| `11.2.1` | 2 | NASS Client Positional Compatibility & 404 Mapping | pending | unassigned | - | - |
| `11.2.2` | 2 | Corridor Analysis Partition Geometry & Segment Compatibility | pending | unassigned | - | - |
| `11.3.1` | 3 | Full Suite Verification & Code Cleanliness | pending | unassigned | - | - |

## Wave Gates

- **Wave 1** depends on baseline. Task `11.1.1` runs solo.
- **Wave 2** depends on `11.1.1`. Tasks `11.2.1` and `11.2.2` touch disjoint files and run in parallel (max 2 workers).
- **Wave 3** depends on `11.2.1` and `11.2.2`. Task `11.3.1` runs solo.
- At every wave boundary, run serially:
  - `uv run pytest -m "not live_sda"`
  - `uv run ruff check .`
  - `uv run ruff format --check .`

---

## Task Reports

<!-- Subagents append task outcome reports here upon completion -->
