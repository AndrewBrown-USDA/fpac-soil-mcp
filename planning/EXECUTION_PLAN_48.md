# EXECUTION PLAN 48: Consolidate Evaluation Corpora

## Goal & Scope

**Goal:** Unify the Python/Pi, Databricks, and JavaScript harness evaluation data around `eval/eval_cases.v1.json` as the sole corpus. Reconcile the 38 Python cases and 19 overlapping harness cases without losing judge-first metadata or harness assertions, validate the merged schema strictly, move every active reader to the unified file, restore whole-corpus ID coverage, and remove the duplicate `prompt_test_cases.json`.

**In scope:**

- Reconcile one record per unique case ID in `eval/eval_cases.v1.json`, preserving Python evaluation fields and judge-first facts/guidelines/keywords while retaining harness-only fields and behavior.
- Extend the Python dataset schema with field-specific validation for the five harness fields: `assertions`, `invocation`, `expected_result`, `ownership`, and `protected_regulatory_assertions`. Continue rejecting unknown fields and duplicate IDs.
- Change Python, Pi, Databricks notebook, and harness readers/tests to use the unified corpus directly; remove the JavaScript overlay merge.
- Restore a corpus-ID check that covers all cases and test harness loading/invocation against the unified corpus.
- Delete `eval/prompt_test_cases.json` after all active readers have migrated; update all active documentation and the Pi evaluation skill reference.
- Preserve the harness `/api/eval-cases` response envelope while setting the obsolete overlay fields `executable_version` and `executable_source` to `null`.

**Out of scope:**

- Changes to scorer logic, judge prompts, agent behavior, or scoring/evaluation methodology. The consolidation must preserve `expected_facts`, `guidelines`, `required_behaviors`, `source_disclosure`, `expected_keywords`, tool expectations, status/prohibited-behavior metadata, and budgets for their existing consumers.
- Adding new case intent or changing expected results beyond resolving known cross-file conflicts under the approved precedence rule.
- Changing `eval/common/prohibited_behaviors.v1.json` or adding a replacement for the stale `silent_nccpi_fallback` behavior ID. The unified rows use the current Python case's valid behavior IDs.
- A live Pi run, a Databricks/model-judged T1 run, or any network-dependent evaluation.
- Rewriting historical plans, state reports, or other historical planning artifacts that mention the former filename.
- New dependencies, an ADR, or changes outside the files listed in each task.

**Verbatim issue constraints:**

- “Consolidate into `eval_cases.v1.json` as the single source of truth.”
- “Move the 19 prompt-only cases into `eval_cases.v1.json` and delete `prompt_test_cases.json`.”
- `eval/common/test_common_matching.py`: “Restore corpus-ID check to cover all cases”
- “Remove overlay merge logic; load `eval_cases.v1.json` directly”

## Reconnaissance Log (2026-11-12)

