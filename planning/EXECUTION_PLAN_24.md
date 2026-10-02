# EXECUTION PLAN 24: Complete Generic Corridor Productivity Scoring

## Goal & Scope

**Goal**: Resolve the follow-up review findings against the planning/documentation
specification by making corridor analysis fully consistent with the generic
productivity-rating schema, applying the requested productivity index and county
benchmark to corridor scoring, preserving explicit geometry validation for
polygon corridor inputs, establishing exact stable SDA provenance identifiers,
and synchronizing all public metadata. Validate the result with focused offline
tests, the full offline suite, and Ruff.

**In scope**
- Replace all removed NCCPI response-field construction in corridor analysis.
- Pass and score the requested NCCPI, CSR2, CPI, Storie, or CUSTOM productivity
  rating in direct corridor segments and alternatives.
- Consume and validate `max_county_rating_override` in corridor scoring.
- Preserve the explicit validation error for polygon/MultiPolygon corridor
  inputs; corridor analysis requires a representable centerline.
- Define exact stable provenance identifiers for supported SDA rating selectors.
- Synchronize README, manifest, and `server.json` public descriptions.
- Add corridor, tool-routing, provenance, and contract regression tests.
- Run targeted tests, the full offline suite, and both Ruff gates.

**Out of scope**
- Deriving a centerline from polygon geometry.
- Live-network tests as a required gate.
- New external dependencies, user SQL, or a broad LESA/statutory redesign.
- Reintroducing `nccpi_rating` or `nccpi_class`.
- Unrelated review findings not coupled to corridor genericization.

**Verbatim constraints**
- “create wave orchestration plan to resolve these issues”
- “comprehensively test their validity”
- “reject” polygon corridor inputs.
- “full_support” for non-NCCPI corridor scoring.
- “consume” the benchmark override.
- “stable_exact” provenance identifiers.

## Reconnaissance Log

- Repository: `D:\workspace\fpac-soil-mcp`; Python 3.11+, `uv`, pytest, Ruff.
- Prior green baseline: `uv run pytest -m "not live_network"` — 309 passed,
  12 deselected; `uv run ruff check .` and `uv run ruff format --check .`
  passed after Orchestration 23.
- Relevant files are large enough to require anchors: `corridor_analysis.py`
  contains centerline processing, segment scoring, alternative scoring, and
  CSV/manifest output; `soil_tools.py` contains both public LESA routing and
  corridor wrapper logic.
- Existing reference seams: generic polygon scoring in
  `polygon_analysis.py`, index normalization in `lesa.py`, SDA interpretation
  parsing in `sda_client.py`, and corridor fixtures/mocks in
  `tests/test_corridor_analysis.py`.
- Current hard inconsistency: `corridor_analysis.py` constructs removed
  `nccpi_rating`/`nccpi_class` fields.
- Current behavior gap: corridor analysis only retrieves NCCPI, while public
  routing accepts other indexes; the benchmark override is passed but ignored.
- Current geometry contract: `calculate_preliminary_lesa` explicitly rejects
  polygon corridor inputs; this remains intentional.
- Public metadata surfaces are `README.md`, `manifest.yaml`, and `server.json`;
  all three must describe the same generic productivity and corridor behavior.
- Full suites run serially; workers run targeted tests only. Maximum two
  concurrent workers.

## Decision Log

- **2026-09-30**: Use dependency-first order: corridor core scoring/schema,
  then public routing, then provenance/metadata, then tests, then verification.
- **2026-09-30**: Require full CSR2/CPI/Storie/CUSTOM corridor scoring rather
  than metadata-only propagation.
- **2026-09-30**: Keep polygon/MultiPolygon corridor inputs as an explicit
  validation error; do not invent a centerline.
- **2026-09-30**: Consume `max_county_rating_override` as the validated
  corridor benchmark used by scoring.
- **2026-09-30**: Use stable exact provenance identifiers verified against the
  fixed SDA selector/rule semantics; no runtime catalog lookup is required.
