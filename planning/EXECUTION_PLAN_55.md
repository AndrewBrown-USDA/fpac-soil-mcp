# EXECUTION_PLAN_55: Corridor, Map, Measurement & Chat Tool UX

Follows Plan 54 on `feature/local-dev-trial`.

## Decisions
- Keep both Area and Corridor controls visible, compacted into icon-only toolbar buttons with accessible hover/focus labels.
- Area AOI and Corridor are mutually exclusive for chat attachment: only one active geometry context (Area OR Corridor) is attached to chat at a time.
- Auto-attach on draw/edit, with a single "Attached to chat" toggle/chip to detach (no separate Attach and Detach buttons).
- Unify staging area with regular AOI drawing; support multiple AOIs/corridors (primary + alternatives + staging) with a single unified label concept. Keep AOI buffer extensible in the model.
- Unify upload / paste / copy / download into one panel.
- Measurement: concise active indicator + live rubber-band preview line after the first click.
- Chat tool calls: collapse tool output by default; place "Show on map" on the top bar with tool call & AOI info.

## Wave Table

| Wave | Task | Title | Depends On | Files in Scope |
|---|---|---|---|---|
| 1 | 55.1.1 | Fix corridor chat attachment & AOI mutual exclusivity | — | `ActiveCorridorContext.tsx`, `ActiveAoiContext.tsx`, `corridorSession.ts`, `corridorSession.test.ts`, chat transport/input |
| 1 | 55.1.2 | Fix remove/clear & unify feature/label model (primary, alt, staging) | — | `corridorGeometry.ts`, `corridorGeometry.test.ts`, `geojson.ts` |
| 2 | 55.2.1 | Collapse tool output by default & move Show on Map to top bar | — | `ShowOnMapButton.tsx`, chat tool-call component(s) |
| 2 | 55.2.2 | Concise measurement indicator & live rubber-band preview line | — | `MapPanel.tsx` (measure section), `distance.ts` |
| 3 | 55.3.1 | Icon-only toolbar, single attach/detach chip & unified I/O panel | 55.1.1, 55.1.2, 55.2.2 | `MapPanel.tsx`, `GeoJsonInput.tsx`, `ActiveAoiChip.tsx`, `corridor-map.spec.ts`, `toolbar.spec.ts` |
| 4 | 55.4.1 | Integrated validation and handoff | 55.2.1, 55.3.1 | `STATE_55.md` |
