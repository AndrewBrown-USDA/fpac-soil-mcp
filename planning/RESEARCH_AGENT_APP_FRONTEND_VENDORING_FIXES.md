# Research: Fixes for the Plan 40 Agent App Frontend Review

Status: research only; no code changed. Input for fixing PR branch `feature/agent-app-map1`.

Date: 2026-10-28. Reviewed `origin/feature/agent-app-map1` (b02527d) against `origin/main` (a06092a). Sources were read in this session:

* Upstream template `databricks/app-templates`, cloned read-only with the user's permission. Origin HEAD was 3826450 (2026-10-21).
* The MLflow 3.17.1 wheel from PyPI. This is the version pinned in the app's `uv.lock`.
* Public Databricks docs.
* This repo.

## Question

The two-axis review of Plan 40 found problems. For each one:

1. Which fix will actually work?
2. Should it be fixed in Databricks (workspace clone and serverless compute) or sent back to the local agent that drafted the PR?

## Summary

1. **The PR vendored only the client half of the template.** The pinned tree `c7e05c0787909bc6e0b79adf2f162fd0bc2a8edd` is `e2e-chatbot-app-next/client` at upstream commit `0e572976459aafa3d41047067382cb9a6c015d52` (2026-10-16). It is not the whole `e2e-chatbot-app-next` directory that `start_app.py` used to clone[^u-pin]. `main` ran `npm install`, `npm run build` and `npm run start` in that whole directory, which is an npm workspace with `client`, `server` and `packages/*`[^u-rootpkg]. The Express server is what serves `/api/chat`, `/api/session`, `/api/history`, `/api/config` and the built client[^u-index]. **Working fix: vendor the whole `e2e-chatbot-app-next` directory at commit 0e57297, with its own lockfile.** Do not rebuild the server or patch around the missing pieces.
2. **No change to the readiness pattern is needed after that.** The upstream server prints `Backend server is running on http://localhost:<port>`[^u-index]. `start_app.py` matches `Server is running on http://localhost` with `re.IGNORECASE`[^r-ready], so the full template satisfies it as-is.
3. **The session-ID change is a real regression.** The upstream server sends the chat ID as `context.conversation_id` in the `/invocations` body, never as `custom_inputs.session_id`[^u-ctx]. `get_session_id` reads `context.conversation_id` first[^r-utils]. The branch replaced it with `sanitize_custom_inputs(...).get("session_id")`, so chats from the real UI would lose MLflow trace session grouping. **Fix: go back to `get_session_id`.**
4. **Custom routes work, but the test checks the wrong thing.** MLflow 3.17.1's chat-proxy middleware first checks every route registered on the app, whatever order they were added in. Only unmatched requests are forwarded, and only for allowlisted paths such as `/api/*`, with 503 on a connection error[^m-proxy]. So `/api/geo/health` is served by FastAPI. The assertion that it comes after `/invocations` doesn't test anything. The upstream Express server doesn't use `/api/geo`[^u-index], so the prefix is free.
5. **The upstream template never sends `custom_inputs` or reads `custom_outputs`.** No file in `server/`, `packages/` or `client/src` mentions them[^u-noci]. That is the "exact adapter loss" Plan 40 task 40.2.1 asked to record. It also supports decision D6: an AOI needs its own backend route, not the chat transport.
6. **Runtime facts that constrain the fix.** The Databricks Apps runtime has Node.js 22.16 and no preinstalled Node libraries. It installs automatically only from a `package.json` at the app root[^d-env][^d-deps]. The frontend lives in a subfolder, so `start_app.py` must keep running npm itself. CI uses Node 20; it should use 22 to match the runtime.
7. **Serverless compute can't validate the frontend.** `/usr/local/bin/npm` and `npx` are broken symlinks; there is no `node_modules/npm`[^r-npm]. Every frontend install, lint, build and run check has to happen locally (or in CI). This is the main reason for how the work is split below.

## Findings and fixes

