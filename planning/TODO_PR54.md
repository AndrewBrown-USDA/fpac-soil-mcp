# TODO

## Goal
Resolve all four open code-review threads on PR #54 with backward-compatible migration handling, bounded request streaming, and accessible frontend controls.

## Tasks

### 1. Repair the trace ID migration sequence
- [x] Change the `0001_add_trace_id` journal timestamp so migration order is strictly `0000`, `0001`, then `0002`.
- [x] Make the trace ID column addition safe to replay for databases that already applied the earlier `0001` migration.
- [x] Validate the migration journal and SQL with the existing Drizzle checks and frontend build path.

### 2. Enforce the AOI request limit while streaming
- [x] Read `/api/geo/screen` request chunks incrementally and stop as soon as the accumulated body exceeds `geo.MAX_BODY_BYTES`.
- [x] Preserve the existing bounded 422 response, JSON validation, privacy behavior, and MCP-call suppression for rejected bodies.
- [x] Add a regression test proving an oversized chunked request is rejected before later chunks are consumed or MCP tools are called.

### 3. Restore browser zoom accessibility
- [x] Remove the viewport `maximum-scale` restriction while preserving the existing width and initial-scale settings.

### 4. Give the sidebar toggle an accessible name
- [x] Add a direct accessible label to the icon-only sidebar toggle button that remains available when the tooltip is hidden.
- [x] Preserve the current toggle behavior, icon state, tooltip, styling, and test identifier.

### 5. Keep vendored frontend documentation current
- [x] Update ADR 0015's local-change inventory for the reviewed vendored frontend files affected by these fixes.

### 6. Validate the complete review remediation
- [x] Run the focused agent-app geo screening tests.
- [x] Run the agent-app Python lint and offline test checks.
- [x] Run the vendored frontend install, read-only Biome lint, Drizzle migration/build, and production build checks.
- [x] Confirm all four PR #54 review findings are covered by the resulting diff and passing checks.

## Notes
- Scope is limited to the four unresolved code-review threads on PR #54 and directly coupled tests and documentation.
- The migration fix must support fresh databases, databases with only `0000` recorded, and databases where the earlier `0001` migration already added `traceId`.
- Request bodies must remain capped at 256 KB without buffering an arbitrarily larger upload first.
- Do not run the vendored frontend's write-enabled `npm run lint` or `lint:fix` scripts.
- Preserve unrelated worktree changes and the preliminary-screening/privacy boundaries in ADR 0016.