- Repository: `D:\workspace\fpac-soil-mcp`, branch `refactor/eval-corpus1`. The worktree was clean except for the user-provided untracked `planning/RESEARCH_ISSUE_88_EVAL_CORPUS_CONSOLIDATION.md`; preserve it.
- Current files contain 38 prompt-corpus cases and 19 harness records. The 19 harness IDs all overlap; 19 cases occur only in the prompt corpus. There are 38 unique IDs and no duplicates.
- Overlapping rows are not identical. Conflicts include seven adversarial `required_behaviors` values and CORR-01's category, prompt, facts, geometry, and harness metadata. The user decided to use Python values for shared evaluation fields, retaining harness-only fields from the overlay and resolving the conflicts explicitly.
- The harness corpus has the stale `silent_nccpi_fallback` behavior ID (in addition to `fabricated_rating_or_provenance`); it is absent from the current Python cases and behavior catalog. Do not add a deprecated catalog entry. Use the Python value for this shared core field.
- Python schema entry point: `eval/common/dataset.py` (344 lines); `DEFAULT_PATH`, `ALLOWED_FIELDS`, `_row_errors`, and `validate_cases` are the relevant anchors. Python dataset tests are in `eval/common/test_common_dataset.py` (292 lines); the whole-corpus behavior/catalog test is in `eval/common/test_common_matching.py` (185 lines).
- Pi readers: `eval/pi/run_evals.py` (1005 lines; `FIXTURES_PATH`) and `eval/pi/test_agent_eval.py` (1165 lines; `PROMPT_FIXTURES_PATH` and `prompt_dataset` fixture). Databricks reference: `eval/databricks/run_t1_eval_notebook.py` (163 lines; introductory markdown). Contract tests: `tests/eval/test_phase4_databricks_contract.py` (117 lines; `DATASET_PATH`, `HARNESS_CASES_PATH`, and `_read_harness_cases`).
- Harness readers: `eval/fpac_soil_mcp_harness/lib/config.js` (91 lines; `evalCasesPath`) and `lib/evalCases.js` (201 lines; `resolveArguments`, `buildInvocation`, `loadEvalCases`). Harness tests: `test/harness.test.js` (197 lines) and `test/smoke.test.js`; smoke tests bind to dynamically selected loopback ports. Existing `loadEvalCases` returns both primary and overlay metadata; the user chose to keep the response envelope and null the overlay-only values after migration.
- Five harness-only fields in the current overlay are `assertions`, `invocation`, `expected_result`, `ownership`, and `protected_regulatory_assertions`. Strict field-specific checks are required; do not broaden the Python schema to accept arbitrary keys.
- Active filename references also exist in root `AGENTS.md`/`README.md`, `.github/skills/pi-mcp-eval/SKILL.md`, and harness/Databricks `AGENTS.md`, `.env.example`, and READMEs. Historical references in `planning/` remain unchanged.
- Test architecture: ADR 0011 is Accepted and requires mocked/offline tests by default, with live network and agent evals opt-in. No ADR conflicts with this work.
- Baseline before wave 1:
  - `uv run pytest -m "not live_network and not agent_eval" -q` — 951 passed, 45 deselected.
  - `uv run ruff check .` — passed; `uv run ruff format --check .` — passed (652 files already formatted).
  - From `eval\fpac_soil_mcp_harness`: `npm run check` — passed; `npm test` — 18 passed, 0 failed.
  - Root pytest emitted existing Shapely and MLflow deprecation warnings. They are baseline-only and unrelated.
- Reference implementations: `validate_cases`/`_row_errors` in `eval/common/dataset.py`; `test_checked_in_dataset_validates` in `eval/common/test_common_dataset.py`; `resolveArguments`, `buildInvocation`, and `loadEvalCases` in `eval/fpac_soil_mcp_harness/lib/evalCases.js`; existing harness smoke assertions in `test/smoke.test.js`.

## Decision Log

1. **D1 — 2026-11-12 — Conflict precedence:** Use `prompt_test_cases.json` as authority for shared Python evaluation fields, including the seven behavior-list disagreements and CORR-01's category/prompt/facts/geometry. Retain harness-only fields from `eval_cases.v1.json`; do not apply blanket overlay precedence.
2. **D2 — 2026-11-12 — Active references:** Update every active code, configuration, skill, and user-facing documentation reference to the old filename. Preserve historical planning and state reports unchanged.
3. **D3 — 2026-11-12 — Acceptance:** Require offline Python, Ruff, and harness checks. Live Pi and Databricks/model-judged runs are not gates for corpus consolidation, consistent with ADR 0011.
4. **D4 — 2026-11-12 — Parallelism:** Maximum two concurrent workers per wave.
5. **D5 — 2026-11-12 — Worker policy:** Use runtime-default worker model selection and the wave-orchestration escalation ladder; no custom model or credit budget.
6. **D6 — 2026-11-12 — Validation:** Add field-specific type/shape validation for the five established harness-only fields and continue rejecting unknown fields.
7. **D7 — 2026-11-12 — Harness API:** Keep the existing `/api/eval-cases` response envelope; set `executable_version` and `executable_source` to `null` because the overlay no longer exists. `version` and `source` identify the unified corpus.
8. **D8 — 2026-11-12 — Migration order:** Reconcile and validate the unified file first, migrate Python and JavaScript consumers in parallel next, then delete the old file and update active documentation. This keeps every wave independently testable.

