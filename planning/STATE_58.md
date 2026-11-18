# STATE_58 -- Shared coverage vocabularies and `error` status (issue #84)

Branch: `refactor/coverage-vocab1` off `origin/main` 9acfbd2 (Plan 57 merged via PR #118). Local only, no upstream; ask before every push.
Plan status: approved by the user 2026-11-18 (D20). Next: record the baseline, then Wave 1.
Resume: read this file, then `git log --oneline origin/main..HEAD`, then the next pending wave in EXECUTION_PLAN_58.md.

## Baseline (record before Wave 1)

Expected from STATE_57 final (5dec901); 8c5ade6 only bumps the version and 9acfbd2 has the same tree.

- [ ] Root offline pytest (`-m "not live_network and not agent_eval"`): expect 1031 passed, 3 skipped, 45 deselected.
- [ ] App pytest (`apps/agent-fpac-soil-openai-sdk`, `--frozen`): expect 310 passed.
- [ ] JS harness (`/tmp` archive + `npm ci`): expect 20/20.
- [ ] `ruff check` + `ruff format --check` on a `/tmp` archive copy: clean.
- [ ] `make app-frontend-check`: biome 0 errors.
- [ ] Probe: FastMCP 4.1.7 `list_tools()` output schema renders a `Literal` field as `enum` (informs 58.4.1).

## Wave board

| Task | Title | Status | Commit |
| --- | --- | --- | --- |
| 58.1.1 | Coverage vocabulary module | pending | |
| 58.2.1 | SDA client rating rows | pending | |
| 58.2.2 | Soil lookup tools | pending | |
| 58.2.3 | NCCPI baseline failure reports `error` | pending | |
| 58.3.1 | Polygon analyzer | pending | |
| 58.3.2 | Corridor analyzer | pending | |
| 58.3.3 | LESA domain and `_lesa_coverage_status` | pending | |
| 58.4.1 | Type every coverage field; output schemas | pending | |
| 58.4.2 | Agent app and frontend consumers | pending | |
| 58.4.3 | README note and ADR 0019 | pending | |
| 58.5.1 | Final verification | pending | |
| 58.5.2 | Post-SDA checks (non-blocking) | pending | |

## Task reports
