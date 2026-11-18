# Project Goals (`planning/GOALS.md`)

Last Updated: 2026-11-17
Source State: STATE_55.md (all tasks done); issue #89 (map panel AOI state hardening, items A-E)
Scope: every goal below applies to both the area AOI and the corridor context (user decision, 2026-11-17). SDA is down: all verification uses fakes and fixtures, never live SDA.

## Circled Goal (Active)

- **[G57]** A triage record in `planning/` classifies each issue #89 item (A-E) and its corridor counterpart as still-applies, changed, or obsolete at main 129a091, with current file and line evidence.
  - Why now: Issue line references predate many map changes; triage decides which of G59-G65 survive and fixes their anchors.
  - Exit criteria: Triage table with one row per item x {AOI, corridor}, each row citing file:line evidence and a keep/drop/reshape verdict.
  - First action: Plan 56 Wave 1 triage task on branch `fix/map-aoi-hardening1`.

## Sequenced Goals (Dependency DAG)

- **[G58]** Browser fixtures and Node tests exercise AOI and corridor flows (chat switch, screening, Show on map, Use as AOI, chat-stream retry) with faked responses; no step needs SDA or MCP.
  - Depends on: G57
- **[G63]** An ADR (0003 or 0016) records whether the fallback limitation sentence may stand in for the ADR 0003 regulatory notice.
  - Depends on: G57
- **[G59]** Every Edit-mode change (drag, vertex delete, midpoint insert) to the AOI or a corridor feature updates the attached geometry, with tests for each. (Item A)
  - Depends on: G58
- **[G60]** AOI and corridor context `chatId` is null while no chat is mounted and map geometry input is disabled; switching chats never changes another chat's AOI or corridor; the new-chat flow keeps its geometry. (Item B)
  - Depends on: G58
- **[G61]** Late Show-on-map, Use-as-AOI, and screening results are dropped when `chatId` or the geometry ref changed since the request started; the outline request aborts when the popup closes. (Item B)
  - Depends on: G58
- **[G62]** Undo restores the previous full AOI or corridor context (same ref and summary); Detach goes through the Clear path and is undoable; Undo is disabled with nothing to restore. (Item C)
  - Depends on: G59, G60, G61
- **[G64]** AOI and corridor screening handle a missing regulatory notice per G63, tests cover the missing-notice case, and `failed_chat_summary` is attached or deleted. (Item D)
  - Depends on: G63
- **[G65]** A fake-stream test shows whether a chat-server retry after browser disconnect still sends `active_aoi` and `active_corridor`; if real, keys are released only after the stream and any retry finish, including error paths. (Item E)
  - Depends on: G58
- **[G66]** ADR 0015 `### Local changes` (and ADR 0016 / 0003 where wording changed) describes the shipped code.
  - Depends on: G59, G60, G61, G62, G64, G65

## Independent Backlog

- (none)

## Deferred

- (none)

## Blocked / Pruned

- **[G67]** Corridor edit/undo parity as a separate goal.
  - Status: Pruned
  - Reason: Merged into G59 and G62 after the user put the corridor in scope for every item.
- **[G68]** GOALS.md marks G50-G56 done.
  - Status: Pruned
  - Reason: Done by this rewrite (see Completed).

## Completed

- **[G50]-[G56]** Plan 55 goals (corridor attachment exclusivity, labels and remove/clear, toolbar and chip, geometry I/O, measurement preview, collapsed tool output). Evidence: `STATE_55.md`, all tasks done.