- **2026-09-30**: Retain at most two workers, one targeted retry before
  mid-tier escalation, and serial full offline/Ruff acceptance gates.

## Finding-to-Task Traceability

| Finding | Task |
|---|---|
| Removed NCCPI fields still constructed | 24.1.1 |
| Non-NCCPI corridor scoring missing | 24.1.1 |
| Benchmark override ignored | 24.1.1 |
| Public routing does not consistently propagate corridor options | 24.2.1 |
| Polygon corridor behavior must remain explicit and tested | 24.2.1, 24.3.2 |
| Approximate productivity provenance | 24.1.2 |
| README/manifest/server metadata drift | 24.2.2 |
| Corridor and contract regression coverage | 24.3.1, 24.3.2 |
| Full offline/Ruff verification | 24.4.1 |

## Wave & Dependency Table

| Wave | Task | Title | Files in scope | Depends on |
|---|---|---|---|---|
| 1 | 24.1.1 | Generalizing corridor rating retrieval and scoring | `src/fpac_soil_mcp/corridor_analysis.py`, `planning/tasks/24.1.1.todo.md` | none |
| 1 | 24.1.2 | Defining exact productivity provenance identifiers | `src/fpac_soil_mcp/sda_client.py`, `planning/tasks/24.1.2.todo.md` | none |
| 2 | 24.2.1 | Completing corridor tool routing and validation contracts | `src/fpac_soil_mcp/tools/soil_tools.py`, `planning/tasks/24.2.1.todo.md` | 24.1.1 |
| 2 | 24.2.2 | Synchronizing public corridor metadata | `README.md`, `manifest.yaml`, `server.json`, `planning/tasks/24.2.2.todo.md` | 24.1.1, 24.1.2 |
| 3 | 24.3.1 | Testing generic corridor scoring and alternatives | `tests/test_corridor_analysis.py`, `planning/tasks/24.3.1.todo.md` | 24.1.1, 24.1.2 |
| 3 | 24.3.2 | Testing public corridor routing and geometry errors | `tests/test_tools.py`, `tests/test_phase2_contracts.py`, `tests/test_phase3_contracts.py`, `planning/tasks/24.3.2.todo.md` | 24.2.1 |
| 4 | 24.4.1 | Running complete corridor remediation verification | `planning/STATE_24.md`, `planning/tasks/24.4.1.todo.md` | 24.3.1, 24.3.2, 24.2.2 |

## Task Specifications

### 24.1.1 — Generalizing corridor rating retrieval and scoring
- **Repo**: `AndrewBrown-USDA/fpac-soil-mcp`
- **Files in scope**: `src/fpac_soil_mcp/corridor_analysis.py`,
  `planning/tasks/24.1.1.todo.md`
- **Depends on**: none
- **Spec**: Extend `CorridorAnalyzer.analyze_corridor` with normalized
  productivity-index and optional benchmark parameters. Select the fixed SDA
  interpretation rule for the requested index, retrieve it for direct and
  alternative segments, populate only generic `SoilMapUnitAcreage` fields, and
  calculate segment/alternative/composite LE scores from the selected rating.
  Validate the benchmark override using the existing polygon conventions and
  use it wherever corridor normalization requires a county maximum. Preserve
  unavailable-rating, zero-rating, farmland categorization, reconciliation,
  and error behavior.
- **Constraints**: Do not add SQL passthrough, change geometry partitioning,
  alter public model aliases, or touch tests/docs.
- **Grep anchors**: `analyze_corridor`, `include_nccpi`, `get_interpretations`,
  `interp_map`, `nccpi_rating`, `nccpi_class`, `segment_le_sum`,
  `alt_seg_le_sum`.
- **Reference implementations**: `polygon_analysis.py` requested-index
  selection and `_normalize_productivity_index` in `lesa.py`.
