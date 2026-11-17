# STATE_56: Map AOI and Corridor State Hardening (issue #89)

Branch `fix/map-aoi-hardening1` (off `origin/main` 129a091), clone `~/fpac-soil-mcp-ui`.
Plan: `planning/EXECUTION_PLAN_56.md`. Goals: `planning/GOALS.md` G57-G66.

## Baseline (record before Wave 1; all offline)

Recorded 2026-11-17 at f0af2fc (apps/ identical to 129a091), in a `git archive` copy at /tmp/p56, serverless, Node v22.20.0.

- [x] `make app-check`: ruff clean; pytest 297 passed, 2 warnings.
- [x] `make app-frontend-check`: biome 654 files, 0 errors, 10 warnings; build OK.
- [x] Node tests (map/*.test.ts + chatExport.test.ts): 36/36 pass.
- [x] `npm run test:local-auth`: 1/1 pass.
- [x] Playwright: map-toolbar 10/10, corridor-map 3/3 (one cold-start run 2/3, then 3/3 twice), map-tabs 2/2, map-legend 6/6, site-assessment 5/5, chat-export 3/3.
- Playwright on serverless needs: `PLAYWRIGHT_BROWSERS_PATH=/tmp/pw-browsers npx playwright install chromium`; missing libs (libatk-1.0, libatk-bridge-2.0, libatspi, libXdamage) fetched without root via `apt-get -o Dir::State::Lists=/tmp/apt/lists -o Dir::Cache=/tmp/apt/cache -o Debug::NoLocking=1 update/download`, extracted with `dpkg-deb -x` to /tmp/pwlibs, run with `LD_LIBRARY_PATH=/tmp/pwlibs/usr/lib/x86_64-linux-gnu CI=1`. Redo after a serverless restart.

## Wave Board

| Wave | Task | Status | Commit | Notes |
|---|---|---|---|---|
| 1 | 56.1.1 Triage issue #89 against main | done | (this commit) | Triage gate open: spec changes listed in TRIAGE_56.md, awaiting user |
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

## 56.1.1
- Status: done (docs only). Output `planning/TRIAGE_56.md`; micro-plan `planning/tasks/56.1.1.todo.md`.
- Verdicts: AOI A, B1, B2, C, D still apply; E suspected for both. Corridor: A unverified (change handler syncs; Edit select mode has no flags), B1/B2/C/D changed, E suspected.
- Already safe: AOI screening (`useScreening.ts` requestId guard + `setSummary` ref check); corridor screening supersession (requestId).
- Spot-check (orchestrator, independent grep): A-AOI select flags L259-272 and single `draw.on`; B2 `applyAreaAsAoi` L756, ShowOnMap `mapResult.show` L129; C-AOI `newAoiRef(), geometry, summary: null` L88; C-corridor `corridor_ref: corridorReference()` L693; E only server test is auth.test.ts. All match.
- Deviations: 11 row headings (E combined; B split into B1/B2) instead of 10.
- Gotchas: Playwright lib workaround above; corridor-map can flake on cold Vite start; user decision needed on corridor Undo before Wave 8.
