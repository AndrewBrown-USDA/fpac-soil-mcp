# Prompt: local stand-in for the dev-app Site Assessment trial

Repo: `/home/andrew/work/fpac-soil-mcp`. The Site Assessment work from orchestration 52 is committed. Read `planning/STATE_52.md` (wave board and gate results) and `planning/EXECUTION_PLAN_52.md` ("Conditional Dev-App Trial and Remote Boundaries") first.

## Goal

Make the guided Site Assessment interview and its confirmed-summary gate testable end to end on this machine, as close to the deployed dev apps as possible without pushing or redeploying. The dev apps are `agent-fpac-soil-dev` (chat agent, `apps/agent-fpac-soil-openai-sdk/`) and `mcp-fpac-soil-dev` (MCP server, `/mcp` over Streamable HTTP). The real trial needs separate user approval, so this task must not push, deploy, or touch any remote.

## What the trial must prove (from the plan)

1. The question comes from the validated tool (`get_site_assessment_question`) with registry-defined choices and evaluation info.
2. Answer, comment, and provenance records survive the conversation (`site_assessment_answer` records in history).
3. LESA (`calculate_preliminary_lesa`) is blocked until Confirm matches the answer set (`site_assessment_confirmed_summary`, `confirmed: true`).
4. Missing inputs show conservative maximums labeled as assumed.
5. Output stays undetermined/preliminary.
6. Do not assert that AOI geometry is absent from chat or tool traces (ADR 0016).

## Constraints

- Read `AGENTS.md` at the repo root and in `apps/agent-fpac-soil-openai-sdk/` first.
- Run commands from the repo root, or the app directory where noted. Use `uv run ...` directly on this Linux host. `make app-check` failed on the earlier Windows host; check whether it works here before relying on it.
- Playwright was waived (plan D11). Do not block on it; use it only if it runs cheaply.
- No remote actions: no `git push`, no PR, no review-thread replies, no `databricks apps deploy`, no writes to the dev workspace. Read-only Databricks access is fine only if needed to find config.
- Do not commit `.env`, credentials, or tokens. No user-supplied SQL. Planning-artifact commits use `docs(planning):` and stay separate from code.
- `planning/GOALS.md` has an unstaged user edit. Leave it alone.

## Steps

1. **Discover the deployed shape.** Read `apps/agent-fpac-soil-openai-sdk/app.yaml` (or equivalent), the Databricks app config, `server.json`, and `Dockerfile`. Record how the agent finds the MCP server (env var, URL) and how the MCP server runs in production (Streamable HTTP on `/mcp`).
2. **Local MCP server.** Start it with `MCP_TRANSPORT=http` on a local port (`make run-http` or equivalent). Confirm `/health` and that `/mcp` lists the Site Assessment tools.
3. **Local agent app.** Find how the chat app starts locally (`agent_server/start_server.py`, `scripts/start_app.py`) and point it at the local MCP server. Work out what model/auth the agent needs; local Databricks auth is not configured. Decide whether a stub or fixture LLM can drive the interview or a real endpoint is required. Ask the user before wiring any real model or workspace credential.
4. **Scripted interview run.** Drive the interview through the chat API, or the browser harness at `eval/fpac_soil_mcp_harness/` if faster. Cover soil-first screening, Start/Skip, answers, Confirm, then LESA. Check each of the six points above and record the actual tool-call sequence and results.
5. **Negative cases.** Confirm LESA is refused with no confirmation, with mismatched answers, and with a Criterion 7 fact plus farm-acre pair. Confirm refusals occur before any MCP call (check the call log).
6. **Make it repeatable.** Put the scripted run behind one command (`make` target or `scripts/` entry) with a short README note. Keep it out of the default offline test path; use an opt-in marker or env var if it needs a running server.
7. **Report.** Add a section to `planning/STATE_52.md` (or a new `planning/` file if the gate needs its own state) covering what runs locally, what cannot be reproduced locally and why (auth, model endpoint, workspace-only config), the exact commands, and any local-vs-dev gap that could change the result.

## Stop and ask the user if

- A real Databricks or model credential is needed.
- Local setup needs a change to production code paths, not just test wiring.
- Reproducing dev behavior would require a remote action.
