# Execution Plan 33 — Databricks-Native Eval Tier (T0 + T1)

## Goal & Scope

### Goal

Extend the fpac-soil-mcp evaluation workflow to Databricks as proposed in `planning/RESEARCH_DATABRICKS_EVAL_INTEGRATION.md`: keep the Pi CLI harness as the local smoke test, fix its known defects, and add a Databricks-native tier built on MLflow 3.12 — deterministic T0 contract checks over the in-memory FastMCP client, a backward-compatible v2 shared dataset with verified ground truth, and a T1 in-process agent eval (in-memory FastMCP server + Databricks foundation model endpoint, traced and scored with MLflow) that runs on serverless without a service principal.

### In scope (research note rollout steps 1-4)

- Step 1: fix Pi harness defects 2.4.1-2.4.4 (mojibake, 9-vs-10 tool coverage, dead/double-counted `WARN`, duplicated parsing).
- Step 2: T0 contract tests in `eval/contract/` (default offline suite).
- Step 3: `prompt_test_cases.json` v2 schema + loader in `eval/common/`; ground truth for POINT-01, MUKEY-01, INTERP-01, DISC-01, RES-01.
- Step 4: T1 agent loop, scorers, runner, and notebook under `eval/databricks/`; 5-case serverless pipeline check.
- Note sections adopted: 6.1, 6.2, 6.4 (cut in decision D9), 7, 8 (privacy, environment, run tagging), 9 (layout).

### Out of scope (explicit deferrals)

- Step 5: scheduled serverless Lakeflow Job for T1 (needs a Jobs-page handoff; later orchestration).
- Step 6: T2 deployed-app eval and `eval/databricks/eval_auth.py` (blocked on Q2; Unity Gateway MCP services return 403 per `planning/OFFICE_HOURS_QUESTIONS.md`).
- Step 7: dataset expansion to 50+ rows, scope-refusal rows, SME labeling session.
- MLflow prompt registry (`register_prompt`/`load_prompt`) and v2 scope-aware system prompt.
- UC-backed MLflow evaluation dataset sync and UC trace storage (blocked on Q3).
- LESA ground truth (blocked on Q4; observed run-to-run variance).
- Open questions Q1-Q4 remain open; nothing here depends on their answers.
- The template's `mcp-eval` skill (Phoenix/LangChain harness): not vendored or adapted (D10).
- Phoenix setup: handled separately, outside this orchestration (D10).
- USAI gateway / `USAI_API_KEY`: not permitted; all model access uses Databricks foundation model endpoints (D10).

### Verbatim constraints from the user

- "i'd like to stick to the note and not necessarily rely on any of the existing Pi harness"
- "yes, pi can be switched to import from common"
- AGENTS.md: "Preserve the preliminary-screening limitation in every soil-query response"; "Do not make live network tests part of the default offline test path"; "Enforce Section 1619 and coordinate privacy protections via `privacy.py`".

## Decision log

