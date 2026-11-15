# STATE 51: Structured Site Assessment Interview and Confirmation

Resume point for orchestration 51. Plan: `planning/EXECUTION_PLAN_52.md`.
Worker prompt: `planning/PROMPT_TEMPLATE_52.md`.

## Baseline (recorded before wave 1)

Baseline tests were recorded on branch `feature/sa-checklist2` at `7e8f71f`.
The current branch advanced through docs-only commits `f709c21` and `151819c`;
the test baseline remains applicable because those commits changed only
documentation.

- [x] Root pytest: 1,019 passed, 45 deselected. The final fixture-only update
  after this run was app-scoped; root pytest excludes `apps/`.
- [x] Root Ruff check and format check passed.
- [x] Agent-app pytest: 196 passed.
- [x] Agent-app Ruff check and format check passed.
- [x] Frontend read-only Biome lint and client/server builds passed; 10
  existing lint warnings, no errors.
- [x] Frontend `npm ci` completed; npm audit reported 10 existing advisories
  (4 low, 6 moderate). No automated dependency changes.
- [ ] Databricks-authenticated integrated chat trial — not run; local auth is
  not configured.
- [ ] Dev-app trial — pending separate explicit push/redeployment approval.
- [!] `make app-check` previously failed to start on this Windows host with an
  Rtools path error; direct `uv`/Ruff commands are the fallback.

## Decisions

