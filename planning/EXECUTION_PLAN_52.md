# EXECUTION PLAN 52: Structured Site Assessment Interview and Confirmation

## Goal & Scope

### Goal

Complete the remaining PR #100 work on the user-selected current checkout,
`feature/sa-checklist2`: give the agent a validated-resource-backed Site
Assessment question/answer contract; present the questions and review summary
as informative, interactive cards; require an explicit summary-card Confirm
whose structured record matches the submitted answers before a preliminary
LESA call; conservatively represent missing Site Assessment inputs; correct
interview/CDL sequencing; and prevent stale CDL map results from being shown
for a replaced AOI. Verify locally before any separately authorized dev-app
trial.

### In scope

- Add structured question, answer, evidence/comment, provenance, unknown,
  skipped, and confirmed-summary records using the validated criteria resource.
- Show registry-sourced question wording, citations, band choices, point
  schedules, and available evaluation context in distinct frontend cards.
- Use the Confirm/Edit summary interaction as the single user approval.
  Enforce a separate, agent-side guard that rejects missing or mismatched
  confirmation records before forwarding the Site Assessment answers to
  `calculate_preliminary_lesa`.
- Score unknown, unavailable, skipped, and omitted Site Assessment inputs at
  conservative maximum points, label those assumptions, keep the result
  undetermined, and expose a separate conservative bound; record ADR 0018.
- Run soil screening before offering Start/Skip for the interview; never
  submit interview-based LESA inputs before the interview is confirmed.
- Request combined CDL context once for attached or pasted AOIs and do not
  follow it with a redundant `analyze_cdl_histogram` call.
- Reject stale CDL summaries when the active AOI no longer matches the AOI
  used by the result.
- Add focused backend, evaluation-contract, and frontend Playwright tests,
  then run the serial local validation gate.
- Update the PR-scoped goal graph and the approved `TODO.md` acceptance
  language.

### Out of scope

- Lakebase or other persistent interview storage; answers and confirmation
  remain structured conversation-history/tool-call items and MLflow trace
  data.
- Official FPPA determinations, completed AD-1006/CPA-106 forms, legal advice,
  exemption decisions, or siting recommendations.
- A new LESA-only MCP client/approval exception or a second MCP Approve click.
  The explicit summary-card Confirm is the user approval; the agent-side
  matching-history check is the programmatic gate.
- Trace redaction or a no-AOI-geometry-in-traces guarantee. Preserve accepted
  ADR 0016, which allows geometry in chat/tool traces.
- Adding a React component-test dependency or a TypeScript-check gate. Use the
  already-installed Playwright dependency; the frontend gate remains
  read-only lint and build.
- Pushes, redeployments, PR edits, review-thread replies, or other remote
  actions without separate explicit user authorization.
- The already completed CDL identify exclusion, CDL WKT/WKID reprojection, and
  criteria-band validation fixes; do not rework them.

### User-stated constraints

> "Answers, comments and provenance are stored as structured tool-call items
> in the conversation history, plus the MLflow trace. Lakebase persistence is
> a follow-up PR."

> "Missing Site Assessment inputs get maximum points as a conservative
> assumption, never 0. They stay labelled 'assumed (no evidence)' and the
> result stays undetermined."

> "Pushes need your approval."

The user later chose `preserve-adr`: retain ADR 0016 and revise the old
no-geometry trace acceptance. The user also chose `confirm-only`: summary-card
Confirm plus the agent-side matching-history guard, with no separate MCP
Approve step. For frontend interactions, use the existing Playwright
dependency rather than adding React Testing Library/jsdom.

## Decision Log

