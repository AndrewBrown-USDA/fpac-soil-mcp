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
| 4 | Genie Code | 44.4.1 | done |
| 4 | gate | root check, app-check, test-live | passed on 18d76dd (688 passed / 3 skipped; app 135; live 43 / 3 skipped) |
| 5 | Genie Code | 44.5.1 | done, a98cbad |
| 5 | User + Genie Code | 44.5.2 (dev apps, MCP server lookup, A3) | done, 0d6ed22; fixes 8138b45, 1db8429 |
| 5 | gate | root check, app-check | pending |
| 6 | Genie Code | 44.6.1 | done, 0653022; fixes 48b3fe8, 95719d9 |
| 6 | gate | root check, app-check, app-frontend-check | pending |
| 7 | Genie Code | 44.7.1 | done (not yet seen in a browser) |
| 7 | gate | root check, app-check, app-frontend-check | pending |
| 8 | User + Genie Code | 44.8.1 | done, trial passed (planning/evidence/44.8.1-trial.md) |
| 8 | Genie Code | 44.8.2 | done (not yet seen in a browser) |
| 8 | gate | root check, app-check, app-frontend-check | pending |
| 9 | Genie Code | 44.9.1 | done (not yet seen in a browser) |
| 9 | Genie Code | 44.9.2 | done |
| 9 | gate | root check, app-check, app-frontend-check | pending |
| 10 | User + Genie Code | 44.10.1 | in progress (planning/evidence/44.10.1-trial.md) |
| 11 | Genie Code | 44.11.1 | done, 95e78d1 (`planning/REVIEW_44.md`) |
| 11 | Genie Code | 44.11.2 | done, 0d607d4 |
| 11 | Genie Code | 44.11.4 | done, 83887aa |
| 11 | Genie Code | 44.11.5 | done, e1a544e |
| 11 | Genie Code | 44.11.6 | done, 34bf2c7 |
| 11 | Genie Code | 44.11.7 | done, 9d035c9; user browser check pending |
| 11 | User + Genie Code | 44.11.3 | in progress: T1 done (POLY-01 ok, POLY-02 blocked on WKT follow-up); browser check pending (planning/evidence/44.11.3-eval.md) |
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

## Wave 3 follow-up and push

- 1156bba (`fix(map): give each corridor alternative a unique map layer id`): `_alternative_layer_ids` adds `_2`, `_3`, ... for ids that clean up to the same suffix; 5 new tests; root 671 / 3. Wave 3 pushed 57b627d..1156bba with user approval.

## Amendment A2 (2026-11-04)

- User direction: contract test file named `tests/test_map_tool_contracts.py` (not `test_phase8_contracts.py`). 44.4.1 also documents the two map settings in the README configuration reference. Recorded in EXECUTION_PLAN_44 (bcbd7b2).

## 44.4.1

- **Status:** done. Commit 18d76dd (`feat(map): add include_map to the polygon and corridor tools`).
- **Files:** `src/fpac_soil_mcp/tools/spatial_analysis_tools.py` (`include_map: Annotated[bool, Field(description="Leave false. ...")] = False` on both tools, always passed to the analyzer); `tests/test_tools.py` (3 call assertions amended with `include_map=False`, 4 pass-through tests); `tests/test_map_tool_contracts.py` (new, 13 tests through `FastMCP` + `register_tools` on synthetic clients); `README.md` (both tool rows, `MAP_SIMPLIFY_TOLERANCE_M`, `MAP_MAX_GEOJSON_BYTES`).
- **Checks:** contract + tools + phase 3 tests 13 / 30 / 13 passed; root 688 passed / 3 skipped.
- **Deviations:** size check uses a fixed 4,000-byte margin, not 10%: the additive keys measured 2,163 bytes (polygon, +43%) and 2,657 bytes (corridor, +47%) on the small fixtures, mostly the farmland legend. The pre-change response is the same call with the four additive keys removed (no stored fixture). The section 4 table in the test is checked against the ADR table text, so ADR edits that add or drop a row fail the test.
- **Gotchas for 44.5.x:** the MCP JSON schema shows `include_map` with `default: false` and the "Leave false." description; the tool-level `description` strings in `tools/__init__.py` do not mention it. Default responses grow by about 2-3 KB per call (descriptor layers and legend), which reaches the model context; if that matters for agent token budgets, a later task could trim descriptors when `include_map` is false. `.env.example` still lacks the map settings.
- **Process:** shell writes to workspace files can also lag `git` reads; edits now land via `/tmp` clone + `cat >` and a `cmp` check before commit.

## Amendment A3 (2026-11-04)