- Continue on current branch `feature/sa-checklist2` at `151819c`; preserve the
  committed root `AGENTS.md`/`README.md` changes and all existing
  `.worktrees\`.
- Use at most two concurrent workers in new isolated `51.*` worktrees.
- Keep project-wide G1 active and add PR-scoped goals G23-G30.
- Preserve ADR 0016; geometry may appear in chat/tool traces.
- Use summary-card Confirm as the sole user approval; agent-side gate requires
  a matching confirmed-summary history record. No second MCP Approve step.
- Use existing Playwright for frontend interactions; no new component-test
  dependency and no TypeScript-check gate.
- Use `get_site_assessment_question` and `record_site_assessment_answer` as
  the existing UI contracts. Confirm emits
  `type: site_assessment_confirmed_summary`, `confirmed: true`, and unchanged
  answer records under `answers`. CDL staleness compares active `aoi_ref` and
  geometry; an exact reattachment is equivalent, with no added generation
  token. Plan contract recorded in `752cbf7`.
- The user waived running Playwright; retain the fixture, but do not block
  local integration on browser availability. Plan amendment D11 records this.
- Parent review found that `project_farm_acres` and
  `county_average_farm_acres` independently score Criterion 7. Plan amendment
  D12 requires these inputs to match a confirmed Criterion 7 registry band
  before forwarding; task 52.3.1 remains in progress pending the worker fix.
- Parent review also confirmed the downstream evaluator rejects any combined
  Criterion 7 fact and farm-acre pair; D13 requires the gate to reject this
  combination even when the two representations agree.
- Integrated app tests found six existing AOI-context assertions that the
  server call boundary remains unwrapped without an AOI. D14 records that the
  confirmation gate wraps every request-scoped server and adds the test to
  task scope; the suite remains blocked pending this coupled fix.
- Planning files are tracked; commit them separately with
  `docs(planning):` after plan approval.
- No remote actions are authorized by this plan.

## Wave Board

| Wave | Task | Status | Commit | Notes |
|---|---|---|---|---|
| 1 | 52.1.1 Conservative missing-input scoring and ADR 0018 | done | `2899a61` / `062bc30`; follow-ups `aafb797` / `abc1f9f`, `38c544f` / `9f65159`; merges `1afeecb`, `f5cd0a7`, `ef99795` | Conservative assumptions, regression contracts, and formatting verified. |
| 1 | 52.1.2 Structured Site Assessment tool/history contract | done | `f76e146` / `4fe9fea`; follow-up `e251d92` / `b4a1ce0`; merges `c7e3e5d`, `7412853` | Structured tools and scoped app Ruff checks verified. |
| 1 gate | Foundation contract checks | done | | Root: 1,023 passed, 45 deselected; Ruff check/format passed. App: 206 passed; Ruff check/format passed on changed owned files. |
| 2 | 52.2.1 Interview trigger/CDL sequence and eval cases | done | `b569a95` / `fc46ec6` / `4d30ac3`; merge `b0cb2bd` | Soil-first/site-only sequencing, combined CDL guidance, and ordered/prohibited-tool replay contracts verified. |
| 2 | 52.2.2 Question/summary cards, Playwright fixture, stale-CDL guard | done | `0e570ca` / `ad26df0` / `9a8276d`; merge `28dd305` | Cards and stale-AOI guard integrated; lint/build pass; Playwright execution waived by user. |
| 2 gate | Interview flow and frontend checks | done | | Task 52.2.1 targeted tests pass; frontend Biome lint/build pass. Playwright waived by user. |
| 3 | 52.3.1 Confirm-only matching-history gate | done | `18fda4b` / `696fab2` / `31604bf` / `5ddc4a3` (on `feature/sa-checklist2`; reachable from `refactor/mcp2`); planning `db27d87`, `39f4eee` | D12/D13/D14 implemented and verified in this session; worker worktree was never created on this host. |
| 3 gate | Serial integrated local acceptance | done | `15dab08` | Root: 994 passed, 3 skipped, 43 deselected; root Ruff check/format passed. App: 254 passed; Ruff check/format clean on owned files (6 pre-existing E402/format findings in `start_server.py`, `scripts/` untouched). Frontend: Biome 10 existing warnings, no errors; build passed after `npm ci`. |
| 4 | Conditional dev-app trial | blocked | | Requires separate user approval to push/redeploy. |

## Worker Worktrees

Preserve all pre-existing worktrees from orchestration 50. Add new `51.*`
worktrees only when a wave starts; record their path, branch, and disposition
here.

| Task | Path | Branch | Created (local) | Status |
|---|---|---|---|---|
| 52.1.1 | `.worktrees\52.1.1` | `feature/sa-checklist2-52.1.1-worker` | 2026-11-13 17:08:16 -08:00 | complete; retain |
| 52.1.2 | `.worktrees\52.1.2` | `feature/sa-checklist2-52.1.2-worker` | 2026-11-13 17:08:16 -08:00 | complete; retain |
| 52.2.1 | `.worktrees\52.2.1` | `feature/sa-checklist2-52.2.1-worker` | 2026-11-13 17:33:03 -08:00 | complete; retain |
| 52.2.2 | `.worktrees\52.2.2` | `feature/sa-checklist2-52.2.2-worker` | 2026-11-13 17:33:03 -08:00 | complete; retain |
| 52.3.1 | `.worktrees\52.3.1` (not present on Linux host) | `feature/sa-checklist2-52.3.1-worker` (not present; work on `feature/sa-checklist2`) | 2026-11-13 18:56:53 -08:00 | complete; worktree missing, nothing to retain |

## Task Reports

<!-- Append one concise report per completed task; keep each to 15 lines max. -->

### 52.1.1 — Score missing Site Assessment inputs conservatively
- Status: complete; planning commits `2899a61`, `aafb797`, `38c544f`; code/style commits `062bc30`, `abc1f9f`, `9f65159`; integrated merges `1afeecb`, `f5cd0a7`, `ef99795`.
- Added registry-maximum assumptions with separate provenance and upper bound; actual awards remain zero for missing inputs and incomplete results remain undetermined. Added and indexed ADR 0018.
- Root targeted scoring/contracts — 96 passed; amended regression contracts and prompts — 171 passed; app prompt test — 33 passed with one existing config warning.
- Final `uv run --group dev pytest -q` — 1,023 passed, 45 deselected, 220 warnings.
- `uv run ruff check .` and `uv run ruff format --check .` — passed; 6,031 files already formatted.
- Plan scope was amended in `6919b42` after the full suite exposed directly coupled stale assertions; all were fixed within the amended scope. No remote actions.

### 52.1.2 — Add the structured Site Assessment tool contract
- Status: complete; planning commits `f76e146`, `e251d92`; code/style commits `4fe9fea`, `b4a1ce0`; integrated merges `c7e3e5d`, `7412853`.
- Added resource-backed question and answer function tools; agent construction enables them only with validated criteria context.
- Added tests for resource-derived choices/citations/points, provenance, unknown/skipped records, supplied-point rejection, and history pass-through.
- `uv run --frozen --python 3.11 pytest tests\test_site_assessment_tools.py tests\test_agent_construction.py tests\test_agent_mcp_wiring.py tests\test_history_normalization.py -q` — 51 passed, 1 existing `asyncio_mode` warning.
- Final app `uv run --frozen --python 3.11 pytest tests -q` — 206 passed, 122 existing warnings. Ruff check and format passed on the seven changed owned Python files.
- Whole-app Ruff also identified 19 findings in other app files and formatting issues in `scripts/app_diagnostics.py` and `scripts/start_app.py`; left untouched. Shared `history.py` was not changed. Answer records use `type: site_assessment_answer`; outputs are JSON strings in function-call history.

### 52.2.1 — Sequence the interview and CDL evaluation
- Status: complete; planning commits `b569a95`, `fc46ec6`; code commit `4d30ac3`; integrated merge `b0cb2bd`.
- Updated root/app prompts and tests for soil-first screening, site-only Start/Skip, completion/confirmation ordering, one combined CDL context call, and no histogram follow-up.
- Added replay cases `SA-MA-05/06`; eval validation and scorers now check ordered tool subsequences and prohibited tools.
- Root targeted prompt/dataset/scorer tests — 75 passed, 1 skipped; contract/eval tests — 61 passed, 1 skipped, 2 deselected; app prompt test — 33 passed.
- No deviations or remote actions.

### 52.2.2 — Render interview cards and reject stale CDL results
- Status: complete; planning commits `0e570ca`, `9a8276d`; code commit `ad26df0`; integrated merge `28dd305`.
- Added resource-backed question and confirmation cards with structured answer/confirm records, explicit unknown/skipped answers, assumptions, and Edit/Confirm actions.
- CDL map storage now rejects absent or mismatched active AOIs using the captured reference and geometry. Added an isolated Playwright fixture/test without production routes or new dependencies.
- User waived Playwright execution. Read-only Biome lint passed with 10 existing warnings; frontend production build passed for client and server (database migration skipped because no database config is present).
- No remote actions.

## Final Acceptance

- [x] Root tests and Ruff checks pass serially; 1,023 passed, 45 deselected; Ruff check/format passed.
- [x] Agent-app tests and Ruff checks pass on changed owned files; 206 passed; scoped Ruff check/format passed.
- [!] Playwright execution waived by explicit user instruction; keep the
  fixture/test. Read-only Biome lint passed with 10 existing warnings and the
  frontend production build passed.
- [ ] Review final diff and ensure no user-owned edits or remote actions were
  included.
- [ ] Dev-app trial and review-thread replies remain blocked until separately
  authorized.

### 52.3.1 — Enforce the matching confirmed-summary gate
- Status: complete; planning commits `db27d87`, `39f4eee`; code commits `18fda4b`, `696fab2`, `31604bf`, `5ddc4a3` on `feature/sa-checklist2` (reachable from `refactor/mcp2`).
- Added `agent_server/site_assessment_gate.py`; gate wraps every request-scoped MCP server for invoke and stream handlers, with or without AOI. Rejects missing/mismatched confirmation and dual Criterion 7 representations before forwarding.
- Targeted (`test_site_assessment_gate.py`, `test_agent_mcp_wiring.py`, `test_aoi_context.py`) — 125 passed. Full app suite — 254 passed.
- No worker worktree or worker micro-TODO exists for this task on the Linux host; verified by orchestrator from committed diff.
- No remote actions.

### Integrated gate (wave 3) — 2026-11-15
- Root eval test `test_prompt_dataset_schema_and_completeness` failed on CDL tools added to `manifest.yaml`. Fixed in `15dab08`: CDL-01/CDL-02 prompt cases added to `eval/eval_cases.v1.json`; corpus size (42) and ID set updated in `eval/common/`; tool count 12 in `eval/pi/test_agent_eval.py`.
- Root `pytest -m "not live_network"` — 994 passed, 3 skipped, 43 deselected. Root Ruff check/format passed.

## Local stand-in for the dev-app trial (2026-11-15)

Plan and log: `planning/TODO_LOCAL_DEV_TRIAL.md`. No push, deploy, or remote action.

**Command:** `make trial-local` (opt-in; not in `make check`). It starts its own MCP
server on a free port, runs the scenario, and stops the server. Use
`cd apps/agent-fpac-soil-openai-sdk && uv run python scripts/trial_local.py --mcp-url http://127.0.0.1:PORT/mcp`
for an already running server. Result: 19 checks passed.

