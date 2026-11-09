# Handoff: wrap up Plan 44 (Phase 8 M3-M5)

Paste the prompt below into a new agent session. Written 2026-11-07.

---

You are finishing Plan 44 in `/Workspace/Users/andrew.g.brown@usda.gov/fpac-soil-mcp`, branch `feature/agent-app-map2`. All build tasks are done; what remains is closing the deployed trial (44.10.1), the two-axis code review (44.11.1, plus any fix tasks), and close-out (44.12.1). Work in one session, one commit per task, and ask the user before every push, merge or production deploy.

## Read first

- Root `AGENTS.md` and `apps/agent-fpac-soil-openai-sdk/AGENTS.md`.
- `planning/EXECUTION_PLAN_44.md`: Goal & Scope, Decision Log D1-D9 and A1-A4, and the task specs for 44.10.1, 44.11.1 and 44.12.1 (bottom of the file).
- `planning/STATE_44.md` (wave board, open items) and `planning/evidence/44.10.1-trial.md` (trial steps, traces, fix notes).
- ADRs 0003, 0010-0017 (0017 is the map result contract, still `Proposed`).

## Step 0: confirm the repo state (do this first)

The previous session lost compute while reverting the SSURGO label change, so the last commit and push may not have happened.

1. `git status -s`, `git log --oneline -6`, `git log --oneline origin/feature/agent-app-map2..HEAD`.
2. Expected end state:
   - `apps/agent-fpac-soil-openai-sdk/frontend/client/src/components/map/overlays.ts` draws every overlay at native size: no `tileSize` field on `Overlay`, SSURGO `WIDTH=256&HEIGHT=256`, `addSource` with `tileSize: 256` and `minzoom: overlay.minzoom`, and a comment above `SSURGO_WMS_TILES` saying not to stretch tiles. `git diff c79c639 -- <that file>` should show only that comment (the file was edited in the workspace to this state).
   - Commit `revert(agent-app): draw SSURGO tiles at native size`, and a trial-sheet note in `planning/evidence/44.10.1-trial.md` saying the user wants no stretching (1.33x, 2x and an uncommitted 1.5x all blurred the labels), labels are fixed size in SDA WMS, and app-drawn labels would be a follow-up. Commit that note as `docs(planning): record native-size SSURGO decision`.
3. If either commit is missing, make it. Run `make app-frontend-check` first (source `databricks/bootstrap-serverless.sh`; expect 10 biome lint diagnostics, all outside `components/map/`, and 5 `tsc` errors, none in `components/map/`).
4. With user approval, push. Both dev apps redeploy from git automatically; poll `apps get mcp-fpac-soil-dev` and `apps get agent-fpac-soil-dev` until the active deployment's `git_source.resolved_commit` is the new head and the state is `SUCCEEDED`/`RUNNING`. Last confirmed: both on `95ca3cc` (2x labels).

## Step 1: close 44.10.1 (user re-check)

Ask the user to hard-refresh the dev agent app and confirm:

- SSURGO labels are crisp at native size (accepted as small).
- The identify popup stays inside the map near every edge and corner (fix `c79c639`: re-anchor after the portal renders). If it still clips, likely next fixes: set an explicit `anchor` from the click position relative to the map centre, or a fixed `offset`.
- The popup's theme and content (fix `a1bfdac`) are still fine.

User already passed steps 1-6 (screening, Show on map, corridor alternatives, overlays, identify, Use as AOI on Nevada, IA Urban Area GEOID 61597 at 191 vertices, the over-cap message on Scott County, IA 19163 at 2,201 vertices, screening the Use-as-AOI result). Record the outcome and set the `## Result` section of the trial sheet; update STATE_44 (44.10.1 done, fix tasks 44.10.1a-c listed with commits: `a1bfdac` popup theme/content, `c79c639` re-anchor, `63337a1`/`213f0a8` label stretching then reverted).

