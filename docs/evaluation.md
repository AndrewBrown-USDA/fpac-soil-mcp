# Evaluation and Artifact Handling

This guide covers the project's offline contract tests and opt-in agent evaluations. Evaluation output is diagnostic evidence, not an official FPPA determination or an agency record.

## Evaluation tiers

| Tier | Purpose | Command |
| :--- | :--- | :--- |
| T0 contract | Offline checks against the in-memory MCP server. | `uv run pytest eval/contract/` |
| Pi agent evaluation | Opt-in evaluation through the Pi CLI agent. | `make test-eval` |
| T1 Databricks | Agent evaluation with MLflow tracing and scoring. | `make eval-databricks` |

See [`eval/databricks/README.md`](../eval/databricks/README.md) for T1 prerequisites and options. The default test suite does not contact external services or run agent evaluations.

A separate T2 deployed-access smoke is currently deferred. It checks authenticated access to the deployed MCP endpoint, not agent or model quality; see the [Databricks evaluation guide](../eval/databricks/README.md#deferred-t2) for its prerequisites and current status.

## Retaining Pi evaluation artifacts

Artifact capture is opt-in. By default, evaluation output is not retained. To retain artifacts, provide an external root directory:

```powershell
uv run python eval\pi\run_evals.py --capture-artifacts --artifact-root C:\path\to\eval-artifacts
```

The equivalent environment variables are `EVAL_CAPTURE_ARTIFACTS=1` and `EVAL_CAPTURE_ROOT`. The runner requires an artifact root outside the repository and its fixture directories. Use an access-restricted location; captured output can contain prompts, tool data, provider output, or other sensitive material.

Each run and case is stored under a separate attempt directory. It contains metadata, bounded output copies, parsed events, and raw streams for local debugging. Inspect `metadata.json` first. The raw files are more sensitive than the bounded copies and should only be used when necessary.

Retention is controlled by the caller: protect the artifact root, share files only as needed, and remove them after review. Never add captured artifacts to the repository. Checked-in evaluation fixtures should be minimal, deterministic, sanitized, and based on verified data shapes.

Production privacy protections, including Section 1619 and coordinate safeguards, continue to apply regardless of evaluation settings. Evaluation artifacts must not be treated as production data-retention records or official FPPA determinations.
