# PROMPT TEMPLATE 4: Phase 2 Polygon AOI Screening & Farmland Analysis

You are implementing exactly one scoped task in **Orchestration 4** of `fpac-soil-mcp`, supervised by an orchestrator that reviews your plan before you may write code.

## Task {{id}}: {{title}}

### Task Spec
{{task_spec}}

---

## Ground Rules (Non-Negotiable)

- **NEVER write code or run state-changing commands before your plan is approved.**
- **NEVER touch files outside "Files in scope"**; if required, STOP and report.
- **NEVER go off-plan**; discovered work goes in "## Discovered" in your task todo and waits.
- **NEVER assume**: resolve unknowns by reading code in Analysis; anything still ambiguous becomes numbered questions (max 5) in your plan report.
- **NEVER allow SQL injection**: SDA queries must use strictly parameterized templates and sanitized WKT/numeric identifiers.
- **NEVER claim binding determinations**: all outputs must carry preliminary screening notices under 7 CFR Part 657 / 658.
- If a test fails twice for the same reason, stop and report — do not thrash.

---

## [Worker] Phase 1 — Analysis

Read the following before writing your micro-plan:
1. `AGENTS.md` and repository conventions in `pyproject.toml`.
2. Relevant sections of `planning/MASTER_PLAN.md` (Phase 2) and `planning/RESEARCH_PUBLIC_APIS_AND_INTERPRETATIONS.md`.
3. `planning/STATE_4.md` for baseline and dependency task reports.
4. Named grep anchors and reference implementations in your task spec.

---

## [Worker] Phase 2 — Micro-Planning

Write `planning/tasks/{{id}}.todo.md` with:
```markdown
# {{id}} — {{title}}

## Goal
<One sentence defining the task outcome>

## TODO Items
- [ ] 1. Small verifiable step
- [ ] 2. Next step ...
- [ ] N. Targeted test execution

## Notes
<Facts discovered in Analysis, constraints honored, hazards noted>

## Questions
<Numbered, max 5, omit if none>
```

Output the file contents as your report and **END YOUR TURN**. Wait for orchestrator approval.

---

## [Worker] Phase 3 — Execution

Once you receive:
`APPROVED — execute the plan as written. [Answers to any questions]`

1. Work the TODO items strictly in order, flipping `- [ ]` to `- [x]`.
2. Match surrounding code style, type hinting, and Pydantic conventions.
3. Run **only the targeted tests** named in your task specification.
4. If an unexpected blocker occurs, stop and report.

---

## [Worker] Phase 4 — Reporting

Append a concise report (≤15 lines) to `planning/STATE_4.md` under `## {{id}}`:
```markdown
## {{id}}
- **Status**: Complete.
- **Files changed**: `<path>` (lines X-Y), ...
- **Targeted tests**: `<command>` -> X passed in Ys.
- **Deviations**: None.
- **Gotchas for dependent tasks**: <Key takeaways or "None">.
```
