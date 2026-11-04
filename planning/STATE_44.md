# Orchestration 44 State

## Baseline

- **Repository:** workspace clone `/Workspace/Users/andrew.g.brown@usda.gov/fpac-soil-mcp`; edits and commits happen there; gates run in `/tmp` clones (D8).
- **Branch:** `feature/agent-app-map2` off `origin/main` 06525de (PR #75 and PR #74 merged); plan commits 5b5ed9a, 3ca93a1 are on `origin/feature/agent-app-map2` (in sync at baseline).
- **Plan date:** 2026-11-04; approved by the user 2026-11-04.
- **Agent app:** `agent-fpac-soil-openai-sdk` RUNNING, git `main`, `auto_deploy: true`, active deployment 06525de.
- **MCP server app:** `mcp-fpac-soil` RUNNING, deployed 2026-10-21 from `/Workspace/Users/Groups/team-03/fpac-soil-mcp` (predates Plan 43).
- **Last known suite results (from STATE_43 and the PR #75 gate; not yet re-run on 06525de):** root offline 599+ passed / 3 skipped; live 41 passed / 1 pre-existing SDA "kill state" failure / 3 skipped; frontend biome 0 errors / 10 warnings, client build OK with the MapLibre worker asset.
- [x] **Pre-wave-1 baseline on 06525de** (fresh `/tmp/p44`, 2026-11-04):
  - root `make check`: rc 0; ruff + format clean; 626 passed / 3 skipped / 45 deselected.
  - `make test-live`: rc 0; 43 passed / 3 skipped (the STATE_43 SDA "kill state" failure did not recur).
  - `make app-check`: rc 0; ruff clean; 135 passed.
  - `make app-frontend-check`: rc 0; `npm ci` 573 packages; biome 0 errors / 10 warnings; build OK, emits `maplibre-gl-worker-*.js`.
  - Node v22.20.0, npm 10.9.3 via `databricks/bootstrap-serverless.sh`.

## Wave board

| Wave | Executor | Task | Status |
|---|---|---|---|
| 1 | Genie Code | 44.1.1 | done |
| 1 | User + Genie Code | 44.1.2 | done |
| 1 | gate | root check, app-check | passed on 09f42e6 (626 passed / 3 skipped; app 135); wave 1 done |
| 2 | Genie Code | 44.2.1 | done |
| 2 | Genie Code | 44.2.2 | done |
| 2 | gate | root check, app-check, test-live | passed on 0767fa2 (645 passed / 3 skipped; app 135; live 43 / 3 skipped) |
| 3 | Genie Code | 44.3.1 | done |
| 3 | Genie Code | 44.3.2 | done |
| 3 | gate | root check, app-check, test-live | passed on 5dd084a (666 passed / 3 skipped; app 135; live 43 / 3 skipped) |
| 4 | Genie Code | 44.4.1 | pending |
| 4 | gate | root check, app-check, test-live | pending |
| 5 | Genie Code | 44.5.1 | pending |
| 5 | User + Genie Code | 44.5.2 | pending |
| 5 | gate | root check, app-check | pending |
| 6 | Genie Code | 44.6.1 | pending |
| 6 | gate | root check, app-check, app-frontend-check | pending |
| 7 | Genie Code | 44.7.1 | pending |
| 7 | gate | root check, app-check, app-frontend-check | pending |
| 8 | User + Genie Code | 44.8.1 | pending |
| 8 | Genie Code | 44.8.2 | pending |
| 8 | gate | root check, app-check, app-frontend-check | pending |
| 9 | Genie Code | 44.9.1 | pending |
| 9 | Genie Code | 44.9.2 | pending |
| 9 | gate | root check, app-check, app-frontend-check | pending |
| 10 | User + Genie Code | 44.10.1 | pending |
| 11 | Genie Code | 44.11.1 | pending |
| 12 | Genie Code + User | 44.12.1 | pending |
| 12 | gate | all suites | pending |

## Task Reports

<!-- Append one report per task (<=15 lines): status, files, commands/results, deviations, gotchas, commit. -->

## 44.1.1

- **Status:** done. Commit 3d9d9b6 (`docs(decisions): propose the server map result contract for the analyze tools`).
- **Files:** `docs/decisions/0017-server-map-result-contract.md` (new, 223 lines, `Proposed`); `docs/decisions/README.md` (index row, Databricks Delivery era sentence); `planning/tasks/44.1.1.todo.md`.
- **Checks:** `grep -n 0017 docs/decisions/README.md` shows the row and link; link target exists; no coordinate-like numbers in the ADR. Root `make check` does not read `docs/` (wave gate below).
- **Deviations:** none.
- **Gotchas for 44.2.1:** legend values follow `categorize_farmland_class` (7 values incl. `conditional_prime`, `unmapped`); those two take the deployed `farmlandClasses.ts` colours. Patterns enum: `solid`, `diagonal_hatch`, `cross_hatch`, `dot_stipple`, `outline`, `dashed_outline`. `bounds` is null when no layer is inline. The size cap drops whole layers from the end of the list (`delivery: omitted`, `truncated: true`, warning in `map.warnings`); it never drops part of a layer. Layer `authority` values: `user_input`, `machine_estimate`, `reference_data`. `data_vintage` nullable (no SSURGO vintage without an extra query). The section 4 mapping table is what 44.4.1 asserts.

## 44.1.2

- **Status:** done. Parts 1-2 by Genie Code; part 3 browser-console run from the deployed app by the user 2026-11-04: all 4 rows ok (GetMap image loads untainted, GetFeatureInfo 270 B, counties 43 KB, urban 232 KB). Outcome pass: D5 option A holds, no proxy. URL templates for `overlays.ts` are in the evidence file.
- **Files:** `planning/evidence/44.1.2-overlays.md` (new).
- **Findings so far:** all four requests succeed with CORS for the app origin (SSURGO `*`; TIGERweb echoes the origin). SSURGO GetFeatureInfo supports only `text/plain`/`text/html`/`gml2` and returns `mukey`/`musym`, not farmland class. Sample urban area 5694 vertices (over the 2000 cap); sample county 1050.
- **Gotchas:** TIGERweb CORS needs simple GETs (preflight gets no CORS headers). Browser CSP of the app is not covered by the server-side probe; the browser run checks it.

## 44.2.2

- **Status:** done. Commit d8231c0 (`feat(tigerweb): return fetched urban area geometries alongside the screening record`).
- **Files:** `src/fpac_soil_mcp/tigerweb_client.py` (`check_urban_exemption` now delegates; new `check_urban_exemption_with_geometries` returns `(record, [(name, Polygon|MultiPolygon)])`, +32/-3); `tests/test_tigerweb_client.py` (+82, 4 tests); `planning/tasks/44.2.2.todo.md`.
- **Checks:** `uv run pytest tests/test_tigerweb_client.py -q` 34 passed; ruff check and format clean.
- **Deviations:** none. `UrbanExemptionRecord` and all callers unchanged.
- **Gotchas for 44.3.x:** names follow `NAME` -> `BASENAME` -> `Unknown Urban Area`; only features with parseable rings appear in the list. Point inputs and error paths return `[]`. Existing analyzer tests mock `check_urban_exemption` on a mock client; when 44.3.x switch to the new method, those mocks need `check_urban_exemption_with_geometries.return_value = (record, [])` (or the analyzer should call the new method only when `include_map` is true, keeping the old mocks valid).

## 44.2.1

- **Status:** done. Commit 0767fa2 (`feat(map): add the map result contract models, builders and settings`).
- **Files:** `src/fpac_soil_mcp/map_contract.py` (new); `config.py` (`map_simplify_tolerance_m` 1.0, >= 0; `map_max_geojson_bytes` 2,000,000, > 0); `models.py` (optional `schema_version`, `data_mode`, `authority`, `map` on both analyze responses); `tests/test_map_contract.py` (new, 15 tests); `planning/tasks/44.2.1.todo.md`.
- **Checks:** `uv run pytest tests/test_map_contract.py tests/test_models.py tests/test_config.py -q` 20 passed (also with `-W error::DeprecationWarning`); ruff clean.
- **Deviations:** `features_from_sda_rows` returns `(Shapely geometry, properties)` pairs, not GeoJSON dicts, so `build_layer` can simplify before writing GeoJSON. Settings validator tests live in `test_map_contract.py` (`test_config.py` not in scope).
- **API for 44.3.x:** `build_layer(layer_id=, title=, kind=, authority=, source=, features=[(geom, props)], include_map=, data_vintage=, style_key=, legend=, simplify_tolerance_m=)`; `build_map_block(layers, max_bytes)` applies the cap and bounds; `farmland_legend()`, `single_legend(value, label, color, pattern)`; colour constants `URBAN_CONTEXT_COLOR`, `CORRIDOR_DIRECT_COLOR`, `ALTERNATIVE_COLORS`, `NEUTRAL_OUTLINE_COLOR`.
- **Gotchas:** `map_contract` must not import `models`/analyzers at module level (cycle); `features_from_sda_rows` imports `categorize_farmland_class` lazily. Simplification is per geometry (`preserve_topology=True`), not coverage simplify. Every response now dumps `schema_version`, `data_mode`, `authority` and an empty `map` (no layers) until 44.3.x fill descriptors; no existing test needed changes.

## Amendment A1 (2026-11-04)

- User direction: analyzers always use `check_urban_exemption_with_geometries`; amend tests instead of keeping old-method mocks. Recorded in EXECUTION_PLAN_44 (3cbd426); 44.3.2 scope gained the urban mocks in `tests/test_corridor_analysis.py` and `tests/test_phase3_contracts.py`.

## 44.3.1

- **Status:** done. Commit a555940 (`feat(map): add map layers to the polygon farmland analysis`).
- **Files:** `src/fpac_soil_mcp/polygon_analysis.py` (`include_map` on `analyze_polygon` and both wrappers; new urban method; `return_geom=include_map`; `_polygon_map`); `tests/test_polygon_map.py` (new, 8 tests).
- **Checks:** `uv run pytest tests/test_polygon_map.py tests/test_polygon_analysis.py -q` 37 passed; root 654 passed / 3 skipped.
- **Deviations:** none. Layers `aoi`, `farmland_classes`, `urban_context` in drop-priority order; AOI not simplified; geometry-error path returns descriptors.
- **Gotchas:** layer order is drop priority, not draw order: 44.6.1 should draw outline-pattern layers above filled ones. `urban_context` is the full intersecting urban areas, not clipped.

## 44.3.2

- **Status:** done. Commits 34633df (`feat(map): add map layers to the corridor farmland analysis`), ce6c190 (format fix).
- **Files:** `src/fpac_soil_mcp/corridor_analysis.py` (`include_map`; per-segment new urban method; segment SDA `return_geom=include_map`, alternative SDA calls unchanged; module-level `_corridor_map`, `_alternative_layer_suffix`; `map_settings` alias because `analyze_corridor` has a local `settings = Settings()`); `tests/test_corridor_map.py` (new, 12 tests); urban mocks amended in `tests/test_corridor_analysis.py` (11) and `tests/test_phase3_contracts.py` (4).
- **Checks:** `uv run pytest tests/test_corridor_map.py tests/test_corridor_analysis.py tests/test_phase3_contracts.py -q` 57 passed; mutation check (forcing `return_geom=True`, breaking urban de-duplication) failed 2 tests as expected; root 666 passed / 3 skipped.
- **Deviations:** layer order `corridor_direct`, `corridor_indirect` (only with indirect input), `corridor_alternative_<id>`, `farmland_classes`, `county_segments`, `urban_context`; `farmland_classes` covers the whole footprint (direct plus indirect) because the segment SDA query runs on the footprint segment; county properties `county_name`, `geoid`, `state_fips`, `county_fips`.
- **Gotchas:** alternative ids map to `[a-z0-9_]` (`Route 9/East` -> `route_9_east`, empty -> `alt`); duplicate suffixes get `_2`, `_3`, ... in input order (`_alternative_layer_ids`, follow-up commit after the wave 3 gate; 5 new tests).

## Process incident (wave 2 and 3)

- Python `open(t, "w").write(open(t).read()...)` truncates before reading, so the 44.2.1, 44.2.2 and 44.3.1 checklists were committed empty (44.2.2 already pushed). Restored in 5dd084a from the STATE reports. Python writes to workspace files can also lag shell reads, which left 34633df unformatted (fixed in ce6c190). From here: copy-backs and edits that are committed in the same step go through the shell.