## Wave & Dependency Table

| Wave | Task | Title | Must edit | Can create | Depends on |
|---|---|---|---|---|---|
| 1 | 48.1.1 | Reconcile corpus and validate unified schema | `eval/eval_cases.v1.json`; `eval/common/dataset.py`; `eval/common/test_common_dataset.py` | none | baseline |
| 2 | 48.2.1 | Migrate Python evaluation readers and ID coverage | `eval/pi/run_evals.py`; `eval/pi/test_agent_eval.py`; `eval/databricks/run_t1_eval_notebook.py`; `eval/common/test_common_matching.py`; `tests/eval/test_phase4_databricks_contract.py` | none | 48.1.1 |
| 2 | 48.2.2 | Load the unified corpus directly in the harness | `eval/fpac_soil_mcp_harness/lib/config.js`; `eval/fpac_soil_mcp_harness/lib/evalCases.js`; `eval/fpac_soil_mcp_harness/test/harness.test.js`; `eval/fpac_soil_mcp_harness/test/smoke.test.js` | none | 48.1.1 |
| 3 | 48.3.1 | Retire the duplicate corpus and update active references | delete `eval/prompt_test_cases.json`; edit `AGENTS.md`; `README.md`; `.github/skills/pi-mcp-eval/SKILL.md`; `eval/fpac_soil_mcp_harness/AGENTS.md`; `eval/fpac_soil_mcp_harness/.env.example`; `eval/fpac_soil_mcp_harness/README.md`; `eval/databricks/README.md` | none | 48.2.1, 48.2.2 |

**Wave discipline:** task file scopes are disjoint within each wave. Workers may run targeted tests only; the orchestrator runs the full gate serially at each wave boundary. At most two workers run concurrently. Keep the old prompt corpus through waves 1 and 2 so existing readers remain functional until all consumers have moved.

## Task Specifications

### 48.1.1 — Reconcile corpus and validate unified schema

- **Repo:** `AndrewBrown-USDA/fpac-soil-mcp` (`D:\workspace\fpac-soil-mcp`)
- **Files in scope:**
  - Must edit: `eval/eval_cases.v1.json`, `eval/common/dataset.py`, `eval/common/test_common_dataset.py`.
  - Can create: none. Scratch, if needed, only under `.development/48/`.
- **Depends on:** none.
- **Spec:** Build the single 38-record corpus in `eval/eval_cases.v1.json`. For every shared ID, preserve Python source values for shared evaluation fields and add harness-only fields from the existing overlay. Transfer the 19 Python-only cases. Explicitly reconcile the seven adversarial `required_behaviors` conflicts and CORR-01; preserve `expected_facts`, `guidelines`, `expected_keywords`, tool/status/budget metadata, and harness-specific invocation/assertion/result data. Use the current Python `prohibited_behaviors` for shared rows so `silent_nccpi_fallback` is not carried forward. Point `DEFAULT_PATH` at the unified file and strictly validate each established harness-only field without weakening unknown-field or duplicate-ID rejection. Match the schema and test style in `validate_cases` and `test_checked_in_dataset_validates`.
- **Constraints (do not touch):** Do not edit or delete `eval/prompt_test_cases.json` in this task; it is retained as a migration source until wave 3. Do not modify the prohibited-behavior catalog, scorer logic, harness loader, or other consumers. Do not use blanket merge precedence or accept arbitrary unknown keys.
- **Grep anchors:** `DEFAULT_PATH`, `ALLOWED_FIELDS`, `_row_errors`, `validate_cases` in `eval/common/dataset.py`; `test_checked_in_dataset_validates` and invalid-field tests in `eval/common/test_common_dataset.py`; `CORR-01` and the seven behavior-conflict cases in both corpus files.
- **Acceptance:** `uv run pytest eval/common/test_common_dataset.py -q` passes. The default loader validates all 38 unique unified rows, every field has the expected type/shape, the duplicate/unknown-key checks remain strict, and no stale prohibited behavior ID is accepted.

