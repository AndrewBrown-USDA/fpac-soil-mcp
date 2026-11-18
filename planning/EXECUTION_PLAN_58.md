# EXECUTION_PLAN_58 -- Shared coverage vocabularies; failed queries report `error` (issue #84)

Branch: `refactor/coverage-vocab1` off `feature/nccpi-baseline1` 8c5ade6 (Plan 57, unmerged). Rebase onto `main` after #85 merges. Breaking change to the public MCP output contract, shipped in 0.6.0 (unreleased).

## Goal & Scope

**Goal.** Replace the per-module `coverage_status` strings with two shared, schema-enforced vocabularies (soil mapping coverage, productivity rating coverage), documented in one place. A failed request or upstream query must report `error`, never `unmapped` or `unrated`, so an SDA outage can't be read as "no soils" or "no rating".

**In scope**
- New `src/fpac_soil_mcp/models/coverage.py`: `SoilMappingCoverage`, `RatingCoverage`, value constants, one value table.
- Producers: SDA client rating rows, soil lookup tools, NCCPI baseline helper, polygon analyzer, corridor analyzer, LESA domain + `lesa_tools`.
- Typing every `coverage_status` / `*_coverage_status` field in `models/soil.py`, `models/spatial.py`, `models/lesa.py`.
- Consumers: agent app tests and frontend type, eval contract tests.
- Docs: README (0.6.0 rename note), `docs/sdv-metadata-contract.md` cross-reference, new ADR 0019 + index row.

**Out of scope (explicit)**
- A structured `error` field on polygon, corridor or LESA responses (D12; later contract change).
- Renaming any field (D5) or SDV caveat / reason codes such as `no_coverage`, `not_found` (D13).
- Farmland category keys (`category_acres["unmapped"]`, `unknown`), map layer categories in `spatial/map_builder.py`, CDL `PARTIAL`: different concepts, unchanged.
- Frontend wording; the map panel keeps showing the raw string (D15).
- Moving `include_map` geometry into MCP `_meta` (next plan; see Follow-on).
- Version bump (stays 0.6.0, D14). Historical `planning/` files.

**Verbatim constraints from the user**
- "we need to distinguish the error case from unrated or unmapped; right now SDA is down"
- Issue #84 acceptance: "Every coverage_status field in src/ uses a shared vocabulary type"; "Schema tests reject values outside the vocabulary"; "The tool output schemas list the allowed values"; "A regression test covers the unmapped path in _lesa_coverage_status."

## Vocabulary (the contract this plan implements)

| Type | Value | Meaning |
| --- | --- | --- |
| `SoilMappingCoverage` | `covered` | All evaluated area has SSURGO map units |
| | `partial` | Some evaluated area has no map unit |
| | `unmapped` | Query succeeded; no map units returned |
| | `error` | Invalid request or upstream query failed; cause in `limitations` (and `error` where present) |
| `RatingCoverage` | `rated` | All mapped area / component share supports the rating |
| | `partial` | Rating supported for part of the area / components |
| | `unrated` | Mapped soil, but no usable rating |
| | `unmapped` | No mapped soil to rate |
| | `unknown` | Nothing evaluated (zero acreage) or SDA returned no row for the map unit |
| | `error` | Rating query failed; cause in `limitations` |

Renames: `partially_covered` -> `partial`; `no_data`, `invalid_request` -> `error`; rating `covered` -> `rated`; SDA `no_coverage` -> `unrated`; SDA `not_found` -> `unknown`. NCCPI baseline with no SDA row stays `null` (Plan 57 D10).

## Decision log

