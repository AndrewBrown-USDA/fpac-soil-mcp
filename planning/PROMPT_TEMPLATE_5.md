# PROMPT TEMPLATE 5: Exact SSURGO Spatial Clipping, Live Integration & Manifest Alignment

You are executing a task in the **fpac-soil-mcp** repository under wave-orchestration.

## Repository Conventions

- **Conventions files**: Read `AGENTS.md` and `planning/MASTER_PLAN.md` before making changes.
- **Python standards**: Python >=3.11, strict typing, Pydantic v2 schemas, `uv` for package management, `ruff` for linting and formatting.
- **Spatial queries**: Pattern-match against `soilDB::SDA_spatialQuery` in `D:\workspace\soilDB\R\SDA-spatial.R`.
- **Regulatory constraints**: Preserve all preliminary screening disclaimers and limitations (7 CFR § 658, Form AD-1006 / NRCS-CPA-106).
- **Test execution**: Run `uv run pytest -m "not live_sda"` for offline validation; run `uv run pytest -m live_sda` only for live integration tests.

## Git Workflow Standards

- Follow conventional commits format: `<type>(<scope>): <subject>`.
- Keep commit message titles to one sentence (imperative mood, lowercase, no period at end).
- Do not mention wave or phase numbers in commit messages.
- Always include the standard Co-authored-by trailer.

## Assigned Task

Task ID: `{{TASK_ID}}`
Task Title: `{{TASK_TITLE}}`
Files in Scope: `{{FILES_IN_SCOPE}}`
Depends on: `{{DEPENDS_ON}}`

## Task Specification

{{TASK_SPEC}}

## Verification & Acceptance

Run the targeted acceptance command:
```powershell
{{ACCEPTANCE_COMMAND}}
```

Verify lint and formatting:
```powershell
uv run ruff check {{FILES_IN_SCOPE}}
uv run ruff format --check {{FILES_IN_SCOPE}}
```
