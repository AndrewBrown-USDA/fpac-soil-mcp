# EXECUTION PLAN 25: Resolve PR #9 Review Findings

## Goal & Scope

**Goal**: Resolve the five open Copilot review findings on PR #9: prevent
unrated NCCPI sentinel values from entering corridor LE scoring, preserve exact
coordinate validation in the POINT-01 agent evaluation, publish metadata for all
registered tools, reject the currently unsupported `CUSTOM` productivity
selector explicitly, and ensure corridor responses use the exact
`SDA:NCCPI_V3` provenance identifier. Validate the fixes with focused tests,
the full offline suite, Ruff, and the agent evaluation when `pi` is available.

**In scope**
- Normalize/filter sentinel and unrated productivity values in both direct and
  alternative corridor scoring loops.
- Reject `CUSTOM` before attempting an SDA lookup, with an explicit error.
- Preserve exact `SDA:NCCPI_V3` fallback provenance in corridor map-unit output.
- Restore structured POINT-01 latitude/longitude argument extraction and exact
  numeric assertions.
- Expand `server.json` to enumerate all 10 registered tools consistently with
  `manifest.yaml`.
- Add or update focused regression and contract tests for every finding.
- Run targeted tests, full offline tests, Ruff, and conditional agent eval.

**Out of scope**
- Implementing arbitrary user-defined SDA attributes for `CUSTOM`; deferred.
- Changing the public tool API beyond explicit rejection of `CUSTOM`.
- Live-network tests as a required gate.
- Unrelated review findings already marked resolved in the PR.
- Broad refactoring or a statutory/LESA model redesign.

**Verbatim constraints**
- “we should just throw an error if it is invoked for now, we can address it later”
- “enumerate_all”
- “assert_exact_point”
- “recommended”
- “two_workers”

## Reconnaissance Log

- Repository: `D:\workspace\fpac-soil-mcp`; Python >=3.11, `uv`, pytest, Ruff.
- Latest completed orchestration is 24. Its baseline was 316 passed and 12
  deselected for `uv run pytest -m "not live_network"`, with Ruff lint and
  format checks passing.
- `corridor_analysis.py` is 909 lines; direct scoring is anchored near
  `interp_map`/`numeric_rating` and alternative scoring near `alt_interp_map`/
  `num_rating`. Both loops must receive identical unrated filtering.
- `eval/test_agent_eval.py` already has structured tool-name extraction, but
  not structured argument extraction. POINT-01 supplies exact coordinates in
  `eval/prompt_test_cases.json`.
- `server.json` currently lists only two tools; `manifest.yaml` lists all ten.
- Existing sentinel normalization references are
  `polygon_analysis._normalize_numeric_rating` and
  `sda_client.get_interpretations` parsing with `is_rated`.
- Full suites must run serially. Workers run only targeted tests. Maximum two
  concurrent workers.

## Decision Log

- **2026-10-05**: `CUSTOM` remains a placeholder and must raise an explicit
  unsupported-selector error; arbitrary attributes are deferred.
- **2026-10-05**: `server.json` must enumerate all 10 registered tools and
  stay aligned with `manifest.yaml`.
- **2026-10-05**: POINT-01 must assert exact structured latitude `41.8781` and
  longitude `-93.0977`, not merely tool invocation or key presence.
- **2026-10-05**: Acceptance is targeted tests, full offline tests, and Ruff;
  agent eval is required when `pi` is available and otherwise recorded as
  skipped; live-network tests remain opt-in.
- **2026-10-05**: Use at most two concurrent workers; same-file tasks are
  serialized and full-suite verification is serial.

## Finding-to-Task Traceability

| Review finding | Task |
|---|---|
| NCCPI sentinels incorrectly score as rated | 25.1.1, 25.3.1 |
| POINT-01 arguments no longer validated | 25.2.1, 25.3.2 |
| `server.json` exposes only two tools | 25.2.2, 25.3.2 |
| `CUSTOM` has no real SDA attribute mapping | 25.1.1, 25.3.1 |
| NCCPI fallback provenance is not exact | 25.1.1, 25.3.1 |
| Complete verification | 25.4.1 |

## Wave & Dependency Table

