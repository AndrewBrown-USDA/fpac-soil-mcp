# EXECUTION PLAN 47: Judge-First Scoring for Natural-Language Expectations

## Goal & Scope

**Goal:** The deterministic scorers `keywords_present`, `source_disclosed`, and
`required_behaviors_present` were built for the Pi harness, which had no judge.
The Databricks T1 eval now has working MLflow judges, and these string matchers
produce failure noise rather than signal. Move natural-language intent (required
behaviors, source citation, expected content) to judges, keep deterministic
checks only where they test structure or exact values, and fix the runner bug
behind the six `None` responses so zero-budget adversarial cases are actually
evaluated.

**In scope:**

- Fix `eval/databricks/agent.py` sending `tools=None` (HTTP 400) on
  zero-budget and budget-exhausted turns.
- New deterministic `agent_completed` scorer that fails errored traces.
- Route `required_behaviors` and `source_disclosure` into per-row MLflow
  `guidelines` so `expectations_guidelines` grades them; remove the
  `required_behaviors_present` and `source_disclosed` scorers.
- Remove the matching string checks from Pi (`eval/pi/run_evals.py`) and the
  unused `requiredBehaviors` / `sourceDisclosure` predicates from the harness;
  delete the now-unused `required_behavior_missing` helper.
- Pi keyword misses become advisory (reported, not failing).
- ADV cases: `expected_keywords` -> `[]`, unique intent folded into
  `required_behaviors`.
- Author `expected_facts` for the 15 non-ADV cases that have keywords but no
  facts, then remove the Databricks `keywords_present` scorer.
- Full `--all` rerun compared against run `f2df7fe1d52a4c139df1bdde4748768f`.

**Out of scope:**

- Changing the working judges (`correctness`, `fppa_compliance`,
  `expectations_guidelines`, `tool_call_correctness`, `safety`,
  `tool_call_efficiency`) or their prompts. The 5 `fppa_compliance`, 1
  `correctness`, and 12 `tool_call_correctness` failures stay as signal.
- `prohibited_behaviors_absent`, the budget scorers, `numeric_within_tolerance`,
  `tool_arguments_within_tolerance`, `required_tools_called`,
  `required_status_matches`, `privacy_non_echo`.
- The harness keyword smoke check on non-ADV cases (it checks raw server
  output, not agent prose) and `common.matching.keywords_present` (still used by
  Pi advisory).
- Reworking the LESA-01 prompt (see Hazards) or the ADV-GEOMETRY-01 server
  defect.
- Stamping `verified_on` on new facts; live re-verification of data facts.
- An ADR. Optional `adr-distillation` after the final gate.

**Verbatim constraints:**

- "Don't break the judges that are working well."
- "`prohibited_behaviors_absent` (14/14 pass) and the budget scorers (14/14
  pass each) are correctly deterministic ... Leave them."
- "`numeric_within_tolerance` and `tool_arguments_within_tolerance` are also
  correctly deterministic. Leave them."
- "Conventional commits. Run `eval/databricks/test_databricks_scorers.py` after
  scorer changes. Ruff on a `git archive HEAD` copy in `/tmp` (workspace FS
  gives false EXE002)."
- "If removing a scorer, also remove the now-unused fields from the case
  definitions ... or mark them deprecated with a comment explaining" (resolved
  by D3/D4: fields stay with a documented new role; see 47.2.1).
- "fix the tools none bug first in the plan"

## Reconnaissance Log (2026-11-12)

