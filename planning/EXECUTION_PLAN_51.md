# EXECUTION PLAN 51: Guided AD-1006 Interview and CDL Map Context

## Goal & Scope

**Goal:** Add a conversational, “ask user question” workflow to the existing
agent chat so analysts can review all 12 AD-1006 Site Assessment criteria,
provide qualitative or semi-quantitative answers with rationale, confirm the
answers, and submit supported inputs to the existing preliminary LESA
calculator. At assessment start, the workflow uses a combined CDL analysis to
show the AOI, a one-mile exterior ring, and a 30 m exterior band under the
latest verified CDL vintage. CDL remains crop/land-cover context, not an
authoritative FPPA source or an automatic Criterion 2 score.

**In scope:**

- Refresh the generated eCFR reference files and verify the current
  Site Assessment registry against 7 CFR Part 658 before enabling the guided
  scoring flow.
- Align only Criterion 7's registry score bands with the exact five-percentage-
  point deductions in § 658.5(b)(7), as explicitly authorized after refresh
  identified a mismatch.
- Add one combined MCP CDL-context analysis that reuses the existing CDL
  client and returns full class distributions for the AOI, a one-mile
  buffer-minus-AOI ring, and a 30 m buffer-minus-AOI band, all using one
  latest verified vintage.
- Preserve per-class evidence, coverage, vintage, source, and provenance. Do
  not produce a default binary “agricultural” percentage or translate ring
  area into a Criterion 2 perimeter percentage.
- Add the agent-chat interview for all 12 AD-1006 criteria, allow unknown or
  partial answers, show a review summary, require explicit confirmation before
  the existing preliminary LESA calculation, and keep assessment state in the
  current conversation only.
- Automatically run CDL context once when a guided Site Assessment starts and
  an AOI is attached. If CDL is unavailable or coverage is incomplete, report
  that state and continue without inventing evidence or points.
- Add a fixed, toggleable CDL raster context layer and a “Show CDL on map”
  action that displays the three class summaries in the map panel.
- Add focused offline tests, frontend lint/build validation, and a local
  browser walkthrough. No deployed dev-app walkthrough is required.

**Out of scope:**

- Official NRCS/agency determinations, agency-approved scores, completed or
  signed forms, legal exemption decisions, site selection, or alternative
  recommendations.
- Treating CDL as authoritative evidence of active farming, legal farmland
  status, non-urban status, or direct boundary contact.
- Automatically prefilling or awarding Criterion 2 points from CDL. The
  analyst continues to supply or confirm the criterion’s perimeter percentage
  with provenance.
- Changes to LESA scoring algorithms or registry criteria other than the
  specifically authorized correction to Criterion 7's registry score bands.
- Corridor/CPA-106 interviewing, new assessment/case persistence, multiple
  AOIs, a generated CDL GeoJSON map layer, or a new front-end dependency.
- A CDL proxy endpoint. If the fixed ImageServer overlay is blocked by browser
  CORS, stop and request approval before adding a proxy.
- Deployed application testing or live-service acceptance beyond the
  repository’s separately run live-network tests.

**Verbatim constraints from the user:**

- “i want a workflow integrated, and likely nice UI integration for agent chat
  map app, for asking user questions to qualitatively/semiquantitatively rank
  site assessment components in LESA score.”
- “i want to note that i want "ask user question" style interface integrated
  into the chat.”
- “cropland data layer is not an authoritative source for anything in FPPA
  specifically, it is simply an index of the crop types and land covers.”
- “i suppose it is not "direct contact" but nobody estimates direct contact
  from an indirect source so the point is moot, we just need enough pixels to
  be able to make a reasonable call. we are assuming that the land cover/use
  does not vary significantly at the scale below about 300m in terms of bulk
  composition”

## Reconnaissance Log (2026-11-12)

- Repository: `D:\workspace\fpac-soil-mcp`, branch
  `feature/sa-checklist1`, HEAD `d8a78df`. The worktree contains the approved
  `planning/GOALS.md` update only. Planning files are tracked by default and
  are not ignored. The highest existing orchestration is 47.
- Repository rules: root `AGENTS.md` requires fixed-input query boundaries,
  explicit provenance/status, and the preliminary authority notice. App
  `AGENTS.md` requires chat/map changes to preserve the AOI session-context
  contract, use fixed overlay URL constants, update ADR 0015’s local-change
  list, and run app checks.
