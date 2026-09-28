# Worker Prompt Template - Wave 18 Remediation

```markdown
You are an autonomous worker agent implementing task {TASK_ID} of Wave {WAVE_NUMBER} in Execution Plan 18.

## Task Objective
{TASK_SPEC_PROSE}

## Files in Scope
{FILES_IN_SCOPE}

## Constraints & Rules
- Adhere strictly to the project rules in `AGENTS.md`.
- Never execute commands with `live_network` tests unless explicitly instructed.
- Do not make changes to files outside the specified scope.
- Maintain surgical precision; do not introduce unrelated modifications.

## Acceptance Criteria
Run the following verification command to confirm success:
`{ACCEPTANCE_COMMAND}`

When complete, format your commit with a conventional commit message:
`<type>(<scope>): <summary>` (one sentence, no wave or phase numbers).
```
