# Execution Plan 34 — PR Review Remediation for the Databricks Eval Tier

Branch: `feat/databricks-eval1` (HEAD `3db89a4` at planning time) · Template: `planning/PROMPT_TEMPLATE_34.md` · State: `planning/STATE_34.md`

## Goal & Scope

**Goal.** Resolve the Copilot review findings on the `feat/databricks-eval1` PR that apply to live code and current docs: document and pin the AGENT span's current behaviour, enforce number boundaries in keyword matching, let `--dry-run` work without MLflow, reject malformed datasets, make scorer list comparison strict, and correct the README. Then re-verify offline and with one 5-case live MLflow run.

**In scope (review finding → task):**

| # | Finding (severity) | Task |
|---|---|---|
| F1 | `eval/databricks/agent.py` AGENT span inputs/outputs recorded unsanitized (critical) | 34.2.2 (test + docstring) + 34.3.2 (README) |
| F2 | `eval/common/matching.py` CFR citation matching lacks numeric boundaries (moderate) | 34.1.1 |
| F3 | `eval/databricks/run_mlflow_eval.py` dry run constructs MLflow scorers (moderate) | 34.2.1 (names) + 34.3.1 |
| F4 | `eval/common/dataset.py` non-list `test_cases` silently loads zero cases (moderate) | 34.1.2 |
| F5 | `eval/databricks/scorers.py` list args string-coerced (moderate) | 34.2.1 |
| F6 | `eval/databricks/README.md` calls the future scope-aware prompt v2 (nit) | 34.3.2 |

**Out of scope (explicit):**

- Every finding on `planning/EXECUTION_PLAN_33.md` (C2 `2.0.0`, C4/C5 and task-spec `v1` default). Plan 33 is frozen history and is not edited (D5). Superseding facts live in `STATE_33.md` and D12.
- Text-content scrubbing of free-form prompts/answers. `privacy.sanitize_public_payload` is key-based; this plan does not add value-level PII detection.
- Full CFR citation parsing (title/part/section objects). Rejected in D4.
- Posting PR replies or resolving review threads on GitHub (the user does this).
- Pi live `make test-eval`, T2 deployed-app eval, dataset expansion, MLflow prompt registry (still deferred from Plan 33).

**Verbatim user constraints:**

- "As with #22 the primary purpose of the MLflow eval harness is to evaluate known, synthetic cases." (PR reply on F1)
- "actually plan 33 is frozen as history and is outdated and out of scope."

## Decision log

| ID | Date | Decision |
|---|---|---|
| D1 | 2026-10-21 | F1: document and pin, do not change the trace. The key-based sanitizer has nothing to strip from a plain-text request string or answer, so routing them through `_sanitize` adds no protection and risks breaking the judge scorers that read the `@mlflow.trace` root span. Instead: (a) keep `@mlflow.trace` as-is; (b) add a test pinning that the AGENT span records only the request text and the answer text, and that TOOL spans (where structured data lives) remain sanitized; (c) README states the synthetic-only rule and explains why AGENT-level sanitization adds no value. |
| D2 | 2026-10-21 | New Plan 34 on `feat/databricks-eval1` (pattern: Plan 31 for REVIEW_27). No `EXECUTION_PLAN_34.md` found on any remote branch at planning time. |
| D3 | 2026-10-21 | Also fix the two summary-only moderate findings: F4 (dataset) and F5 (scorers). |
| D4 | 2026-10-21 | F2: digit-edge boundaries on **all** keywords in `keywords_present`. A keyword whose comparison form starts with a digit must not be preceded by a digit; one that ends with a digit must not be followed by a digit. Anything else (including `.`) may follow, so `7 CFR Part 658` still matches `7 CFR § 658.5`. |
| D5 | 2026-10-21 | `EXECUTION_PLAN_33.md` is frozen history, outdated, and out of scope. Only the README is corrected: scope-aware prompt takes the next free number (`v3`), privacy section states the synthetic-only rule and explains why AGENT-level sanitization is unnecessary. |
| D6 | 2026-10-21 | Acceptance: targeted pytest + `ruff check`/`ruff format --check` (`--extend-ignore EXE002`) per task; at the end, full offline suite with the `eval-databricks` group and in an exact no-group env, plus one 5-case live T1 run on serverless. Scores are recorded, not gated; the live run must show non-null scorers. |

## Recon log (2026-10-21)

