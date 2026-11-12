# STATE 47: Judge-First Scoring for Natural-Language Expectations

Resume point for orchestration 47. Plan: `planning/EXECUTION_PLAN_47.md`.
Worker prompt: `planning/PROMPT_TEMPLATE_47.md`.

## Baseline (record before wave 1)

- [ ] Branch created off `fix/eval-tuning1` (`8c90f0d`); name recorded here.
- [ ] Test env: `pip install -e . mlflow==3.12.0 pytest-asyncio` (project deps such as `fastmcp` are not on the serverless image; a bare dry run failed with `No module named 'fastmcp'` on 2026-11-12); `PYTHONDONTWRITEBYTECODE=1`.
- [ ] Dry run: `PYTHONPATH=src:eval python eval/databricks/run_mlflow_eval.py --dry-run --all` prints 38 records.
- [ ] `PY eval/common` -- counts:
- [ ] `PY eval/databricks/test_databricks_scorers.py eval/databricks/test_databricks_agent.py eval/databricks/test_databricks_runner.py eval/databricks/test_databricks_dry_run.py` -- counts:
- [ ] `PY eval/pi/test_agent_eval.py -m "not agent_eval"` -- counts:
- [ ] `PY tests/eval/test_phase4_databricks_contract.py` -- counts:
- [ ] Harness `npm run check && npm test` (`/tmp` copy) -- counts:
- [ ] Ruff on archive copy of `eval/` -- result:

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
