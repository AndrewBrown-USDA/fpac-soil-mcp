# TODO

## Goal
Enable a full local chat-UI and real-model Site Assessment trial against the local MCP server without Databricks authentication, with optional live USDA SDA LESA verification.

## Tasks

### 1. Map local runtime and auth initialization
- [x] Trace `start-app`, agent server startup, model client construction, and MCP client initialization to identify Databricks-authenticated code paths and current local configuration.
- [x] Define the explicit environment-variable bypass behavior: `FPAC_LOCAL_DEV=1` selects an OpenAI-compatible local model endpoint and an explicit local `FPAC_MCP_URL`; default unset behavior remains Databricks-backed, and local mode must fail closed instead of using deployed defaults.

### 2. Implement local-only wiring
- [x] Implement the approved bypass in the smallest appropriate app configuration/startup seams; preserve default deployed behavior when the flag is unset.
- [x] Add tests proving bypass mode uses the configured local model and MCP endpoint without constructing Databricks workspace credentials, and unset mode preserves current behavior.
- [x] Document required environment variables and commands for starting the local MCP server, llama.cpp, and chat UI.

### 3. Exercise the chat UI and genuine model
- [ ] Run the local chat UI and use llama.cpp on port 8090 to exercise soil screening, interview Start/Skip, resource-backed questions, answer/comment records, Confirm/Edit, and LESA gating through real conversation turns.
- [ ] Capture pass/fail evidence for model-generated numeric answers, source/verification fields, and structured confirmation matching; fix only failures within this plan and add regression tests.
- [ ] Add or update a repeatable browser/UI test for the covered interview and confirmation flow, using existing frontend test dependencies.

### 4. Verify live MCP outcomes
- [ ] Exercise at least one refused LESA request and confirm the refusal causes no LESA MCP call; exercise one matching confirmed-summary success path against the local MCP server.
- [ ] When external network access is available, verify the real USDA SDA LESA success path and record the response status and limitations; keep network-dependent checks opt-in and distinct from offline tests.
- [ ] Run relevant root/app/frontend checks and review the complete diff.

### 5. Record and close
- [ ] Record exact setup/run commands, environment-variable semantics, observed model/UI outcomes, live USDA result or network limitation, and remaining gaps in `planning/STATE_52.md`.
- [ ] Mark verified tasks complete and archive this plan to the next available `planning/TODO_YYYYMMDD-N.md`.
- [ ] Make focused local commits for verified implementation and separate `docs(planning):` commits for the approved plan/status/archive; do not push or perform remote actions.

## Notes
- Branch: continue on clean `feature/local-dev-trial`; do not switch branches or create a worktree.
- Planning artifacts are tracked and committed separately with `docs(planning):` commits.
- Target local model is referred to only as llama.cpp on port 8090; do not assume a particular model or capability before probing it.
- Live USDA SDA testing is requested, but must remain clearly network-dependent and opt-in. No push, deployment, or other remote repository action is authorized.
- The bypass is explicit and local-only; it must not cause fallback to deployed MCP/model services or alter normal deployed behavior.

## Discovered Tasks
- [x] Route slash-containing local model IDs through the Agents SDK's explicit OpenAI provider prefix; add a regression test and verify with the llama.cpp model ID returned by `/v1/models`. The first real agent request failed with `Unknown prefix` because the SDK parsed the filesystem path in the model ID as a provider name. Verified by live model-backed UI tool call; commit `d879ef6`.
- [x] Add a synthetic frontend session only when `FPAC_LOCAL_DEV=1`, so the chat UI can submit real requests without a Databricks browser session; test that normal auth is unchanged when the flag is unset and document the local-only boundary in ADR 0015. Browser probing reached the UI but real chat API calls returned 401 without an authenticated session. Local session/proxy used successfully; tests pass; commit `01bfe44`.
