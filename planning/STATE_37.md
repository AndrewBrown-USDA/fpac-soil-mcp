# Orchestration 37 State

## Baseline

- **Repository:** `/Workspace/Users/andrew.g.brown@usda.gov/fpac-soil-mcp` (Databricks workspace clone; shell `sh`).
- **Branch (D11, revised):** `docs/eval-agent-workbench-tracks`, on top of `20592dc`; research notes and Plan 37 ship in one PR.
- **Known pre-existing changes:** map-note provenance edit committed and pushed on the research branch (`20592dc`).
- **Validation policy (D9):** ad hoc docs consistency script per wave; `git diff --stat` scope check; `make check` once in 37.4.1, or recorded as deferred to a local run if `uv` is unavailable.
- **Execution policy (D10):** single executor, serial waves; STOP for user review after 37.2.1; commits allowed on this non-`main` branch.
- **Baseline capture (37.1.1 attempt 2, 2026-10-24):**
  1. `git status -sb`; `git rev-list --left-right --count origin/main...HEAD` -> branch `docs/eval-agent-workbench-tracks`, HEAD `20592dc`, 0 behind / 7 ahead of `origin/main` (`21a1497`), in sync with its remote; untracked: the three Plan 37 artifacts only; index empty.
  2. `git grep -n -i -E 'MASTER_PLAN|Marimo|hackathon_demo|ipyleaflet|Phase 8|Phase 4|Criterion 2|perimeter'` and `git grep -c -i -E 'workbench|harness'` (frozen files excluded). Hits outside D8 scope, all **no change needed**: ADRs 0004/0006/0007/0010 (historical context or `polygon_area_perimeter`); `eval/prompt_test_cases.json`, `eval/eval_cases.v1.json` (category labels); `src/fpac_soil_mcp/constants.py` L114/L130/L146/L162 and `geometry.py`, `tests/test_corridor_scoring.py` (code); point-in-time planning docs (`PHASE_2_POLYGON_ANALYSIS.md`, `POST_PHASE_3_CONSISTENCY_REVIEW.md`, `RESEARCH_ARCGIS_TOOLBOX_CROSSWALK.md`, `RESEARCH_PUBLIC_APIS_AND_INTERPRETATIONS.md`, `RESEARCH_DATABRICKS_EVAL_INTEGRATION.md`, `RESEARCH_FEATURE_EVAL_HARNESS_DATABRICKS.md`, `RESEARCH_JS_HARNESS_AGENT_APP_INTEGRATION.md`, `REVIEW_27_FIXES.md`, `CAPTURE_CONTRACT_29.md`, `OFFICE_HOURS_QUESTIONS.md`, `TODO_PR34.md`); `README.md` L363-392 and `QUICKSTART.md` L151 ("local browser workbench"; consistent with D5); CI/dependabot (harness jobs). The only non-frozen file naming Marimo as the client is `SPATIAL_VISUALIZATION_STRATEGY.md` (in scope, 37.3.1). ESCALATE: none.
  3. Anchors: `AGENTS.md` L71 (Find Things `planning\`) and L160 (References); strategy doc `### 2.1 Prototype Architecture (Hackathon & Analyst Workbench)` L16 (Marimo diagram L20); app `AGENTS.md` `## References` L62; harness README `## Notes` L107 ("not a hosted or production deployment" L30); Databricks eval README `## Deferred (T2)` L121. `MASTER_PLAN.md` 457 lines; all 37.2.1 grep anchors present (Phase 4 L235, Phase 8 L373, Post-Hackathon L411, section 4 L424, section 5 L437, References L452).
  4. `grep -i -E 'perimeter|adjacen|criterion 2'` on `lesa.py`, `corridor_scoring.py`, `tools/*.py` -> no hits; only point constants exist in `constants.py`. Criterion 2 is not implemented.
  5. `docs/decisions/README.md`: ADRs 0001-0013 all Accepted, none superseded.
  6. `git ls-tree` over `git branch -r`: highest plan is `EXECUTION_PLAN_36`; 37 is free.
  7. Spot checks (tracks note): `AGENTS.md` L63-71, L129, L141; `STATE_35.md` L38-44 (live-check table empty); ADR 0012 L49 -> all match. Map-note cites drifted: `[^map-phase]` L243-254 is now L239-250, `[^map-open]` L256-264 is now L252-259. Spot checks (map note): `start_app.py` L147, L224; `start_server.py` L18-20; `agent.py` L93; `config.py` L17-19, L49-52 -> all match.
  8. `git diff 20592dc HEAD -- planning/RESEARCH_*.md` -> empty.
- **Plan facts verified for 37.2.1:** Phase 4 plans 17-27, 31, 32 by title; `SDAServiceUnavailableError` at `sda_client.py` L737.

## Wave board

| Wave | Task | Status |
|---|---|---|
| 1 | 37.1.1 | done |
| 2 | 37.2.1 | pending |
| 3 | 37.3.1 | pending |
| 3 | 37.3.2 | pending |
| 3 | 37.3.3 | pending |
| 4 | 37.4.1 | pending |

## Task reports

<!-- Append one concise report under each task heading. Include status, changed files/line ranges, exact validation commands and results, deviations, and dependent-task gotchas. -->

## 37.1.1

- **Attempt 1 (2026-10-24): ESCALATE after step 1.** The remote research branch had PR-review commits (`97296b6`, `b40f657`, `5bd80d6`) not in the recon baseline; the Git folder pulled them mid-recon and staged the Plan 37 artifacts. The notes changed in substance (AOI pre-dispatch, M3 = server `map` envelope, T2 on `/mcp`, WKT upload no longer confirmed, SDA maintenance handling delivered), contradicting D2, D6, and specs 37.2.1 / 37.3.2.
- **Resolution:** user chose to run Plan 37 on this branch (D11, revised; an interim choice to branch off `main` was withdrawn). Extras unstaged; map-note edit committed and pushed as `20592dc`. Plan revised: Recon Log revision 1, D2 and D6 revised, D11-D12 added, specs 37.1.1 step 8, 37.2.1 items 2/4/4a/5/8, 37.3.2, and D9 greps updated; prompt template points at D1-D12.
- **Next:** re-run from step 1 on this branch.
- **Attempt 2 (2026-10-24): done.** Baseline items 1-8 recorded above; no ESCALATE entries. Files: `STATE_37.md`, `planning/tasks/37.1.1.todo.md`; commit adds the three Plan 37 artifacts plus the todo. Deviations: none. Gotcha for 37.2.1: the tracks note's two map-note line cites have drifted (research text stays unchanged per 37.3.2; link to section headings, not line numbers).
