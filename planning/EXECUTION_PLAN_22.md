# EXECUTION PLAN 22: Resolve Local Review Findings After PR #9 Remediation

## Goal & Scope

**Goal**: Resolve the remaining local code-review findings on top of the
un pushed PR #9 remediation commits. Preserve the current LESA behavior while
ensuring requested productivity indexes and corridor project semantics are
honored, regulatory text remains centralized, public metadata is complete, and
the changes are covered by focused offline tests.

**In scope**
- Preserve requested productivity indexes through corridor and fallback LESA paths.
- Route explicit corridor projects through buffered corridor analysis.
- Centralize new regulatory constants in `constants.py`.
- Remove duplicated LESA fallback construction.
- Simplify `calculate_area_weighted_le` to its established domain shape if
  existing callers permit it.
- Update `server.json` and historical planning text.
- Add regression tests and run offline/Ruff verification.

**Out of scope**
- Live-network execution as a required gate.
- Broad LESA scoring redesign, statutory threshold changes, or new dependencies.
- Reworking already-resolved PR #9 findings unless a regression test exposes one.
- Implementing the future interactive visualization strategy; retain it as
  roadmap documentation only.

**Verbatim constraints**
- “resolve issues with local code review on top of our other changes that have
  not been pushed yet”
- “all” (include both smell refactors)
- Use targeted offline tests, the full offline suite, and Ruff; live tests remain
  opt-in.

## Reconnaissance Log

- Repository: `D:\workspace\fpac-soil-mcp`; Python 3.11+, `uv`, pytest, Ruff.
- Current baseline: `uv run pytest -m "not live_network"` — 269 passed,
  12 deselected.
- Relevant file sizes: `lesa.py` 818 lines, `soil_tools.py` 665,
  `constants.py` 167, `models.py` 540, `sda_client.py` 1174.
  Workers must use grep anchors rather than whole-file reads.
- Conventions: `AGENTS.md` requires centralized regulatory language, explicit
  validation/errors, updated README/manifest/server metadata for public tools,
  mocked tests, and opt-in live tests.
- Reference implementations: `lesa.py::_normalize_productivity_index`,
  `corridor_analysis.py::analyze_corridor`, `geometry.py::buffer_centerline`,
  `soil_tools.py::analyze_corridor_fppa`, and existing fallback tests in
  `tests/test_lesa.py` and `tests/test_tools.py`.
- Hazards: edits to `lesa.py` and `soil_tools.py` are serialized; full tests
  must run serially because shared fixtures/resources can make concurrent
  suites flaky. `server.json` is currently not updated with the new tool.

## Decision Log

- **2026-09-30**: Include all six behavior/spec findings, both hard standards
  findings, and both baseline-smell refactors.
- **2026-09-30**: Order work as shared constants, LESA core, public tool wiring,
  regression tests, then metadata/planning and final verification.
- **2026-09-30**: Acceptance is targeted offline tests, the full offline suite,
  and both Ruff checks; live-network tests remain opt-in.
- **2026-09-30**: Existing public defaults and response shapes must remain
  backward compatible; requested non-NCCPI indexes must not be relabeled NCCPI.

## Finding-to-Task Traceability

| Review finding | Task |
|---|---|
| Corridor productivity index/benchmark propagation | 22.3.1, 22.4.2 |
| Explicit corridor `project_type` routing | 22.3.1, 22.4.2 |
| Non-NCCPI fallback summaries | 22.2.1, 22.4.1 |
| Over-broad CPI matching follow-up | Already resolved in Orchestration 21; regression coverage remains in existing SDA tests |
| Missing `server.json` public metadata | 22.3.2, 22.4.2 |
| Regulatory literals outside `constants.py` | 22.1.1, 22.2.1 |
| Duplicated LESA fallback construction | 22.2.1, 22.4.1 |
| Dual-shape `calculate_area_weighted_le` API | 22.2.1, 22.4.1 |
| Historical Plan 19 allowlist wording | 22.3.2 |

## Wave & Dependency Table

| Wave | Task | Title | Files in scope | Depends on |
|---|---|---|---|---|
| 1 | 22.1.1 | Centralizing LESA regulatory constants | `src/fpac_soil_mcp/constants.py` | none |
| 2 | 22.2.1 | Correcting LESA index propagation and simplifying aggregation | `src/fpac_soil_mcp/lesa.py` | 22.1.1 |
| 3 | 22.3.1 | Completing corridor LESA routing and index propagation | `src/fpac_soil_mcp/tools/soil_tools.py` | 22.2.1 |
| 3 | 22.3.2 | Updating public metadata and planning history | `server.json`, `planning/EXECUTION_PLAN_19.md` | none |
| 4 | 22.4.1 | Testing LESA core corrections | `tests/test_lesa.py` | 22.2.1 |
| 4 | 22.4.2 | Testing public corridor and metadata behavior | `tests/test_tools.py`, `tests/test_server.py` | 22.3.1, 22.3.2 |
| 5 | 22.5.1 | Running final offline and lint verification | `planning/STATE_22.md` | 22.4.1, 22.4.2 |

## Task Specifications

### 22.1.1 — Centralizing LESA regulatory constants
- **Repo**: `AndrewBrown-USDA/fpac-soil-mcp`
- **Files in scope**: `src/fpac_soil_mcp/constants.py`
- **Depends on**: none
- **Spec**: Add named constants for the new LESA statutory point limits,
  criterion labels, and cited action guidance currently embedded in `lesa.py`.
  Preserve values and public imports; use the repository's existing constants
  style. Do not move algorithmic behavior.