- Relevant accepted decisions: ADR 0003 (preliminary authority), ADR 0004
  (EPSG:6933 for buffering and WGS84 geodesic area), ADR 0012 (separate MCP
  client; no app wrapper tools for resources/prompts), ADR 0015 (owned
  frontend changes must be listed), ADR 0016 (one AOI in browser chat-session
  context), ADR 0017 (map results are additive; context overlays are distinct
  from analysis results).
- Existing contracts: `analyze_cdl_histogram` handles one polygon and
  requires an explicit vintage and qualifying-class list. The client already
  validates catalog vintages and returns class histograms, but there is no
  combined AOI/ring workflow or latest-vintage selector. Keep the existing
  tool backward-compatible.
- Existing Site Assessment support: the validated
  `fppa://site-assessment-criteria` resource defines all 12 criteria and
  scoring rules; `fppa_site_assessment_assistant` points clients to it; the
  LESA tool accepts fact-based inputs and reports criterion-level results.
  `McpServer.read_resource(uri)` is available to the app, so the registry can
  be consumed without adding a model-callable wrapper tool.
- Existing map support: `overlays.ts` is a fixed-URL raster catalog;
  `OverlayControl` presents off-by-default context layers. Map tool results
  currently route through `/api/geo/map`, while the app’s
  `MapResultContext`/`ShowOnMapButton` can be extended for a non-GeoJSON CDL
  summary without changing server map geometry.
- Related planning: Plan 45 already delivered the question/scoring registry
  and deferred agricultural adjacency. This plan adds only the user-requested
  non-authoritative CDL context; it does not claim that the deferred
  authoritative Criterion 2 source has been delivered.
- Key file sizes: `cdl_client.py` 432 lines; `cdl_models.py` 152;
  `tools/cdl_tools.py` 153; `lesa.py` 1,011; `tools/lesa_tools.py` 523;
  app `agent_server/geo.py` 443; frontend `MapPanel.tsx` 720 and
  `useScreening.ts` 118. Use grep anchors, not whole-file reads, for large
  files.
- Baseline:
  - `uv run --group dev pytest tests/test_cdl_models.py
    tests/test_cdl_client.py tests/test_cdl_tools.py tests/test_lesa.py
    tests/test_site_assessment_contract.py -q` — 109 passed.
  - `uv run --group dev pytest tests/test_site_assessment_resource.py
    tests/test_prompts.py -q` — 9 passed.
  - App offline tests — 177 passed; app Ruff check and format check — passed.
    `make app-check` itself failed because the installed Windows `make`
    executable exits with an Rtools path error; the equivalent `uv run`
    commands passed.
  - Frontend `npm ci`, read-only Biome lint, and `npm run build` — passed.
    Existing lint warnings and 10 `npm audit` findings (4 low, 6 moderate)
    were reported; do not address unrelated baseline findings.
  - Full `make check`, live-network tests, and deployed app tests were not run.
- **Required prerequisite:** `uv run python scripts\fetch_ecfr.py --check`
  reports Parts 657/658 XML differs from the checked-in manifest. Refresh the
  generated copies and verify the Site Assessment registry before the
  interview/scoring work proceeds. Never hand-edit generated eCFR files.
- **Hazard:** direct browser CORS support for the CDL ImageServer overlay is
  not established in this repository. Probe locally; if blocked, stop rather
  than adding a proxy without approval.

## Decision Log

1. **D1 — 2026-11-12 — interview:** Use a conversational chat interview,
   one criterion at a time, for all 12 AD-1006 Site Assessment criteria.
2. **D2 — 2026-11-12 — answers and scoring:** Allow unknown/skip and partial
   inputs. Summarize all answers for user correction and explicit confirmation
   before submitting to the existing preliminary LESA calculator. Do not
   change its scoring rules in this plan.
3. **D3 — 2026-11-12 — state:** Keep answers and review in the existing chat
   conversation; do not create a separate case record.
4. **D4 — 2026-11-12 — CDL trigger and vintage:** At guided assessment start,
   automatically analyze CDL if an AOI is attached. Use the latest verified
   vintage for all requested zones and disclose it.
5. **D5 — 2026-11-12 — CDL summaries:** Return full per-class distributions
   for the AOI, one-mile exterior ring, and fixed 30 m exterior band. Do not
   show an aggregate crop/agricultural percentage by default.
6. **D6 — 2026-11-12 — Criterion 2 semantics:** CDL is context only; it does
   not prefill the user’s Criterion 2 perimeter percentage or award points.
   The 30 m band is a near-perimeter proxy, not literal direct contact.
