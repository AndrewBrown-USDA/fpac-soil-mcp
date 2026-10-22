# State 35 — Wire the `agent-fpac-soil-openai-sdk` Agent App to fpac-soil-mcp

Plan: `planning/EXECUTION_PLAN_35.md` · Template: `planning/PROMPT_TEMPLATE_35.md` · Branch: `feat/agent-app-fpac-mcp`

## Baseline (record before wave 1)

- [x] Branch `feat/agent-app-fpac-mcp` from `origin/main` `ca799b0`, with template cherry-picked as `58b5e89`; upstream unset (D1).
- [x] Tree clean apart from the Plan 35 artifacts and the research note; artifacts committed together with this file (`docs(planning):`, plan approved 2026-10-22). `apps/agent-fpac-soil-openai-sdk/uv.lock` stays untracked (H4).
- [x] Root offline suite with group: `UV_PROJECT_ENVIRONMENT=/tmp/fpac-venv PYTHONDONTWRITEBYTECODE=1 uv run --group eval-databricks pytest -p no:cacheprovider -q` → 496 passed, 24 deselected (2026-10-22)
- [x] App suite: `cd apps/agent-fpac-soil-openai-sdk && UV_PROJECT_ENVIRONMENT=/tmp/agent-venv uv run --python 3.11 pytest -p no:cacheprovider -q` → 6 passed
- [x] `uv run ruff check . --extend-ignore EXE002` → **105 errors, all in `apps/`** (clean with `--exclude apps`). Fixed by 35.1.1.
- [x] `uv run ruff format --check .` → **16 would reformat, all in `apps/`** (420 formatted with `--exclude apps`). Fixed by 35.1.1.
- [x] Model probe (5-token chat, as the user): `databricks-claude-sonnet-5-5` PERMISSION_DENIED (workspace-level); `databricks-gpt-5-6-luna` OK with `reasoning_effort="none"`; `databricks-claude-sonnet-4-5` OK.
- [x] Deployed app: git source `template/agent-fpac-soil-openai-sdk-1792601940628`, resources `experiment` only, SP ID 70416953425179 with no `CAN_USE` on `mcp-fpac-soil`.

## Wave board

| Wave | Task | Title | Status | Worker | Result |
|---|---|---|---|---|---|
| 1 | 35.1.1 | Root Ruff excludes `apps/` | done | orchestrator (inline) | `c4de9ec` |
| 1 | 35.1.2 | Agent config module and chat system prompt | done | orchestrator (inline) | `073d464` |
| 1 | 35.1.3 | Deployment config declarations | done | orchestrator (inline) | `c33a830` |
| 1 | 35.1.4 | App README FPAC section | done | orchestrator (inline) | `6b48342` |
| 2 | 35.2.1 | FPAC agent: model, prompt, reasoning, no template tool | done | orchestrator (inline) | `1fa62ac` |
| 3 | 35.3.1 | Connect `mcp-fpac-soil` in both handlers | done | orchestrator (inline) | `fa3961d` |
| 4 | 35.4.1 | Full offline gates (serial) | done | orchestrator (inline) | all green |
| 5 | 35.5.1 | Grants, redeploy, 3-prompt live check (MANUAL) | pending | user / Apps page | |

## Wave gates

| Wave | App pytest | Root pytest (group) | ruff check . | ruff format --check . | Explicit apps/ ruff | Notes |
|---|---|---|---|---|---|---|
| 1 | 32 passed | 496 passed, 24 deselected | All checks passed | 427 formatted, 0 reformat | 4 files clean | `apps/` absent from `--show-files`; `uv.lock` still untracked |
| 2 | 37 passed | 496 passed, 24 deselected | All checks passed | 428 formatted, 0 reformat | 2 template F841 in handlers (fixed by 35.3.1) | expected; see 35.2.1 |
| 3 | 46 passed | (run in wave 4) | All checks passed | 0 reformat | `agent.py` + wiring test clean | grep `system/ai\|get_current_time\|claude-sonnet-5-5` in `agent.py` → none |
| 4 | 46 passed | 496 passed, 24 deselected | All checks passed | 429 formatted, 0 reformat | 7 plan `.py` files clean | `git status`: only `apps/.../uv.lock` untracked (H4); same format count with `--exclude apps`, so `apps/` is not formatted from root |

## Live check (35.5.1)

| Prompt | No 403 | fpac tool call in trace | Limitation stated | Within 180 s | Trace ID |
|---|---|---|---|---|---|
| DISC-01 | | | | | |
| POINT-01 | | | | | |
| LESA-01 | | | | | |

## Task reports

<!-- Workers append `## <task-id>` sections here (<=15 lines each). -->

## 35.1.1
- Status: done (`c4de9ec`). `pyproject.toml` L48-49: comment + `extend-exclude = ["apps"]`.
- `ruff check . --extend-ignore EXE002` → All checks passed; `ruff format --check .` → 0 reformat.
- Explicit `apps/.../agent_server/history.py` → All checks passed (file is clean; H3 path behavior was already shown in recon with `start_app.py`).
- Deviations: none.

