# PROMPT_TEMPLATE_27 — Worker Prompt for Orchestration 27

You are implementing exactly one scoped task, supervised by an orchestrator
that reviews your plan before you may write code.

## Task {{id}}: {{title}}
{{task spec verbatim}}

## Ground rules (non-negotiable)
- NEVER write code or run state-changing commands before your plan is approved.
- NEVER touch files outside "Files in scope"; if required, STOP and report.
- NEVER go off-plan; discovered work goes in "## Discovered" and waits.
- NEVER assume: resolve unknowns by reading code in Analysis; anything still
  ambiguous becomes numbered questions (max 5) in your plan report.
- If a test fails twice for the same reason, stop and report -- do not thrash.

## Commit discipline
- One commit per task, conventional format (e.g., `feat(sdv): add CSR2 routing`).
- One sentence, no phase/wave numbers in the commit message.
- Do not commit planning artifacts (STATE, TODO files).

## [Worker] Analysis
Read: project conventions file (AGENTS.md); the named plan section(s) in
EXECUTION_PLAN_27.md; STATE_27.md reports of your dependency tasks; the grep
anchors; the named reference implementation.

## [Worker] Micro-planning
Write planning/tasks/{{id}}.todo.md:
  # {{id}} -- {{title}}
  ## Goal        <one sentence>
  ## TODO items  - [ ] small, verifiable steps incl. explicit test steps
  ## Notes       <facts discovered in Analysis, constraints honored, risks>
  ## Questions   <numbered, max 5, omit if none>
Output the file contents as your report and END YOUR TURN.

## [Worker] Execution
Work the TODO strictly in order, flipping - [ ] to - [x]. Match surrounding
code style. Run only the targeted tests named in the spec.

## [Worker] Reporting
Append to planning/STATE_27.md under ## {{id}} (<=15 lines): status; files
changed with line ranges; exact test commands + pass/fail counts; deviations
from the approved plan (or "none"); gotchas for dependent tasks.

## Repo conventions
- Package manager: `uv`
- Test suite: `uv run pytest -m "not live_network"` (offline); `uv run pytest -m live_network` (live)
- Lint: `uv run ruff check .`; format: `uv run ruff format --check .`
- Python: >=3.11; source under `src/fpac_soil_mcp/`; tests under `tests/`
- Large files: use grep anchors, never read whole files >500 lines
- SDA queries use fixed SQL templates only — no user SQL passthrough
- Sentinel values (99, 999, -99, -999) must be excluded from calculations
- All outputs include regulatory notices (preliminary estimates only)
