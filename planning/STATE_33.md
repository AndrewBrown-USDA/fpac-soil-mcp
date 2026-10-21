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
| 5 | 33.5.1 | T1 agent loop with tracing | pending | | |
| 5 | 33.5.2 | T1 scorers | pending | | |
| 6 | 33.6.1 | T1 runner, notebook, 5-case serverless check (LIVE step) | pending | | |
| 6 | 33.6.2 | Documentation and Make target | pending | | |

## Wave gates

| Wave | Offline pytest | ruff check | ruff format | eval-databricks tests | Notes |
|---|---|---|---|---|---|
| 1 | 395 passed, 1 skipped, 22 deselected | pass (EXE002 ignored) | 390 formatted | n/a | +19 tests |
| 2 | 407 passed, 1 skipped, 22 deselected | pass (EXE002 ignored) | 393 formatted | n/a | +12 T0 tests |
| 3 | 429 passed, 1 skipped, 22 deselected | pass (EXE002 ignored) | 396 formatted | n/a | +22 dataset tests |
| 4 | 429 passed, 1 skipped, 22 deselected | pass (EXE002 ignored) | 396 formatted | n/a | user sign-off: approved 2026-10-21 (with POINT-01 county + 413100 corrections) |
| 5 | | | | | |
| 6 | | | | | T1 run ID / experiment / per-scorer counts: |

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
