# EXECUTION_PLAN_57 -- Remove `include_nccpi`; always include NCCPI as national baseline context (issue #85)

Branch: `feature/nccpi-baseline1` (off `origin/main` e0c625e). Breaking change to the public MCP tool surface.

## Goal & Scope

**Goal.** Remove the `include_nccpi` parameter everywhere and always return per-map-unit NCCPI v3 ratings as a supplementary national baseline next to the primary productivity index. `productivity_index` still selects the only index used for Land Evaluation scoring. This simplifies tool calling and gives every analysis the same cross-state-comparable baseline.

**In scope**
- Domain: `PolygonAnalyzer.analyze_polygon` (+ `_sync` / `_async` wrappers) and `CorridorAnalyzer.analyze_corridor` lose `include_nccpi` and the `ratings_requested` gate; ratings are always fetched when map unit keys exist.
- New per-map-unit NCCPI baseline fields on `SoilMapUnitAcreage` (polygon `map_units` and corridor `county_segments[].map_units`), filled for every index.
- Tools: `analyze_farmland_by_polygon`, `analyze_corridor_fppa`, and the two `lesa_tools` call sites.
- Callers: agent app `geo.py`, JS eval harness `evalCases.js`, criterion 2 benchmark fixture, tests.
- Public docs: registered tool descriptions, `server.json`, `manifest.yaml`, `README.md`, `QUICKSTART.md`.
- Eval corpus: SA-MA-04 `user_prompt` in `eval/eval_cases.v1.json`.
- ADR 0008 amendment.

**Out of scope (explicit)**
- Changing which index drives Land Evaluation (still `productivity_index`).
- Changing SDA query templates (the NCCPI interpretation query already exists).
- Fetching NCCPI and the primary index in one SDA call (follow-up optimization).
- NCCPI relative rating against a county NCCPI max (user: interesting follow-up, not this change).
- Area-weighted NCCPI baseline summaries per AOI or segment.
- Showing the baseline in map layers / `IdentifyPopup` (ADR 0017 map contract; follow-up).
- Corridor alternatives: they build no `SoilMapUnitAcreage` rows today, so they get no baseline fields.
- Historical `planning/` documents (EXECUTION_PLAN_19 .. 46 evidence) keep their `include_nccpi` mentions as history.
- The existing primary-NCCPI `get_productivity_ratings` -> `get_interpretations` fallback in `_get_corridor_ratings` (not related to the removed argument).

**Verbatim constraints from the user**
- "we do not want any fallbacks or relics of the old arguments and everything needs to be wired up properly."
- "include_nccpi should not be a parameter of the tool and supplying it should be an error but it should not occur in the function definition."
- "we want per mapunit fields for every index. if they are null because they arent populated or they are e.g. a miscellaneous non-soil component/mapunit report them as null (not zero or anything that could be interpreted as a rating)"
- ADR 0008 amendment: "clarify that this is intended to simplify the tool calling and make a consistent baseline productivity data available."

## Decision log