- Tree clean at `3db89a4`. Highest plan in `planning/` = 33.
- `eval/common/matching.py` (48 lines): `_CFR_UNIT` L12 rewrites `C.F.R. Part`/`§`/`Sec.` to `cfr `; `_keyword_form` L32; `keywords_present` L37-48 uses `in` substring (L47). Pi (`eval/run_evals.py`, `eval/test_agent_eval.py`) and `eval/databricks/scorers.py` all call it, so D4 changes all three harnesses.
- Dataset keywords with a digit edge (14): `7 CFR` (DISC-01, URBAN-01), `7 CFR Part 657`, `7 CFR Part 658` (RES-01), `AD-1006` (DISC-01, RES-02, PROMPT-04, LESA-02), `NRCS-CPA-106` (DISC-01, RES-02), `409406` (POINT-01), `412850` (MUKEY-01), `658.5(c)` (PROMPT-02), `160` (LESA-01). Note `_keyword_form("7 CFR")` = `"7 cfr "` (trailing space), so only its leading edge is a digit.
- `eval/common/dataset.py` (208 lines): `load_cases` L165; `cases = _read(Path(path)).get("test_cases", [])` L178, no type check; `validate_cases` L143 raises `ValueError` listing problems.
- `eval/databricks/scorers.py` (193 lines): `_matches_expected` L69-89, string-list branch L85-86 `sorted(str(item) for item in actual)`; `DETERMINISTIC_SCORER_NAMES` already exported (imported by runner tests); `deterministic_scorers` L156, `judge_scorers` L169 (6 judges: `Correctness`, `Guidelines(name="fppa_compliance")`, `ExpectationsGuidelines`, `ToolCallCorrectness`, `Safety`, `ToolCallEfficiency`), `build_scorers` L191. mlflow imported lazily inside builders.
- `eval/databricks/run_mlflow_eval.py` (201 lines): top-level `from scorers import build_scorers` L32; `run` L144; `build_scorers` L149 before `if args.dry_run` L152; `import mlflow` L156.
- `eval/databricks/test_databricks_runner.py`: module-level `pytest.importorskip("mlflow")` L15, so every runner test skips without the group. A no-mlflow dry-run test needs its own file.
- `eval/databricks/agent.py` (278 lines): `_sanitize` L69; TOOL spans L257-263; `@mlflow.trace(name="fpac_soil_agent", span_type="AGENT")` L274 on `predict` L275.
- `src/fpac_soil_mcp/privacy.py`: `sanitize_public_payload(payload: dict)` L133 drops keys in `PROHIBITED_PERSONAL_KEY_PATTERNS`, recursively; non-dict raises `TypeError`; strings pass through unchanged.
- `eval/databricks/test_databricks_agent.py`: `test_agent_calls_tool_then_answers_with_c4_trace` L121 (asserts root `AGENT`), `test_span_payloads_are_sanitized` L203 (TOOL only).
- `eval/databricks/README.md` (119 lines): usage L34 dry-run with `--group eval-databricks`; prompts L80-88 ("planned as v2 in D11" L87-88); Privacy L90-94.
- Last recorded gate (STATE_33, after D12): 462 tests with group, ruff clean. `3db89a4` added SDA tests since; re-record baseline before wave 1.
- Workspace recipe: `UV_PROJECT_ENVIRONMENT=/tmp/fpac-venv PYTHONDONTWRITEBYTECODE=1 uv run ... pytest -p no:cacheprovider`; ruff needs `--extend-ignore EXE002`. File writes only through `editAsset`. No sub-agent spawning on this surface: the orchestrator runs tasks inline, still writing each micro-TODO first.

## Shared contracts

- **K1 — `keywords_present(text, keywords) -> tuple[bool, list[str]]`** signature and return shape unchanged; the CFR unification of `_CFR_UNIT` unchanged; only the containment test gains D4 boundaries.
- **K2 — `scorer_names(judge_model: str | None = None) -> list[str]`** in `scorers.py`: pure (no mlflow import), returns names in the exact order `build_scorers` produces: `DETERMINISTIC_SCORER_NAMES` followed by the six judge names. A with-group test asserts `scorer_names() == [s.name for s in build_scorers("x")]`.
- **K3 — runner dry-run result** stays `{"records": [...], "scorer_names": [...]}`; non-dry-run behavior unchanged.
- **K4 — AGENT span**: `@mlflow.trace(name="fpac_soil_agent", span_type="AGENT")` stays unchanged. The decorator records the request string and the answer string automatically. The key-based sanitizer has nothing to strip from plain text, so no sanitize call is added (D1). A new test pins this shape: root inputs contain the request, root outputs contain the answer, and TOOL spans (which carry structured arguments) remain sanitized. `predict(request: str) -> str` signature unchanged.

