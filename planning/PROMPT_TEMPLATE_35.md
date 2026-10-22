# Worker Prompt Template — Plan 35

You are implementing exactly one scoped task, `{{TASK_ID}} — {{TASK_TITLE}}`, from `planning/EXECUTION_PLAN_35.md` in the fpac-soil-mcp repository. An orchestrator reviews your plan before you may write code.

## Read first

- `AGENTS.md` (root) and `apps/agent-fpac-soil-openai-sdk/AGENTS.md`
- `docs/decisions/0011-mocked-default-live-opt-in-test-architecture.md`
- `planning/EXECUTION_PLAN_35.md`: Goal & Scope, Decision log (D1-D11), Recon log, Shared contracts (K1-K4), Hazards (H1-H8), Judgment calls (J1-J3), and your task spec
- `planning/STATE_35.md` reports for your dependency tasks
- the grep anchors and reference implementation named in your spec (do not read large files whole)
- `[[git-workflow-standards]](../../git-workflow-standards/SKILL.md)` when available

Do not edit earlier plans (`EXECUTION_PLAN_34.md` and below) or anything under `eval/` or `src/`.

## Assigned task specification

{{TASK_SPEC}}

## Ground rules (non-negotiable)

- NEVER write code or run state-changing commands before your plan is approved.
- NEVER touch files outside "Files in scope"; if required, STOP and report.
- NEVER go off-plan; discovered work goes in `## Discovered` and waits.
- NEVER assume: resolve unknowns by reading code in Analysis; anything still ambiguous becomes numbered questions (max 5) in your plan report.
- Honor shared contracts K1-K4 exactly; later tasks depend on them.
- `agent_server/config.py` stays pure (stdlib only). Do not edit `agent_server/utils.py`, `history.py`, `start_server.py`, `scripts/`, `manifest.yaml`, or the app `pyproject.toml`.
- No network calls in tests. Never call a real model endpoint or MCP server; patch `McpServer`, `Runner`, `WorkspaceClient`. Importing `agent_server.agent` needs the dummy Databricks env from `tests/conftest.py` (H1). The app has no pytest-asyncio: use `asyncio.run` (H8).
- Never stage or commit `apps/agent-fpac-soil-openai-sdk/uv.lock` (H4). Stage by explicit path.
- Never run `databricks bundle deploy`, `apps deploy`, or permission changes (D9). Only 35.5.1 touches the deployed app, and it is manual.
- If a test fails twice for the same reason, stop and report — do not thrash.

## [Worker] Analysis

Confirm dependency tasks are `done` in `STATE_35.md`. Record verified facts (actual line numbers, signatures, current behavior) in your Notes.

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
# app tests (run from apps/agent-fpac-soil-openai-sdk)
UV_PROJECT_ENVIRONMENT=/tmp/agent-venv PYTHONDONTWRITEBYTECODE=1 uv run --python 3.11 pytest -p no:cacheprovider <files> -q
# root tests (run from repo root)
UV_PROJECT_ENVIRONMENT=/tmp/fpac-venv PYTHONDONTWRITEBYTECODE=1 uv run --group eval-databricks pytest -p no:cacheprovider -q
# ruff (run from repo root; pass apps/ files explicitly, H3)
UV_PROJECT_ENVIRONMENT=/tmp/fpac-venv uv run ruff check --extend-ignore EXE002 <paths>
UV_PROJECT_ENVIRONMENT=/tmp/fpac-venv uv run ruff format --check <paths>
```

Write files only through the workspace edit tool (shell writes to `/Workspace` are blocked).

## [Worker] Reporting

Append to `planning/STATE_35.md` under `## {{TASK_ID}}` (<=15 lines):

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

Commit only when the orchestrator requests it. Format: conventional, one sentence, domain scope (`feat(agent-app):`, `test(agent-app):`, `build(lint):`, `docs(agent-app):`, `docs(planning):`), and no orchestration, wave, or task numbers.

## Gate messages

- Plan ready: `READY: <task-id> — plan written, dependencies verified`
- Completion: `DONE: <task-id> — <short result>`
- Blocked: `BLOCKED: <task-id> — <specific blocker and evidence>`
- Live result (35.5.1 only): `LIVE-RESULT: 35.5.1 — <n>/3 prompts pass, trace ids in report`

## Escalation (orchestrator-enforced)

1. Micro-plan off-spec twice -> orchestrator writes the micro-TODO and hands it to you as fixed input.
2. Acceptance fails after one retry (`FAILED VERIFICATION: ...`) -> task re-run on a mid-tier model.
3. Missing or malformed report -> one retry with feedback, then mid-tier re-run.
4. Needing out-of-scope edits is a decomposition bug -> stop; the orchestrator re-scopes the plan.