| ID | Date | Decision | Source |
| --- | --- | --- | --- |
| D1 | 2026-11-18 | Baseline lives in per-map-unit fields on `SoilMapUnitAcreage`, filled for every index including NCCPI primary (then equal to the primary values). | user |
| D2 | 2026-11-18 | Unpopulated values, sentinels (99 etc.) and miscellaneous / non-soil map units are `null`; never 0, never a default percentage, never anything readable as a rating. | user |
| D3 | 2026-11-18 | Baseline NCCPI query failure appends one limitation line; primary ratings, LE and coverage are unchanged. | user |
| D4 | 2026-11-18 | `include_nccpi` appears in no function signature, docstring, schema, kwargs dict or call site. Supplying it to a tool is an error. FastMCP 4.1.7 already rejects unknown arguments (`ToolError`, pydantic `unexpected_keyword_argument`), so no custom code: a regression test through the registered server proves it. Direct Python callers get `TypeError`. | user + recon |
| D5 | 2026-11-18 | Amend ADR 0008 (no new ADR): purpose is simpler tool calling and a consistent baseline productivity dataset. | user |
| D6 | 2026-11-18 | Baseline content: raw weighted-average NCCPI v3 rating, class, source, rated pct, total pct, coverage status. No benchmark query, no relative rating, no LE effect. Non-NCCPI primary costs one extra `get_interpretations` call per analysis (per county segment for corridors); NCCPI primary reuses the rows already fetched. | user (accepted rec) |
| D7 | 2026-11-18 | Leave historical `planning/` mentions untouched. | user (accepted rec) |
| D8 | 2026-11-18 | Execution model as Plan 56: one Genie Code agent runs tasks serially in `~/fpac-soil-mcp` with a plan gate per task; one local commit per task (commits allowed on the feature branch); ask before every push; offline only (fakes / fixtures). | user (accepted rec) |
| D9 | 2026-11-18 | Polygon `tabular_csv` gains `nccpi_baseline_rating` and `nccpi_baseline_rating_class` columns (empty cell for null). Corridor CSV is a per-county summary and is unchanged. | my proposal, flagged for review |
| D10 | 2026-11-18 | `nccpi_baseline_coverage_status` is `null` when SDA returned no NCCPI row for the map unit; `"rated"` / `"partial"` / `"unrated"` only when a row exists. | my proposal, flagged for review |

## Recon log (facts, 2026-11-18 on e0c625e)

- Real files: `src/fpac_soil_mcp/domain/polygon_analyzer.py` (591 lines) and `domain/corridor_analyzer.py` (1410 lines); the issue's `polygon_analysis.py` / `corridor_analysis.py` names are stale.
- Today `include_nccpi=True` with `csr2` fetches only CSR2; NCCPI is never fetched for non-NCCPI indexes. The baseline is new behavior.
- Gate: `ratings_requested = include_nccpi or norm_idx != "nccpi"` at polygon_analyzer.py:184 and corridor_analyzer.py:247; corridor uses it at ~464, ~476, ~674, ~800, ~994, ~1017.
- `SoilMapUnitAcreage` (models/soil.py:111) is constructed only at polygon_analyzer.py:~318 and corridor_analyzer.py:~585. Corridor alternatives build no map-unit models.
- NCCPI rule name: `SDV_RATING_REGISTRY["nccpi"].rule_name` (`clients/sda/sdv_registry.py`); sentinels: `PRODUCTIVITY_SEMANTICS["nccpi"]["sentinels"]` (sdv_registry.py:231). `SDAClient.get_interpretations(mukeys, rule_name, aggregation_method)` at clients/sda/client.py:372.
- Live `include_nccpi` refs outside `planning/`: geo.py:352, app tests/test_geo_screen.py:272, eval/fpac_soil_mcp_harness/lib/evalCases.js:96, spatial_analysis_tools.py (35, 51, 68, 81, 103, 138), lesa_tools.py (348, 434), polygon_analyzer.py (103, 112, 184, 562-587), corridor_analyzer.py (211, 225, 247), tests/test_polygon_analysis.py (141, 148, 179), tests/test_tools.py (572, 707, 937, 973, 985, 1006, 1015), tests/test_phase2_contracts.py:99, tests/test_phase3_contracts.py (184, 314, 323, 661), tests/fixtures/criterion2_benchmark.v1.json (4x; compared against manifest by tests/test_criterion2_benchmark.py).
- Registered descriptions: `src/fpac_soil_mcp/mcp/tools/__init__.py` (~69 polygon, ~129 corridor). `tests/test_server.py` asserts runtime descriptions == `server.json` == `manifest.yaml`, so all three change together.
- SA-MA-04 facts and guidelines already allow supplementary NCCPI (242917a); only `user_prompt` (eval_cases.v1.json:923) still says "rather than silently substituting NCCPI". No `prompt_test_cases.json` exists.
- README.md:49, QUICKSTART.md:81 describe polygon screening; neither mentions `include_nccpi`.
- Baseline (STATE_57): root offline pytest 993 passed / 3 skipped / 45 deselected; app pytest 310 passed; JS harness 20/20.

