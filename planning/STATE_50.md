# State 50: Layered Module Refactor (`G31`)

## Baseline (2026-11-14)
- `make check`: **952 passed, 3 skipped, 45 deselected** (`ruff check .` and `ruff format --check .` clean).
- Git working tree: clean.

## Wave Board

| Task | Wave | Status | Notes |
| :--- | :--- | :--- | :--- |
| `50.1.1` | 1 | done | Create `core/` package |
| `50.1.2` | 1 | done | Create `models/` package |
| `50.2.1` | 2 | done | Create `spatial/` package |
| `50.2.2` | 2 | done | Create `clients/` (http, tigerweb, nass, cdl) |
| `50.2.3` | 2 | done | Create `clients/sda/` package |
| `50.3.1` | 3 | done | Create `domain/` governance & reference modules |
| `50.3.2` | 3 | done | Create unified `domain/lesa.py` |
| `50.3.3` | 3 | done | Create `domain/{polygon,corridor}_analyzer.py` |
| `50.4.1` | 4 | done | Create `mcp/` surface & update `pyproject.toml`, `main.py` |
| `50.5.1` | 5 | done | Update `tests/` imports |
| `50.5.2` | 5 | done | Update `eval/` imports |
| `50.6.1` | 6 | done | Remove old flat modules & run `make check` + `make test-eval` |

## Task Reports

*(Appended as workers complete each task.)*

### `50.6.1` — report
- **Status**: done (re-scoped per EXECUTION_PLAN_50 D4).
- **Changes**: removed 4 `try/except ImportError` fallbacks to flat modules in `clients/sda/client.py`, `clients/sda/sdv_registry.py`, `clients/tigerweb.py`, `domain/lesa.py`; deleted 25 flat modules plus `tools/`, `resources/`, `prompts/` under `src/fpac_soil_mcp/`.
- **Code commits**: `07e3753` refactor(clients): import layered modules directly without flat fallbacks; `1771361` refactor: remove superseded flat modules.
- **Verification**:
  - `uv run python -c "from fpac_soil_mcp.mcp.app import create_mcp_server; create_mcp_server()"` → ok.
  - Stale-path grep over `src tests eval main.py pyproject.toml` → 0 hits.
  - `make check` → 952 passed, 3 skipped, 45 deselected (matches baseline).
  - `make test-eval PYTHON="uv run python"` → 38 passed, 0 failed.
- **Deviation**: `make test-eval` fails with plain `make` because the Makefile defaults `PYTHON ?= python` (system interpreter, no package). Same default on `main`; not changed here. Run with `PYTHON="uv run python"`.
- **Gotchas**: none for later tasks; orchestration 50 has no remaining waves.