| ID | Decision | Rationale / source |
|---|---|---|
| D1 | Continue on the current checkout `D:\workspace\fpac-soil-mcp`, branch `feature/sa-checklist2`, current HEAD `151819c`; do not switch to `feature/sa-checklist1` or a Databricks clone. | User selected the current checkout after the branch mismatch was found. Docs-only commits `f709c21` and `151819c` advanced the branch during planning. |
| D2 | Keep G1 as the project-wide circled goal; add the PR #100 sub-goal DAG as G23-G30. | User approved a PR-scoped graph while preserving G1. |
| D3 | Use up to two concurrent workers in new isolated `51.*` worktrees. | User selected two-worktree execution; retain all existing `.worktrees\` entries. |
| D4 | Preserve accepted ADR 0016; AOI geometry may appear in chat/tool traces, so remove the former no-geometry trace acceptance. | User selected `preserve-adr`. |
| D5 | The explicit summary-card Confirm is the sole user approval, with the server-side matching-history guard. Do not carve out a LESA-only HostedMCP approval path. | User selected `confirm-only` after reviewing the approval integration constraint. |
| D6 | Use Playwright for click-to-structured-answer and confirmation tests; do not add component-test dependencies. | User selected the existing Playwright dependency. |
| D7 | Track planning artifacts and commit them separately from implementation using `docs(planning):`. | Recorded in the approved `TODO.md` planning notes. |
| D8 | Frontend validation remains lint/build; do not add `tsc` because upstream already fails it. | Approved plan constraint in `TODO.md` and app `AGENTS.md`. |
| D9 | Local implementation commits are allowed after worker micro-plan approval and verification; remote actions remain separately gated. | User requires approval for pushes; no remote action is authorized by this plan. |
| D10 | Frontend recognizes `get_site_assessment_question` and `record_site_assessment_answer` by their existing tool names and preserves the 52.1.2 answer record fields. Confirm emits `type: site_assessment_confirmed_summary`, `confirmed: true`, and an `answers` array of those unchanged records. CDL results are stale when no AOI is active or its `aoi_ref`/geometry differs; a reattached AOI with the same reference and geometry is equivalent, so no new generation token is added. | Aligns frontend history with the completed tool contract and gives the confirmation gate a stable record while avoiding unrelated AOI-state changes. |
| D11 | The user waived executing the Playwright suite; keep its fixture/test deliverable, but do not block integration on browser availability. | Explicit user instruction: “proceed without playwright”. |
| D12 | When either `project_farm_acres` or `county_average_farm_acres` is supplied to the interview-flow LESA call, require both; when both are supplied, derive Criterion 7's registry band and require that answer to be present in the confirmed summary before forwarding the call. | Parent review found these inputs independently score Criterion 7, so matching only `criteria_facts` would leave an unconfirmed scoring path. |
| D13 | Reject any Criterion 7 fact supplied together with the farm-acre pair, even when both representations resolve to the same band. | The downstream LESA evaluator rejects simultaneous Criterion 7 fact and farm-acre inputs; the gate must return the explicit error before forwarding instead of allowing an avoidable MCP failure. |
| D14 | Install the confirmation wrapper on the request-scoped MCP server whether or not an AOI is active; update the AOI-context test that expected the unwrapped call boundary while preserving AOI behavior. | The gate must protect site LESA calls independently of AOI state; integrated tests exposed an obsolete assertion about wrapper identity. |

## Reconnaissance and Hazards

- Current repo/branch: `D:\workspace\fpac-soil-mcp`,
  `feature/sa-checklist2`, HEAD `151819c`.
- During planning, docs-only commits `f709c21` (root `AGENTS.md` and
  `README.md`) and `151819c` (`docs/evaluation.md`) were added to the current
  branch. Preserve these changes. The working tree currently has no edits to
  those files; `.worktrees\` remains untracked with registered
  orchestration-50 worktrees. Create only new `51.*` worktrees if execution
  requires them.
- Planning artifacts are tracked, not ignored. The tracked `TODO.md` and
  `planning/GOALS.md` are updated for this plan; commit them with the new plan
  files only after plan approval.
- Key entry points: `agent_server/agent.py` (agent assembly, MCP connection,
  invoke/stream handlers); `agent_server/history.py` (history normalization);
  `agent_server/aoi_context.py` (MCP `call_tool` wrapper precedent);
  `frontend/client/src/components/message.tsx` (dynamic tool rendering);
  `frontend/client/src/hooks/use-approval.ts` (existing approval UI, not used
  as the LESA gate under D5); `src/fpac_soil_mcp/tools/lesa_tools.py`
  (`_score_registry_facts`); `ShowOnMapButton.tsx` (CDL result presentation).
- `agent.py` validates the Site Assessment resource before adding it to
  instructions, but constructs the `Agent` with `tools=[]`. The
  `invoke_handler` and `stream_handler` both normalize request history before
  `Runner.run`; the confirmation guard must cover both execution paths.
- `history.py` documents that it is copied across three OpenAI Agents SDK
  templates. Existing normalization passes non-message/tool records through;
  avoid editing it unless tests prove it is necessary, and preserve its
  copy-synchronization invariant if it must change.
- Frontend currently has one focused Node test (`identify.test.ts`) and
  `@playwright/test` is already installed, but no component-test harness.
  Create an isolated Playwright fixture/entry for the new cards; do not ship a
  test-only UI route in the production navigation.
- Evaluation cases are in `eval/eval_cases.v1.json`; SA-MA-02 currently
  expects missing criteria to remain unavailable/not scored and must be
  revised for the approved conservative-max behavior. Add prompt cases there
  for the traced LESA and AOI/CDL sequences.
- ADR 0016 expressly allows geometry in chat/tool traces. ADRs 0003, 0007,
  0012, 0015, and 0017 remain relevant: preserve the preliminary authority
  boundary, existing LESA architecture, separate MCP-client boundary,
  vendored frontend change ledger, and server map-result contract.
- Baselines recorded on `feature/sa-checklist2` at `7e8f71f` before the
  intervening docs-only commits: root tests
  1,019 passed / 45 deselected; root Ruff check/format passed; app tests
  196 passed and app Ruff check/format passed; frontend read-only Biome lint
  and client/server builds passed with 10 existing lint warnings. The app
  fixture-only final change is outside root pytest collection. `make app-check`
  has previously failed to start on this Windows host with an Rtools path
  error; use its direct `uv`/Ruff equivalents if it remains unusable.
- `npm ci` previously reported 10 existing audit advisories (4 low,
  6 moderate); do not apply automated dependency updates.
- No Databricks-authenticated integrated chat trial or dev-app trial has been
  completed on this checkout. Such verification follows only after explicit
  push/redeployment approval.

## Wave Table

| Wave | Theme | Tasks | Dependencies |
|---|---|---|---|
| 1 | Foundation contracts | 52.1.1 Conservative missing-input scoring; 52.1.2 Structured interview tool contract | None; task files are disjoint. |
| 2 | Interview experience and sequencing | 52.2.1 Trigger/CDL sequencing and replay cases; 52.2.2 Question/summary cards, Playwright fixture, and stale-CDL guard | 52.2.1 depends on 52.1.1 and 52.1.2; 52.2.2 depends on 52.1.2. |
| 3 | Confirmation enforcement | 52.3.1 Confirm-only agent-side matching-history gate | 52.1.2, 52.2.1, and 52.2.2. |
| 4 | Serial acceptance and handoff | Orchestrator runs the integrated local validation gate; dev trial remains conditional on separate remote approval | All implementation tasks complete. |

Wave tasks are disjoint within each wave. Use at most two workers, each in a
new isolated `51.*` worktree. Run shared/full test suites serially at the
orchestrator gate.

## Task Specifications

### 52.1.1 — Score missing Site Assessment inputs conservatively

- **Repo:** `D:\workspace\fpac-soil-mcp`
- **Must edit:**
  `src\fpac_soil_mcp\tools\lesa_tools.py`,
  `src\fpac_soil_mcp\models.py`,
  `tests\test_lesa.py`,
  `tests\test_site_assessment_contract.py`,
  `tests\test_tools.py`,
  `tests\eval\test_phase4_databricks_contract.py`,
  `eval\eval_cases.v1.json`,
  `apps\agent-fpac-soil-openai-sdk\agent_server\prompts\system_prompt.txt`,
  `apps\agent-fpac-soil-openai-sdk\tests\test_agent_config.py`,
  `docs\decisions\README.md`.
- **Can create:**
  `docs\decisions\0018-conservative-missing-site-assessment-inputs.md`,
  focused tests in the listed test files.
- **Depends on:** none.
- **Specification:** Change the existing unavailable/not-scored behavior for
  omitted, unknown, unavailable, and skipped Site Assessment criteria. Assign
  each the registry maximum as a conservative assumption; preserve an explicit
  `assumed (no evidence)` label/status and provenance; keep the actual result
  undetermined and expose a separate conservative bound. Do not represent an
  assumption as evidence or as a completed/official LESA score. Update the
  system prompt's no-zero-fill rule without weakening no-invented-values or
  authority limits. Preserve the app prompt's canonical FPAC policy block;
  place the Site Assessment-specific bound clarification in its interview
  rules. Update SA-MA-02 and directly coupled test expectations to this
  contract. Document the owner-approved rule as ADR 0018 and index it.
- **Do not touch:** Site Assessment registry bands or CFR text, interview UI,
  prompt sequencing, MCP tool wiring, AOI handling, dependency manifests, or
  remote resources.
- **Grep anchors:** `_score_registry_facts` in `lesa_tools.py`;
  `PreliminaryLESAResponse` and criterion result models in `models.py`;
  missing/unavailable assertions in `tests\test_lesa.py`;
  `unknown_partial_unavailable` and `no_invented_values_authority` in
  `system_prompt.txt`; case `SA-MA-02` in `eval\eval_cases.v1.json`.
- **Reference implementations:** registry-driven band scoring in
  `_score_registry_facts`; current `evidence_status`/`input_authority` result
  fields; ADR 0007 and ADR 0003.
- **Acceptance:** focused tests prove omitted, unknown, unavailable, and
  skipped criteria get maximum points only as labelled assumptions, preserve
  an undetermined result, and expose a distinct conservative bound; known
  evidence keeps existing scoring. Also verify the updated eval contract,
  tool assertion, and canonical app-policy copy. Run from root:
  `uv run pytest tests\test_lesa.py tests\test_site_assessment_contract.py tests\test_tools.py tests\eval\test_phase4_databricks_contract.py tests\test_prompts.py -q`.
  Run from the app directory:
  `uv run --frozen --python 3.11 pytest tests\test_agent_config.py -q`.

### 52.1.2 — Add the structured Site Assessment tool contract

- **Repo:** `D:\workspace\fpac-soil-mcp`
- **Must edit:**
  `apps\agent-fpac-soil-openai-sdk\agent_server\agent.py`,
  `apps\agent-fpac-soil-openai-sdk\tests\test_agent_construction.py`,
  `apps\agent-fpac-soil-openai-sdk\tests\test_agent_mcp_wiring.py`,
  `apps\agent-fpac-soil-openai-sdk\tests\test_history_normalization.py`.
- **Can create:**
  `apps\agent-fpac-soil-openai-sdk\agent_server\site_assessment_tools.py`,
  `apps\agent-fpac-soil-openai-sdk\tests\test_site_assessment_tools.py`.
- **Depends on:** none.
- **Specification:** Add agent-side function tool(s) built only from the
  validated `fppa://site-assessment-criteria` resource. Emit one criterion at
  a time with criterion number, question, citation, resource-defined choices
  and point schedule, plus structured answer/evidence/comment/provenance
  fields. Store user answers, comments, provenance, unknown, and skipped
  states as structured tool-call/history items; preserve them through history
  normalization. Provenance values must distinguish user, agent, and tool
  inputs. Never accept model-supplied points or duplicate the registry. If
  the resource is missing or malformed, disable the interview tool as the
  current resource path does. Do not change the shared `history.py` helper
  unless a focused failing test proves it necessary; if so, stop and report
  the cross-template implications before widening scope.
