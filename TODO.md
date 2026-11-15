# TODO

## Goal
Allow explicitly opted-in MLflow tracing for the local chat app, persisted outside the repository and disabled by default.

## Tasks

### 1. Define local trace configuration
- [x] Add `FPAC_LOCAL_MLFLOW_TRACING=1` as the opt-in switch; tracing remains disabled in local mode unless set.
- [x] Configure MLflow's local file store at `~/.local/share/fpac-soil/mlflow`, with an explicit override path if needed, and document how to inspect traces.
- [x] Preserve deployed tracking/autolog behavior when `FPAC_LOCAL_DEV` is unset; retain the geometry privacy boundary for out-of-band map screening.

### 2. Verify and record
- [x] Add tests for default-off, opt-in local tracking URI, and unchanged non-local behavior.
- [x] Run app checks and a local trace smoke test that creates a trace, flushes it, and verifies it is searchable in the selected store. `make app-check`: 266 passed; smoke trace found in SQLite store.
- [x] Update the app README and planning state with safe handling warnings for prompts, tool arguments/results, geometry, and other sensitive contents.
- [x] Commit implementation and any planning records separately; archive this plan. No push or deploy. Implementation commits: `1d80f6a`, `1fe9e99`; smoke test and checks recorded in `planning/STATE_52.md`.

## Notes
- Branch: continue on `feature/local-dev-trial`; no worktree or branch switch.
- Planning artifacts are tracked and committed separately.
- Local trace setting: opt-in `FPAC_LOCAL_MLFLOW_TRACING=1`; default off.
- Default store: `~/.local/share/fpac-soil/mlflow`, outside repository and `/tmp`.
- No remote actions authorized.
