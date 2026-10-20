# Execution Plan 32 — PR #24 Review Closure

## Goal & Scope

### Goal

Close the still-relevant review findings from GitHub PR #24 while intentionally expanding the public productivity-index scope to NCCPI, CSR2, CPI, and STORIE. Establish one canonical selector/rating-semantics contract, apply it consistently to SDA SQL, county maxima, corridor and tool routing, benchmark calculations, tests, and public metadata, and preserve the current module boundary rather than extracting a new routing module.

### In scope

- Canonical selector normalization, aliases, scale, precision, sentinel semantics, and provenance.
- Dynamic `chorizon` and `cocropyld` aggregation and county-max filtering.
- Index-aware post-processing, including valid CSR2/CPI `99.0`.
- Direct and alternative corridor routing and tool-wrapper forwarding.
- Polygon and LESA regression coverage for all four selectors.
- Storie fixture arithmetic under the raw-then-final-rounding contract.
- README, `manifest.yaml`, `server.json`, ADR 0008, and planning-scope synchronization.

### Out of scope

- Extracting a dedicated SDV routing module; the current `sda_client.py` boundary is retained.
- Broad LESA/statutory redesign, geometry redesign, or centerline derivation from polygons.
- Making live-network tests part of every worker task; they remain a final opt-in gate.
- Reworking unrelated pre-existing defects.

### Verbatim constraints

- “this is absolutely intentional to expand the scope!”
- “keep current boundary; correct scope wording”
- “raw-then-final”
- Maximum concurrent workers: 3.
- Shared files such as `sda_client.py` are serialized.
- Live-network tests are required at final acceptance; if external access blocks them, the plan remains incomplete.

## Reconnaissance Log

- Repository: `D:\workspace\fpac-soil-mcp`; branch `feat/phase-4-part-2-sdv-routing`; head `b627665`.
- Next orchestration number is 32; no plan-32 artifacts existed at intake.
- Conventions: `AGENTS.md`; default commands use `uv`, pytest, and Ruff.
- Large shared files: `src\fpac_soil_mcp\sda_client.py`, `corridor_analysis.py`, `tools\soil_tools.py`, `tests\test_sda_client.py`, `tests\test_corridor_analysis.py`, and `tests\test_lesa.py`.
- Active constraints: ADR 0002 fixed SQL/no passthrough, ADR 0007 shared LESA architecture, ADR 0008 four-selector public contract, ADR 0011 mocked-default/live-opt-in testing.
- Baseline recorded by plan 31: offline `317 passed, 1 skipped, 21 deselected`; live `21 passed`. Re-run before wave 1 if the environment has changed.

## Decision Log

| Date | Decision |
|---|---|
| 2026-10-20 | Order waves as semantics → SDA SQL/post-processing → routing → tests/fixtures → docs/planning. |
| 2026-10-20 | Preserve the intentional four-selector public scope: NCCPI, CSR2, CPI, STORIE. |
| 2026-10-20 | Aggregate unrounded values and round only at the response boundary. |
| 2026-10-20 | Keep routing in `sda_client.py`; correct the PR/plan wording instead of extracting a module. |
| 2026-10-20 | Use at most 3 concurrent workers; serialize shared-file edits. |
| 2026-10-20 | Require targeted tests per wave, offline suite and Ruff checks, plus live-network tests at final acceptance. |
| 2026-10-20 | Use default workers and escalate only for blocked or failing tasks. |
| 2026-10-20 | User approved the plan for execution. |

## Wave Table

| Wave | Tasks | Dependencies | Parallelism |
|---|---|---|---|
| 1 | 32.1.1 Canonical rating semantics | None | 1; shared semantic contract |
| 2 | 32.2.1 SDA SQL and parser fixes | 32.1.1 | 1; `sda_client.py` serialized |
| 3 | 32.3.1 Corridor/tool routing | 32.1.1, 32.2.1 | 1; routing surfaces coupled |
| 4 | 32.4.1 Benchmark and regression tests | 32.2.1, 32.3.1 | 1; shared test fixtures |
| 5 | 32.5.1 Public metadata and planning closure | 32.4.1 | 1 |
| 6 | 32.6.1 Full verification | 32.5.1 | 1; serial test gates |

## Hazards

- Do not globally reject `99`; it can be valid for CSR2/CPI.
- SQL-side filtering must precede weighted aggregation and `MAX()`.
- Direct and alternative corridor loops must use the same selector and benchmark policy.
- Removing the NCCPI-only benchmark skip without scale-aware assertions will create false confidence.
- Documentation must not advertise behavior that routing/tests do not prove.
- Live tests may require network access and must remain separate from the default offline path; a blocked live run is not acceptance.

## Task Specifications

### 32.1.1 — Define canonical selector and rating semantics

