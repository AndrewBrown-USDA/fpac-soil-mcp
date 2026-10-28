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
| 2 | 40.2.1 | pending |
| 2 | 40.2.2 | pending |
| 2 | 40.2.3 | pending |
| 3 | 40.3.1 | pending |

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

Pending.

## 40.2.2

Pending.

## 40.2.3

Pending.

## 40.3.1

Pending.
