# PROMPT TEMPLATE 11: PR #5 Code Review Findings Remediation

You are an autonomous coding subagent assigned to execute a specific task in the `fpac-soil-mcp` repository.

## Repository Context & Rules

- Language: Python >=3.11 with standard typing and Pydantic v2 models.
- Environment & Package Manager: `uv` (use `uv run pytest ...`, `uv run ruff check .`, `uv run ruff format --check .`).
- Transport & Scope: Preserve stdio/SSE/HTTP FastMCP transport support, public tool names, parameter schemas, and statutory FPPA notices in `constants.py`.
- No live network requests during offline unit tests; mock HTTP dependencies with `httpx.MockTransport` or unit fixtures.

## Git & Commit Discipline

- Follow Conventional Commits format with clean, descriptive summaries:
  - `fix(http): distinguish None from empty retry_status_codes in request helper`
  - `test(http): add unit tests for shared http client helper`
  - `fix(nass): preserve positional args and 404 unavailable status`
  - `fix(corridor): support CountyPartitionGeometry instances in corridor analysis`
- Do NOT include wave numbers, phase tags, or task IDs in git commit messages.
- Do not commit secrets, virtual environment directories, caches, or build artifacts.

## Task Gate & Acceptance Verification

1. Read only the files specified in your task's `Files in scope`.
2. Locate the code anchors specified in `Grep Anchors`.
3. Apply surgical, robust modifications matching the task specification.
4. Run your task's `Acceptance Command` to confirm local test passage.
5. Run `uv run ruff check .` and `uv run ruff format --check .` to guarantee linter compliance.
6. Provide a concise completion summary reporting status, modified files, and verification output.
