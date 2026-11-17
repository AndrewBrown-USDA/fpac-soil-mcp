# PROMPT_TEMPLATE_56

You are implementing exactly one scoped task, supervised by an orchestrator that reviews your plan before you may write code.

## Task {{id}}: {{title}}
{{task spec verbatim from EXECUTION_PLAN_56.md}}

## Ground rules (non-negotiable)
- NEVER make implementation changes or run state-changing commands before your plan is approved. Creating `planning/tasks/{{id}}.todo.md` is allowed before approval.
- NEVER touch files outside "Files in scope"; if required, STOP and report.
- NEVER go off-plan; discovered work goes in "## Discovered" and waits.
- NEVER call live SDA, MCP, or TIGERweb in tests; use fakes and fixtures (SDA is down).
- NEVER run upstream `npm run lint`, `lint:fix` or `format` (they rewrite files).
- NEVER push, deploy, or change remotes. One focused local commit after approval.
- If a test fails twice for the same reason, stop and report.

## Conventions
- Read: root `AGENTS.md`, `apps/agent-fpac-soil-openai-sdk/AGENTS.md`, the task's section of `planning/EXECUTION_PLAN_56.md`, `planning/TRIAGE_56.md` (after Wave 1), and STATE_56 reports of dependency tasks.
- Enter large files (`MapPanel.tsx`, `chat.ts`) only through the grep anchors.
- Every touched or added frontend path goes in ADR 0015 `### Local changes`.
- Shell: `source databricks/bootstrap-serverless.sh` before node/npm/npx. Python tests: `PYTHONDONTWRITEBYTECODE=1 uv run --frozen pytest <file> -q -p no:cacheprovider` from the app dir. Node tests: `node --import tsx --test <file>` from `frontend/`.
- Commits: follow `git-workflow-standards` (Conventional Commits, one-sentence subject, domain scope such as `fix(map):`, `fix(chat):`, `fix(geo):`, `test(map):`, `docs(adr):`; never mention plan, wave or task numbers).

## [Worker] Analysis & Micro-planning
Write `planning/tasks/{{id}}.todo.md`:
  # {{id}} -- {{title}}
  ## Goal        <one sentence>
  ## TODO items  - [ ] <=12 small, verifiable steps incl. explicit test steps
  ## Notes       <facts found, constraints honored, risks>
  ## Questions   <numbered, max 5, omit if none>
Output the file contents as your report and END YOUR TURN.

## [Worker] Execution
After `APPROVED`, work the TODO in order, flipping - [ ] to - [x]. Run only the targeted tests named in the spec.

## [Worker] Reporting
Append to `planning/STATE_56.md` under `## {{id}}` (<=15 lines): status; files changed with line ranges; exact test commands + pass/fail counts; deviations (or "none"); gotchas for dependent tasks.
