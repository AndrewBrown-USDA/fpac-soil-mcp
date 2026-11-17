# STATE_56: Map AOI and Corridor State Hardening (issue #89)

Branch `fix/map-aoi-hardening1` (off `origin/main` 129a091), clone `~/fpac-soil-mcp-ui`.
Plan: `planning/EXECUTION_PLAN_56.md`. Goals: `planning/GOALS.md` G57-G66.

## Baseline (record before Wave 1; all offline)

- [ ] `make app-check` (ruff on a /tmp `git archive` copy; pytest count)
- [ ] `make app-frontend-check` (biome 0 errors / warning count; build OK)
- [ ] Node tests: `node --import tsx --test client/src/components/map/*.test.ts client/src/lib/chatExport.test.ts`
- [ ] `npm run test:local-auth`
- [ ] Playwright: `test:map-toolbar`, `test:corridor-map`, `test:map-tabs`, `test:map-legend`, `test:site-assessment`, `test:chat-export` (record pass counts; if Playwright browsers cannot run on serverless, record that and stop for a decision)

## Wave Board

| Wave | Task | Status | Commit | Notes |
|---|---|---|---|---|
| 1 | 56.1.1 Triage issue #89 against main | pending | | Triage gate: rewrite Waves 3-8 specs, show user |
| 2 | 56.2.1 Offline AOI-state test fixture | pending | | |
| 2 | 56.2.2 Record the notice rule in ADR 0016 | pending | | |
| 3 | 56.3.1 D backend: notice from MCP only | pending | | |
| 3 | 56.3.2 D frontend: invalid-notice display; attach failed summary | pending | | |
| 4 | 56.4.1 E: keep geometry context through stream retry | pending | | |
| 5 | 56.5.1 A: Edit-mode changes update attached geometry | pending | | |
| 6 | 56.6.1 B1: chat-scoped AOI/corridor context | pending | | |
| 7 | 56.7.1 B2: drop late results; abort outline | pending | | |
| 8 | 56.8.1 C: Undo / Clear / Detach symmetry | pending | | |
| 9 | 56.9.1 Integrated validation and ADR sweep | pending | | |
| 10 | 56.10.1 Post-SDA manual and deployed checks | pending | | Non-blocking; trigger: SDA available |

## Task Reports