7. **D7 — 2026-11-12 — map:** Use a toggleable raster context layer and a
   “Show CDL on map” action for the three summaries. Use fixed URLs. If browser
   CORS blocks direct access, stop and ask before adding a proxy.
8. **D8 — 2026-11-12 — order and execution:** Verify/refetch eCFR and implement
   the combined CDL tool before chat and UI integration. The conversational
   interview is the first user-facing emphasis. Maximum concurrency is two;
   use worktree isolation for parallel tasks in this repository. Planning
   artifacts are tracked. Acceptance is offline checks plus a local browser
   walkthrough; no deployed dev-app trial.
9. **D9 — 2026-11-12 — eCFR blocker:** The current eCFR check is stale. Refresh
   the generated copies and compare the registry before guided scoring. If
   the refreshed text reveals a scoring conflict, stop and request a
   domain-owner decision; do not modify scoring rules under this plan.

## Task DAG and Wave Table

| Wave | Task | Summary | Depends on |
|---|---|---|---|
| 1 | 51.1.1 | Refresh eCFR references and align Criterion 7 registry bands | none |
| 1 | 51.1.2 | Add the combined AOI / one-mile ring / 30 m CDL context tool | none |
| 1 | 51.1.3 | Synchronize Wave 1 tool and Criterion 7 contracts | 51.1.1, 51.1.2 |
| 1 gate | - | eCFR and CDL contract gate | 51.1.1, 51.1.2, 51.1.3 |
| 2 | 51.2.1 | Add resource-backed guided chat interview and confirmed LESA handoff | 51.1.1, 51.1.2, 51.1.3, Wave 1 gate |
| 2 | 51.2.2 | Add CDL raster context overlay and “Show CDL on map” summaries | 51.1.2, Wave 1 gate |
| 2 | 51.2.3 | Synchronize AOI handler test mocks with criteria resource reads | 51.2.1 |
| 2 gate | - | Chat/map integration gate | 51.2.1, 51.2.2, 51.2.3 |
| 3 gate | - | Serial offline/live-when-required checks and local browser walkthrough | Wave 2 gate |

### 51.1.1 — Refresh eCFR references and align Criterion 7 registry bands

