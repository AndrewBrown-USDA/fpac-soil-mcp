# TODO

## Goal
Apply the three open Copilot review corrections to PR #47's master-plan research note and create one documentation update commit.

## Tasks

### 1. Correct orchestration classification
- [x] Change the summary count from Plans 28-36 to Plans 28-30 and 33-36.
- [x] State that 7 of the last 10 orchestrations concern clients, evaluation, or deployment.
- [x] Keep Plans 31 and 32 classified as Phase 4 server productivity-index work.

### 2. Correct Phase 7 maintenance status
- [x] Replace the stale raw-`JSONDecodeError` claim with the delivered `SDAServiceUnavailableError` behavior.
- [x] Cite `SDAClient._execute_query()` and its regression test as implemented Phase 7 hardening.
- [x] Ensure the proposed Phase 7 master-plan edit records this work as delivered rather than backlog.

### 3. Correct T1 topology
- [x] Describe the agent app model route as AI Gateway.
- [x] Describe current T1 evaluation as using `WorkspaceClient().serving_endpoints.get_open_ai_client()`.
- [x] Record T1 migration to AI Gateway as pending instead of implying it is complete.

### 4. Validate the documentation
- [x] Check Markdown footnote references and definitions.
- [x] Run `git diff --check`.
- [x] Verify the final diff addresses all three PR #47 review threads without unrelated changes.

### 5. Commit the review fixes
- [x] Create one Conventional Commit containing only the corrected research note.
- [x] Exclude this operational `TODO.md` from the commit.
- [x] Verify the commit contents and report the commit hash.

## Notes
- Scope is `planning/RESEARCH_EVAL_AGENT_WORKBENCH_TRACKS.md` only.
- Do not modify production code, `planning/MASTER_PLAN.md`, ADRs, or execution plans.
- The review findings are low severity and documentation-only.
