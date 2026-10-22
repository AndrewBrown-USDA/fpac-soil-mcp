---
name: pi-mcp-eval
description: Runs the repository's isolated, opt-in Pi agent evaluation process against MCP prompt fixtures. Use when executing or diagnosing a release-time Pi eval, checking MCP tool evidence, or reviewing sanitized eval results; do not use for general benchmarking, production logging, or official FPPA determinations.
---

# Pi MCP Eval

Run the repository's release-time Pi evaluation without mixing it with production logging or the default offline test suite.

## Preconditions

- Work from `D:\workspace\fpac-soil-mcp`.
- Run `uv sync` if dependencies are not installed.
- Confirm `pi` is available on `PATH`.
- Confirm required model/provider configuration is available without exposing credentials.
- Keep retained artifacts outside the repository.

## Standard commands

Run one case:

```powershell
uv run python eval\pi\run_evals.py --case-id POINT-01
```

Run a category:

```powershell
uv run python eval\pi\run_evals.py --category point
```

Inspect available options:

```powershell
uv run python eval\pi\run_evals.py --help
```

Use the runner's explicit capture option only when evidence is needed. Use an artifact root outside the repository and never place credentials, prompts, coordinates, geometry, producer data, or generated responses in filenames or metadata.

## Execution rules

1. Use `eval\pi\run_evals.py`; do not improvise a production invocation.
2. Preserve the temporary sandbox and stdio MCP transport.
3. Treat dedicated structured tool events as execution evidence. Prose and prompt echo never count.
4. Keep Pi/agent evaluation opt-in; do not replace the default offline test path.
5. Retain raw artifacts only when explicitly requested, with bounded size and cleanup.
6. Use sanitized fixtures from `eval\fixtures\event_capture\` for parser regressions.

## Result interpretation

- `PASS`: expected structured evidence and output checks succeeded.
- `FAIL`: an expected tool, keyword, or diagnostic contract failed.
- `TIMEOUT`: Pi exceeded the configured timeout.
- `ERROR`: startup or subprocess execution failed.
- `absent`: no dedicated structured tool event was observed.
- `present_unrecognized`: dedicated evidence exists but the normalized extractor did not recognize it.
- `recognized`: structured evidence was extracted successfully.

Do not interpret Pi output as an official FPPA determination, an NRCS form, or a production audit record.

## Troubleshooting

- **Pi not found:** install/configure Pi and verify `Get-Command pi`.
- **Missing fixture:** verify `eval\prompt_test_cases.json` exists and is valid JSON.
- **Missing tool evidence:** inspect initialization/tool-list diagnostics; do not infer execution from prose.
- **Timeout/startup failure:** rerun one case with a bounded timeout and retain sanitized diagnostics only when needed.
- **Artifact rejection:** choose an external artifact root; repository-local retention is intentionally blocked.

## Validation

After parser or capture changes, run the deterministic checks first:

```powershell
uv run pytest eval\pi\test_agent_eval.py -m "not agent_eval" -q
uv run pytest -m "not live_network and not agent_eval"
uv run ruff check .
uv run ruff format --check .
```

Run `uv run pytest eval\pi\test_agent_eval.py -m agent_eval -q` or `make test-eval` only as explicit opt-in gates when Pi and provider access are available.

Related skills: use `performance-benchmarking` for scaling or branch-speed comparisons, `worker-validation` for validating code fixes, and `skill-research` for creating or revising skills.