| ID | Date | Decision |
|---|---|---|
| D1 | 2026-10-20 | Orchestration 33 = rollout steps 1-4. Steps 5, 6, 7 deferred. |
| D2 | 2026-10-20 | T1 deps live in a new `eval-databricks` dependency group (`mlflow>=3.12,<4`, `databricks-sdk[openai]>=0.122`), not in `dev`. `uv.lock` regenerated once against the pinned PyPI index. Imports of `mlflow`/`openai`/`databricks.sdk` are lazy; their tests use `pytest.importorskip`. Notebook installs with `%pip install -e .` and relies on preinstalled MLflow. |
| D3 | 2026-10-20 | Agent default `databricks-gpt-5-6-luna`; judge default `databricks-claude-sonnet-4-5`; both overridable; `databricks-claude-haiku-4-5` optional second agent run. Q1 recorded as a Pi-vs-T1 comparability caveat. |
| D4 | 2026-10-20 | Follow the note's layout: `eval/common/`, `eval/contract/`, `eval/databricks/`. The Databricks tier must not import `run_evals` or `test_agent_eval`. |
| D5 | 2026-10-20 | `eval/common/matching.py` is new harness-neutral code (`normalize_text`, `tool_matches`, `keywords_present`). Pi switches to importing these from `common`. Pi event parsers stay Pi-only in `run_evals.py`; `test_agent_eval.py` drops its duplicate parsers and imports them from `run_evals`. Dependency direction: Pi -> common <- databricks; common imports neither. |
| D6 | 2026-10-20 | Ground truth for POINT-01, MUKEY-01, INTERP-01, DISC-01, RES-01, each with `verified_on` and `live_data_sensitive: true`. Same five rows drive the T1 5-case check. Ground-truth task acceptance = user sign-off on recorded values. |
| D7 | 2026-10-20 | Reuse Plan 32 worker rules (default worker models; escalate to mid-tier only on block/failure; max 3 concurrent workers; shared files serialized). Live-service tasks (33.4.1, the live step of 33.6.1) run serially, never concurrently. |
| D8 | 2026-10-20 | Per-wave gate: offline pytest + `ruff check` + `ruff format --check`, test count non-decreasing, no regressions; MLflow tests skip where the group is absent. T1 wave adds a 5-case serverless notebook run with all scorers non-null and run ID + per-scorer counts recorded in STATE. Scores are findings, not gates. Full 20-case run optional. Pi live run is a manual laptop check before merge. |
| D9 | 2026-10-20 | Scorers in: deterministic (tools called, keywords, numeric tolerance, argument tolerance), `Correctness`, `Guidelines` compliance, `ToolCallCorrectness`, `Safety`, `ToolCallEfficiency` (last two non-gating). `read_resource`/`get_prompt` exposed as agent tools. `force_tool_use` schema field in, scope rows deferred. Traces sanitized through `privacy.py`. Runs tagged `git_sha` + `git_branch`. Prompt registry and UC dataset sync deferred. |
| D10 | 2026-10-20 | Do not bring over or use the template `mcp-eval` skill. Phoenix setup is addressed separately. USAI API key/gateway is a no-go. |
| D11 | 2026-10-20 | Adopt two methods directly (no skill): `temperature=0` for the agent and for judges where the judge API supports it; file-based versioned system prompts at `eval/databricks/prompts/system_prompt_v{n}.txt`, selected by `--system-prompt-version` (default `v1`) and logged as a run tag. Only v1 (forced-tool) ships; v2 scope-aware prompt waits for scope rows; MLflow prompt registry stays deferred. |

## Recon log (facts)

