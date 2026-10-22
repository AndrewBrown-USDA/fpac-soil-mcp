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
| 2 | 35.2.1 | FPAC agent: model, prompt, reasoning, no template tool | pending | | |
| 3 | 35.3.1 | Connect `mcp-fpac-soil` in both handlers | pending | | |
| 4 | 35.4.1 | Full offline gates (serial) | pending | | |
| 5 | 35.5.1 | Grants, redeploy, 3-prompt live check (MANUAL) | pending | user / Apps page | |

## Wave gates

| Wave | App pytest | Root pytest (group) | ruff check . | ruff format --check . | Explicit apps/ ruff | Notes |
|---|---|---|---|---|---|---|
| 1 | 32 passed | 496 passed, 24 deselected | All checks passed | 427 formatted, 0 reformat | 4 files clean | `apps/` absent from `--show-files`; `uv.lock` still untracked |
| 2 | | | | | | |
| 3 | | | | | | |
| 4 | | | | | | |

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