## Hazards

- `tests/test_polygon_analysis.py:141` used `include_nccpi=False` so its single-response SDA mock never got a rating query. Without the flag the mock must answer rating and baseline queries too.
- Waves 2 and 3 edit the same analyzer files: sequence, never parallelize across waves.
- Wave 2 order is callers first (57.2.1-57.2.3), analyzers last (57.2.4, 57.2.5): while the analyzers still accept the kwarg, removing it from callers keeps every intermediate commit green. Reversing the order breaks `lesa_tools` between commits.
- Workspace FS rejects `__pycache__`: always `PYTHONDONTWRITEBYTECODE=1` and `-p no:cacheprovider`. Ruff in the workspace clone reports false EXE002; lint a `git archive HEAD` copy in `/tmp`.
- JS harness needs `node_modules`: run from a `git archive HEAD eval` copy in `/tmp` after `npm ci` (whole `eval/` tree, harness reads `eval/common`).
- Corridor: one limitation per failed baseline query, deduplicated across segments.

## Wave table

| Wave | Theme | Tasks | Depends on | Gate |
| --- | --- | --- | --- | --- |
| 1 | Baseline building block | 57.1.1 | baseline recorded | targeted + root suite |
| 2 | Remove `include_nccpi` everywhere (breaking) | 57.2.1, 57.2.2, 57.2.3, 57.2.4, 57.2.5 | 1 | root suite, app-test, harness tests |
| 3 | Wire the NCCPI baseline | 57.3.1, 57.3.2 | 2 | root suite |
| 4 | Public surface, eval, ADR | 57.4.1, 57.4.2, 57.4.3 | 3 | root suite, harness tests |
| 5 | Final verification | 57.5.1 (blocking), 57.5.2 (post-SDA, non-blocking) | 4 | all gates |

Files within each wave are pairwise disjoint (checked in review). Execute tasks in id order; the Wave 2 specs below are listed analyzers-first, but 57.2.1-57.2.3 (callers) run before 57.2.4-57.2.5 (analyzers).

## Task specs

### 57.1.1 -- NCCPI baseline model fields and helper
- Repo: fpac-soil-mcp. Depends on: none.
- Must edit: `src/fpac_soil_mcp/models/soil.py`. Can create: `src/fpac_soil_mcp/domain/nccpi_baseline.py`, `tests/test_nccpi_baseline.py`. Scratch: `/tmp`.
- Spec:
  - Add to `SoilMapUnitAcreage`, all `default=None`: `nccpi_baseline_rating: float | None`, `nccpi_baseline_rating_class: str | None`, `nccpi_baseline_rating_source: str | None`, `nccpi_baseline_coverage_status: str | None`, `nccpi_baseline_rated_pct: float | None`, `nccpi_baseline_total_pct: float | None`. Descriptions state: supplementary NCCPI v3 national baseline, always included, never used for Land Evaluation; null means no rating (never 0).
  - New module `domain/nccpi_baseline.py`:
    - `fetch_nccpi_baseline(sda_client, mukeys, *, primary_index: str, primary_rows: Mapping[str, Mapping[str, Any]]) -> tuple[dict[str, dict[str, Any]], str | None]`. If `primary_index == "nccpi"`, build from `primary_rows` with no SDA call. Otherwise one `sda_client.get_interpretations(mukeys=..., rule_name=SDV_RATING_REGISTRY["nccpi"].rule_name, aggregation_method="Weighted Average")`. On `SDAClientError` return `({}, "NCCPI national baseline unavailable: <exc>")`. Empty `mukeys` -> `({}, None)`, no call.
    - `nccpi_baseline_fields(row: Mapping[str, Any] | None) -> dict[str, Any]` returning exactly the six model kwargs. No row -> all six `None`. Rating `None`, non-numeric or in `PRODUCTIVITY_SEMANTICS["nccpi"]["sentinels"]` -> rating and class `None`. Pcts taken only from the row (never defaulted to 0 or 100). Coverage: row present and rating set -> `"partial"` if rated_pct < total_pct else `"rated"`; row present, no rating -> `"unrated"`; no row -> `None` (D10).