- Branch `feat/databricks-eval1`; `planning/RESEARCH_DATABRICKS_EVAL_INTEGRATION.md` and `planning/OFFICE_HOURS_QUESTIONS.md` staged, uncommitted. Highest prior plan: 32.
- Research note line cites [S1]/[S2] are stale: `eval/run_evals.py` is 948 lines, `eval/test_agent_eval.py` 1274 lines (post PR #22). Use the grep anchors below, never the note's line numbers.
- Dataset has **20** cases (note says 21): DISC-01/02, POINT-01/02, MUKEY-01, POLY-01/02, URBAN-01, INTERP-01, CORR-01/02, RES-01..03, PROMPT-01..04, LESA-01/02. Fields: `id, category, target_type, target_name, user_prompt, expected_tools, expected_keywords, sample_geometry`. Version `1.0.0`.
- Mojibake `\u00c2\u00a7` present in 4 `user_prompt` values (JSON lines ~180, ~235, ~349, ~387: URBAN-01, CORR-01, PROMPT-02, LESA-01).
- `test_prompt_dataset_schema_and_completeness` (~L1149) lists 9 tools, omits `calculate_preliminary_lesa`. `manifest.yaml` L40 says "all 9 tools"; manifest lists 10 tools, 3 resources, 4 prompts.
- `run_evals.py` summary (~L936-937): `WARN` counted in both `warned` and `failed`; nothing sets `WARN`.
- `test_agent_eval.py` already `import run_evals` (L22) but re-defines `normalize_text` (L36), `extract_structured_tool_names` (~L690), `extract_assistant_content` (~L803); `extract_tool_calls` (~L828) exists only there. The test-local `extract_structured_tool_names` may differ from `run_evals.py` (~L262-369) — diff before deleting.
- Pi-side generic helpers: `run_evals.normalize_text` (~L251), `run_evals._tool_matches` (~L506, suffix `_name`/`:name`).
- Import mechanics: `eval/` has no `__init__.py`; pytest rootdir insertion puts `eval/` on `sys.path` for `eval/*.py` tests only. `python eval/run_evals.py` puts `eval/` on `sys.path[0]`. Subfolders need `pythonpath = ["eval"]` in `[tool.pytest.ini_options]`; test basenames must be unique repo-wide (no `__init__.py` in test dirs).
- `uv.lock` pins FastMCP 4.1.1. Verified API: `async with fastmcp.Client(server) as c` with `list_tools()`, `call_tool(name, args)` -> `CallToolResult(content, data, is_error, meta, structured_content)`, `list_resources()`, `read_resource(uri)`, `list_prompts()`, `get_prompt(name, args)`. Use `tool.input_schema` (`inputSchema` is deprecated). Client is async-only.
- Tools build `SDAClient()` inline; offline tests patch `fpac_soil_mcp.tools.soil_tools.SDAClient` (pattern: `tests/test_tools.py` L41). `tests/conftest.py` has `mcp_server` fixture (`create_mcp_server()`) and SDA mock payloads.
- Regulatory text: `constants.REGULATORY_NOTICE`, `REGULATORY_LIMITATIONS`, `CITATIONS`; response models carry `regulatory_notice` fields.
- Privacy: `privacy.sanitize_public_payload(payload: dict) -> SanitizationResult`, `validate_public_payload`, `assert_public_payload`.
- Serverless facts: MLflow 3.12.0 preinstalled; `pi`/`npm` absent; `fastmcp`, `openai` not importable by default; endpoints `databricks-gpt-5-6-luna`, `databricks-claude-sonnet-4-5`, `databricks-claude-haiku-4-5` exist. Serverless needs a shapely 2.2.0 reinstall (project memory).
- Offline test baseline could not be run from the Workspace FS (`OSError: [Errno 95]` writing `__pycache__` in `.venv`). Record baseline before wave 1 with `PYTHONDONTWRITEBYTECODE=1 uv run pytest -p no:cacheprovider -m "not live_network"` or on the laptop. Last recorded: 327 passed, 22 deselected (Plan 31).
- Relevant ADRs: 0001 (FastMCP layout), 0003 (screening authority boundary), 0010 (public payload PII sanitization), 0011 (mocked default, live opt-in).

## Shared contracts (all tasks must honor)

**C1 — matching API** (`eval/common/matching.py`): `normalize_text(text: str) -> str` (same semantics as `run_evals.normalize_text`); `tool_matches(expected: str, called: Iterable[str]) -> bool` (exact or suffix `_expected` / `:expected`); `keywords_present(text: str, keywords: Iterable[str]) -> tuple[bool, list[str]]` (case-insensitive over normalized text; returns missing keywords).

**C2 — dataset v2** (`eval/prompt_test_cases.json`, `"version": "2.0.0"`): every v1 field unchanged. Optional per-row additions:

- `expected_tool_calls: [{"name": str, "arguments"?: object}]`
- `expected_facts: [str]`
- `numeric_expectations: [{"tool": str, "path": str, "value": number, "abs_tol": number}]` — `path` is dot/bracket path into the TOOL span output `result` (C4).
- `guidelines: [str]`
- `force_tool_use: bool` (default `true`)
- `live_data_sensitive: bool` (default `false`)
- `verified_on: "YYYY-MM-DD"` (present only on ground-truth rows)

**C3 — MLflow record shape** (`eval/common/dataset.py::to_mlflow_records(cases)`): `{"inputs": {"request": user_prompt}, "expectations": {"case_id", "expected_tools", "expected_keywords", and each present v2 field: "expected_tool_calls", "expected_facts", "numeric_expectations", "guidelines"}}`. Empty/absent v2 fields are omitted from `expectations`.

**C4 — agent trace shape** (`eval/databricks/agent.py`): root span `span_type="AGENT"`; one child span per dispatch with `span_type="TOOL"`, span name = the tool name exposed to the model, inputs = the argument dict, outputs = `{"result": <structured_content if not None else data else joined text content>, "is_error": bool}`. Synthetic tools: `read_resource(uri: str)` and `get_prompt(name: str, arguments: object = {})`. Chat calls use `temperature=0`. System prompt text is loaded from `eval/databricks/prompts/system_prompt_{version}.txt` (D11). Span inputs/outputs pass through `privacy.sanitize_public_payload` before being recorded. `predict(request: str) -> str` returns final assistant text.

**C5 — runner CLI** (`eval/databricks/run_mlflow_eval.py`): `--cases ID,ID` | `--ground-truth` (default: rows with `verified_on`) | `--all`; `--model` (default `databricks-gpt-5-6-luna`); `--judge-model` (default `databricks-claude-sonnet-4-5`); `--experiment` (default `/Users/<current user>/fpac-soil-mcp-eval`); `--max-workers` (default 1, sets `MLFLOW_GENAI_EVAL_MAX_WORKERS`); `--max-turns` (default 8); `--system-prompt-version` (default `v1`; choices = files present in `eval/databricks/prompts/`); `--dry-run` (build records + scorers, no model calls). Callable as `run(argv: list[str] | None)` for notebooks.

## Wave / dependency table

| Wave | Theme | Tasks | Depends on | Parallelism |
|---|---|---|---|---|
| 1 | Foundation | 33.1.1 common matching + pytest path + dep group; 33.1.2 dataset encoding + manifest text | baseline | 2 parallel (disjoint) |
| 2 | Harness alignment + T0 | 33.2.1 Pi harness alignment; 33.2.2 T0 contract tests | 33.1.1, 33.1.2 | 2 parallel (disjoint) |
| 3 | Dataset schema | 33.3.1 v2 schema + loader | 33.1.1, 33.1.2 | 1 |
| 4 | Ground truth (live, serial) | 33.4.1 verified values for 5 rows | 33.3.1 | 1, serial live |
| 5 | T1 components | 33.5.1 agent loop + tracing; 33.5.2 scorers | 33.1.1, 33.3.1 (33.4.1 for 33.5.2 fixtures) | 2 parallel (disjoint) |
| 6 | T1 runner + docs | 33.6.1 runner + notebook + live 5-case run; 33.6.2 docs | 33.5.1, 33.5.2, 33.4.1 | 2 parallel; live step serial |

File ownership per wave (pairwise disjoint within each wave):

| Wave | Task | Must edit | Can create |
|---|---|---|---|
| 1 | 33.1.1 | `pyproject.toml`, `uv.lock` | `eval/common/__init__.py`, `eval/common/matching.py`, `eval/common/test_common_matching.py` |
| 1 | 33.1.2 | `eval/prompt_test_cases.json`, `manifest.yaml` | — |
| 2 | 33.2.1 | `eval/run_evals.py`, `eval/test_agent_eval.py` | — |
| 2 | 33.2.2 | — | `eval/contract/test_contract.py` |
| 3 | 33.3.1 | — | `eval/common/dataset.py`, `eval/common/test_common_dataset.py` |
| 4 | 33.4.1 | `eval/prompt_test_cases.json` | `.development/ground_truth_33.py` (untracked) |
| 5 | 33.5.1 | — | `eval/databricks/agent.py`, `eval/databricks/test_databricks_agent.py`, `eval/databricks/prompts/system_prompt_v1.txt` |
| 5 | 33.5.2 | — | `eval/databricks/scorers.py`, `eval/databricks/test_databricks_scorers.py` |
| 6 | 33.6.1 | — | `eval/databricks/run_mlflow_eval.py`, `eval/databricks/run_t1_eval_notebook.py`, `eval/databricks/test_databricks_runner.py` |
| 6 | 33.6.2 | `README.md`, `AGENTS.md`, `Makefile` | `eval/databricks/README.md` |

## Hazards

- **H1 stale anchors:** never trust research-note line numbers; use the grep anchors in each spec.
- **H2 import path:** after 33.1.1, `eval/` is on pytest's path; do not add `__init__.py` to `eval/`, `eval/contract/`, or `eval/databricks/`. `eval/common/` is the only package. Keep test basenames unique.
- **H3 parser drift:** `test_agent_eval.py`'s copies of `extract_structured_tool_names`/`extract_assistant_content` may differ from `run_evals.py`. 33.2.1 must diff first; `run_evals.py` is canonical; any behavior a test relied on and `run_evals.py` lacks is a Discovered item, not a silent change.
- **H4 async client:** FastMCP `Client` is async. T0 tests use `asyncio.run` (pattern `tests/test_phase2_contracts.py` L143) or `pytest-asyncio` auto mode (already configured). T1 `predict` wraps one fresh `async with Client(...)` per call in `asyncio.run`; if a loop is already running (notebook), run it in a worker thread. Never cache a client across loops.
- **H5 lockfile:** regenerate `uv.lock` only in 33.1.1, with the `[[tool.uv.index]]` PyPI pin in effect; inspect that every new `source` is `https://pypi.org/simple/`.
- **H6 privacy:** traces store prompts, arguments, coordinates. Synthetic fixtures only; all span payloads through `sanitize_public_payload`.
- **H7 live tests:** nothing in waves 1-6 may make a network call in the default offline suite. Live work is confined to 33.4.1 (scratch script) and the live step of 33.6.1.
- **H8 Workspace FS:** pytest on `/Workspace` can fail writing bytecode; use `PYTHONDONTWRITEBYTECODE=1` and `-p no:cacheprovider`.
- **H10 Pi and v2:** v2 is additive; Pi's `load_test_cases` ignores unknown keys and `version`, so no Pi loader change is needed. If any Pi test asserts `version == "1.0.0"`, report it as Discovered in 33.4.1.
- **H9 regulatory boundary (ADR 0003):** no eval code or dataset text may describe outputs as an official FPPA determination, LESA score, AD-1006, or NRCS-CPA-106.

## Task specs

### 33.1.1 — Harness-neutral matching module, pytest path, eval-databricks group

- **Repo:** fpac-soil-mcp
- **Depends on:** baseline recorded in STATE_33.md
- **Files in scope:** must edit `pyproject.toml` (`[dependency-groups]`, `[tool.pytest.ini_options]` only), `uv.lock`; can create `eval/common/__init__.py`, `eval/common/matching.py`, `eval/common/test_common_matching.py`; scratch `.development/`.
- **Spec:** Implement contract C1 as new code (do not import from `run_evals`). Add `pythonpath = ["eval"]` to pytest options. Add dependency group `eval-databricks = ["mlflow>=3.12,<4", "databricks-sdk[openai]>=0.122"]`. Regenerate `uv.lock` (`uv lock`) and confirm `uv sync` (default groups) does not install mlflow. Unit tests cover: Unicode dashes/NBSP normalization, exact and suffix tool matches, non-match on partial names (e.g. `point` vs `get_farmland_classification_by_point`), keyword case-insensitivity and missing-keyword reporting.
- **Constraints:** do not touch `eval/run_evals.py`, `eval/test_agent_eval.py`, `[project] dependencies`, `[dependency-groups].dev`, or the `[[tool.uv.index]]` block.
- **Anchors:** `pyproject.toml` `[dependency-groups]`, `[tool.pytest.ini_options]`; reference semantics `run_evals.py` `def normalize_text` (~L251), `def _tool_matches` (~L506).
- **Reference implementation:** `run_evals.normalize_text` / `_tool_matches` behavior (port semantics, not imports).
- **Acceptance:** `uv run pytest eval/common/test_common_matching.py -q` passes; `uv lock --check` passes; `git diff uv.lock` shows only additions for the new group plus resolution metadata, all from pypi.org.

### 33.1.2 — Dataset encoding repair and manifest wording

- **Repo:** fpac-soil-mcp
- **Depends on:** baseline
- **Files in scope:** must edit `eval/prompt_test_cases.json`, `manifest.yaml`.
- **Spec:** Replace each `\u00c2\u00a7` (mojibake `Â§`) with `\u00a7` (`§`) in the 4 affected `user_prompt` values; change nothing else in the JSON (no reformatting, keep `"version": "1.0.0"`). Change `manifest.yaml` prompt description "all 9 tools" to "all 10 tools".
- **Constraints:** no other wording changes; do not touch `server.json` or source code.
- **Anchors:** `grep -n 'u00c2' eval/prompt_test_cases.json` (4 hits, ~L180/235/349/387); `grep -n 'all 9 tools' manifest.yaml` (L40).
- **Acceptance:** `python -c "import json;t=open('eval/prompt_test_cases.json',encoding='utf-8').read();assert 'u00c2' not in t and '\u00c2' not in json.dumps(json.loads(t),ensure_ascii=False);print('ok')"`; `grep -c 'all 10 tools' manifest.yaml` = 1; `uv run pytest eval/test_agent_eval.py -q` unchanged pass count.

### 33.2.1 — Pi harness alignment (common imports, WARN, dedup, coverage)

- **Repo:** fpac-soil-mcp
- **Depends on:** 33.1.1, 33.1.2
- **Files in scope:** must edit `eval/run_evals.py`, `eval/test_agent_eval.py`.
- **Spec:**
  1. `run_evals.py`: import `normalize_text` and `tool_matches` from `common.matching`; delete the local `normalize_text`; keep `_tool_matches` as a one-line alias to `tool_matches` (existing tests import it).
  2. `run_evals.py` summary: remove the dead `WARN` counter and `WARN` from the failed set; summary line reports Passed/Failed only.
  3. `test_agent_eval.py`: diff its `normalize_text`, `extract_structured_tool_names`, `extract_assistant_content` against `run_evals.py` (H3). Delete the local copies and import from `run_evals`. Move nothing else.
  4. `extract_tool_calls` stays in `test_agent_eval.py` (Pi-only; D5).
  5. `test_prompt_dataset_schema_and_completeness`: add `calculate_preliminary_lesa` to `expected_tools`; additionally assert the set equals the 10 manifest tool names.
- **Constraints:** CLI flags, capture-artifact behavior, event parsing semantics, and retry logic unchanged. Do not touch `eval/common/`.
- **Anchors:** `run_evals.py`: `def normalize_text`, `def _tool_matches`, `warned = sum(` (~L936); `test_agent_eval.py`: `from run_evals import (` (L23), `def normalize_text` (L36), `def extract_structured_tool_names` (~L690), `def extract_assistant_content` (~L803), `def test_prompt_dataset_schema_and_completeness` (~L1149).
- **Acceptance:** `uv run pytest eval/test_agent_eval.py eval/common -q` passes with the same or higher count; `grep -c 'def normalize_text' eval/run_evals.py eval/test_agent_eval.py` = 0 each; `grep -n WARN eval/run_evals.py` empty; `python eval/run_evals.py --help` exits 0.

### 33.2.2 — T0 contract tests over the in-memory FastMCP client

- **Repo:** fpac-soil-mcp
- **Depends on:** 33.1.1 (pytest path)
- **Files in scope:** can create `eval/contract/test_contract.py`.
- **Spec:** Offline tests using `fastmcp.Client(create_mcp_server())`:
  1. Tool names, resource URIs, prompt names equal those in `manifest.yaml` (parse with regex `^  - name: (\S+)` under `tools:`/`prompts:` and `^  - uri: (\S+)` under `resources:`; no new deps).
  2. Every tool exposes a non-empty `input_schema`.
  3. `explain_fppa_screening_scope` and `list_farmland_classes` results contain the preliminary-screening limitation (match against `constants.REGULATORY_NOTICE` or a `REGULATORY_LIMITATIONS` entry).
  4. `get_farmland_classification_by_point` and `get_farmland_classification_by_mukey` with `fpac_soil_mcp.tools.soil_tools.SDAClient` patched to a client using the conftest prime payload return a `regulatory_notice`.
  5. Invalid inputs (latitude 999; mukey `-5`/non-numeric) yield `is_error` or a structured error, never an unhandled exception.
  6. `fppa://regulatory-notice` resource text contains `7 CFR Part 657` and `7 CFR Part 658`.
- **Constraints:** no network; no `__init__.py`; do not edit `tests/conftest.py` (re-declare the small mock you need locally or import payload constants from `tests.conftest`).
- **Anchors:** `tests/test_tools.py` `@patch("fpac_soil_mcp.tools.soil_tools.SDAClient")` (L41); `tests/conftest.py` `MOCK_SDA_PRIME_FARMLAND_RESPONSE`; `tests/test_phase2_contracts.py` `asyncio.run(mcp.list_tools())` (L143); `src/fpac_soil_mcp/constants.py` `REGULATORY_NOTICE`.
- **Reference implementation:** `tests/test_server.py` list_tools usage (~L31).
- **Acceptance:** `uv run pytest eval/contract/test_contract.py -q` passes offline; deliberately removing a tool name from a local copy of the manifest set makes test 1 fail (state this check in the report).

### 33.3.1 — Dataset v2 schema and loader

- **Repo:** fpac-soil-mcp
- **Depends on:** 33.1.1, 33.1.2
- **Files in scope:** can create `eval/common/dataset.py`, `eval/common/test_common_dataset.py`.
- **Spec:** Implement C2 validation and C3 conversion with stdlib/pydantic only (pydantic is a runtime dep). API: `load_cases(path=DEFAULT_PATH, *, ids=None, ground_truth_only=False, category=None) -> list[dict]`; `validate_cases(cases) -> None` (raises `ValueError` listing row id + field); `to_mlflow_records(cases) -> list[dict]`. Validation: required v1 fields present; unique ids; `expected_tool_calls[*].name` in `expected_tools` when both present; `numeric_expectations` numbers finite and `abs_tol >= 0`; `verified_on` ISO date; reject unknown top-level row keys. Tests: the checked-in v1 file validates; synthetic v2 rows convert to C3; each validation error path.
- **Constraints:** no mlflow import; do not edit the JSON.
- **Anchors:** `eval/run_evals.py` `def load_test_cases` (~L209) for filter semantics.
- **Acceptance:** `uv run pytest eval/common -q` passes.

### 33.4.1 — Ground truth for five rows (LIVE, serial, user sign-off)

- **Repo:** fpac-soil-mcp
- **Depends on:** 33.3.1
- **Files in scope:** must edit `eval/prompt_test_cases.json`; scratch `.development/ground_truth_33.py` (untracked, not committed).
- **Spec:** Using the package's own clients/tools (no hand-written SQL), query live SDA for POINT-01, MUKEY-01, INTERP-01; read static values for DISC-01 and RES-01 from `constants.py`/resource output. Write into those five rows: `expected_tool_calls` (POINT-01 with exact coordinate arguments using the tool's real parameter names; RES-01 `read_resource` with `uri`), `expected_facts` (2-4 short factual statements each: mukey, farmland class, NCCPI rating with tolerance stated, citations), `numeric_expectations` where numeric (INTERP-01 NCCPI per mukey, abs_tol 0.01), one compliance `guidelines` entry, `force_tool_use: true`, `live_data_sensitive: true` (false for DISC-01/RES-01), `verified_on`. Bump `"version"` to `"2.0.0"`. No changes to other rows or v1 fields.
- **Constraints:** runs serially (D7); must not alter `expected_tools`/`expected_keywords`; no LESA values.
- **Anchors:** `src/fpac_soil_mcp/tools/soil_tools.py` `def get_farmland_classification_by_point` (L54), `get_farmland_classification_by_mukey`, `get_soil_interpretations`; `src/fpac_soil_mcp/tools/fppa_tools.py` `def explain_fppa_screening_scope` (L14).
- **Acceptance:** `uv run python -c "from common.dataset import load_cases;print(len(load_cases(ground_truth_only=True)))"` (run from `eval/`) prints 5; `uv run pytest eval -q` passes; report includes a table of every recorded value with its source call. **Gate: user sign-off on the value table before commit.**

