# EXECUTION PLAN 49: Deployed MCP T2 Access Smoke

## Goal & Scope

**Goal:** Establish a documented, repeatable, authenticated access path for T2 evaluation against the deployed `mcp-fpac-soil` Streamable HTTP `/mcp` endpoint. A dedicated Databricks service principal runs the smoke check, reuses the server's current HTTP session behavior, discovers tools, calls the static `explain_fppa_screening_scope` tool, and produces a sanitized evidence report.

**In scope:**

- Add an offline-testable T2 smoke client using the Databricks SDK's run-as credentials and the existing app lookup pattern to resolve `mcp-fpac-soil`.
- Exercise MCP initialization, tool discovery, session reuse, and one static tool call without depending on USDA/Census service availability.
- Add a Databricks notebook entry point for a job/notebook configured to run as the dedicated T2 evaluation service principal.
- Document runtime prerequisites, the `CAN_USE` grant, command/notebook use, evidence fields, and failure behavior.
- Close the Track E T2-authentication choice in `planning/MASTER_PLAN.md`; keep stateless Streamable HTTP as separate deferred work.
- Record a successful live smoke run in a sanitized `planning/evidence/` report.

**Out of scope:**

- Running the full T2 case corpus, changing T1 evaluation/model behavior, measuring Criterion 2 performance, or running model judges.
- Creating service principals, changing Databricks grants or job identities, deploying applications, or configuring Unity Gateway. Those require workspace-owner action; the plan assumes a dedicated evaluation principal is approved and configured externally.
- Changing the MCP server's transport/session configuration, adopting stateless HTTP, or changing the static tool or any server business logic.
- Using Unity Gateway MCP service authentication while its current access path returns 403.
- Committing credentials, PATs, access tokens, full principal identifiers, request/response bodies, or producer/private data.
- Modifying the separate agent app, adding dependencies, changing other evaluation tiers, or superseding an ADR.

**Verbatim user constraint:** “flag stateless as a future work item”

**Scope clarification:** The initial scope was “current branch”; the user then expanded it to the “roadmap.” This plan is limited to the selected highest-leverage roadmap goal, G1 in `planning/GOALS.md`.

## Reconnaissance Log (2026-11-12)

- Repository: `D:\workspace\fpac-soil-mcp`, branch `refactor/eval-corpus1`, HEAD `ad56ace` (`docs(eval): corpus consolidation`), tracking `origin/refactor/eval-corpus1`. The worktree was clean before this session; `planning/GOALS.md` is now modified by the goal-graph update. No other pre-existing changes were present.
- Orchestration numbering: `planning/EXECUTION_PLAN_48.md` is the latest plan; use 49. Existing numbered plans, states, and `planning/GOALS.md` are tracked. `.gitignore` has no planning-directory ignore rule.
- Entrypoint sizes: `eval/databricks/run_mlflow_eval.py` (206 lines), `eval/databricks/run_t1_eval_notebook.py` (40), `eval/databricks/test_databricks_runner.py` (89), `eval/databricks/test_databricks_dry_run.py` (27), `src/fpac_soil_mcp/app.py` (58), and `src/fpac_soil_mcp/routes.py` (38).
- Existing pattern: the T1 runner uses lazy Databricks imports, CLI arguments, and git SHA/branch tags (`eval/databricks/run_mlflow_eval.py`); its notebook wrapper is `eval/databricks/run_t1_eval_notebook.py`. The agent app resolves an App URL with `WorkspaceClient.apps.get(...)` and uses its app service principal with `CAN_USE` (`apps/agent-fpac-soil-openai-sdk/agent_server/config.py`, `agent_server/agent.py`, ADR 0012).
- T2 facts: `eval/databricks/README.md` records that T2 is deferred and Unity Gateway MCP service access returns 403. The master plan lists service-principal M2M vs Unity Gateway as an open T2 authentication choice and stateless-vs-stateful HTTP as a separate deployment decision. The server calls `mcp.run(transport="http")` without an explicit stateless override (`src/fpac_soil_mcp/app.py`).
- Static smoke target: `explain_fppa_screening_scope` returns a deterministic local response and does not query upstream services (`src/fpac_soil_mcp/tools/fppa_tools.py`). Keep the MCP client in one context across initialize, list, and call so it handles the deployed transport's current session behavior.
- Test architecture: ADR 0011 requires mocked/offline checks by default; live service calls remain opt-in. The T0 contract suite uses an in-memory FastMCP client. Databricks tests use pytest and local MLflow fixtures when the optional dependency group is installed. No local shared port is needed for the planned unit tests.
- Green baseline: `make check` passed on 2026-11-12: Ruff check passed, 663 files formatted, and 964 passed / 45 deselected. It emitted 183 existing warnings (pytest-asyncio configuration, Shapely transform deprecations, and MLflow SQLAlchemy deprecation). `make app-check` was not run because the separate agent app is out of scope.
- Runtime prerequisite not verified: existence of a dedicated T2 service principal, its run-as configuration, and `CAN_USE` on `mcp-fpac-soil` were not verified. A workspace owner must provide these before the live smoke; workers must not create identities, alter grants, or substitute another principal.
- Accepted ADR alignment: ADR 0011 (mocked default/live opt-in) and ADR 0012 (separate MCP client and service-principal auth precedent) are honored. ADR 0017 and server behavior are not changed. No ADR is superseded.

