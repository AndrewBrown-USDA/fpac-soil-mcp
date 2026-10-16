# Orchestration 29 State

## Baseline checklist

- [x] `git status --short` recorded before Wave 1: clean after planning commit
- [x] `uv run pytest -m "not live_network and not agent_eval" -q`: 303 passed, 14 deselected
- [x] `uv run pytest eval\test_agent_eval.py -m "not agent_eval" -q`: 17 passed, 2 deselected
- [x] `uv run ruff check .`: all checks passed
- [x] `uv run ruff format --check .`: 349 files already formatted
- [x] Existing PR #22 review findings and ADR-0010 scope recorded in `EXECUTION_PLAN_29.md`
- [ ] Pi availability and live/agent-eval prerequisites checked
- [x] Live/agent-eval shared-port and serial-execution constraints recorded

### Baseline results

| Check | Date | Result | Notes |
|---|---|---|---|
| `git status --short` | 2026-10-15 | clean | Baseline taken after planning commit `a7cec87` |
| Offline pytest | 2026-10-15 | 303 passed, 14 deselected | `uv run pytest -m "not live_network and not agent_eval" -q` |
| Eval pytest | 2026-10-15 | 17 passed, 2 deselected | `uv run pytest eval\test_agent_eval.py -m "not agent_eval" -q` |
| Ruff check | 2026-10-15 | passed | `uv run ruff check .` |
| Ruff format | 2026-10-15 | passed | `uv run ruff format --check .` |
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
| 29.1.1 | 1 | done | 29.1.1-retention-contract-execution | Define eval raw-retention exception and update ADR-0010 |
| 29.2.1 | 2 | pending | — | Fix capture core for path, bounds, classification, and finalization |
| 29.2.2 | 3 | pending | — | Surface CLI capture diagnostics |
| 29.3.1 | 4 | pending | — | Add deterministic review-regression tests |
| 29.4.1 | 5 | pending | — | Document operation and record closure verification |

## Task reports

<!-- Worker reports are appended below, one section per task, <=15 lines. -->

### 29.1.1 — Defining the eval retention exception

- Status: complete.
- Changed only `docs\decisions\0010-public-payload-pii-detection-and-sanitization.md`,
  `planning\CAPTURE_CONTRACT_29.md`, this TODO, and this state file.
- Documented explicit opt-in raw retention, external repository-independent
  roots, safe identifiers, operator warnings/protection/cleanup, sanitized
  fixtures, and prohibited repository-local raw artifacts.
- Preserved public/production `privacy.py`, Section 1619, and payload
  sanitization requirements; bounded-copy truncation is distinct from complete
  evaluation evidence.
- Command: `rg -n "eval|raw|opt-in|external|repository|production|fixture|sanitize|retention" docs\decisions\0010-public-payload-pii-detection-and-sanitization.md planning\CAPTURE_CONTRACT_29.md`
- Result: passed; all required anchors and boundaries were present.
- Deviations: none. No runtime code or tests changed.
- Dependent-task gotchas: 29.2.x must enforce the documented external-root,
  identifier-safety, opt-in, and complete-evidence/bounded-copy boundaries;
  raw artifacts remain outside the repository.
