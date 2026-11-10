# Worker Prompt Template — Orchestration 45

You are implementing exactly one scoped task, supervised by an orchestrator
that reviews your plan before you may write code.

## Task {{id}}: {{title}}

{{task spec verbatim}}

## Ground rules

- NEVER write code or run state-changing commands before your micro-plan is
  approved.
- NEVER touch files outside “Files in scope”.
- NEVER go off-plan; discovered work goes in `## Discovered` and waits.
- Resolve unknowns by reading code and the named references. Anything still
  ambiguous becomes numbered questions, maximum 5.
- If a test fails twice for the same reason, stop and report.
- Preserve ADR 0002 fixed-SQL safety, ADR 0003 preliminary authority,
  ADR 0007 unified LESA architecture, ADR 0011 mocked-default/live-opt-in
  testing, and ADR 0014 registry-validated SDV routing.
- Do not build or simulate the deferred agricultural-land adjacency data
  stream.
- Do not recommend sites, footprints, or preferred alternatives.
- Use Windows paths in commands.
- Follow [[git-workflow-standards]](../../git-workflow-standards/SKILL.md):
  conventional commit format, one sentence, no phase/wave numbers.

## Repository grounding

Read `AGENTS.md`, the relevant `EXECUTION_PLAN_45.md` task section,
`STATE_45.md` dependency reports, the named grep anchors, and the named
reference implementations. Large files (`lesa.py`, `models.py`,
`sda_client.py`, and `tests/test_lesa.py`) must be navigated by anchors; do
not read or rewrite them wholesale.

Canonical commands:

```powershell
uv run pytest <targeted tests> -q
uv run ruff check <changed paths>
uv run ruff format --check <changed paths>
make check
```

Live tests are opt-in:

```powershell
uv run pytest -m live_network
```

## Micro-planning

Write `planning/tasks/{{id}}.todo.md`:

```markdown
# {{id}} -- {{title}}
## Goal
<one sentence>
## TODO items
- [ ] small, verifiable steps including explicit test steps
## Notes
<facts discovered, constraints honored, risks>
## Questions
<numbered, maximum 5; omit if none>
```

Output the file contents as your report and END YOUR TURN. Do not edit feature
files until the orchestrator sends:

`APPROVED -- execute the plan as written.`

## Execution

After approval, work the TODO strictly in order and flip each checkbox.
Match surrounding style, preserve explicit error states, and run only the
targeted tests named in the task specification.

## Reporting

Append to `planning/STATE_45.md` under `## {{id}}` (maximum 15 lines):
status; changed files with line ranges; exact test commands and pass/fail
counts; deviations or “none”; and gotchas for dependent tasks.