| ID | Date | Decision | Source |
| --- | --- | --- | --- |
| D1 | 2026-11-18 | Branch `refactor/coverage-vocab1` off `feature/nccpi-baseline1`; rebase after #85 merges. | user (accepted rec) |
| D2 | 2026-11-18 | Two `Literal` types in `models/coverage.py`; rating type also covers SDA rows, NCCPI baseline, LESA. | user (accepted rec) |
| D3 | 2026-11-18 | Canonical values and renames as in the Vocabulary table. | user (accepted rec) |
| D4 | 2026-11-18 | Explicit `error` value in both types; a failed query is never reported as `unmapped`/`unrated`. | user |
| D5 | 2026-11-18 | Keep field names; the type and description carry the dimension. | user (accepted rec) |
| D6 | 2026-11-18 | Hard rename, no aliases; in-repo consumers updated in this plan. | user (accepted rec) |
| D7 | 2026-11-18 | One value table in the `models/coverage.py` docstring, referenced by field descriptions; new ADR 0019. | user (accepted rec) |
| D8 | 2026-11-18 | Execution model as Plan 57 (see PROMPT_TEMPLATE_58); offline only; ask before every push. | user (accepted rec) |
| D9 | 2026-11-18 | Corridor `reconciliation_summary.productivity_coverage_status` = `error` if any county segment's spatial or rating query failed; segments keep their own statuses. | user (accepted rec) |
| D10 | 2026-11-18 | Spatial ok + rating failed -> mapping `covered`/`partial`, rating `error`. Spatial failed -> both `error`. County-max failure -> limitation only. Corridor rating failure now adds a limitation. | user (accepted rec) |
| D11 | 2026-11-18 | NCCPI baseline query failure -> per-unit `nccpi_baseline_coverage_status = "error"` (other baseline fields null); no SDA row stays null. Amends Plan 57 D10. | user (accepted rec) |
| D12 | 2026-11-18 | No new structured `error` field on polygon/corridor/LESA responses (deferred). | user (accepted rec) |
| D13 | 2026-11-18 | SDV caveat keys / reason codes unchanged; the value table notes reason `no_coverage` -> status `unrated`. | user (accepted rec) |
| D14 | 2026-11-18 | Ship in 0.6.0; no version bump; rename note in README. | user (accepted rec) |
| D15 | 2026-11-18 | Frontend keeps raw string display; only the TS type and fixtures change. | user (accepted rec) |
| D16 | 2026-11-18 | Add a Follow-on section for the `_meta` plan; no `_meta` work here. | user (accepted rec) |
| D17 | 2026-11-18 | PROPOSED: polygon map units set `productivity_coverage_status` from the rating row (today always the default `unknown`, even when rated), using the corridor rule. | my proposal, pending |
| D18 | 2026-11-18 | PROPOSED: `manifest.yaml` / `server.json` unchanged. They have no release-notes field, no tool description lists coverage values, and `tests/test_server.py` pins description parity; the rename note goes in README only. | my proposal, pending |
| D19 | 2026-11-18 | PROPOSED: `LandEvaluationSummary.coverage_status` is temporarily widened to `RatingCoverage` plus legacy `"covered"` in Wave 1 so every commit stays green; narrowed in 58.4.1. | my proposal, pending |

## Recon log (facts, 2026-11-18 on 8c5ade6)