- User direction: a dev agent app plus `mcp-fpac-soil-dev`, both from git on the dev branch; the production agent app stays on `main`. The agent app's MCP URL comes from its `mcp_server` resource (`FPAC_MCP_APP` `valueFrom`, SDK lookup), so `app.yaml` is branch-neutral and close-out has nothing to revert. 44.5.2 and 44.12.1 rewritten in EXECUTION_PLAN_44.

## Open items

- Default `map` descriptors add about 2.0-2.5 KB per analyze call to model context (legends about 1 KB, colour and pattern about 0.4 KB, null or false fields about 0.4-0.6 KB). Kept unconditional (user, 2026-11-04). Measure the share on real AOIs during the 44.8.1 trials; unconditional trims if needed: omit null or false descriptor fields, or legend colours by `style_key`.
- `.env.example` lacks `MAP_SIMPLIFY_TOLERANCE_M` and `MAP_MAX_GEOJSON_BYTES`.
- Follow-up after Plan 44 (user, 2026-11-04): AOI memory within a chat session, so the user and the agent can refer to several AOIs (for example, comparing alternative sites). Today one AOI per chat (ADR 0016): a new AOI replaces the old, and "Show on map" reports "Not available" for calls made on an earlier AOI. Needs its own plan and an ADR 0016 amendment: per-chat list of `aoi_ref` -> geometry (session storage, bounded count and size), naming/selection in the panel, `active_aoi` widened to the referenced set for substitution in chat and `/api/geo/map`, and the model note listing the available references. Corridor alternatives already compare inside one `analyze_corridor_fppa` call.

## Wave 5 progress (2026-11-04)

