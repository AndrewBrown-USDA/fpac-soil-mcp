# Orchestration 42 State

## Baseline

- **Repository:** personal clone `/Workspace/Users/andrew.g.brown@usda.gov/fpac-soil-mcp`; work happens in a `/tmp` clone and is fast-forwarded into the workspace clone after each task (D8).
- **Branch:** `feature/agent-app-map1` at 0823c7f (merge of main 6e730b8); 0 behind / 20 ahead of `origin/main`; pushed. PR open, not merged.
- **Baseline date:** 2026-10-30.
- **App tests (`make app-test`, /tmp merge of 421acaf + 6e730b8, same tree as 0823c7f):** 61 passed; `make app-lint` clean.
- **Root `make check`:** ruff clean, 508 files formatted, 597 passed / 3 skipped / 44 deselected.
- **`make app-frontend-check` (421acaf; frontend unchanged since):** `npm ci` 753 packages; biome 588 files, 0 errors, 10 warnings; client and server builds complete.
- **Frontend parity:** 604 files blob- and mode-identical to upstream 0e57297; only ADR 0015 exclusions missing.
- **Deployed app:** `agent-fpac-soil-openai-sdk` `default_git_source.branch = feature/agent-app-map1`, `auto_deploy: true` (user changed it 2026-10-30; `apps get` at plan time showed compute STARTING, no active deployment listed yet). Experiment 517983779529169.
- **PR CI:** green per the user on 421acaf; not re-checked on 0823c7f.
- **Re-baseline:** at the start of wave 1, re-run the three checks on the branch head from a fresh `/tmp` clone and record here.
- **Re-baseline result (2026-10-30, fresh `/tmp/p42` at 9a19b7e, new compute):** `make app-check` lint clean, 61 passed; `make app-frontend-check` `npm ci` 753 packages, biome 588 files 0 errors 10 warnings, client and server builds complete; root `make check` ruff clean, 511 files formatted, 597 passed / 3 skipped / 44 deselected. Matches the baseline above (ruff's formatted-file count differs by clone; not a regression). Node via `/tmp/nodevenv` + `/tmp/nbin` wrappers (npm 10.9.3, node 22.20.0).

## Wave board

| Wave | Executor | Task | Status |
|---|---|---|---|
| 1 | Databricks | 42.1.1 | done (4da95a2) |
| 1 | Databricks | 42.1.2 | done (254910a) |
| 1 | gate | app-check, root check | done (254910a) |
| 2 | Databricks | 42.2.1 | pending |
| 2 | Databricks | 42.2.2 | pending |
| 2 | gate | app-check, app-frontend-check, root check | pending |
| 2 | User + Databricks | 42.2.3 | pending |
| 3 | Databricks | 42.3.1 | pending |
| 3 | Databricks | 42.3.2 | pending |
| 3 | gate | app-check, app-frontend-check, root check | pending |
| 4 | Databricks | 42.4.1 | pending |
| 4 | gate | app-check, app-frontend-check, root check | pending |
| 5 | User + Databricks | 42.5.1 | pending |
| 5 | Databricks | 42.5.2 | pending |

## Task reports

<!-- Append one concise report (<=15 lines) under each task heading: status, changed files, exact commands and results, deviations, gotchas, commit. No coordinates. -->

## 42.1.1

- Status: done, commit 4da95a2 `docs(agent-app): allow owned local changes to the vendored frontend`.
- Changed: `docs/decisions/0015-vendored-agent-app-frontend.md` (status `Proposed`, `EXECUTION_PLAN_42` in `source_context`, drivers/option 1/outcome reworded to an owned copy from base 0e57297, new Lockfile and Local changes bullets, `### Local changes` empty-state line, 6-step update procedure, merged Negative consequence, scope boundary points to ADR 0016, parity and deployed-check validation updated); app `AGENTS.md` (`frontend/` Find-Things line, Frontend workflow steps 1-5 incl. `npm install --workspace @databricks/chatbot-client --save-exact`); app `README.md` (vendored-frontend paragraph and update sentence).
- Checks: `grep -nE 'No local edits|never regenerate|byte-for-byte|Do not add map' <3 files>` empty; `status: "Proposed"` and `### Local changes` match.
- Deviations: none. Left README "Deploying" (`main` git source) unchanged as the steady-state instruction.
- Gotchas: 42.4.1 fills `### Local changes`; 42.2.2 must list its added/changed frontend paths there too, or leave a note for 42.4.1.

## 42.1.2

- Status: done, commit 254910a `docs(decisions): propose out-of-band AOI screening handoff`.
- Changed: new `docs/decisions/0016-out-of-band-aoi-screening-handoff.md` (`Proposed`, 2026-10-30; context cites Plan 40 R6 evidence and decision; options 1-4; outcome states the 42.2.1 request limits, MCP calls, response shape, `chat_summary` allowlist and exclusions, handoff, privacy and lifecycle; validation lists the 42.2.1 offline tests and 42.5.1 trial); `docs/decisions/README.md` (0015 row `Proposed`, context `40, 41, 42`; new 0016 row; one Databricks Delivery sentence).
- Checks: `status: "Proposed"` matches; both README rows `Proposed`; `grep -nE '[0-9]{1,3}\.[0-9]{4,}'` on ADR 0016 empty.
- Deviations: none.
- Gotchas: 42.2.1 implements the ADR 0016 contract as written; if it must differ (status codes, field names), update ADR 0016 in the same task.

## Wave 1 gate

- Fresh `/tmp/p42g` clone at 254910a: `make app-check` ruff clean, 11 files formatted, 61 passed; root `make check` ruff clean, 514 files formatted, 597 passed / 3 skipped / 44 deselected. `app-frontend-check` not required (no frontend change). Clone clean after checks.
