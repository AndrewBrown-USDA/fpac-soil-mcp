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
| 5 | 45.5.1 Correct registry mappings against eCFR | done |
| 5 | 45.5.2 Align LESA criterion 7 and unavailable LE semantics | done |
| 5 | 45.5.3 Enforce fact authority, conflicts, and corridor variants | done |
| 5 gate | Registry, LESA, and fact-authority validation | passed |
| 6 | 45.5.4 Reconcile coverage, provenance, and geometry/type validation | done |
| 6 | 45.5.5 Repair Databricks evaluation coverage and evidence | done |
| 6 | 45.6.1 Synchronize dependent regression assertions | done |
| 6 gate | Databricks remediation validation | passed |

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

### Original triage board (superseded by the amendment below)

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

## Databricks review amendment

- **Review commit pulled:** `6549d26`; reusable `scripts\fetch_ecfr.py`,
  `make ecfr`, `make ecfr-check`, and checked-in Part 657/658 references are
  now available.
- **Decision status:** DB45-05 resolved by D9 (analyst percentage accepted with
  explicit provenance while spatial adjacency remains deferred); DB45-08
  resolved by D9 (human-entered facts are analyst-proposed/user-provided, not
  machine estimates); DB45-11 resolved by D10 (align criterion 7 to CFR);
  DB45-15 resolved by D11 (reject LineString/site mismatch).
- **Remediation wave:** 45.5.1-45.5.5 added to `EXECUTION_PLAN_45.md`;
  implementation is pending.

### Updated triage board

| ID | Disposition after amendment |
|---|---|
| DB45-01 | Wave 5 / 45.5.1 |
| DB45-02 | Wave 5 / 45.5.2 |
| DB45-03 | Wave 5 / 45.5.3 |
| DB45-04 | Wave 5 / 45.5.3 |
| DB45-05 | Resolved by D9; implement in 45.5.1/45.5.3 |
| DB45-06 | Wave 5 / 45.5.3 |
| DB45-07 | Wave 5 / 45.5.3 |
| DB45-08 | Resolved by D9; implement in 45.5.3 |
| DB45-09 | Wave 5 / 45.5.4 |
| DB45-10 | Wave 5 / 45.5.2 |
| DB45-11 | Resolved by D10; implement in 45.5.2 |
| DB45-12 | Wave 5 / 45.5.4 |
| DB45-13 | Wave 5 / 45.5.1 |
| DB45-14 | Wave 5 / 45.5.4 |
| DB45-15 | Resolved by D11; implement in 45.5.4 |
| DB45-E1 | Wave 5 / 45.5.5 |
| DB45-E2 | Wave 5 / 45.5.5 |
| DB45-E3 | Wave 5 / 45.5.5 |
| DB45-E4 | Out of scope; retained as Plan 44 follow-up |
| DB45-N1 | Documented in Databricks review; validate when credentials exist |
| DB45-N2 | Recorded existing limitation |

## 45.5.3

- **Status:** implemented; targeted acceptance passed.
- **Files:** `tools\lesa_tools.py`, `models.py`, `tests\test_tools.py`, and task TODO.
- **Checks:** final `uv run pytest tests\test_tools.py -q` -> 40 passed, including rerun after error-message compatibility adjustment.
- **Lint/format:** scoped `ruff check` passed; `ruff format --check` reports both Python files formatted.
- **Changes:** human facts retain analyst authority and evidence metadata; conflicts, invalid values, unmet rationale/verification, and out-of-range points are rejected.
- **Corridor:** criteria 8/11 use corridor maxima; criteria 5/6 remain statutorily zeroed, and nonzero overrides are rejected.
- **Compatibility:** negative `max_points` retains the established `max_points cannot be negative` error message; non-finite values remain rejected.
- **Type validation:** non-mapping fact/override inputs raise explicit `TypeError` messages; invalid values otherwise retain validation errors.
- **Deviations:** none; no registry or generated eCFR files changed.
- **Gotchas:** the first test attempt caught the registry during an intermediate invalid update; final targeted run passed against the updated contract.

## 45.5.4

- **Status:** implemented; targeted acceptance passed.
- **Files:** `corridor_analysis.py`, `tools\lesa_tools.py`, `models.py`,
  `tests\test_corridor_analysis.py`, `tests\test_tools.py`, and task TODO.
