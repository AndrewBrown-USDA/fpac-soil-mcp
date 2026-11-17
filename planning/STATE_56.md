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
| 1 | 56.1.1 Triage issue #89 against main | done | 43691a2 | User approved spec changes; applied in de8c367 |
| 2 | 56.2.1 Offline AOI-state test fixture | done | 8dbb325 | aoi-state 3/3; negative check fails as expected |
| 2 | 56.2.2 Record the notice rule in ADR 0016 | done | 07d950b | Markdown only; ADR 0003 unchanged |
| 3 | 56.3.1 D backend: notice from MCP only | done | a3e04d2 | pytest 305 |
| 3 | 56.3.2 D frontend: invalid-notice display; attach failed summary | done | 84a43ba | Show-on-map test moved to 56.7.1 |
| 4 | 56.4.1 E: keep geometry context through stream retry | done | 430a200 | Reproduced, then fixed |
| 5 | 56.5.1 A: Edit-mode changes update attached geometry | done | bc41661 | Corridor Edit inert (Discovered) |
| 6 | 56.6.1 B1: chat-scoped AOI/corridor context | done | 72ccf93 | Cold-start warm-up proposed |
| 7 | 56.7.1 B2: drop late results; abort outline | done | 9d4f37d | fakeGeo map shape fixed |
| 8 | 56.8.1 C: Undo / Clear / Detach symmetry | pending | | |
| 9 | 56.9.1 Integrated validation and ADR sweep | pending | | |
| 10 | 56.10.1 Post-SDA manual and deployed checks | pending | | Non-blocking; trigger: SDA available |
| 11 | 56.11.1 Discovered: keep geometry out of request logs | pending | | User: low priority; after all other waves |
| - | 56.12.1 Discovered: map tools waited for basemap tiles | done | 4a223b1, 5eb12f1 | User-approved 2026-11-17; was the cold-start flake |

## Task Reports

## 56.1.1
- Status: done (docs only). Output `planning/TRIAGE_56.md`; micro-plan `planning/tasks/56.1.1.todo.md`.
- Verdicts: AOI A, B1, B2, C, D still apply; E suspected for both. Corridor: A unverified (change handler syncs; Edit select mode has no flags), B1/B2/C/D changed, E suspected.
- Already safe: AOI screening (`useScreening.ts` requestId guard + `setSummary` ref check); corridor screening supersession (requestId).
- Spot-check (orchestrator, independent grep): A-AOI select flags L259-272 and single `draw.on`; B2 `applyAreaAsAoi` L756, ShowOnMap `mapResult.show` L129; C-AOI `newAoiRef(), geometry, summary: null` L88; C-corridor `corridor_ref: corridorReference()` L693; E only server test is auth.test.ts. All match.
- Deviations: 11 row headings (E combined; B split into B1/B2) instead of 10.
- Gotchas: Playwright lib workaround above; corridor-map can flake on cold Vite start; user decision needed on corridor Undo before Wave 8.

## 56.2.1
- Status: done, 8dbb325 `test(map): add offline AOI and corridor state fixture`.
- Files: new `client/aoi-state-fixture.html`, `client/src/components/map/aoi-state-fixture.tsx` (chat A/B buttons, `?chat=none`, hidden `fixture-state` probe), `playwright.aoi-state.config.ts` (port 5188), `tests/aoi-state/aoi-state.spec.ts` (`fakeGeo` with delayMs/fail/notice, `probe`, `pasteAoi`); `package.json` `test:aoi-state`; ADR 0015 entry.
- Tests: `npm run test:aoi-state` 3/3; negative check (fake `notice: null`) makes the summary test fail 1/1 as expected; map-toolbar 10/10; corridor-map 3/3; `make app-frontend-check` 657 files, 0 errors, 10 warnings, build OK.
- Deviations: none.
- Gotchas: `map-toolbar-fixture.tsx` and `map-legend-fixture.tsx` mount `MapPanel` without setting a chat id (grep: 0 `setChatId`). Once 56.6.1 disables input when `chatId` is null, they need one; 56.6.1's file scope now includes both (plan updated). `fakeGeo`'s `/api/geo/map` layer shape is unchecked against `inlineLayers`; verify it before 56.3.2/56.7.1 rely on it.