- **Do not touch:** MCP server contracts, persistence/Lakebase, frontend
  rendering, scoring behavior, or AOI geometry/tracing policy.
- **Grep anchors:** `_site_assessment_criteria_context`, `create_agent`,
  `_connect_fpac_agent`, and `tools=[]` in `agent.py`; history pass-through in
  `history.py`; `fppa://site-assessment-criteria` resource validation tests.
- **Reference implementations:** criteria validation/context assembly in
  `agent.py`; `normalize_history_items` pass-through behavior. No app-local
  Agents SDK function tool exists; use the pinned SDK's `function_tool`
  pattern, not the root FastMCP registration pattern.
- **Acceptance:** tests prove tool choices and citations come only from the
  validated resource; user selections produce structured records with
  provenance; skipped/unknown survive replay; invalid resource disables the
  interview; supplied points cannot override registry points. Run from the
  app directory:
  `uv run --frozen --python 3.11 pytest tests\test_site_assessment_tools.py tests\test_agent_construction.py tests\test_agent_mcp_wiring.py tests\test_history_normalization.py -q`.

### 52.2.1 — Correct interview triggering and CDL request sequence

- **Repo:** `D:\workspace\fpac-soil-mcp`
- **Must edit:**
  `src\fpac_soil_mcp\prompts\fppa_prompts.py`,
  `tests\test_prompts.py`,
  `apps\agent-fpac-soil-openai-sdk\agent_server\prompts\system_prompt.txt`,
  `apps\agent-fpac-soil-openai-sdk\tests\test_agent_config.py`,
  `eval\eval_cases.v1.json`,
  `eval\common\dataset.py`,
  `eval\common\test_common_dataset.py`,
  `eval\databricks\scorers.py`,
  `eval\databricks\test_databricks_scorers.py`.
