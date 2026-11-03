# EXECUTION PLAN 43: Phase 4 Criterion 2 Close-out

## Goal & Scope

### Goal

Complete Phase 4 Criterion 2 for both site and corridor workflows by computing
perimeter agricultural adjacency from the existing TIGERweb and geometry
abstractions, applying the verified point-awarding rules, exposing transparent
provenance and unavailable-data states, and closing the corresponding roadmap
and evaluation records. This is a preliminary estimate only and must not issue
an official FPPA determination or agency-approved Site Assessment.

### In scope

- Verify and encode the §658.5(b)/(c) Criterion 2 scoring contract.
- Reuse `TigerwebClient`, existing geometry validation/intersection helpers, and
  current unified LESA structures.
- Support both site/AOI and corridor project paths.
- Return the perimeter ratio, evidence status, rule/version, awarded points,
  verification flags, and source provenance.
- Add mocked and live TIGERweb coverage, LESA integration, corridor integration,
  and regression/evaluation tests.
- Update Phase 4 state, master-plan status, public metadata, and task records.

### Out of scope

- New land-cover providers, parcel datasets, or custom GIS infrastructure.
- Phase 8 map-envelope implementation or new agent-app UI features.
- Multiple AOIs, persistence, custom basemaps, production authorization, or
  agent-app evaluation.
- Rewriting unrelated LESA criteria or changing existing LE normalization.

### Verbatim constraints

- “need to wrap up phase 4 asap”
- “points now”
- “existing TIGERweb”
- “site and corridor”
- “parallel”
- “2”
- “full”

## Reconnaissance Log

- Phase 4 is explicitly marked partially complete; Criterion 2 is the open
  server item in `planning/MASTER_PLAN.md`.
- Unified scoring is in `src/fpac_soil_mcp/lesa.py` (809 lines); geometry is in
  `geometry.py` (483 lines), and TIGERweb integration is in
  `tigerweb_client.py` (542 lines). Use grep anchors rather than whole-file
  rewrites.
- Existing reference tests are `tests/test_lesa.py` (586 lines),
  `tests/test_corridor_scoring.py` (320 lines), `tests/test_tigerweb_client.py`,
  and `tests/test_polygon_analysis.py`.
- Accepted constraints include unified LESA architecture (ADR 0007), dynamic
  TIGERweb spatial handling (ADR 0006), preliminary authority boundaries
  (ADR 0003), and mocked-default/live-opt-in tests (ADR 0011).
- Required commands are `uv run pytest -m "not live_network"`, focused tests,
  `uv run pytest -m live_network`, `uv run ruff check .`, and
  `uv run ruff format --check .`.

## Decision Log

- **2026-11-03 — scoring:** implement ratio and point awarding in this plan;
  do not defer points.
- **2026-11-03 — evidence:** reuse existing TIGERweb and geometry utilities;
  do not add a new external land-cover source.
- **2026-11-03 — project types:** cover both site and corridor paths.
- **2026-11-03 — execution:** permit at most two concurrent workers where file
  scopes are disjoint; use serial gates between waves.
- **2026-11-03 — acceptance:** require focused mocked tests, Ruff, formatting,
  offline suite, and live-network validation.

## Wave & Dependency Table

| Wave | Task | Title | Files in scope | Depends on |
|---|---|---|---|---|
| 1 | 43.1.1 | Define verified Criterion 2 scoring contract | `constants.py`, scoring registry/data, `models.py`, task record | none |
| 1 | 43.1.2 | Add TIGERweb perimeter evidence helper | `tigerweb_client.py`, `geometry.py`, client tests, task record | none |
| 2 | 43.2.1 | Integrate Criterion 2 into unified LESA paths | `lesa.py`, `polygon_analysis.py`, `corridor_analysis.py`, tool wiring, focused tests | 43.1.1, 43.1.2 |
| 3 | 43.3.1 | Complete contract, live, and regression verification | phase contract tests, live tests, eval fixtures, task record | 43.2.1 |
| 4 | 43.4.1 | Close Phase 4 documentation and roadmap state | `MASTER_PLAN.md`, `STATE_43.md`, README/manifest metadata as needed | 43.3.1 |

## Hazards

- Do not infer agricultural use from “not urban” without recording the evidence
  limitation and unavailable state.
- Preserve existing authority notices and never convert a machine estimate into
  an agency-approved score.
- Keep live tests opt-in; network failures must be explicit, not silently
  treated as zero adjacency.
- Shared LESA and model files make wave 2 serial even though wave 1 has two
  disjoint tasks.
- Verify the exact regulation-derived point mapping before implementation;
  document the citation and version in the scoring registry.

## Task Specifications

### 43.1.1 — Define verified Criterion 2 scoring contract

- **Repo:** `.`
- **Files in scope:** `src/fpac_soil_mcp/constants.py`, the existing scoring
  registry/data location, `src/fpac_soil_mcp/models.py`,
  `planning/tasks/43.1.1.todo.md`.