- Anchors: `class SoilMapUnitAcreage` (soil.py:111); `PRODUCTIVITY_SEMANTICS`, `SDV_RATING_REGISTRY` in `clients/sda/sdv_registry.py`; reference pattern `_normalize_corridor_rating` (corridor_analyzer.py:121) and the NCCPI branch in polygon_analyzer.py ~186-210.
- Do not touch: analyzers, tools.
- Acceptance: tests cover no SDA call for NCCPI primary; exactly one call for each of csr2/cpi/storie; sentinel 99 -> null; misc map unit row (null rating, e.g. muname "Water") -> rating/class null, status `"unrated"`; unknown mukey -> all null; SDA error -> `{}` + limitation; model default JSON shows `null` for all six. Command: `uv run --group dev pytest tests/test_nccpi_baseline.py tests/test_models.py -q -p no:cacheprovider`.

### 57.2.4 -- Remove `include_nccpi` from the polygon analyzer
- Depends on: 57.2.1 (callers no longer pass the kwarg). Must edit: `src/fpac_soil_mcp/domain/polygon_analyzer.py`, `tests/test_polygon_analysis.py`, `tests/test_phase2_contracts.py`.
- Spec: delete the parameter and its docstring line from `analyze_polygon`, `analyze_polygon_sync`, `analyze_polygon_async`; delete `ratings_requested`; rating fetch and county-max block run whenever `mukeys` / `raw_units` exist. Delete `test_analyze_polygon_include_nccpi_false_skips_rating_query`; fix the line-141 test's mock to answer rating queries; drop the kwarg at test_phase2_contracts.py:99. Add a test that `analyze_polygon(..., include_nccpi=True)` raises `TypeError`.
- Anchors: `ratings_requested` (~184), `def analyze_polygon_sync` (~558), `def analyze_polygon_async` (~575).
- Do not touch: baseline wiring (57.3.1), CSV.
- Acceptance: `git grep -n include_nccpi -- src/fpac_soil_mcp/domain/polygon_analyzer.py tests/test_polygon_analysis.py tests/test_phase2_contracts.py` empty except the new TypeError test; `uv run --group dev pytest tests/test_polygon_analysis.py tests/test_phase2_contracts.py -q -p no:cacheprovider`.

### 57.2.5 -- Remove `include_nccpi` from the corridor analyzer
- Depends on: 57.2.1. Must edit: `src/fpac_soil_mcp/domain/corridor_analyzer.py`, `tests/test_corridor_analysis.py`.
- Spec: delete the parameter and docstring line from `analyze_corridor`; delete `ratings_requested` and every use (~464, ~476, ~674, ~800, ~994, ~1017), removing branches that become dead (`not ratings_requested`) rather than leaving constant conditions. Fix the docstring `productivity_index` line to name all four selectors. Add a `TypeError` test for `include_nccpi=`.
- Anchors: `def analyze_corridor` (~204), `ratings_requested`.
- Do not touch: `_get_corridor_ratings` fallback, alternatives logic beyond the gate.
- Acceptance: grep on both files empty except the TypeError test; `uv run --group dev pytest tests/test_corridor_analysis.py tests/test_corridor_scoring.py tests/test_multi_county_productivity.py tests/test_corridor_map.py -q -p no:cacheprovider`.

