# Orchestration 26 State

## Baseline

- Repository: `D:\workspace\fpac-soil-mcp`
- Prior baseline: `uv run pytest -m "not live_network"` — 328 passed,
  12 deselected.
- Prior lint baseline: `uv run ruff check .` passed.
- Prior format baseline: `uv run ruff format --check .` passed.
- Live SDA tests and pi agent evals are opt-in and must remain separate.
- Maximum two concurrent workers; full-suite verification is serial.

## Wave board

| Wave | Task | Status |
|---|---|---|
| 1 | 26.1.1 Align selectors and unavailable LE semantics | done |
| 2 | 26.2.1 Propagate selector validation through tools | done |
| 3 | 26.3.1 Add productivity and LESA regression tests | done |
| 3 | 26.3.2 Correct the 45-acre evaluation fixture | done |
| 3 | 26.3.3 Diagnose and retry missing eval tools | done |
| 4 | 26.4.1 Add opt-in SDA rule catalog coverage | done |
| 5 | 26.5.1 Run complete verification | done |
| 5 | 26.5.2 Correct verification formatting failures | done |
| 6 | 26.6.1 Remove premature selector surfaces | done |

## Task reports

<!-- Worker reports are appended below, one section per task, <=15 lines. -->

## 26.6.1

- **Status**: complete; public and test contracts now expose validated national NCCPI only.
- **Changes**: removed speculative selector enum members, fixed SDA query/provenance
  branches, caller/metadata claims, unsupported eval cases, product-specific
  rejection parametrizations, and non-NCCPI benchmark fixtures; retained NCCPI and
  metadata-validated dynamic SDV queries.
- **Targeted tests**: `uv run pytest tests\test_models.py tests\test_sda_client.py tests\test_lesa.py tests\test_corridor_analysis.py tests\test_tools.py tests\test_live_sda.py -m "not live_network" -q` — 140 passed, 7 deselected.
- **Offline suite**: `uv run pytest -m "not live_network"` — 295 passed, 12 deselected.
- **Ruff**: `uv run ruff check .` passed; `uv run ruff format --check .` passed with 319 files already formatted.
- **Scope**: changed only task-scoped implementation, metadata, eval/test, and planning files; no live-network tests were run.
- **Corrective review**: removed the stale corridor README claim and CSR2/CPI/Storie
  benchmark fixtures; reran all validations successfully.
- **Deviations**: none.
- **Corrective review**: removed the remaining unsupported corridor README
  description and filtered `tests\fixtures\le_benchmarks.json` to NCCPI cases only.

## 26.5.2

- **Status**: complete; Ruff-only formatting corrections applied.
- **Diagnostics resolved**: `eval\test_agent_eval.py` had one `I001` import-order error;
  `eval\run_evals.py` and `tests\test_geometry.py` were the two unformatted files.
- **Validation**: `uv run ruff check .` — all checks passed.
- **Validation**: `uv run ruff format --check .` — 318 files already formatted.
- **Targeted tests**: `uv run pytest eval\test_agent_eval.py -m "not agent_eval" -q`
  — 7 passed, 2 deselected; `uv run pytest tests\test_geometry.py -q` — 15 passed.
- **Scope**: only the three named code/test files and the two planning files changed.
- **Deviations**: none; no behavior changes or refactors.

## 26.1.1

- **Status**: implemented; targeted tests expose expected stale assertions.
- **Files**: `models.py`, `sda_client.py`, and `lesa.py`; `integration_models.py` and
  `corridor_scoring.py` required no changes.
- **Validation**: `uv run pytest tests\test_sda_client.py tests\test_lesa.py tests\test_corridor_scoring.py -q`
  — 115 passed, 9 failed.
- **Failures**: seven tests expect removed CSR2/CPI/Storie retrieval; two expect
  zero-coverage LE score `0.0` instead of unavailable `None`.
- **Deviations**: legacy enum members remain for deserialization compatibility;
  fixed SDA retrieval rejects them.
