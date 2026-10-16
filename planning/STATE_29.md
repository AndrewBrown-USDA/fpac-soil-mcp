# Orchestration 29 State

## Baseline checklist

- [ ] `git status --short` recorded before Wave 1
- [ ] `uv run pytest -m "not live_network and not agent_eval" -q`
- [ ] `uv run pytest eval\test_agent_eval.py -m "not agent_eval" -q`
- [ ] `uv run ruff check .`
- [ ] `uv run ruff format --check .`
- [ ] Existing PR #22 review findings and ADR-0010 scope recorded
- [ ] Pi availability and live/agent-eval prerequisites checked
- [ ] Live/agent-eval shared-port and serial-execution constraints recorded

### Baseline results

| Check | Date | Result | Notes |
|---|---|---|---|
| `git status --short` | pending | pending | Record existing changes and untracked planning artifacts |
| Offline pytest | pending | pending | `uv run pytest -m "not live_network and not agent_eval" -q` |
| Eval pytest | pending | pending | `uv run pytest eval\test_agent_eval.py -m "not agent_eval" -q` |
| Ruff check | pending | pending | `uv run ruff check .` |
| Ruff format | pending | pending | `uv run ruff format --check .` |
| Pi/live prerequisites | pending | pending | Record availability, credentials, network, and port conditions |

## Closure checklist

- [ ] Targeted review-regression tests pass
- [ ] Offline project suite passes
- [ ] Ruff check passes
- [ ] Ruff format check passes
- [ ] `git diff --check` passes
- [ ] Raw artifacts remain outside the repository and no raw fixture is tracked
- [ ] Live/agent-eval validation ran serially and passed, or the exact environmental block is recorded

## Wave board

| Task | Wave | Status | Worker | Notes |
|---|---:|---|---|---|
| 29.1.1 | 1 | pending | — | Define eval raw-retention exception and update ADR-0010 |
| 29.2.1 | 2 | pending | — | Fix runner behavior for all six PR #22 findings |
| 29.3.1 | 3 | pending | — | Add deterministic review-regression tests |
| 29.4.1 | 4 | pending | — | Document operation and record closure verification |

## Task reports

<!-- Worker reports are appended below, one section per task, <=15 lines. -->