### 57.2.1 -- Remove `include_nccpi` from the MCP tools and LESA call sites
- Depends on: 57.1.1. Must edit: `src/fpac_soil_mcp/mcp/tools/spatial_analysis_tools.py`, `src/fpac_soil_mcp/mcp/tools/lesa_tools.py`, `tests/test_tools.py`, `tests/test_phase3_contracts.py`, `tests/fixtures/criterion2_benchmark.v1.json`.
- Spec: remove the parameter, docstring lines and `corridor_kwargs["include_nccpi"]` from both tools; update both `productivity_index` docstring lines to list `nccpi`, `csr2`, `cpi`, `storie` and say it selects the Land Evaluation index while NCCPI is always included as baseline. Remove the kwarg at lesa_tools.py ~348 and ~434. In tests, drop the kwarg from calls and `assert_called_once_with` expectations; delete the `include_nccpi=False` corridor case (~1006/1015) or turn it into a csr2 case without the flag. Remove the 4 fixture occurrences.
- Anchors: `def analyze_farmland_by_polygon`, `def analyze_corridor_fppa`, `corridor_kwargs`, `analyze_corridor(` and `analyze_polygon(` in lesa_tools.py.
- Do not touch: `tools/__init__.py` descriptions (57.4.1).
- Acceptance: grep on the five files empty; `uv run --group dev pytest tests/test_tools.py tests/test_phase3_contracts.py tests/test_criterion2_benchmark.py tests/test_lesa.py -q -p no:cacheprovider`.

### 57.2.2 -- Remove `include_nccpi` from the agent app
- Depends on: 57.1.1. Must edit: `apps/agent-fpac-soil-openai-sdk/agent_server/geo.py`, `apps/agent-fpac-soil-openai-sdk/tests/test_geo_screen.py`.
- Spec: drop the key from the `ANALYSIS_TOOL` arguments (~352) and from the test expectation (~272).
- Acceptance: grep empty in `apps/`; `make app-check` (ruff on a `/tmp` archive copy if EXE002 appears).

### 57.2.3 -- Remove `include_nccpi` from the JS eval harness
- Depends on: 57.1.1. Must edit: `eval/fpac_soil_mcp_harness/lib/evalCases.js` (+ `test/harness.test.js` only if it asserts the derived arguments).
- Spec: `analyze_farmland_by_polygon` deriver returns `{ geojson: tc.sample_geometry }`.
- Acceptance: grep empty in `eval/`; harness `node --test test/harness.test.js test/smoke.test.js` 20/20 from a `/tmp` archive copy with `npm ci`.

### 57.3.1 -- Wire the NCCPI baseline into polygon analysis
- Depends on: 57.1.1, 57.2.4. Must edit: `src/fpac_soil_mcp/domain/polygon_analyzer.py`, `tests/test_polygon_analysis.py`.
- Spec: after the primary rating fetch, call `fetch_nccpi_baseline` (pass `rating_map` as `primary_rows` for NCCPI primary); append the limitation if returned; pass `**nccpi_baseline_fields(baseline.get(mukey_str))` into `SoilMapUnitAcreage`. Add CSV columns `nccpi_baseline_rating`, `nccpi_baseline_rating_class` (empty cell for `None`, D9). LE, `le_summary`, primary fields unchanged.
- Anchors: `# 4. Ingest Productivity Ratings` (~180), `SoilMapUnitAcreage(` (~318), `# 6. Generate CSV table` (~428).
- Acceptance tests: for csr2, cpi, storie: baseline fields populated from the fake NCCPI rows, primary fields and LE identical to a run where the baseline fake returns nothing; nccpi primary: baseline equals primary and `get_interpretations` called once; misc unit -> baseline null in model and empty in CSV; baseline `SDAClientError` -> one limitation, primary + LE unchanged. Command: `uv run --group dev pytest tests/test_polygon_analysis.py tests/test_polygon_map.py tests/test_phase2_contracts.py -q -p no:cacheprovider`.