- **Can create:** focused prompt/eval-contract tests in the listed test paths.
- **Depends on:** 52.1.1 and 52.1.2.
- **Specification:** For a request to perform LESA, run the preliminary soil
  screening first, then offer Start/Skip for the guided Site Assessment
  interview, and do not make an interview-based LESA call before completion
  and confirmation. Offer the interview only for site (LE) projects. When an
  attached AOI or pasted WKT/GeoJSON AOI is in scope, request the combined CDL
  context once; do not call `analyze_cdl_histogram` after
  `analyze_cdl_context`. Keep CDL separate from Criterion 2. Add model-assisted
  replay cases for the traced full-AD-1006 request and the pasted-AOI
  agricultural-use prompt. Extend the evaluation contract with an ordered
  expected-tool subsequence and prohibited-tool list so those cases can assert
  sequencing and the absence of a pre-confirmation calculator call or
  redundant histogram without relying on exact prose.
- **Do not touch:** tool schema or band validation, frontend components,
  scoring code, maps, or deployment configuration.
- **Grep anchors:** `fppa_site_assessment_assistant_prompt` in
  `fppa_prompts.py`; `Site Assessment interview behavior` and AOI/CDL rules in
  `system_prompt.txt`; existing model-assisted cases in
  `eval\eval_cases.v1.json`; case validation in `eval\common\dataset.py`;
  tool scorers in `eval\databricks\scorers.py`.
