# STATE 4: Phase 2 Polygon AOI Screening & Farmland Analysis

## Green Baseline Checklist

- [x] Orchestrations 1, 2, and 3 are complete.
- [x] Planning inputs read in full: `planning\MASTER_PLAN.md` (Phase 2), `planning\RESEARCH_PUBLIC_APIS_AND_INTERPRETATIONS.md`, and py-soildb spatial query reference implementation.
- [x] Repository conventions reviewed: `AGENTS.md`, `pyproject.toml`, prior execution plans, and prior state files.
- [x] Initial worktree status recorded as clean (`git status --short` produced no unexpected entries).
- [x] Offline baseline: `uv run pytest -m "not live_sda" -q` -> `82 passed, 3 deselected`.
- [x] Tool versions recorded: `uv 0.12.9`; `Python 3.11.16`.
- [x] Baseline lint: `uv run ruff check .` -> passed.
- [ ] Baseline formatting: `uv run ruff format --check .` -> pre-existing failure in fenced Python examples in `planning\RESEARCH_PUBLIC_APIS_AND_INTERPRETATIONS.md`; changed Python files must format cleanly.

## Wave Board

| Task ID | Wave | Title | Status | Worker | Assigned At | Completed At |
| --- | --- | --- | --- | --- | --- | --- |
| `4.1.1` | 1 | Spatial Primitives & Geometry Engine | pending | - | - | - |
| `4.2.1` | 2 | SDA Spatial & Interpretation Engine | pending | - | - | - |
| `4.2.2` | 2 | Census TIGERweb Urban Area Client | pending | - | - | - |
| `4.2.3` | 2 | 50-AOI Benchmark Fixtures & Validation | pending | - | - | - |
| `4.3.1` | 3 | Polygon Analysis Engine & Response Models | pending | - | - | - |
| `4.4.1` | 4 | FastMCP Polygon Screening Tools | pending | - | - | - |
| `4.5.1` | 5 | Phase 2 Contract & Regression Suite | pending | - | - | - |

## Wave Gates

- **Wave 1** depends on the recorded baseline; tests and lint are green.
- **Wave 2** depends on `4.1.1` (geometry engine and spatial dependencies). Tasks `4.2.1`, `4.2.2`, and `4.2.3` have disjoint files and can run in parallel worktrees (up to 3 concurrent workers).
- **Wave 3** depends on `4.2.1`, `4.2.2`, and `4.2.3`.
- **Wave 4** depends on `4.3.1`.
- **Wave 5** depends on `4.4.1`.
- At every wave boundary, run serially:
  - `uv run pytest -m "not live_sda"`
  - `uv run ruff check .`
  - `uv run ruff format --check` on changed Python files.

---

## Task Reports

<!-- Worker task completion reports will be appended below (≤15 lines per task) -->