- **Repo:** `D:\workspace\fpac-soil-mcp`
- **Files in scope:** `src\fpac_soil_mcp\models.py`, `src\fpac_soil_mcp\sda_client.py`, focused `tests\test_sda_client.py`
- **Depends on:** None
- **Spec:** Define or consolidate canonical selector normalization, aliases, scale, precision, sentinel policy, and provenance for NCCPI, CSR2, CPI, and STORIE. Normalize before routing, filtering, and rounding. Preserve existing public validation and fixed-SQL constraints. Ensure valid CSR2/CPI `99.0` is distinguishable from NCCPI/STORIE sentinel semantics.
- **Do not touch:** corridor behavior, public docs, broad LESA architecture, dependency manifests.
- **Grep anchors:** `ProductivityIndexType`, `VALIDATED_PRODUCTIVITY_INDEXES`, `_round_for_index`, `get_county_max_productivity_rating`, `get_productivity_ratings`.
- **Reference implementations:** ADR 0008; commits `74d69fc56b6ed6bf2e102bc0e3ad6f7bbca02939` and `5d1a8acd93de6d0bddc87233b19ce7880024c936`.
- **Acceptance:** alias/scale/precision/sentinel/provenance unit tests pass; fixed selectors retain existing behavior; valid CSR2/CPI `99.0` is not rejected by a universal rule; existing alias and Storie-precision tests remain green.
- **Targeted command:** `uv run pytest tests\test_sda_client.py -k "round or sentinel or productivity or county_max or alias or provenance"`

### 32.2.1 — Fix dynamic SDA aggregation and county maxima

- **Repo:** `D:\workspace\fpac-soil-mcp`
- **Files in scope:** `src\fpac_soil_mcp\sda_client.py`, `tests\test_sda_client.py`
- **Depends on:** 32.1.1
- **Spec:** Apply canonical index-aware sentinel predicates before `chorizon` depth-weighted aggregation, `cocropyld` aggregation, dynamic county maxima, and generic component maxima. Apply the same semantics in Python response parsing and `is_rated` classification. Preserve miscellaneous-area exclusions. Add tests for mixed valid/sentinel, sentinel-only, valid zero, and valid CSR2/CPI `99`.
- **Do not touch:** corridor or polygon orchestration, public metadata, live tests.
- **Grep anchors:** `chorizon`, `cocropyld`, `get_county_max_productivity_rating`, `get_productivity_ratings`, `numeric_rating`, `is_rated`, `miscellaneous area`.
- **Reference implementations:** existing `cointerp` sentinel predicates; `74d69fc56b6ed6bf2e102bc0e3ad6f7bbca02939`.
- **Acceptance:** no sentinel from the defined set affects weighted ratings or county maxima; no-rated paths return explicit unrated/None; valid zero and valid CSR2/CPI `99` behavior is covered; existing CPI component filtering remains unchanged and tested.
- **Targeted command:** `uv run pytest tests\test_sda_client.py`

### 32.3.1 — Correct corridor and tool selector routing

- **Repo:** `D:\workspace\fpac-soil-mcp`
- **Files in scope:** `src\fpac_soil_mcp\corridor_analysis.py`, `src\fpac_soil_mcp\tools\soil_tools.py`, focused `tests\test_corridor_analysis.py`, `tests\test_tools.py`
- **Depends on:** 32.1.1, 32.2.1
- **Spec:** Route requested non-NCCPI selectors through productivity retrieval, derive rating retrieval from the selected index rather than only `include_nccpi`, and always forward normalized `productivity_index` through direct and alternative corridor and preliminary LESA paths. Use index-specific county fallback semantics. Preserve explicit polygon/MultiPolygon rejection and shared LESA architecture.
- **Do not touch:** SDA SQL generation, public docs, geometry algorithms, ADR files.
- **Grep anchors:** `_get_corridor_ratings`, `analyze_corridor`, `analyze_alternatives`, `ratings_requested`, `include_nccpi`, `productivity_index`, `max_county_rating_override`, `calculate_preliminary_lesa`.
- **Reference implementations:** `planning\EXECUTION_PLAN_24.md`; `planning\EXECUTION_PLAN_25.md`; existing polygon selector guard tests.
- **Acceptance:** mocked tests prove CSR2/CPI/STORIE call the correct retrieval path, normalized `productivity_index` takes precedence over conflicting `include_nccpi`, selector forwarding occurs without overrides, direct/alternative paths agree, and fallback does not assume NCCPI scale.
- **Targeted command:** `uv run pytest tests\test_corridor_analysis.py tests\test_tools.py -k "productivity or corridor or selector or lesa or alternative"`

### 32.4.1 — Expand benchmark and regression coverage

