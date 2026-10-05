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
| 1 | 26.1.1 Align selectors and unavailable LE semantics | pending |
| 2 | 26.2.1 Propagate selector validation through tools | pending |
| 3 | 26.3.1 Add productivity and LESA regression tests | pending |
| 3 | 26.3.2 Correct the 45-acre evaluation fixture | pending |
| 3 | 26.3.3 Diagnose and retry missing eval tools | pending |
| 4 | 26.4.1 Add opt-in SDA rule catalog coverage | pending |
| 5 | 26.5.1 Run complete verification | pending |

## Task reports

<!-- Worker reports are appended below, one section per task, <=15 lines. -->

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
