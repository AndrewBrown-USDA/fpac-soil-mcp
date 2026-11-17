# EXECUTION_PLAN_56: Map AOI and Corridor State Hardening (issue #89)

Branch `fix/map-aoi-hardening1` off `origin/main` 129a091, in the workspace
clone `~/fpac-soil-mcp-ui`. Goals: `planning/GOALS.md` G57-G66.

## Goal & Scope

**Goal.** Close issue #89 ("Map panel AOI state hardening", items A-E) for
`apps/agent-fpac-soil-openai-sdk`, for both the area AOI and the corridor
context. The issue's line references are to 8c90f0d and predate many map
changes (corridor workflow, toolbar, geometry I/O), so the first stage triages
which items still apply and refreshes their anchors before any fix.

**In scope.**
- Triage of A-E against main 129a091, for AOI and corridor (G57).
- Offline test scaffolding for the affected flows (G58).
- A: Edit-mode changes keep attached geometry in sync (G59).
- B: chat-scoped state and stale async results (G60, G61).
- C: Undo / Clear / Detach symmetry (G62).
- D: regulatory-notice rule and `failed_chat_summary` (G63, G64).
- E: geometry context survives the chat-server stream retry (G65).
- ADR 0015 `### Local changes`, ADR 0016 (and 0003 if wording changes) (G66).

**Out of scope.** Live SDA or MCP calls in any acceptance step; deploying the
dev app; pushing; new map features beyond what A-E require; upstream lint
autofix scripts.

