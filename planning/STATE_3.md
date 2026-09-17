# STATE 3: Phase 1 Domain, Governance, and Case State Model

## Green Baseline Checklist

- [x] Orchestrations 1 and 2 are complete.
- [x] Planning inputs read in full: `planning\MASTER_PLAN.md` and `planning\RESEARCH_PUBLIC_APIS_AND_INTERPRETATIONS.md`.
- [x] Repository conventions reviewed: `AGENTS.md`, `pyproject.toml`, prior execution plans, and prior state files.
- [x] Initial worktree status recorded as clean (`git status --short` produced no entries).
- [x] Offline baseline: `uv run pytest -m "not live_sda" -q` -> `42 passed, 3 deselected`.
- [x] Tool versions recorded: `uv 0.12.9`; `Python 3.11.16`.
- [x] Baseline lint: `uv run ruff check .` -> passed.
- [ ] Baseline formatting: `uv run ruff format --check .` -> pre-existing failure in fenced Python examples in `planning\RESEARCH_PUBLIC_APIS_AND_INTERPRETATIONS.md`; Orchestration 3 must not worsen it, and changed Python files must format cleanly.

## Wave Board

| Task ID | Wave | Title | Status | Worker | Assigned At | Completed At |
| --- | --- | --- | --- | --- | --- | --- |
| `3.1.1` | 1 | Authority and Provenance Primitives | pending |  |  |  |
| `3.2.1` | 2 | FPPA Case Domain Models | pending |  |  |  |
| `3.2.2` | 2 | Public Integration Records | pending |  |  |  |
| `3.2.3` | 2 | Public-Only Privacy Policy | pending |  |  |  |
| `3.2.4` | 2 | Official Source Registry | pending |  |  |  |
| `3.2.5` | 2 | Integration Configuration | pending |  |  |  |
| `3.3.1` | 3 | Workflow State Machine | pending |  |  |  |
| `3.4.1` | 4 | Phase 1 Contract Integration | pending |  |  |  |

## Wave Gates

- Wave 1 depends on the recorded baseline; tests and lint are green, and the known documentation-formatting failure is unchanged.
- Wave 2 depends on `3.1.1`.
- Wave 3 depends on `3.2.1` and `3.2.3`.
- Wave 4 depends on every Wave 2 task and `3.3.1`.
- At every wave boundary, run serially:
  - `uv run pytest -m "not live_sda"`
  - `uv run ruff check .`
  - `uv run ruff format --check` on changed Python files, plus `uv run ruff format --check .` to confirm the only repository-wide failure remains the pre-existing research-document examples.
- Live SDA, NASS, and TIGERweb checks are deferred; Orchestration 3 adds no network behavior.

## Task Reports

<!-- Workers append one <=15-line section per task here after execution. -->