- Workspace clone `/Workspace/Users/andrew.g.brown@usda.gov/fpac-soil-mcp` is
  on `fix/eval-tuning1` at `8c90f0d` (merge of PR #87, contains `80f3457`).
- File sizes: `scorers.py` 368 lines, `run_mlflow_eval.py` 206, `agent.py`
  318, `dataset.py` 369, `test_databricks_scorers.py` 270.
- **None responses (root cause, verified on all 6 traces):** state `ERROR`,
  root span `BadRequestError: 400 INVALID_PARAMETER_VALUE: Invalid type of chat
  model 'tools' parameter. Expecting List[Map[String, Any]]`. `agent.py`
  ~L261 sets `active_tools = None` and passes `tools=active_tools`. Endpoint
  probe: `tools=None` -> 400; omitting `tools` -> OK, both with and without
  prior tool-call history. The unit test
  `test_zero_call_budget_disables_tool_use_and_is_added_to_system_prompt`
  (`test_databricks_agent.py` ~L189) uses `FakeLLM`, which accepts
  `tools=None`, so it missed the bug. The mid-run exhaustion path (budget 1-2,
  8 ADV cases) has the same latent bug; no run exercised it because those ADV
  cases called no tools.
- **Crashed traces passed scorers:** on the 6 errored traces,
  `tool_call_budget`, `retry_budget`, `latency_budget`,
  `prohibited_behaviors_absent`, `tool_call_correctness` passed 6/6;
  `fppa_compliance` passed ADV-PRIVACY-01 and ADV-RELOCATE-01.
- **Judge coverage:** `correctness` and `expectations_guidelines` returned
  None on all 14 ADV rows (no `expected_facts` / `guidelines`).
  `fppa_compliance` = yes on every non-None `source_disclosed` failure. No
  judge covers source or behavior intent today.
- **Failures were phrasing:** every non-None failure of the three scorers was
  synonym or wording ("can't", "unknown/unavailable", "does not prove ...
  suitable", "SSURGO" without "USDA NRCS"). LESA-01 missed "site
  assessment" (tool rejected input; response says "Part VI criterion").
- **Consumers:** Pi `run_evals.py` ~L601-606 (required/source hard fail),
  ~L837-842 (keywords hard fail). Harness has no LLM: calls MCP directly and
  keyword-checks raw output (`server.js` ~L212, `evalCases.js` `checkKeywords`
  ~L203). Harness `requiredBehaviors` / `sourceDisclosure` predicates
  (`evalAssertions.js` ~L65-75) are enabled by no case; only
  `harness.test.js` ~L133-139 uses them. Harness merges `eval_cases.v1.json`
  over `prompt_test_cases.json`; v1 ADV entries have no `expected_keywords`
  key.
- **Dataset:** `expected_keywords` is a required list field
  (`REQUIRED_V1_FIELDS`, `dataset.py` ~L22) read unconditionally by
  `to_mlflow_records` (~L343). `EXPECTATION_FIELDS` ~L61. 9 cases have
  `expected_facts`. Non-ADV cases with keywords but no facts (15):
  DISC-02, POINT-02, POLY-01, POLY-02, URBAN-01, CORR-01, CORR-02, RES-02,
  RES-03, PROMPT-01..04, LESA-01, LESA-02. All 15 have TOOL spans in run
  `f2df7fe1`; only LESA-01's `calculate_preliminary_lesa` span is an error.
- `tests/eval/test_phase4_databricks_contract.py` ~L50 asserts SA-MA
  `expected_keywords` / `expected_facts` match between `prompt_test_cases.json`
  and `eval_cases.v1.json`. Do not edit SA-MA keywords or facts.
- `test_common_matching.py` ~L266/~L406 iterate dataset keywords and require
  digit-edged keywords to exist (non-ADV keywords keep them).
- ADRs: none conflict (0003 preliminary authority is preserved by keeping
  `fppa_compliance` and the guideline wording).
- MLflow: experiment id `517983779529169`; `search_traces` needs
  `locations=["517983779529169"]`.
- Test env (serverless): `PYTHONDONTWRITEBYTECODE=1`; `pip install -e .
  mlflow==3.12.0 pytest-asyncio`, then `pip install fastmcp==4.1.6 mcp==2.3.0`
  (bare image lacks `fastmcp`; the first install resolves fastmcp 3.4.0 / mcp
  1.30.0, which breaks `agent.py` `tool.input_schema`; verified at baseline); Ruff on `git archive HEAD | tar -x` in `/tmp`
  with `RUFF_CACHE_DIR=/tmp/ruff-cache`; harness tests via the `/tmp/r87` copy +
  `source databricks/bootstrap-serverless.sh` + `npm ci && npm test`.
- Reference implementations: `make_trace` in `test_databricks_scorers.py`
  ~L44; `FakeLLM` in `test_databricks_agent.py` ~L55;
  `FPPA_COMPLIANCE_GUIDELINE` wording in `scorers.py` ~L21 (conditional
  "when the response reports results" pattern).

## Decision Log

1. **D1 - 2026-11-12 - ordering:** Fix the `tools=None` runner bug first.
2. **D2 - 2026-11-12 - judge:** Behavior and source intent move to the
   existing `expectations_guidelines` judge via per-row `guidelines` built in
   `to_mlflow_records`. No new judge class.
3. **D3 - 2026-11-12 - Pi/harness behaviors:** Remove the
   `required_behaviors` / `source_disclosure` string checks from Pi and the
   dead predicates from the harness. Fields stay in the case files as judge
   input only.
4. **D4 - 2026-11-12 - keywords:** ADV `expected_keywords` -> `[]`, unique
   intent folded into `required_behaviors`. Pi keyword misses are advisory.
   Harness keeps keywords on non-ADV cases. Databricks `keywords_present` is
   removed once every non-ADV case with keywords has `expected_facts`.
5. **D5 - 2026-11-12 - fact sources:** Regulatory facts from policy text and
   prompts; data facts from TOOL span outputs of run `f2df7fe1`; no
   `verified_on` on new facts; `keywords_present` removed only after all 15
   cases have facts. Accepted risk: server output becomes ground truth, so
   `correctness` catches agent misreporting, not server bugs.
6. **D6 - 2026-11-12 - errored traces:** Add deterministic `agent_completed`
   (fails on trace state ERROR or None response, rationale quotes the error).
   Judges and structural scorers unchanged.
7. **D7 - 2026-11-12 - logistics (defaults accepted):** New branch off
   `fix/eval-tuning1`; one conventional commit per task, no wave numbers;
   max two concurrent workers per wave (carried from Plan 46 D4); targeted
   tests per task, serial suites at each gate; final full `--all` rerun.

## Scorer Dispositions

| Scorer | Disposition | Evidence |
|---|---|---|
| `required_behaviors_present` | **2 - replace with judge** (existing `expectations_guidelines` via per-row guidelines) | 8/14 fails; every non-None fail was paraphrase; no judge covered ADV rows |
| `source_disclosed` | **2 - replace with judge** (conditional source guideline) | 0/8; judges did not penalize the same rows (`fppa_compliance` yes, `correctness` None) |
| `keywords_present` | **3 then 1** - narrow (ADV keywords removed), then remove from Databricks once `correctness` has facts; harness keeps it on raw server output; Pi advisory | 12/14 ADV fails were phrasing; 21/22 non-ADV pass and mostly name exact values |
| new `agent_completed` | **added** (deterministic, structural) | 6 crashed traces passed budget/prohibited/tool-correctness scorers |

## Wave & Dependency Table

| Wave | Task | Title | Must edit | Can create | Depends on |
|---|---|---|---|---|---|
| 1 | 47.1.1 | Omit `tools` when withheld | `eval/databricks/agent.py`; `eval/databricks/test_databricks_agent.py` | none | baseline |
| 1 | 47.1.2 | Add `agent_completed` scorer | `eval/databricks/scorers.py`; `eval/databricks/test_databricks_scorers.py`; `eval/databricks/README.md` | none | baseline |
| 1 gate | - | Zero-budget live smoke | none | `.development/47/` | 47.1.1, 47.1.2 |
| 2 | 47.2.1 | Build judge guidelines from behaviors and sources | `eval/common/dataset.py`; `eval/common/test_common_dataset.py` | none | 47.1 gate |
| 2 | 47.2.2 | Remove behavior/source string scorers | `eval/databricks/scorers.py`; `eval/databricks/test_databricks_scorers.py`; `eval/databricks/README.md` | none | 47.1 gate |
| 2 | 47.2.3 | Pi: drop behavior/source checks, advisory keywords | `eval/pi/run_evals.py`; `eval/pi/test_agent_eval.py` | none | 47.1 gate |
| 2 | 47.2.4 | Harness: drop unused behavior/source predicates | `eval/fpac_soil_mcp_harness/lib/evalAssertions.js`; `eval/fpac_soil_mcp_harness/test/harness.test.js`; `eval/fpac_soil_mcp_harness/README.md` | none | 47.1 gate |
| 2 gate | - | String-check retirement gate | none | none | 47.2.1-47.2.4 |
| 3 | 47.3.1 | ADV keywords to required behaviors | `eval/prompt_test_cases.json` | none | 47.2 gate |
| 3 | 47.3.2 | Delete `required_behavior_missing` | `eval/common/matching.py`; `eval/common/test_common_matching.py` | none | 47.2 gate |
| 3 gate | - | Case-data gate + fact source extraction | none | `.development/47/f2df7fe1_tool_outputs.json` | 47.3.1, 47.3.2 |
| 4 | 47.4.1 | Author expected facts for 15 cases | `eval/prompt_test_cases.json`; `tests/eval/test_phase4_databricks_contract.py` | none | 47.3 gate |
| 4 gate | - | Facts gate | none | none | 47.4.1 |
| 5 | 47.5.1 | Remove Databricks `keywords_present` | `eval/databricks/scorers.py`; `eval/databricks/test_databricks_scorers.py`; `eval/databricks/README.md`; `eval/common/dataset.py`; `eval/common/test_common_dataset.py` | none | 47.4 gate |
| final | - | Full T1 rerun vs `f2df7fe1` | `planning/STATE_47.md` | none | 47.5.1 |

Disjointness: within each wave, Must-edit sets are pairwise disjoint (checked
by grep for hidden coupling; see Hazards). Wave 2 has four tasks; run at most
two at once (D7).

## Hazards

- **FakeLLM accepts `tools=None`.** 47.1.1 tests must assert the `tools` key is
  *absent* from `llm.calls[i]`, not merely falsy.
- **Same file across waves:** `scorers.py` (47.1.2, 47.2.2, 47.5.1),
  `prompt_test_cases.json` (47.3.1, 47.4.1), `dataset.py` (47.2.1, 47.5.1).
  Sequenced by wave; each worker reads the prior task's STATE report first.
- **Import order:** `scorers.py` L17 and `run_evals.py` ~L32 import
  `required_behavior_missing`; 47.3.2 deletes it only after 47.2.2 and 47.2.3
  remove those imports.
- **Pi fail-closed behaviors:** Pi's `required_behavior_missing` fails unknown
  behavior text. 47.3.1 rewrites `required_behaviors` only after 47.2.3
  removes that check.
- **SA-MA cross-file test** (`tests/eval/test_phase4_databricks_contract.py`):
  do not touch SA-MA keywords or facts.
- **LESA-01 no-facts test** (`test_missing_expected_facts_omit_judge_expectations_instead_of_failing`,
  `tests/eval/test_phase4_databricks_contract.py` ~L135) asserts LESA-01 has no
  `expected_facts` or `guidelines`. 47.4.1 gives LESA-01 facts, so it owns
  rewriting that test on a synthetic row. Found in plan review.
- **LESA-01:** the case's input assigns 120 points to one criterion and the
  tool rejects it. Per D5 its data facts describe the rejection the server
  returned. Flag in STATE that the case prompt likely needs rework (out of
  scope).
- **T1 privacy rule:** fact extraction reads only synthetic/public case
  traces; the `.development/47/` dump is untracked.
- Pi test run: the user previously declined one broad Pi pytest command; the
  47.2.3 command is targeted to `eval/pi/test_agent_eval.py -m "not
  agent_eval"`. Confirm with the user at the wave 2 gate if needed.

## Review Flags (judgment calls for approval)

- **R1:** 15 cases need facts, not 13 as first estimated in conversation (7 of
  the 9 fact-bearing cases have keywords; 22 - 7 = 15).
- **R2:** The live opt-in Pi test at `test_agent_eval.py` ~L1301 still
  hard-asserts POINT-01 keywords (exact values `prime farmland`, `409406`).
  Left as is; Pi advisory applies to the runner only.
- **R3:** 47.4.1 covers 15 cases in one file; if the micro-plan exceeds 12
  steps, split by case family into two sequential tasks (same file, so not
  parallel).
- **R4:** Moving behaviors into `expectations_guidelines` makes ADV rows
  judged for the first time; expect new judge failures that are real signal or
  judge strictness. The final gate lists them as findings, not fixes.
- **R5:** The source guideline is conditional ("when the response reports ...
  results"), mirroring `fppa_compliance`, so refusals that report nothing are
  not penalized for omitting a source.
- **R6:** LESA-01 facts encode the server's rejection (D5 source rule).
- **R7:** Branch name not yet chosen; proposed `feat/judge-first-scoring`
  off `fix/eval-tuning1` (`8c90f0d`).
- **R8 (review fix):** 47.4.1 now also edits
  `tests/eval/test_phase4_databricks_contract.py` (LESA-01 no-facts test), and
  47.2.1 acceptance runs that file because it exercises `to_mlflow_records`.

## Test Commands

Run from the repo root unless noted. `PY` below means
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:eval python -m pytest -p no:cacheprovider -q`
(`src` is needed because `agent.py` imports `fpac_soil_mcp`; on a local uv
checkout, `uv run pytest -q` is equivalent).

- Databricks scorers: `PY eval/databricks/test_databricks_scorers.py`
- Databricks agent: `PY eval/databricks/test_databricks_agent.py`
- Databricks runner/dry run: `PY eval/databricks/test_databricks_runner.py eval/databricks/test_databricks_dry_run.py`
- Common: `PY eval/common`
- Pi: `PY eval/pi/test_agent_eval.py -m "not agent_eval"`
- Phase 4 contract: `PY tests/eval/test_phase4_databricks_contract.py`
- Harness: in `/tmp/r87/repo` copy, `source databricks/bootstrap-serverless.sh && cd eval/fpac_soil_mcp_harness && npm ci && npm run check && npm test`
- Ruff (archive copy avoids workspace-FS false EXE002; `git stash create` snapshots uncommitted edits without touching the working tree, falling back to HEAD when clean): `rm -rf /tmp/r47 && mkdir /tmp/r47 && T=$(git stash create) && git archive "${T:-HEAD}" | tar -x -C /tmp/r47 && cd /tmp/r47 && RUFF_CACHE_DIR=/tmp/ruff-cache ruff check <files> && RUFF_CACHE_DIR=/tmp/ruff-cache ruff format --check <files>`

## Task Specs

### 47.1.1 - Omit `tools` when withheld

- **Repo:** fpac-soil-mcp. **Temp:** `.development/47/`.
- **Must edit:** `eval/databricks/agent.py`, `eval/databricks/test_databricks_agent.py`.
- **Depends on:** baseline.
- **Spec:** In `build_agent.run`, never pass `tools=None`. Build the create
  kwargs and include `tools` only when tools are active; when the budget is
  exhausted (from the start or mid-run) omit the key entirely. Endpoint probe
  confirmed omitting `tools` works with and without tool-call history. Keep
  the existing zero-budget system prompt text. Add tests: (a) zero budget ->
  `"tools" not in llm.calls[0]`; (b) `max_tool_calls=1` with a FakeLLM script
  `("tools", [one call])` then `("text", ...)` -> first call has `tools`,
  second call has no `tools` key, answer is the text.
- **Anchors:** `active_tools = None if budget_exhausted` (~L261);
  `llm.chat.completions.create(` (~L262); `class FakeLLM` (~L55);
  `test_zero_call_budget_disables_tool_use` (~L189).
- **Do not touch:** prompt files, `case_forces_tool_use`, tracing.
- **Acceptance:** `PY eval/databricks/test_databricks_agent.py` passes with the
  two new assertions; the updated zero-budget test fails on the old code
  (worker states this was checked by reasoning or a revert).

### 47.1.2 - Add `agent_completed` scorer

- **Must edit:** `eval/databricks/scorers.py`, `eval/databricks/test_databricks_scorers.py`, `eval/databricks/README.md`.
- **Depends on:** baseline.
- **Spec:** Add deterministic `agent_completed(trace, outputs)` that always
  returns a Feedback (never None): `False` when `trace.info.state` is ERROR or
  `outputs is None`, rationale = root span status description (truncated to
  300 chars) or "no response"; else `True`. Register in
  `DETERMINISTIC_SCORER_NAMES` and the `deterministic_scorers` tuple (first
  position). Tests: passing trace via `make_trace`; errored trace via an
  `@mlflow.trace` function that raises (catch the exception, then
  `mlflow.get_trace(mlflow.get_last_active_trace_id())`); names test still
  matches built scorers. README Scoring section: list all current
  deterministic scorers including `agent_completed`.
- **Anchors:** `DETERMINISTIC_SCORER_NAMES` (~L28); `def deterministic_scorers`
  (~L307); `def make_trace` (test ~L44); `test_scorer_names_match_built_scorers`
  (~L252); README `## Scoring` (~L147).
- **Do not touch:** judge scorers, other deterministic scorers.
- **Acceptance:** `PY eval/databricks/test_databricks_scorers.py eval/databricks/test_databricks_runner.py eval/databricks/test_databricks_dry_run.py` pass.

### 47.1 gate - Zero-budget live smoke (orchestrator)

From the executeCode python session with `eval` and `eval/databricks` on
`sys.path`: `run_mlflow_eval.run(["--cases",
"ADV-PRIVACY-01,ADV-INJECTION-01,ADV-CORRIDOR-01,ADV-RELOCATE-01,ADV-FORMS-01,ADV-UNRELATED-01"])`.
Pass: 6/6 non-None responses, `agent_completed` 6/6 pass, `tool_call_budget`
6/6 pass. Record run id and per-scorer counts in STATE_47.

### 47.2.1 - Build judge guidelines from behaviors and sources

- **Must edit:** `eval/common/dataset.py`, `eval/common/test_common_dataset.py`.
- **Depends on:** 47.1 gate.
- **Spec:** In `to_mlflow_records`, set `expectations["guidelines"]` to the
  case's `guidelines` + each `required_behaviors` entry verbatim + one sentence
  per `source_disclosure` entry: `"When the response reports soil, farmland,
  or urban-area results, it identifies {source} as a data source; a response
  that reports no results does not need to name a source."` De-duplicate,
  preserve order, omit the key when empty. Remove `required_behaviors` and
  `source_disclosure` from `EXPECTATION_FIELDS` (they now arrive only as
  guidelines). Keep both in `ADVERSARIAL_FIELDS` validation. Add a comment
  block above `ADVERSARIAL_FIELDS` documenting field roles: `required_behaviors`
  and `source_disclosure` are judge input (`expectations_guidelines`) only and
  are no longer string-matched by any runner; `expected_keywords` is a harness
  raw-output smoke check and a Pi advisory. Tests: a row with all three inputs
  yields the merged list; a row with none has no `guidelines` key; existing
  record-shape tests updated.
- **Anchors:** `EXPECTATION_FIELDS` (~L61); `ADVERSARIAL_FIELDS` (~L44);
  `def to_mlflow_records` (~L343); test ~L110-124, ~L194-204.
- **Do not touch:** validation rules, `case_forces_tool_use`, case JSON.
- **Acceptance:** `PY eval/common/test_common_dataset.py tests/eval/test_phase4_databricks_contract.py` passes; `PYTHONPATH=src:eval python
  eval/databricks/run_mlflow_eval.py --dry-run --all`
  prints 38 records.

### 47.2.2 - Remove behavior/source string scorers

- **Must edit:** `eval/databricks/scorers.py`, `eval/databricks/test_databricks_scorers.py`, `eval/databricks/README.md`.
- **Depends on:** 47.1 gate (reads 47.1.2 report).
- **Spec:** Delete `required_behaviors_present` and `source_disclosed`, their
  entries in `DETERMINISTIC_SCORER_NAMES` and the scorer tuple, the
  `required_behavior_missing` import, and their test assertions. Update the
  `required_status_matches` comment (~L229) that names
  `required_behaviors_present`. README: state that behavior and source intent
  is graded by `expectations_guidelines` via per-row guidelines.
- **Anchors:** `def required_behaviors_present` (~L237); `def source_disclosed`
  (~L248); import L17; `test_safety_and_disclosure_scorers` (~L146).
- **Do not touch:** `prohibited_behaviors_absent`, `privacy_non_echo`, judges,
  `keywords_present` (removed in 47.5.1).
- **Acceptance:** `PY eval/databricks/test_databricks_scorers.py eval/databricks/test_databricks_runner.py eval/databricks/test_databricks_dry_run.py` pass; `git grep -n "source_disclosed\|required_behaviors_present" -- eval` returns nothing.

### 47.2.3 - Pi: drop behavior/source checks, advisory keywords

- **Must edit:** `eval/pi/run_evals.py`, `eval/pi/test_agent_eval.py`.
- **Depends on:** 47.1 gate.
- **Spec:** Remove the `required_behavior_missing` and `source_disclosure`
  failure appends (~L601-606) and the `required_behavior_missing` import
  (~L32). Keyword misses (~L837-842) no longer append to `failures`; record
  them in the case result as `advisory_missing_keywords` (list) and print them
  as an advisory line. Leave `expected_status`, prohibited, privacy, tool, and
  budget checks unchanged. Update or add tests: a case with missing keywords
  still passes and reports the advisory; a case with `required_behaviors` /
  `source_disclosure` no longer fails on them.
- **Anchors:** `required_behavior_missing(text` (~L601);
  `missing_sources` (~L604); `missing_keywords = keywords_present` (~L837);
  result dict `"expected_keywords": expected_keywords` (~L992);
  `test_agent_eval.py` ~L384-386, ~L578, ~L1301.
- **Do not touch:** `common/matching.py`, Pi prompts, case JSON, and the live
  opt-in `agent_eval` test at ~L1301 (it hard-asserts POINT-01's exact-value
  keywords; left as is, see review flag R2).
- **Acceptance:** `PY eval/pi/test_agent_eval.py -m "not agent_eval"` passes.

### 47.2.4 - Harness: drop unused behavior/source predicates

- **Must edit:** `eval/fpac_soil_mcp_harness/lib/evalAssertions.js`, `eval/fpac_soil_mcp_harness/test/harness.test.js`, `eval/fpac_soil_mcp_harness/README.md`.
- **Depends on:** 47.1 gate.
- **Spec:** Remove the `requiredBehaviors` and `sourceDisclosure` predicates
  and their test usage (`harness.test.js` ~L133-139 predicate list and the
  `source_disclosure` fixture field). Keep `checkKeywords` and all other
  predicates. README: note that behavior and source intent is judged in the
  Databricks eval, and the harness keyword check covers raw server output
  only.
- **Anchors:** `requiredBehaviors:` (~L65); `sourceDisclosure:` (~L71);
  harness test ~L133.
- **Do not touch:** `server.js`, `evalCases.js`, case JSON.
- **Acceptance:** harness `npm run check && npm test` pass in the `/tmp` copy;
  `git grep -n "requiredBehaviors\|sourceDisclosure" -- eval/fpac_soil_mcp_harness` returns nothing.

### 47.2 gate - String-check retirement (orchestrator)

Serially: `PY eval/common eval/databricks/test_databricks_scorers.py
eval/databricks/test_databricks_agent.py eval/databricks/test_databricks_runner.py
eval/databricks/test_databricks_dry_run.py tests/eval/test_phase4_databricks_contract.py`;
Pi command; harness command; Ruff on touched Python files.

### 47.3.1 - ADV keywords to required behaviors

- **Must edit:** `eval/prompt_test_cases.json` (ADV-* entries only).
- **Depends on:** 47.2 gate.
- **Spec:** For each of the 14 ADV cases set `expected_keywords` to `[]`. Where
  a keyword's intent is not already stated by an existing `required_behaviors`
  entry, append one plain-language behavior sentence (e.g. ADV-PARTIAL-01
  "partial" -> "States that the result is incomplete because part of the
  lookup failed."). Do not change prompts, prohibited behaviors, budgets, or
  status fields. Record a keyword -> behavior mapping table in the task TODO
  notes.
- **Anchors:** `"id": "ADV-` entries; current keyword list in Recon.
- **Do not touch:** non-ADV cases, `eval_cases.v1.json`.
- **Acceptance:** `PY eval/common` and `PY tests/eval/test_phase4_databricks_contract.py` pass; a one-liner confirms 14 ADV cases have `expected_keywords == []` and non-empty `required_behaviors`.

### 47.3.2 - Delete `required_behavior_missing`

- **Must edit:** `eval/common/matching.py`, `eval/common/test_common_matching.py`.
- **Depends on:** 47.2 gate (47.2.2 and 47.2.3 removed the imports).
- **Spec:** Delete `required_behavior_missing` and its tests (~L181-207).
  Confirm with `git grep -n required_behavior_missing` that no caller remains.
- **Anchors:** `def required_behavior_missing` (~L128); tests ~L181, ~L194, ~L207.
- **Do not touch:** `keywords_present`, prohibited-behavior helpers.
- **Acceptance:** `PY eval/common` passes; the grep is empty.

### 47.3 gate - Case data + fact source extraction (orchestrator)

Run the 47.2 gate suites. Then dump, for the 15 cases listed in Recon, every
TOOL span `name`, sanitized `inputs`, and `outputs` from run `f2df7fe1`
(`locations=["517983779529169"]`) to
`.development/47/f2df7fe1_tool_outputs.json` (untracked).

### 47.4.1 - Author expected facts for 15 cases

- **Must edit:** `eval/prompt_test_cases.json` (the 15 cases only);
  `tests/eval/test_phase4_databricks_contract.py` (only
  `test_missing_expected_facts_omit_judge_expectations_instead_of_failing`:
  build a synthetic row from LESA-01 with `expected_facts` and `guidelines`
  removed, keep both record assertions).
- **Depends on:** 47.3 gate.
- **Spec:** Add `expected_facts` (2-4 full sentences each) to DISC-02,
  POINT-02, POLY-01, POLY-02, URBAN-01, CORR-01, CORR-02, RES-02, RES-03,
  PROMPT-01..04, LESA-01, LESA-02. Every existing keyword must be covered by at
  least one fact. Regulatory facts come from `FPPA_POLICY_BLOCK`, resources,
  and the case prompt; data facts (mukeys, acres, ratings, county names,
  classes) come only from `.development/47/f2df7fe1_tool_outputs.json`. Use
  tolerant wording for numbers ("about X acres (within 1%)"), matching the
  INTERP-01 style. Do not add `verified_on`. Keep `expected_keywords` as is.
  LESA-01: facts describe the server's rejection; note in Discovered that the
  prompt likely needs rework.
- **Anchors:** existing facts on POINT-01, MUKEY-01, INTERP-01 as style
  reference.
- **Do not touch:** ADV and SA-MA cases, `eval_cases.v1.json`.
- **Acceptance:** `PY eval/common tests/eval/test_phase4_databricks_contract.py`
  pass; a one-liner confirms every non-ADV case with keywords has non-empty
  `expected_facts`; orchestrator spot-checks 5 data facts against the dump.

### 47.4 gate - Facts (orchestrator)

Suites from 47.2 gate. Optional live check: `--cases` on 3 of the 15 to
confirm `correctness` now returns a value.

### 47.5.1 - Remove Databricks `keywords_present`

- **Must edit:** `eval/databricks/scorers.py`, `eval/databricks/test_databricks_scorers.py`, `eval/databricks/README.md`, `eval/common/dataset.py`, `eval/common/test_common_dataset.py`.
- **Depends on:** 47.4 gate.
- **Spec:** Delete the `keywords_present` scorer, its name entry, the
  `_keywords_present` import, and `test_keywords_present`. In
  `to_mlflow_records`, stop copying `expected_keywords` into expectations
  (field stays required in the case schema for Pi and the harness). Add a
  dataset test: every non-ADV case with non-empty `expected_keywords` has
  non-empty `expected_facts` (guards D5). Update the field-role comment and
  README.
- **Anchors:** `def keywords_present` (scorers ~L149); import L16;
  `"expected_keywords": list(case["expected_keywords"])` (dataset ~L356);
  test_common_dataset ~L194-204.
- **Do not touch:** `common.matching.keywords_present`, Pi, harness.
- **Acceptance:** `PY eval/common eval/databricks/test_databricks_scorers.py eval/databricks/test_databricks_runner.py eval/databricks/test_databricks_dry_run.py tests/eval/test_phase4_databricks_contract.py` pass.

### Final gate - Full T1 rerun (orchestrator)

All suites serially + Ruff + harness. Then `run_mlflow_eval.run(["--all",
"--max-workers", "4"])`. Record in STATE_47 a comparison table versus
`f2df7fe1` for every scorer. Expected: 0 None responses; `agent_completed`
38/38; `correctness` non-null on 24 rows (9 + 15); `expectations_guidelines`
non-null on all ADV rows; removed scorers absent. Investigate (do not fix in
this plan) any new `expectations_guidelines` or `correctness` failures and
list them as findings.