### 48.2.1 — Migrate Python evaluation readers and ID coverage

- **Repo:** `AndrewBrown-USDA/fpac-soil-mcp` (`D:\workspace\fpac-soil-mcp`)
- **Files in scope:**
  - Must edit: `eval/pi/run_evals.py`, `eval/pi/test_agent_eval.py`, `eval/databricks/run_t1_eval_notebook.py`, `eval/common/test_common_matching.py`, `tests/eval/test_phase4_databricks_contract.py`.
  - Can create: none. Scratch, if needed, only under `.development/48/`.
- **Depends on:** 48.1.1.
- **Spec:** Redirect Pi's runner and test fixture to the unified file, update the Databricks notebook reference, and update the phase-4 contract tests to inspect the unified record rather than compare two copies. Restore an ID check that covers all 38 cases in `test_common_matching.py`, pinning the full expected ID set and rejecting duplicates; retain the behavior-catalog coverage over every row. Do not change Pi scoring or Databricks record/scorer behavior.
- **Constraints (do not touch):** Do not edit `eval/common/dataset.py`, either corpus JSON file, or harness code in this task. Do not invoke Pi live agent tests or Databricks/model evaluation.
- **Grep anchors:** `FIXTURES_PATH` in `eval/pi/run_evals.py`; `PROMPT_FIXTURES_PATH`/`prompt_dataset` in `eval/pi/test_agent_eval.py`; `DATASET_PATH`, `HARNESS_CASES_PATH`, `_read_harness_cases` in `tests/eval/test_phase4_databricks_contract.py`; `test_every_corpus_behavior_id_is_in_the_shared_catalog` in `eval/common/test_common_matching.py`.
- **Acceptance:** `uv run pytest eval/pi/test_agent_eval.py tests/eval/test_phase4_databricks_contract.py eval/common/test_common_matching.py -m "not agent_eval" -q` passes; `rg -n "eval/eval_cases.v1.json" eval/databricks/run_t1_eval_notebook.py` finds the updated notebook reference.

### 48.2.2 — Load the unified corpus directly in the harness

- **Repo:** `AndrewBrown-USDA/fpac-soil-mcp` (`D:\workspace\fpac-soil-mcp`)
- **Files in scope:**
  - Must edit: `eval/fpac_soil_mcp_harness/lib/config.js`, `eval/fpac_soil_mcp_harness/lib/evalCases.js`, `eval/fpac_soil_mcp_harness/test/harness.test.js`, `eval/fpac_soil_mcp_harness/test/smoke.test.js`.
  - Can create: none. Scratch, if needed, only under `.development/48/`.
- **Depends on:** 48.1.1.
- **Spec:** Point the default harness configuration to `eval_cases.v1.json` and make `loadEvalCases` load that file directly, without reading or merging a sibling overlay. Preserve explicit invocation/argument handling and derive invocations for transferred Python-only tool, resource, and prompt cases using the existing `resolveArguments`/`buildInvocation` patterns. Preserve the existing response envelope; return `null` for `executable_version` and `executable_source`, with `version` and `source` describing the unified file. Add unit and HTTP smoke assertions for all 38 IDs, direct loading, invocation construction, and the metadata contract.
- **Constraints (do not touch):** Do not edit either corpus JSON file, Python readers/tests, or documentation. Keep `EVAL_CASES_PATH` overrides, current route shape, and deterministic harness behavior; do not add server/API features.
- **Grep anchors:** `evalCasesPath` in `lib/config.js`; `resolveArguments`, `buildInvocation`, `loadEvalCases` in `lib/evalCases.js`; loader/invocation tests in `test/harness.test.js`; `/api/eval-cases` assertions in `test/smoke.test.js`.
- **Acceptance:** From `eval\fpac_soil_mcp_harness`, `npm run check && npm test` passes. Tests prove the configured default is the unified file, all 38 cases load without overlay behavior, and overlay-only metadata is null.

