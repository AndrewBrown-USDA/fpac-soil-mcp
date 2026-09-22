# EXECUTION PLAN 13: Resolution of PR #6 Review Findings & Container Runtime Hardening

## Goal & Scope

### Goal
Resolve all five reviewer discussion comments on PR #6, reconcile container transport dispatch and health checks across `main.py` and `Dockerfile`, eliminate remaining legacy `live_sda` marker references across planning and test files, and verify the repository test baseline.

### In Scope
1. **Container Entrypoint & Transport Dispatch (`main.py`, `Dockerfile`)**:
   - Update `main.py` to support `http` and `streamable-http` transports in addition to `sse` and `stdio`, matching `app.py`.
   - Update `Dockerfile` to install `curl` in runtime stage for health checks, configure `HEALTHCHECK` for `http`/`sse` modes (with graceful exit on `stdio`), and align entrypoint to `["fpac-soil-mcp"]` / `["python", "main.py"]`.
2. **Test Marker Consistency & Legacy Cleanup (`tests/test_server.py`, `planning/`)**:
   - Rename `test_live_sda_*` test functions in `tests/test_server.py` to `test_live_network_*` to maintain 100% naming consistency with the `@pytest.mark.live_network` marker.
   - Update `planning/EXECUTION_PLAN_12.md`, `planning/STATE_12.md`, and `planning/tasks/12.2.2.todo.md` replacing `live_sda` references with `live_network`.
3. **Documentation & Validation Alignment (`README.md`)**:
   - Confirm and align container health check documentation and transport options in `README.md`.
4. **Full Test & Lint Verification**:
   - Run `uv run pytest -m "not live_network"`, `uv run ruff check .`, and `uv run ruff format --check .`.

### Out of Scope
- Modifying underlying MCP tools or spatial/algebraic calculation logic.
- Adding new endpoints or modifying public API contracts.
- External network test execution during local unit validation.

### Verbatim Constraints
- "Invoke the installed `fpac-soil-mcp` console script here (or update `main.py`) so the container uses the app's transport dispatch."
- "The PR and README describe a built-in container health check, but this image has no `HEALTHCHECK` instruction... add a conditional check (so the documented stdio override remains usable) or remove that claim."
- "Update this command to `live_network` before treating the plan as verified."
- "Update the command to `not live_network`."
- "Update it to `live_network` so the recorded validation command remains runnable."
- "Preserve all existing MCP tool signatures and green test baseline."

---

## Decision Log

- **2026-09-22**: `main.py` updated to mirror `app.py` transport dispatch logic (`sse`, `http`, `streamable-http`, fallback `stdio`).
- **2026-09-22**: `Dockerfile` runtime image updated with `curl` package and a conditional `HEALTHCHECK` instruction checking `http://localhost:${MCP_PORT:-8000}/health` when transport is network-based (`sse`/`http`), returning 0 if `MCP_TRANSPORT=stdio`.
- **2026-09-22**: Standardized all live test function names in `tests/test_server.py` to `test_live_network_*`.
- **2026-09-22**: Reconciled historical and plan 12 planning files (`EXECUTION_PLAN_12.md`, `STATE_12.md`, `tasks/12.2.2.todo.md`) to reference `live_network` instead of obsolete `live_sda`.
- **2026-09-22**: 2-wave execution structure: Wave 1 addresses code/runtime changes (`main.py`, `Dockerfile`, `tests/test_server.py`), Wave 2 synchronizes planning records, documentation, and final end-to-end verification.

---

## Technical Reconnaissance

- **Target Files**:
  - `main.py` (23 lines)
  - `Dockerfile` (42 lines)
  - `tests/test_server.py` (355 lines)
  - `planning/EXECUTION_PLAN_12.md`
  - `planning/STATE_12.md`
  - `planning/tasks/12.2.2.todo.md`
  - `README.md`
- **Test Command**: `uv run pytest -m "not live_network"`
- **Lint Command**: `uv run ruff check .`
- **Format Command**: `uv run ruff format --check .`
- **Baseline Status**: 192 passed, 10 deselected in offline test suite.

---

## Wave Table