**What it proves against the real local `/mcp` (Streamable HTTP):**
1. Question and choices come from the criteria tool, built from the served `fppa://site-assessment-criteria` resource.
2. Answer records keep `type`, comment, evidence, provenance, and derived points.
3. `calculate_preliminary_lesa` is refused (no MCP call made) with no confirmation, no summary, mismatched facts, a missing answer-set member, and a Criterion 7 fact plus farm acres.
4. A matching confirmed summary reaches LESA. Skipped, unknown, and unasked criteria are conservative maximums labelled `assumed (no evidence)`.
5. Result is undetermined: `total_lesa_score` null, `threshold_status` `not_evaluated`, separate `conservative_total_lesa_upper_bound`, preliminary notice present.
6. The script makes no claim about AOI geometry in traces (ADR 0016).

**Defect found and fixed (production code):** the served resource carried null `min`/`max`,
default `min_inclusive`/`max_inclusive`, and null `point_range`/`representative_*` on
every band, so the app validator rejected it and disabled the interview. App tests passed
only because their fixture reads the raw registry file. `fppa_resources.py` now serves each
band with `exclude_unset=True`; `tests/test_site_assessment_resource.py` covers it. This
likely affects the dev apps until redeployed.

**Not reproducible locally:**
- A full model-generated 12-criterion interview through Confirm → LESA has not been demonstrated in the browser. Live UI proved soil screening and one resource-backed Criterion 1 answer turn; the answer tool now canonicalizes the band ID. `make trial-local` independently proves the LESA refusal and matching-confirmation paths against a local MCP server.
- Model-generated free-form numeric answers were not demonstrated; the real UI answer came from selecting a resource-defined band. The app answer tool also supports numeric values and has offline tests.
- Frontend Playwright now passes 3 Site Assessment card tests; the fourth AOI-map fixture test is skipped because its expected “Attach AOI” control is absent from that isolated fixture. This is unrelated to answer/confirmation behavior.
- App checks: `make app-check` passed (262 tests); frontend `test:local-auth` passed; frontend build passed. Biome lint produced existing warnings and no errors.
- Opt-in `make trial-local` completed 19/19 checks, including live USDA SDA polygon screening and LESA success. Result is preliminary and undetermined when evidence is absent; the conservative upper bound is separately labelled. Do not treat this as an official determination or form.

**Local-vs-dev gaps that could change results:**
- `FPAC_LOCAL_DEV=1` is an explicit loopback-only synthetic session and local provider route. Configure `AGENT_MODEL` with the exact model ID reported by `http://127.0.0.1:8090/v1/models`, `LOCAL_LLM_BASE_URL=http://127.0.0.1:8090/v1`, and `FPAC_MCP_URL=http://127.0.0.1:<port>/mcp`; local mode fails closed rather than resolving deployed defaults.
- Live browser answer-card submits a registry band ID and now retains evidence, comment, provenance, verification status, source provenance, justification, and registry-derived points. The corresponding tool accepts either a numeric answer or a registry band identifier and emits canonical band IDs.
- Dev deployment code and registry may differ from this checkout until the branch is pushed; no push/deploy was performed.
