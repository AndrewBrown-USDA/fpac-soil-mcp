# Review 44 -- two-axis review of `origin/main...feature/agent-app-map2`

Task 44.11.1. Reviewed 2026-11-07 at branch head e760691 (merge base 06525de; 76 files, +5810/-223).

## Scope and limits

- **Standards axis:** root and app `AGENTS.md`, ADRs 0003, 0010-0017, repo style.
- **Spec axis:** `EXECUTION_PLAN_44.md` Goal & Scope, D1-D9, A1-A3 (Decision Log), A4 (recorded in `STATE_44.md`), and the M3-M5 rows of `RESEARCH_MAP_WIDGET_AGENT_APP.md` section 10.
- **Read closely:** `tools/spatial_analysis_tools.py` and `tools/__init__.py` registrations, `agent_server/geo.py` diff, `map_contract.py` (`simplify_for_display`, `enforce_size_cap`), `identify.ts` and `overlays.ts` URL handling, ADR 0015 local-changes list, ADR 0016 request/MCP-call text, `.env.example`, `manifest.yaml`, README tool and configuration rows.
- **Not read line by line:** `polygon_analysis.py` and `corridor_analysis.py` map code, `mapLayers.ts`, `MapPanel.tsx`, `Legend.tsx`. For these the review relies on the task tests and gates in `STATE_44.md` and on the 44.8.1 and 44.10.1 browser trials.
- **Main drift:** `origin/main` is at 87e0a75, 5 commits ahead of the merge base (Dependabot #76/#77 and #80 eval-harness config). `git merge-tree` reports no conflicts.

## Findings

Severity: **high** blocks merge; **medium** fix before merge; **low** fix or accept; **info** no action needed.

| # | Axis | Severity | Finding | Evidence | Proposal |
| --- | --- | --- | --- | --- | --- |
| R1 | Standards | medium | App `AGENTS.md` still says `/api/geo/screen` makes "the two MCP calls"; since 44.5.1 it makes one (`analyze_farmland_by_polygon` with `include_map=True`). | app `AGENTS.md` L34; `geo.py` `screen_aoi` | Fix (44.11.2) |
| R2 | Standards | medium | ADR 0016 (Accepted) still describes the screening route calling `get_soil_polygons_by_geometry` with `clip=True` and a "clipped soil FeatureCollection" in `display`. Both were replaced by the ADR 0017 `map` block. Per the ADR convention, a merged ADR gets a dated amendment, not a rewrite. | ADR 0016 L128-134 | Fix (44.11.2): dated amendment pointing to ADR 0017 |
| R3 | Standards | low | `.env.example` does not list `MAP_SIMPLIFY_TOLERANCE_M` or `MAP_MAX_GEOJSON_BYTES`. Root `AGENTS.md` names `.env.example` as the list of supported variables. README L352-353 documents both. | `grep MAP_ .env.example` empty | Fix (44.11.2) |
| R4 | Standards | low | The registered tool descriptions in `tools/__init__.py` for the two analyze tools do not mention `include_map`. The parameter itself carries the description "Leave false. ..." (`IncludeMap` `Field`), and README L268/L273 list it. `manifest.yaml` lists tool descriptions only, no parameters, so it needs no change. | `tools/__init__.py` L66-74, L106-112; `spatial_analysis_tools.py` `INCLUDE_MAP_DESCRIPTION` | Accept: the parameter description is what the model sees, and leaving the flag out of the tool description avoids prompting the model to set it |
| R5 | Standards | info | `simplify_for_display` logs the GEOS exception text, which can include a coordinate. This is server-side and ADR 0016 allows geometry in logs; no repository file is affected. | `map_contract.py` `simplify_for_display` | Accept |
| R6 | Standards | info | Checked and conforming: ADR 0015 `### Local changes` covers `message.tsx`, `ChatLayout.tsx` and the new map files (under `client/src/components/map/**`). `geo.py` logs only exception type names and fixed messages, and `/api/geo/map` errors are fixed text. Overlay and identify URLs are string constants. `MAP_TOOLS` matches between `geo.py` and `ShowOnMapButton.tsx`. Version 0.5.0 is consistent across `pyproject.toml`, `server.json`, `manifest.yaml` and `__init__.py`. | as listed | none |
| R7 | Spec | low | Vertex caps can diverge: the frontend `MAX_AOI_VERTICES = 2000` is a constant (`geojson.ts` L116), but the server reads `GEO_MAX_VERTICES` (default 2000). If the env var is lowered, "Use as AOI" accepts an outline that `/api/geo/screen` then rejects with its bounded 422 message. No data risk. | `geojson.ts` L116; `geo.py` L26, L69-72 | Deferred (user): follow-up to serve the limit from the server |
| R8 | Spec | low | A4 (corridor alternatives get the class breakdown and `farmland_classes` coverage) is recorded in `STATE_44.md` but not in the plan's Decision Log. | `STATE_44.md` L156; plan Decision Log ends at A3 | Fix (44.11.2): add A4 to the Decision Log |
| R9 | Spec | low | The `STATE_44.md` wave board still shows the gate rows for waves 5-9 as `pending`. The task reports I read record gates for waves 6 and 9; I did not confirm waves 5, 7 and 8 from the reports. | `STATE_44.md` L35-45, L153, L158 | Accept: close-out 44.12.1 runs every gate on the final head and updates the board |
| R10 | Spec | info | The M3 exit row asks for a `map` envelope on "every spatially enabled MCP tool" with polygon, soil, urban and corridor fixtures. D3 limits it to the two analyze tools, and 44.4.1 counts the `farmland_classes` layer as the soil fixture. | research s10 M3; D3 | Accept (decided D3); 44.12.1 records it in `MASTER_PLAN.md` |
| R11 | Spec | info | The M5 row lists a catalog endpoint and proxy. D5 replaced both with a fixed frontend catalog after the 44.1.2 probe passed. | research s10 M5; D5; 44.1.2 | Accept (decided D5) |
| R12 | Spec | low | The M4 exit row names POLY-01/POLY-02. The 44.8.1 and 44.10.1 trials used ad hoc prompts and do not reference those case ids. | `grep POLY-0 planning/evidence/44.*` empty | Fix (user): fix task 44.11.3 runs both cases |
| R13 | Spec | info | SSURGO identify shows symbol/mukey/survey but no farmland class or map unit name (SDA WMS `GetFeatureInfo` returns `mukey`/`musym` only). The popup says to run screening. | 44.1.2 evidence; 44.10.1 trial | Accept |
| R14 | Spec | info | SSURGO labels are small at native tile size (user decision: no stretching). | 44.10.1 trial sheet | Defer: app-drawn labels as a follow-up |
| R15 | Spec | info | Follow-ups outside Plan 44 scope: multiple AOIs per chat, drawing corridors on the map, app-drawn SSURGO labels, efficiency review (`planning/HANDOFF_EFFICIENCY_REVIEW.md`). | Goal & Scope deferrals; STATE_44 | Defer: list in `MASTER_PLAN.md` at close-out |
| R16 | Spec | medium | 44.10.1 is not closed: the user has not yet re-checked crisp native-size labels, popup placement near edges and corners, and popup theme on e760691. | trial sheet `## Result` empty | User re-check, then record the result |

No high-severity findings.

## Decisions (user, 2026-11-07)

- **Fix:** R1, R2, R3 and R8 in fix task 44.11.2 (docs only). R12 in fix task 44.11.3: "i do want to make sure those eval cases work". R16 by the user's 44.10.1 re-check.
- **Accepted as proposed:** R4, R5, R6, R9, R10, R11, R13.
- **Deferred to `MASTER_PLAN.md` follow-ups at close-out:** R7 (serve the AOI vertex limit from the server so the frontend uses the same value; user: "a follow up to serve limit from server would be good"), R14, R15.

Fix task specs are in `EXECUTION_PLAN_44.md` (44.11.2, 44.11.3).

## Code review (PR)

Review comments on the PR to `main` (branch `feature/agent-app-map2`). Each comment is numbered `C1`, `C2`, ... with source, summary, axis (Standards or Spec), severity (high blocks merge; medium fix before merge; low fix or accept; info no action), and proposed disposition.

| # | Source | Summary | Axis | Severity | Disposition |
| --- | --- | --- | --- | --- | --- |
| C1 | Copilot, `main.py:11-12` | `SRC_DIR` is only inserted when absent from `sys.path`. If the checkout's `src` is already on `sys.path` behind an installed package (e.g. an editable install), the guard skips the insert, leaving the installed copy first so stale code can be imported, defeating the entrypoint's purpose. | Standards | medium | Fix (44.13.1): remove any existing occurrence and insert at index 0 unconditionally when the directory exists |