- **Gotchas**: dependent tasks must update selector and zero-coverage expectations.

## 26.2.1

- **Status**: implemented; targeted tests expose expected stale selector assertions.
- **Files**: `polygon_analysis.py`, `corridor_analysis.py`, and `tools/soil_tools.py`.
- **Validation**: `uv run pytest tests\test_polygon_analysis.py tests\test_corridor_analysis.py tests\test_tools.py -q`
  — 49 passed, 33 failed; Ruff and `git diff --check` passed.
- **Failures**: existing tests expect removed CSR2/CPI/Storie/custom retrieval.
- **Deviations**: none.

## 26.5.1

- **Status**: complete after 26.5.2 corrective formatting task.
- **Mandatory offline verification**: `uv run pytest -m "not live_network"` — 325 passed, 12 deselected, 0 failed (337 collected; 325 selected), including final rerun after formatting fixes.
- **Ruff lint**: `uv run ruff check .` — failed on both initial run and one permitted identical retry; 1 `I001` import-order error in `eval\test_agent_eval.py`. No source/test edits made.
- **Ruff format**: `uv run ruff format --check .` — failed; 2 files would be reformatted (`eval\run_evals.py`, `tests\test_geometry.py`), 315 already formatted. No source/test edits made.
- **Agent gate**: `pi` available; `uv run pytest eval\test_agent_eval.py -m agent_eval -k "point_screening or affected_productivity_cases"` — 1 passed, 8 deselected, 0 failed.
- **Live SDA gate**: network available; `uv run pytest tests\test_live_sda.py -m live_network -k "rule or productivity"` — 1 passed, 6 deselected, 0 failed.
- **Deviations**: initial Ruff gates failed and were corrected by 26.5.2; final Ruff gates pass. Live and agent gates were run because available.
- **Scope verification**: `git status --short` showed only `planning/tasks/26.5.1.todo.md` before this report; only the two scoped planning files were changed.

## 26.4.1

- **Status**: complete; live gate remains opt-in.
- **Files**: `tests/test_live_sda.py`.
- **Validation**: live rule/productivity selection — 1 passed, 6 deselected;
  Ruff and format passed; `git diff --check` passed.
- **Offline selection**: 7 deselected, exit code 5 because no tests matched;
  no live tests ran in that command.
- **Changes**: tolerant national NCCPI discovery and catalog-independent CSR2
  rejection; stale Storie retrieval coverage removed.

## 26.3.1

- **Status**: complete.
- **Files**: five test modules changed; `tests/test_corridor_scoring.py` required no
  edits because existing unavailable-threshold coverage was sufficient.
- **Validation**: targeted six-module command — 197 passed; focused Ruff lint and
  format checks passed; `git diff --check` passed.
- **Coverage**: unsupported selectors reject before SDA calls; NCCPI, valid zero
  ratings, partial coverage, unavailable LE, and indeterminate threshold are tested.
- **Deviations**: none.
- **Gotchas**: sentinel-only polygon compatibility retains a zero candidate score
  in that manifest path; direct LESA summaries use `None`.

## 26.3.3

- **Status**: complete.
- **Files**: `eval/run_evals.py`, `eval/test_agent_eval.py`.
- **Validation**: `uv run pytest eval\test_agent_eval.py -m "not agent_eval" -q`
  — 7 passed, 2 deselected.
- **Changes**: initialization-first tool capture, explicit fallback/unknown
  diagnostics, advertised-vs-unadvertised classification, and one bounded retry.
- **Deviations**: none.
- **Gotchas**: 26.3.1 must replace legacy retrieval expectations with rejection and
  no-SDA-call assertions.

## 26.3.2

- **Status**: complete.
- **Files**: `eval/prompt_test_cases.json`, `tests/test_geometry.py`.
- **Validation**: `uv run pytest tests\test_geometry.py -q` — 15 passed.
- **Changes**: LESA-02 WKT and GeoJSON now describe the same approximately 45-acre
  AOI; regression coverage keeps affected-farm acreage separate.
- **Deviations**: none.
