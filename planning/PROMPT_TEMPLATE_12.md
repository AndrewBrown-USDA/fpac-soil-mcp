# PROMPT TEMPLATE 12: Production Dockerfile Hardening & FastMCP Prompt Suite Expansion

You are an autonomous coding subagent assigned to execute a specific task in the `fpac-soil-mcp` repository.

## Repository Context & Rules

- Language: Python >=3.11 with standard typing and Pydantic v2 models.
- Environment & Package Manager: `uv` (use `uv run pytest ...`, `uv run ruff check .`, `uv run ruff format --check .`).
- Transport & Scope: Preserve stdio/SSE/HTTP FastMCP transport support, public tool names, parameter schemas, and statutory FPPA notices in `constants.py`.
- Security & Container Rules: Multi-stage Docker build, non-root user `appuser` (UID 10001), standard signal handling, and clean `.dockerignore`.
- FastMCP Prompts: Maintain strict 7 CFR Parts 657 & 658 regulatory guardrails, no fabricated LE/SA scores, clear references to official NRCS workflows.
- No live network requests during offline unit tests; mock HTTP dependencies with `httpx.MockTransport` or unit fixtures.

## Git & Commit Discipline

- Follow Conventional Commits format with clean, descriptive summaries:
  - `build(docker): optimize multi-stage build with non-root appuser`
  - `feat(prompts): expand fppa fastmcp prompt suite`
  - `test(server): add comprehensive unit tests for expanded prompts`
  - `docs(readme): sync manifest and documentation for wave 12`
- Do NOT include wave numbers, phase tags, or task IDs in git commit messages.
- Do not commit secrets, virtual environment directories, caches, or build artifacts.

## Task Gate & Acceptance Verification

1. Read only the files specified in your task's `Files in scope`.
2. Locate the code anchors specified in `Grep Anchors`.
3. Apply surgical, robust modifications matching the task specification.
4. Run your task's `Acceptance Command` to confirm local test passage.
5. Run `uv run ruff check .` and `uv run ruff format --check .` to guarantee linter compliance.
6. Provide a concise completion summary reporting status, modified files, and verification output.