- **Acceptance**: `uv run python -m compileall -q src\fpac_soil_mcp\corridor_analysis.py`
  passes; no removed field names remain in executable corridor construction.

### 24.1.2 — Defining exact productivity provenance identifiers
- **Repo**: `AndrewBrown-USDA/fpac-soil-mcp`
- **Files in scope**: `src/fpac_soil_mcp/sda_client.py`,
  `planning/tasks/24.1.2.todo.md`
- **Depends on**: none
- **Spec**: Replace approximate non-NCCPI provenance labels with these exact
  stable identifiers: `SDA:NCCPI_V3`, `SDA:CSR2`, `SDA:CPI`,
  `SDA:STORIE`, and `SDA:CUSTOM`. Map each identifier to the fixed selector
  or rule semantics used by the implementation, keep provenance attached to
  every returned rating row, and preserve explicit fallback/error semantics.
  Consolidate duplicated constants or construction where practical without
  changing query templates.
- **Constraints**: Do not introduce live catalog calls, user SQL, new
  dependencies, or unrelated SDA parsing changes.
- **Grep anchors**: `get_interpretations`, `productivity_rating_source`,
  `NCCPI - National Commodity`, `CSR2`, `CPI`, `Storie`.
- **Reference implementations**: existing fixed SDA query templates and
  `ProductivityIndexType` in `models.py`.
- **Acceptance**: `uv run pytest tests\test_sda_client.py -k "provenance or interpretation"`
  passes with literal assertions for all five identifiers.

### 24.2.1 — Completing corridor tool routing and validation contracts
- **Repo**: `AndrewBrown-USDA/fpac-soil-mcp`
- **Files in scope**: `src/fpac_soil_mcp/tools/soil_tools.py`,
  `planning/tasks/24.2.1.todo.md`
- **Depends on**: 24.1.1
- **Spec**: Pass normalized productivity index, `include_nccpi`, benchmark
  override, buffer, and alternatives consistently from
  `analyze_corridor_fppa` and `calculate_preliminary_lesa` into the generalized
  corridor analyzer. Ensure polygon/MultiPolygon `project_type="corridor"`
  continues to raise the explicit representability error, while line/WKT
  inputs use corridor analysis. Remove stale docstrings claiming only NCCPI
  support or that the benchmark is ignored.
- **Constraints**: Do not derive centerlines, change site/polygon routing, or
  duplicate score calculations in the tool wrapper.
- **Grep anchors**: `analyze_corridor_fppa`, `calculate_preliminary_lesa`,
  `corridor_kwargs`, `normalized_productivity_index`,
  `GeometryValidationError`.
- **Reference implementations**: current polygon routing branch and
  corridor tests in `tests/test_tools.py`.
- **Acceptance**: `uv run pytest tests\test_tools.py -k "corridor or lesa"`
  passes and explicitly covers line, WKT, non-NCCPI, benchmark propagation,
  and polygon rejection.

### 24.2.2 — Synchronizing public corridor metadata
- **Repo**: `AndrewBrown-USDA/fpac-soil-mcp`
- **Files in scope**: `README.md`, `manifest.yaml`, `server.json`,
  `planning/tasks/24.2.2.todo.md`
- **Depends on**: 24.1.1, 24.1.2
- **Spec**: Align descriptions and examples across all three public metadata
  surfaces with generic productivity fields, supported indexes, exact
  provenance, benchmark behavior, and the explicit line-centerline corridor
  geometry requirement. Remove stale NCCPI-only or ignored-override claims.
- **Constraints**: Documentation/metadata only; do not change Python behavior
  or invent support not present in the implementation.
- **Grep anchors**: `productivity_rating`, `productivity_index`,
  `max_county_rating_override`, `analyze_corridor_fppa`,
  `calculate_preliminary_lesa`.
- **Reference implementations**: current README generic schema section and
  manifest tool descriptions.
