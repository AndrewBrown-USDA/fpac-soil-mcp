# EXECUTION PLAN 37: Fold Delivery-Track Research into the Master Plan

## Goal & Scope

**Goal:** Incorporate the research notes on `docs/eval-agent-workbench-tracks` (`planning/RESEARCH_EVAL_AGENT_WORKBENCH_TRACKS.md`, `planning/RESEARCH_MAP_WIDGET_AGENT_APP.md`, as of `20592dc`) into `planning/MASTER_PLAN.md` and the directly affected planning, onboarding, and evaluation resources. Changes are surgical and documentation-only; existing useful content is preserved; unresolved decisions are recorded explicitly.

**In scope:**

- `planning/MASTER_PLAN.md`: Phase 4 status correction, Phase 8 client re-scope, a new delivery-tracks section (D Deployment, E Evaluation, A Agent App, W MCP Workbench), decision notes, and references.
- `AGENTS.md` (Find Things and References entries for the master plan).
- `planning/SPATIAL_VISUALIZATION_STRATEGY.md` section 2.1 (supersession note only).
- Status lines on both research notes (the 3-line map-note provenance edit is already committed on the research branch as `20592dc`).
- One-line pointers in `apps/agent-fpac-soil-openai-sdk/AGENTS.md`, `eval/fpac_soil_mcp_harness/README.md`, and `eval/databricks/README.md`.
- `planning/EXECUTION_PLAN_37.md`, `planning/PROMPT_TEMPLATE_37.md`, `planning/STATE_37.md`, and `planning/tasks/37.*.todo.md`.

**Out of scope:**