- **Reference implementations:** existing Site Assessment prompt/resource
  contract; combined `analyze_cdl_context` tool contract; existing
  `expected_tools` and `expected_tool_calls` validation/scoring; ADR 0003.
- **Acceptance:** prompt tests assert soil-first, Start/Skip-before-LESA,
  site-only interview, one combined CDL request, and no redundant histogram.
  Eval scorer tests prove ordered subsequences and prohibited tools are
  checked; replay cases encode the traced sequences. Run from root:
  `uv run pytest tests\test_prompts.py eval\common\test_common_dataset.py eval\databricks\test_databricks_scorers.py -q` and
  `uv run pytest eval\contract\test_contract.py eval\pi\test_agent_eval.py eval\databricks\test_databricks_agent.py -q`.
  Run from the app directory:
  `uv run --frozen --python 3.11 pytest tests\test_agent_config.py -q`.

### 52.2.2 — Build informative interview cards and reject stale CDL results

- **Repo:** `D:\workspace\fpac-soil-mcp`
- **Must edit:**
  `apps\agent-fpac-soil-openai-sdk\frontend\client\src\components\message.tsx`,
  `apps\agent-fpac-soil-openai-sdk\frontend\client\src\components\map\ShowOnMapButton.tsx`,
  `apps\agent-fpac-soil-openai-sdk\frontend\package.json`,
  `apps\agent-fpac-soil-openai-sdk\AGENTS.md`,
  `docs\decisions\0015-vendored-agent-app-frontend.md`.