## 56.2.2
- Status: done, 07d950b `docs(adr): require the MCP regulatory notice for map screening results`.
- Files: ADR 0016 amendment blockquote (2026-11-17) and two `### Map screening route` bullets (Regulatory notice, Failed screening).
- Checks: diff read against D2/D3; ADR 0003 L31/L35 require the notice on all primary screening responses, no contradiction, unchanged.
- Deviations: the amendment names "Show on map" too; 56.3.2's spec now includes a Show-on-map null-notice test (message already at `MapPanel.tsx` L1124-1131).

## Wave 2 gate
- `make app-check` on the committed tree: ruff all checks passed; pytest 297 passed. Frontend gates as in 56.2.1. No regressions vs baseline.

## 56.3.1
- Status: done, a3e04d2 `fix(geo): require the MCP regulatory notice on map screening results`.
- Change: `_result_notice` returns `str | None`; missing, blank or non-string notice -> `None` on screen, corridor and map routes. `failed_chat_summary` kept.
- Tests: 3 geo files 80 passed; 8 new/changed tests fail against the old `geo.py` (negative check); `make app-check` 305 passed (297 + 8), ruff clean.
- Deviations: blank (whitespace-only) notice also treated as missing.

## 56.3.2
- Status: done, 84a43ba `fix(map): attach failed screening summaries and flag missing corridor notices`.
- Change: `useScreening.ts` `summaryToAttach` (valid+notice, or `screening_failed`); `MapPanel.tsx` summary effect uses it; `useCorridorScreening.ts` keeps null-notice results (results view shows invalid message). No change needed in `ScreeningResults.tsx` / `CorridorScreeningResults.tsx`.
- Tests: new `useScreening.test.ts` + `useCorridorScreening.test.ts` 8/8; Node total 44/44; aoi-state 6/6 (3 new); corridor-map 3/3; `make app-frontend-check` 659 files, 0 errors, 10 warnings, build OK.
- Negative check (old product code, new spec): failed-summary and corridor-null-notice cases fail; AOI missing-notice case passes (guards existing behavior).
- Deviations: Show-on-map null-notice test moved to 56.7.1 (fixture does not mount `ShowOnMapButton`; fixture outside scope); plan updated.

## Wave 3 gate
- Committed tree (84a43ba archive): `make app-check` ruff clean, pytest 305 passed; `make app-frontend-check` 0 errors, 10 warnings, build OK; Node 44/44; corridor-map 3/3; map-toolbar 10/10.
- aoi-state: first run after fresh `npm ci`/build 5 passed, 1 failed (test not captured); 3 reruns with `--retries=0` 6/6 each. Treated as a cold-start flake like the baseline corridor-map one; watch in Wave 4.

## 56.4.1
- Status: done, 430a200 `fix(chat): keep map geometry context through the stream fallback`.
- Bug real: the stream is teed into the resume cache and keeps running after the client disconnects; `res.on('close')` released both keys, so a later `generateText` fallback sent no `active_aoi` / `active_corridor`.
- Repro: extracted `bindRequestGeometry` with the old behaviour; new test (real registry + real `databricksFetch`, stubbed `fetch`) failed on the missing `active_aoi`, while the pre-release assertion in test 2 passed (injection itself worked).
- Fix: `bindRequestGeometry(body)` returns headers + idempotent `release()`; released in `execute` `finally` and the route's `catch`; no `close` listener.
- Tests: `test:chat-geometry` 3/3 (needs `--test-force-exit`: importing `chat.ts` leaves open handles); local-auth 1/1; Node 44/44; `make app-frontend-check` 0 errors, 10 warnings; server `tsc --noEmit` 2 errors before and after, none in touched files.
- Deviations: route-level test not used (needs OAuth provider, host, mock server); `execute` body left at upstream indentation inside the new `try` (ADR 0015 minimal diff).
- Discovered: `databricksFetch` logs the full request body (`Databricks request:`), including `custom_inputs.active_aoi` geometry. User (2026-11-17): not a priority; small fix, so added as 56.11.1 after all other waves.

