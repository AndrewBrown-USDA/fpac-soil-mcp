# TODO

## Goal
Fix five agent map app UI issues from user feedback on branch `ui/agent-map-feedback1` (from `origin/main` 526c21c), without changing server values, legends or notice text.

Paths below are relative to `apps/agent-fpac-soil-openai-sdk/frontend/client/src/` unless noted.

## Tasks

### 1. Plan
- [x] Commit this TODO.md (`docs(planning): plan agent map UI feedback fixes`).

### 2. Export chat no longer overlaps the Ephemeral badge
- [x] `components/chat-header.tsx`: add an optional `actions` slot rendered inside the right-side `ml-auto` row, after the Ephemeral / Feedback disabled badges.
- [x] `components/chat.tsx`: pass `<ChatExportActions>` through that slot; remove the `absolute right-4 top-3` wrapper.
- [x] Check: `tests/chat-export/export.spec.ts` selectors (`Export chat`) still match; no layout overlap by reading the classes (both items are flex siblings in one row).

### 3. Map legend shows farmland classes once
- [x] `components/map/MapPanel.tsx`: render `CoreFarmlandLegend` only when the shown map block has no `farmland_classes` layer (before screening, or for results without that layer). Server legend values stay as returned.
- [x] `tests/map-legend/legend.spec.ts`: add an assertion that "Prime farmland" appears exactly once in the legend after a result with a farmland layer is shown; keep the existing before-screening checks.

### 4. Regulatory notice moves to the bottom; farmland figures are not labelled a machine estimate
- [x] Add a shared `RegulatoryNotice` component in `components/map/ScreeningResults.tsx`: a collapsed `<details>` with summary "Regulatory notice", text shown verbatim and unchanged, `text-xs`; the "Regulatory notice missing - treat this result as invalid." alert stays visible and unchanged.
- [x] `ScreeningResults.tsx`: order = summary strip, results table, regulatory notice (last). Remove the "Preliminary machine estimate" badge from the AOI summary strip; update the ordering comment.
- [x] `components/map/CorridorScreeningResults.tsx`: use `RegulatoryNotice` at the bottom (already last); keep the "Preliminary screening estimate" badge (corridor results include the composite relative rating).
- [x] `components/map/MapPanel.tsx` tool-result view (~L1141): move the notice below the server legend and use `RegulatoryNotice`.
- [x] Keep the map banner "Preliminary screening view. Not an official NRCS determination." and the status texts unchanged.
- [x] Update any Playwright spec or fixture that relies on the old order or the badge text (grep `Regulatory notice`, `Preliminary machine estimate`).
- [x] `docs/decisions/0017-server-map-result-contract.md`: add a dated amendment: the AOI farmland summary no longer carries a machine-estimate badge (class acres come straight from the SDA database); the server layer authority label in the legend and the `regulatory_notice` still render on every result; the notice sits at the bottom, collapsed.

### 5. Area and Corridor tools: show only the active set
- [x] `components/map/MapPanel.tsx`: render the "Corridor tools" group only when `mapMode === 'corridor'`, in the same slot as the "Area of interest" group (right after Mode), followed by Map view and Line measurement for both modes.
- [x] Toolbar row: `flex-wrap` stays for narrow screens; button groups use `flex-nowrap` so each set stays on one line when there is room.
- [x] Remove the now-redundant `mapMode !== 'corridor'` disable conditions on corridor buttons.
- [x] `tests/map-toolbar/toolbar.spec.ts` (~L255-270) and `tests/corridor-map/corridor-map.spec.ts`: change "primary line visible but disabled in Area mode" to "not present in Area mode"; assert Polygon is absent in Corridor mode.

### 6. Hide the label inputs
- [x] `components/map/MapPanel.tsx`: remove the Area label / Alternative label input from the toolbar. Keep the state: GeoJSON copy/download keep the default name, alternatives keep the "Alternative N" default.
- [x] Update specs that fill `Alternative label` (`corridor-map.spec.ts` L60, `toolbar.spec.ts` L287-291): drop the fill and expect the default label.

### 7. Records and gate
- [x] `docs/decisions/0015-vendored-agent-app-frontend.md`: list every changed file under `### Local changes`.
- [x] Gate (clean `/tmp` clone of the branch, Node 22): `make app-frontend-check` (biome lint read-only + build) with no new errors vs the baseline, and `make app-check` passes.
- [x] Run the touched Playwright suites (`test:chat-export`, `test:map-legend`, `test:map-toolbar`, `test:corridor-map`) if a browser is available on serverless; otherwise record that they were not run and list them for a local run.
- [x] Read back the full diff against `origin/main`: only the files listed above changed; notice text, server legend values and lockfiles unchanged.
- [x] One commit per section 2-7 (Conventional Commits, scope `agent-app`); ask before pushing.

## Notes
- Decisions (the user, 2026-11-20, accepted my proposed defaults): new branch from origin/main; notice collapsed at the bottom, text unchanged; drop only the AOI badge; hide both label inputs; Export chat goes in the header row as a text button.
- ADR 0003 only requires the notice on every result; the notice-first order came from ADR 0017 / the earlier visual work, so ADR 0017 is the one amended.
- Out of scope, needs your approval: the server still tags the `farmland_classes` map layer as `authority="machine_estimate"` (`src/fpac_soil_mcp/domain/polygon_analyzer.py` L599), so the legend still says "Preliminary Machine Estimate. Source: ..." for farmland classes. Changing that is an MCP server change (`reference_data`?) and would touch server tests and ADR 0017.
- Wiring alternative labels to the tool call later needs `createCorridorInput`, the `geo.py` corridor request model and `screen_corridor` (`alternative_id`), plus tests.
