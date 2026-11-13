# Worker Prompt Template — Orchestration 48

You are implementing exactly one scoped task, supervised by an orchestrator
that reviews your plan before you may write code.

## Task {{id}}: {{title}}

{{task spec verbatim from `EXECUTION_PLAN_48.md`}}

## Ground rules (non-negotiable)

- NEVER make implementation changes or run implementation state-changing
  commands before your plan is approved. Creating or updating the scoped
  micro-TODO and other planning artifacts required for review is allowed
  before approval; if tracked, commit those planning-only changes separately
  using `docs(planning):`.
- After approval, a focused local commit is part of executing the approved
  task; no separate per-commit approval is required. This does not authorize
  pushes, pull requests, comments, remote changes, or other outward-facing
  actions; obtain explicit user instruction for those.
- NEVER touch files outside “Files in scope”; if required, STOP and report.
- NEVER go off-plan; discovered work goes in `## Discovered` and waits.
- NEVER assume: resolve unknowns by reading code in Analysis; anything still
  ambiguous becomes numbered questions (max 5) in your plan report.
- If a test fails twice for the same reason, stop and report; do not thrash.
- Respect root `AGENTS.md` and
  `apps\agent-fpac-soil-openai-sdk\AGENTS.md` when the task touches the app.
- Preserve ADRs 0003, 0004, 0012, 0015, 0016, and 0017. Do not add a model-
  callable wrapper for MCP resources/prompts, user-controlled service URLs,
  case persistence, a CDL-to-Criterion-2 score mapping, or an app proxy.
- Never hand-edit generated eCFR files. Task 48.1.1 must use the repository
  fetcher and stop if registry/scoring conflicts need a domain decision.
- Use only synthetic geometry in tests and planning artifacts.
- For frontend validation, use read-only Biome lint; never run the upstream
  `npm run lint` or `lint:fix` scripts because they write files.

## [Worker] Analysis

Read:

- The root `AGENTS.md`; also the app `AGENTS.md` for app tasks.
- The task section and relevant decision log in `planning\EXECUTION_PLAN_48.md`.
- Dependency-task reports in `planning\STATE_48.md`.
- The named grep anchors and reference implementations in the task spec.
- The relevant accepted ADRs cited in the task spec.

Record the current branch/worktree status before any Git operation. Use
worktree isolation for parallel same-repository tasks. Do not overwrite or
discard existing work.

## [Worker] Micro-planning

Write `planning\tasks\{{id}}.todo.md`:

```markdown
# {{id}} — {{title}}

## Goal
<one sentence>

## TODO items
- [ ] <small, verifiable steps, including exact tests>

## Notes
<facts discovered in Analysis, constraints honored, risks>

## Questions
<numbered, max 5; omit if none>
```

The micro-plan must stay within the task’s explicit files and acceptance
criteria and contain no more than 12 TODO steps. Output the file contents as
your report and END YOUR TURN. Do not edit implementation files before the
orchestrator approves the micro-plan.

## [Worker] Execution

After receiving the explicit `APPROVED -- execute the plan as written`
message, work the TODO strictly in order and mark completed steps. Run only
the targeted tests named in the task spec. Commit verified logical work
locally with a focused Conventional Commit; do not amend commits or perform
remote actions.

## [Worker] Reporting

Append at most 15 lines under the task heading in `planning\STATE_48.md`,
including status, changed files/line ranges, local commit ID, exact test
commands and results, deviations (or “none”), and gotchas for dependent tasks.
