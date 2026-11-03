# Worker Prompt Template — Execution Plan 43

You are executing one task from `planning/EXECUTION_PLAN_43.md`.

Read `AGENTS.md`, the assigned task specification, applicable accepted ADRs,
and the current `planning/STATE_43.md`. Make only the task-scoped changes.
Follow existing Python, Pydantic, FastMCP, test, provenance, and regulatory
notice patterns. Do not add live-network tests to the default path.

Run the task's targeted tests, then the required wave gate:

```powershell
uv run pytest -m "not live_network"
uv run ruff check .
uv run ruff format --check .
uv run pytest -m live_network
```

The live command is opt-in and may fail for an external network reason; report
that explicitly. Use conventional commits with one concise sentence and no
phase or wave numbers. Follow [[git-workflow-standards]](../../git-workflow-standards/SKILL.md).

Append a concise report to `planning/STATE_43.md` with status, changed files,
commands/results, deviations, and commit. Do not include real coordinates,
credentials, or sensitive payloads in planning artifacts.
