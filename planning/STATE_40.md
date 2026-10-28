# Orchestration 40 State

## Baseline

- **Repository:** `D:\workspace\fpac-soil-mcp`.
- **Plan:** Agent-app map preparation, M0 and M1 only.
- **Baseline date:** 2026-10-27.
- **App validation command:** `make app-check` from the repository root; direct root-level pytest against the app is not a valid baseline.
- **Observed baseline issue:** direct `uv run pytest apps\agent-fpac-soil-openai-sdk\tests -q` failed collection because the app project import path and `ruamel` dependency were not active. Re-run the canonical command before Wave 1.
- **Canonical baseline:** `make app-check` passed: Ruff check passed, 9 files formatted, and 54 app tests passed with 1 pre-existing `asyncio_mode` warning.
- **Entry-point sizes:** `scripts\start_app.py` 345 lines; `agent_server\agent.py` 167 lines; `agent_server\start_server.py` 25 lines; `MASTER_PLAN.md` 554 lines; map research 292 lines; spatial strategy 214 lines.
- **Accepted constraints:** ADR 0003 preliminary-screening boundary; ADR 0010 privacy handling; ADR 0012 separate MCP client; ADR 0013 public PyPI default.
- **User decisions:** vendor template; custom basemap URLs eventually allowed with validation; browser GeoJSON/WKT MVP; session-only AOIs; M0+M1 scope; max 3 workers; recommended automated plus documented integration evidence; default worker policy.
- **Working-tree status:** capture immediately before execution; do not revert unrelated changes.

## Wave board

| Wave | Task | Status |
|---|---|---|
| 1 | 40.1.1 | done |
| 2 | 40.2.1 | done |
| 2 | 40.2.2 | done |
| 2 | 40.2.3 | done |
| 3 | 40.3.1 | done |

## Task reports

<!-- Append one concise report under each task heading. Include status, changed files/line ranges, exact validation commands and results, deviations, and dependent-task gotchas. -->

## 40.1.1

- **Status:** done after one escalation; vendored frontend and startup/validation integration completed.
- **Changed files:** vendored `apps\agent-fpac-soil-openai-sdk\frontend\` and lockfile; `scripts\start_app.py`; app README/AGENTS; root `Makefile`; CI workflow; ADR 0014.
- **Source:** materialized the verified frontend tree `c7e05c0787909bc6e0b79adf2f162fd0bc2a8edd`; generated a frontend lockfile from the verified upstream package metadata (source package-lock blob `664a26741dfba5f8fbf54d3abe583180876cb49a`).
- **Checks:** `make app-check` passed: Ruff passed, 54 Python app tests passed with 1 pre-existing `asyncio_mode` warning, `npm ci` passed, frontend lint/typecheck/build passed. Frontend emitted dependency/deprecation warnings only.
- **Deviation:** added local frontend shims and narrowed frontend validation to the vendored client boundary to resolve upstream workspace assumptions; no map behavior or runtime clone was introduced. Node modules and staging artifacts were removed.
- **Gotcha:** frontend validation uses the vendored client package boundary rather than the upstream monorepo workspace.

## 40.2.1

- **Status:** done; raw AOI integration remains blocked because pre-trace redaction could not be proven.
- **Files:** agent/history filtering, focused AOI tests, evidence, and AOI handoff decision record.
- **Checks:** targeted AOI tests passed (3); combined focused tests passed (6); full `make app-check` passed with 60 app tests.
- **Deviation:** none from the approved safety boundary; no raw geometry, durable AOI storage, or M3 map envelope added.
- **Gotcha:** future AOI implementation must resolve pre-trace capture order before enabling geometry handoff.

## 40.2.2

- **Status:** done; added minimal `GET /api/geo/health` probe and route evidence.
- **Files:** `start_server.py`, `tests\test_custom_routes.py`, route evidence.
- **Checks:** route tests passed (3); full `make app-check` passed. One Ruff import-order failure was fixed on the permitted retry.
- **Deviation:** none; no proxy, catalog, conversion, or unrestricted forwarding behavior added.
- **Gotcha:** future `/api/geo/*` routes still require deployed/chat-proxy verification.

## 40.2.3

- **Status:** done; networking evidence recorded without production code.
- **Files:** `planning\evidence\40.2.3-networking.md`.
- **Checks:** local HTTPS/CORS observations recorded; browser/app-context behavior remains explicitly unknown.
- **Deviation:** none; no proxy, map component, or deployment networking policy added.
- **Gotcha:** later map work must validate CORS and egress from the intended app context.

## 40.3.1

- **Status:** done; M1 findings reviewed and frozen without enabling AOI integration.
- **Changed files:** `planning\tasks\40.3.1.todo.md`; this report appended to `planning\STATE_40.md`. No Plan 40 implementation files or M2/M3 files were changed.
- **Review:** user decisions are represented as vendor-template, custom-URLs-with-validation, browser-MVP, session-only AOIs, and M0+M1 scope. Wave 2 file scopes are disjoint. Acceptance commands are reproducible. ADR 0003 preliminary-screening and ADR 0012 separate-MCP-client boundaries remain intact.
- **Checks:** `make app-check` passed: Ruff check, format check, 60 app tests passed with the existing unknown `asyncio_mode` and MLflow SQLAlchemy deprecation warnings. `cd apps\agent-fpac-soil-openai-sdk\frontend && npm ci && npm run lint && npm run typecheck && npm run build` passed: 555 packages installed, lint/typecheck/build passed; npm reported dependency audit vulnerabilities and deprecation/install-script warnings only.
- **Findings:** 40.2.1 correctly keeps AOI integration blocked because pre-trace redaction is unproven; 40.2.2 proves only the bounded health probe; 40.2.3 preserves browser/app-context CORS, deployed egress, exact tile/layer, and constrained-proxy behavior as unknown where untested. No unsupported success claims or silent failures were found.
- **Scope note:** an untracked `apps\agent-fpac-soil-openai-sdk\mlflow.db` was present before this task's validation and was not modified or included.
- **Deviation:** none.
- **Handoff:** future work must resolve the R6/pre-trace blocker before AOI dispatch, preserve session-only/raw-geometry exclusions, and separately scope M2/M3; no AOI, map UI, proxy, conversion, or server `map` envelope work is authorized by this task.
