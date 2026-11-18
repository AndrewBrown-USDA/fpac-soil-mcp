# STATE_58 -- Shared coverage vocabularies and `error` status (issue #84)

Branch: `refactor/coverage-vocab1` off `origin/main` 9acfbd2 (Plan 57 merged via PR #118). Local only, no upstream; ask before every push.
Plan status: approved by the user 2026-11-18 (D20). Baseline recorded 2026-11-18 on 6a293a0. Next: Wave 1.
Resume: read this file, then `git log --oneline origin/main..HEAD`, then the next pending wave in EXECUTION_PLAN_58.md.

## Baseline (recorded 2026-11-18 on 6a293a0, serverless)

Matches STATE_57 final (5dec901); 9acfbd2 has the same tree as 8c5ade6.

- [x] Root offline pytest (`-m "not live_network and not agent_eval"`): 1031 passed, 3 skipped, 45 deselected.
- [x] App pytest (`apps/agent-fpac-soil-openai-sdk`, `--frozen`): 310 passed.
- [x] JS harness (`/tmp` archive + `npm ci`): 20/20.
- [x] `ruff check` + `ruff format --check` on a `/tmp` archive copy: clean (811 files formatted).
- [x] `make app-frontend-check` (on the `/tmp` archive): biome 0 errors, 10 warnings; build OK.
- [x] Probe: FastMCP 4.1.7 renders `Literal` as `{"enum": [...], "type": "string"}` and `Literal | None` as `anyOf[enum, null]`. Read `Tool.output_schema` (`outputSchema` is deprecated).

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