## Hazards

- **H1** D4 touches all three harnesses through `keywords_present`. A previously passing case may now fail only if the answer glued a digit onto a keyword; the new test pins the 14 digit-edged dataset keywords.
- **H3** Dry-run without mlflow: `run_mlflow_eval.py` and its imports (`agent`, `scorers`, `common.dataset`) must stay mlflow-free at import time. Verify with an exact no-group env (`uv run --exact` without the group); plain `uv run` leaves group packages installed.
- **H4** `_matches_expected` strictness may flip `tool_arguments_within_tolerance` on live traces if the model sends numeric strings; the live run shows this.
- **H5** Privacy: T1 runs on synthetic/public cases only (D1). Live run uses the five ground-truth rows.
- **H6** Plan 33 artifacts are read-only.

## Wave table

| Wave | Theme | Task | Title | Depends on | Files (must edit / can create) |
|---|---|---|---|---|---|
| 1 | Shared helpers | 34.1.1 | Digit-boundary keyword matching | — | `eval/common/matching.py`, `eval/common/test_common_matching.py` |
| 1 | Shared helpers | 34.1.2 | Reject malformed `test_cases` | — | `eval/common/dataset.py`, `eval/common/test_common_dataset.py` |
| 2 | Databricks tier | 34.2.1 | Strict list scoring + `scorer_names` | wave 1 | `eval/databricks/scorers.py`, `eval/databricks/test_databricks_scorers.py` |
| 2 | Databricks tier | 34.2.2 | AGENT span documentation and pinning test | wave 1 | `eval/databricks/agent.py`, `eval/databricks/test_databricks_agent.py` |
| 3 | Runner + docs | 34.3.1 | Dry run without MLflow | 34.2.1 | `eval/databricks/run_mlflow_eval.py`; can create `eval/databricks/test_databricks_dry_run.py` |
| 3 | Runner + docs | 34.3.2 | README corrections | 34.2.2 | `eval/databricks/README.md` |
| 4 | Verification (LIVE, serial) | 34.4.1 | Full gates + 5-case live run | waves 1-3 | `planning/STATE_34.md` only |

Files are pairwise disjoint within every wave. Waves 1-3 are offline. Wave 4 is the only live step. Scratch output goes in `.development/` (untracked).

## Task specs

### 34.1.1 — Digit-boundary keyword matching

- **Repo:** fpac-soil-mcp · **Depends on:** none
- **Files in scope:** must edit `eval/common/matching.py`, `eval/common/test_common_matching.py`.
- **Spec:** Implement D4/K1. In `keywords_present`, replace the substring check with a compiled pattern per keyword form: `re.escape(form)`, prefixed with `(?<!\d)` when `form[0].isdigit()` and suffixed with `(?!\d)` when `form[-1].isdigit()`; search the haystack. Keep `_CFR_UNIT`, `_keyword_form`, `normalize_text`, `tool_matches` unchanged. Update the `keywords_present` docstring to state the boundary rule. Tests: negatives `7 CFR` vs `27 CFR Part 658`; `7 CFR Part 658` vs `7 CFR Part 6580`; `409406` vs `4094061`; `160` vs `1600`; `AD-1006` vs `AD-10060`. Positives: `7 CFR Part 658` vs `7 CFR § 658.5` and `7 C.F.R. 658`; `160` vs `score of 160.`; `658.5(c)` vs `§ 658.5(c)`. Add a parametrized test over every `expected_keywords` entry in the dataset with a digit edge: the keyword embedded in a sentence (`f"See {kw} here."`) still matches.
- **Constraints:** no new dependencies; do not touch Pi files or scorers.
- **Anchors:** `matching.py` `_CFR_UNIT` L12, `def keywords_present` L37, `missing = [` L47. Test file: existing CFR tests (grep `CFR`).
- **Reference:** existing CFR-equivalence tests in `test_common_matching.py`.
- **Acceptance:** `UV_PROJECT_ENVIRONMENT=/tmp/fpac-venv PYTHONDONTWRITEBYTECODE=1 uv run pytest -p no:cacheprovider eval/common/test_common_matching.py -q` passes; `uv run ruff check --extend-ignore EXE002 eval/common` and `uv run ruff format --check eval/common` pass.