- **Repo:** `D:\workspace\fpac-soil-mcp`
- **Must edit:** generated files under `docs\cfr\` only if refreshed content
  differs: `title-7-part-657.xml`, `title-7-part-657.md`,
  `title-7-part-658.xml`, `title-7-part-658.md`, `manifest.json`;
  `src\fpac_soil_mcp\data\site_assessment.v1.json`;
  focused tests in `tests\test_site_assessment_contract.py` and, if needed,
  `tests\test_site_assessment_resource.py`; append the task report to
  `planning\STATE_51.md`.
- **Can create:** `planning\tasks\51.1.1.todo.md`.
- **Depends on:** none.
- **Specification:** Refresh the checked-in eCFR files using
  `scripts\fetch_ecfr.py`, then rerun the check. Compare the current
  `site_assessment.v1.json` question and scoring contract against the refreshed
  7 CFR § 658.5(b) text. The refresh identified a Criterion 7 band mismatch,
  and the domain owner explicitly authorized correcting that registry entry.
  Use the 5-percentage-point deduction rule: 0 points at 50% or less of the
  county average; 1 point above 50% through 55%; then one additional point
  for each successive 5-point band through 9 points above 90% through 95%;
  10 points above 95%, including at or above the average. Encode boundaries
  without gaps or overlaps and test each threshold. Do not change any other
  registry entry or scoring algorithm. Compare all remaining criteria and
  record any additional mismatch; an additional mismatch blocks 51.2.1 pending
  a separate explicit decision.
- **Do not touch:** LESA scoring algorithms, registry entries other than
  Criterion 7, prompts, app code, or non-generated CFR documentation.
- **Grep anchors:** `scripts\fetch_ecfr.py`; `docs\cfr\manifest.json`;
  `src\fpac_soil_mcp\data\site_assessment.v1.json`.
- **Reference implementation:** `planning\EXECUTION_PLAN_45.md` D9 and
  repository eCFR generation/check workflow.
- **Acceptance:** `uv run python scripts\fetch_ecfr.py --check` passes after
  refresh; `uv run pytest tests\test_site_assessment_contract.py
  tests\test_site_assessment_resource.py -q` passes; registry/CFR comparison
  and Criterion 7 threshold tests are recorded in the task report. If any
  additional content conflicts, report the block rather than changing scope.

### 51.1.2 — Add combined CDL context analysis

- **Repo:** `D:\workspace\fpac-soil-mcp`
- **Must edit:** `src\fpac_soil_mcp\geometry.py`,
  `src\fpac_soil_mcp\cdl_client.py`, `src\fpac_soil_mcp\cdl_models.py`,
  `src\fpac_soil_mcp\tools\cdl_tools.py`,
  `src\fpac_soil_mcp\tools\__init__.py`, `README.md`, `manifest.yaml`,
  `server.json`, and focused tests in `tests\test_geometry.py`,
  `tests\test_cdl_client.py`, `tests\test_cdl_models.py`,
  `tests\test_cdl_tools.py` (or a new `tests\test_cdl_context.py`); append the
  task report to `planning\STATE_51.md`.
- **Can create:** `planning\tasks\51.1.2.todo.md` and the optional focused
  test file named above.
- **Depends on:** none.
- **Specification:** Add one registered MCP tool that accepts one validated
  Polygon/MultiPolygon AOI and returns full CDL class distributions for the
  AOI, the one-mile buffer minus AOI, and the 30 m buffer minus AOI. Construct
  distance buffers in EPSG:6933 per ADR 0004, subtract the exact AOI, and
  transform valid result geometry for the CDL service. Select the latest
  catalog vintage only when uniquely verified; use that same vintage for all
  zones. Return source, vintage, coverage, status, and provenance per result.
  Preserve every raw class code/name and counts/shares; do not invent a
  qualifying-class policy, binary agricultural percentage, or Criterion 2
  perimeter percentage. Keep `analyze_cdl_histogram`’s existing contract
  compatible. Surface partial, invalid, ambiguous, and upstream-error states
  explicitly.
- **Do not touch:** LESA scoring, criterion registry, TIGERweb evidence,
  agent app, or map renderer.
- **Grep anchors:** `geometry.py` `buffer_centerline`,
  `calculate_acreage`; `cdl_client.py` `resolve_product_vintage`,
  `analyze_polygon_histogram`; `cdl_tools.py` `analyze_cdl_histogram`;
  `tools\__init__.py` `analyze_cdl_histogram`.
- **Reference implementations:** `analyze_cdl_histogram` and
  `CDLClient.analyze_polygon_histogram`; geometry projection/buffering contract
  in ADR 0004; existing fixed-tool registration in `tools\__init__.py`.
- **Acceptance:** focused mocked tests cover geometry subtraction,
  latest-vintage ambiguity/unavailability, same-vintage use across all three
  zones, per-class preservation, coverage/error states, and no default
  qualifying percentage. Run
  `uv run pytest tests\test_geometry.py tests\test_cdl_client.py
  tests\test_cdl_models.py tests\test_cdl_tools.py -q`, then
  `uv run ruff check .` and `uv run ruff format --check .`. Update all public
  MCP surface references listed above.

### 51.1.3 — Synchronize Wave 1 tool and Criterion 7 contracts

- **Repo:** `D:\workspace\fpac-soil-mcp`
- **Must edit:** `src\fpac_soil_mcp\tools\__init__.py`, `README.md`,
  `manifest.yaml`, `server.json`, `tests\test_phase2_contracts.py`,
  `tests\test_server.py`, `tests\test_lesa.py`,
  `tests\test_corridor_scoring.py`, `eval\contract\test_contract.py`,
  `eval\databricks\test_databricks_agent.py`; append the task report to
  `planning\STATE_51.md`.
- **Can create:** `planning\tasks\51.1.3.todo.md`.
- **Depends on:** 51.1.1 and 51.1.2.
- **Specification:** Resolve the Wave 1 failures found by the serial `make
  check`. Keep the `analyze_cdl_context` description identical in the runtime
  registration, README, manifest, and server metadata; start it with an
  action-oriented verb accepted by the contract test. Update tool-count and
  expected-name assertions to include the new public tool, without weakening
  exact-set or metadata-consistency checks. Update Criterion 7 description
  assertions to reflect the corrected registry band label while preserving
  score and threshold assertions.
- **Do not touch:** CDL analysis behavior, Criterion 7 score bands, LESA
  scoring algorithms, prompts, app code, or unrelated evaluation cases.
- **Grep anchors:** `tools\__init__.py` `analyze_cdl_context`;
  `test_server.py` `EXPECTED_TOOLS` and published metadata checks;
  `eval\contract\test_contract.py` expected tool set and counts;
  `eval\databricks\test_databricks_agent.py` tool count;
  Criterion 7 description assertions in the named scoring tests.
- **Reference implementations:** existing runtime/published tool metadata
  equality checks in `tests\test_server.py`; exact tool-set tests in
  `eval\contract\test_contract.py`.
- **Acceptance:** the focused tests below pass and preserve exact runtime,
  manifest, and `server.json` tool-set/description agreement:
  `uv run pytest tests\test_phase2_contracts.py tests\test_server.py
  tests\test_lesa.py tests\test_corridor_scoring.py
  eval\contract\test_contract.py eval\databricks\test_databricks_agent.py -q`.
  `uv run ruff check .` and `uv run ruff format --check .` pass.

### 51.2.1 — Add resource-backed conversational Site Assessment flow

- **Repo:** `D:\workspace\fpac-soil-mcp`
- **Must edit:** `src\fpac_soil_mcp\prompts\fppa_prompts.py`,
  `tests\test_prompts.py`,
  `apps\agent-fpac-soil-openai-sdk\agent_server\agent.py`,
  `apps\agent-fpac-soil-openai-sdk\agent_server\prompts\system_prompt.txt`,
  and focused app tests in
  `apps\agent-fpac-soil-openai-sdk\tests\test_agent_mcp_wiring.py` and/or
  `test_agent_config.py`; append the task report to `planning\STATE_51.md`.
- **Can create:** `planning\tasks\51.2.1.todo.md` and focused tests in the
  listed test files.
- **Depends on:** 51.1.1, 51.1.2, 51.1.3, and the Wave 1 gate.
- **Specification:** Use the existing `fppa://site-assessment-criteria`
  resource as the single source for the 12 site questions and scoring bands.
  Read it in the agent server and provide it as agent context; do not expose a
  wrapper resource/prompt tool or duplicate the registry in a second scoring
  table. For a guided AD-1006 interview, ask one criterion at a time, accept
  qualitative/semi-quantitative responses and rationale, preserve unknown or
  skipped answers, and automatically request the combined CDL context once
  when the user has an attached AOI. Show the complete answer/evidence summary
  and require explicit user confirmation before submitting supported facts to
  the existing preliminary LESA calculation. Keep CDL context separate from
  Criterion 2 input; never use CDL to fill or score that percentage. Keep
  assessment state in the conversation, preserve existing no-invented-values,
  preliminary-authority, and no-siting rules, and report incomplete/
  unavailable results without zero-filling.
