# State 33 — Databricks-Native Eval Tier (T0 + T1)

Plan: `planning/EXECUTION_PLAN_33.md` · Template: `planning/PROMPT_TEMPLATE_33.md` · Branch: `feat/databricks-eval1`

## Baseline (record before wave 1)

- [x] Branch is `feat/databricks-eval1` (HEAD 7b281cb); staged research note, office-hours questions, and Plan 33 artifacts committed (`docs(planning):`).
- [x] Offline suite (2026-10-21, serverless, `UV_PROJECT_ENVIRONMENT=/tmp/fpac-venv`): **376 passed, 1 skipped, 22 deselected**. The repo `.venv` on `/Workspace` is not used; set `UV_PROJECT_ENVIRONMENT=/tmp/fpac-venv PYTHONDONTWRITEBYTECODE=1` and pass `-p no:cacheprovider`.
- [x] `uv run ruff check .` → 59 × EXE002 only (Workspace FS reports every file as executable; not a code defect). `uv run ruff check . --extend-ignore EXE002` → All checks passed. Wave gates use `--extend-ignore EXE002` on Workspace.
- [x] `uv run ruff format --check .` → 385 files already formatted
- [ ] Pi live baseline (laptop, optional): `make test-eval` → ___ / 20 PASS
- [x] Serverless facts re-confirmed: MLflow 3.12.0 installed; endpoints `databricks-gpt-5-6-luna`, `databricks-claude-sonnet-4-5` READY

## Wave board

| Wave | Task | Title | Status | Worker | Result |
|---|---|---|---|---|---|
| 1 | 33.1.1 | Common matching, pytest path, eval-databricks group | done | orchestrator (inline) | 073fe5e |
| 1 | 33.1.2 | Dataset encoding repair, manifest wording | done | orchestrator (inline) | 25d7570 |
| 2 | 33.2.1 | Pi harness alignment | done | orchestrator (inline) | 1e10e6d |
| 2 | 33.2.2 | T0 contract tests | done | orchestrator (inline) | 0818300 |
| 3 | 33.3.1 | Dataset v2 schema and loader | done | orchestrator (inline) | 85a8077 |
| 4 | 33.4.1 | Ground truth for five rows (LIVE, user sign-off) | done | orchestrator (inline) | signed off 2026-10-21 |
| 5 | 33.5.1 | T1 agent loop with tracing | done | orchestrator (inline) | 431b89a |
| 5 | 33.5.2 | T1 scorers | done | orchestrator (inline) | 8787a65 |
| 6 | 33.6.1 | T1 runner, notebook, 5-case serverless check (LIVE step) | done | orchestrator (inline) | 274b540; run 69535e209a0c4e1dbb7b6bd79ad40c19 |
| 6 | 33.6.2 | Documentation and Make target | done | orchestrator (inline) | c2b8fd9 |

## Wave gates

| Wave | Offline pytest | ruff check | ruff format | eval-databricks tests | Notes |
|---|---|---|---|---|---|
| 1 | 395 passed, 1 skipped, 22 deselected | pass (EXE002 ignored) | 390 formatted | n/a | +19 tests |
| 2 | 407 passed, 1 skipped, 22 deselected | pass (EXE002 ignored) | 393 formatted | n/a | +12 T0 tests |
| 3 | 429 passed, 1 skipped, 22 deselected | pass (EXE002 ignored) | 396 formatted | n/a | +22 dataset tests |
| 4 | 429 passed, 1 skipped, 22 deselected | pass (EXE002 ignored) | 396 formatted | n/a | user sign-off: approved 2026-10-21 (with POINT-01 county + 413100 corrections) |
| 5 | 443 passed, 1 skipped, 22 deselected | pass (EXE002 ignored) | 403 formatted | 14 passed; exact no-group env: 2 skipped | +14 T1 tests |
| 6 | 448 passed, 1 skipped, 22 deselected (with group); exact no-group env: 429 passed, 4 skipped | pass (EXE002 ignored) | 409 formatted | 19 passed | +5 runner tests. T1 run `69535e209a0c4e1dbb7b6bd79ad40c19`, experiment `/Users/andrew.g.brown@usda.gov/fpac-soil-mcp-eval`; counts in 33.6.1 report |

Pre-merge manual: Pi live `make test-eval` on laptop → ___

## Task reports

<!-- Workers append `## <task-id>` sections here (<=15 lines each). -->

Execution note: this environment has no sub-agent spawning, so the orchestrator executes each task inline, still writing the micro-TODO and self-reviewing it against the spec before editing code.