- 47e99f0 A3 recorded; a98cbad 44.5.1; 0d6ed22 44.5.2 Genie Code part (`agent.py` and `test_agent_mcp_wiring.py` added to its scope).
- Gates on 0d6ed22: root `make check` 688 passed / 3 skipped (unchanged, no server code); `make app-check` 173 passed (was 135). Live suite not rerun (no server change).
- Not pushed. Push waits for user approval after the dev apps exist.
- Pushed `fdc0e4c..527da95` (user approval). Both dev apps RUNNING on 527da95, git source `feature/agent-app-map2`, auto-deploy on (the dev agent app's was turned on after its first deploy):
  - `mcp-fpac-soil-dev`: https://mcp-fpac-soil-dev-7474654188777746.aws.databricksapps.com, deployment 01f1d8b1ef2a149ebb7f69ec15d690d3, SP `app-2vrjmx mcp-fpac-soil-dev`.
  - `agent-fpac-soil-dev`: https://agent-fpac-soil-dev-7474654188777746.aws.databricksapps.com, deployment 01f1d8b3839618b8a717abcad3dbffb4, SP `app-2vrjmx agent-fpac-soil-dev`; resources `mcp_server` -> `mcp-fpac-soil-dev` CAN_USE, `llm-endpoint` `models.ai.gpt-5-6-luna`, `experiment` 4493391463784067.
  - Production `agent-fpac-soil-openai-sdk` unchanged on `main` 06525de.
- Smoke call not possible from Genie Code: the dev server returns 401 to the workspace PAT, and app log access fails the same OAuth exchange. Pending user browser check on the dev agent app (see 44.5.2 checklist).
- Every push to the branch now redeploys both dev apps.
- Browser check failed: every screening returned the tool-error display. Dev server log: `Invalid arguments for tool 'analyze_farmland_by_polygon': unexpected_keyword_argument` at 01:29 UTC, while `apps get` reports 527da95 (the branch has `include_map`, `main` does not). `main.py` imported `fpac_soil_mcp` from the installed environment, which evidently held an older build of the same version 0.4.0. Fix: `main.py` puts its own `src/` first on `sys.path`; `tests/test_main_entrypoint.py` (3 tests). Root `make check` 691 passed / 3 skipped. Needs a push to redeploy both dev apps.
- 1db8429 bumps the package to 0.5.0 (user direction) so an environment holding an older 0.4.0 build cannot satisfy the install. Pushed `527da95..1db8429`; both dev apps redeployed on 1db8429: `mcp-fpac-soil-dev` 01f1d8c643a416c39d3420671dfa3e4b, `agent-fpac-soil-dev` 01f1d8c644121f89adfb33529c3cd3e0.
- 44.5.2 acceptance (user browser check, 2026-11-04): screening on the dev agent app succeeds through `mcp-fpac-soil-dev` with `include_map=True`; chat tool calls work (the `FPAC_MCP_APP` lookup works with CAN_USE alone). Wave 5 done.
- Open: dev agent app traces are not saved (`PERMISSION_DENIED`: `app-2vrjmx agent-fpac-soil-dev` lacks SELECT on `users.andrew_g_brown.4493391463784067_otel_spans`); user to grant or switch experiment. Not a wave gate.
- Wave 6 (2026-11-04): 0653022 44.6.1. Gates: `make app-check` 173 passed; `make app-frontend-check` passed; `tsc` 5 errors before and after, none in `components/map/`. Root suite unaffected (no root files). Rendering not yet checked in a browser.
- Wave 6 fixes: 48b3fe8 draws outline-only layers above filled layers (server order is drop priority); 95719d9 keeps the map at the panel's full visible height when results show (user report: the map halved after screening). Pushed `1db8429..95719d9` early with user approval to check the renderer. Dev apps on 95719d9: `mcp-fpac-soil-dev` 01f1d8cc00d21e4aaf59068031777b9d, `agent-fpac-soil-dev` 01f1d8cc00c91179bc5ebdb158638886.
- Wave 6 browser check (user, 2026-11-04): renderer looks right; map height stays fixed after screening. Wave 6 done.
- A4 (user, 2026-11-05, trial 44.8.1): corridor alternatives report the same class breakdown as the primary (`prime_farmland_acres`, `conditional_prime_acres`, `statewide_importance_acres`, `local_importance_acres`, `unique_farmland_acres`, `not_prime_acres`, `not_prime_pct`, `unmapped_acres`; additive on `CorridorAlternativeComparison`), and with `include_map=true` the `farmland_classes` layer also covers each alternative, clipped to ground outside the primary footprint and earlier alternatives (pieces carry `alignment`, no `area_ac`). Alternative SDA calls now follow `include_map` for `return_geom`; numbers unchanged with or without the map. Local check (two-alternative Ames prompt): Alt B 173.13 ac = 79.8 prime + 69.51 conditional + 14.53 statewide + 9.29 not prime; Alt C 200.39 ac = 71.89 + 48.19 + 58.48 + 21.81 not prime + 0.02 unmapped; farmland features main 131, Alt B 127, Alt C 137; 428 KB, no warnings. Root `make check` 694 passed / 3 skipped.
- Wave 8 (2026-11-05): 44.8.1 trial passed; M4 exit criterion met. Dev apps on cfe1b57. Next: 44.8.2 overlay catalog and toggles.
- Wave 9 (2026-11-06): 44.9.1 5444db6; 44.9.2 docs (ADR 0015 local changes, app README map results and dev trial apps, app AGENTS.md). Root `make check` 694 passed / 3 skipped; `make app-check` 175 passed; doc links resolve. Efficiency review handoff prompt in `planning/HANDOFF_EFFICIENCY_REVIEW.md` (follow-up, not a Plan 44 task).
- 2026-11-07: SSURGO native-size revert bfa39cd, trial note f2baab2, handoff e760691; pushed with user approval; both dev apps RUNNING on e760691. 44.10.1 awaits the user's re-check.

## 44.11.1

- **Status:** done. Commit 95e78d1 (`docs(planning): add the two-axis branch review`).
- **Files:** `planning/REVIEW_44.md` (new): 16 findings R1-R16, none high. Not read line by line: the analyzer map code and the `mapLayers.ts`/`MapPanel.tsx`/`Legend.tsx` renderer (relied on task tests, gates and the trials).
- **Checks:** cited lines re-grepped; `git merge-tree HEAD origin/main` (87e0a75) has no conflicts.
- **Decisions (user, 2026-11-07, A5):** fix R1-R3 and R8 (44.11.2) and R12 (44.11.3, POLY-01/POLY-02 evals); accept R4-R6, R9-R11 and R13; defer R7 (server-served vertex limit), R14 and R15 to `MASTER_PLAN.md`. R8 done in the plan Decision Log (A4).

## 44.11.2

- **Status:** done. Commit 0d607d4 (`docs: align AOI screening docs and env example with the map result contract`).
- **Files:** app `AGENTS.md` L34 (one MCP call, R1); ADR 0016 dated amendment 2026-11-07 after the acceptance note (R2, original text kept); `.env.example` commented `MAP_SIMPLIFY_TOLERANCE_M=1.0` and `MAP_MAX_GEOJSON_BYTES=2000000` (R3).
- **Checks:** `grep -c "two MCP calls"` 0; `grep MAP_ .env.example` shows both; env vars load into `Settings` (2.5 / 123 test values). Fresh `/tmp/g44` clone at 0d607d4: root `make check` rc 0, 694 passed / 3 skipped; `make app-check` rc 0, 175 passed. (In the workspace clone, ruff reports only EXE002 from file modes.)
- **Deviations:** none; R7 comment dropped (user chose a server-served limit follow-up).
- Pushed `e760691..a7816d9` (user-approved, 2026-11-07).

## A6 (user, 2026-11-07): "add show on map" for POLY-02

- Recorded in the plan Decision Log with tasks 44.11.4 and 44.11.5 (ec37816).

## 44.11.4

- **Status:** done. Commit 83887aa (`feat(map): add the map result to get_soil_polygons_by_geometry`).
- **Files:** `tools/soil_lookup_tools.py` (`include_map: IncludeMap = False`; `_soil_map_fields` adds `schema_version`, `data_mode`, `authority`, `map` with `aoi` + `farmland_classes` from the fetched rows, on success and both error paths); `tests/test_soil_polygons_map.py` (new, 7 tests); `tests/test_map_tool_contracts.py` (schema test covers the tool); root `README.md` tool row; ADR 0017 (A6 folded in).
- **Checks:** new tests 7 passed, and 8 fail with the old `soil_lookup_tools.py`. Fresh `/tmp/g44` clone: root `make check` 701 passed / 3 skipped (694 + 7); `make test-live` 43 passed / 3 skipped.
- **Gotcha for 44.11.3:** the POLY-02 prompt gives the AOI as WKT (`POLYGON((...))`), but `parse_geojson_geometry` accepts only GeoJSON (a WKT string raises "Invalid GeoJSON string"). The case passes only if the model converts it to GeoJSON. Not changed here; the eval will show whether it does. User (2026-11-07): WKT input support is a follow-up, not a Plan 44 task; list it in `MASTER_PLAN.md` at close-out.

## 44.11.5

- **Status:** done. Commit e1a544e (`feat(agent-app): show soil polygon results on the map`).
- **Files:** `geo.py` (`SOIL_POLYGONS_TOOL` in `MAP_TOOLS` and `MapRequest`); app `tests/test_geo_map.py` (soil tool accepted with `aoi_ref` substitution and forced flag; removed from the reject list); `ShowOnMapButton.tsx` `MAP_TOOLS`; app `README.md`; ADR 0015 `message.tsx` entry; ADR 0016 2026-11-07 amendment.
- **Checks:** new test fails with the old `geo.py` (1 failed) and passes with the new one. Fresh `/tmp/g44` clone: `make app-check` 175 passed (one test added, one reject case removed); `make app-frontend-check` rc 0 (10 biome warnings, baseline), build OK; `tsc` 5 errors, none in `components/map/`.

## A7 (user approved, 2026-11-09): result polygon popup from `include_map`

- Plan Decision Log 16 and tasks 44.11.6, 44.11.7 (315915c). Also from the browser check: popup headings sized to the content (516f80f).

## 44.11.6

- **Status:** done. Commit 34bf2c7 (`feat(map): add map unit productivity to farmland features`).
- **Files:** `map_contract.py` (`PRODUCTIVITY_PROPERTIES`, `with_productivity`, `productivity_by_mukey`; `features_from_sda_rows` passes the keys through); `polygon_analysis.py` (from `unit_models` for rated mukeys); `corridor_analysis.py` (primary from segment `unit_models`; alternatives from their own rating query via `_feature_ratings`; the alternative rows are now collected after that query); tests in `test_map_tool_contracts.py` (2) and `test_corridor_map.py` (1); ADR 0017 layer table. Scope note: `test_corridor_map.py` added to the task's files for the alternative case.
- **Checks:** the 3 new tests fail with the old analyzers. Fresh `/tmp/g44` clone: root `make check` 704 passed / 3 skipped (701 + 3); `make test-live` 43 passed / 3 skipped. Existing call-count and "numbers unchanged" tests still pass.

## 44.11.7

- **Status:** done (code). Commit 9d035c9 (`feat(agent-app): identify drawn farmland polygons on click`); user browser check pending.
- **Files:** `mapLayers.ts` (invisible `result-farmland_classes-hit` fill so outline-only classes are clickable), `IdentifyPopup.tsx` (`resultInfo`, "Result: map unit" section: name, symbol, farmland class, acres, productivity and index, alignment for corridor alternatives; footer line only with overlay sections), `MapPanel.tsx` (queries the hit layer on click; the hint only when neither a result nor an in-range layer), app `README.md`.
- **Checks:** `make app-frontend-check` rc 0 (10 biome warnings, baseline), build OK; `tsc` 5 errors, none in `components/map/`. No frontend unit test. Browser check pending.