- **Do not touch:** Site Assessment scoring rules, `site_assessment.v1.json`,
  corridor workflow, assessment persistence, frontend files, or deployment
  configuration. The Criterion 7 mismatch found by 51.1.1 was resolved under
  the explicit owner authorization; any additional mismatch remains blocked
  pending a separate decision.
- **Grep anchors:** `agent.py` `create_agent`, `_connect_fpac_agent`;
  `system_prompt.txt` `Required semantic rules`;
  `fppa_prompts.py` `fppa_site_assessment_assistant_prompt`;
  `resources\fppa_resources.py` `fppa://site-assessment-criteria`.
- **Reference implementations:** `SITE_ASSESSMENT_REGISTRY` resource and
  current `fppa_site_assessment_assistant` prompt; app MCP connection and
  AOI-context flow in `agent.py` / `aoi_context.py`.
- **Acceptance:** tests prove the validated resource reaches agent context,
  the prompts preserve existing policy, unknown values remain unavailable,
  and no score submission occurs before answer confirmation. Run
  `uv run pytest tests\test_prompts.py tests\test_site_assessment_resource.py
  -q`; from the app directory run
  `uv run --frozen --python 3.11 pytest
  tests\test_agent_mcp_wiring.py tests\test_agent_config.py -q`, plus app
  Ruff check/format check on owned files.

### 51.2.2 — Add CDL map overlay and summary display

- **Repo:** `D:\workspace\fpac-soil-mcp`
- **Must edit:** `apps\agent-fpac-soil-openai-sdk\frontend\client\src\components\map\overlays.ts`,
  `OverlayControl.tsx`, `MapPanel.tsx`, `MapResultContext.tsx`,
  `ShowOnMapButton.tsx`, `apps\agent-fpac-soil-openai-sdk\frontend\client\src\components\message.tsx`,
  `apps\agent-fpac-soil-openai-sdk\AGENTS.md`, and
  `docs\decisions\0015-vendored-agent-app-frontend.md`; append the task report
  to `planning\STATE_51.md`.