- **Changes:** LESA coverage is normalized to `covered`, `partial`, `unrated`,
  `unmapped`, or `unknown`; polygon and corridor summaries carry acreage,
  coverage percentage, and selected rating-source provenance/notices.
- **Geometry:** line geometry with default/site project type is explicitly
  rejected; valid corridor lines and site polygons remain supported.
- **Authority:** missing LE remains unavailable and threshold-indeterminate;
  preliminary-screening limitations remain in force.
- **Checks:** targeted pytest -> 74 passed; scoped Ruff check and format check
  passed. Existing pytest-asyncio and Shapely deprecation warnings remain.
- **Deviations:** none; no commit created.

## 45.5.2

- **Status:** implemented; targeted acceptance passed.
- **Files:** `lesa.py`, `polygon_analysis.py`, `tests/test_lesa.py`,
  `tests/test_polygon_analysis.py`, and task TODO.
- **Changes:** criterion 7 now follows the CFR 5%-deduction schedule; zero
  rated acreage is unavailable and threshold-indeterminate; factual criterion 7
  awards 0 at exactly 50% below average.
- **Checks:** `uv run pytest tests\test_lesa.py tests\test_polygon_analysis.py -q`
  -> 75 passed; targeted `uv run ruff format --check` over all four scoped
  source/test files passed after formatting `polygon_analysis.py`.
- **Deviations:** none.
- **Gotchas:** none.

## 45.5.1

- **Status:** implemented.
- **Files:** Site Assessment registry, typed validation/scoring helpers, fixture-driven contract tests, CFR fixture, and task TODO.
- **Mapping:** Criteria 1–12 are anchored to 7 CFR § 658.5(b)(1)–(12), including explicit interval endpoints, score direction, CFR deduction/multi-service schedules, and representative-value conventions.
- **Criterion 2:** Analyst percentages score only with provenance; spatial evidence remains explicitly deferred/unavailable.
- **Criterion 9 correction:** All required services = 5, some = representative 3 (4-to-1 range; midpoint 2.5 rounded upward), none = 0; score direction is more services, more points.
- **Unknowns:** Unknown/unavailable inputs remain unscored; out-of-band numeric values do not match a score band.
- **Checks:** `uv run pytest tests\test_site_assessment_contract.py -q` -> 12 passed; targeted Ruff check passed; targeted Ruff format check passed.
- **Deviations:** none; generated eCFR files and unrelated concurrent task changes were untouched.

## 45.5.5

- **Status:** implemented; targeted acceptance passed.
- **Files:** T1 dataset loader, Databricks scorer labels and README, both evaluation catalogs, offline contract test, and task TODO.
- **Cases:** SA-MA-01..04 now load in T1; tool cases carry matching GeoJSON, expected tool arguments, grounded facts, and model-assisted labels.
- **Safety:** missing Site Assessment inputs remain unavailable/incomplete; no case rewards fabricated points or siting advice.
- **Dataset:** `evidence_tier` is validated and preserved in MLflow expectations; dataset version is 2.0.2.
- **Evidence:** deterministic scorer outputs remain `deterministic_contract`; judge outputs remain `model_assisted`.
- **Checks:** `uv run pytest tests\eval\test_phase4_databricks_contract.py eval\databricks\test_databricks_scorers.py -q` -> 16 passed.
- **Checks:** `uv run pytest eval\common\test_common_dataset.py eval\databricks\test_databricks_dry_run.py -q` -> 30 passed.
- **Independent gate:** `uv run pytest eval\contract\test_contract.py -q` -> 13 passed.
- **Lint/format:** scoped Ruff check passed; all three changed Python files passed format check.
- **Databricks:** evaluation not invoked because credentials were not confirmed; README records the serverless uv/session-Python limitation without masking failures.
- **Deviations:** none; DB45-E4 remains out of scope and no commit was made.

## 45.6.1

- **Status:** implemented; targeted acceptance passed.
- **Files:** three dependent regression test files and task TODO.
- **Changes:** criterion-7 description and deduction assertions now match the CFR schedule; exactly 50% below average expects 0 points; T1 `--all` dry run expects 24 records.
- **Checks:** targeted pytest -> 27 passed; `make check` -> 783 passed, 45 deselected; Ruff check and format passed.
- **Deviations:** none; no commit created.
