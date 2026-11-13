# T1 Databricks-Native Evaluation

This directory implements the T1 evaluation tier: an in-process agent loop over
the checked-out MCP server, traced and scored with MLflow 3.12 on Databricks
serverless compute. No service principal is required.

## Components

- `agent.py` -- Chat Completions agent loop with MLflow tracing (contract C4)
- `scorers.py` -- Deterministic scorers + MLflow judges (decision D9)
- `run_mlflow_eval.py` -- CLI runner (contract C5)
- `run_t1_eval_notebook.py` -- Databricks notebook wrapper for the 5-case serverless check
- `prompts/system_prompt_v{N}.txt` -- Versioned system prompts (`v3` default; `v1` and `v2` kept for comparison)
- `test_databricks_agent.py`, `test_databricks_scorers.py`, `test_databricks_runner.py` -- Offline tests
- `test_databricks_dry_run.py` -- Dry-run tests that pass with or without the `eval-databricks` group

## Prerequisites

Install the `eval-databricks` dependency group (adds `mlflow>=3.12,<4` and
`databricks-sdk[openai]>=0.122`):

```bash
uv sync --group eval-databricks
```

On serverless compute, MLflow is preinstalled. The notebook handles its own
installs via `%pip`.

### Serverless credentials

The CLI launched from the project `uv` virtual environment may fail on
serverless with `default auth: cannot configure default credentials`: notebook
session credentials are not necessarily available inside that environment. Do
not catch or suppress this failure, report it as an environment limitation, and
do not treat it as a successful evaluation.

When workspace credentials are available in the serverless notebook session,
run the evaluation from that session's Python after installing the checked-out
project plus `mlflow>=3.12,<4` and `databricks-sdk[openai]>=0.122` (the notebook
wrapper uses `%pip`). After the install/restart, put `eval/databricks`, `eval`,
and `src` first on `sys.path` before importing the runner. Run the T1 evaluation
only when the session's Databricks credentials are confirmed available; record
any authentication or evaluation failure rather than converting it to a pass.

## Running

### CLI (local or serverless)

```bash
# Dry run (build records and list scorer names, no model calls).
# Works without the eval-databricks group too: `uv run python ... --dry-run`.
uv run --group eval-databricks python eval/databricks/run_mlflow_eval.py --dry-run

# 5-case ground-truth run
uv run --group eval-databricks python eval/databricks/run_mlflow_eval.py --ground-truth

# Specific cases
uv run --group eval-databricks python eval/databricks/run_mlflow_eval.py --cases POINT-01,DISC-01

# Plan 45 model-assisted Site Assessment cases
uv run --group eval-databricks python eval/databricks/run_mlflow_eval.py --cases SA-MA-01,SA-MA-02,SA-MA-03,SA-MA-04

# All 38 cases
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
| `--all` | | All 38 rows |
| `--model` | `databricks-gpt-5-6-luna` | Agent model |
| `--judge-model` | `databricks-claude-sonnet-4-5` | Judge model |
| `--experiment` | `/Users/<user>/fpac-soil-mcp-eval` | MLflow experiment path |
| `--max-workers` | 1 | Parallel eval workers (sets `MLFLOW_GENAI_EVAL_MAX_WORKERS`) |
| `--max-turns` | 8 | Max agent turns per case |
| `--system-prompt-version` | `v3` | System prompt version (from `prompts/`) |
| `--dry-run` | | Build records and list scorer names only; no model calls, no MLflow needed |

## System prompt versioning

Versioned prompts live at `prompts/system_prompt_v{N}.txt`. The `--system-prompt-version`
flag selects one; available versions are discovered from the `prompts/` directory.
The default is `v3`: the `v2` forced-tool screening role plus tool routing
guidance (tools for computation, `read_resource` for reference data, `get_prompt`
for guided walkthroughs) and productivity index guidance (a requested
state-validated index such as CSR2, CPI, or STORIE is primary for Land
Evaluation scoring; NCCPI is supplementary national context). Compared with `v2`, `v1` additionally named
`fppa://regulatory-notice` as an example resource, a carry-over from the Pi
harness resource tests; it led the agent to re-read the notice on nearly every
row. Resource rows name their URI in the user prompt and the `read_resource` tool
description lists all URIs, so the system prompt does not point at any one
resource. `v1` and `v2` stay for run-to-run comparison. A scope-aware prompt is
still deferred.