- Plain-`str` fields: `FarmlandClassificationResponse.coverage_status` (models/soil.py:56), `SoilMapUnitAcreage.productivity_coverage_status` (soil.py:131) and `.nccpi_baseline_coverage_status` (soil.py:162), `PolygonFarmlandAnalysisResponse.coverage_status` (models/spatial.py:34), `CorridorCountySegment.coverage_status` (spatial.py:104) and `.productivity_coverage_status` (spatial.py:108). Only `LandEvaluationSummary.coverage_status` (models/lesa.py:168) is a `Literal`. No `validate_assignment` on these models (polygon assigns `le_summary.coverage_status` after construction).
- Producers: soil_lookup_tools.py 72/157/177 (`no_data`, SDA error with `ToolError`), 95/199 (`unmapped`), 115/218 (`covered`); polygon_analyzer.py 141 (`invalid_request`), 416-432 (mapping + LE); corridor_analyzer.py 560-570 (map-unit rating fallback incl. `no_coverage`), 663-687 (segment), 806-815 (reconciliation); domain/lesa.py 499-506; lesa_tools.py `_lesa_coverage_status` 616-631 (literal `"unmapped"` check at 626), callers 393-395, 480-483; clients/sda/client.py 578 (`not_found`), 622-626, 648-650; domain/nccpi_baseline.py 58-60 (failure -> `{}`), 88-92.
- Failure paths today: polygon_analyzer.py:176 spatial failure -> limitation, empty units -> `unmapped`; :207/:219 rating failure -> limitation, ratings empty -> LE `unrated`. corridor_analyzer.py:455 spatial failure -> limitation -> `unmapped`; :465 `_get_corridor_ratings` failure -> log only, no limitation. Only `FarmlandClassificationResponse` has an `error` field.
- Polygon `SoilMapUnitAcreage(` (~318-337) never sets `productivity_coverage_status` (D17).
- Tests asserting values: tests/test_tools.py (65-226 soil lookup; 407-677 LESA; 789-794), test_polygon_analysis.py (107, 405-407, 524-566), test_polygon_map.py (110, 204), test_corridor_analysis.py (700-769, 1083-1086), test_phase3_contracts.py:335, test_lesa.py (286, 310), test_sda_client.py:869, test_sdv_contract.py:285, test_nccpi_baseline.py (97-129), test_map_contract.py:222, test_server.py:493, tests/fixtures/phase4_gold_set.json:14 (`rated`, unchanged). eval/contract/test_contract.py 419/449 (`no_data`). App tests: test_geo_map.py 100/133, test_geo_screen.py 291/303 (`partially_covered`), test_geo_corridor.py 63/186, test_aoi_context.py:43 (`complete`, synthetic pass-through).
- Pass-through consumers (no value logic): app `geo.py` (`_short_text`), frontend `ScreeningResults.tsx:26`, `useScreening.ts:26` (`string | null`), eval scorers / `evalAssertions.js` / `eval/pi/run_evals.py` (read `coverage_status` as status).
- No edit needed (checked): `mcp/tools/lesa.py` (re-export only), `tests/test_map_tool_contracts.py` (truthiness only), `tests/test_phase2_contracts.py`, `tests/test_multi_county_productivity.py`.
- No test inspects tool output schemas today. ADR index ends at 0018. No CHANGELOG file. README/manifest/server.json list no coverage values.
- Expected baseline (STATE_57 final at 5dec901; 8c5ade6 only bumps the version): root offline pytest 1031 passed / 3 skipped / 45 deselected; app 310; JS harness 20/20; ruff clean. Re-record before Wave 1.

## Hazards

- `"unmapped"`, `"unknown"`, `"partial"` also appear as farmland category keys, map categories and CDL enum values. Change only coverage assignments; retired-value greps target `partially_covered|no_data|invalid_request` and `coverage_status`-adjacent `no_coverage|not_found`.
- `no_coverage` / `not_found` stay as `SDV_CAVEATS` keys (D13); only `coverage_status` values change.
- `LandEvaluationSummary` validates on construction (domain/lesa.py:534): keep D19 widening until 58.4.1, or Wave 3 commits break.
- `tests/test_tools.py` holds soil lookup and LESA tests: 58.2.2 and 58.3.3 edit it in different waves; never parallelize.
- `lesa_tools` reads polygon/corridor statuses: run 58.3.3 after 58.3.1 and 58.3.2.
- Workspace FS rejects `__pycache__`: `PYTHONDONTWRITEBYTECODE=1`, `-p no:cacheprovider`. Ruff on a `git archive HEAD` copy in `/tmp`. JS harness from a `/tmp` archive of `eval/` after `npm ci`.
- SDA is down: every test uses fakes; nothing calls live services.

## Wave table

| Wave | Theme | Tasks | Depends on | Gate |
| --- | --- | --- | --- | --- |
| 1 | Vocabulary module | 58.1.1 | baseline | targeted + root suite |
| 2 | Leaf producers | 58.2.1, 58.2.2, 58.2.3 | 1 | root suite, eval contract |
| 3 | Analyzers and LESA | 58.3.1, 58.3.2, 58.3.3 | 2 | root suite |
| 4 | Types, consumers, docs | 58.4.1, 58.4.2, 58.4.3 | 3 | root suite, app-check, harness |
| 5 | Final verification | 58.5.1 (blocking), 58.5.2 (post-SDA, non-blocking) | 4 | all gates |

