# Worker Prompt Template — Plan 33

You are implementing exactly one scoped task, `{{TASK_ID}} — {{TASK_TITLE}}`, from `planning/EXECUTION_PLAN_33.md` in the fpac-soil-mcp repository. An orchestrator reviews your plan before you may write code.

## Read first

- `AGENTS.md`
- `docs/decisions/0003-preliminary-screening-authority-boundary.md`
- `docs/decisions/0010-public-payload-pii-detection-and-sanitization.md`
- `docs/decisions/0011-mocked-default-live-opt-in-test-architecture.md`
- `planning/EXECUTION_PLAN_33.md`: Decision log, Recon log, Shared contracts (C1-C5), Hazards (H1-H10), and your task spec
- `planning/STATE_33.md` reports for your dependency tasks
- the grep anchors and reference implementation named in your spec (do not read large files whole; `eval/run_evals.py` is ~950 lines and `eval/test_agent_eval.py` ~1270)
- `[[git-workflow-standards]](../../git-workflow-standards/SKILL.md)` when available

## Assigned task specification

{{TASK_SPEC}}

## Ground rules (non-negotiable)

- NEVER write code or run state-changing commands before your plan is approved.
- NEVER touch files outside "Files in scope"; if required, STOP and report.
- NEVER go off-plan; discovered work goes in `## Discovered` and waits.
- NEVER assume: resolve unknowns by reading code in Analysis; anything still ambiguous becomes numbered questions (max 5) in your plan report.
- Honor shared contracts C1-C5 exactly; parallel tasks depend on them.
- The Databricks tier (`eval/databricks/`) must never import `run_evals` or `test_agent_eval`. `eval/common/` imports neither Pi nor Databricks code.
- Do not add `__init__.py` anywhere under `eval/` except `eval/common/`. Keep test file basenames unique.
- No network calls in default offline tests. Live work happens only where the spec says LIVE, and only serially.
- Preserve the preliminary-screening limitation; no wording implying an official FPPA determination, LESA score, AD-1006, or NRCS-CPA-106.
- Route any recorded trace payloads through `privacy.sanitize_public_payload`.
- If a test fails twice for the same reason, stop and report — do not thrash.
- Never schedule or assume more than three concurrent workers; shared files are serialized.

## [Worker] Analysis

Read the files above. Confirm dependency tasks are `done` in `STATE_33.md`. Record facts you verified (actual line numbers, signatures, current behavior).

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

Work the TODO strictly in order, flipping `- [ ]` to `- [x]`. Match surrounding code style (Ruff, line length 100, py311). Run only the targeted acceptance commands in your spec. On the Workspace filesystem prefix pytest with `PYTHONDONTWRITEBYTECODE=1` and add `-p no:cacheprovider`.

## [Worker] Reporting

Append to `planning/STATE_33.md` under `## {{TASK_ID}}` (<=15 lines):

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

Commit only when the orchestrator requests it: conventional format, one sentence, domain scope (e.g. `fix(eval):`, `feat(eval):`, `test(eval):`, `docs(eval):`, `build(deps):`), no orchestration, wave, or task numbers.

## Gate messages

- Plan ready: `READY: <task-id> — plan written, dependencies verified`
- Completion: `DONE: <task-id> — <short result>`
- Blocked: `BLOCKED: <task-id> — <specific blocker and evidence>`
- Live task value table (33.4.1 only): `SIGNOFF-NEEDED: 33.4.1 — value table in report`

## Escalation (orchestrator-enforced)

1. Micro-plan off-spec twice -> orchestrator writes the micro-TODO and hands it to you as fixed input.
2. Acceptance fails after one retry (`FAILED VERIFICATION: ...`) -> task re-run on a mid-tier model.
3. Missing or malformed report -> one retry with feedback, then mid-tier re-run.
4. Needing out-of-scope edits is a decomposition bug -> stop; the orchestrator re-scopes the plan.
