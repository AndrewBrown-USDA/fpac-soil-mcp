# Evaluation and Artifact Handling

This guide covers the project's offline contract tests and opt-in agent evaluations. Evaluation output is diagnostic evidence, not an official FPPA determination or an agency record.

## Evaluation tiers

| Tier | Purpose | Command |
| :--- | :--- | :--- |
| T0 contract | Offline checks against the in-memory MCP server. | `uv run pytest eval/contract/` |
| Pi agent evaluation | Opt-in evaluation through the Pi CLI agent. | `make test-eval` |
| T1 Databricks | Agent evaluation with MLflow tracing and scoring. | `make eval-databricks` |

See [`eval/databricks/README.md`](../eval/databricks/README.md) for T1 prerequisites and options. The default test suite does not contact external services or run agent evaluations.

T2 checks authenticated access to the deployed MCP endpoint separately from agent quality. Its deployment prerequisites and rollout status are described in the [Databricks evaluation guide](../eval/databricks/README.md#deferred-t2).

## Case coverage

The shared corpus [`eval/eval_cases.v1.json`](../eval/eval_cases.v1.json), version 1.1.0, contains 42 cases: 22 workflow/resource/prompt cases, six model-assisted Site Assessment cases, and 14 adversarial cases. Twenty-eight have expected facts and five have verification dates.

Coverage includes soil/spatial retrieval, urban and LESA screening, CDL context, reference guidance, scope and authority boundaries, missing/partial data, outages, geometry validation, injection, privacy, and performance budgets. Metrics apply only where a case supplies the relevant expectations; null or not-applicable scores are not automatic failures.

## Recorded evaluation evidence

| Activity | Recorded finding | Source |
| :--- | :--- | :--- |
| Historical T1 full suite | 38 completed; correctness 17 pass/7 fail/14 null | [Plan 47 state](../planning/STATE_47.md#final-gate), run `69d873e7100b497e85728cca03943ea8` |
| Historical Pi full suite | 24 passed, 14 failed of 38 | [Pi report](../planning/evidence/46.8.1-pi-auth-eval.md) |
| Selected Pi failure reruns | 9 passed, 5 failed of 14 selected cases | [Rerun report](../planning/evidence/46.8.4-pi-failed-case-rerun.md) |
| November 20 v1/v2 comparison | Efficiency 5/25 vs 25/25; correctness 25/25 both | [Prompt comparison](#prompt-comparison) |

Results describe each run's case set, prompt, and scoring configuration. The 38-case full-suite runs and the repeated five-case comparison are reported separately; selected reruns retain their own denominators.

### Prompt comparison

The November 20 experiment compared v1 and v2 on five cases, repeated five times per arm. Alternating arm order and fixed tools/models/settings isolated a prompt change: v2 removed a generic resource-helper instruction. The recorded comparison used code `4850c392`, agent `databricks-gpt-5-6-luna`, judge `databricks-claude-sonnet-4-5`, and live upstream data.

| Measure | v1 | v2 |
| :--- | :--- | :--- |
| Completed attempts | 25/25 | 25/25 |
| Correctness | 25/25 | 25/25 |
| Tool-call efficiency | 5/25 | 25/25 |
| Tool-call correctness | 7/25 | 25/25 |
| Automated screening-boundary check | 25/25 | 24/25 |
| Total server and helper calls | 45 | 25 |
| Median agent-trace elapsed time | 8.07 seconds | 6.68 seconds |

V1 added a redundant regulatory-notice resource call on the four non-resource tasks. V2 retained the resource call for the resource task while avoiding those extra calls. Human review identified one v2 screening-boundary label/rationale disagreement; the original automated 24/25 score is retained.

Provenance: comparison `fpac-prompt-v1v2-cmp-20261120-01`, MLflow report run `5f8e316f4eb34a798598b48ba3cd5665`, experiment `1982416510426575`. The exported notebook's saved outputs record 50 completed rows and a results-CSV SHA-256 check against `4f5029aab70a02fcf9010bbf9ed5f5e0327ceb24d5cf12b9084d330beefd0ee7`.

The five-case comparison demonstrates prompt-driven tool-use differences. Repetitions are repeated trials of the same cases; timing describes agent traces affected by live services. Current prompts and deployed access have their own evaluation scope.

## Future evaluation

A full-suite with/without-MCP comparison would measure the effect of tool access, complementing the prompt-only experiment. It would use matched models, task policy, case inputs, references, and repeated trials. Tool-specific metrics would apply to the MCP arm; answer correctness, uncertainty handling, and screening boundaries would be compared by task category. This is a planned experiment, so the recorded results above concern MCP-enabled agents.

Component responsibilities and source boundaries are described in the [architecture guide](architecture.md).

## Retaining Pi evaluation artifacts

Artifact capture is opt-in. By default, evaluation output is not retained. To retain artifacts, provide an external root directory:

```powershell
uv run python eval\pi\run_evals.py --capture-artifacts --artifact-root C:\path\to\eval-artifacts
```

The equivalent environment variables are `EVAL_CAPTURE_ARTIFACTS=1` and `EVAL_CAPTURE_ROOT`. The runner requires an artifact root outside the repository and its fixture directories. Use an access-restricted location; captured output can contain prompts, tool data, provider output, or other sensitive material.

Each run and case is stored under a separate attempt directory. It contains metadata, bounded output copies, parsed events, and raw streams for local debugging. Inspect `metadata.json` first. The raw files are more sensitive than the bounded copies and should only be used when necessary.

Retention is controlled by the caller: protect the artifact root, share files only as needed, and remove them after review. Never add captured artifacts to the repository. Checked-in evaluation fixtures should be minimal, deterministic, sanitized, and based on verified data shapes.

Production privacy protections, including Section 1619 and coordinate safeguards, continue to apply regardless of evaluation settings. Evaluation artifacts must not be treated as production data-retention records or official FPPA determinations.