| Wave | Task ID | Title | Files in Scope | Dependencies |
| --- | --- | --- | --- | --- |
| 1 | `13.1.1` | Align `main.py` and `Dockerfile` Container Runtime & Healthcheck | `main.py`, `Dockerfile` | None |
| 1 | `13.1.2` | Standardize Live Test Method Naming in `tests/test_server.py` | `tests/test_server.py` | None |
| 2 | `13.2.1` | Reconcile Planning & Documentation References to `live_network` | `planning/EXECUTION_PLAN_12.md`, `planning/STATE_12.md`, `planning/tasks/12.2.2.todo.md`, `README.md` | `13.1.1`, `13.1.2` |

---

## Task Specifications

### Task 13.1.1: Align `main.py` and `Dockerfile` Container Runtime & Healthcheck
- **Task ID**: `13.1.1`
- **Files in Scope**: `main.py`, `Dockerfile`
- **Dependencies**: None
- **Spec Prose**:
  1. In `main.py`, update `main()` to support `http` and `streamable-http` transports in addition to `sse`, using `settings.mcp_host` and `settings.mcp_port`, matching the logic in `app.py`.
  2. In `Dockerfile`, add `curl` installation in the runtime stage (`apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*`).
  3. In `Dockerfile`, add a `HEALTHCHECK` directive that tests `/health` via curl when `MCP_TRANSPORT` is `sse` or `http`, or exits 0 if `stdio`.
  4. Ensure `ENTRYPOINT ["fpac-soil-mcp"]` or `["python", "main.py"]` accurately dispatches all transports.
- **Constraints**: Do not alter `app.py` or `config.py`.
- **Grep Anchors**:
  - `settings.mcp_transport.lower()` in `main.py`
  - `HEALTHCHECK` in `Dockerfile`
- **Acceptance Command**: `uv run pytest tests/test_config.py tests/test_server.py -m "not live_network"`

---

### Task 13.1.2: Standardize Live Test Method Naming in `tests/test_server.py`
- **Task ID**: `13.1.2`
- **Files in Scope**: `tests/test_server.py`
- **Dependencies**: None
- **Spec Prose**:
  1. In `tests/test_server.py`, rename `test_live_sda_point_lookup_prime_farmland` to `test_live_network_sda_point_lookup_prime_farmland`.
  2. Rename `test_live_sda_mukey_lookup` to `test_live_network_sda_mukey_lookup`.
  3. Ensure all tests under `TestLiveSDAIntegration` or renamed `TestLiveNetworkIntegration` consistently use `@pytest.mark.live_network`.
- **Constraints**: Do not break offline mock assertions in `tests/test_server.py`.
- **Grep Anchors**:
  - `test_live_sda_` in `tests/test_server.py`
- **Acceptance Command**: `uv run pytest tests/test_server.py -m "not live_network"`

---

### Task 13.2.1: Reconcile Planning & Documentation References to `live_network`
- **Task ID**: `13.2.1`
- **Files in Scope**: `planning/EXECUTION_PLAN_12.md`, `planning/STATE_12.md`, `planning/tasks/12.2.2.todo.md`, `README.md`
- **Dependencies**: `13.1.1`, `13.1.2`
- **Spec Prose**:
  1. Update `planning/EXECUTION_PLAN_12.md` to replace all remaining `live_sda` test commands with `live_network`.
  2. Update `planning/STATE_12.md` lines 6 and 24 to replace `live_sda` with `live_network`.
  3. Update `planning/tasks/12.2.2.todo.md` lines 21 and 29 to replace `live_sda` with `live_network`.
  4. Verify `README.md` Docker container section accurately describes the `HEALTHCHECK` behavior and transport options.
- **Constraints**: Do not modify code under `src/`.
- **Grep Anchors**:
  - `not live_sda` in `planning/EXECUTION_PLAN_12.md`
  - `not live_sda` in `planning/STATE_12.md`
  - `not live_sda` in `planning/tasks/12.2.2.todo.md`
- **Acceptance Command**: `uv run pytest -m "not live_network" ; if ($?) { uv run ruff check . } ; if ($?) { uv run ruff format --check . }`
