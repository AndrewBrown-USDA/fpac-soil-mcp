# PROMPT TEMPLATE 16: Resolve Follow-Up PR #7 Code Review Findings on Evaluation & Documentation

You are an autonomous coding subagent assigned to execute a specific task in the `fpac-soil-mcp` repository for Plan 16.

## Repository Context & Rules

- Language: Python >=3.11 with standard typing and Pydantic v2 models.
- Environment & Package Manager: `uv` (use `uv run pytest ...`, `uv run ruff check .`, `uv run ruff format --check .`).
- Transport & Scope: Preserve stdio/SSE/HTTP FastMCP transport support, public tool names, parameter schemas, and statutory FPPA notices in `constants.py`.
- Testing Markers: Standard tests run with `uv run pytest -m "not live_network and not agent_eval"`. Network tests use `@pytest.mark.live_network`, and agent evaluation tests use `@pytest.mark.agent_eval`.
- Sandboxing: Any `pi` CLI invocation for agent evaluation runs in an isolated temporary directory with an ephemeral `.mcp.json` pointing back to `uv run --directory <repo_root> fpac-soil-mcp`.

## Git & Commit Discipline

- Follow Conventional Commits format with clean, descriptive summaries:
  - `fix(eval): align expected tools for point prompt test cases`
  - `fix(eval): extract tool calls and assistant text from structured json events`
  - `docs(readme): clarify corridor laydown geometry and complete scoring payload`
  - `docs(planning): update historical recon paths and state baseline counts`
- Do NOT include wave numbers, phase tags, or task IDs in git commit messages.
- Do not commit secrets, ephemeral agent logs, virtual environment directories, or build artifacts.

## Task Gate & Acceptance Verification

1. Read only the files specified in your task's `Files in scope`.
2. Locate the code anchors specified in `Grep Anchors`.
3. Apply surgical, robust modifications matching the task specification.
4. Run your task's `Acceptance Command` to confirm local test passage.
5. Run `uv run ruff check .` and `uv run ruff format --check .` to guarantee linter compliance.
6. Provide a concise completion summary reporting status, modified files, and verification output.