### 34.1.2 — Reject malformed `test_cases`

- **Repo:** fpac-soil-mcp · **Depends on:** none
- **Files in scope:** must edit `eval/common/dataset.py`, `eval/common/test_common_dataset.py`.
- **Spec:** In `load_cases`, after `_read`, require the top-level value to be a dict with a `test_cases` key whose value is a list; otherwise raise `ValueError` with a message naming the path and the problem (`missing` vs `must be a list, got <type>`). Then make `validate_cases` report a non-dict row as an error (`row <index>: must be an object`) instead of crashing. Empty list stays valid. Tests: missing key, dict value, string value, non-dict row each raise `ValueError` with the expected message; the real dataset still loads.
- **Constraints:** do not change `to_mlflow_records`, `EXPECTATION_FIELDS`, or row-level field rules.
- **Anchors:** `def validate_cases` L143, `def load_cases` L165, `.get("test_cases", [])` L178.
- **Reference:** existing `ValueError` tests in `test_common_dataset.py` using `tmp_path` JSON files.
- **Acceptance:** `... pytest -p no:cacheprovider eval/common/test_common_dataset.py -q` passes; ruff check/format on `eval/common` pass.

### 34.2.1 — Strict list scoring and `scorer_names`

- **Repo:** fpac-soil-mcp · **Depends on:** wave 1 done
- **Files in scope:** must edit `eval/databricks/scorers.py`, `eval/databricks/test_databricks_scorers.py`.
- **Spec:** (F5) In `_matches_expected`, for an all-string `expected` list, return False unless every item of `actual` is a `str`; then compare sorted lists. (K2) Add module constant `JUDGE_SCORER_NAMES` (the six judge names in `judge_scorers` order) and pure `scorer_names(judge_model: str | None = None) -> list[str]` returning `[*DETERMINISTIC_SCORER_NAMES, *JUDGE_SCORER_NAMES]`. Before hard-coding judge names, read them from the installed MLflow 3.12 classes (`.name` of each constructed judge) and record them in the micro-TODO notes. Tests: `[1]` vs expected `["1"]` fails; `["b", "a"]` vs `["a", "b"]` passes; a mixed list fails; with mlflow, `scorer_names() == [s.name for s in build_scorers("databricks-claude-sonnet-4-5")]`. `scorer_names` must not import mlflow; the no-group run in 34.3.1 proves it.
- **Constraints:** no change to scorer semantics other than F5; `build_scorers` order unchanged.
- **Anchors:** `def _matches_expected` L69, string-list branch L85-86, `DETERMINISTIC_SCORER_NAMES`, `def judge_scorers` L169, `def build_scorers` L191.
- **Acceptance:** `... uv run --group eval-databricks pytest -p no:cacheprovider eval/databricks/test_databricks_scorers.py -q` passes; ruff on `eval/databricks/scorers.py` and its test pass.

### 34.2.2 — AGENT span documentation and pinning test

- **Repo:** fpac-soil-mcp · **Depends on:** wave 1 done
- **Files in scope:** must edit `eval/databricks/agent.py`, `eval/databricks/test_databricks_agent.py`.
- **Spec:** Implement K4 (D1). Do NOT change `@mlflow.trace` or the `predict` function body. Update the module docstring's tracing contract to state: the AGENT span records the plain-text request and answer via `@mlflow.trace`; this does not pass through `_sanitize` because the key-based policy has nothing to strip from plain text; TOOL spans carry structured arguments and continue to be sanitized; T1 must only be run on synthetic or public cases. Add `test_agent_span_shape_is_pinned`: run one scripted tool call via the existing `_run` helper, assert root span `name == "fpac_soil_agent"`, `span_type == "AGENT"`, that root span inputs contain the request string, root span outputs contain the final answer text, and that every TOOL span's `parent_id == root.span_id`. Also assert that TOOL spans are still sanitized (the existing `test_span_payloads_are_sanitized` covers this; the new test only checks the parent relationship). Keep `test_agent_calls_tool_then_answers_with_c4_trace` and `test_span_payloads_are_sanitized` green.
- **Constraints:** no changes to `@mlflow.trace`, `predict`, TOOL span behavior, `build_agent` signature, `chat_params`, or prompts. No value-level PII scrubbing (out of scope).
- **Anchors:** `def _sanitize` L69, `def build_agent` L203, `@mlflow.trace` L274, `def predict` L275; tests L121, L203.
- **Reference:** existing `test_agent_calls_tool_then_answers_with_c4_trace` L121 and `test_span_payloads_are_sanitized` L203.
- **Acceptance:** `... uv run --group eval-databricks pytest -p no:cacheprovider eval/databricks/test_databricks_agent.py -q` passes; ruff on both files passes.

