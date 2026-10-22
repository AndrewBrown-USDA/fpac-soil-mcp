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
| 1 | 35.1.1 | Root Ruff excludes `apps/` | pending | | |
| 1 | 35.1.2 | Agent config module and chat system prompt | pending | | |
| 1 | 35.1.3 | Deployment config declarations | pending | | |
| 1 | 35.1.4 | App README FPAC section | pending | | |
| 2 | 35.2.1 | FPAC agent: model, prompt, reasoning, no template tool | pending | | |
| 3 | 35.3.1 | Connect `mcp-fpac-soil` in both handlers | pending | | |
| 4 | 35.4.1 | Full offline gates (serial) | pending | | |
| 5 | 35.5.1 | Grants, redeploy, 3-prompt live check (MANUAL) | pending | user / Apps page | |

## Wave gates

| Wave | App pytest | Root pytest (group) | ruff check . | ruff format --check . | Explicit apps/ ruff | Notes |
|---|---|---|---|---|---|---|
| 1 | | | | | | |
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
