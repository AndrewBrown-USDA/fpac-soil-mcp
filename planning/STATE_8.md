# STATE 8: Code Review Remediation (Standards & Spec Refinements)

## Green Baseline Checklist

- [x] Orchestrations 1 through 7 complete.
- [x] Code review completed for `512e351...HEAD` with 6 action items identified.
- [x] Initial worktree status recorded: clean baseline.
- [x] Baseline test suite verified: `uv run pytest -m "not live_sda" -q` -> `148 passed, 10 deselected`.
- [x] Baseline lint verified: `uv run ruff check .` -> clean.
- [x] Baseline formatting verified: `uv run ruff format --check .` -> clean.

## Wave Board

| Task ID | Wave | Title | Status | Worker | Assigned At | Completed At |
| --- | --- | --- | --- | --- | --- | --- |
| `8.1.1` | 1 | Centralize Regulatory Constants & Types | pending | — | — | — |
| `8.2.1` | 2 | Refactor Corridor Scoring & Strategy Evaluators | pending | — | — | — |
| `8.2.2` | 2 | Typed TIGERweb County Partitioning | pending | — | — | — |
| `8.3.1` | 3 | Alternative Composite LE & Reconciliation Warnings | pending | — | — | — |
| `8.4.1` | 4 | Multi-County Criterion 7 Weighting & Tool Integration | pending | — | — | — |
| `8.5.1` | 5 | End-to-End Phase 3 Contract Suite & Verification | pending | — | — | — |

## Wave Gates

- **Wave 1** depends on baseline. Task `8.1.1` runs solo.
- **Wave 2** depends on `8.1.1`. Tasks `8.2.1` and `8.2.2` touch disjoint files and run in parallel.
- **Wave 3** depends on `8.2.2`. Task `8.3.1` runs solo.
- **Wave 4** depends on `8.2.1` and `8.3.1`. Task `8.4.1` runs solo.
- **Wave 5** depends on `8.4.1`. Task `8.5.1` runs solo.
- At every wave boundary, run serially:
  - `uv run pytest -m "not live_sda"`
  - `uv run ruff check .`
  - `uv run ruff format --check .`

---

## Task Reports

<!-- Worker task completion reports are appended below -->