## 33.1.1

Status: done (073fe5e)
Changes:
- eval/common/__init__.py, matching.py (C1: normalize_text, tool_matches, keywords_present), test_common_matching.py (19 tests)
- pyproject.toml: `eval-databricks` group; `pythonpath = ["eval"]`
- uv.lock: +mlflow/databricks-sdk[openai] tree; only resolution-marker rewrites to existing entries; all sources pypi.org
Validation:
- pytest eval/common/test_common_matching.py: 19 passed; `uv lock --check`: ok; default `uv sync` has no mlflow
Deviations:
- Spec example `point` vs `..._by_point` would match under C1 suffix semantics; tests use extended-name and no-boundary non-matches instead.
Gotchas for dependents:
- Import as `from common.matching import ...` (pytest path); scripts must put `eval/` on sys.path.

## 33.1.2

Status: done (25d7570)
Changes:
- eval/prompt_test_cases.json: 4 x `\u00c2\u00a7` -> `\u00a7` (URBAN-01, CORR-01, PROMPT-02, LESA-01); version still 1.0.0
- manifest.yaml L40: "all 10 tools"
Validation:
- acceptance python check: ok; `grep -c 'all 10 tools' manifest.yaml`: 1; eval/test_agent_eval.py: 33 passed, 2 deselected (unchanged)
Deviations: none
Gotchas for dependents: none

## 33.2.1

Status: done (1e10e6d)
Changes:
- eval/run_evals.py: import `normalize_text`, `tool_matches` from `common.matching`; local `normalize_text` and `unicodedata` removed; `_tool_matches = tool_matches`; summary is Passed/Failed only
- eval/test_agent_eval.py: local `normalize_text`, `extract_structured_tool_names`, `extract_assistant_content` deleted, imported from `run_evals` (H3 diff: comments/formatting only); coverage test asserts all 10 manifest tools
Validation:
- pytest eval/test_agent_eval.py eval/common: 52 passed, 2 deselected; `-m agent_eval -k schema_and_completeness`: 1 passed
- `grep -c 'def normalize_text'`: 0/0; `grep -n WARN eval/run_evals.py`: empty; `run_evals.py --help`: exit 0
Deviations: none
Discovered:
- `test_prompt_dataset_schema_and_completeness` is `@pytest.mark.agent_eval`, so it is deselected offline; T0 covers manifest equality offline. Consider unmarking it later (needs no Pi).

## 33.2.2

Status: done (0818300)
Changes:
- eval/contract/test_contract.py: 12 offline tests (manifest parity, input schemas, notices, mocked point/mukey, invalid inputs with zero SDA requests, regulatory-notice resource)
Validation:
- pytest eval/contract/test_contract.py: 12 passed; negative check `test_manifest_parser_detects_a_missing_tool` proves a dropped tool makes the sets unequal
Deviations:
- Spec item 3 assumed `list_farmland_classes` returns `regulatory_notice`; it returns `FarmlandClassListResponse(source, authority, classes)`. It is a reference listing, not a soil query, so the test asserts `authority`/`classes` instead.
Discovered:
- Decide whether `list_farmland_classes` should also carry `regulatory_notice` (source change, out of scope).

## 33.3.1

Status: done (85a8077)
Changes:
- eval/common/dataset.py: `load_cases`, `validate_cases`, `to_mlflow_records` (C2/C3), plus `dataset_version()` and `SYNTHETIC_TOOLS`
- eval/common/test_common_dataset.py: 22 tests (checked-in file, filters, C3 shape, 15 error paths, duplicates)
Validation:
- pytest eval/common: 41 passed
Deviations:
- Added `dataset_version(path)` for the C5 `dataset_version` tag.
Gotchas for dependents:
- `expected_tool_calls` names must be in `expected_tools` only when that list is non-empty; `read_resource`/`get_prompt` are always allowed (RES-01).
- `load_cases(ids=...)` raises on unknown ids; whole file is validated before filtering.

## 33.4.1