### 34.3.1 — Dry run without MLflow

- **Repo:** fpac-soil-mcp · **Depends on:** 34.2.1
- **Files in scope:** must edit `eval/databricks/run_mlflow_eval.py`; can create `eval/databricks/test_databricks_dry_run.py`.
- **Spec:** (F3/K3) In `run`, compute `names = scorer_names(args.judge_model)` and return the dry-run result before any scorer construction; call `build_scorers` only on the live path (after the dry-run branch) and keep `scorer_names` used for `summarize_traces` equal to `[s.name for s in scorers]`. Change the top-level import to `from scorers import build_scorers, scorer_names`. Update the module docstring: dry run needs no optional group. New test file without `importorskip("mlflow")`: `run(["--dry-run"])` returns 5 ground-truth records and `scorer_names()`; `run(["--dry-run", "--all"])` returns all rows. It must pass both with and without the group.
- **Constraints:** do not edit `test_databricks_runner.py` (existing with-group dry-run tests must stay green); test basename must be unique repo-wide.
- **Anchors:** `from scorers import build_scorers` L32, `def run` L144, `build_scorers(args.judge_model)` L149, `if args.dry_run` L152.
- **Acceptance:** with group: `... uv run --group eval-databricks pytest -p no:cacheprovider eval/databricks/test_databricks_runner.py eval/databricks/test_databricks_dry_run.py -q` passes. Exact no-group env (separate `UV_PROJECT_ENVIRONMENT=/tmp/fpac-venv-nogroup`, `uv run --exact`): `pytest eval/databricks/test_databricks_dry_run.py -q` passes (not skipped). Ruff passes.

### 34.3.2 — README corrections

- **Repo:** fpac-soil-mcp · **Depends on:** 34.2.2 done (README wording follows the 34.3.1 spec, not its code)
- **Files in scope:** must edit `eval/databricks/README.md`.
- **Spec:** (F6) Replace "A scope-aware prompt (planned as v2 in D11) is deferred and will take the next free number." with wording that the scope-aware prompt is deferred and will be `v3`. (F1/D1) Privacy section: TOOL span payloads pass through `privacy.sanitize_public_payload`; the AGENT span records the plain-text request and answer via `@mlflow.trace`, which the key-based sanitizer cannot meaningfully act on, so it is not sanitized; T1 is for known synthetic or public cases only and must not be run on producer data. (F3) Usage: note that `--dry-run` works without the `eval-databricks` group (keep the existing command). No other edits.
- **Anchors:** dry-run usage L34; prompts L87-88; `## Privacy` L90-94.
- **Acceptance:** `grep -n "planned as" eval/databricks/README.md` returns nothing; `grep -n "v3" eval/databricks/README.md` and `grep -n "synthetic" eval/databricks/README.md` each return the new lines; ruff format check is not applicable.

### 34.4.1 — Full gates and 5-case live run (LIVE, serial)

- **Repo:** fpac-soil-mcp · **Depends on:** waves 1-3 done
- **Files in scope:** must edit `planning/STATE_34.md` only.
- **Spec:** Run serially: full offline suite with group; exact no-group suite; `ruff check . --extend-ignore EXE002`; `ruff format --check .`. Then one live T1 run on serverless with defaults (`--ground-truth`, v2 prompt, `databricks-gpt-5-6-luna` agent, `databricks-claude-sonnet-4-5` judge) via the notebook wrapper `eval/databricks/run_t1_eval_notebook.py` or `run([])`. Record run id, per-scorer pass/fail/null counts, and compare with STATE_33 D12 run `bc2e4bee`. Inspect one trace: AGENT span inputs contain the request, outputs contain the answer, TOOL spans are children. Pass bar (D6): no offline regressions vs baseline; judge scorers non-null on all 5 rows; scores recorded, not gated.
- **Constraints:** no code edits; failures go back to the owning task via the escalation ladder.
- **Acceptance:** STATE_34 wave-gate row and 34.4.1 report filled with exact commands, counts, and run id.