- **Do not touch**: `lesa.py`, tools, tests, or statutory values.
- **Grep anchors**: `FARMLAND_CLASS`, `REGULATORY`, `7 CFR`, `SITE_CRITERIA`.
- **Acceptance**: import `fpac_soil_mcp.constants` successfully and run
  `uv run ruff check src/fpac_soil_mcp/constants.py`.

### 22.2.1 — Correcting LESA index propagation and simplifying aggregation
- **Files in scope**: `src/fpac_soil_mcp/lesa.py`
- **Depends on**: 22.1.1
- **Spec**: Import and use centralized constants; preserve normalized
  `ProductivityIndexType` in every fallback and normal summary; remove the
  duplicated fallback construction through one helper; simplify
  `calculate_area_weighted_le` only if all current callers use one coherent
  input shape, preserving numerical results and response types. If callers do
  not permit simplification, document the concrete incompatible callers and
  retain the smallest justified compatibility shim. Add no new statutory rules.
- **Do not touch**: tools, models, constants, tests, or public signatures unless
  the existing signature can remain backward compatible.
- **Grep anchors**: `_normalize_productivity_index`, `calculate_area_weighted_le`,
  `LandEvaluationSummary`, `evaluate_lesa`, `SITE_CRITERIA_NAMES`.
- **Acceptance**: `uv run pytest tests/test_lesa.py`.

### 22.3.1 — Completing corridor LESA routing and index propagation
- **Files in scope**: `src/fpac_soil_mcp/tools/soil_tools.py`
- **Depends on**: 22.2.1
- **Spec**: For `project_type="corridor"` or line geometry, use the existing
  corridor buffering/analysis path. Pass the requested productivity index,
  NCCPI inclusion policy, benchmark override, buffer distance, and units
  consistently; do not construct corridor results as NCCPI when another index
  was requested. Preserve documented defaults, WKT support, errors, and output
  shape.
- **Do not touch**: corridor algorithms, geometry helpers, LESA core, or other
  MCP tools.
- **Grep anchors**: `calculate_preliminary_lesa`, `analyze_corridor_fppa`,
  `project_type`, `corridor_buffer_distance`, `productivity_index`,
  `LandEvaluationSummary`.
- **Acceptance**: `uv run pytest tests/test_tools.py`.

### 22.3.2 — Updating public metadata and planning history
- **Files in scope**: `server.json`, `planning/EXECUTION_PLAN_19.md`
- **Depends on**: none
- **Spec**: Update `server.json` so its public description/capability metadata
  reflects `calculate_preliminary_lesa`. Correct the historical Plan 19
  decision-log statement that describes removed unsupported SDV tables, without
  rewriting unrelated history.
- **Do not touch**: source code, manifests, README, or other planning files.
- **Grep anchors**: `description`, `calculate_preliminary_lesa`,
  `ALLOWED_SDV_TABLES`, `coiacsr2`, `cstorie`.
- **Acceptance**: parse `server.json` successfully and run targeted Ruff on
  the changed Python planning content if applicable; repository-wide Ruff is
  reserved for task 22.5.1.

### 22.4.1 — Testing LESA core corrections
- **Files in scope**: `tests/test_lesa.py`
- **Depends on**: 22.2.1
- **Spec**: Add regression tests proving CSR2/CPI/Storie remain the selected
  index in fallback summaries, aggregation simplification preserves results,
  and existing sentinel behavior remains intact. If simplification is not
  justified, test and document the compatibility shim instead. Use existing
  fixtures and test style; no network access.
- **Do not touch**: production code or shared fixtures.
- **Grep anchors**: `evaluate_lesa`, `calculate_area_weighted_le`,
  `ProductivityIndexType`, `sentinel`, `fallback`.
- **Acceptance**: `uv run pytest tests/test_lesa.py`.

### 22.4.2 — Testing public corridor and metadata behavior
- **Files in scope**: `tests/test_tools.py`, `tests/test_server.py`
- **Depends on**: 22.3.1, 22.3.2
- **Spec**: Add mocked regression coverage for polygon geometry with
  `project_type="corridor"`, line/WKT corridor routing, explicit buffer
  propagation, and CSR2/CPI/Storie propagation. Verify the public server
  metadata exposes the LESA capability. Keep tests offline.
- **Do not touch**: production code, live tests, or shared fixtures outside
  these files.
- **Grep anchors**: `calculate_preliminary_lesa`, `analyze_corridor_fppa`,
  `buffer_distance`, `project_type`, `create_mcp_server`.
- **Acceptance**: `uv run pytest tests/test_tools.py tests/test_server.py`.

### 22.5.1 — Running final offline and lint verification
- **Files in scope**: `planning/STATE_22.md` (generated caches and temporary
  test artifacts are not committed and are outside the task scope)
- **Depends on**: 22.4.1, 22.4.2
- **Spec**: Run the complete offline suite and both Ruff checks serially,
  record exact counts/outcomes in STATE_22, and note live tests as opt-in.
- **Do not touch**: source or test files.
- **Acceptance**: `uv run pytest -m "not live_network"`; `uv run ruff check .`;
  `uv run ruff format --check .`.
