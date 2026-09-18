# PROMPT TEMPLATE 7: Phase 3 Multi-County Corridor Analysis (CPA-106)

You are implementing exactly one scoped task in **Orchestration 7** of `fpac-soil-mcp`, supervised by an orchestrator that reviews your plan before you may write code.

## Task {{id}}: {{title}}

### Task Spec
{{task_spec}}

---

## Ground Rules (Non-Negotiable)

- **NEVER write code or run state-changing commands before your plan is approved.**
- **NEVER touch files outside "Files in scope"**; if required, STOP and report.
- **NEVER go off-plan**; discovered work goes in "## Discovered" in your task todo and waits.
- **NEVER assume**: resolve unknowns by reading code in Analysis; anything still ambiguous becomes numbered questions (max 5) in your plan report.
- **NEVER allow single-county simplification**: multi-county corridors must be partitioned dynamically and reconciled across county boundaries within 0.1% tolerance.
- **NEVER allow SQL injection**: SDA queries must use strictly parameterized templates and sanitized WKT/numeric identifiers.
- **NEVER claim binding determinations**: all outputs must carry preliminary screening notices under 7 CFR Parts 657 & 658.
- If a test fails twice for the same reason, stop and report — do not thrash.
- Commit discipline: follow conventional commits (`feat:`, `fix:`, `test:`, `docs:`) with single-sentence summaries and Co-authored-by trailer; do not include phase or wave numbers in commit titles.

---

## [Worker] Phase 1 — Analysis

Read the following before writing your micro-plan:
1. `AGENTS.md` and repository conventions in `pyproject.toml`.
2. Relevant sections of `planning/MASTER_PLAN.md` (Phase 3) and `planning/RESEARCH_ARCGIS_TOOLBOX_CROSSWALK.md`.
3. `planning/STATE_7.md` for baseline and dependency task reports.
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

Execute your plan step by step, updating `planning/tasks/{{id}}.todo.md` as you complete items. Run targeted test commands frequently.

When done, output your task report in the format:
```markdown
### {{id}}: {{title}}
- **Status**: Completed
- **Files Changed**: <comma-separated list of modified/created files>
- **Verification**: <command run and result summary>
- **Summary**: <2-3 sentence overview of changes delivered and any gotchas for dependent tasks>
```