### 48.3.1 — Retire the duplicate corpus and update active references

- **Repo:** `AndrewBrown-USDA/fpac-soil-mcp` (`D:\workspace\fpac-soil-mcp`)
- **Files in scope:**
  - Must edit: `AGENTS.md`, `README.md`, `.github/skills/pi-mcp-eval/SKILL.md`, `eval/fpac_soil_mcp_harness/AGENTS.md`, `eval/fpac_soil_mcp_harness/.env.example`, `eval/fpac_soil_mcp_harness/README.md`, `eval/databricks/README.md`, only the module docstring in `eval/common/dataset.py`, and only the fixture path constant in `tests/test_geometry.py`; delete `eval/prompt_test_cases.json`.
  - Can create: none. Scratch, if needed, only under `.development/48/`.
- **Depends on:** 48.2.1 and 48.2.2.
- **Spec:** Remove the duplicate prompt corpus only after every active reader has migrated. Update active setup, skill, harness, and Databricks documentation to name `eval/eval_cases.v1.json` as the single corpus, including the standalone harness deployment instructions and `EVAL_CASES_PATH` example. Update the `eval/common/dataset.py` module docstring to identify the unified corpus. Update the fixture path constant in `tests/test_geometry.py` to use the unified corpus, without changing test logic. Preserve historical planning artifacts and past state reports unchanged.
- **Constraints (do not touch):** Do not change runtime logic or test assertions. In `eval/common/dataset.py`, update only the module docstring; in `tests/test_geometry.py`, update only the fixture path constant. Do not edit historical plans/state or the unified case data. Do not leave active source, config, or documentation references to `prompt_test_cases.json`.
- **Grep anchors:** corpus references in root `AGENTS.md` and `README.md`; issue/fixture references in `.github/skills/pi-mcp-eval/SKILL.md`; the module docstring in `eval/common/dataset.py`; `LESA_FIXTURE_PATH` in `tests/test_geometry.py`; default corpus and setup text in harness `AGENTS.md`, `.env.example`, and `README.md`; shared adversarial corpus paragraph in `eval/databricks/README.md`.
- **Acceptance:** `git grep -n "prompt_test_cases\\.json" -- AGENTS.md README.md .github/skills/pi-mcp-eval eval` returns no matches, and `Test-Path eval\\prompt_test_cases.json` is false. Full wave gate passes.

## Hazards

- The two inputs are overlapping but not equivalent. Never spread the harness row over the Python row wholesale; retain Python values for shared evaluation fields and merge only harness-only fields, with the named conflicts handled explicitly.
- `silent_nccpi_fallback` occurs as a prohibited-behavior ID in the old overlay, not as a case ID. It was removed from the current catalog; use the Python-side row and ensure catalog validation still fails closed.
- The harness has explicit `invocation` values and `expected_tool_calls` can describe a different evidence contract. Preserve both fields; do not infer one from or overwrite the other.
- The SA-MA contract currently compares two JSON copies. After consolidation, test the unified row's data and invocation contract directly rather than retaining a self-comparison.
- The harness `loadEvalCases` response currently includes overlay metadata, and `test/smoke.test.js` asserts it. Keep the envelope but make the obsolete values `null`, as decided.
- Keep all tests offline. The harness HTTP smoke tests choose ephemeral loopback ports; run the harness test suite as one command and run wave gates serially.
- Do not rewrite old `planning/EXECUTION_PLAN_*` or `STATE_*` references: those are historical records, not active configuration.

## Wave Acceptance Gates

At the end of **each wave**, the orchestrator runs these serially:

1. `uv run pytest -m "not live_network and not agent_eval" -q`
2. `uv run ruff check .` and `uv run ruff format --check .`
3. From `eval\fpac_soil_mcp_harness`: `npm run check && npm test`

No live Pi or Databricks/model-judged evaluation is required. If a gate fails, follow the escalation limits in wave-orchestration; do not expand scope to fix unrelated baseline warnings.
