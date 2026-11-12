# STATE 47: Judge-First Scoring for Natural-Language Expectations

Resume point for orchestration 47. Plan: `planning/EXECUTION_PLAN_47.md`.
Worker prompt: `planning/PROMPT_TEMPLATE_47.md`.

## Baseline (record before wave 1)

Recorded 2026-11-12 on Databricks serverless (Python 3.12).

- [x] Branch created off `fix/eval-tuning1` (`8c90f0d`): `feat/judge-first-scoring` @ `2b7c9ee`, clean tree, 0 ahead / 0 behind origin.
- [x] Test env: `pip install -e . mlflow==3.12.0 pytest-asyncio` (project deps such as `fastmcp` are not on the serverless image; a bare dry run failed with `No module named 'fastmcp'` on 2026-11-12); `PYTHONDONTWRITEBYTECODE=1`. Resolved to mlflow 3.12.0, **fastmcp 3.4.0, mcp 1.30.0** (uv.lock pins fastmcp 4.1.6, mcp 2.3.0; mlflow 3.12.0 declares `fastmcp<4` for its `mcp` extra). Ruff 0.17.5 (lock 0.17.3).
- [x] Dry run: `PYTHONPATH=src:eval python eval/databricks/run_mlflow_eval.py --dry-run --all` -- `Dry run: 38 records`, 18 scorers.
- [x] `PY eval/common` -- 132 passed.
- [x] `PY eval/databricks/test_databricks_scorers.py eval/databricks/test_databricks_agent.py eval/databricks/test_databricks_runner.py eval/databricks/test_databricks_dry_run.py` -- **28 passed, 7 failed (PRE-EXISTING, environment)**. All 7 in `test_databricks_agent.py` (test_agent_calls_tool_then_answers_with_c4_trace, test_zero_call_budget_disables_tool_use_and_is_added_to_system_prompt, test_agent_span_shape_is_pinned, test_read_resource_and_get_prompt_dispatch, test_max_turns_is_honored, test_tool_errors_are_returned_to_the_model_not_raised, test_span_payloads_are_sanitized). Error: `AttributeError: 'Tool' object has no attribute 'input_schema'. Did you mean: 'inputSchema'?` at `agent.py` L156 (`_discover`). Cause: the install resolves fastmcp 3.4.0 / mcp 1.30.0 instead of the locked 4.1.6 / 2.3.0. Not fixed (baseline rule); awaiting user decision.
- [x] `PY eval/pi/test_agent_eval.py -m "not agent_eval"` -- 40 passed, 2 deselected.
- [x] `PY tests/eval/test_phase4_databricks_contract.py` -- 6 passed.
- [x] Harness `npm run check && npm test` (`/tmp/r87/repo` copy, node v22.20.0, npm 10.9.3) -- check OK; tests 18, pass 18, fail 0, skipped 0.
- [x] Ruff on archive copy of `eval/` (`ruff check eval/` + `ruff format --check eval/`) -- All checks passed; 20 files already formatted.

Reference T1 run: `f2df7fe1d52a4c139df1bdde4748768f` (38 cases, `--all`,
agent `databricks-gpt-5-6-luna`, judge `databricks-claude-sonnet-4-5`,
git `ff8ac91`). Scorer results from that run: `keywords_present` 23 pass /
13 fail / 2 null; `source_disclosed` 0 / 8 / 30; `required_behaviors_present`
6 / 8 / 24; 6 traces ERROR (`tools=None` -> HTTP 400).

## Wave Board

| Wave | Task | Status | Commit | Notes |
|---|---|---|---|---|
| 1 | 47.1.1 Omit `tools` when withheld | pending | | |
| 1 | 47.1.2 Add `agent_completed` scorer | pending | | |
| 1 gate | Zero-budget live smoke | pending | | |
| 2 | 47.2.1 Judge guidelines from behaviors/sources | pending | | |
| 2 | 47.2.2 Remove behavior/source string scorers | pending | | |
| 2 | 47.2.3 Pi: drop checks, advisory keywords | pending | | |
| 2 | 47.2.4 Harness: drop unused predicates | pending | | |
| 2 gate | String-check retirement | pending | | |
| 3 | 47.3.1 ADV keywords to required behaviors | pending | | |
| 3 | 47.3.2 Delete `required_behavior_missing` | pending | | |
| 3 gate | Case data + fact source extraction | pending | | |
| 4 | 47.4.1 Expected facts for 15 cases | pending | | |
| 4 gate | Facts | pending | | |
| 5 | 47.5.1 Remove Databricks `keywords_present` | pending | | |
| final | Full T1 rerun vs `f2df7fe1` | pending | | |

## Task Reports

<!-- Orchestrator appends <=15 lines per task under `## <id>`. -->

## Findings

- LESA-01 prompt assigns 120 points to one Part VI criterion; the tool rejects
  it. Candidate for case rework (out of scope for plan 47).
