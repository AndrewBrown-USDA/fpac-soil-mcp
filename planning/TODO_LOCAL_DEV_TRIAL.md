# TODO

## Goal
Make the guided Site Assessment interview and confirmed-summary gate testable end to end locally (headless Python layer + local `/mcp`, optional full chat UI), with no push, deploy, or remote action.

## Tasks

### 1. Discover deployed shape
- [x] Read `AGENTS.md` (root and app), `planning/STATE_52.md`, app `app.yaml`/`databricks.yml`/`config.py`, `server.json`, `Dockerfile`; record how the agent resolves the MCP server (`FPAC_MCP_APP`/`FPAC_MCP_URL`) and that prod uses Streamable HTTP `/mcp`.
- [x] Check whether `make app-check` works on this Linux host (record result).

### 2. Local MCP server
- [x] Start with `MCP_TRANSPORT=http` on a free port; confirm `/health` and that `/mcp` lists the Site Assessment tools (`get_site_assessment_question`, `calculate_preliminary_lesa`, etc.).

### 3. Model and agent wiring
- [x] Probe `http://127.0.0.1:8090` (read-only, e.g. `/v1/models`) to confirm it is an OpenAI-compatible LLM server; ask before any real/workspace credential is used.
- [x] Determine how the app can use it (`AGENT_MODEL`/client base URL, `conftest.py` dummy creds) with test wiring only; if production code paths would need changes, stop and ask.
- [x] Define a deterministic stub-LLM fallback for CI-style headless runs (scripted tool calls) so the run does not need port 8090.
- [x] Investigate a full-UI local setup (`uv run start-app`, `FPAC_MCP_URL` -> local MCP, no Databricks auth); document feasibility and blockers, do not block on Playwright.

### 4. Scripted interview run (headless)
- [x] Drive: soil-first screening, Start/Skip, answers + comments, Confirm, then LESA via the agent gate and local `/mcp`.
- [x] Verify and log tool-call sequence for the six plan points (validated question/choices, answer records in history, LESA blocked until matching confirmation, assumed conservative maximums, undetermined/preliminary output, no claim that AOI geometry is absent from traces per ADR 0016).

### 5. Negative cases
- [x] LESA refused with no confirmation, mismatched answers, and a Criterion 7 fact + farm-acre pair; assert via call log that refusals happen before any MCP call.

### 6. Make repeatable
- [x] Add one command (`make trial-local` + script under `scripts/` or `eval/`) that starts its own MCP server on a free port, runs the scenario, and tears down.
- [x] Keep it out of the default offline path (opt-in marker/env var); add a short README note.
- [x] Run `make check` and app tests to confirm nothing regressed.

### 7. Report and commit
- [x] Add a section to `planning/STATE_52.md` (what runs locally, what can't and why, exact commands, local-vs-dev gaps) and tick this file.
- [x] Commit locally (no push): code/Makefile/README in one commit, planning docs in a separate `docs(planning):` commit; leave `planning/GOALS.md` and root `TODO.md` untouched.

## Notes
- No push, PR, deploy, review replies, or remote writes. No `.env`/credentials committed. No user-supplied SQL.
- Assumption: port 8090 is a local OpenAI-compatible LLM server; will verify in task 3.
- Stop and ask if a real Databricks/model credential is needed, production code must change, or a remote action is required.

## Discovered Tasks (needs approval)
- [x] (resolved, option A: served bands use `exclude_unset`) **Blocker found in task 4:** the live `/mcp` resource `fppa://site-assessment-criteria` differs from `src/fpac_soil_mcp/data/site_assessment.v1.json`. Every band carries `min: null`, `max: null`, `min_inclusive`/`max_inclusive`, `point_range`, and `representative_*_rule`. The app validator `_site_assessment_criteria_context` rejects this ("scoring band bounds are malformed"), so `_connect_fpac_agent` disables the interview. App tests pass only because their fixture loads the raw registry file. Fixing it needs a production-code change on one side: serve the resource with `exclude_none` (server), or make the validator tolerate null bounds (app). Stopped per the "production code path" rule.
- State: `apps/agent-fpac-soil-openai-sdk/scripts/trial_local.py` is drafted, using an offline stub workspace client (a real `WorkspaceClient()` hangs contacting a Databricks host). Tasks 1-2 are done. Task 3 is partly done: port 8090 is a llama.cpp server (Qwen3.6-35B, completion only) and is not wired.
