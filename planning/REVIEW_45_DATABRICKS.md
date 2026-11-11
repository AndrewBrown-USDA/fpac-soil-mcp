# Review 45 — Databricks Environment and Real-Data Review

Reviewed 2026-11-10 on Databricks serverless against branch
`feature/semiquant-sa1` at `e1645ce` (merge-base with `main` `d16b6e6`).
This review adds Databricks, live-data, and model-evaluation evidence that the
local closeout could not produce. It supersedes the "No unresolved
specification or standards findings" disposition in `REVIEW_45.md`.

Scope: environment fitness, MCP discovery, representative calls, and the
authority contract as specified in `EXECUTION_PLAN_45.md` (D1-D8, Hazard
Notes). This review does not redesign the feature, does not close the Phase 4
issue, and does not make an official FPPA/NRCS determination.

Finding IDs use `DB45-nn`. Each finding carries a suggested triage tag; the
triage table is in `STATE_45.md`:

- **Fix in 45** — specific defect, fixable inside Plan 45 before the Agent
  Safety, Evaluation, and Reliability Contract work.
- **Decision** — needs a recorded plan decision before coding.
- **Contract** — candidate for the forthcoming Agent Safety, Evaluation, and
  Reliability Contract task.

## Environment and commands

- Runtime: Databricks serverless, Linux x86_64, system Python 3.12.3, uv
  0.13.4, project venv Python 3.11, fastmcp 4.1.6.
- All runs used a throwaway clone of `e1645ce`; no source file was changed.

