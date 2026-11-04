# Orchestration 44 State

## Baseline

- **Repository:** workspace clone `/Workspace/Users/andrew.g.brown@usda.gov/fpac-soil-mcp`; edits and commits happen there; gates run in `/tmp` clones (D8).
- **Branch:** `feature/agent-app-map2` off `origin/main` 06525de (PR #75 and PR #74 merged); not pushed.
- **Plan date:** 2026-11-04; approved by the user 2026-11-04.
- **Agent app:** `agent-fpac-soil-openai-sdk` RUNNING, git `main`, `auto_deploy: true`, active deployment 06525de.
- **MCP server app:** `mcp-fpac-soil` RUNNING, deployed 2026-10-21 from `/Workspace/Users/Groups/team-03/fpac-soil-mcp` (predates Plan 43).
- **Last known suite results (from STATE_43 and the PR #75 gate; not yet re-run on 06525de):** root offline 599+ passed / 3 skipped; live 41 passed / 1 pre-existing SDA "kill state" failure / 3 skipped; frontend biome 0 errors / 10 warnings, client build OK with the MapLibre worker asset.
- [ ] **Pre-wave-1 baseline on 06525de** (fresh `/tmp/p44`): root `make check`, `make test-live`, `make app-check`, `make app-frontend-check`. Record counts here before 44.1.1.

## Wave board

| Wave | Executor | Task | Status |
|---|---|---|---|
| 1 | Genie Code | 44.1.1 | pending |
| 1 | User + Genie Code | 44.1.2 | pending |
| 1 | gate | root check, app-check | pending |
| 2 | Genie Code | 44.2.1 | pending |
| 2 | Genie Code | 44.2.2 | pending |
| 2 | gate | root check, app-check, test-live | pending |
| 3 | Genie Code | 44.3.1 | pending |
| 3 | Genie Code | 44.3.2 | pending |
| 3 | gate | root check, app-check, test-live | pending |
| 4 | Genie Code | 44.4.1 | pending |
| 4 | gate | root check, app-check, test-live | pending |
| 5 | Genie Code | 44.5.1 | pending |
| 5 | User + Genie Code | 44.5.2 | pending |
| 5 | gate | root check, app-check | pending |
| 6 | Genie Code | 44.6.1 | pending |
| 6 | gate | root check, app-check, app-frontend-check | pending |
| 7 | Genie Code | 44.7.1 | pending |
| 7 | gate | root check, app-check, app-frontend-check | pending |
| 8 | User + Genie Code | 44.8.1 | pending |
| 8 | Genie Code | 44.8.2 | pending |
| 8 | gate | root check, app-check, app-frontend-check | pending |
| 9 | Genie Code | 44.9.1 | pending |
| 9 | Genie Code | 44.9.2 | pending |
| 9 | gate | root check, app-check, app-frontend-check | pending |
| 10 | User + Genie Code | 44.10.1 | pending |
| 11 | Genie Code | 44.11.1 | pending |
| 12 | Genie Code + User | 44.12.1 | pending |
| 12 | gate | all suites | pending |

## Task Reports

<!-- Append one report per task (<=15 lines): status, files, commands/results, deviations, gotchas, commit. -->