- **Acceptance**: a scoped text/JSON consistency check confirms that all three
  files mention generic productivity ratings, supported indexes, benchmark
  behavior, and the line-centerline corridor requirement.

### 24.3.1 — Testing generic corridor scoring and alternatives
- **Repo**: `AndrewBrown-USDA/fpac-soil-mcp`
- **Files in scope**: `tests/test_corridor_analysis.py`,
  `planning/tasks/24.3.1.todo.md`
- **Depends on**: 24.1.1, 24.1.2
- **Spec**: Add mocked tests proving generic map-unit fields and provenance,
  CSR2/CPI/Storie/CUSTOM selector propagation, direct and alternative scoring,
  benchmark override consumption, zero/unavailable ratings, and no removed
  NCCPI fields. Retain existing reconciliation and fallback coverage.
- **Constraints**: Offline mocks only; do not weaken existing assertions or
  modify production files.
- **Grep anchors**: existing `test_corridor_analysis_two_counties`,
  alternatives test, zero-score test, and `MagicMock(spec=SDAClient)`.
- **Reference implementations**: `tests/test_polygon_analysis.py` parameterized
  requested-index and sentinel tests.
- **Acceptance**: `uv run pytest tests\test_corridor_analysis.py`.

### 24.3.2 — Testing public corridor routing and geometry errors
- **Repo**: `AndrewBrown-USDA/fpac-soil-mcp`
- **Files in scope**: `tests/test_tools.py`, `tests/test_phase2_contracts.py`,
  `tests/test_phase3_contracts.py`, `planning/tasks/24.3.2.todo.md`
- **Depends on**: 24.2.1
- **Spec**: Extend public-tool tests to assert normalized index, benchmark,
  include flag, buffer, and exact analyzer call shape for line and WKT
  corridors; assert explicit polygon-corridor rejection; update only stale
  contract expectations caused by the intentional generic schema.
- **Constraints**: Do not alter production code or remove unrelated contract
  coverage.
- **Grep anchors**: current corridor parameterization around
  `test_calculate_preliminary_lesa`, `analyze_corridor_fppa` mocks, and
  removed-field assertions.
- **Reference implementations**: current `tests/test_tools.py` routing tests
  and Phase 2/3 public contract tests.
- **Acceptance**: `uv run pytest tests\test_tools.py tests\test_phase2_contracts.py tests\test_phase3_contracts.py`.

### 24.4.1 — Running complete corridor remediation verification
- **Repo**: `AndrewBrown-USDA/fpac-soil-mcp`
- **Files in scope**: `planning/STATE_24.md`,
  `planning/tasks/24.4.1.todo.md`
- **Depends on**: 24.2.2, 24.3.1, 24.3.2
- **Spec**: Consolidate worker reports, then run the targeted suites and the
  complete offline suite and Ruff check/format gates serially. Record exact
  commands, counts, deviations, and live-network exclusions in STATE_24.md.
  Do not modify production behavior during verification; if a failure is
  caused by an earlier task, return it through the escalation ladder.
- **Constraints**: No live-network tests, no broad cleanup, no unrelated fixes.
- **Grep anchors**: `planning/STATE_24.md` wave board and verification section.
- **Reference implementations**: `planning/STATE_23.md`.
- **Acceptance**: `uv run pytest -m "not live_network"`, `uv run ruff check .`,
  and `uv run ruff format --check .` all pass.

## Hazards and Escalation

- SDA selector/rule names must remain fixed and safe; workers must not create
  arbitrary SQL or silently substitute NCCPI for another requested index.
- A corridor benchmark override must be validated and applied consistently,
  not merely accepted and echoed.
- Direct and alternative corridor scoring are duplicate algorithm surfaces;
  both must use the same selector and normalization helper.
- Full suites are serial because mocked/shared resources can be order-sensitive.
- If a worker needs an out-of-scope file, stop and revise the task boundary.
- Allow one targeted-test retry; then escalate to a mid-tier worker. Do not
  loop a small worker.