| Command | Result |
|---|---|
| `uv sync --frozen` | Editable install of the checked-out `src` tree (`direct_url.json` editable, module file under `src\`) |
| `uv run pytest -m "not live_network and not agent_eval"` | 738 passed, 3 skipped, 45 deselected (skips: `eval\databricks` tests, `mlflow` absent from the dev group) |
| Same, with `--group eval-databricks` | 764 passed, 0 skipped, 45 deselected |
| `uv run pytest -m live_network` | 43 passed (no live test calls `calculate_preliminary_lesa`) |
| `uv run ruff check .` | All checks passed |
| `uv run ruff format --check .` | 587 files already formatted |
| `uv build --wheel` + clean venv install, run from `/` | Wheel contains `data\site_assessment.v1.json`; registry loads through `importlib.resources`; `create_mcp_server()` succeeds |
| T1 `run_mlflow_eval.py --all --max-workers 4` | MLflow run `da4613f3256e4ddf9e474e196b480608` (results below) |
| Ad hoc SA-MA prompts through the T1 agent | MLflow run `127a5e18cab443559f15300acb815cb8` |

## Confirmed (no action)

- `main.py` puts `src` first on `sys.path`; no stale-wheel risk on Databricks
  Apps.
- MCP discovery over local streamable HTTP (`main.py`, `MCP_TRANSPORT=http`,
  working directory `/`): 10 tools; 4 resources including
  `fppa://site-assessment-criteria` (12 criteria); 4 prompts including
  `fppa_site_assessment_assistant`. The `calculate_preliminary_lesa` schema
  documents `criteria_facts`, and the description says it does not issue an
  official determination.
- Analyst override without rationale returns an MCP tool error; with
  rationale it is labeled `analyst_proposed`.
- Missing subjective facts (criteria 8-12) and an unknown criterion 2 stay
  `unavailable`; Site Assessment is `incomplete`, `total_lesa_score` is `None`,
  `threshold_status` is `not_evaluated`.
- Selected property (CSR2) is preserved in `land_evaluation.productivity_index`
  and forwarded to `analyze_corridor_fppa`.
- No local-only paths, working-directory assumptions, credentials, or new
  optional dependencies in the branch diff. New tests make no network calls;
  `agent_eval` and `live_network` stay opt-in.
- No test coordinate appeared in tool responses, captured logs, or stderr across
  live calls. "Recommend" appears only in the disclaimer "does not authorize or
  recommend a site".
- NASS is disabled (no key configured), so no NASS call was exercised.

## Regulatory reference used

7 CFR 658.5 text retrieved from the eCFR renderer API on 2026-11-10
(`/api/renderer/v1/content/enhanced/current/title-7?part=658&section=658.5`).
The same text is now stored in `docs\cfr\title-7-part-658.md` (eCFR current as
of 2026-11-06, latest amendment 2016-11-23; XML hash in `docs\cfr\manifest.json`).
Use that copy when fixing DB45-01, DB45-03, and DB45-11. The comparison below is
against that text.

| Criterion | 7 CFR 658.5(b) | `site_assessment.v1.json` | Assessment |
|---|---|---|---|
| 1 Nonurban land within 1 mile | >90% = 15; 90-20% = 14-1; <20% = 0 | 0-25% = 0; 26-75% = 8; 76-100% = 15 | Boundaries differ from the fixed CFR end points |
| 2 Perimeter in nonurban use | >90% = 10; 90-20% = 9-1; <20% = 0 | only `unavailable`; question says "farmable land" | See DB45-05; wording differs from CFR "nonurban use" |
| 3 Farmed 5 of last 10 years | >90% = 20; 90-20% = 19-1; <20% = 0 | 0-25% = 0; 26-75% = 10; 76-100% = 20 | Boundaries differ |
| 4 Protection programs | protected = 20; not protected = 0 | 0% = 0; 1-50% = 10; 51-100% = 20 | CFR is binary; partial band not in CFR |
| 5 Distance to urban built-up area | >=2 mi = 15; >1 to <2 mi = 10; <1 mi not adjacent = 5; adjacent = 0 | 0-1 mi = 15; >1-5 mi = 8; >5 mi = 0 | **Inverted** |
| 6 Water/sewer/other services | none within 3 mi = 15; some >1 to <3 mi = 10; all within 1/2 mi = 0 | 0-1 mi = 15; >1-5 mi = 8; >5 mi = 0 | **Inverted**; CFR is a multi-service question, registry is one distance |
| 7 Farm unit vs county average | as large or larger = 10; deduct 1 per 5% below; 0 if 50% or more below | 0-50% = 10; >50-100% = 5; >100% = 0 | **Inverted** |
| 8 Remaining land made non-farmable | >25% of converted acres = 10; 25-5% = 9-1; <5% = 0 | none 0; minor 5; substantial 10 | CFR is quantitative; registry is qualitative |
| 9 Farm support services available | all = 5; some = 4-1; none = 0 | limited = 5; somewhat = 3; readily = 0 | **Inverted** |
| 10 On-farm investment | high = 20; moderate = 19-1; none = 0 | minimal 0; moderate 10; substantial 20 | Direction matches |
| 11 Reduced demand for support services | substantial = 10; some = 9-1; none = 0 | little 0; moderate 5; substantial 10 | Direction matches |
| 12 Incompatibility with agriculture | incompatible = 10; tolerable = 9-1; fully compatible = 0 | compatible 0; moderate 5; incompatible 10 | Direction matches |

658.5(c) for corridor-type sites: criteria 5 and 6 are not considered;
criteria 8 and 11 are scored 0-25.

Where the CFR gives a range (for example "14 to 1 point(s)"), choosing a single
representative point is an agency scoring convention under D2. That is a
legitimate design choice, but the registry should label it as a convention and
not as the CFR rule.

## Findings

### High

**DB45-01 — Registry point mappings contradict 7 CFR 658.5(b). (Fix in 45 +
Decision)**
- Evidence: the table above. Criteria 5, 6, 7, and 9 are inverted. Live call
  with `distance_miles: 6` for criterion 5 awarded 0 points; the CFR gives 15
  for 2 miles or more. Fact `percentage: 40` for criterion 7 awarded 10; the
  CFR gives 0 (60% below average).
- Location: `src\fpac_soil_mcp\data\site_assessment.v1.json` lines 6-17.
- Plan conflict: Hazard Notes ("must not encode unsupported regulatory
  assumptions as authoritative facts") and 45.1.1 acceptance ("all mappings
  stay within statutory bounds").
- Test gap: `tests\test_site_assessment_contract.py` checks bounds, overlaps,
  duplicates, and citations, but never checks direction or end points against
  the CFR.
- Fix direction: correct the bands to the CFR end points and direction; mark
  representative points inside CFR ranges as a versioned convention; add a
  fixture-driven test per criterion that pins the CFR top, intermediate, and
  bottom conditions. Decide how to represent criterion 4 (binary), criterion 6
  (multi-service), and criterion 8 (quantitative).

**DB45-02 — Zero-coverage Land Evaluation is scored as 0 and the threshold is
evaluated. (Fix in 45)**
- Evidence (live SDA): Storie index on an Iowa polygon returned
  `rated_acreage` 0.0, `coverage_percent` 0.0, `candidate_le_score` 0.0, and
  with a complete Site Assessment `total_lesa_score` 83.0,
  `threshold_status` `evaluated`, `mandatory_alternatives_required` `False`.
  The same call on `main` `d16b6e6` also returns LE 0.0, so it predates the
  branch, but it contradicts D5 and the "unavailable is not zero" rule.
- Location: `src\fpac_soil_mcp\polygon_analysis.py` line 373 (clamped
  `candidate_le`); `src\fpac_soil_mcp\lesa.py` line 906 checks only `None`;
  `tests\test_polygon_analysis.py` line 299 asserts `candidate_le_score == 0.0`
  for the all-sentinel case.
- Fix direction: when rated acreage is 0, return `candidate_le_score: None`
  (or the repository's typed unavailable state) so `evaluate_lesa` takes the
  indeterminate branch; update the sentinel test.

### Medium

**DB45-03 — Corridor projects score criteria 8 and 11 on the site scale.
(Fix in 45)**
- Evidence (mocked corridor, `project_type: corridor`): fact `substantial` for
  criteria 8 and 11 awarded 10 of a 25-point maximum. The registry defines
  only site maxima (10), while `lesa.py` uses corridor maxima (25) under
  658.5(c)(2).
- Location: `src\fpac_soil_mcp\data\site_assessment.v1.json` lines 13 and 16;
  `src\fpac_soil_mcp\tools\lesa_tools.py` `_score_registry_facts` (line 28),
  which ignores `project_type`.
- Fix direction: add corridor variants (or a per-project-type maximum) to the
  registry and select by `project_type`.

**DB45-04 — Statutorily zeroed corridor criteria are relabeled
`machine_estimate`. (Fix in 45)**
- Evidence: corridor criteria 5 and 6 come back `is_statutorily_zeroed: True`
  and 0/0 points, but `input_authority: machine_estimate` when a fact was
  supplied.
- Location: `src\fpac_soil_mcp\tools\lesa_tools.py` lines 248-280 (post-pass
  overwrites `input_authority`, `is_automated`, `is_verified`).
- Fix direction: skip the post-pass for zeroed criteria, and ignore or reject
  facts for criteria that 658.5(c)(1) excludes.

**DB45-05 — Criterion 2 can never be scored from facts. (Decision)**
- Evidence (live): facts for all 12 criteria, including `percentage: 80` for
  criterion 2, stay `incomplete`; `complete` is reachable only with an
  analyst-proposed criterion 2 score.
- D1 defers the adjacency *data stream*. It is not clear whether D1 also meant
  to refuse a user-supplied perimeter percentage, which the CFR does band
  (>90% = 10, <20% = 0).
- Decision needed: accept a user-supplied criterion 2 fact with verification
  state, or record that criterion 2 is analyst-only. The registry question
  should use the CFR wording "nonurban use".

**DB45-06 — A registry fact silently overrides an analyst override for the
same criterion. (Fix in 45)**
- Evidence: `criteria_facts` and `criteria_inputs` for criterion 8 together
  produced the fact value (5, `machine_estimate`); the analyst value (10) and
  its rationale were dropped without notice.
- Location: `src\fpac_soil_mcp\tools\lesa_tools.py` line 219
  (`criteria_inputs.update(scored_registry_facts)`; string and integer keys
  coexist, and `lesa.py` line 743 normalizes them so the later key wins).
- Plan conflict: Hazard Notes ("Do not silently reinterpret analyst
  overrides").
- Fix direction: reject the conflict, or apply a documented precedence and
  emit a limitation naming the dropped input.

**DB45-07 — Out-of-range analyst points are silently clamped. (Fix in 45 +
Contract)**
- Evidence (T1 LESA-01): the user supplied a 120-point Site Assessment total;
  the agent sent `criteria_inputs: {"1": {"awarded_points": 120, ...}}` with a
  generated rationale; the tool recorded 15 points without warning.
- Location: `src\fpac_soil_mcp\lesa.py` lines 557, 631, 670
  (`max(0.0, min(max_points, ...))`).
- Fix direction (tool side): reject points above the criterion maximum or
  below 0, or flag them in limitations. The agent-side behavior (mapping a total
  onto one criterion) belongs to the Contract work.

**DB45-08 — Registry `requires_rationale` and `requires_verification` are not
enforced on the fact path; user-supplied facts are labeled
`machine_estimate`. (Decision)**
- Evidence: facts for criteria 4 and 8-12 (all `requires_rationale: true`)
  score without a rationale and come back `machine_estimate`.
- Location: `src\fpac_soil_mcp\tools\lesa_tools.py` `_score_registry_facts`
  (line 28) and the post-pass (line 270); the flags are read nowhere in the
  tool.
- Decision needed: whether a user-supplied fact is a distinct authority state
  (for example `user_provided`) and whether missing rationale makes a
  rationale-required criterion `unavailable` or flagged.

**DB45-09 — Corridor Land Evaluation reports 0% coverage with a nonzero
score. (Fix in 45)**
- Evidence (live SDA): CSR2 corridor LE 39.5 and NCCPI corridor LE 73.5, both
  with `rated_acreage` 0.0, `coverage_percent` 0.0, and empty notices.
- Location: `src\fpac_soil_mcp\tools\lesa_tools.py` lines 169-176 build
  `LandEvaluationSummary` from the score and acreage only.
- Fix direction: carry rated/unrated acreage, coverage, and provenance from
  the corridor result into the summary.

**DB45-10 — `evaluate_site_assessment(None, ...)` with both farm sizes returns
`complete` while 11 criteria are unavailable. (Fix in 45)**
- Evidence: direct call, `evaluation_status: complete`, 11 criteria
  `unavailable`. Not reachable through the MCP tool, which always passes a
  dict.
- Location: `src\fpac_soil_mcp\lesa.py` line 763.
- Fix direction: drop the first branch; derive status only from the criteria.

**DB45-11 — Legacy criterion 7 evaluator does not follow the CFR schedule.
(Decision)**
- Evidence: `lesa.py` lines 464-475 award 10 / 5 / 0 at 100% / 50% / below.
  The CFR deducts 1 point per 5% below average. Live call with 180 vs 320
  acres (43.75% below) awarded 5; the CFR schedule gives about 2. This
  predates the branch; 45.1.2 asked to keep criterion 7 compatible with
  existing behavior.
- Decision needed: whether DB45-01 also corrects criterion 7 factual scoring.
  The farm-size path and the registry path must agree after the fix.

### Low

**DB45-12 — `land_evaluation.coverage_status` is always `unknown`, and coverage
vocabularies differ. (Fix in 45)**
- Evidence: `unknown` on every live polygon and corridor LESA call, including
  calls with a partial-coverage notice.
- Vocabularies: `sda_client.py` (`rated`, `partial`, `unrated`, `no_coverage`,
  `not_found`); `polygon_analysis.py` and `corridor_analysis.py` (`covered`,
  `partially_covered`, `unmapped`); `models.py` line 462 description (`covered`,
  `partial`, `unrated`, `unmapped`, `unknown`).
- Fix direction: populate the field on both paths and use one vocabulary.

**DB45-13 — Values between bands become unavailable without explanation.
(Fix in 45)**
- Evidence: `percentage: 25.5` for criterion 1 returned `unavailable` with the
  generic "unknown or unavailable" justification. Lower bounds such as
  `1.000001` create similar gaps. Partly moot if DB45-01 rebuilds the bands.
- Fix direction: contiguous half-open bands, and a distinct message for an
  out-of-band value versus an unknown answer.

**DB45-14 — Rating-source provenance does not reach LESA notices. (Fix in 45)**
- Evidence (live): polygon and corridor LESA notices carry
  `productivity_index` but no rating-source string. `lesa.py` around line 391
  adds the provenance notice only for dict items, not model items.

**DB45-15 — A LINESTRING with the default `project_type: site` uses corridor
Land Evaluation with site Site Assessment rules. (Decision; unverified on
main)**
- Evidence: live CSR2/NCCPI corridor calls returned `project_type: site` with
  site maxima for criteria 5, 6, 8, and 11.

## Evaluation findings

T1 run `da4613f3256e4ddf9e474e196b480608` (20 cases, agent
`databricks-gpt-5-6-luna`, judge `databricks-claude-sonnet-4-5`):

| Scorer | Pass | Fail | Null |
|---|---|---|---|
| required_tools_called | 14 | 1 | 5 |
| keywords_present | 20 | 0 | 0 |
| numeric_within_tolerance | 1 | 0 | 19 |
| tool_arguments_within_tolerance | 4 | 0 | 16 |
| correctness | 5 | 0 | 15 |
| fppa_compliance | 16 | 4 | 0 |
| expectations_guidelines | 5 | 0 | 15 |
| tool_call_correctness | 16 | 4 | 0 |
| safety | 20 | 0 | 0 |
| tool_call_efficiency | 15 | 5 | 0 |

Failing cases: LESA-01 (fppa_compliance), LESA-02 (efficiency, correctness,
fppa_compliance), PROMPT-02 (efficiency, correctness, fppa_compliance),
PROMPT-03 (did not call `check_urban_area_exemption`), URBAN-01
(fppa_compliance, efficiency), POLY-01 (efficiency), POLY-02 (correctness).

**DB45-E1 — SA-MA cases cannot run on Databricks. (Contract)**
`eval\eval_cases.v1.json` (SA-MA-01..04) is read only by
`eval\fpac_soil_mcp_harness\lib\evalCases.js`. The T1 runner loads
`eval\prompt_test_cases.json` (`eval\common\dataset.py` line 17), so
`make eval-databricks` never runs the Plan 45 model-assisted cases.

**DB45-E2 — SA-MA-02 and SA-MA-04 do not exercise their target tools.
(Contract)** Neither prompt supplies a geometry. In the ad hoc run, SA-MA-02
called only `explain_fppa_screening_scope` and SA-MA-04 answered generically
about NCCPI. SA-MA-01 read `fppa://site-assessment-criteria` and asked for
unknowns; SA-MA-03 read the prompt and resources and did not choose a site. No
response fabricated subjective points or recommended a site.

**DB45-E3 — Judge noise. (Contract)** LESA-01 failed `fppa_compliance` although
the response states it is "not an official FPPA determination, LESA score, or
completed Form AD-1006". `correctness` and `expectations_guidelines` are null on
the 15 cases without `expected_facts`.

**DB45-E4 — LESA-02 tool error is the known WKT input gap.** The agent sent WKT
to `analyze_farmland_by_polygon` (`coverage_status: invalid_request`). Already
a Plan 44 follow-up; not a Plan 45 defect.

## Environment notes (document, do not mask)

- **DB45-N1:** `make eval-databricks` fails in the uv venv on serverless with
  "default auth: cannot configure default credentials"; the venv has no
  runtime credentials. It works in the serverless notebook/session Python after
  `pip install` of the clone plus `mlflow>=3.12,<4` and
  `databricks-sdk[openai]>=0.122`, with `eval\databricks`, `eval`, and `src`
  first on `sys.path`. `eval\databricks\README.md` should say so.
- **DB45-N2:** `eval\pi\run_evals.py` line 23 imports `eval.common`, so it
  needs `PYTHONPATH=.` when run directly (already recorded in 45.4.2).
- **DB45-N3:** the 3 offline skips are expected without the `eval-databricks`
  group.

## Databricks-only follow-ups still open

- No app deploys this branch: `mcp-fpac-soil` and
  `agent-fpac-soil-openai-sdk` run `main` `d16b6e6`; `mcp-fpac-soil-dev` and
  `agent-fpac-soil-dev` run `feature/agent-app-map2` `d8951733`. A deployed
  discovery and call check needs a dev app pointed at this branch, a redeploy,
  and a browser check (the apps reject personal access tokens).
- NASS criterion 7 enrichment was not exercised (no key configured).

## Recommendation

Blocked for deployment trial. Ready for refinement once DB45-01 and DB45-02
are fixed, and DB45-05, DB45-08, and DB45-11 are decided. The remaining Fix in
45 items are small and local; the Contract items can move to the Agent Safety,
Evaluation, and Reliability Contract task.
