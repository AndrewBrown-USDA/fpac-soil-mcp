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
| `3.1.1` | 1 | Authority and Provenance Primitives | done | orchestrator | 2026-09-16 | 2026-09-16 |
| `3.2.1` | 2 | FPPA Case Domain Models | done | orchestrator | 2026-09-16 | 2026-09-16 |
| `3.2.2` | 2 | Public Integration Records | done | orchestrator | 2026-09-16 | 2026-09-16 |
| `3.2.3` | 2 | Public-Only Privacy Policy | done | orchestrator | 2026-09-16 | 2026-09-16 |
| `3.2.4` | 2 | Official Source Registry | done | orchestrator | 2026-09-16 | 2026-09-16 |
| `3.2.5` | 2 | Integration Configuration | done | orchestrator | 2026-09-16 | 2026-09-16 |
| `3.3.1` | 3 | Workflow State Machine | done | orchestrator | 2026-09-16 | 2026-09-16 |
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

## 3.1.1
- **Status**: Complete.
- **Files changed**: `src/fpac_soil_mcp/authority.py` (lines 1-224), `tests/test_authority.py` (lines 1-210), `planning/tasks/3.1.1.todo.md` (lines 1-32).
- **Targeted tests**: `uv run pytest tests\test_authority.py -q` -> 9 passed in 0.04s.
- **Deviations**: None.
- **Gotchas for dependent tasks**: `AuthorityValue` requires complete `Attestation` with appropriate `ActorCategory` (`agency_official` or `nrcs_official`) for privileged authority states; naive datetimes and blank strings are rejected.

## 3.2.1
- **Status**: Complete.
- **Files changed**: `src/fpac_soil_mcp/case_models.py` (lines 1-240), `tests/test_case_models.py` (lines 1-210), `planning/tasks/3.2.1.todo.md` (lines 1-32).
- **Targeted tests**: `uv run pytest tests\test_case_models.py -q` -> 8 passed in 0.04s.
- **Deviations**: None.
- **Gotchas for dependent tasks**: `FppaCase` validates consistency between `request.case_id` and `case_id`, and checks uniqueness across impact areas, claims, runs, and decisions.

## 3.2.2
- **Status**: Complete.
- **Files changed**: `src/fpac_soil_mcp/integration_models.py` (lines 1-205), `tests/test_integration_models.py` (lines 1-160), `planning/tasks/3.2.2.todo.md` (lines 1-32).
- **Targeted tests**: `uv run pytest tests\test_integration_models.py -q` -> 6 passed in 0.03s.
- **Deviations**: None.
- **Gotchas for dependent tasks**: All integration records require valid `Provenance` even in error or unavailable status; numeric ratings and percentages strictly bounded.

## 3.2.3
- **Status**: Complete.
- **Files changed**: `src/fpac_soil_mcp/privacy.py` (lines 1-140), `tests/test_privacy.py` (lines 1-125), `planning/tasks/3.2.3.todo.md` (lines 1-32).
- **Targeted tests**: `uv run pytest tests\test_privacy.py -q` -> 4 passed in 0.02s.
- **Deviations**: None.
- **Gotchas for dependent tasks**: `assert_public_payload` raises `ProhibitedPersonalDataError` listing field paths without leaking values; `sanitize_public_payload` returns a sanitized copy without mutating input.

## 3.2.4
- **Status**: Complete.
- **Files changed**: `src/fpac_soil_mcp/official_sources.py` (lines 1-155), `src/fpac_soil_mcp/data/official_sources.v1.json`, `src/fpac_soil_mcp/data/regional_scoring.v1.json`, `tests/test_official_sources.py` (lines 1-70), `planning/tasks/3.2.4.todo.md` (lines 1-32).
- **Targeted tests**: `uv run pytest tests\test_official_sources.py -q` -> 4 passed in 0.03s.
- **Deviations**: None.
- **Gotchas for dependent tasks**: Data files loaded from package resources; regional scoring registry starts empty by design.

## 3.2.5
- **Status**: Complete.
- **Files changed**: `src/fpac_soil_mcp/config.py` (lines 1-145), `.env.example`, `tests/test_config.py` (lines 1-55), `planning/tasks/3.2.5.todo.md` (lines 1-32).
- **Targeted tests**: `uv run pytest tests\test_config.py tests\test_server.py -q -m "not live_sda"` -> 13 passed in 0.09s.
- **Deviations**: None.
- **Gotchas for dependent tasks**: `Settings` supports SDA-only startup without NASS key, but fails if `nass_enabled=True` without a key or when `validate_nass_capability()` is invoked.

## 3.3.1
- **Status**: Complete.
- **Files changed**: `src/fpac_soil_mcp/workflow.py` (lines 1-135), `tests/test_workflow.py` (lines 1-220), `planning/tasks/3.3.1.todo.md` (lines 1-32).
- **Targeted tests**: `uv run pytest tests\test_workflow.py -q` -> 5 passed in 0.07s.
- **Deviations**: None.
- **Gotchas for dependent tasks**: Transitions return a new `FppaCase` instance and validate preconditions (public policy checks for readiness, completed runs for analysis completion, decisions for provisional completion, rationale + actor for closure).


