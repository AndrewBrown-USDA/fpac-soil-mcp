# Orchestration 45 State

## Baseline

- **Repository:** `D:\workspace\fpac-soil-mcp`
- **Plan date:** 2026-11-09
- **Highest prior orchestration:** 44
- **Offline baseline:** `uv run pytest -q -m "not live_network and not agent_eval"` ->
  705 passed, 3 skipped, 45 deselected.
- **Known warnings:** existing pytest-asyncio configuration warning and Shapely
  `shapely.ops.transform` deprecation warnings.
- **Entry-point sizes:** `lesa.py` 889 lines; `corridor_scoring.py` 468;
  `models.py` 654; `tools\lesa_tools.py` 175; `tests\test_lesa.py` 709;
  `eval\prompt_test_cases.json` 583.
- **Required baseline commands before execution:** `make check`; if upstream
  behavior is changed, `uv run pytest -m live_network`; if evaluation code is
  changed, `make test-eval` and/or `make eval-databricks`.
- **Architectural constraints:** ADR 0002 fixed SQL; ADR 0003 preliminary
  authority; ADR 0007 unified LESA; ADR 0011 mocked default/live opt-in;
  ADR 0014 validated metadata registry.

## Wave board

| Wave | Task | Status |
|---|---|---|
| 1 | 45.1.1 Define Site Assessment question and scoring registry | done |
| 1 | 45.1.2 Add typed incomplete/authority result semantics | done |
| 1 | gate Site Assessment contract | passed |
| 2 | 45.2.1 Wire fact-based inputs and question resource | pending |
| 2 | 45.2.2 Correct wording and authority gaps | pending |
| 2 | gate Site Assessment integration | pending |
| 3 | 45.3.1 Preserve selected property through aggregation | pending |
| 3 | 45.3.2 Reconcile coverage, maxima, and provenance | pending |
| 3 | gate aggregation and relevant live tests | pending |
| 4 | 45.4.1 Build deterministic gold-set evidence | pending |
| 4 | 45.4.2 Separate model-assisted evidence and diagnostics | pending |
| 4 | 45.4.3 Synchronize docs and closeout evidence | pending |
| 4 | gate final validation and review | pending |

## Task Reports

<!-- Append one report per task, maximum 15 lines. -->

## 45.1.1

- **Status:** done.
- **Files:** versioned Site Assessment registry JSON, typed loader/validators,
  focused contract tests, and `planning/tasks/45.1.1.todo.md`.
- **Checks:** targeted registry tests 9 passed; Ruff check and format clean.
- **Deviations:** none.
- **Gotchas:** adjacency remains explicitly deferred/unavailable.

## 45.1.2

- **Status:** done.
- **Files:** `lesa.py`, `models.py`, `tests/test_lesa.py`,
  dependent criterion-2 fixture in `tests/test_phase3_contracts.py`, and TODO.
- **Checks:** targeted LESA/phase-3 tests 59 passed; full gate 718 passed,
  3 skipped, 45 deselected; Ruff check and format clean.
- **Deviations:** dependent fixture gained required override rationale.
- **Gotchas:** analyst-proposed point overrides now require non-empty rationale.

