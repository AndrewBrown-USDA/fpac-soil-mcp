# State 50: Layered Module Refactor (`G17`)

## Baseline (2026-11-14)
- `make check`: **952 passed, 3 skipped, 45 deselected** (`ruff check .` and `ruff format --check .` clean).
- Git working tree: clean.

## Wave Board

| Task | Wave | Status | Notes |
| :--- | :--- | :--- | :--- |
| `50.1.1` | 1 | pending | Create `core/` package |
| `50.1.2` | 1 | pending | Create `models/` package |
| `50.2.1` | 2 | pending | Create `spatial/` package |
| `50.2.2` | 2 | pending | Create `clients/` (http, tigerweb, nass, cdl) |
| `50.2.3` | 2 | pending | Create `clients/sda/` package |
| `50.3.1` | 3 | pending | Create `domain/` governance & reference modules |
| `50.3.2` | 3 | pending | Create unified `domain/lesa.py` |
| `50.3.3` | 3 | pending | Create `domain/{polygon,corridor}_analyzer.py` |
| `50.4.1` | 4 | pending | Create `mcp/` surface & update `pyproject.toml`, `main.py` |
| `50.5.1` | 5 | pending | Update `tests/` imports |
| `50.5.2` | 5 | pending | Update `eval/` imports |
| `50.6.1` | 6 | pending | Remove old flat modules & run `make check` + `make test-eval` |

## Task Reports

*(Appended as workers complete each task.)*