| Wave | Task | Title | Files in scope | Depends on |
|---|---|---|---|---|
| 1 | 25.1.1 | Hardening corridor rating normalization | `src/fpac_soil_mcp/corridor_analysis.py`, `planning/tasks/25.1.1.todo.md` | none |
| 2 | 25.2.1 | Restoring agent coordinate validation | `eval/test_agent_eval.py`, `planning/tasks/25.2.1.todo.md` | none |
| 2 | 25.2.2 | Publishing the complete tool registry | `server.json`, `planning/tasks/25.2.2.todo.md` | none |
| 3 | 25.3.1 | Testing corridor review regressions | `tests/test_corridor_analysis.py`, `planning/tasks/25.3.1.todo.md` | 25.1.1 |
| 3 | 25.3.2 | Testing metadata and agent contracts | `tests/test_server.py`, `eval/test_agent_eval.py`, `planning/tasks/25.3.2.todo.md` | 25.2.1, 25.2.2 |
| 4 | 25.4.1 | Running complete review verification | `planning/STATE_25.md`, `planning/tasks/25.4.1.todo.md` | 25.3.1, 25.3.2 |

## Task Specifications

### 25.1.1 — Hardening corridor rating normalization
- **Repo**: `AndrewBrown-USDA/fpac-soil-mcp`
- **Files in scope**: `src/fpac_soil_mcp/corridor_analysis.py`,
  `planning/tasks/25.1.1.todo.md`
- **Depends on**: none
- **Spec**: Apply the repository’s existing `is_rated`/sentinel normalization
  semantics before direct and alternative corridor LE scoring. Unrated,
  negative, 99, 999, -99, and -999 values must not contribute acreage or score.
  Preserve valid zero ratings as rated. Make the NCCPI fallback source exactly
  `SDA:NCCPI_V3`. Reject normalized `CUSTOM` explicitly before SDA retrieval
  with a clear `ValueError` or repository-standard equivalent.
- **Constraints**: Do not add arbitrary SQL or an attribute parameter; do not
  change geometry, county partitioning, public response models, or resolved
  behavior; keep direct and alternative loops consistent.
- **Grep anchors**: `_normalize_productivity_index`, `_get_corridor_ratings`,
  `ratings_requested`, `numeric_rating`, `segment_le_sum`, `alt_seg_le_sum`,
  `productivity_rating_source`.
- **Reference implementations**: `polygon_analysis._normalize_numeric_rating`
  and `sda_client.get_interpretations` parsing.
- **Acceptance**: `uv run python -m compileall -q
  src\fpac_soil_mcp\corridor_analysis.py` succeeds; targeted corridor tests
  prove sentinel values are unrated in both loops, valid zero remains
  scoreable, `CUSTOM` raises explicitly, and fallback provenance is
  `SDA:NCCPI_V3`.

### 25.2.1 — Restoring agent coordinate validation
- **Repo**: `AndrewBrown-USDA/fpac-soil-mcp`
- **Files in scope**: `eval/test_agent_eval.py`,
  `planning/tasks/25.2.1.todo.md`
- **Depends on**: none
- **Spec**: Extend structured event extraction to retain tool-call arguments
  across the event shapes already supported by the name extractor. In
  POINT-01, identify the target tool call and assert latitude `41.8781` and
  longitude `-93.0977` numerically with a small tolerance, while retaining
  exact tool-name matching and output keyword checks.
- **Constraints**: Do not fall back to flattened event text for arguments; do
  not weaken tool-name or assistant-output assertions; preserve compatibility
  with existing pi event formats.
- **Grep anchors**: `extract_structured_tool_names`, `extract_tool_calls`,
  `test_pi_point_screening_evaluation`, `POINT-01`.
- **Reference implementations**: `eval/run_evals.py` structured event helpers
  and `prompt_test_cases.json` sample geometry.
- **Acceptance**: a focused unit-level test or deterministic helper assertion
  fails for wrong coordinates and passes for POINT-01's exact coordinates;
  `uv run pytest eval\test_agent_eval.py -m "not agent_eval"` passes.

### 25.2.2 — Publishing the complete tool registry
- **Repo**: `AndrewBrown-USDA/fpac-soil-mcp`
- **Files in scope**: `server.json`, `planning/tasks/25.2.2.todo.md`
- **Depends on**: none
- **Spec**: Expand `server.json.tools` to all 10 registered public tools,
  matching names and public descriptions in `manifest.yaml`. Include the two
  existing LESA/corridor entries and the eight omitted tools without claiming
  unsupported behavior.