## Wave 4 gate
- Committed tree (430a200 archive): `make app-check` ruff clean, pytest 305; `make app-frontend-check` 0 errors, 10 warnings, build OK; Node 44/44; chat-geometry 3/3; local-auth 1/1; corridor-map 3/3; map-toolbar 10/10.
- aoi-state: cold run 5/6. Failing test now identified: the first test, `getByRole('button', { name: 'Polygon' })` still disabled at the 5 s expect timeout while the cold Vite server loads the map. Warm rerun 6/6. Likely the same cause as the Wave 3 and baseline corridor-map cold-run failures (those were not captured). Proposed test-only fix: a longer timeout on the initial map-ready wait in the fixture specs (needs user approval; not in any task scope).

## 56.5.1
- Status: done, bc41661 `fix(map): keep Edit-mode AOI changes attached`.
- Root cause (differs from triage): Terra Draw 1.39 select mode already fires `finish` for drag, midpoint insert and vertex delete, but the `finish` handler removed every other snapshot feature, including Terra Draw's selection-point and midpoint features. After the first edit, midpoint/delete hit missing ids ("No feature with this id") and the AOI stopped updating.
- Fix: pure `mapControls.ts` `aoiFeaturesToRemove` (select finish -> nothing; draw finish -> previous polygon/rectangle only); `MapPanel.tsx` `finish` uses it. Edits still go through `replaceAoi` (new ref, summary dropped; ref stability is item C).
- Tests: Node 46/46 (2 new); new aoi-state Edit case (draw at known pixels, drag / midpoint / delete, no page errors); fails twice on old `MapPanel.tsx` at the midpoint step (expected 6 vertices, got 5). Corridor guard test: Edit corridor drag leaves the stored corridor unchanged.
- Discovered: Edit corridor cannot edit (select mode has no flags), so the button does nothing; needs a product decision. Cold-start flake also seen in 3 of 7 cold probe runs, even with a 30 s wait.

## Wave 5 gate
- Committed tree (bc41661): `make app-check` ruff clean, pytest 305; `make app-frontend-check` 0 errors, 10 warnings, build OK; Node 46/46; chat-geometry 3/3; local-auth 1/1; corridor-map 4/4; map-toolbar 10/10; aoi-state 7/7 (gate run). An earlier working-copy run had the first aoi-state test fail on the cold map-ready wait.

## 56.6.1
- Status: done, 72ccf93 `fix(map): scope AOI and corridor context to the open chat`.
- Fix: `chat.tsx` clears both chat ids on unmount; providers take `null` (no geometry, writes and cross-detach ignored, no attach event); `MapPanel.tsx` disables AOI/corridor drawing, paste (fieldset), Use-as-AOI, Undo, Clear and corridor removal with a status line, and leaves draw modes on chat loss. map-toolbar/map-legend fixtures set a chat id; aoi-state fixture adds Close fixture chat (test-only deviation).
- New chat: `NewChatPage` keeps `Chat` mounted and switches the URL with `replaceState`, so the id never goes null; a remount reloads from sessionStorage.
- Tests: 3 new aoi-state cases. Negative check: the no-chat and close-chat cases fail on the old code; A -> B -> A passes on old code (regression guard).
- Discovered: single-test Playwright runs failed 3 of 3 at the first map-ready wait (always a cold load); cold load about 5 s, and about 1 in 5 cold loads hang until reload. Proposed: Playwright warm-up globalSetup (open fixture, wait up to 30 s, reload if needed). Suspected (not verified): re-entering a chat re-attaches a corridor draft under a new `corridor_ref` (item C).

