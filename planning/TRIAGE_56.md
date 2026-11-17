# TRIAGE_56: issue #89 against main 129a091

Paths are under `apps/agent-fpac-soil-openai-sdk/frontend/client/src/components/map/`
unless shown otherwise. Line numbers are at 129a091 (identical code at f0af2fc).
Verdicts: **still-applies**, **changed** (applies in a different form),
**obsolete**, **unverified** (needs the task's failing test first).

## Summary

| Item | AOI | Corridor |
|---|---|---|
| A Edit changes sync | still-applies | unverified (likely obsolete for sync; Edit may be inert) |
| B1 chat-scoped context | still-applies | changed (partial guard) |
| B2 late results | still-applies | changed (screening guarded; chat switch not) |
| C Undo/Clear/Detach | still-applies | changed (no Undo exists; ref churn) |
| D notice / failed summary | still-applies | changed (null notice shows an error; no summary) |
| E retry keeps context | still-applies (suspected) | still-applies (suspected) |

## Rows

### A-AOI - still-applies
- Evidence: `MapPanel.tsx` L259-272 select mode `polygon.feature.coordinates: { midpoints: true, draggable: true, deletable: true }`; L277 `draw.on('finish', ...)` is the only AOI draw handler (no `draw.on('change'`).
- Anchors: L259-272, L277-300, `replaceAoi` L180.
- Offline repro: aoi-state fixture; draw polygon, Edit, right-click a vertex; compare map snapshot with attached geometry.

### A-corridor - unverified
- Evidence: L308 `new TerraDrawSelectMode({})` (no flags); L328-345 `corridorDraw.on('change')` rebuilds centerline/alternatives/staging on every change, and the attach effect L683-696 re-attaches when the signature changes. Any edit that does happen therefore syncs.
- Open: with no flags, "Edit corridor" (L972) may not let the user select or edit anything.
- Plan impact: 56.5.1 adds a corridor test that drags a vertex in Edit corridor; if nothing can be edited, record it as Discovered (not a sync bug) and keep corridor A test-only.

### B1-AOI - still-applies
- Evidence: `ActiveAoiContext.tsx` `setChatId: (chatId: string) => void` (no null); `chat.tsx` L66-69 sets the id in an effect with no cleanup; `MapPanel.tsx` has no `chatId` gating for AOI input (only corridor at L684). `ChatPage.tsx` renders "Loading chat..." without `Chat`, so the previous id stays set.
- Anchors: `ActiveAoiContext.tsx` `setChatId`, `setGeometry`; `chat.tsx` L63-80; `ChatPage.tsx` loading branch; `NewChatPage.tsx` L9/L17 `generateUUID()`.

### B1-corridor - changed
- Evidence: `ActiveCorridorContext.tsx` L36 `setChatId(chatId: string)` (no null); `chat.tsx` L74-77 same pattern. `MapPanel.tsx` L684 only attaches when `corridorDraftChatId.current === chatId` (set at L721 when drawing starts), so a draft started in chat A is not attached in chat B. Not guarded: clear/remove/detach during "Loading chat..." act on the previous chat's storage.

### B2-AOI - still-applies
- Evidence: `ShowOnMapButton.tsx` `run` awaits `fetch('/api/geo/map'` (L107) then calls `mapResult.show` (L129) with no chat/ref re-check; `MapPanel.tsx` L470-475 clears the shown result on chat/AOI change, but a response landing after that re-shows it. `IdentifyPopup.tsx` L89 passes `new AbortController().signal` (cannot abort), then `onUseGeometry` (L109) -> `applyAreaAsAoi` (L755-770) applies it to whatever chat is current.
- Already safe: AOI screening. `useScreening.ts` `requestId` guard (L54-111) drops superseded runs, and `setSummary` ignores a non-matching `aoi_ref`.

### B2-corridor - changed
- Evidence: `useCorridorScreening.ts` L54-68 `requestId` guard drops superseded runs. Not guarded: a corridor screening that resolves after a chat switch is still shown (no chat id captured).

### C-AOI - still-applies
- Evidence: `MapPanel.tsx` L127 `previousAoi: PolygonGeometry | null`; `undo` L774-783 calls `setGeometry(restored)` -> `ActiveAoiContext.tsx` `setGeometry` mints `newAoiRef()` with `summary: null`. Chip Detach: `ActiveAoiChip.tsx` L36 `context.detach` -> `setGeometry(null)`, bypassing `replaceAoi`, so nothing is saved to undo. Undo button L946 is enabled when `aoi` exists with no `previousAoi`; `undo` then restores `null` (an irreversible clear).

### C-corridor - changed
- Evidence: no corridor Undo state or control (no `previousCorridor`/corridor undo in `MapPanel.tsx`). Chip Detach -> `ActiveCorridorContext.tsx` L68 `setCorridor(null)`; drawn features stay on the map. Every corridor change re-attaches with a new `corridor_ref: corridorReference()` (L691-695), so tool cards tied to the previous ref become stale after any edit.
- Decision needed before Wave 8: add a corridor Undo (restore previous full context, same `corridor_ref`), or limit corridor C to "Detach goes through clearCorridor" only.

### D-AOI - still-applies
- Evidence: `agent_server/geo.py` L176-181 `_result_notice` returns `NON_PRIME_LIMITATION` when the MCP notice is missing; callers L264 (`build_chat_summary`), L503 (`screen_corridor`), L469 (`select_display_corridor`), L573 (`map_for_tool`). `tests/test_geo_map.py` L151 asserts the fallback. `ScreeningResults.tsx` L65-72 invalid message is unreachable. `failed_chat_summary` (L268) is returned by `screen_aoi` (L358-363) but `MapPanel.tsx` L420-431 attaches summaries only when there is no `display.error`.

### D-corridor - changed
- Evidence: `useCorridorScreening.ts` L41 rejects a response with no notice as "Corridor screening returned an incomplete result." (an error), so `CorridorScreeningResults.tsx` L51's invalid message is unreachable either way. `screen_corridor` (L473) builds no `chat_summary` (no `chat_summary` after L380 in `geo.py`), so D3 does not apply to the corridor.
- Plan impact: 56.3.2 corridor = show the invalid-notice message (or an equivalent explicit invalid state) instead of the generic error; no summary work.

### E-AOI and E-corridor - still-applies (suspected)
- Evidence: `frontend/server/src/routes/chat.ts` L261-272 registers both keys and releases them on `res.on('close')`; `drainStreamToWriter` then `fallbackToGenerateText` (L351-360) runs later in the same handler. Registry: `packages/ai-sdk-providers/src/providers-server.ts` L26-42. No server test covers this (`server/src` tests: `middleware/auth.test.ts` only).
- Plan impact: none; 56.4.1 starts with the failing test as specified.

## Hazards check

- Confirmed: `MapPanel.tsx` 1165 lines, `chat.ts` 640; issue line numbers stale.
- Confirmed: corridor null notice -> error at `useCorridorScreening.ts` L41.
- Confirmed: `screen_corridor` has no `chat_summary`.
- Confirmed: no corridor Undo state.
- New: Playwright needs 4 shared libraries missing on serverless (`libatk-1.0`, `libatk-bridge-2.0`, `libatspi`, `libXdamage`). Workaround used for the baseline: user-level `apt-get download` into `/tmp/pwlibs` plus `LD_LIBRARY_PATH`, browsers in `/tmp/pw-browsers`. Rebuild after any serverless restart.

## Discovered (not in scope; wait for the user)

1. Corridor "Edit corridor" select mode has no flags (L308); editing may be inert.
2. Corridor edits mint a new `corridor_ref` on every change (L691-695), unlike the AOI (which keeps its ref until replaced). Folded into the C-corridor decision.
3. `corridor-map` Playwright flaked once on a cold dev server (1 failed / 2 passed), then 3/3 twice.

## Spec changes for Waves 3-8

- 56.3.2: corridor part is "null notice -> explicit invalid-notice message"; drop corridor summary work.
- 56.5.1: corridor part becomes a test (drag in Edit corridor keeps attached corridor in sync); if editing is inert, test-only plus Discovered item.
- 56.6.1: corridor part = null `chatId` gating for clear/remove/detach and input; keep the existing draft-chat guard.
- 56.7.1: AOI screening needs no change (already guarded); scope = ShowOnMap, Use-as-AOI outline, corridor screening chat switch.
- 56.8.1: corridor part waits for the user's decision (add Undo with stable `corridor_ref`, or Detach-via-clear only).
- 56.4.1, 56.3.1: unchanged.