- **Depends on:** none.
- **Spec prose:** Establish the normalized Criterion 2 input, valid range,
  site/corridor point scales, rule citation/version, unavailable semantics,
  and response fields for ratio, evidence status, points, and verification.
  Keep the contract compatible with existing Pydantic response models.
- **Do not touch:** LE normalization, unrelated criteria, public authority
  wording outside the affected criterion.
- **Grep anchors:** `SITE_CRITERIA_MAX_POINTS`, `CORRIDOR_CRITERIA_MAX_POINTS`,
  `SiteAssessmentCriterion`, `evaluate_site_assessment`.
- **Acceptance:** model and rule tests cover bounds, missing evidence,
  unavailable status, both project types, and cited point mapping.

### 43.1.2 — Add TIGERweb perimeter evidence helper

- **Repo:** `.`
- **Files in scope:** `src/fpac_soil_mcp/tigerweb_client.py`,
  `src/fpac_soil_mcp/geometry.py`, `tests/test_tigerweb_client.py`,
  `tests/test_geometry.py`, `planning/tasks/43.1.2.todo.md`.
- **Depends on:** none.
- **Spec prose:** Add a reusable perimeter-intersection operation using the
  existing TIGERweb endpoint and Shapely geometry helpers. Return a bounded
  ratio and explicit evidence/provenance/unavailable state, handling invalid,
  empty, multipart, and boundary-touching geometries without silent fallback.
- **Do not touch:** SDA SQL templates, NASS query behavior, arbitrary HTTP
  passthrough, or live-test defaults.
- **Grep anchors:** `TigerwebClient.check_urban_exemption`,
  `calculate_acreage`, `parse_geojson_geometry`, retry helper usage.
- **Acceptance:** focused mocked tests pass for normal, multipart, boundary,
  upstream-error, and unavailable cases; live test is opt-in.

### 43.2.1 — Integrate Criterion 2 into unified LESA paths

- **Repo:** `.`
- **Files in scope:** `src/fpac_soil_mcp/lesa.py`,
  `src/fpac_soil_mcp/polygon_analysis.py`,
  `src/fpac_soil_mcp/corridor_analysis.py`,
  relevant tool registration, `tests/test_lesa.py`,
  `tests/test_polygon_analysis.py`, `tests/test_corridor_analysis.py`.
- **Depends on:** 43.1.1, 43.1.2.
- **Spec prose:** Thread the perimeter evidence through site and corridor
  analysis, calculate the prescribed points, preserve existing explicit
  overrides, expose per-criterion rule/provenance/verification fields, and
  distinguish unavailable from zero. Keep corridor-specific criterion limits
  and total-score behavior intact.
- **Do not touch:** frontend code, Phase 8 map envelope, unrelated criteria,
  or existing LE calculations.
- **Grep anchors:** `evaluate_site_assessment`, `evaluate_lesa`,
  `calculate_preliminary_lesa`, `analyze_corridor`, `PolygonAnalyzer`.
- **Acceptance:** focused unit and integration tests verify both project types,
  unavailable evidence, explicit overrides, threshold evaluation, and
  preliminary notices.

### 43.3.1 — Complete contract, live, and regression verification

- **Repo:** `.`
- **Files in scope:** phase contract tests, `tests/test_live_tigerweb.py`,
  relevant `eval/prompt_test_cases.json`, `planning/tasks/43.3.1.todo.md`.
- **Depends on:** 43.2.1.
- **Spec prose:** Add deterministic cases for site and corridor Criterion 2,
  missing/unavailable evidence, boundary conditions, and no-siting guidance.
  Add opt-in live TIGERweb coverage and update public tool/evaluation contracts
  only where the new response surface is public.
- **Do not touch:** unrelated eval cases or default live-network selection.
- **Grep anchors:** phase contract test conventions, `live_network` marker,
  existing LESA eval cases.
- **Acceptance:** focused tests pass; live TIGERweb command passes or reports
  an explicit external failure; offline suite, Ruff, and formatting pass.

### 43.4.1 — Close Phase 4 documentation and roadmap state

- **Repo:** `.`
- **Files in scope:** `planning/MASTER_PLAN.md`, `planning/STATE_43.md`,
  `planning/tasks/43.4.1.todo.md`, public metadata only if required.
- **Depends on:** 43.3.1.
- **Spec prose:** Mark Criterion 2 delivered, record exact verification
  commands/results, preserve remaining Phase 4 limitations and authority
  boundaries, and link the next Phase 8/Track A work without expanding scope.
- **Do not touch:** historical state files except by adding a direct correction
  required for consistency.
- **Grep anchors:** Phase 4 “Open”, Track A “Next: M3”, prior state report
  format.
- **Acceptance:** no stale “Criterion 2 open” claim remains in current planning;
  state report is complete and repository checks remain green.