## Wave 6 gate
- Committed tree (72ccf93): `make app-check` ruff clean, pytest 305; `make app-frontend-check` 0 errors, 10 warnings, build OK; Node 46/46; chat-geometry 3/3; local-auth 1/1; aoi-state 10/10; corridor-map 4/4; map-toolbar 10/10; map-legend 6/6; map-tabs 2/2. No cold-start failure in the gate run.
- Missed: site-assessment was not in this gate; its fixture used `ActiveAoiProvider` with no chat id, so one test broke (fixed in 5eb12f1, see 56.12.1). Later gates run all Playwright suites, including site-assessment and chat-export.

## 56.12.1 (discovered: map readiness)
- Root cause of the "cold-start" flake: `MapPanel.tsx` set up layers and Terra Draw (and `mapReady`) in MapLibre `load`, which waits for every visible USGS basemap tile. In Playwright about 15% of loads (6/40) left some blocked tile requests pending forever, so `load` never fired; the page was otherwise healthy and a reload fixed it. In the app, one hung USGS tile did the same (reproduced by holding one tile: never ready; all tiles +6 s: ready at 7.2 s).
- Ruled out: Vite warmth (a globalSetup warm-up still failed; reverted, never committed), network (still hung with external DNS blocked). The earlier "1 in 5 hang" probe did not block tiles.
- Fix (user-approved): 4a223b1 `fix(map): enable drawing tools once the map style loads` (`map.once('style.load', ...)`; no `setStyle` in the code). Trial: 0/40 hangs, slowest 2.0 s cold. New aoi-state test holds every basemap tile: passes on the fix, fails on old `load` (warm server).
- 5eb12f1 `test(map): open a fixture chat in the site-assessment map fixture` (Wave 6 fixture gap).
- Gate (4a223b1 + fixture fix): `make app-check` pytest 305; `make app-frontend-check` 0 errors, 10 warnings; Node 46/46; chat-geometry 3/3; local-auth 1/1; aoi-state 11/11 (plus 2 runs with the Vite cache cleared, 11/11 each); corridor-map 4/4; map-toolbar 10/10; map-legend 6/6; map-tabs 2/2; site-assessment 5/5 (x2); chat-export 3/3.
- Not verified in the deployed app. Trade-off: tools can enable before the basemap shows; tile failures still show their own message.
- Branch pushed by the user 2026-11-17: `origin/fix/map-aoi-hardening1` at bd9fb8d (verified with ls-remote); upstream now the same-named branch. `origin/main` has moved to 50e0e13 since the branch point (129a091).

## 56.7.1
- Status: done, 9d4f37d `fix(map): drop map results that arrive after the chat or AOI changed`.
- Fix: `ShowOnMapButton.tsx` and `IdentifyPopup.tsx` (`AreaActions`) record chat id + `aoi_ref` at request start and drop the response if either changed (latest values from a ref); the outline uses a real `AbortController`, aborted on unmount (popup close); `MapPanel.tsx` resets corridor screening on chat change. AOI screening unchanged (already guarded).
- Fixture: test-only Show on map button bound to the current AOI, `data-shown` probe, `__mapJumpTo` camera hook. Spec: `fakeGeo` map layer fixed to `inline_geojson` + `feature_collection` (the old `inline` + `data` was dropped by `inlineLayers`, the Wave 1 gotcha); `pasteAoi` opens the panel only when closed.
- Tests: 8 new aoi-state cases. Negative check: the 5 late-result/abort cases fail on old code; control, null notice (moved from 56.3.2), AOI screening regression pass.

## Wave 7 gate
- Committed tree (9d4f37d): `make app-check` ruff clean, pytest 305; `make app-frontend-check` 0 errors, 10 warnings, build OK; Node 46/46; chat-geometry 3/3; local-auth 1/1; aoi-state 19/19; corridor-map 4/4; map-toolbar 10/10; map-legend 6/6; map-tabs 2/2; site-assessment 5/5; chat-export 3/3.