Traces: dev agent traces now save (user granted the app service principal `8da7b721-f052-488d-ae97-5624dec5cfa3` SELECT, MODIFY on `users.andrew_g_brown.4493391463784067_otel_{spans,logs,metrics,annotations}` and SELECT on the `_trace_metadata` and `_trace_unified` views). Query `users.andrew_g_brown.\`4493391463784067_otel_spans\`` (root span name `stream_handler`; `attributes` is VARIANT, read with `attributes:['mlflow.spanInputs']`). One `get_farmland_classification_by_point` call timed out at 180 s at 15:21 UTC 2026-11-06; it did not recur.

## Step 2: 44.11.1 two-axis review

Follow the spec in the plan: review `origin/main...feature/agent-app-map2` on two independent passes (Standards: AGENTS.md files, ADRs 0003 and 0010-0017, repo style; Spec: Goal & Scope, D1-D9, A1-A4, master plan M3-M5 exit criteria). Write `planning/REVIEW_44.md` with findings side by side and severity. Findings that need code become fix tasks 44.11.2+ in the plan's wave table with their own specs; get user decisions on the rest.

Known items to classify (fix, accept or defer):

- `.env.example` lacks `MAP_SIMPLIFY_TOLERANCE_M` and `MAP_MAX_GEOJSON_BYTES`.
- Tool description strings in `src/fpac_soil_mcp/tools/__init__.py` do not mention `include_map`.
- Frontend vertex cap `MAX_AOI_VERTICES = 2000` in `geojson.ts` is a constant; the server cap comes from `GEO_MAX_VERTICES` (default 2000) and can differ.
- SSURGO identify has no farmland class or map unit name (SDA WMS lacks them); popup says to run screening.
- Post-Plan-44 follow-ups already recorded: multiple AOIs per chat, drawing corridors on the map, app-drawn SSURGO labels, the efficiency review (`planning/HANDOFF_EFFICIENCY_REVIEW.md`).

## Step 3: 44.12.1 close-out

Per the plan spec: ADR 0017 to `Accepted`; update `docs/decisions/README.md`, `planning/MASTER_PLAN.md` (Phase 8 and Track A: M3-M5 delivered, remaining Phase 8 items listed), one status note in `planning/SPATIAL_VISUALIZATION_STRATEGY.md`, and `STATE_44.md`. Run every gate (root `make check`, `make test-live` if the user approves network, `make app-check`, `make app-frontend-check`). Then, each step only with user approval:

1. Push and open or update the PR to `main`; the user merges.
2. The production agent app `agent-fpac-soil-openai-sdk` auto-deploys from `main`; confirm with `apps get` that it runs the merge commit. Its `mcp_server` resource already names `mcp-fpac-soil`.
3. The production MCP server `mcp-fpac-soil` is not git-backed: it deploys from `/Workspace/Users/Groups/team-03/fpac-soil-mcp` (snapshot). Refresh that clone to `main` and redeploy it; then smoke-test `analyze_farmland_by_polygon` with `include_map=true` returns a `map` block. Production agent app features that need `include_map` will fail against the old server until this is done, so do steps 2 and 3 close together.
4. Ask whether to stop or keep `mcp-fpac-soil-dev` and `agent-fpac-soil-dev`.
5. Acceptance: `grep -rn mcp-fpac-soil-dev` finds nothing outside `planning/` and app docs; both production apps show the merged code.

## Working rules learned in Plan 44

- Never `open(p, "w").write(open(p).read())`: it truncates first. Edit in a `/tmp` clone (`git clone` the workspace repo), copy back with `cat /tmp/clone/$f > $W/$f`, check with `cmp -s`, then commit in the workspace repo. Small edits through the file-edit tool are also fine.
- New workspace files are executable: `git add --chmod=-x`. Ruff on workspace paths: `--extend-ignore EXE002`.
- `uv run` with `UV_LINK_MODE=copy`. Source `databricks/bootstrap-serverless.sh` before node/npm/npx.
- App logs and browser checks are the user's (the app rejects PAT auth for logs). Map routes and identify are untraced by design (ADR 0016).
- Compute was flaky at the end of the last session (commands not accepted within 30 s); if it happens, use the file-edit tool for edits and the Apps API for app state, and retry shell later.
- Plain, short user-facing updates; one commit per task with Conventional Commit messages.