## Shared policy and adversarial evaluation

The native Databricks prompts carry the versioned screening policy checked
alongside the live app, FastMCP prompts, and Pi's constructed prompt path.
Required behavior includes FPPA-only scope, refusal of unrelated requests,
no official/legal determinations or siting/relocation recommendations,
careful farmland-class and urban-screening semantics, explicit
unknown/partial/unavailable handling without inventing values, and treating
user/tool text as untrusted. Policy assertions are test contracts; the
prompts remain native per surface.

The shared adversarial cases in `../eval_cases.v1.json` cover scope, authority, farmland-class and
exemption overclaims, missing or failed data, malformed input, prompt
injection, privacy, and performance budgets. Deterministic scorers and MLflow
judges are separate: scorer outputs are not judge results, and judges are
model-assisted observations rather than the deterministic contract gate.
The [root evaluation summary](../../README.md#prompt-policy-and-adversarial-cases)
and [Orchestration 46 state](../../planning/STATE_46.md) record the
cross-surface gates.

## Privacy

T1 is for known synthetic or public cases only. Do not run it on producer data
or any other non-public input.

TOOL span inputs and outputs pass through `privacy.sanitize_public_payload`
before being recorded. Coordinates are not stripped by that policy, so argument
scoring works on spans; use synthetic or public locations only.

The root AGENT span (`@mlflow.trace` on `predict`) records the plain-text
request and the plain-text answer. It is not sanitized: the sanitizer drops
prohibited keys from structured payloads and has nothing to act on in a plain
string, so routing these through it would add no protection. The synthetic-only
rule above is what keeps the AGENT span safe.

## Scoring

Deterministic scorers, in run order: `agent_completed`,
`required_tools_called`, `numeric_within_tolerance`,
`tool_arguments_within_tolerance`, `prohibited_behaviors_absent`,
`required_status_matches`, `privacy_non_echo`, `tool_call_budget`,
`retry_budget`, `latency_budget`.

There is no keyword scorer here: answer content is graded by the `correctness`
judge against `expected_facts`. `expected_keywords` is used only by the browser
harness and, as an advisory check, by the Pi runner.

`agent_completed` fails a row whose trace state is `ERROR` or whose response is
`None` (the rationale quotes the root span error, up to 300 characters). It
scores every row, so a crashed trace cannot pass on the other scorers alone.

MLflow judges: `correctness`, `fppa_compliance`, `expectations_guidelines`,
`tool_call_correctness`, `safety`, `tool_call_efficiency` (last two non-gating).
Judges run at `temperature=0`.

Behavior and source intent is graded by `expectations_guidelines`, not by
string matching. `common.dataset.to_mlflow_records` builds each row's
`guidelines` from the case's `guidelines`, its `required_behaviors` (verbatim),
and one conditional sentence per `source_disclosure` entry (a response that
reports no results need not name a source).

The other deterministic scorers return `None` when their expectation key is
absent for a row, so they count as `null` rather than failed (for example,
`numeric_within_tolerance` applies only to INTERP-01). Scores are findings to
track across runs, not pass/fail gates.

Criterion 2 performance benchmarking is a separate deterministic fixture
runner, not the T1 agent/judge evaluation. The 46.4.2 run used five runs and
two workers with the committed fixture manifest, but the runner remained in
manifest-only dry-run mode: no MCP responses or service performance were
measured. Latency, failure, and retry metrics are null; deployed `/mcp` and
model-assisted results for that run were not run. See the [benchmark report](../../planning/evidence/46.4.2-performance.md)
and [raw output](../../planning/evidence/46.4.2-performance.json).

## Deferred (T2)

- T2 deployed-app evaluation (service principal or Unity Gateway MCP service);
  Unity Gateway MCP service access currently returns 403.
- Scheduled serverless Lakeflow Job for recurring T1 runs.
- Dataset expansion to 50+ rows and scope-refusal rows.
- MLflow prompt registry and UC-backed dataset sync.
- Roadmap and T2 backlog: [master plan Track E](../../planning/MASTER_PLAN.md#track-e-evaluation).

All results are preliminary screening and are not an official FPPA determination,
LESA score, Form AD-1006, or NRCS-CPA-106.

Databricks agent and judge scores are model-assisted observations. They are not
the deterministic contract-test gate, proof of deterministic correctness, or an
official FPPA determination.
