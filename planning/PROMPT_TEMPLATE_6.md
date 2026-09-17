# PROMPT TEMPLATE 6: Master Plan Integration & Parity Update

You are a worker agent executing a single task from **EXECUTION PLAN 6** (`planning/EXECUTION_PLAN_6.md`).
Your goal is to perform surgical, accurate edits to update `planning/MASTER_PLAN.md` and related planning artifacts in accordance with your assigned task specification.

---

## Assigned Task Context

**Task ID**: `{{TASK_ID}}`
**Title**: `{{TASK_TITLE}}`
**Files in Scope**: `{{FILES_IN_SCOPE}}`

---

## Instructions

1. **Read Task Spec**: Carefully read the full task specification in `planning/EXECUTION_PLAN_6.md` for Task `{{TASK_ID}}`.
2. **Review Research & Conventions**:
   - Primary reference: `planning/RESEARCH_ARCGIS_TOOLBOX_CROSSWALK.md`
   - Master plan: `planning/MASTER_PLAN.md`
   - Conventions: `AGENTS.md`
3. **Micro-Plan First**:
   - Create and populate `planning/tasks/{{TASK_ID}}.todo.md` with explicit checkbox items for each step of your task before modifying files.
4. **Execute Edits Surgically**:
   - Edit ONLY the files listed in your task scope.
   - Do not modify Python source files in `src/` or tests in `tests/`.
   - Ensure all citations, mathematical formulas, and crosswalk references to `RESEARCH_ARCGIS_TOOLBOX_CROSSWALK.md` are exact.
5. **Verify Work**:
   - Inspect diffs with `git diff {{FILES_IN_SCOPE}}`.
   - Run linter/formatting if applicable on markdown files.
6. **Report Completion**:
   - Check off all todo items in `planning/tasks/{{TASK_ID}}.todo.md`.
   - Update `planning/STATE_6.md` marking Task `{{TASK_ID}}` as `done` with worker summary in the Task Reports section.
   - Follow git workflow standards for single-sentence conventional commits.
