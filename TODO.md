# TODO

## Goal
Apply the low-hanging-fruit visual refresh from `planning/RESEARCH_AGENT_MAP_APP_VISUAL_DESIGN.md` ("field atlas" look, research items 1-5) to the agent app frontend, presentation only, on `ui/agent-map-app-pretty1`.

## Tasks

### 1. Baseline
- [x] In a throwaway `/tmp` copy of committed HEAD 5d53ce7, run the frontend gate (`npm ci`, `npx biome lint --skip=nursery/useSortedClasses --skip=style/useTemplate .`, `npm run build`) and record error/warning counts as the baseline. Result: 607 files, 0 errors, 10 warnings, build OK.

### 2. Tokens, app-wide (`client/src/index.css`)
- [x] Light `:root`: warm paper surfaces (`--background`, `--card`, `--popover`, `--secondary`, `--muted`, `--accent`, sidebar), warm borders/inputs, deep ink `--foreground`, forest-green `--primary`/`--ring`/`--sidebar-primary`; add `--atlas-soil` (accent for header rule only) and `--atlas-leaf`.
- [x] `.dark`: matching warm-dark variants of the same tokens; no new tokens missing from `.dark`.
- [x] Leave data colours untouched: `farmlandClasses.ts`, server map styles, `--chart-*`, `--destructive`.
- [x] Verify with a script: WCAG contrast >= 4.5:1 for foreground/background, muted-foreground/background, primary-foreground/primary, and foreground/secondary, in light and dark. Result: 24 pairs (incl. card, sidebar, destructive, soil, tooltip), 0 below 4.5:1; lowest 5.01 (dark destructive). White on primary is 6.34 light (was 5.08 on the old blue), 5.19 dark.

### 3. Panel header and map toggle
- [x] `MapPanel.tsx`: compact header ("FPAC Soil" title, "Map workspace" subtitle, thin soil-coloured rule) above the existing preliminary notice; AOI status pill showing the active `aoi_ref` or "No AOI" (values already in `activeAoi`).
- [x] `ChatLayout.tsx`: toggle gets a lucide `Map` icon plus the existing text labels, same `aria-expanded`/`aria-controls`, same open/closed widths and narrow-screen default.

### 4. Toolbar hierarchy
- [x] Split the single toolbar into labelled groups "Draw area" (Polygon, Rectangle) and "Edit area" (Edit, Undo, Clear), each `role="group"` with `aria-label`, lucide icons beside the existing text labels; keep `aria-pressed`, `disabled` rules and handlers unchanged.
- [x] Selected tool state not colour-only: pressed button also shows a check icon or ring.
- [x] `GeoJsonInput`: give its block an "Import GeoJSON" group heading in the same style; no behaviour change.

### 5. Status message bars
- [x] Add `components/map/StatusMessage.tsx` (variants info/success/warning/error using the existing `--background-*`/`--border-*` tokens, icon + wrapping text, no truncation; error variant keeps `role="alert"`).
- [x] Use it for the preliminary notice (warning, same text), the screening status line (info while idle/running, success when done, still `aria-live="polite"`), and the AOI/screening/tile error block (same messages).
- [x] `ShowOnMapButton.tsx`: add a lucide `MapPin` icon to the button and render its error through `StatusMessage`; same text and states.

### 6. Results layout
- [x] `ScreeningResults.tsx`: summary strip above the notice from existing `analysis` values only (AOI acres, FPPA-protected acres and %, coverage status), labelled "Preliminary machine estimate"; hide fields that are null, never compute new numbers.
- [x] Regulatory notice stays first in content order after the strip, verbatim, with a heading; legend and table get section spacing and small headings; `ResultsTable` content unchanged except caption/heading typography.
- [x] Apply the same notice/legend treatment to the tool-result view in `MapPanel.tsx` ("Map of ... result" header gets a "Tool result" badge vs "AOI screening").

### 7. Docs and gate
- [x] ADR 0015 `### Local changes`: list `index.css`, `ChatLayout.tsx` (if not already listed) and the new `StatusMessage.tsx`.
- [x] Frontend gate in a fresh `/tmp` clone of the committed head: 0 lint errors, warnings <= baseline, build OK; `make app-check` still passes. Result at 764c721: npm ci OK, 608 files 0 errors / 10 warnings (same as baseline, none in changed files), build OK, app-check 177 passed.
- [x] Read-back check of the diff: preliminary notice text, regulatory notice rendering, Legend source/vintage/authority, `farmlandClasses.ts`, `mapLayers.ts`, `overlays.ts` unchanged; no new npm dependencies. Result: farmlandClasses, mapLayers, overlays, Legend, ResultsTable, client/package.json and package-lock.json identical to 5d53ce7; notice, missing-notice, tile-error and status strings present; aria-pressed/expanded/controls/live kept.
- [x] Commit per section with conventional commits (`feat(app-ui): ...`, `docs(adr): ...`); do not push. Commits: 7f67144, f1e7b78, 9ef00aa, 48ae432 (tasks 4-6 together), 764c721, plus this TODO update. Not pushed.

## Notes
- Branch: `ui/agent-map-app-pretty1`, worked in the separate Git folder `~/fpac-soil-mcp-ui`; the main clone (`~/fpac-soil-mcp`, another agent on `fix/eval-tuning1`) is not touched.
- Out of scope: map fill/outline colours and server symbology (ADR 0017), accessibility audit, browser screenshots. The user does the browser check after push.
- Icons come from `lucide-react` (already a dependency, 0.446.0). No new packages, no lockfile change.
- Risk: app-wide primary colour change from blue to green affects every chat button and link; contrast is checked in task 2, appearance needs the user's browser check.
- Commits stay local until the user approves the push (a push may redeploy the dev apps).
- Task 6: the summary strip sits above the regulatory notice as planned (user decision 2026-11-12, after I raised the ADR 0003 "notice first" comment); the strip carries the "Preliminary machine estimate" badge and the notice still precedes the legend and table. `ResultsTable.tsx` and `Legend.tsx` are unchanged; they are wrapped in cards instead.
- Small addition (task 5): "Run screening" uses the primary (filled) button variant, so the main action stands out from the outlined tool buttons.
- 2026-11-12: Auto Mode blocked the commit for task 4 onward (it read the `~/fpac-soil-mcp-ui` path as the main clone); the user confirmed commits in this clone. Tasks 4-6 share `MapPanel.tsx` edits, so they landed as one frontend commit instead of one per section.