Files within each wave are pairwise disjoint. One agent runs tasks serially in id order.

## Task specs

### 58.1.1 -- Coverage vocabulary module
- Depends on: baseline. Can create: `src/fpac_soil_mcp/models/coverage.py`, `tests/test_coverage_vocab.py`. Must edit: `src/fpac_soil_mcp/models/__init__.py` (export), `src/fpac_soil_mcp/models/lesa.py` (D19 only).
- Spec: `SoilMappingCoverage = Literal["covered", "partial", "unmapped", "error"]`, `RatingCoverage = Literal["rated", "partial", "unrated", "unmapped", "unknown", "error"]`; module constants for each value (e.g. `MAPPING_UNMAPPED`, `RATING_ERROR`) and frozensets of each vocabulary derived with `typing.get_args`. Module docstring holds the Vocabulary table, the rename list and the D13 reason-code note. Widen `LandEvaluationSummary.coverage_status` to `RatingCoverage | Literal["covered"]` with a `# transitional` comment; default stays `"unknown"`.
- Do not touch: producers, other model fields.
- Acceptance: tests check the value sets exactly, constants match `get_args`, a pydantic model with each type rejects `"partially_covered"` and `"no_data"`. `pytest tests/test_coverage_vocab.py tests/test_models.py tests/test_lesa.py`.

### 58.2.1 -- SDA client rating rows
- Depends on: 58.1.1. Must edit: `src/fpac_soil_mcp/clients/sda/client.py`, `tests/test_sda_client.py`, `tests/test_sdv_contract.py`, `docs/sdv-metadata-contract.md`.
- Spec: `not_found` -> `RATING_UNKNOWN`; `no_coverage` status -> `RATING_UNRATED`; `rated`/`partial`/`unrated` via constants. Caveat keys untouched. Doc: one sentence near line 142/187 that reason `no_coverage` maps to status `unrated` (link to `models/coverage.py`).
- Anchors: `"coverage_status": "not_found"` (~578), `coverage_status = ` (~622, ~648).
- Acceptance: no `coverage_status` literal `no_coverage`/`not_found` left in client.py; test for an absent mukey -> `unknown`, zero-coverage row -> `unrated`. `pytest tests/test_sda_client.py tests/test_sdv_contract.py`.

### 58.2.2 -- Soil lookup tools
- Depends on: 58.1.1. Must edit: `src/fpac_soil_mcp/mcp/tools/soil_lookup_tools.py`, `tests/test_tools.py` (soil lookup tests only, ~65-226), `eval/contract/test_contract.py` (~449).
- Spec: `no_data` -> `MAPPING_ERROR` (keeps `ToolError`); `unmapped`/`covered` via constants. Field descriptions change in 58.4.1, not here.
- Acceptance: `git grep -n no_data -- src/fpac_soil_mcp/mcp/tools/soil_lookup_tools.py` empty; SDA error -> `error` + `error` object set, empty result -> `unmapped`. `pytest tests/test_tools.py eval/contract`.

### 58.2.3 -- NCCPI baseline failure reports `error`
- Depends on: 58.1.1. Must edit: `src/fpac_soil_mcp/domain/nccpi_baseline.py`, `tests/test_nccpi_baseline.py`, `tests/test_polygon_analysis.py` (the failure assertion ~566 only).
- Spec (D11): on `SDAClientError`, `fetch_nccpi_baseline` returns a failure marker per requested mukey (e.g. `{mukey: {"_baseline_error": True}}`) plus the limitation; `nccpi_baseline_fields` maps the marker to all-null values with `nccpi_baseline_coverage_status = RATING_ERROR`. No row -> all null (unchanged). Rated/partial/unrated via constants. Analyzer call sites unchanged.
- Acceptance: tests for failure -> every unit `error` and rating null; no-row -> null; limitation text unchanged. `pytest tests/test_nccpi_baseline.py tests/test_polygon_analysis.py tests/test_corridor_analysis.py`.