- **Can create:** focused question and summary card components under
  `frontend\client\src\components\`; an isolated Playwright fixture, test
  config, and test file under `frontend\`; a test-only script in the frontend
  package manifest.
- **Depends on:** 52.1.2.
- **Specification:** Render a distinct question card from the structured
  question tool item. Show the criterion's nature, question, citation,
  resource-defined band choices and points, relevant evaluation information
  available in the resource, optional evidence/comment input, and provenance.
  Identify the question through the existing
  `get_site_assessment_question` tool name and keep answer records in the
  `record_site_assessment_answer` contract from 52.1.2. The Confirm action
  emits a `site_assessment_confirmed_summary` record with `confirmed: true`
  and an `answers` array containing the unchanged structured answer records.
  Provide explicit unknown/skipped choices without inventing score bands.
  Emit the selected choice as a structured answer record. Render the complete
  review summary separately from response prose, including assumption labels,
  and provide Confirm/Edit actions; Confirm emits the structured confirmation
  record. Use existing design tokens and do not represent preliminary
  information as an official determination. Before storing a CDL result in
  map context, reject it if the active AOI has been replaced or detached.
  Add an isolated Playwright test fixture using the existing
  `@playwright/test` dependency; do not add a production route or new test
  dependency. Update ADR 0015's local-change ledger and app guidance.
- **Do not touch:** app server confirmation enforcement, MCP calls, frontend
  approval behavior for unrelated tools, package lock/dependencies, other
  overlays, or production navigation.
- **Grep anchors:** `ToolPartRenderer` and dynamic-tool blocks in
  `message.tsx`; `parseCDLContextResult`, `unavailable`, and `mapResult.show`
  in `ShowOnMapButton.tsx`; Playwright dependency/scripts in
  `frontend\package.json`; ADR 0015 `Local changes`.
- **Reference implementations:** existing `McpTool`/tool-part rendering,
  `CDLContextSummary`, existing chat design tokens, and the current
  `identify.test.ts` Node test style for small pure helpers.
- **Acceptance:** Playwright tests click a registry band and assert the
  exact structured answer, comment/provenance, Confirm/Edit behavior, and
  replaced-AOI refusal before `mapResult.show`. Run from
  `apps\agent-fpac-soil-openai-sdk\frontend`:
  `npm run test:site-assessment` (execution waived by D11); then run the app's
  read-only frontend lint and build gate: `npm ci`, `npx biome lint
  --skip=nursery/useSortedClasses --skip=style/useTemplate .`, and
  `npm run build`. Do not run write-mode lint or `tsc`.

### 52.3.1 — Enforce the matching confirmed-summary gate

- **Repo:** `D:\workspace\fpac-soil-mcp`
- **Must edit:**
  `apps\agent-fpac-soil-openai-sdk\agent_server\agent.py`,
  `apps\agent-fpac-soil-openai-sdk\tests\test_agent_mcp_wiring.py`,
  `apps\agent-fpac-soil-openai-sdk\tests\test_aoi_context.py`.
- **Can create:**
  `apps\agent-fpac-soil-openai-sdk\agent_server\site_assessment_gate.py`,
  `apps\agent-fpac-soil-openai-sdk\tests\test_site_assessment_gate.py`.
- **Depends on:** 52.1.2, 52.2.1, and 52.2.2.
- **Specification:** Enforce the gate at the agent-side MCP call boundary for
  both `invoke_handler` and `stream_handler`. Before forwarding any site
  `calculate_preliminary_lesa` call in the interview flow—including a
  confirmed Skip or unknown-only summary—require a
  `site_assessment_confirmed_summary` record with `confirmed: true` and an
  `answers` array in the current request history. Its canonical answers and
  statuses must exactly match the submitted Site Assessment inputs. Do not
  bypass the gate merely because inputs are absent. Reject missing
  confirmation, stale/mismatched answers, and invalid confirmation with an
  explicit tool error and no MCP call. Keep summary-card Confirm as the only
  user approval; do not add or require a second MCP Approve action. Derive
  selected points from validated resource band IDs/registry rules, not
  model-supplied points.
  Treat `project_farm_acres` and `county_average_farm_acres` as Criterion 7
  scoring inputs: reject an incomplete pair, derive the registry band from
  their ratio when both are supplied, and require it to match a confirmed
  Criterion 7 answer. Reject any simultaneous explicit Criterion 7 fact and
  farm-acre pair, even if both resolve to the same band, because the
  downstream evaluator prohibits both representations.
  Bind the gate on every request-scoped MCP server, with or without an AOI;
  preserve AOI context behavior and update its test for the expected wrapper.
  Preserve explicit unknown/skipped records and the existing
  preliminary-authority boundary. Corridor flows remain outside the
  Site Assessment interview gate.
- **Do not touch:** frontend question/summary presentation, criteria registry
  scoring policy, persistence, approval flows for unrelated tools, or
  trace-redaction behavior.
- **Grep anchors:** `invoke_handler`, `stream_handler`, `_connect_fpac_agent`,
  and `server.call_tool` in `agent.py`/`aoi_context.py`; active request history
  conversion and existing MCP wiring tests.
- **Reference implementations:** `bind_active_aoi` as an agent-side
  `call_tool` wrapper; `normalize_history_items`; the structured records from
  52.1.2 and Confirm action from 52.2.2.
- **Acceptance:** focused tests prove the MCP calculator is never called
  without confirmation or on mismatch, is called after a matching Confirm,
  including when the confirmed summary records Skip/unknown states, and
  behaves consistently for invoke and stream handlers. Tests also prove
  points cannot be overridden by the model, and unconfirmed or mismatched
  farm-acre inputs cannot score Criterion 7, and simultaneous Criterion 7
  facts and farm-acre inputs are rejected before forwarding. Run from the app
  directory:
  `uv run --frozen --python 3.11 pytest tests\test_site_assessment_gate.py tests\test_agent_mcp_wiring.py tests\test_aoi_context.py -q`.

## Integrated Acceptance Gate

After all tasks are integrated, run serially:

1. Root: `uv run --group dev pytest -q`, `uv run ruff check .`, and
   `uv run ruff format --check .`.
2. Agent app: `uv run --frozen --python 3.11 pytest tests -q`,
   `uv run ruff check`/`ruff format --check` on the owned app files.
3. Frontend: `npm run test:site-assessment` (waived by D11), read-only Biome
   lint, and `npm run build` (through `make app-frontend-check` if the host
   Make target is usable; otherwise direct equivalents). Do not add a
   TypeScript check.
4. Confirm baseline counts and any existing warnings in `STATE_52.md`; do not
   fix unrelated audit or lint findings.

No wave is complete until its targeted tests pass and each implementation
commit is locally integrated. The orchestrator owns full-suite validation;
workers run only their task's targeted commands.

## Conditional Dev-App Trial and Remote Boundaries

The final dev-app trial is not authorized by plan approval or local task
approval. After a separate explicit user approval to push/redeploy, verify on
`agent-fpac-soil-dev` and `mcp-fpac-soil-dev` that the question comes from the
validated tool, the interface shows registry-defined question/choices/
evaluation information, answer/comment/provenance records survive the
conversation, LESA is blocked until Confirm matches the answer set, missing
inputs show conservative maximums labelled assumed, and the output remains
undetermined/preliminary where required. Follow ADR 0016: do not assert that
AOI geometry is absent from chat/tool traces. Reply to Copilot review threads
only after separate explicit authorization. Report any push/redeploy or
review-thread work as blocked until authorized.