- Any production, test, CI, or app code change (including Criterion 2 perimeter adjacency, which is the next server plan, D3).
- New or superseded ADRs (D7).
- Resolving map-note section 11 decisions 1-5 (D6); they are recorded as open in Track A.
- Relocating or renaming the workbench folder (D5).
- A committed docs checker or Makefile target (D9; recorded as a backlog item).
- `README.md`, `QUICKSTART.md`, `manifest.yaml`, `server.json` (MCP surface unchanged).
- Frozen history: `EXECUTION_PLAN_1..36`, `PROMPT_TEMPLATE_*`, `STATE_1..36`, `planning/tasks/` files of earlier plans, `evolution-digest.md`, `interval-ledger.json`.
- The untracked `eval/fpac_soil_mcp_harness/TODO.md` (issue #36 plan; leave untracked and unedited).
- Pushing the branch or opening a PR.

**Verbatim constraints from the request:**

- "Keep changes surgical and documentation-focused. Do not modify production code unless the research proves it is necessary and explicitly approved."
- "Preserve existing useful content, avoid speculative commitments, and record unresolved decisions explicitly."
- "Clearly separate established facts, proposed decisions, assumptions, and open questions."
- "Do not create planning artifacts outside the repository's established `planning/` and `docs/decisions/` conventions."
- "committing is acceptable as long as you are on a branch" (2026-10-24).

## Reconnaissance Log

Captured 2026-10-24 in the Databricks workspace clone `/Workspace/Users/andrew.g.brown@usda.gov/fpac-soil-mcp` (shell: `sh`, not PowerShell).

- **Revision 1 (2026-10-24, after the 37.1.1 escalation):** the remote research branch had PR-review commits not in the first recon (`97296b6`, merge `b40f657`, `5bd80d6`). They changed the map AOI pattern (wrapper tools -> explicit backend pre-dispatch, blocked on an M1 redaction spike R6), renumbered map phases (M3 = required server `map` envelope, before M4 results; M5 overlays; M6 formats), retargeted T2 at deployed `/mcp`, removed issue #36 WKT upload as a confirmed workbench item, and recorded SDA maintenance-page handling as delivered. D2, D6, D11, and the 37.1.1 / 37.2.1 / 37.3.2 specs were revised to match. The map-note provenance edit was committed and pushed on the research branch (`20592dc`).
- Research branch `docs/eval-agent-workbench-tracks` at `20592dc` is 7 ahead of `origin/main` (`21a1497`), 0 behind; it touches only the two research notes. Plan 37 runs on this same branch, on top of `20592dc` (D11, revised).
- Working tree at revision time: Plan 37 artifacts and `eval/fpac_soil_mcp_harness/TODO.md` untracked. A Git folder pull had staged all four; they were unstaged. The Git folder can change HEAD or the index between commands.
- Highest plan number on any remote branch: 36. This plan is 37.
- `planning/MASTER_PLAN.md` is 457 lines; sections: Summary, 1 Problem and Goals, 2 System Architecture, 3 Phased Delivery Roadmap (Phases 0-8 + Post-Hackathon), 4 Workstream Ownership, 5 Definition of Done, References. It does not mention evaluation tiers, the agent app, the workbench, or deployment as delivery streams.
- Criterion 2 (perimeter agricultural adjacency) is not implemented; only point constants exist (`src/fpac_soil_mcp/constants.py` L114, L146). Phase 4 exit criterion "Objective SA calculations (perimeter adjacency, farm size ratio) reproduce deterministically" is unmet.
- `planning/STATE_35.md` live-check table is empty (Track D/E evidence gap).
- No markdown lint exists in `Makefile` or `.github/workflows/`; `make check` covers ruff + pytest only.
- ADRs 0001-0013 are Accepted; none contradicts the branch content. ADR 0012 (agent app as separate MCP client) and ADR 0013 (PyPI default index) bound Track A.
- The workspace search index is stale (it does not return `MASTER_PLAN.md`), and one shell submission failed. Task 37.1.1 must redo all greps directly with the shell.

## Decision Log

1. **D1, 2026-10-24, Roadmap structure:** keep Phases 0-8 as the server roadmap; add parallel delivery tracks D (Deployment), E (Evaluation), A (Agent App), W (MCP Workbench). Each phase, and each track backlog item, remains one plan-wave.
2. **D2, 2026-10-24 (revised), Phase 8 client:** the agent-app map widget (Track A, map phases M0-M7) is the Phase 8 client. Phase 8 keeps deliverable 1, the visualization envelope / server `map` block, which is map M3 and must precede Track A M4 result rendering. The Marimo + ipyleaflet demo is superseded for now and recorded, not deleted. A workbench map tab is an optional Track W backlog item and is not a Phase 8 dependency.
3. **D3, 2026-10-24, Phase 4 status:** mark Phase 4 "(Partially Complete)". Criterion 2 perimeter agricultural adjacency stays an open Phase 4 item and is the next server plan (separate from Plan 37).
4. **D4, 2026-10-24, Link, don't restate:** the master plan records goal, status, delivered work as plan/ADR/PR references, one-line backlog items, and measurable exit criteria. Task counts, test counts, run IDs, and file lists stay in `EXECUTION_PLAN_N`, `STATE_N`, and ADRs.
5. **D5, 2026-10-24, Workbench name:** "MCP Workbench"; audience developers and admins; not an authorization boundary; stays in `eval/fpac_soil_mcp_harness/`. "Relocate if hosted" is an open Track W decision.
6. **D6, 2026-10-24 (revised), Map scope:** Track A commits structure only: M0 (vendor and pin the chat UI) is the first standalone orchestration, M1 spikes (R2, R3, R4, R6) the second, M2-M7 scoped after M1 findings. AOI integration uses explicit backend pre-dispatch and stays blocked until R6 proves pre-trace redaction and history exclusion. Map-note section 11 decisions 1-5 stay open in Track A; decision 6 (plan number) is resolved by this plan.
7. **D7, 2026-10-24, ADRs:** no new ADR in Plan 37 and none superseded. "ADR on the vendored frontend" is an M0 exit item; "ADR on AOI handoff" is an M1 exit item.
8. **D8, 2026-10-24, File scope:** as listed under In scope. No change to `README.md`, `manifest.yaml`, `server.json`, ADRs, frozen plans, or the harness `TODO.md`.
9. **D9, 2026-10-24, Validation:** per wave, an ad hoc (uncommitted) docs consistency script; a `git diff --stat` scope check; `make check` once at the end (recorded as deferred to a local run if `uv` is unavailable). A committed checker is a backlog item.
10. **D10, 2026-10-24, Execution:** serial W1 -> W2 -> stop for user review -> W3 -> W4. Escalate if any W1 fact check contradicts D1-D9 or D11-D12. Commits are allowed while on a non-`main` branch; conventional `docs(...)` scopes; no wave numbers in commit messages.
11. **D11, 2026-10-24 (revised), Branch:** Plan 37 runs on `docs/eval-agent-workbench-tracks`, on top of `20592dc`; the research notes and the Plan 37 changes ship in the same PR. In `git diff origin/main...HEAD` scope checks, the two research notes' baseline commits (`a0b95ac`..`20592dc`) are expected.
12. **D12, 2026-10-24, Track content follows the revised notes:** Track E backlog = T1 model client to model gateway and T2 against deployed `/mcp`; an agent-app eval against `/invocations` is a Track A item and is not called T2. Track W lists WKT/GeoJSON upload as an open decision, not a backlog item. Phase 7 records SDA maintenance-page handling as delivered.

## Wave & Dependency Table

| Wave | Task | Title | Files in scope | Depends on |
|---|---|---|---|---|
| 1 | 37.1.1 | Recon freeze and baseline | `planning/STATE_37.md`, `planning/tasks/37.1.1.todo.md` | none |
| 2 | 37.2.1 | Update the master plan | `planning/MASTER_PLAN.md` | 37.1.1 |
| 3 | 37.3.1 | Align onboarding and spatial strategy | `AGENTS.md`, `planning/SPATIAL_VISUALIZATION_STRATEGY.md` | 37.2.1 + user review |
| 3 | 37.3.2 | Mark research notes as folded in | `planning/RESEARCH_EVAL_AGENT_WORKBENCH_TRACKS.md`, `planning/RESEARCH_MAP_WIDGET_AGENT_APP.md` | 37.2.1 + user review |
| 3 | 37.3.3 | Add subproject pointer lines | `apps/agent-fpac-soil-openai-sdk/AGENTS.md`, `eval/fpac_soil_mcp_harness/README.md`, `eval/databricks/README.md` | 37.2.1 + user review |
| 4 | 37.4.1 | Two-axis review, validation, and report | `planning/STATE_37.md` (fixes to any W2/W3 file only when a check fails) | 37.3.1, 37.3.2, 37.3.3 |

Wave 3 tasks have pairwise-disjoint files but run serially (single executor, D10). Every task also writes its own `planning/tasks/37.x.y.todo.md` and appends to `planning/STATE_37.md`.

## Hazards

- **Drift from frozen history.** `EXECUTION_PLAN_33.md` is frozen (Plan 34 D5). Never edit earlier plans to make them agree; the master plan links to them instead.
- **Stale anchors.** Line numbers cited in the research notes (for example `AGENTS.md` L71, L160; `constants.py` L114, L146) must be re-verified in 37.1.1 before use.
- **Speculative commitment.** Track backlogs must not promise dates, owners not named in the repo, or designs decided only by spikes (map R2, R3, R4).
- **Authority language.** Any new text that mentions screening outcomes must keep the ADR 0003 boundary and must not duplicate `constants.py` notices; link to them.
- **Long-file edits.** `MASTER_PLAN.md` is 457 lines; edit by section heading anchors, not whole-file rewrites.
- **Git folder side effects.** The workspace Git folder can pull, switch HEAD, or stage files between commands. Run `git status -sb` and `git diff --cached --name-only` immediately before every commit; never commit `eval/fpac_soil_mcp_harness/TODO.md`.

## Task Specifications

### 37.1.1 - Recon freeze and baseline

**Repository:** `/Workspace/Users/andrew.g.brown@usda.gov/fpac-soil-mcp`

**Files in scope**

- Must edit: `planning/STATE_37.md` (Baseline section and 37.1.1 report)
- Can create: `planning/tasks/37.1.1.todo.md`
- Temp/scratch: shell output only; no files

**Depends on:** none.

**Specification:** Re-establish every fact Plan 37 relies on, directly from the repository, and record it in `STATE_37.md`:

1. Branch name, `HEAD` SHA, ahead/behind counts vs `origin/main`, working-tree status.
2. Repo-wide grep (excluding frozen plan files) for `MASTER_PLAN`, `Marimo`, `hackathon_demo`, `ipyleaflet`, `workbench`, `harness`, `Phase 8`, `Phase 4`, `Criterion 2`, `perimeter`. List every hit outside the D8 scope and classify it as "no change needed" or "ESCALATE".
3. Confirm the current text at `AGENTS.md` master-plan lines, `SPATIAL_VISUALIZATION_STRATEGY.md` section 2.1, and the three pointer targets; record the exact anchor lines.
4. Confirm Criterion 2 absence (`constants.py` and `src/fpac_soil_mcp/lesa.py`, `tools/`).
5. Confirm ADR statuses in `docs/decisions/README.md`.
6. Confirm the highest `EXECUTION_PLAN_N` across `git branch -r`.
7. Spot-check five line citations in each research note.
8. Confirm both research notes on the branch match `20592dc` (`git diff 20592dc HEAD -- planning/RESEARCH_*.md` is empty), then commit only the three Plan 37 artifacts and the task todo (`docs(planning): plan master plan update for delivery tracks`).

**Constraints:** No edits to any file except `STATE_37.md` and the task todo; the commit in step 8 contains only the Plan 37 artifacts and `planning/tasks/37.1.1.todo.md`.

**Grep anchors:** `## 3. Phased Delivery Roadmap`, `### Phase 4`, `### Phase 8`, `planning\MASTER_PLAN.md`, `### 2.1` (strategy doc).

**Reference implementations:** `planning/STATE_36.md` task 36.1.4 (baseline capture style).

**Acceptance:** `STATE_37.md` Baseline section lists items 1-7 with commands and results; every out-of-scope hit is classified; no ESCALATE entries, or the run stops and reports them; `git show --stat HEAD` lists only the allowed files.

**Escalate when:** any fact contradicts D1-D12 (for example Criterion 2 is implemented, a Plan 37 already exists on another branch, a non-D8 file states Marimo as the planned client, or the research notes on the branch differ from `20592dc`).

### 37.2.1 - Update the master plan

**Repository:** `/Workspace/Users/andrew.g.brown@usda.gov/fpac-soil-mcp`

**Files in scope**

- Must edit: `planning/MASTER_PLAN.md`
- Can create: `planning/tasks/37.2.1.todo.md`

**Depends on:** 37.1.1.

**Specification:** Edit by section, preserving all existing content that remains true:

1. **Summary:** one added sentence that the roadmap is server Phases 0-8 plus parallel delivery tracks D, E, A, W (D1).
2. **Section 2 System Architecture:** a short "Delivery surfaces" paragraph naming the MCP server (`/mcp`), the Databricks agent app (ADR 0012; model through model gateway per its amendment), the MCP Workbench (D5 wording, not an authorization boundary), and the evaluation tiers T0/T1 (T2 against deployed `/mcp` planned). Link, don't restate (D4).
3. **Phase 4:** heading status "(Partially Complete)"; delivered work as plan references (Plans 17-27, 31, 32; verify in 37.1.1); open item "Criterion 2 perimeter agricultural adjacency (next server plan; data source decision pending)" (D3). Exit criteria unchanged.
4. **Phase 8:** keep deliverable 1 (envelope / server `map` block = map M3, required before Track A M4); replace the Marimo client deliverable with a link to Track A (D2); add one line "Marimo + ipyleaflet demo: superseded for now by the agent-app map (D2, 2026-10-24); not built"; adjust exit criteria so the client criterion points at the Track A M2 and M4 exit criteria.
4a. **Phase 7:** one line recording SDA maintenance-page handling as delivered (`SDAServiceUnavailableError`), as a code reference only (D12, D4).
5. **New section "Delivery Tracks"** after the Post-Hackathon subsection (renumber nothing else). One subsection per track with exactly these fields: Goal; Status; Delivered (plan/ADR/PR refs only); Backlog (one line each); Exit criteria (measurable); Open decisions; Source (link to the research note section).
   - **Track D Deployment:** from `RESEARCH_EVAL_AGENT_WORKBENCH_TRACKS.md`; include the `STATE_35.md` live-check gap as a backlog item.
   - **Track E Evaluation:** T0, T1 delivered; backlog T1 model client to model gateway, T2 against deployed `/mcp`, committed docs checker (D9, D12).
   - **Track A Agent App:** delivered refs; backlog M0 (first standalone orchestration, exit item "ADR on vendored frontend"), M1 spikes (R2, R3, R4, R6; exit item "ADR on AOI handoff"), M2-M7 "scoped after M1", with M3 tracked in Phase 8 (D2, D6); separate agent-app eval against `/invocations` (D12); constraint: AOI integration blocked until R6 passes; open decisions = map note section 11 items 1-5 (D6).
   - **Track W MCP Workbench:** delivered Plan 36; backlog includes optional map tab (D2) and hosted deployment; open decisions "relocate if hosted" (D5) and "WKT/GeoJSON upload as shared code" (D12).
6. **Section 4 Workstream Ownership:** add rows for the four tracks only if owners are stated in the repo; otherwise add "Owner: not yet assigned" (no invented owners).
7. **Section 5 Definition of Done:** add one bullet that track work also meets its track exit criteria; no other change.
8. **Decision notes:** a short "Planning decisions (2026-10-24)" list with D1-D7 and D12 one-liners, each linking to this plan.
9. **References:** add both research notes and `EXECUTION_PLAN_37.md`.
10. Separate facts from proposals: every track Status line states only what shipped; every Backlog/Open line is phrased as proposed or open.

**Constraints:** No restated test counts, run IDs, or file lists (D4). No dates or owners not in the repo. Do not duplicate `constants.py` regulatory text; link to ADR 0003. Do not edit any other file.

**Grep anchors:** `## Summary`, `## 2. System Architecture`, `### Key Principles`, `### Phase 4:`, `### Phase 8:`, `### Post-Hackathon`, `## 4. Workstream Ownership`, `## 5. Definition of Done`, `## References`.

**Reference implementations:** existing Phase 2 and Phase 3 subsections (status-in-heading style, exit-criteria lists).

**Acceptance:**

- `grep -n 'Phase 4: .*(Partially Complete)' planning/MASTER_PLAN.md` returns one line.
- `grep -niE 'marimo' planning/MASTER_PLAN.md` returns only the superseded line.
- `grep -cE '^### Track (D|E|A|W)' planning/MASTER_PLAN.md` returns 4.
- Each track has the seven fields (grep for `**Exit criteria:**` count = 4).
- D9 docs consistency script passes on the file.
- `git diff --stat` lists only `planning/MASTER_PLAN.md` plus Plan 37 artifacts.

**Gate:** after this task, STOP and present the diff summary and check output to the user (D10). Commit after approval: `docs(planning): add delivery tracks to master plan`.

### 37.3.1 - Align onboarding and spatial strategy

**Files in scope:** `AGENTS.md`, `planning/SPATIAL_VISUALIZATION_STRATEGY.md`; can create `planning/tasks/37.3.1.todo.md`.

**Depends on:** 37.2.1 and user approval.

**Specification:** In `AGENTS.md`, update the two master-plan descriptions (Find Things `planning\` line and References line) to "product mission, target architecture, governance, server roadmap, and delivery tracks". In the strategy doc section 2.1, add a two-sentence note: the Marimo prototype is superseded for now by the agent-app map (master plan Phase 8 / Track A; Plan 37 D2); sections 3-6 remain the contract the agent-app map follows. No other changes.

**Constraints:** Keep the Windows path style already used in `AGENTS.md`. Do not edit strategy sections 3-6.

**Acceptance:** `git diff --numstat` shows at most 4 changed lines in `AGENTS.md` and at most 4 added lines in the strategy doc; links resolve (D9 script).

### 37.3.2 - Mark research notes as folded in

**Files in scope:** `planning/RESEARCH_EVAL_AGENT_WORKBENCH_TRACKS.md`, `planning/RESEARCH_MAP_WIDGET_AGENT_APP.md`; can create `planning/tasks/37.3.2.todo.md`.

**Depends on:** 37.2.1 and user approval.

**Specification:** Add one status line under each title: "Status: folded into `MASTER_PLAN.md` by Plan 37 (2026-10-24). Answered questions: see `EXECUTION_PLAN_37.md` D1-D7 and D12; remaining open items are listed in the master plan tracks." In the map note section 11, append "(resolved: Plan 37)" to item 6 and "(open: Track A)" to items 1-5. In the tracks note section 5, annotate the questions: 1 -> D5, 2 -> D2 and D6, 3 -> D1, 4 -> D3, 5 -> D4. Research text is otherwise unchanged.

**Acceptance:** each file gains a status line; `git diff` shows no removed research sentences; D9 script passes.

### 37.3.3 - Add subproject pointer lines

**Files in scope:** `apps/agent-fpac-soil-openai-sdk/AGENTS.md`, `eval/fpac_soil_mcp_harness/README.md`, `eval/databricks/README.md`; can create `planning/tasks/37.3.3.todo.md`.

**Depends on:** 37.2.1 and user approval.

**Specification:** One line each, placed in the existing references or overview area: the app points to master plan Track A (and the map note); the workbench README names it the "MCP Workbench" and points to Track W, keeping the existing "not an authorization boundary" statement; the Databricks eval README points to Track E (T2 backlog).

**Constraints:** Exactly one added line per file (two if a blank separator is required); no other edits.

**Acceptance:** `git diff --numstat` shows at most 2 additions and 0 deletions per file; relative links resolve.

### 37.4.1 - Two-axis review, validation, and report

**Files in scope:** `planning/STATE_37.md`; fixes to W2/W3 files only when a check fails, limited to the failing lines; can create `planning/tasks/37.4.1.todo.md`.

**Depends on:** 37.3.1, 37.3.2, 37.3.3.

**Specification:**

1. Spec axis: every In-scope item and D1-D10 traces to a changed line; no Out-of-scope file changed.
2. Standards axis: ADR 0003, 0012, 0013 consistency; no duplicated regulatory text; no restated counts (D4); facts vs proposals separated; exit criteria measurable.
3. Duplication/contradiction sweep: grep for statements about Phase 4 status, Phase 8 client, workbench name, and track names across all non-frozen docs.
4. Run the D9 docs consistency script over all changed files; `git diff --stat origin/main...HEAD` scope check; `make check` (or record "deferred to local run" with the failure reason).
5. Record results in `STATE_37.md`; commit `docs(planning): align onboarding and research notes with master plan`.

**Acceptance:** `STATE_37.md` contains the review findings (or "none"), script output, scope check, `make check` result, and remaining risks; working tree clean except the untracked harness `TODO.md`.

## Docs Consistency Script (D9)

Run ad hoc from the repo root; do not commit. Checks, for each changed Markdown file:

1. Relative links resolve to existing paths; `#anchor` fragments match a heading slug in the target.
2. Footnote references `[^id]` and definitions `[^id]:` match one to one.
3. Every `Plan N` / `EXECUTION_PLAN_N` and `ADR NNNN` reference resolves to an existing file.
4. Stale-claim greps across non-frozen docs: no `Phase 4: .*(Complete)` without "Partially"; Marimo appears only as superseded; no "AOI registry" or "M6 = server `map` block" in `MASTER_PLAN.md`; `EXECUTION_PLAN_37.md` contains D1-D12.