### 57.3.2 -- Wire the NCCPI baseline into corridor analysis
- Depends on: 57.1.1, 57.2.5. Must edit: `src/fpac_soil_mcp/domain/corridor_analyzer.py`, `tests/test_corridor_analysis.py`.
- Spec: per county segment, after `_get_corridor_ratings`, call `fetch_nccpi_baseline` (`interp_map` as `primary_rows` for NCCPI primary); add limitation once (dedupe across segments); spread `nccpi_baseline_fields(...)` into `SoilMapUnitAcreage(` (~585). Composite LE, segment LE, reconciliation unchanged. No alternative changes.
- Acceptance tests: two-county csr2 corridor has baseline on every segment map unit; nccpi primary reuses rows (no extra call); misc unit null; one segment's baseline failure -> one limitation, LE unchanged. Command: `uv run --group dev pytest tests/test_corridor_analysis.py tests/test_multi_county_productivity.py tests/test_corridor_scoring.py -q -p no:cacheprovider`.

### 57.4.1 -- Tool descriptions, published metadata and docs
- Depends on: 57.3.1, 57.3.2. Must edit: `src/fpac_soil_mcp/mcp/tools/__init__.py`, `server.json`, `manifest.yaml`, `README.md`, `QUICKSTART.md`, `tests/test_server.py`.
- Spec: polygon and corridor descriptions (identical text in all three metadata files) say NCCPI v3 is always included per map unit as national baseline context and `productivity_index` (nccpi, csr2, cpi, storie) selects the index used for Land Evaluation scoring. README/QUICKSTART: same wording, plus a short breaking-change note that `include_nccpi` was removed. Add tests: `list_tools()` input schemas for both tools have no `include_nccpi` property; `call_tool` with `include_nccpi` raises `ToolError` for both tools (fake analyzers or patched SDA, no network).
- Acceptance: `uv run --group dev pytest tests/test_server.py -q -p no:cacheprovider`.

### 57.4.2 -- SA-MA-04 eval prompt
- Depends on: 57.3.1. Must edit: `eval/eval_cases.v1.json` (SA-MA-04 only; any test asserting the prompt text, if one exists, is in scope after the orchestrator confirms).
- Spec: replace "and state when evidence is unavailable rather than silently substituting NCCPI" with wording that keeps CSR2 as the scoring index, allows NCCPI as baseline context, and asks to state unavailable evidence. Keep facts and guidelines.
- Acceptance: `uv run --group dev pytest eval/common eval/contract -q -p no:cacheprovider`; harness tests 20/20.

### 57.4.3 -- Amend ADR 0008
- Depends on: 57.3.1, 57.3.2. Must edit: `docs/decisions/0008-nccpi-validated-public-index-with-extensible-sdv-routing.md`, `docs/decisions/README.md` (index status cell).
- Spec: dated amendment (2026-11-18) under Decision Outcome: NCCPI national baseline always returned per map unit; purpose = simpler tool calling + consistent baseline productivity data; `include_nccpi` removed (breaking); null semantics (D2); LE still from `productivity_index`; follow-ups (relative rating, single-call fetch, map display). Index row: `Accepted (amended 2026-10-27, EP39; 2026-11-18, EP57)`.
- Acceptance: links resolve (`grep -n 0008 docs/decisions/README.md`); no other ADR edited.

### 57.5.1 -- Final verification (orchestrator)
- `git grep -n include_nccpi -- ':!planning'` returns only the two `TypeError` tests and the `ToolError` tests.
- Root suite, `make lint` + `make format-check` (archive copy), `make app-check`, harness tests: all green vs. baseline.
- In-memory FastMCP smoke with fake SDA: csr2 polygon and corridor responses show primary CSR2 + NCCPI baseline fields, null for a misc unit, unchanged LE.
- Update STATE_57 goal table; ask before push.

### 57.5.2 -- Post-SDA checks (non-blocking for merge)
- When SDA is reachable: `make test-live`; T1 `eval-databricks` for SA-MA-01..04 (README command); record results in STATE_57.