### 33.5.1 — T1 agent loop with MLflow tracing

- **Repo:** fpac-soil-mcp
- **Depends on:** 33.1.1, 33.3.1
- **Files in scope:** can create `eval/databricks/agent.py`, `eval/databricks/test_databricks_agent.py`, `eval/databricks/prompts/system_prompt_v1.txt`.
- **Spec:** Implement C4. `build_agent(model: str, *, server_factory=create_mcp_server, client=None, max_turns=8, force_tool_use=True, system_prompt_version="v1") -> Callable[[str], str]`; `available_prompt_versions() -> list[str]` (from files in `prompts/`); unknown version raises `ValueError`. Discover tools via in-memory client, convert to OpenAI function schemas from `input_schema`, append `read_resource` and `get_prompt`. OpenAI client from `WorkspaceClient().serving_endpoints.get_open_ai_client()` unless injected. Chat Completions loop with `temperature=0` until no tool calls or `max_turns`. Write `prompts/system_prompt_v1.txt` = FPPA preliminary-screening role + forced-tool instruction (port the intent of the Pi `--append-system-prompt` text; no official-determination wording, H9); load it by version (D11). When `force_tool_use` is false, omit the forced-tool sentence (marked block in the file). Root `@mlflow.trace(span_type="AGENT")`; per-dispatch `mlflow.start_span(name=tool_name, span_type="TOOL")`; sanitize payloads (H6); tool errors returned to the model as error text, not raised. Lazy-import mlflow/openai/databricks.sdk inside functions. Offline tests (`pytest.importorskip("mlflow")`): fake OpenAI client scripted to call `explain_fppa_screening_scope` then answer; assert returned text, one TOOL span with C4 shape, `read_resource` dispatch works, `max_turns` honored, `temperature=0` passed, v1 prompt loaded and unknown version rejected.
- **Constraints:** must not import `run_evals`/`test_agent_eval` (D4); no network in tests; no `__init__.py`.
- **Anchors:** `src/fpac_soil_mcp/app.py` `def create_mcp_server`; `src/fpac_soil_mcp/privacy.py` `def sanitize_public_payload` (L133).
- **Reference implementation:** template `mcp-hackathon-template/eval/databricks/agent_eval_offline.py` predict/trace pattern (no SP, no persistent loop).
- **Acceptance:** `uv run --group eval-databricks pytest eval/databricks/test_databricks_agent.py -q` passes; `uv run pytest eval/databricks -q` (no group) skips cleanly.

