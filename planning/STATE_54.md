# STATE 54: Agent-App Map Usability and Corridor Workflow

Resume point for orchestration 54. Plan: `planning/EXECUTION_PLAN_54.md`. Worker prompt: `planning/PROMPT_TEMPLATE_54.md`.

## Baseline

- [x] Repository `/home/andrew/work/fpac-soil-mcp`, branch `feature/local-dev-trial`, clean at `f05b84c` before baseline rerun.
- [x] Existing Plan 53 final gates at this exact code commit: `make check` 993 passed, 3 skipped, 45 deselected; `make app-check` 266 passed; `make app-frontend-check` passed.
- [x] Frontend baseline caveats from Plan 53: 11 lint warnings (including one MapPanel exhaustive-dependency warning), 10 npm audit advisories, existing Vite/React/chunk warnings; build passed.
- [x] Planning artifacts tracked; plan-only commits remain separate from implementation commits.
- [x] Re-ran baseline at `f05b84c`: `make check` 993 passed/3 skipped/45 deselected; `make app-check` 266 passed; `make app-frontend-check` passed with 11 existing warnings, 10 npm advisories, ephemeral DB migration skip, and existing build warnings.

## Decisions

- Plan 54 follows Plan 53 on `feature/local-dev-trial`; user asks to start at G42 and include as many agent-app map UI goals as feasible.
- Usability-first priority: compact icon controls, accessible hover/focus labels, crosshair drawing/measurement cursor, miles as measure default.
- SSURGO default refers to returned server result polygons, not fixed context overlay. On each new successful result, show inline result vectors by default; preserve explicit hide control.
- Amend ADR 0016: corridor is a separate per-chat context from polygon `active_aoi`; primary centerline, alternatives, staging geometry, buffer distance and units.
- Both direct map corridor screening and chat handoff are supported. Corridor context auto-attaches per conversation, has a separate detach control, and does not replace polygon AOI.
- Corridor buffer is blank until user entry, unit defaults to feet, distance is on each side. Measurement unit independently defaults to miles.
- Map corridor screening stays preliminary and sends no Site Assessment inputs. Direct route is stateless/untraced and uses existing `analyze_corridor_fppa` only.
- CDL color key follows official USDA NASS code/name/color table; context imagery is not analysis evidence.
- NAIP source changes to the user-selected USDA FPAC `conus_naip` ImageServer. Planning probes returned HTTP 200 PNG with origin-specific CORS; service metadata includes `Purpose: test:202407180638 naip service`, a caveat the user approved retaining.
- At most two concurrent workers; planning artifacts are tracked and planning-only commits separate.
- Preserve ADR 0003, update ADR 0015 local-change ledger, amend ADR 0016, preserve ADR 0017 server-owned map contract.

## Wave Board

| Wave | Task | Status | Commit | Notes |
|---|---|---|---|---|
| 1 | 54.1.1 Compact accessible map controls and cursor defaults | pending | | G42 |
| 2 | 54.2.1 Map-pane server legend and authoritative CDL key | pending | | G43 |
| 2 | 54.2.2 Replace NAIP with fixed USDA FPAC ImageServer | pending | | G49; test-purpose metadata caveat |
| 3 | 54.3.1 Returned SSURGO visibility on new results | pending | | G44 |
| 4 | 54.4.1 ADR 0016 corridor amendment and validated context model | pending | | G45 |
| 5 | 54.5.1 Direct stateless corridor screening route | pending | | G46 |
| 5 | 54.5.2 Bind corridor context to agent tool calls | pending | | G47 |
| 6 | 54.6.1 Per-chat corridor context transport | pending | | G47 |
| 7 | 54.7.1 Corridor drawing and buffer controls | pending | | G48 |
| 8 | 54.8.1 Direct corridor submission and result display | pending | | G48 |
| 9 | Integrated validation and handoff | pending | | |

## Task Reports

(Workers append <=15-line reports here after each committed task.)

## Final Acceptance

- [ ] All task reports and implementation commits recorded.
- [ ] `make app-check` passes.
- [ ] `make app-frontend-check` passes; warnings are compared with baseline.
- [ ] Focused corridor, legend, map, and existing regression suites pass.
- [ ] `git diff --check` passes; ADR 0015 ledger and ADR 0016 amendment reviewed.
- [ ] Polygon AOI and corridor context remain separate; direct map calls remain untraced and preliminary; no Site Assessment inputs are submitted.
- [ ] No remote actions performed.
