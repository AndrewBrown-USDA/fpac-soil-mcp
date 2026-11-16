# EXECUTION_PLAN_55: Corridor, Map, Measurement & Chat Tool UX

Follows Plan 54 on `feature/local-dev-trial`.

Planning artifacts are tracked and committed separately from implementation.
The workspace is the clean root worktree on branch `feature/local-dev-trial`;
workers must use isolated worktrees for concurrent tasks in this repository.

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
| 1 | 55.1.1 | Enforce AOI/corridor chat attachment exclusivity | — | Context providers, chat request serialization, session tests |
| 1 | 55.2.1 | Collapse tool output by default and promote Show on Map | — | `message.tsx`, map action component, chat UI tests |
| 2 | 55.1.2 | Preserve corridor labels and synchronize remove/clear state | 55.1.1 | `corridorGeometry.ts`, `corridorGeometry.test.ts`, `corridorSession.ts`, `corridorSession.test.ts`, `MapPanel.tsx`, corridor-map tests, `geojson.ts` only if required |
| 3 | 55.2.2 | Concise measurement indicator and live rubber-band preview | 55.1.2 | `MapPanel.tsx`, `distance.ts`, distance tests, toolbar tests |
| 4 | 55.3.1 | Icon toolbar, unified attachment chip and geometry I/O panel | 55.1.1, 55.1.2, 55.2.2 | `MapPanel.tsx`, `GeoJsonInput.tsx`, `ActiveAoiChip.tsx`, corridor-map and toolbar specs |
| 5 | 55.4.1 | Integrated validation and handoff | 55.2.1, 55.3.1 | `STATE_55.md` |

## Task Specifications

All paths below are relative to `apps/agent-fpac-soil-openai-sdk/`. Follow its
nested `AGENTS.md`: every modified upstream frontend file and every added path
must be inventoried in `docs/decisions/0015-vendored-agent-app-frontend.md`.
Frontend test commands run from `frontend/`. Use `make app-frontend-check`
from the repository root for the non-writing lint/build gate. Do not run
upstream lint scripts that rewrite files.

### 55.1.1 — Enforce AOI/corridor chat attachment exclusivity

- **Files in scope:** `frontend/client/src/components/map/ActiveAoiContext.tsx`, `ActiveCorridorContext.tsx`, `frontend/client/src/components/chat.tsx`, `frontend/client/src/components/map/corridorSession.ts`, `corridorSession.test.ts`; focused adjacent tests may be created.
- **Anchors:** provider `setGeometry`/`save`/`setChatId`; corridor `setCorridor`/`saveCorridor`/`setChatId`; chat `activeAoiRef`, `activeCorridorRef`, `prepareSendMessagesRequest`.
- **Spec:** On draw/edit, attach the newest geometry context and detach the other. Requests serialize no more than one of `activeAoi` or `activeCorridor`; preserve per-chat persistence and existing payload compatibility.
- **Acceptance:** focused Vitest for `corridorSession.test.ts` and added tests; `make app-frontend-check`.

### 55.2.1 — Collapse tool output and promote Show on Map

- **Files in scope:** `frontend/client/src/components/message.tsx`, `frontend/client/src/components/elements/tool.tsx`, `frontend/client/src/components/map/ShowOnMapButton.tsx`, the focused fixture/spec files, and `docs/decisions/0015-vendored-agent-app-frontend.md`.
- **Anchors:** `ToolPartRenderer`, MCP `McpTool defaultOpen`, `McpToolContent`, `showOnMap` rendering.
- **Spec:** MCP tool output/details are collapsed by default without changing approval/action behavior. Put Show on Map in the tool-call top bar with tool-call and AOI information where available.
- **Acceptance:** targeted Vitest/Playwright coverage for collapsed output and top-bar map action; `make app-frontend-check`.

### 55.1.2 — Corridor labels and remove/clear synchronization

- **Files in scope:** `frontend/client/src/components/map/corridorGeometry.ts`, `corridorGeometry.test.ts`, `corridorSession.ts`, `corridorSession.test.ts`, `MapPanel.tsx`, existing corridor-map Playwright spec, and `docs/decisions/0015-vendored-agent-app-frontend.md`. `geojson.ts` only if a shared helper is required.
- **Anchors:** `createCorridorInput`, alternative label mapping, `combineStagingAreas`, `corridorDrawKind`, TerraDraw `onFinish`/`onChange`, `clearCorridor`, `removeCorridorFeature`.
- **Spec:** Preserve a unified label/role for primary, alternatives, and staging through model serialization. Removing or clearing synchronizes TerraDraw, draft React state, and attached corridor state; labels do not alter MCP geometry schema.
- **Acceptance:** focused Vitest for corridor geometry/session; `npm run test:corridor-map`; `make app-frontend-check`.

### 55.2.2 — Measurement preview

- **Files in scope:** `frontend/client/src/components/map/MapPanel.tsx`, `distance.ts`, `distance.test.ts`, `frontend/tests/map-toolbar/toolbar.spec.ts`, and `docs/decisions/0015-vendored-agent-app-frontend.md`.
- **Anchors:** measurement GeoJSON source/layer, map click and mouse-move handlers, `measurePoints`, `lineCollection`, `lineDistance`, line-measurement toolbar group.
- **Spec:** Show a concise active-measurement indicator. After the first click, render a live rubber-band line to the pointer without adding a committed measurement point; preserve distance and finish/cancel behavior.
- **Acceptance:** focused distance tests; `npm run test:map-toolbar`; `make app-frontend-check`.

### 55.3.1 — Toolbar, attachment chip, and unified geometry I/O

- **Files in scope:** `frontend/client/src/components/map/MapPanel.tsx`, `GeoJsonInput.tsx`, `ActiveAoiChip.tsx`, `frontend/tests/corridor-map/corridor-map.spec.ts`, `frontend/tests/map-toolbar/toolbar.spec.ts`, and `docs/decisions/0015-vendored-agent-app-frontend.md`.
- **Anchors:** map toolbar controls, attachment status/chip, geometry input and export controls.
- **Spec:** Keep Area and Corridor controls visible as compact icon-only buttons with accessible labels. Expose one attach/detach chip for the mutually exclusive active geometry. Unify upload, paste, copy, and download in one panel; retain existing validation and workflows.
- **Acceptance:** `npm run test:corridor-map`; `npm run test:map-toolbar`; `make app-frontend-check`.

### 55.4.1 — Integrated validation and handoff

- **Files in scope:** `planning/STATE_55.md` only.
- **Spec:** Orchestrator verifies the integrated diff, runs named targeted suites and `make app-frontend-check`, records commits, results, deviations, and follow-up. No deployment or remote actions.
- **Acceptance:** all task board entries reflect verified status and exact validation results.
