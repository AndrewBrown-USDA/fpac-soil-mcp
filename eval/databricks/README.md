# T1 Databricks-Native Evaluation

This directory implements the T1 evaluation tier: an in-process agent loop over
the checked-out MCP server, traced and scored with MLflow 3.12 on Databricks
serverless compute. No service principal is required.

## Components

- `agent.py` -- Chat Completions agent loop with MLflow tracing (contract C4)
- `scorers.py` -- Deterministic scorers + MLflow judges (decision D9)
- `run_mlflow_eval.py` -- CLI runner (contract C5)
- `run_t1_eval_notebook.py` -- Databricks notebook wrapper for the 5-case serverless check
- `prompts/system_prompt_v1.txt` -- Versioned system prompt (forced-tool screening role)
- `test_databricks_agent.py`, `test_databricks_scorers.py`, `test_databricks_runner.py` -- Offline tests

## Prerequisites

Install the `eval-databricks` dependency group (adds `mlflow>=3.12,<4` and
`databricks-sdk[openai]>=0.122`):

```bash
uv sync --group eval-databricks
```

On serverless compute, MLflow is preinstalled. The notebook handles its own
installs via `%pip`.

## Running

### CLI (local or serverless)

```bash
# Dry run (build records and scorers, no model calls)
uv run --group eval-databricks python eval/databricks/run_mlflow_eval.py --dry-run

# 5-case ground-truth run
uv run --group eval-databricks python eval/databricks/run_mlflow_eval.py --ground-truth

# Specific cases
uv run --group eval-databricks python eval/databricks/run_mlflow_eval.py --cases POINT-01,DISC-01

# All 20 cases
uv run --group eval-databricks python eval/databricks/run_mlflow_eval.py --all
```

### Make target

```bash
make eval-databricks ARGS="--ground-truth"
```

### Databricks notebook

Open `eval/databricks/run_t1_eval_notebook.py` on serverless compute and run all
cells. It installs the repo and `databricks-sdk[openai]`, reinstalls shapely,
restarts Python, and calls `run(ARGS)` (default `["--ground-truth"]`). The runner
prints the MLflow run ID and per-scorer pass/fail/null counts.

Live rows call USDA Soil Data Access. SDA is unavailable during its daily
maintenance window (12:30-12:45 AM Central) and returns an HTML page, which shows
up as tool errors in the traces; rerun after the window.

## CLI flags (C5)

| Flag | Default | Description |
| --- | --- | --- |
| `--cases ID,ID` | | Comma-separated case IDs |
| `--ground-truth` | (default) | Only verified rows |
| `--all` | | All 20 rows |
| `--model` | `databricks-gpt-5-6-luna` | Agent model |
| `--judge-model` | `databricks-claude-sonnet-4-5` | Judge model |
| `--experiment` | `/Users/<user>/fpac-soil-mcp-eval` | MLflow experiment path |
| `--max-workers` | 1 | Parallel eval workers (sets `MLFLOW_GENAI_EVAL_MAX_WORKERS`) |
| `--max-turns` | 8 | Max agent turns per case |
| `--system-prompt-version` | `v1` | System prompt version (from `prompts/`) |
| `--dry-run` | | Build records and scorers only, no model calls |

## System prompt versioning

Versioned prompts live at `prompts/system_prompt_v{N}.txt`. The `--system-prompt-version`
flag selects one; available versions are discovered from the `prompts/` directory.
Only `v1` (forced-tool screening role) ships. A v2 scope-aware prompt is deferred.

## Privacy

TOOL span inputs and outputs pass through `privacy.sanitize_public_payload`
before being recorded. Coordinates are not stripped by that policy, so argument
scoring works on spans; use synthetic or public locations only.

## Scoring

Deterministic scorers: `required_tools_called`, `keywords_present`,
`numeric_within_tolerance`, `tool_arguments_within_tolerance`.

MLflow judges: `correctness`, `fppa_compliance`, `expectations_guidelines`,
`tool_call_correctness`, `safety`, `tool_call_efficiency` (last two non-gating).
Judges run at `temperature=0`.

Deterministic scorers return `None` when their expectation key is absent for a
row, so they count as `null` rather than failed (for example,
`numeric_within_tolerance` applies only to INTERP-01). Scores are findings to
track across runs, not pass/fail gates.

## Deferred (T2)

- T2 deployed-app evaluation (service principal or Unity Gateway MCP service);
  Unity Gateway MCP service access currently returns 403.
- Scheduled serverless Lakeflow Job for recurring T1 runs.
- Dataset expansion to 50+ rows and scope-refusal rows.
- MLflow prompt registry and UC-backed dataset sync.

All results are preliminary screening and are not an official FPPA determination,
LESA score, Form AD-1006, or NRCS-CPA-106.