### 58.3.1 -- Polygon analyzer
- Depends on: 58.2.1, 58.2.3. Must edit: `src/fpac_soil_mcp/domain/polygon_analyzer.py`, `tests/test_polygon_analysis.py`, `tests/test_polygon_map.py`. (`tests/test_phase2_contracts.py` asserts no coverage values; run it, don't edit it.)
- Spec: mapping: `partially_covered` -> `partial`, `invalid_request` -> `MAPPING_ERROR`; track `spatial_failed` (except at ~176) -> mapping `error` and LE `error`; track `rating_failed` (~207/~219) -> LE `error` while mapping is computed normally (D10). LE `covered` -> `rated`. County-max failure unchanged. D17 (if approved): set map-unit `productivity_coverage_status` from the rating row using the corridor rule.
- Anchors: `coverage_status="invalid_request"` (~141), `except SDAClientError` (~176, ~207, ~219), `le_coverage_status` (~421), `SoilMapUnitAcreage(` (~318).
- Acceptance: tests with a failing fake SDA client: spatial failure -> `error`/`error` + limitation (not `unmapped`); rating failure -> `covered`/`error`; invalid geometry -> `error`; partial -> `partial`; full LE -> `rated`. `pytest tests/test_polygon_analysis.py tests/test_polygon_map.py tests/test_phase2_contracts.py`.

### 58.3.2 -- Corridor analyzer
- Depends on: 58.2.1, 58.2.3. Must edit: `src/fpac_soil_mcp/domain/corridor_analyzer.py`, `tests/test_corridor_analysis.py`, `tests/test_phase3_contracts.py`. (`tests/test_multi_county_productivity.py` asserts no coverage values; run it, don't edit it.)
- Spec: map-unit fallback (~560-570) `no_coverage` -> `unrated`, values via constants; segment mapping `partially_covered` -> `partial`; segment rating `covered` -> `rated`. Per segment track spatial failure (~455) -> segment `error`/`error`; rating failure (~465) -> add a limitation (deduped) and segment rating `error`. Reconciliation (~806-815): `covered` -> `rated`; `error` if any segment failed (D9). County-max (~493) unchanged. Alternatives: no coverage fields, unchanged.
- Acceptance: two-county fake where county B's spatial query fails -> B `error`/`error`, A unchanged, reconciliation `error`, one limitation; rating failure -> limitation present and segment rating `error`. `pytest tests/test_corridor_analysis.py tests/test_phase3_contracts.py tests/test_multi_county_productivity.py tests/test_corridor_scoring.py tests/test_corridor_map.py`.

### 58.3.3 -- LESA domain and `_lesa_coverage_status`
- Depends on: 58.3.1, 58.3.2. Must edit: `src/fpac_soil_mcp/domain/lesa.py`, `src/fpac_soil_mcp/mcp/tools/lesa_tools.py`, `tests/test_lesa.py`, `tests/test_tools.py` (LESA tests only, ~407-677).
- Spec: domain/lesa.py:499 `covered` -> `rated` via constants. `_lesa_coverage_status`: compare against `MAPPING_UNMAPPED`/`MAPPING_ERROR` constants; return `RATING_ERROR` if any source status is `error`; else existing logic with `rated`. Return type `RatingCoverage`.
- Acceptance: regression tests: source `unmapped` + zero rated -> `unmapped`; source `error` -> `error`; zero mapped acreage -> `unmapped`; full -> `rated`. `pytest tests/test_lesa.py tests/test_tools.py`.

### 58.4.1 -- Type every coverage field; output schemas
- Depends on: Wave 3. Must edit: `src/fpac_soil_mcp/models/soil.py`, `src/fpac_soil_mcp/models/spatial.py`, `src/fpac_soil_mcp/models/lesa.py`, `tests/test_coverage_vocab.py`, `tests/test_map_contract.py`, `tests/test_server.py` (~493 + new schema test).
- Spec: `FarmlandClassificationResponse`, `PolygonFarmlandAnalysisResponse`, `CorridorCountySegment.coverage_status` -> `SoilMappingCoverage`; `SoilMapUnitAcreage.productivity_coverage_status`, `CorridorCountySegment.productivity_coverage_status`, `LandEvaluationSummary.coverage_status` (drop D19 widening) -> `RatingCoverage`; `nccpi_baseline_coverage_status` -> `RatingCoverage | None`. Descriptions name the dimension and point to `fpac_soil_mcp.models.coverage`.
- Acceptance: `git grep -nE "coverage_status: str" -- src` empty; tests: each model rejects a retired value; `list_tools()` output schemas for the soil lookup, polygon, corridor and LESA tools list exactly the enum values. `pytest tests/test_coverage_vocab.py tests/test_server.py tests/test_map_contract.py`, then the root suite.

### 58.4.2 -- Agent app and frontend consumers
- Depends on: 58.4.1. Must edit: `apps/agent-fpac-soil-openai-sdk/tests/test_geo_map.py`, `apps/agent-fpac-soil-openai-sdk/tests/test_geo_screen.py`, `apps/agent-fpac-soil-openai-sdk/tests/test_geo_corridor.py` (only if values change), `apps/agent-fpac-soil-openai-sdk/frontend/client/src/components/map/useScreening.ts`.
- Spec: fixtures `partially_covered` -> `partial`; `useScreening.ts` `coverage_status?: 'covered' | 'partial' | 'unmapped' | 'error' | null`. `geo.py` unchanged (pass-through); `test_aoi_context.py` synthetic value unchanged.
- Acceptance: `git grep -n partially_covered -- apps` empty; `make app-check`; `make app-frontend-check` (biome 0 errors).

### 58.4.3 -- README note and ADR 0019
- Depends on: 58.4.1. Must edit: `README.md`, `docs/decisions/README.md`. Can create: `docs/decisions/0019-shared-coverage-vocabularies.md`.
- Spec: README: short 0.6.0 breaking-change note listing the renames and the `error` rule. ADR 0019 (Accepted, 2026-11-18): context (issue #84, outage misreport), decision (two vocabularies, `error`, hard rename, field names kept), consequences, deferred items (structured error field, `_meta` plan). Index row.
- Acceptance: links resolve; no other ADR edited.

### 58.5.1 -- Final verification (orchestrator)
- `git grep -nE '"(partially_covered|no_data|invalid_request)"' -- src tests eval apps ':!**/node_modules' ':!tests/test_coverage_vocab.py'` empty (the vocab test names retired values only to prove they are rejected); `no_coverage`/`not_found` only as `SDV_CAVEATS` keys/usages.
- In-memory FastMCP smoke with a failing fake SDA client: polygon, corridor, soil lookup and LESA return `error` (not `unmapped`/`unrated`) with a limitation.
- Root suite, lint + format (archive copy), `make app-check`, `make app-frontend-check`, harness tests: green vs. baseline. Update STATE_58; ask before push.

### 58.5.2 -- Post-SDA checks (non-blocking)
- When SDA is reachable: `make test-live`; one live polygon and corridor screening confirm real `covered`/`rated` values; record in STATE_58.

## Follow-on: `_meta` map geometry plan (D16)

- Shared files: `apps/agent-fpac-soil-openai-sdk/agent_server/geo.py`, `domain/polygon_analyzer.py`, `domain/corridor_analyzer.py`, `models/spatial.py`, `mcp/tools/soil_lookup_tools.py`, `tests/test_map_contract.py`, `tests/test_map_tool_contracts.py`, `tests/test_polygon_map.py`, `tests/test_tools.py`.
- Its explicit output schemas (needed because `ToolResult` drops the generated schema) must keep the coverage enums; reuse the 58.4.1 schema test.
