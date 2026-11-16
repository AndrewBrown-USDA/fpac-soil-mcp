# Project Goals (`planning/GOALS.md`)

Last Updated: 2026-11-15
Source State: STATE_55.md

## Circled Goal (Active)

- **[G52]** Feature and label model unifies primary, alternatives, and staging areas (as AOIs) with a single label concept and extensible AOI buffer support, and remove/clear reliably deletes Terra Draw features and resets state.
  - Why now: Unblocks both reliable remove/clear (`G51`) and the unified icon-only toolbar (`G53`).
  - Exit criteria: `corridorGeometry.test.ts` passes with unified primary/alternative/staging/label model and reliable clear/remove.
  - First action: Execute Plan 55 Wave 1 (`55.1.1` and `55.1.2`).

## Sequenced Goals (Dependency DAG)

- **[G50]** Corridor context (`custom_inputs.active_corridor`) reliably attaches to chat and is mutually exclusive with Area AOI.
- **[G51]** Corridor remove/clear reliably deletes Terra Draw features and resets state.
  - Depends on: G52
- **[G53]** Area and Corridor controls are compact icon-only toolbar buttons with auto-attach and a single attach/detach toggle chip.
  - Depends on: G50, G52
- **[G54]** Upload, paste, copy, and download are unified into a single geometry I/O panel.
  - Depends on: G50, G52

## Independent Backlog (Included in Plan 55)

- **[G55]** Measurement mode shows a concise active indicator and draws a live rubber-band preview line after the first click.
- **[G56]** Chat tool outputs are collapsed by default, and "Show on map" is on the tool-call top bar with AOI info.