- **Can create:** `planning\tasks\51.2.2.todo.md` and a focused
  `components\map\` summary component.
- **Depends on:** 51.1.2 and the Wave 1 gate.
- **Specification:** Add the CDL ImageServer as a fixed, off-by-default
  raster context overlay with attribution and vintage/context labeling. Add a
  “Show CDL on map” action for the combined tool result; it opens the map and
  displays the AOI, one-mile ring, and 30 m band class distributions using
  server-returned values only. Keep the full class distribution available in
  the summary without mislabeling class shares as official farmland or
  perimeter-contact scores. Keep class/source/vintage/coverage and
  preliminary-use limitations visible. Use the existing React map-result
  context; do not add a new route or re-query analysis solely to show its
  summary. If browser CORS blocks the fixed service URL, stop and report; do
  not add a proxy.
- **Do not touch:** MCP server contracts, scoring, chat/session persistence,
  user-controlled overlay URLs, package manifests/lockfiles, or other
  overlays.
- **Grep anchors:** `overlays.ts` `OVERLAYS`, `addOverlay`;
  `OverlayControl.tsx` `OVERLAYS.map`;
  `MapPanel.tsx` `overlayOn`, `toggleOverlay`;
  `MapResultContext.tsx` `ShownMapResult`;
  `ShowOnMapButton.tsx` `MAP_TOOLS`;
  `message.tsx` `ShowOnMapButton`.
- **Reference implementations:** existing fixed SSURGO/TIGERweb context
  overlays and the current tool-card “Show on map” flow.
- **Acceptance:** frontend lint/build succeeds; the local browser walkthrough
  verifies the toggleable CDL raster, attribution/status, tool-card action,
  and all three summaries. Use
  `Set-Location apps\agent-fpac-soil-openai-sdk\frontend; npm ci; npx biome
  lint --skip=nursery/useSortedClasses --skip=style/useTemplate .; npm run
  build`. Do not run upstream write-mode lint scripts. Update ADR 0015’s
  local-change list and app `AGENTS.md` in the same task.

### 51.2.3 — Synchronize AOI handler test mocks with criteria resource reads

- **Repo:** `D:\workspace\fpac-soil-mcp`
- **Must edit:**
  `apps\agent-fpac-soil-openai-sdk\tests\conftest.py`,
  `apps\agent-fpac-soil-openai-sdk\tests\test_aoi_context.py`, and
  `apps\agent-fpac-soil-openai-sdk\tests\test_aoi_handoff.py`.
- **Can create:** `planning\tasks\51.2.3.todo.md`.
- **Depends on:** 51.2.1.
- **Specification:** Task 51.2.1 added an asynchronous
  `fppa://site-assessment-criteria` resource read whenever the MCP connection
  is healthy. The full app suite found existing AOI handler mocks that do not
  provide this resource result. Add a reusable valid resource fixture, wire the
  affected mock servers to return it asynchronously, and update any
  `create_agent` call expectations for the validated context. Preserve the
  AOI, tool-call binding, coordinate-redaction, model-input, and trace-session
  assertions; do not change production code or weaken the tests.
- **Do not touch:** app runtime code, MCP server contracts, other tests,
  frontend files, or deployment configuration.
- **Acceptance:** from the app directory, run
  `uv run --frozen --python 3.11 pytest tests\test_aoi_context.py
  tests\test_aoi_handoff.py -q`, then the full
  `uv run --frozen --python 3.11 pytest tests -q`; run Ruff check and format
  check on `tests\conftest.py`, `tests\test_aoi_context.py`, and
  `tests\test_aoi_handoff.py`.

## Final Acceptance Gate

Run serially after Wave 2:

- Root offline suite and lint/format: `make check` (on this Windows host,
  equivalent `uv run` checks may be needed because installed `make` is
  currently broken).
- Agent-app Python checks: `make app-check` or its direct `uv run` test and
  Ruff equivalents.
- Frontend: the read-only Biome lint and build command in 51.2.2.
- Live integration: run `uv run --group dev pytest -m live_network`
  separately if external network access is available, as required for changed
  upstream integration behavior. This is not a deployed app test.
- Local browser walkthrough: attached AOI; guided interview starts; combined
  CDL analysis uses one verified vintage; missing CDL data remains explicit;
  summary requires user confirmation; final preliminary result is shown; the
  CDL map action renders all three summaries and the toggleable raster.

## Handoff

Plan files are to be tracked in Git, with the approved planning-only update
committed separately from implementation. Do not push or perform any other
remote Git action without explicit instruction. Execution is not authorized by
this plan until the user approves it.