| # | Problem | Working fix | Evidence | Owner |
|---|---|---|---|---|
| F1 | No Express server, no `start` script; `npm run start` fails, so the deployed UI breaks after merge | Vendor the whole `e2e-chatbot-app-next` at 0e57297: root `package.json`, upstream `package-lock.json`, `client/`, `server/`, `packages/`, `scripts/` (migrate), `biome.jsonc`, `tsconfig.json`, `drizzle.config.ts`. Leave out `.claude/`, `CLAUDE.md`, `tests/`, `playwright.config.ts`, and the standalone-deploy files `app.yaml`, `databricks.yml`, `manifest.yaml`. Keep the layout: the server serves `../../client/dist` relative to its build output[^u-index]. | [^u-pin][^u-rootpkg][^u-index] | Local agent |
| F2 | Lockfile links `@databricks/chatbot-*` to `packages/*` folders that aren't in the repo; two local shims stand in for them | Use the upstream root `package-lock.json` without changes; delete `src/types/databricks-chatbot-packages.d.ts` and `src/vendor/chatbot-core-errors.ts`, and undo the `vite.config.ts` alias. Apart from these, the vendored client matches upstream except `package.json`, `tsconfig.json` and `vite.config.ts`[^r-clientdiff]. | [^r-lock][^r-clientdiff] | Local agent |
| F3 | Lint, typecheck and build scripts were rewritten for the client alone | From the vendored root: `npm ci`, then `npx biome lint` (not the upstream `lint` script, which uses `--write --unsafe` and edits files[^u-rootpkg]), then `npm run build`. Without Postgres variables, `build` runs `db:migrate`, which skips itself ("ephemeral mode")[^u-migrate]. A typecheck command must be chosen and proven locally; upstream has no root typecheck script. | [^u-rootpkg][^u-migrate] | Local agent |
| F4 | Launcher uses `npm install`, not `npm ci`; the no-UI fallback was removed | In `start_app.py`, use `npm ci`, and if `frontend/package.json` is missing, print a warning and set `no_ui` (the old fallback behaviour) | [^r-startapp] | Local agent (same file and test cycle as F1) |
| F5 | `make app-check` now needs npm, so it fails on serverless | Keep `app-check` as Python-only (lint + test). Keep `app-frontend-check` as its own target. Have CI run both. Use Node `22` in `actions/setup-node`, with the cache path pointing at the new root lockfile. | [^d-env][^r-npm] | Local agent (Makefile/CI depend on the new layout) |
| F6 | ADR number 0014 already used by `origin/feat/sdv-metadata-contract`; this ADR lacks MADR frontmatter and isn't in the README index | Renumber to 0015, add the frontmatter and sections used by ADR 0013, add a row to `docs/decisions/README.md`, and record commit 0e57297 (not just the tree) plus the full-directory scope | [^r-adr] | Local agent (its text depends on F1) |
| F7 | `get_session_id` replaced, so `context.conversation_id` is lost | Restore `get_session_id(request)` in `invoke_handler` and `stream_handler`. Delete `sanitize_custom_inputs` (nothing else uses it) and its two unit tests. Keep the test that `custom_inputs` never reach `Runner.run`, and add a stream-handler version of it. Add a test that `context.conversation_id` becomes the trace session. | [^u-ctx][^r-utils] | Databricks |
| F8 | Route-order assertion is meaningless; the unknown-route test passes for the wrong reason | Remove the order assertion. Keep the 200 probe. For unknown `/api/geo/*`, mock the proxy client and assert the request is forwarded to the chat app, not handled by `geo_health`, or drop that test. | [^m-proxy] | Databricks |
| F9 | Evidence files don't match what was found | Update `planning/evidence/40.2.1-aoi.md` with the exact adapter loss (point 5) and the F7 change. Update `40.2.2-routes.md` with the route-first matching rule. | [^u-noci][^m-proxy] | Databricks |
| F10 | No real probe through the app URL (40.2.2), and no real UI round trip | After F1-F9, deploy the branch to the app (the Apps git source is `main`, so switch the branch temporarily or use a test app). Then check `/`, `/api/config`, `/api/geo/health`, one chat turn, and that the MLflow trace has `mlflow.trace.session` set to the chat ID. | [^r-appyaml] | Databricks (user, manual) |
| F11 | Leftover template images | Optional: remove the unused `public/` images, or keep them so the copy matches upstream exactly. Decide once in the ADR. | review | Local agent |

## Recommended split and order

**Send back to the local agent (needs npm, Node 22 and a local browser): F1-F6, F11.** These all touch the frontend layout, launcher, Makefile, CI and ADR, which depend on each other. Splitting them across two environments would cause conflicts. Acceptance:

* the frontend checks in F3 pass
* `make app-check` passes
* `uv run start-app` starts locally, logs "Backend server is running", serves the UI on port 8000 through the chat proxy, and finishes one chat turn against the deployed MCP server
* `git ls-files apps/agent-fpac-soil-openai-sdk/frontend` shows the upstream layout and no shims

**Fix in Databricks: F7-F9 now, F10 after the local agent's push.** These are Python-only and can be checked with the app's uv test suite on serverless (see the workspace test recipe in project notes). They touch `agent_server/agent.py`, `agent_server/history.py`, `tests/test_aoi_handoff.py`, `tests/test_custom_routes.py` and two evidence files. None of these overlap with the local agent's files.

Order:

1. Commit F7-F9 here.
2. The user pushes.
3. The local agent pulls and does F1-F6.
4. The user runs F10 against a test deployment before merging.

If F7-F9 can't be pushed first, send them to the local agent as patch notes instead.

## Unverified

* `npm ci` with the upstream root lockfile, and the full build, haven't been run anywhere in this session (no npm on serverless).
* No typecheck command for the full workspace has been proven to pass.
* Deployed Apps egress to `registry.npmjs.org` is assumed from `main`'s current behaviour (it installs at startup and works). It wasn't re-tested.