## Decision Log

1. **D1 — 2026-11-12 — Scope:** Expand from the current branch to the project roadmap, then plan only the circled G1 access-path goal.
2. **D2 — 2026-11-12 — Authentication:** Use dedicated service-principal M2M from a Databricks job/notebook configured with that principal as its run-as identity. Require only `CAN_USE` on `mcp-fpac-soil`; do not store credentials in the repository. Unity Gateway MCP authentication remains deferred while access returns 403.
3. **D3 — 2026-11-12 — HTTP session behavior:** Preserve the deployed server's current Streamable HTTP behavior and have the smoke client initialize and reuse its session. Do not change server transport settings; record stateless HTTP as future work.
4. **D4 — 2026-11-12 — Smoke call:** Call `explain_fppa_screening_scope` after tool discovery. It validates MCP tool invocation without coupling the result to upstream data availability.
5. **D5 — 2026-11-12 — Evidence:** Persist a sanitized report under `planning/evidence/` with timestamp, commit, endpoint host, principal label (not ID), auth/session modes, tool name, and status. Exclude credentials, identifiers, and request/response bodies.
6. **D6 — 2026-11-12 — Acceptance:** Require targeted offline unit tests and the serial `make check` gate, followed by the authorized Databricks run-as live smoke. Authentication, grant, or transport errors remain explicit failures/blocks; no success-shaped fallback.
7. **D7 — 2026-11-12 — Parallelism:** One worker per wave, no worktree; the work is one repo and a sequentially dependent client/run path.
8. **D8 — 2026-11-12 — Worker policy:** Use runtime-default worker selection and the standard wave-orchestration escalation ladder; no custom model, time, or credit budget.
9. **D9 — 2026-11-12 — Planning artifacts:** Track the numbered plan, prompt template, and state files in Git. Keep planning-only commits separate from implementation commits.
10. **D10 — 2026-11-12 — Deferred work:** Stateless Streamable HTTP remains a future work item with its own client/deployment compatibility check; it is not a dependency of G1.

## Wave & Dependency Table

| Wave | Task | Title | Must edit | Can create | Depends on |
|---|---|---|---|---|---|
| 1 | 49.1.1 | Build the authenticated T2 MCP smoke client | `eval/databricks/run_t2_smoke.py`; `eval/databricks/test_t2_smoke.py` | none | baseline |
| 2 | 49.2.1 | Add the Databricks run-as entry point and document the smoke path | `eval/databricks/run_t2_smoke_notebook.py`; `eval/databricks/README.md` | `planning/evidence/49.2.1-t2-smoke.md` (orchestrator only, after a successful live run) | 49.1.1; dedicated service-principal run-as and `CAN_USE` provisioned externally |

**Wave discipline:** One worker runs per wave, with no worktree. Workers run only their task's targeted tests. The orchestrator runs `make check` serially at each wave boundary. The Wave 2 live call is an explicitly selected acceptance step but requires the external service-principal/run-as prerequisite; if it is unavailable, stop and mark the task blocked rather than weakening auth or treating a dry run as success. The orchestrator updates the Track E decision in `planning/MASTER_PLAN.md` and records any successful live evidence as a separate planning-only closeout, not in a code commit.

## Task Specifications

### 49.1.1 — Build the authenticated T2 MCP smoke client

- **Repo:** `AndrewBrown-USDA/fpac-soil-mcp` (`D:\workspace\fpac-soil-mcp`)
- **Files in scope:**
  - Must edit: create `eval/databricks/run_t2_smoke.py` and `eval/databricks/test_t2_smoke.py`.
  - Can create: none. Scratch, if needed, only under `.development/49/`.