### 33.5.2 — T1 scorers

- **Repo:** fpac-soil-mcp
- **Depends on:** 33.1.1, 33.3.1 (uses C3/C4 shapes; 33.4.1 rows as examples)
- **Files in scope:** can create `eval/databricks/scorers.py`, `eval/databricks/test_databricks_scorers.py`.
- **Spec:** Deterministic `@scorer`s: `required_tools_called(trace, expectations)` (TOOL span names vs `expected_tools` via `common.matching.tool_matches`); `keywords_present(outputs, expectations)`; `numeric_within_tolerance(trace, expectations)` (resolve C2 `path` in matching TOOL span `outputs.result`); `tool_arguments_within_tolerance(trace, expectations)` (numeric args in `expected_tool_calls` within 1e-4, strings exact). Each returns `Feedback` with rationale, and `None`/skip when its expectation key is absent. `build_scorers(judge_model) -> list` returns deterministic scorers + `Correctness`, `Guidelines(name="fppa_compliance", guidelines=<preliminary-screening text from note 6.4>)`, `ExpectationsGuidelines`, `ToolCallCorrectness(should_exact_match=False)`, `Safety`, `ToolCallEfficiency`, judges using `model=f"databricks:/{judge_model}"`, with `temperature=0` where the judge constructor or inference params support it (record in the report which judges could not take it; D11). Tests (importorskip mlflow): build a trace with `mlflow.start_span` matching C4 and assert pass/fail/skip for each deterministic scorer; `build_scorers` returns expected names.
- **Constraints:** must not import Pi modules; no judge calls in tests.
- **Anchors:** `eval/common/matching.py` (C1); research note section 6.4 table.
- **Acceptance:** `uv run --group eval-databricks pytest eval/databricks/test_databricks_scorers.py -q` passes.

