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
| 2 | 45.2.1 Wire fact-based inputs and question resource | done |
| 2 | 45.2.2 Correct wording and authority gaps | done |
| 2 | gate Site Assessment integration | passed |
| 3 | 45.3.1 Preserve selected property through aggregation | done |
| 3 | 45.3.2 Reconcile coverage, maxima, and provenance | done |
| 3 | gate aggregation and relevant live tests | passed |
| 4 | 45.4.1 Build deterministic gold-set evidence | done |
| 4 | 45.4.2 Separate model-assisted evidence and diagnostics | done |
| 4 | 45.4.3 Synchronize docs and closeout evidence | done |
| 4 | gate final validation and review | passed |

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

## 45.2.1

- **Status:** done.
- **Files:** LESA tool/resource wiring, registry export helper, tool/resource
  tests, manifest/contract parity updates, and TODO.
- **Checks:** targeted contract/resource tests 33 passed; full gate 724 passed,
  3 skipped, 45 deselected; Ruff clean.
- **Deviations:** dependent manifest and contract assertions updated for the
  new public resource.
- **Gotchas:** resource URI is `fppa://site-assessment-criteria`.

## 45.2.2

- **Status:** done.
- **Files:** constants, FPPA scope/prompt text, focused FPPA/prompt tests,
  dependent server expectations, and TODO.
- **Checks:** targeted wording tests 3 passed; server tests 19 passed/3
  deselected; full gate 724 passed, 3 skipped, 45 deselected.
- **Deviations:** stale “220 points” and resource expectations were updated.
- **Gotchas:** prompts now require registry questions, unknown handling, and
  non-prescriptive consequences.

## 45.3.1

- **Status:** done.
- **Files:** polygon/corridor/LESA aggregation, focused regression tests,
  multi-county productivity fixture, and TODO.
- **Checks:** targeted aggregation suite 65 passed after fixture corrections;
  combined SDV/aggregation suite 140 passed; full gate 731 passed, 3 skipped,
  45 deselected; Ruff clean.
- **Deviations:** none.
- **Gotchas:** selected property and county maxima remain explicit across paths.

## 45.3.2

- **Status:** done.
- **Files:** `sda_client.py`, `models.py`, SDV contract tests, and TODO.
- **Checks:** targeted SDV/multi-county tests 80 passed; `sda_client.py`
  compiles cleanly; full gate 731 passed, 3 skipped, 45 deselected.
- **Deviations:** none.
- **Gotchas:** missing/partial coverage and provenance are explicit states.

## 45.4.1

- **Status:** done.
- **Files:** deterministic gold-set fixture, common dataset/matching support,
  contract registration, focused gold-set tests, and TODO.
- **Checks:** targeted contract suite 17 passed in 1.58 seconds.
- **Deviations:** none; deterministic evidence remains separate from model judges.
- **Gotchas:** unavailable and subjective inputs remain explicit indeterminate states.

## 45.4.2

- **Status:** done.
- **Files:** Pi/Databricks evaluation handling, four model-assisted cases,
  sanitized evidence report, and TODO.
- **Checks:** targeted model-assisted tests 34 passed, 1 skipped, 2 deselected
  in 0.34 seconds with `PYTHONPATH=.`.
- **Deviations:** `make test-eval` requires `PYTHONPATH=.` in this checkout;
  Databricks execution requires configured workspace credentials.
- **Gotchas:** no case rewards fabricated points or siting recommendations.

## 45.4.3

- **Status:** done.
- **Files:** synchronized milestone/public documentation, closeout evidence,
  independent review, and TODO.
- **Checks:** `make check` passed: 737 passed, 3 skipped, 45 deselected;
  targeted model-assisted tests passed as above.
- **Deviations:** `make test-eval` collection failed without `PYTHONPATH=`;
  `make eval-databricks` was blocked by missing default Databricks credentials.