- **Constraints**: Metadata only; do not change command, environment, version,
  manifest resources, or Python registration.
- **Grep anchors**: `tools`, `calculate_preliminary_lesa`,
  `analyze_corridor_fppa`.
- **Reference implementations**: `manifest.yaml` tool list and
  `tests/test_server.py` metadata assertions.
- **Acceptance**: JSON parses; tool names exactly match the 10 names in
  `manifest.yaml`; no duplicate names.

### 25.3.1 — Testing corridor review regressions
- **Repo**: `AndrewBrown-USDA/fpac-soil-mcp`
- **Files in scope**: `tests/test_corridor_analysis.py`,
  `planning/tasks/25.3.1.todo.md`
- **Depends on**: 25.1.1
- **Spec**: Add mocked regression coverage for direct and alternative
  sentinel filtering, valid zero ratings, explicit `CUSTOM` rejection, and
  exact NCCPI fallback provenance. Preserve existing generic-index,
  benchmark, reconciliation, and alternatives coverage.
- **Constraints**: Offline mocks only; do not alter production code or weaken
  existing assertions; keep tests deterministic and focused.
- **Grep anchors**: existing two-county test, alternative comparison test,
  zero/unavailable rating cases, `MagicMock(spec=SDAClient)`.
- **Reference implementations**: `tests/test_polygon_analysis.py` sentinel
  parameterization and current corridor fixtures.
- **Acceptance**: `uv run pytest tests\test_corridor_analysis.py` passes and
  assertions cover both scoring loops.

### 25.3.2 — Testing metadata and agent contracts
- **Repo**: `AndrewBrown-USDA/fpac-soil-mcp`
- **Files in scope**: `tests/test_server.py`, `eval/test_agent_eval.py`,
  `planning/tasks/25.3.2.todo.md`
- **Depends on**: 25.2.1, 25.2.2
- **Spec**: Add a server metadata contract asserting the published tool set
  equals the manifest tool set. Add deterministic tests for structured
  argument extraction and exact POINT-01 coordinate validation without
  invoking pi. Keep the live/agent marker behavior unchanged.
- **Constraints**: Do not remove existing server lifecycle coverage or require
  external network/model access in the default suite.
- **Grep anchors**: `test_published_server_metadata_exposes_lesa_capabilities`,
  `test_pi_point_screening_evaluation`, extractor helpers.
- **Reference implementations**: `manifest.yaml`, `eval/run_evals.py`, and
  existing `test_server.py` JSON tests.
- **Acceptance**: `uv run pytest tests\test_server.py eval\test_agent_eval.py
  -m "not agent_eval"` passes.

### 25.4.1 — Running complete review verification
- **Repo**: `AndrewBrown-USDA/fpac-soil-mcp`
- **Files in scope**: `planning/STATE_25.md`,
  `planning/tasks/25.4.1.todo.md`
- **Depends on**: 25.3.1, 25.3.2
- **Spec**: Consolidate reports, run targeted suites, then run the full
  offline suite and Ruff gates serially. If `pi` is available, run the
  POINT-01 agent evaluation; otherwise record the conditional skip. Record
  exact commands, counts, live-network exclusions, and deviations.
- **Constraints**: No production edits during verification; no live tests;
  do not hide or retry the same failure more than once before escalation.
- **Grep anchors**: `planning/STATE_25.md` wave board and verification.
- **Reference implementations**: `planning/STATE_24.md`.
- **Acceptance**: targeted tests, `uv run pytest -m "not live_network"`,
  `uv run ruff check .`, and `uv run ruff format --check .` pass; conditional
  agent-eval status is recorded. If compilation is needed for diagnosis, use
  `uv run python -m compileall -q src\fpac_soil_mcp`.

## Hazards and Escalation

- Sentinel handling must be shared semantically across direct and alternative
  scoring; a one-loop fix is incomplete.
- `CUSTOM` must fail before SDA receives a literal unsupported selector.
- `SDA:NCCPI_V3` is a contract identifier, not the human-readable rule name.
- `server.json` and `manifest.yaml` must remain exact-name aligned.
- Structured argument extraction must not regress across pi event shapes.
- Full suites and agent eval are serial; live-network tests stay opt-in.
- If a worker needs an out-of-scope file, revise the task boundary rather than
  widening permissions ad hoc.