Status: done (user signed off 2026-10-21)
Changes:
- eval/prompt_test_cases.json: version 2.0.0; v2 fields on DISC-01, POINT-01, MUKEY-01, INTERP-01, RES-01 (verified_on 2026-10-21); only v1 change is the user-approved POINT-01 county wording
Validation:
- live calls via in-memory FastMCP client (2026-10-21): point (41.8781, -93.0977), mukey 412850, interpretations [412850, 412851, 413100], mukey 413100, explain_fppa_screening_scope, fppa://regulatory-notice
- `load_cases(ground_truth_only=True)`: 5; pytest eval: 86 passed, 2 deselected
Findings for sign-off:
- POINT-01 areasymbol is IA127 (Marshall County, FIPS 19127), not Story (IA169). Per user direction, `user_prompt` now says "Marshall County, IA" (v1-field change, user-approved) and QUICKSTART.md L72 matches; coordinates unchanged so Pi argument tests are unaffected.
- mukey 413100 is intentionally unmapped (tests missing-data handling, per user). Fact and a second INTERP-01 guideline require the response to report it as missing without inventing a rating.
- NCCPI `numeric_rating` is a string in tool output; numeric scorer must coerce. Path `result[i]` because list returns are wrapped as `{"result": [...]}`.
Deviations:
- No `.development/` script committed; live queries were run as an ad hoc session script.
- QUICKSTART.md edited (outside listed scope) to keep the docs prompt consistent with the dataset; user-directed.

## 33.5.1

Status: done (431b89a)
Changes:
- eval/databricks/agent.py (C4): `build_agent`, `available_prompt_versions`, `load_system_prompt`, `chat_params`; synthetic `read_resource`/`get_prompt`; sanitized TOOL spans; thread fallback copies contextvars
- eval/databricks/prompts/system_prompt_v1.txt: screening role + `[forced-tool]` block
- eval/databricks/test_databricks_agent.py: scripted fake client tests
Validation:
- `uv run --group eval-databricks pytest eval/databricks/test_databricks_agent.py`: pass; exact no-group env: skipped
Deviations:
- `chat_params` adds `reasoning_effort="none"` for `gpt-5*`: `databricks-gpt-5-6-luna` rejects function tools on Chat Completions otherwise (probed live).
Gotchas for dependents:
- `%pip install -e .` does not install the group; the 33.6.1 notebook must also install `databricks-sdk[openai]` (MLflow is preinstalled on serverless).
- Coordinates are not stripped by `sanitize_public_payload`, so argument scoring works on spans.

## 33.5.2

Status: done (8787a65)
Changes:
- eval/databricks/scorers.py: `required_tools_called`, `keywords_present`, `numeric_within_tolerance` (coerces numeric strings), `tool_arguments_within_tolerance` (1e-4; string lists order-insensitive; extra args ignored), `resolve_path`, `build_scorers`
- eval/databricks/test_databricks_scorers.py: pass/fail/skip per scorer over C4 traces, names, temperature
Validation:
- `uv run --group eval-databricks pytest eval/databricks/test_databricks_scorers.py`: pass
Deviations: none. All six judges accept `inference_params={"temperature": 0}` on MLflow 3.12.0 and 3.17.1 (D11 fully applied).
Gotchas for dependents:
- Deterministic scorers return `None` when their expectation key is absent, so `numeric_within_tolerance` is null on 4 of the 5 ground-truth rows (only INTERP-01 has numerics). D8 "every scorer non-null on all 5 rows" must be read as "non-null where the expectation applies"; 33.6.1 should report this, not fail on it.

## 33.6.1

Status: done (274b540)
Changes:
- eval/databricks/run_mlflow_eval.py (C5): self-inserts `eval/` + `eval/databricks/` on sys.path; git tags via `subprocess.run(cwd=repo)`; tagged `mlflow.start_run` wrapping `genai.evaluate`; `summarize_traces` counts pass/fail/null from trace assessments (works on MLflow 3.12 and 3.17); default experiment from `current_user.me()`
- run_t1_eval_notebook.py: `%pip` repo + `databricks-sdk[openai]`, shapely reinstall, `restartPython()`, cwd-relative paths; test_databricks_runner.py: 5 tests (dry-run 5/2/20 records, summary counts, git tags)
Live (serverless, mlflow-skinny 3.12.0, 71 s): run `69535e209a0c4e1dbb7b6bd79ad40c19`, tags git_sha 1ac0cb5 / feat/databricks-eval1 / v1 / 2.0.0. pass/fail/null:
- required_tools_called 4/0/1 (RES-01 n/a), keywords_present 4/1/0, numeric_within_tolerance 1/0/4, tool_arguments_within_tolerance 4/0/1, correctness 3/2/0, fppa_compliance 5/0/0, expectations_guidelines 5/0/0, tool_call_correctness 2/3/0, safety 5/0/0, tool_call_efficiency 1/4/0
- Findings: POINT-01 fails keywords + correctness; INTERP-01 fails correctness; agent appends an extra `read_resource` on 4/5 rows (drives efficiency/tool-correctness misses). Every scorer non-null wherever its expectation applies (D8 as read in 33.5.2).
Deviations:
- Live step ran the notebook's cells in a serverless Python session (no notebook-run tool here); editable install needed `src/` on sys.path because that session cannot restart Python (the notebook's `restartPython()` covers this).
- First attempt (run 26924507433b4231a8359804857778ab) hit the SDA daily maintenance window (12:30-12:45 AM CT); discard it.
Discovered:
- `SDAClient` raises a raw `JSONDecodeError` when SDA returns its HTML maintenance page with HTTP 200; should map to an explicit service-unavailable error (source change, out of scope).
- Tune system prompt v2 to avoid the redundant `read_resource` call.