- **Repo:** `D:\workspace\fpac-soil-mcp`
- **Files in scope:** `tests\fixtures\le_benchmarks.json`, `tests\test_lesa.py`, `tests\test_polygon_analysis.py`, `tests\test_corridor_analysis.py`, `tests\test_sda_client.py`
- **Depends on:** 32.2.1, 32.3.1
- **Spec:** Replace the NCCPI-only benchmark skip with scale-aware assertions for CSR2, CPI, and STORIE. Resolve the Storie fixture using raw-then-final rounding. Add explicit cases for all defined sentinels (`99`, `999`, `-99`, `-999`) where applicable, valid zero, valid CSR2/CPI `99`, sentinel-only data, partial coverage, missing county max, miscellaneous-area-only data, polygon STORIE acceptance with downstream selector propagation, and selector forwarding without county overrides. Keep full LESA assertions conditional when fixture summaries are absent. Verify already-fixed alias normalization, Storie precision, CPI miscellaneous-area filtering, and selector-guard behavior rather than reimplementing them.
- **Do not touch:** production routing or SQL, public docs.
- **Grep anchors:** `test_benchmark_cases`, `idx_name`, `expected_lesa_summary`, `CA_STORIE_SAN_JOAQUIN_SITE`, non-NCCPI skip.
- **Reference implementations:** plan 31 tests; existing `tests\test_sda_client.py` rounding/sentinel tests.
- **Acceptance:** all four selector fixtures execute; expected Storie values match the raw-then-final arithmetic contract; named regression cases cover the review findings and preserve prior fixes.
- **Targeted command:** `uv run pytest tests\test_lesa.py tests\test_polygon_analysis.py tests\test_corridor_analysis.py`

### 32.5.1 — Synchronize public metadata and planning scope

- **Repo:** `D:\workspace\fpac-soil-mcp`
- **Files in scope:** `README.md`, `manifest.yaml`, `server.json`, `docs\decisions\0008-nccpi-validated-public-index-with-extensible-sdv-routing.md`, `planning\EXECUTION_PLAN_27.md`, PR description metadata if the orchestrator has GitHub write access
- **Depends on:** 32.4.1
- **Spec:** Document the intentional four-selector contract, aliases, scale/precision, provenance, sentinel behavior, and fallback behavior. Correct the extraction promise in the PR-era planning artifact and PR description, when write access exists, to match the retained `sda_client.py` boundary. Preserve ADR chronology and do not claim unsupported behavior. If PR metadata cannot be edited by the worker, record that as an explicit handoff.
- **Do not touch:** production code, fixtures, dependency files.
- **Grep anchors:** `NCCPI`, `CSR2`, `CPI`, `STORIE`, `productivity_index`, `no module extraction`.
- **Reference implementations:** ADR 0008 and repository public-surface documentation conventions in `AGENTS.md`.
- **Acceptance:** no public metadata says NCCPI-only; all four selectors are described consistently; extraction wording is explicitly corrected.
- **Targeted command:** `uv run rg "NCCPI-only|NCCPI only|CSR2|CPI|STORIE|no module extraction|dedicated module" README.md manifest.yaml server.json docs\decisions\0008-nccpi-validated-public-index-with-extensible-sdv-routing.md planning\EXECUTION_PLAN_27.md`

### 32.6.1 — Complete verification

- **Repo:** `D:\workspace\fpac-soil-mcp`
- **Files in scope:** None; verification only
- **Depends on:** 32.5.1
- **Spec:** Run targeted tests, the offline suite, Ruff checks, and required live-network tests serially. Record failures explicitly; do not convert live-network failures into silent skips.
- **Do not touch:** source or docs unless a directly caused failure requires a surgical correction.
- **Grep anchors:** `pyproject.toml` pytest markers; `AGENTS.md` validation commands.
- **Reference implementations:** `planning\STATE_31.md`.
- **Acceptance:** targeted tests from tasks 32.1.1–32.5.1 pass; `uv run pytest -m "not live_network"` passes; `uv run ruff check .` passes; `uv run ruff format --check .` passes; and `uv run pytest -m live_network` passes. If the live command cannot run or fails because of external access, record the plan as blocked rather than accepted.
- **Targeted command:** Run each command separately and stop on failure: `uv run pytest -m "not live_network"`; `uv run ruff check .`; `uv run ruff format --check .`; `uv run pytest -m live_network`

## File Ownership and Overlap

All waves are intentionally serial because the implementation and test surfaces overlap. No two workers may edit the same file concurrently. `sda_client.py` and `tests\test_sda_client.py` are owned by tasks 32.1.1/32.2.1 in sequence; corridor/tool files are owned by 32.3.1; benchmark and regression files are owned by 32.4.1; public metadata and planning files are owned by 32.5.1.