## 35.1.2
- Status: done (`073d464`). Created `agent_server/config.py` (63 lines), `agent_server/prompts/system_prompt.txt` (verbatim), `tests/conftest.py`, `tests/test_agent_config.py` (19 tests).
- App pytest `tests/test_agent_config.py tests/test_history_normalization.py` → 25 passed. Ruff check + format on 3 files → clean.
- Deviations: none. Timeout parse collects the failure, then raises one `ValueError` naming `FPAC_MCP_TIMEOUT_SECONDS`.
- Gotcha: root Ruff isort treats `agent_server` as third-party (no app `[tool.ruff]`), so it shares the import block with `pytest`/`agents` in app tests and in `agent.py`.
- Pre-existing: app pytest warns `Unknown config option: asyncio_mode` (not from this plan).

## 35.1.3
- Status: done (`c33a830`). `app.yaml` +6 lines (3 env). `databricks.yml`: app name L7 and prod L62, 3 env entries, `llm-endpoint` → luna, NOTE comment rewritten, `mcp_server` app resource. `.env.example` +5 lines. New `tests/test_deploy_config.py` (7 tests).
- App pytest `tests/test_deploy_config.py` → 7 passed. Ruff check + format → clean.
- Deviations: none. `manifest.yaml` untouched (J1).

## 35.1.4
- Status: done (`6b48342`). README +37 lines: `## FPAC Soil configuration` before `## Build with AI Assistance` (purpose + limitation, env table, grants, sonnet-5-5 note, deploy path, 180 s timeout).
- `grep -c "FPAC_MCP_URL\|AGENT_MODEL\|CAN_USE"` → 4.
- Deviations: the last README sentence (tools-unavailable behavior) describes K2/K3 and becomes true after 35.3.1.

## 35.2.1
- Status: done (`1fa62ac`). `agent.py`: removed `get_current_time`, `datetime`, `function_tool`; added `ModelSettings`, `Reasoning`, config imports, `TOOLS_UNAVAILABLE_NOTE`, and `create_agent` per K2. New `tests/test_agent_construction.py` (5 tests).
- App pytest `tests` → 37 passed.
- Deviations: also fixed import-block lint (UP035 `collections.abc.AsyncGenerator`; F401 unused `get_user_workspace_client`). Two template `F841 stack` errors remained in the handlers until 35.3.1, because handler edits were out of scope here.

## 35.3.1
- Status: done (`fa3961d`). `agent.py`: `init_mcp_server` → sync `init_fpac_mcp_server` + `FPAC_MCP_SERVER_NAME`; dropped `build_mcp_url` import; both handlers call a new private `_connect_fpac_agent(stack)` (connect, one INFO summary if unavailable, `create_agent(mcp_servers=..., tools_unavailable=...)`). New `tests/test_agent_mcp_wiring.py` (9 tests).
- App pytest `tests` → 46 passed. Ruff check + format clean; grep check prints nothing.
- Deviations: the 2-line SP-auth / health-check comment sits in the shared helper rather than being duplicated in each handler. Handler signatures, decorators, history normalization, and stream processing are unchanged.
- Gotcha for 35.5.1: if the agent says tools are unavailable, the app log has the `connect_healthy_mcp_servers` WARNING `MCP server 'fpac-soil-mcp' unavailable; continuing without it.` with a traceback, plus an INFO `MCP servers unavailable for this request: fpac-soil-mcp`. Check the `CAN_USE` grant first.

## PR review follow-up (Copilot)
- Duplicate warning: the handler summary is now `logger.info`; the health check keeps the single WARNING with traceback. Wiring test asserts exactly one INFO record from `agent_server.agent`.
- CI coverage: new Makefile targets `app-test` (`uv run --frozen --python 3.11 pytest tests -q` in the app dir), `app-lint` (Ruff on `agent.py`, `config.py`, `history.py`, `tests/`), `app-check`; new CI job `agent-app` runs `make app-check`. Template runtime files (`start_app.py`, `start_server.py`, `utils.py`, `app_diagnostics.py`) are not linted: 18 pre-existing findings, left unchanged.
- asyncio `exc_info=exc` in `scripts/app_diagnostics.py`: declined. `logging` has accepted an exception instance for `exc_info` since Python 3.5 and uses its `__traceback__`; verified on 3.12 outside an `except` block (traceback printed). File is unchanged template code.
- Results: app 46 passed via `make app-test`; app-owned files Ruff clean.

## 35.4.1
- Status: done. All gates green (see wave 4 row). Plan `.py` files under `apps/` linted explicitly: `agent.py`, `config.py`, `conftest.py`, and 4 test files.
- `git status --short` → only `?? apps/agent-fpac-soil-openai-sdk/uv.lock` (H4; the user decides whether to delete it).
- Next: push `git push -u origin feat/agent-app-fpac-mcp`, then 35.5.1 (manual).