**Verbatim constraints (issue #89 and user).**
- "Order: A, then B, then C. D and E can be done in parallel."
- "Every frontend change must update the ### Local changes section of ADR 0015."
- "Frontend tests added" for every item.
- "currently SDA is down so we will need to test without live SDA access"
- "first stage of plan should triage and determine which need to be addressed"

## Decision Log (2026-11-17, the user)

- D1. Every item applies to both the area AOI and the corridor context.
- D2. Item D: the fallback limitation sentence may NOT stand in for the ADR 0003
  notice; the notice must come from MCP. Append `NON_PRIME_LIMITATION` only when
  an MCP notice exists; otherwise return `regulatory_notice: null` so the
  "Regulatory notice missing - treat this result as invalid" message fires.
  Record the rule in ADR 0016.
- D3. Item D: attach `failed_chat_summary` to the chat, scoped to the `aoi_ref`
  captured at screening start; the latest screening state replaces an earlier
  summary for the same ref. Corridor follows if triage finds an equivalent.
- D4. Execution: one Genie Code agent runs tasks serially in
  `~/fpac-soil-mcp-ui`, with a plan gate per task; one local commit per task;
  ask the user before every push. "Parallel" in the wave table means disjoint
  files only.
- D5. Acceptance: per wave, serially: the task's targeted tests,
  `make app-check`, `make app-frontend-check`, and the Playwright suites for the
  touched files. All offline (fakes, fixtures). Deployed-app check, manual
  browser pass and CI are Wave 10, run after SDA returns, and do not block the
  merge.
- D6. Plan approved by the user as drafted (2026-11-17). Open judgment calls
  carried into execution: corridor Undo for item C is confirmed with the user
  before Wave 8; item A approach is chosen in 56.5.1's micro-plan; if
  Playwright cannot run on serverless, the baseline stops for a decision.

## Wave Table

| Wave | Task | Title | Depends on | Files in scope (summary) |
|---|---|---|---|---|
| 1 | 56.1.1 | Triage issue #89 against main | - | `planning/TRIAGE_56.md` (new), `planning/STATE_56.md` |
| 2 | 56.2.1 | Offline AOI-state test fixture | 56.1.1 | new fixture page/tsx, Playwright config + spec, `package.json` script, ADR 0015 |
| 2 | 56.2.2 | Record the notice rule in ADR 0016 | 56.1.1 | `docs/decisions/0016-*.md` |
| 3 | 56.3.1 | D backend: notice from MCP only | 56.2.2 | `geo.py`, `test_geo_map.py`, `test_geo_screen.py`, `test_geo_corridor.py` |
| 3 | 56.3.2 | D frontend: invalid-notice display; attach failed summary | 56.2.1, 56.2.2 | `MapPanel.tsx` (summary effect), screening hooks/results, Node test, aoi-state spec, ADR 0015 |
| 4 | 56.4.1 | E: keep geometry context through stream retry | 56.2.1 | `server/src/routes/chat.ts`, `stream-fallback.ts`, new server test, `package.json` script, ADR 0015 |
| 5 | 56.5.1 | A: Edit-mode changes update attached geometry | 56.2.1 | `MapPanel.tsx` (Terra Draw setup), map tests, ADR 0015 |
| 6 | 56.6.1 | B1: chat-scoped AOI/corridor context | 56.5.1 | `ActiveAoiContext.tsx`, `ActiveCorridorContext.tsx`, `chat.tsx`, `MapPanel.tsx` (input gating), tests, ADR 0015 |
| 7 | 56.7.1 | B2: drop late results; abort outline | 56.6.1 | `ShowOnMapButton.tsx`, `IdentifyPopup.tsx`, `identify.ts`, `MapPanel.tsx`, screening hooks, tests, ADR 0015 |
| 8 | 56.8.1 | C: Undo / Clear / Detach symmetry | 56.5.1, 56.7.1 | `ActiveAoiContext.tsx`, `ActiveCorridorContext.tsx`, `MapPanel.tsx`, `ActiveAoiChip.tsx`, tests, ADR 0015/0016 |
| 9 | 56.9.1 | Integrated validation and ADR sweep | 56.3.1-56.8.1 (incl. 56.3.2) | `planning/STATE_56.md`, ADR 0015/0016 wording only |
| 10 | 56.10.1 | Post-SDA manual and deployed checks (non-blocking) | 56.9.1, SDA available | `planning/STATE_56.md`, `planning/evidence/` |

Waves 3 and 4 are independent of each other (issue: "D and E can be done in
parallel") but both edit ADR 0015, so they are sequenced. Waves 5-8 follow the
issue's A -> B -> C order and all edit `MapPanel.tsx`.

**Triage gate.** After Wave 1 the orchestrator rewrites the specs of Waves 3-8
from `TRIAGE_56.md` (anchors, dropped or reshaped items) and shows the user
the changes before Wave 2 starts. A task the triage marks obsolete becomes a
test-only task (prove the behavior, no code change) or is removed with the
user's agreement.

## Hazards (from recon at 129a091)

- `MapPanel.tsx` is 1165 lines; enter it only through the grep anchors below.
  `chat.ts` is 640 lines.
- The issue's line numbers are stale; never use them as anchors.
- Corridor: `useCorridorScreening.ts` L41 already rejects a response without a
  notice as "incomplete result", so a null notice shows an error, not
  `CorridorScreeningResults` L51's invalid message. 56.3.1 must make the
  user-visible outcome match D2 for both.
- Corridor screening (`screen_corridor`, `geo.py` L473) has no `chat_summary`
  at recon; D3 applies to the corridor only if triage finds an equivalent.
- Recon grep found no corridor Undo state (`previousCorridor`, `corridorUndo`);
  triage confirms whether corridor C means adding Undo for the corridor.
- Workspace FS: ruff reports false EXE002 (lint a `git archive` copy in /tmp);
  pytest in the workspace clone needs `PYTHONDONTWRITEBYTECODE=1` and
  `-p no:cacheprovider`. Every shell needing node/npm starts with
  `source databricks/bootstrap-serverless.sh`. `npm ci` and Playwright run in a
  /tmp copy of the committed tree; never edit there.
- Never run upstream `npm run lint`/`lint:fix`/`format` (they rewrite files).

## Task Specifications

Paths are relative to `apps/agent-fpac-soil-openai-sdk/` unless they start with
`planning/` or `docs/`. Follow the nested `AGENTS.md`. Every modified upstream
frontend file and every added frontend path is listed in ADR 0015
`### Local changes`. Frontend Node tests: from `frontend/`,
`node --import tsx --test <file>`. Python: from the app dir,
`PYTHONDONTWRITEBYTECODE=1 uv run --frozen pytest <file> -q -p no:cacheprovider`.

### 56.1.1 - Triage issue #89 against main

- **Files in scope:** create `planning/TRIAGE_56.md`; append to
  `planning/STATE_56.md`. No code edits.
- **Anchors:** see every anchor in Tasks 56.3.1-56.8.1; issue text in
  `planning/GOALS.md` G59-G65.
- **Spec:** For each item A-E x {AOI, corridor}, record: verdict
  (still-applies / changed / obsolete), evidence (file:line at 129a091 and a
  one-line quote), and the refreshed anchors. Confirm or refute each recon
  claim in Hazards. Write reproduction steps that need no SDA. Note any new
  defect of the same class (chat-scoped state, stale async results) as
  "Discovered"; do not widen scope.
- **Acceptance:** table has 10 rows (5 items x 2 contexts), each with evidence;
  orchestrator spot-checks 3 rows by grep.

### 56.2.1 - Offline AOI-state test fixture

- **Files in scope:** create `frontend/client/aoi-state-fixture.html`,
  `frontend/client/src/components/map/aoi-state-fixture.tsx`,
  `frontend/playwright.aoi-state.config.ts`,
  `frontend/tests/aoi-state/aoi-state.spec.ts`; edit `frontend/package.json`
  (add `test:aoi-state`); ADR 0015.
- **Reference implementations:** `map-toolbar-fixture.tsx`,
  `playwright.map-toolbar.config.ts`, `tests/map-toolbar/toolbar.spec.ts`,
  `corridor-map-fixture.tsx`.
- **Spec:** A fixture that mounts `ActiveAoiProvider`, the corridor provider and
  `MapPanel` with a switchable fake chat id (including "no chat"), and fakes
  `/api/geo/screen`, `/api/geo/corridor`, `/api/geo/map` and the TIGERweb
  outline with Playwright `page.route`, with controllable delay and failure.
  Exposes current `chatId`, `aoi_ref`, geometry and summary through
  `data-*` attributes for assertions. A smoke spec proves the fixture loads,
  draws an AOI and screens with a fake response. No product-code changes.
- **Acceptance:** `npm run test:aoi-state` (smoke passes); existing
  `test:map-toolbar` and `test:corridor-map` still pass;
  `make app-frontend-check`.

### 56.2.2 - Record the notice rule in ADR 0016

- **Files in scope:** `docs/decisions/0016-out-of-band-aoi-screening-handoff.md`.
- **Anchors:** sections on `regulatory_notice` and `chat_summary`; ADR 0003
  notice-first rule.
- **Spec:** Add D2 and D3 as dated decisions: the notice comes only from the MCP
  result; `NON_PRIME_LIMITATION` is appended, never substituted; a result with
  no MCP notice is returned with `regulatory_notice: null` and shown as invalid
  for both AOI and corridor; a failed screening's summary is attached to the
  chat for the ref it started with. Do not edit ADR 0003 unless its text
  contradicts this (then report, do not edit).
- **Acceptance:** orchestrator reads the diff against D2/D3; markdown only.

### 56.3.1 - D backend: notice from MCP only

- **Files in scope:** `agent_server/geo.py`, `tests/test_geo_map.py`,
  `tests/test_geo_screen.py`, `tests/test_geo_corridor.py`. No frontend files.
- **Anchors:** `geo.py` `_result_notice` (L176), `NON_PRIME_LIMITATION` (L31),
  `failed_chat_summary` (L268), `screen_aoi` (L336), `screen_corridor` (L473),
  other `_result_notice(` callers: `build_chat_summary` (L264),
  `select_display_corridor` (L469), `screen_corridor` (L503),
  `map_for_tool` (L573, the Show-on-map path);
  `test_geo_map.py` L151; `test_geo_screen.py` L454.
- **Spec:** Implement D2 in `_result_notice` for every caller (return type
  becomes `str | None`); update L151 to expect `None` for a missing notice; add
  tests that a present notice still gets the limitation appended, for screen,
  corridor and map paths. Keep `failed_chat_summary` and its renderer branch
  (D3 uses them).
- **Acceptance:** the three targeted pytest files pass; `make app-check`.

### 56.3.2 - D frontend: invalid-notice display; attach failed summary

- **Files in scope:** `frontend/client/src/components/map/MapPanel.tsx`
  (summary effect only), `useScreening.ts`, `useCorridorScreening.ts`,
  `ScreeningResults.tsx`, `CorridorScreeningResults.tsx`; new or extended Node
  test; `frontend/tests/aoi-state/aoi-state.spec.ts`; ADR 0015.
- **Anchors:** `MapPanel.tsx` "latest valid screening becomes the AOI's chat
  summary" (about L418-431); `useCorridorScreening.ts` L41;
  `CorridorScreeningResults.tsx` L48-51; `ScreeningResults.tsx` L58-72.
- **Spec:** Implement D3: when a screening for ref R ends with
  `display.error == 'screening_failed'`, attach its `chat_summary` to R (no-op
  if R is no longer attached). A valid result without a notice is still never
  attached. Corridor (per TRIAGE_56): a response with a null notice shows the
  invalid-notice message (today `useCorridorScreening.ts` L41 turns it into a
  generic error) and is never treated as valid; corridor screening has no
  `chat_summary`, so no corridor summary work. "Show on map" results with a
  null notice also show the invalid-notice message (ADR 0016 amendment
  2026-11-17). The message already exists at `MapPanel.tsx` L1124-1131
  (`shown.regulatory_notice`), so this part is a test only (fake
  `/api/geo/map` with a null notice). Test with faked responses only.
- **Acceptance:** Node test and `npm run test:aoi-state` cases for missing
  notice (AOI and corridor) and failed summary pass; `make app-frontend-check`.

### 56.4.1 - E: keep geometry context through stream retry

- **Files in scope:** `frontend/server/src/routes/chat.ts`,
  `frontend/server/src/lib/stream-fallback.ts` (only if needed),
  `frontend/packages/ai-sdk-providers/src/providers-server.ts` (only if a test
  hook is needed), create `frontend/server/src/routes/chat-geometry-release.test.ts`
  (or a lib-level test), edit `frontend/package.json` (test script); ADR 0015.
- **Anchors:** `chat.ts` `registerActiveAoi` / `res.on('close'` (L261-272),
  `drainStreamToWriter` / `fallbackToGenerateText` (about L351-360);
  `providers-server.ts` L26-42. Reference test: `server/src/middleware/auth.test.ts`.
- **Spec:** First write a failing test with a fake stream that fails after
  the response closes, asserting the retry still sees `active_aoi` and
  `active_corridor`. If it does not fail, record "not reproducible" with the
  test kept as a guard and stop. If it fails, release both keys only after the
  stream and any retry finish, on success and every error path, and assert
  every registered key is released.
- **Acceptance:** the new test passes (and was shown failing before the fix if
  the bug was real); `npm run test:local-auth` still passes;
  `make app-frontend-check`.

### 56.5.1 - A: Edit-mode changes update attached geometry

- **Files in scope:** `frontend/client/src/components/map/MapPanel.tsx`
  (Terra Draw setup), `mapControls.ts`/`mapControls.test.ts` or a new helper +
  test, `tests/aoi-state/aoi-state.spec.ts`,
  `tests/corridor-map/corridor-map.spec.ts`; ADR 0015.
- **Anchors:** `MapPanel.tsx` select-mode config (`midpoints: true`,
  `deletable: true`, about L263-271), `draw.on('finish'` (about L277),
  `replaceAoi` (about L180), `corridorDraw.on('finish'` / `on('change'`
  (about L312-345). Terra Draw 1.39.0 (`client/package.json`).
- **Spec:** Choose per the issue: either disable midpoints and vertex delete, or
  apply Terra Draw's saved-change event in Edit mode through `replaceAoi` (AOI)
  and the corridor attach path. Record the choice and why in the task notes.
  Dragging still works. Pure logic goes in a tested helper. Corridor (per
  TRIAGE_56): test-only. Its `change` handler already re-attaches on every
  change; add a test that a drag in Edit corridor keeps the attached corridor
  in sync. If Edit corridor cannot edit anything (select mode at L308 has no
  flags), record that under Discovered; do not fix it here.
- **Acceptance:** Node test for the helper; aoi-state and corridor-map
  Playwright cases: drag, vertex delete, midpoint insert each leave map shape
  equal to attached geometry; `make app-frontend-check`.

### 56.6.1 - B1: chat-scoped AOI/corridor context

- **Files in scope:** `ActiveAoiContext.tsx`, `ActiveCorridorContext.tsx`,
  `frontend/client/src/components/chat.tsx`, `MapPanel.tsx` (input gating),
  `pages/ChatPage.tsx`/`NewChatPage.tsx` only if needed, focused tests,
  `tests/aoi-state/aoi-state.spec.ts`; `map-toolbar-fixture.tsx` and
  `map-legend-fixture.tsx` (they mount `MapPanel` with no chat id and must set
  one, per 56.2.1 report); ADR 0015.
- **Anchors:** `setChatId` in both providers; `chat.tsx` L63-80
  (`setAoiChatId`, `activeAoiRef`, `setCorridorChatId`); `ChatPage.tsx`
  "Loading chat..." branch.
- **Spec:** Chat sets `chatId` to null when it unmounts; providers accept null;
  the map disables AOI and corridor input while `chatId` is null. Switching
  chats never writes another chat's storage; the new-chat flow keeps its
  geometry. Corridor (per TRIAGE_56): keep the existing draft-chat guard
  (`corridorDraftChatId`, about L684/L721); additionally disable corridor
  drawing, clear, remove and chip detach while `chatId` is null.
- **Acceptance:** Playwright: draw during "no chat" is blocked; switch A -> B ->
  A preserves each chat's AOI and corridor; new-chat keeps geometry;
  `test:map-toolbar` and `test:map-legend` still pass;
  `make app-frontend-check`.

### 56.7.1 - B2: drop late results; abort outline

- **Files in scope:** `ShowOnMapButton.tsx`, `IdentifyPopup.tsx`, `identify.ts`
  only if the signal plumbing needs it, `MapPanel.tsx` (`applyAreaAsAoi`,
  screening result effects), `useScreening.ts`, `useCorridorScreening.ts`,
  focused tests, `tests/aoi-state/aoi-state.spec.ts`; ADR 0015.
- **Anchors:** `ShowOnMapButton.tsx` `run` / `fetch('/api/geo/map'` (L107);
  `IdentifyPopup.tsx` L89 (`new AbortController().signal`);
  `MapPanel.tsx` `applyAreaAsAoi`, `screenedRef`.
- **Spec:** Record `chatId` and geometry ref when a request starts; read current
  values from a ref after `await`; drop the result if either changed. Abort the
  outline request when the popup closes or unmounts. Scope (per TRIAGE_56):
  Show on map, the Use-as-AOI outline, and corridor screening across a chat
  switch. AOI screening is already guarded (`useScreening.ts` requestId +
  `setSummary` ref check): add a regression test only, no code change.
- **Acceptance:** Playwright with delayed fakes: switch chat / replace AOI
  before the response -> nothing applied; popup close aborts the route;
  `make app-frontend-check`.

### 56.8.1 - C: Undo / Clear / Detach symmetry

- **Files in scope:** `ActiveAoiContext.tsx`, `ActiveCorridorContext.tsx`,
  `MapPanel.tsx` (`previousAoi`, `undo`, Clear, Undo button), `ActiveAoiChip.tsx`,
  focused tests, Playwright specs; ADR 0015; ADR 0016 if its wording changes.
- **Anchors:** `MapPanel.tsx` `previousAoi` (about L127), `const undo`
  (about L774), `replaceAoi(null)` (about L787), Undo `actionButton` (about
  L946); provider `setGeometry` / `detach`.
- **Spec:** Save the previous full context (ref, geometry, summary) and restore
  it as-is. Chip Detach goes through the Clear path and is undoable. Undo is
  disabled with nothing to restore. Corridor scope: the user decides before
  Wave 8 between (a) a corridor Undo that restores the previous full context
  with a stable `corridor_ref`, or (b) Detach via `clearCorridor` only
  (TRIAGE_56 C-corridor).
- **Acceptance:** Node test on the provider restore; Playwright: undo restores
  same `aoi_ref` and summary; detach -> undo restores; Undo disabled when
  empty; `make app-frontend-check`.

### 56.9.1 - Integrated validation and ADR sweep

- **Files in scope:** `planning/STATE_56.md`; ADR 0015/0016 wording only.
- **Spec:** Run every gate serially on the final tree; confirm ADR 0015 lists
  every touched/added frontend path; confirm each GOALS.md exit criterion with
  evidence. No push.
- **Acceptance:** STATE_56 board all done with commit ids and exact counts.

### 56.10.1 - Post-SDA manual and deployed checks (non-blocking)

- **Trigger:** SDA available again.
- **Spec:** User-run or user-approved: browser pass on chat switch, late
  results, undo/detach, missing-notice display, against the dev app; CI on the
  PR. Record evidence in `planning/evidence/56.10.1-manual.md`.
