# Worker Prompt Template — Plan 34

You are implementing exactly one scoped task, `{{TASK_ID}} — {{TASK_TITLE}}`, from `planning/EXECUTION_PLAN_34.md` in the fpac-soil-mcp repository. An orchestrator reviews your plan before you may write code.

## Read first

- `AGENTS.md`
- `docs/decisions/0010-public-payload-pii-detection-and-sanitization.md`
- `docs/decisions/0011-mocked-default-live-opt-in-test-architecture.md`
- `planning/EXECUTION_PLAN_34.md`: Goal & Scope, Decision log (D1-D6), Recon log, Shared contracts (K1-K4), Hazards (H1-H6), and your task spec
- `planning/STATE_34.md` reports for your dependency tasks
- the grep anchors and reference implementation named in your spec (do not read large files whole)
- `[[git-workflow-standards]](../../git-workflow-standards/SKILL.md)` when available

Do not read or edit `planning/EXECUTION_PLAN_33.md`, `PROMPT_TEMPLATE_33.md`, or `STATE_33.md` except to look up a cited run id; Plan 33 is frozen (D5).

## Assigned task specification

{{TASK_SPEC}}

## Ground rules (non-negotiable)

- NEVER write code or run state-changing commands before your plan is approved.
- NEVER touch files outside "Files in scope"; if required, STOP and report.
- NEVER go off-plan; discovered work goes in `## Discovered` and waits.
- NEVER assume: resolve unknowns by reading code in Analysis; anything still ambiguous becomes numbered questions (max 5) in your plan report.
- Honor shared contracts K1-K4 exactly; later tasks depend on them.
- `eval/databricks/` never imports `run_evals` or `test_agent_eval`; `eval/common/` imports neither Pi nor Databricks code. Keep mlflow imports lazy (inside functions).
- Do not add `__init__.py` under `eval/` except `eval/common/`. Keep test file basenames unique.
- No network calls in offline tests. Only 34.4.1 is LIVE, and it runs serially.
- TOOL span payloads pass through `privacy.sanitize_public_payload` before recording. The AGENT span records plain text via `@mlflow.trace` and is not sanitized (D1). T1 runs only on known synthetic or public cases.
- If a test fails twice for the same reason, stop and report — do not thrash.

## [Worker] Analysis

Confirm dependency tasks are `done` in `STATE_34.md`. Record verified facts (actual line numbers, signatures, current behavior) in your Notes.

## [Worker] Micro-planning

Write `planning/tasks/{{TASK_ID}}.todo.md`:

```markdown
# {{TASK_ID}} -- {{TASK_TITLE}}
## Goal        <one sentence>
## TODO items  - [ ] small, verifiable steps incl. explicit test steps (<=12)
## Notes       <facts discovered in Analysis, constraints honored, risks>
## Questions   <numbered, max 5, omit if none>
```

Output the file contents as your report, send `READY: {{TASK_ID}} — plan written, dependencies verified`, and END YOUR TURN.

## [Worker] Execution (only after `APPROVED`)

Work the TODO strictly in order, flipping `- [ ]` to `- [x]`. Match surrounding style (Ruff, line length 100, py311). Run only the acceptance commands in your spec, with this Workspace recipe:

```sh
UV_PROJECT_ENVIRONMENT=/tmp/fpac-venv PYTHONDONTWRITEBYTECODE=1 uv run [--group eval-databricks] pytest -p no:cacheprovider <files> -q
UV_PROJECT_ENVIRONMENT=/tmp/fpac-venv uv run ruff check --extend-ignore EXE002 <paths>
UV_PROJECT_ENVIRONMENT=/tmp/fpac-venv uv run ruff format --check <paths>
```

For a no-group check use a separate env and `--exact`: `UV_PROJECT_ENVIRONMENT=/tmp/fpac-venv-nogroup uv run --exact pytest ...`. Write files only through the workspace edit tool (shell writes to `/Workspace` are blocked).

## [Worker] Reporting

Append to `planning/STATE_34.md` under `## {{TASK_ID}}` (<=15 lines):

```text
Status: done | blocked
Changes:
- <file>: <meaningful change> (line ranges)
Validation:
- <exact command>: <pass/fail counts>
Deviations:
- none, or explain
Gotchas for dependents:
- none, or list
```

Commit only when the orchestrator requests it: conventional format, one sentence, domain scope (`fix(eval):`, `test(eval):`, `docs(eval):`, `docs(planning):`), no orchestration, wave, or task numbers.

## Gate messages

- Plan ready: `READY: <task-id> — plan written, dependencies verified`
- Completion: `DONE: <task-id> — <short result>`
- Blocked: `BLOCKED: <task-id> — <specific blocker and evidence>`
- Live run result (34.4.1 only): `LIVE-RESULT: 34.4.1 — run <id>, scorer table in report`

## Escalation (orchestrator-enforced)

1. Micro-plan off-spec twice -> orchestrator writes the micro-TODO and hands it to you as fixed input.
2. Acceptance fails after one retry (`FAILED VERIFICATION: ...`) -> task re-run on a mid-tier model.
3. Missing or malformed report -> one retry with feedback, then mid-tier re-run.
4. Needing out-of-scope edits is a decomposition bug -> stop; the orchestrator re-scopes the plan.