## 33.6.1 follow-up (post-wave, user-directed)

Status: done (0713eb7)
Changes:
- eval/prompt_test_cases.json -> 2.0.1: POINT-01 keyword `mukey` -> `409406`; POINT-01 fact IA127 -> "in Marshall County, IA" (prompt never asks for the survey area); INTERP-01 413100 fact drops the unknowable cause (guideline already covers no-invention)
- eval/common/test_common_dataset.py: version check accepts any 1.x/2.x
Live rerun: run `b7d7dfd512dc47bab0d8f116e8109373` (git_sha 0713eb7, dataset 2.0.1). correctness 5/0/0 (was 3/2); POINT-01 keywords now pass; other scorers unchanged.
- New keyword miss: RES-01 `7 CFR Part 658` (agent wrote "7 CFR § 658.5" / "§ 658.2(a)"; passed in the prior run). Phrasing variance, not a data error; candidate for a normalization or keyword change.
- Resolved (e4fbe01): `common.matching.keywords_present` treats `CFR Part N`, `CFR § N.x`, `CFR §§`, `Sec.`/`section`, `C.F.R.` as the same title+part; Pi's two inline keyword checks (`run_evals.py`, `test_agent_eval.py` point test) now call it, so Pi and T1 share one matcher. +13 matching tests; offline 461 passed. Rerun `5afdedd4796b475cb05466f94048c345`: keywords_present 5/0/0, correctness 5/0/0, tool_call_correctness 4/1/0 (judge variance), tool_call_efficiency still 1/4 (extra `read_resource`).

## D12 — v2 system prompt (post-wave, user-directed)

Status: done (c6a6ee7)
Changes:
- prompts/system_prompt_v2.txt: v1 minus line 7 ("Use read_resource … fppa://regulatory-notice"); v1 kept for comparison.
- agent.py: DEFAULT_PROMPT_VERSION = "v2"; load_system_prompt and build_agent default to it.
- run_mlflow_eval.py: --system-prompt-version default reads the same constant.
- test_databricks_agent.py: +1 test asserting v2 is default and differs by one line; C4 trace test expects v2.
- README.md: documents v2 as default and the reason for the change.
- EXECUTION_PLAN_33.md: D12 recorded.
Gate: 462 passed, 1 skipped, 22 deselected; ruff clean.
Comparison runs (same dataset 2.0.1, same agent/judge, same 5 ground-truth rows):
- v1 `671575f4939244c39b8ca1d462343d9d` (79s): `read_resource` appended on 4/5 rows (all except RES-01). tool_call_efficiency 1/4, tool_call_correctness 1/4.
- v2 `bc2e4bee68594f4a8c809b6961d1c2b8` (59s): no spurious `read_resource`. tool_call_efficiency **5/0**, tool_call_correctness **5/0**.
- All other scorers identical between runs: correctness 5/0, fppa_compliance 5/0, expectations_guidelines 5/0, safety 5/0, keywords_present 5/0.
- Root cause confirmed: v1 line 7 naming the URI triggered GPT-5 to fetch it on every row.

## 33.6.2

Status: done (c2b8fd9)
Changes:
- eval/databricks/README.md (new): components, CLI flags, notebook, prompt versioning, privacy, scoring nulls, SDA maintenance note, deferred T2
- README.md eval section: three tiers; AGENTS.md Find Things + Validate; Makefile `eval-databricks` target in `.PHONY` and help
Validation: `make help` lists `eval-databricks`; ruff check/format pass; referenced paths exist
Deviations: removed draft reference to nonexistent `eval_auth.py`; privacy wording narrowed to what `sanitize_public_payload` actually does.