### 33.6.1 — T1 runner, notebook, and 5-case serverless check (live step serial)

- **Repo:** fpac-soil-mcp
- **Depends on:** 33.4.1, 33.5.1, 33.5.2
- **Files in scope:** can create `eval/databricks/run_mlflow_eval.py`, `eval/databricks/run_t1_eval_notebook.py` (Databricks notebook source format), `eval/databricks/test_databricks_runner.py`.
- **Spec:** Implement C5. `run()` loads cases via `common.dataset`, builds records, agent, scorers; sets experiment (create if absent); tags run with `git_sha`, `git_branch` (from `git rev-parse`, `unknown` on failure), `agent_model`, `judge_model`, `dataset_version`, `system_prompt_version`; calls `mlflow.genai.evaluate(data, predict_fn, scorers)`; prints run ID and per-scorer pass/fail/null counts. `--dry-run` makes no model calls. Notebook: `%pip install -e ../..` (repo root) + shapely reinstall cell, then `run(["--ground-truth"])`. Offline test: `--dry-run` on ground-truth rows returns 5 records and the scorer name list. **Live step (serial):** orchestrator runs the notebook on serverless; record run ID, experiment path, per-scorer counts in STATE_33.md.
- **Constraints:** no T2/SP code; no job creation.
- **Anchors:** C5; template `agent_eval_offline.py` CONFIG + experiment setup.
- **Acceptance:** `uv run --group eval-databricks pytest eval/databricks/test_databricks_runner.py -q` passes; live run completes with every scorer non-null on all 5 rows (D8).