- **Gotchas:** live-network tests were not required because implementation files
  and upstream request behavior were unchanged; deferred adjacency remains explicit.

## Databricks review (2026-11-10)

- **Status:** findings open; awaiting triage and a Plan 45 amendment. Full
  evidence in `planning\REVIEW_45_DATABRICKS.md`, which supersedes the
  "no unresolved findings" disposition in `REVIEW_45.md`.
- **Commit:** `e1645ce` on Databricks serverless (uv 0.13.4, venv Python 3.11).
- **Checks:** offline 738 passed / 3 skipped / 45 deselected (764 / 0 with the
  `eval-databricks` group); live 43 passed; Ruff check and format clean; wheel
  packages `site_assessment.v1.json`; local HTTP discovery shows the new
  resource, prompt, and LESA schema.
- **Real data:** 10 live SDA/TIGERweb LESA calls; T1 MLflow run
  `da4613f3256e4ddf9e474e196b480608` (20 cases); ad hoc SA-MA run
  `127a5e18cab443559f15300acb815cb8`.
- **Recommendation:** blocked for deployment trial; ready for refinement after
  DB45-01 and DB45-02 are fixed and DB45-05, DB45-08, DB45-11 are decided.

### Triage board

| ID | Severity | Summary | Suggested triage | Disposition |
|---|---|---|---|---|
| DB45-01 | High | Registry bands contradict 7 CFR 658.5(b); criteria 5, 6, 7, 9 inverted | Fix in 45 + Decision | open |
| DB45-02 | High | Zero-coverage LE scored 0 and threshold evaluated (predates branch) | Fix in 45 | open |
| DB45-03 | Medium | Corridor criteria 8 and 11 scored on site maximum (10 of 25) | Fix in 45 | open |
| DB45-04 | Medium | Statutorily zeroed corridor criteria relabeled `machine_estimate` | Fix in 45 | open |
| DB45-05 | Medium | Criterion 2 never scorable from facts | Decision | open |
| DB45-06 | Medium | Fact silently overrides analyst override on the same criterion | Fix in 45 | open |
| DB45-07 | Medium | Out-of-range analyst points silently clamped (LESA-01: 120 -> 15) | Fix in 45 + Contract | open |
| DB45-08 | Medium | `requires_rationale`/`requires_verification` not enforced; facts labeled `machine_estimate` | Decision | open |
| DB45-09 | Medium | Corridor LE reports 0% coverage with a nonzero score | Fix in 45 | open |
| DB45-10 | Medium | `evaluate_site_assessment(None, ...)` returns `complete` with 11 unavailable | Fix in 45 | open |
| DB45-11 | Medium | Legacy criterion 7 evaluator not on CFR schedule (predates branch) | Decision | open |
| DB45-12 | Low | `coverage_status` always `unknown`; three vocabularies | Fix in 45 | open |
| DB45-13 | Low | Between-band values become unavailable without explanation | Fix in 45 | open |
| DB45-14 | Low | Rating-source provenance missing from LESA notices | Fix in 45 | open |
| DB45-15 | Low | LINESTRING with default `site` type mixes corridor LE and site SA | Decision | open |
| DB45-E1 | Eval | SA-MA cases not in the T1 dataset | Contract | open |
| DB45-E2 | Eval | SA-MA-02/04 prompts lack geometry | Contract | open |
| DB45-E3 | Eval | Judge noise on LESA-01; null correctness without `expected_facts` | Contract | open |
| DB45-E4 | Eval | LESA-02 WKT input gap (Plan 44 follow-up) | out of scope | open |
| DB45-N1 | Env | `make eval-databricks` needs session Python on serverless | document | open |
| DB45-N2 | Env | `run_evals.py` needs `PYTHONPATH=.` | document | recorded |

- **Deployment:** no app runs this branch; a deployed check needs a dev app
  pointed at `feature/semiquant-sa1` plus a browser check.