## Sources

[^u-pin]: `git rev-parse 0e572976:e2e-chatbot-app-next/client` = `c7e05c07...` in `databricks/app-templates`. The same tree also matches parents 4e60dd0 and e0b2d2e. No `e2e-chatbot-app-next` commits after 0e57297 up to origin HEAD 3826450.
[^u-rootpkg]: `e2e-chatbot-app-next/package.json` at 0e57297: `workspaces: ["client","server","packages/*"]`; `build` = `db:migrate && build:client && build:server`; `start` = server workspace `start`; `lint` = `biome lint --write --unsafe`. `server/package.json`: `start` = `NODE_ENV=production node ... dist/index.mjs`.
[^u-index]: `e2e-chatbot-app-next/server/src/index.ts` at 0e57297: L36-38 port from `CHAT_APP_PORT`/`PORT`; L59-64 `/api/chat`, `/api/history`, `/api/session`, `/api/messages`, `/api/config`, `/api/feedback`; L67-70 `/invocations` proxy to `API_PROXY`; L123-131 static `../../client/dist` plus SPA fallback; L250-251 `Backend server is running on http://localhost:${PORT}`.
[^u-ctx]: `e2e-chatbot-app-next/packages/ai-sdk-providers/src/providers-server.ts` L16 header `x-databricks-conversation-id`; L106-127 turns it into body `context.conversation_id` and `user_id`; `server/src/routes/chat.ts` L253 sets the header to the chat `id`.
[^u-noci]: `git grep -E "custom_inputs|custom_outputs|customInputs|databricksOptions"` over `server/`, `packages/`, `client/src` at 0e57297 returned no matches.
[^u-migrate]: `e2e-chatbot-app-next/scripts/migrate.ts` at 0e57297: when `isDatabaseAvailable()` is false, it warns "Skipping migrations in ephemeral mode" and exits 0.
[^m-proxy]: `mlflow-3.17.1-py3-none-any.whl`, `mlflow/genai/agent_server/server.py`: L133-134 allowlist (`/`, `/favicon.ico`, `/ping`, `/assets/`, `/api/`, `/chat/`); L167-168 any registered route whose `path_regex` matches goes to `call_next`; L179 404 for paths not on the allowlist; L224-227 503 on `httpx.ConnectError`, 502 on other errors.
[^d-env]: Databricks Apps environment, https://docs.databricks.com/aws/en/dev-tools/databricks-apps/system-env/ (Node.js 22.16; "No Node.js libraries are pre-installed").
[^d-deps]: Manage dependencies for a Databricks app, https://docs.databricks.com/aws/en/dev-tools/databricks-apps/dependencies/ ("include a package.json file in the root of your app"; npm unless `pnpm-lock.yaml` exists).
[^r-ready]: `apps/agent-fpac-soil-openai-sdk/scripts/start_app.py` L40 `FRONTEND_READY`; L120 `re.search(p, line, re.IGNORECASE)` (origin/main).
[^r-utils]: `apps/agent-fpac-soil-openai-sdk/agent_server/utils.py` L11-16 `get_session_id` (context first, then `custom_inputs.session_id`).
[^r-startapp]: `scripts/start_app.py` on the branch: `API_PROXY` set unconditionally; `npm install` / `npm run build` / `npm run start` in `Path(__file__).parent.parent / "frontend"`.
[^r-lock]: branch `frontend/package-lock.json`: root has no `workspaces`; devDependencies `@databricks/chatbot-auth|core|db: "*"` resolve to `"link": true` entries for `packages/*`, which are not in the tree. 668 entries resolve to `registry.npmjs.org` (none to the workspace package proxy).
[^r-clientdiff]: file-by-file blob comparison of branch `frontend/` with upstream `client/` at 0e57297: only `package.json`, `tsconfig.json`, `vite.config.ts` differ. The branch adds `package-lock.json`, `src/types/databricks-chatbot-packages.d.ts`, `src/vendor/chatbot-core-errors.ts`.
[^r-adr]: `docs/decisions/0014-registry-validated-sdv-metadata-contract.md` on `origin/feat/sdv-metadata-contract`; `docs/decisions/0014-vendored-agent-app-frontend.md` on the PR branch; `docs/decisions/README.md` unchanged on the PR branch; ADR 0013 frontmatter format.
[^r-npm]: serverless compute 2026-10-28: `npm: command not found` although `/usr/local/bin/npm` exists; `/usr/local/lib/node_modules` absent; node v22.23.4.
[^r-appyaml]: `apps/agent-fpac-soil-openai-sdk/app.yaml` (`uv run start-app`, `CHAT_APP_PORT=3000`, `API_PROXY=http://localhost:8000/invocations`); app README: deploys from git source branch `main`.