### 33.6.2 — Documentation and Make target

- **Repo:** fpac-soil-mcp
- **Depends on:** 33.5.1, 33.5.2 (C5 names)
- **Files in scope:** must edit `README.md` (eval section only), `AGENTS.md` (Find Things + Validate sections only), `Makefile`; can create `eval/databricks/README.md`.
- **Spec:** Document the three tiers (Pi local, T0 contract, T1 Databricks), how to run each, the `eval-databricks` group, notebook usage, system prompt versioning (`prompts/system_prompt_v{n}.txt`, `--system-prompt-version`), privacy note, deferred T2. Add Make target `eval-databricks` -> `uv run --group eval-databricks python eval/databricks/run_mlflow_eval.py $(ARGS)` and list it in `.PHONY`/help.
- **Constraints:** no wording that implies official determinations (H9); do not change existing targets.
- **Anchors:** `Makefile` `test-eval:` (L45), `.PHONY` (L15); `AGENTS.md` `## Find Things`, `### Validate a Change`.
- **Acceptance:** `make help` lists `eval-databricks`; `uv run ruff check .` and `uv run ruff format --check .` pass; markdown links resolve to existing paths.

## Wave-end gate (every wave, run serially by the orchestrator)

```text
PYTHONDONTWRITEBYTECODE=1 uv run pytest -p no:cacheprovider -m "not live_network"
uv run ruff check .
uv run ruff format --check .
```

From wave 5 on, also: `uv run --group eval-databricks pytest -p no:cacheprovider eval/databricks -q`.

Before merge (manual, laptop): `make test-eval` (Pi live).

## Post-orchestration (optional)

Run **adr-distillation** on this plan and STATE_33.md to record the eval-tier architecture (in-process T1, shared dataset, common matching) as a new ADR.
