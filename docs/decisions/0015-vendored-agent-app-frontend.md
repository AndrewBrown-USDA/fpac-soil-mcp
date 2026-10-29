---
id: "0015"
title: "Vendor the Full Pinned Chat Template for the Agent App Frontend"
status: "Accepted"
date: 2026-10-28
authors:
  - "Andrew G. Brown"
supersedes: null
superseded_by: null
source_context: "EXECUTION_PLAN_40, EXECUTION_PLAN_41"
---

# 15. Vendor the Full Pinned Chat Template for the Agent App Frontend

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
* The copy must be provably identical to a named upstream commit, so updates are
  a re-copy and a diff, not a merge of local edits.
* Python checks must keep running where npm is unavailable (Databricks
  serverless compute).
* Frontend checks must be read-only; they must not rewrite vendored files.

## Considered Options

1. **Vendor the whole `e2e-chatbot-app-next` folder at one upstream commit, with
   its own root lockfile and no local edits.**
2. **Vendor `client/` only, with shims for the workspace packages** (the Plan 40
   layout) -- diverges from upstream and needs a hand-built lockfile.
3. **Keep cloning upstream at startup** -- unpinned and not reviewable.

## Decision Outcome

Chosen option: "Vendor the whole folder at one commit", because it is the only
layout that builds with the upstream lockfile and stays byte-comparable to
upstream.

* **Pin:** upstream commit `0e572976459aafa3d41047067382cb9a6c015d52`.
  `frontend/` equals the upstream folder at that commit, including file modes,
  minus the excluded files below.
* **Kept:** root `package.json` (npm workspaces `client`, `server`,
  `packages/*`), root `package-lock.json` byte-for-byte, `client/`, `server/`,
  `packages/`, `scripts/`, `biome.jsonc`, `tsconfig.json`, `drizzle.config.ts`,
  `knip.json`, `.gitignore`, `.env.example`, `README.md`. `client/`, `server/`
  and `packages/` stay siblings.
* **Excluded:** `.claude/`, `CLAUDE.md`, `tests/`, `playwright.config.ts`,
  `app.yaml`, `databricks.yml`, `manifest.yaml`.
* **No local edits:** no shims, no map or AOI behaviour.
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

### Update procedure

1. Re-copy the upstream folder at the new commit, applying the same exclusions.
2. Keep the upstream root `package-lock.json`; never regenerate it.
3. Compare `git ls-tree` hashes of `frontend/` entries with upstream.
4. Re-run `make app-frontend-check`. If new error-level lint rules appear in
   upstream, update the skip list and this ADR; do not edit vendored files.
5. Update the pinned commit here and in the app `README.md` and `AGENTS.md`.

### Consequences

* **Positive:** deploys are reproducible; parity with upstream is checkable by
  hash; updates are mechanical.
* **Negative:** about 600 vendored files; no typecheck gate; two upstream lint
  rules are skipped; frontend checks need Node 22 and npm, which Databricks
  serverless compute does not provide by default.

### Scope boundary

This decision vendors the existing chat UI only. Map rendering, AOI drawing,
map routes, and `custom_inputs`/`custom_outputs` handling stay deferred to later
plan work.

## Validation & Compliance

* Parity: `git ls-tree HEAD apps/agent-fpac-soil-openai-sdk/frontend/` hashes
  equal upstream 0e57297 for every kept entry.
* `make app-frontend-check` passes (CI `agent-app` job, Node 22).
* `make app-check` passes without npm.
* Deployed check: Plan 41 task 41.4.1.
