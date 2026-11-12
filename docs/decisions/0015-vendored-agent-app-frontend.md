---
id: "0015"
title: "Vendor the Full Pinned Chat Template for the Agent App Frontend"
status: "Accepted"
date: 2026-10-28
authors:
  - "Andrew G. Brown"
supersedes: null
superseded_by: null
source_context: "EXECUTION_PLAN_40, EXECUTION_PLAN_41, EXECUTION_PLAN_42"
---

# 15. Vendor the Full Pinned Chat Template for the Agent App Frontend

> **Accepted 2026-10-31 (Plan 42).** The owned frontend with its listed local
> changes passed the parity check and the deployed trial; see
> [`planning/evidence/42.6.1-trial.md`](../../planning/evidence/42.6.1-trial.md).

## Context and Problem Statement

The agent app (`apps/agent-fpac-soil-openai-sdk`) serves the Databricks chat UI
from `databricks/app-templates`, folder `e2e-chatbot-app-next`. The original
launcher cloned that template from GitHub at startup, so every deploy could pick
up unreviewed upstream changes. Plan 40 vendored only `client/` with local type
shims and a client-only lockfile. Review found that layout cannot match
upstream: the client imports the `server/` and `packages/*` workspaces, the
upstream server serves `../../client/dist` relative to `server/dist`, and the
only valid lockfile is the upstream root `package-lock.json`.

## Decision Drivers

* Deploys must be reproducible and reviewable; nothing is fetched from GitHub at
  startup.
* The copy must start from a named upstream commit, and every difference from
  it must be listed, so updates are a re-copy, a re-apply of the listed local
  changes, and a diff.
* Python checks must keep running where npm is unavailable (Databricks
  serverless compute).
* Frontend checks must be read-only; they must not rewrite vendored files.
* The repo must be able to build product features (the map panel) into the
  frontend without forking a separate app.

## Considered Options

1. **Vendor the whole `e2e-chatbot-app-next` folder at one upstream base commit,
   with its own root lockfile, and own it from there with listed local
   changes.**
2. **Vendor `client/` only, with shims for the workspace packages** (the Plan 40
   layout) -- diverges from upstream and needs a hand-built lockfile.
3. **Keep cloning upstream at startup** -- unpinned and not reviewable.

## Decision Outcome

Chosen option: "Vendor the whole folder at one commit", because it is the only
layout that builds with a single workspace lockfile and stays hash-comparable
to upstream for every file this repo has not changed.

* **Base commit:** upstream `0e572976459aafa3d41047067382cb9a6c015d52`.
  `frontend/` is the upstream folder at that commit, including file modes,
  minus the excluded files below, and this repo now owns it. Files not in the
  local-changes list stay identical to the base.
* **Kept:** root `package.json` (npm workspaces `client`, `server`,
  `packages/*`), root `package-lock.json`, `client/`, `server/`,
  `packages/`, `scripts/`, `biome.jsonc`, `tsconfig.json`, `drizzle.config.ts`,
  `knip.json`, `.gitignore`, `.env.example`, `README.md`. `client/`, `server/`
  and `packages/` stay siblings.
* **Excluded:** `.claude/`, `CLAUDE.md`, `tests/`, `playwright.config.ts`,
  `app.yaml`, `databricks.yml`, `manifest.yaml`.
* **Lockfile:** npm regenerates the root `package-lock.json` when dependencies
  change; it is committed together with the matching `package.json`. CI and
  `make app-frontend-check` run `npm ci` against it.
* **Local changes:** allowed. Every modified upstream file and every added path
  is listed in `### Local changes` below, kept current by the task that makes
  the change. No shims for the workspace packages.
* **Launcher (`scripts/start_app.py`):** runs `npm ci`, `npm run build`,
  `npm run start` in `frontend/`, sets `API_PROXY`, and keeps the ports and
  readiness pattern. With `--no-ui`, or when `frontend/package.json` is missing,
  it runs the backend only.
* **Checks:** `make app-check` stays Python-only (`app-lint app-test`).
  `make app-frontend-check` runs `npm ci`, then
  `npx biome lint --skip=nursery/useSortedClasses --skip=style/useTemplate .`,
  then `npm run build`. The two skipped rules are the only error-level findings
  in unmodified upstream (39 and 1); upstream's own `lint` script autofixes them
  with `--write --unsafe`, which must never run here. There is no typecheck:
  upstream has no typecheck script, and `tsc --noEmit` fails at 0e57297 for
  `client` (TS7016, TS2305), `server` (TS2305, TS2322) and the composite
  `packages/*` projects. The Vite and tsdown builds do not typecheck.
* **Runtime:** Node 22 (the Databricks Apps runtime is 22.16; CI uses 22).

### Local changes

Modified upstream files:

* `packages/db/migrations/0001_add_trace_id.sql` and
  `packages/db/migrations/meta/_journal.json`: add the MLflow trace ID column
  with replay-safe SQL and an execution-order timestamp.
* `client/index.html`: permit browser page zoom and set the browser title to
  “Farmland Protection Policy Act Agent”.
* `client/src/components/sidebar-toggle.tsx`: give the icon-only sidebar
  toggle an accessible name.
* `client/package.json`: exact pins for the map panel dependencies
  `maplibre-gl`, `terra-draw` and `terra-draw-maplibre-gl-adapter` (first
  pinned at 5.24.0, 1.39.0 and 1.5.0; Dependabot keeps them current).
  MapLibre 6 loads its worker from a file next to its own module, which the
  Vite build does not emit, so `components/map/maplibreWorker.ts` bundles the
  worker with `?worker&url` and passes it to `setWorkerUrl`.
