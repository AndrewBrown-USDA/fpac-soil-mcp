# PROMPT TEMPLATE 17: Phase 4 Implementation - Land Evaluation & Unified LESA Engine

You are an autonomous coding subagent assigned to execute a specific task in the `fpac-soil-mcp` repository for Plan 17 (Phase 4: Land Evaluation & Unified LESA Engine).

## Repository Context & Rules

- Language: Python >=3.11 with standard typing and Pydantic v2 models.
- Environment & Package Manager: `uv` (use `uv run pytest ...`, `uv run ruff check .`, `uv run ruff format --check .`).
- Transport & Scope: Preserve stdio/SSE/HTTP FastMCP transport support, public tool names, parameter schemas, and statutory FPPA notices in `constants.py`.
- Testing Markers: Standard tests run with `uv run pytest -m "not live_network and not agent_eval"`. Network tests use `@pytest.mark.live_network`, and agent evaluation tests use `@pytest.mark.agent_eval`.
- Statutory Rules: Under 7 CFR Part 658, Land Evaluation scores range from 0–100, Site Assessment scores range from 0–160, and Total LESA scores range from 0–260. A Total LESA score >= 160 triggers mandatory consideration of project alternatives under 7 CFR § 658.4(c)(2). Preserve preliminary-screening limitations in all responses.

## Git & Commit Discipline

- Follow Conventional Commits format with clean, descriptive summaries:
  - `feat(sda): add sdv metadata and dynamic productivity rating queries`
  - `feat(models): add unified lesa and relative rating domain models`
  - `feat(lesa): implement land evaluation normalization and unified scoring engine`
  - `feat(polygon): integrate candidate land evaluation into polygon analyzer`
  - `feat(tools): register calculate_preliminary_lesa mcp tool`
  - `test(lesa): add unit and benchmark tests for state productivity ratings`
  - `docs(readme): document preliminary lesa calculation and productivity index options`
- Do NOT include wave numbers, phase tags, or task IDs in git commit messages.
- Do not commit secrets, ephemeral agent logs, virtual environment directories, or build artifacts.

## Task Gate & Acceptance Verification

1. Read only the files specified in your task's `Files in scope`.
2. Locate the code anchors specified in `Grep Anchors`.
3. Apply surgical, robust modifications matching the task specification.
4. Run your task's `Acceptance Command` to confirm local test passage.
5. Run `uv run ruff check .` and `uv run ruff format --check .` to guarantee linter compliance.
6. Provide a concise completion summary reporting status, modified files, and verification output.
