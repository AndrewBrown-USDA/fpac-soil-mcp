# Worker Prompt Template: Wave Orchestration 10

You are an autonomous worker agent executing a task within Wave Orchestration 10 (Code Smell Remediation & Refactoring) for the `fpac-soil-mcp` repository.

## Instructions

1. Read your assigned task specification in `planning/EXECUTION_PLAN_10.md` and check `planning/STATE_10.md`.
2. Follow all project conventions documented in `AGENTS.md`.
3. Only edit files listed in your task's `Files in scope`.
4. Do not touch or modify files marked in constraints.
5. Adhere to strict typing with Pydantic and Python 3.11+ type annotations.
6. Verify your changes using your task's acceptance command before concluding.
7. Run Ruff lint and format:
   ```powershell
   uv run ruff check .
   uv run ruff format --check .
   ```
8. Write conventional, one-sentence git commits without wave numbers (e.g. `refactor(clients): extract shared http request retry helper`).