- **Depends on:** none.
- **Spec:** Implement a small CLI-callable smoke runner that uses the Databricks SDK's current run-as credentials to resolve the `mcp-fpac-soil` App URL and authenticate a FastMCP Streamable HTTP client without reading or logging PATs or secret values. Keep optional Databricks SDK imports lazy so the default offline suite can import and test the module without the `eval-databricks` group. Keep one client context for initialization, tool discovery, and the `explain_fppa_screening_scope` call so the negotiated session is reused. Fail explicitly if the app URL, authentication, session, tool discovery, or tool result is invalid. Add a sanitized result record with timestamp, commit SHA, endpoint host, a generic run-as principal label, auth/session modes, tool name, and status; never serialize request/response bodies or full principal identifiers. Follow the CLI/git-metadata patterns in `eval/databricks/run_mlflow_eval.py` and the app-URL resolution pattern in `apps/agent-fpac-soil-openai-sdk/agent_server/config.py`.
- **Constraints (do not touch):** Do not edit the server, the separate agent app, T1 runner/scorers, dependency manifests, or deployment grants. Do not add a PAT or secret setting. Do not use a soil query or live network in unit tests. Do not silently fall back to unauthenticated access or a local server after auth failure.
- **Grep anchors:** `_git_sha`, `_git_branch`, and `_default_experiment` in `eval/databricks/run_mlflow_eval.py`; `fpac_mcp_url` and `WorkspaceClient.apps.get` in `apps/agent-fpac-soil-openai-sdk/agent_server/config.py`; `explain_fppa_screening_scope` in `src/fpac_soil_mcp/tools/fppa_tools.py`; existing CLI test patterns in `eval/databricks/test_databricks_runner.py`.
- **Acceptance:** `uv run --group eval-databricks pytest eval/databricks/test_t2_smoke.py -q` passes offline. Tests cover URL resolution, auth adaptation, initialization/tool/call ordering and session reuse, a successful sanitized result, and explicit error behavior without making an external request.

### 49.2.1 — Add the Databricks run-as entry point and record smoke evidence

- **Repo:** `AndrewBrown-USDA/fpac-soil-mcp` (`D:\workspace\fpac-soil-mcp`)
- **Files in scope:**
  - Must edit: create `eval/databricks/run_t2_smoke_notebook.py`; edit `eval/databricks/README.md`.
  - Can create: none. Scratch, if needed, only under `.development/49/`. The orchestrator owns `planning/MASTER_PLAN.md` and may create `planning/evidence/49.2.1-t2-smoke.md` only after a successful live run.
- **Depends on:** 49.1.1.
- **Spec:** Add a Databricks notebook source wrapper that invokes the tested smoke runner in a job/notebook configured to run as the dedicated T2 service principal. Document installation/execution, external prerequisites, the least-privilege `CAN_USE` grant, expected sanitized evidence, and explicit handling of auth/session/upstream failures. Keep stateless HTTP and Unity Gateway MCP registration as separate future/deferred items. The orchestrator updates the master-plan Track E auth decision in a separate planning-only closeout. After the worker completes its local implementation and the service principal has been provisioned and granted access by a workspace owner, the orchestrator runs the smoke against deployed `/mcp` and records only the sanitized report specified in D5. Do not interpret dry-run or local tests as deployed access evidence.
- **Constraints (do not touch):** Do not create or modify Databricks identities, grants, app deployment, credentials, or remote workspace configuration. Do not alter the server's transport mode, run full T2/T1 model evaluations, record raw tool output, or claim success if the external prerequisite is absent. Preserve ADR 0011's offline-default architecture and ADR 0012's separate-client boundary.
- **Grep anchors:** T2 deferred/auth text in `eval/databricks/README.md`; T1 notebook setup in `eval/databricks/run_t1_eval_notebook.py`; Track D and Track E open decisions in `planning/MASTER_PLAN.md`; `WorkspaceClient.apps.get` pattern in the agent app config.
- **Acceptance:** `uv run --group eval-databricks pytest eval/databricks/test_t2_smoke.py -q` passes; the notebook wrapper and documentation identify the dedicated run-as principal and no-secret policy; the orchestrator's deployed smoke initializes `/mcp`, discovers and successfully calls `explain_fppa_screening_scope`, and emits the sanitized evidence file. If workspace provisioning is unavailable, report the exact missing prerequisite and keep G1 blocked.

## Hazards

- The dedicated service principal, its Databricks job/notebook run-as assignment, and its `CAN_USE` grant are external prerequisites and were not verified during planning. Do not provision or grant access from the worker.
- Databricks SDK session credentials may not be available from a local `uv` CLI environment even when they exist in a notebook; run the live smoke only in the approved configured Databricks execution context.
- Unity Gateway MCP service access currently returns 403. Do not silently switch to that path or interpret a 403 as a successful access check.
- Do not conflate an MCP transport/tool failure with an upstream USDA/Census failure; the selected static smoke tool avoids upstream calls.
- Keep secrets and raw tool outputs out of test snapshots, logs, and evidence. Only a generic principal label and endpoint host may be retained.
- Do not change server-side stateless/session settings. The deferred stateless work must check compatibility with deployed clients before any transport change.
- Run all local acceptance gates serially. The baseline has existing pytest-asyncio, Shapely, and MLflow deprecation warnings; do not expand scope to fix them.

## Wave Acceptance Gates

At the end of each wave, the orchestrator runs `make check` serially. The task worker runs only its targeted command. After Wave 2's offline gate, the orchestrator verifies the selected deployed smoke in the approved Databricks run-as context. No `make app-check`, harness tests, live soil query, T1 model evaluation, or full T2 corpus run is required for this goal.