* `package-lock.json`: regenerated by npm for those dependencies.
* `client/src/layouts/ChatLayout.tsx`: collapsible map panel column next to
  the chat, wrapped in the active-AOI provider (ADR 0016) and the map-result
  provider, which opens the panel when a tool card's "Show on map" is used
  (Plan 44, ADR 0017). The map toggle has an icon and a focus ring; when open,
  it appears inline with the map-panel header.
* `client/src/index.css`: "field atlas" app theme (warm surfaces, ink text,
  forest-green primary, `--atlas-*` tokens with `atlas-soil`/`atlas-leaf`
  colour utilities) in light and dark mode. Map data colours, chart and
  status tokens are unchanged
  (`planning/RESEARCH_AGENT_MAP_APP_VISUAL_DESIGN.md`).
* `client/src/components/message.tsx`: "Show on map" button on completed
  `analyze_farmland_by_polygon`, `analyze_corridor_fppa` and
  `get_soil_polygons_by_geometry` tool cards (Plan 44, ADR 0017).
* `client/src/components/multimodal-input.tsx`: shows the attached map AOI
  chip above the textarea (ADR 0016).
* `client/src/components/suggested-actions.tsx`: FPPA starter prompts
  (labelled, two columns on wider screens) in place of the two generic
  upstream suggestions. Each reuses an `eval/prompt_test_cases.json`
  `user_prompt` named by `caseId`, plus one map-AOI prompt.
* `client/src/components/chat.tsx`: tells the map panel the open chat id and
  sends the chat's AOI as `activeAoi` with each turn (ADR 0016).
* `packages/core/src/schemas/chat.ts`: optional, bounded `activeAoi` in the
  chat request; invalid values are dropped (ADR 0016).
* `packages/core/src/ai/providers.ts`: re-exports the AOI request helpers.
* `client/src/components/map/farmlandClasses.ts`: keeps unknown/unrecognized
  classification labels distinct from explicit not-prime farmland rather than
  defaulting unrecognized values to `not_prime`.
* `client/src/components/map/MapPanel.tsx`: uses the NCSS acronym-only logo in
  the map-panel header, with the official color and white variants for light
  and dark themes (NCSS Visual Standards Guide, March 2018); Vite-managed
  imports ensure the assets are included in the frontend build.
* `server/src/routes/chat.ts`: registers the request's AOI and passes its key
  to the provider call (ADR 0016).
* `packages/ai-sdk-providers/src/providers-server.ts`: request-scoped AOI
  registry; `databricksFetch` adds the AOI to the agent request as
  `custom_inputs.active_aoi` (ADR 0016).

Added paths:

* `client/src/components/map/**`: map panel (MapLibre and Terra Draw AOI
  drawing, GeoJSON paste and file input, `/api/geo/screen` client, farmland
  class mapping, legend, results table, regulatory notice, error states, the
  per-chat active-AOI context and the AOI chip). Plan 44 added the server
  map-layer renderer with server legends (`mapLayers.ts`, ADR 0017), the
  shown-result context and tool-card button (`MapResultContext.tsx`,
  `ShowOnMapButton.tsx`, calling `/api/geo/map`), the fixed context-overlay
  catalog and toggles (`overlays.ts`, `OverlayControl.tsx`), and identify
  popups with "Use as AOI" (`identify.ts`, `IdentifyPopup.tsx`). The visual
  refresh added the panel header, grouped draw/edit tools, the
  `StatusMessage.tsx` message bar and the screening summary strip. AOI import
  keeps file upload prominent and collapses pasted GeoJSON behind a disclosure.
* `client/src/assets/ncss-acronym-color.png` and
  `client/src/assets/ncss-acronym-white.png`: official NCSS acronym-only logo
  variants prepared from the
  [NCSS Visual Standards Guide](https://www.nrcs.usda.gov/sites/default/files/2022-09/NCSS_logo_style_guide.pdf)
  for light and dark map-panel headers.

### Update procedure

1. Re-copy the upstream folder at the new commit, applying the same exclusions.
2. Re-apply the changes listed in `### Local changes`.
3. Reconcile `client/package.json` and the other workspace `package.json` files
   with the local dependency additions, then let npm regenerate the root
   `package-lock.json`.
4. Compare `git ls-tree` hashes with upstream only for `frontend/` entries not
   in the local-changes list.
5. Re-run `make app-frontend-check`. If new error-level lint rules appear in
   upstream, update the skip list and this ADR rather than editing upstream
   files to satisfy them.
6. Update the base commit here and in the app `README.md` and `AGENTS.md`.

### Consequences

* **Positive:** deploys are reproducible; parity with upstream is checkable by
  hash for unchanged files; product features live in the same app.
* **Negative:** owning local changes turns upstream updates into a re-apply
  step, and the lockfile drifts from upstream once dependencies are added;
  about 600 vendored files; no typecheck gate; two upstream lint
  rules are skipped; frontend checks need Node 22 and npm, which Databricks
  serverless compute does not provide by default.

### Scope boundary

This decision covers how the chat UI is vendored and changed. The map panel and
AOI handoff are local changes made under Plan 42 (map code lives under
`client/src/components/map/`); the handoff contract is ADR 0016.
`custom_inputs`/`custom_outputs` handling stays out of scope.

## Validation & Compliance

* Parity: `git ls-tree HEAD apps/agent-fpac-soil-openai-sdk/frontend/` hashes
  equal upstream 0e57297 for every kept entry not in `### Local changes`.
* `make app-frontend-check` passes (CI `agent-app` job, Node 22).
* `make app-check` passes without npm.
* Deployed check: Plan 41 task 41.4.1; Plan 42 deployed trial before
  `Accepted`.
