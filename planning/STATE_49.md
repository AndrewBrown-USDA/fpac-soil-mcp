# STATE 49: Deployed MCP T2 Access Smoke

Resume point for orchestration 49. Plan: `planning/EXECUTION_PLAN_49.md`.
Worker prompt: `planning/PROMPT_TEMPLATE_49.md`.

## Baseline (recorded before wave 1; 2026-11-12)

- [x] Repo `D:\workspace\fpac-soil-mcp`, branch `refactor/eval-corpus1`, HEAD `ad56ace`; current uncommitted changes are this session's `planning/GOALS.md` update and the three new orchestration 49 planning artifacts.
- [x] Planning artifacts are tracked; orchestration 48 is the latest completed plan. Orchestration 49 is new; preserve all historical plans/states.
- [x] `make check` — Ruff check passed; 663 files formatted; offline Python suite **964 passed, 45 deselected**. Existing deprecation warnings are recorded in `EXECUTION_PLAN_49.md`.
- [x] Accepted ADRs reviewed: 0011 (offline/mock default, live opt-in), 0012 (agent app is separate MCP client with service-principal auth precedent), and 0017 (map response contract; no server changes in scope).
- [x] T2 runner does not yet exist. Reference code: `eval/databricks/run_mlflow_eval.py`, `run_t1_eval_notebook.py`, `test_databricks_runner.py`, and `apps/agent-fpac-soil-openai-sdk/agent_server/config.py`.
- [ ] External prerequisite: workspace owner provisions/approves a dedicated T2 evaluation service principal, assigns it as the Databricks job/notebook run-as identity, and grants only `CAN_USE` on `mcp-fpac-soil`. Do not run the live smoke until this is available.
- [x] No shared local port is required by the targeted unit test. The live acceptance uses the deployed endpoint only; do not substitute a local server.

## Wave Board

| Wave | Task | Status | Commit | Notes |
|---|---|---|---|---|
| 1 | 49.1.1 Build the authenticated T2 MCP smoke client | done | `be7870d`, `b524893`, `4117d07` | Targeted tests and serial `make check` passed; live access remains gated on external provisioning |
| 2 | 49.2.1 Add the Databricks run-as entry point and record smoke evidence | deferred | `2e79852` | Notebook/docs implemented and checks pass; live diagnostic got 401 with the notebook-runtime token. Deferred to a post-hackathon USDA deployment with a provisioned service principal |

## Task Reports

<!-- Orchestrator appends <=15 lines per task under ## <id>. -->

## 49.1.1
- Status: done; implemented authenticated T2 smoke client and offline coverage.
- Files: `eval/databricks/run_t2_smoke.py`, `eval/databricks/test_t2_smoke.py`.
- Code commits: `be7870d` feature, `b524893` Ruff imports, `4117d07` formatting.
- Targeted: `uv run --group eval-databricks pytest eval/databricks/test_t2_smoke.py -q` — 12 passed.
- Wave gate: `make check` — Ruff passed, 670 files formatted, 976 passed / 45 deselected.
- Planning-only commits: `b4fd0a6`, `216d17c`, `1a428f1`, `e99e6c7`, `dd99091`.
- Deviations: one Ruff import fix and a follow-up formatting remediation after the first two wave-gate failures; all resolved.
- Gotchas: the live smoke is still blocked pending a dedicated Databricks run-as principal and `CAN_USE` grant.

## 49.2.1
- Status: deferred (2026-11-13, user decision). Implementation done; deployed acceptance not run. Resume in a post-hackathon USDA deployment where a dedicated service principal can be provisioned.
- Files: `eval/databricks/run_t2_smoke_notebook.py`, `eval/databricks/README.md`.
- Code commit: `2e79852`.
- Targeted: `uv run --group eval-databricks pytest eval/databricks/test_t2_smoke.py -q` — 12 passed.
- Wave gate: `make check` — Ruff passed, 672 files formatted, 976 passed / 45 deselected.
- Planning-only worker commit: `73fb0e2`; orchestrator closeout includes this state and the Track E auth decision.
- Deviations: none in implementation; live smoke and sanitized evidence were not produced because the external prerequisite is not verified.
- Gotchas: do not claim deployed access success or create `planning/evidence/49.2.1-t2-smoke.md` until a workspace owner enables and verifies the required run-as identity/grant.
- Blocker check (2026-11-13, read-only, on Databricks): `mcp-fpac-soil` (running from `main`) grants `CAN_USE` only to `team-03` and the two agent-app service principals; no T2 evaluation principal is granted.
- Candidate `sp-mcp-eval` exists in the workspace, but its owner, purpose, and grants are not visible to non-admins (SCIM detail, account rule set, and `system.access` audit are admin-gated). No visible job runs as it and no repo code references it. Not used: the plan requires a dedicated principal.
- Live diagnostic (2026-11-13, as the CAN_MANAGE user on serverless; not acceptance, no evidence file): (1) the notebook wrapper's `main()` calls `asyncio.run()`, which raises "cannot be called from a running event loop" in a notebook cell; offline tests miss this. (2) Awaiting `run()` directly failed at MCP initialization; a raw `initialize` POST to `/mcp` with the SDK `runtime` Bearer token returned 401 (no session). The Apps proxy rejects the notebook-runtime token regardless of app permission, so a run-as job (same runtime token type) is very likely to fail the same way.
- Resume steps: provision (or confirm owner of) a principal with `CAN_USE` on the app plus an OAuth secret in a secret scope; amend D13 (run-as, no stored credentials) for M2M; add an OAuth M2M token path to `run_t2_smoke.py` with offline tests; then run the live smoke and write `planning/evidence/49.2.1-t2-smoke.md`.
- Event-loop fix (2026-11-13): `main_async()` added; the notebook awaits it and `main()` stays the CLI entry. 3 new offline tests (15 passed); re-run in a live notebook returned the sanitized exit 1 (expected 401), with no event-loop error.
- Side note: an unpinned `pip install -e` resolved `fastmcp` 4.2.0 vs 4.1.6 in `uv.lock`; unrelated to the 401.
