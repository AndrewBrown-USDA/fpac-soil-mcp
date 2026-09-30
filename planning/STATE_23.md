# STATE 23: Correct Generic Productivity Ratings and LESA Routing

## Baseline Checklist

- [x] `uv sync` environment available
- [x] Offline baseline: `uv run pytest -m "not live_network"` — 280 passed,
  12 deselected, 0 failed in 32.83s
- [ ] Targeted task tests pass
- [ ] `uv run ruff check .`
- [ ] `uv run ruff format --check .`
- [x] Live-network tests remain opt-in and are not a completion gate
- [x] Intentional breaking change recorded: remove `nccpi_rating` and
  `nccpi_class`; replace with generic fields plus rating provenance

## Wave Board

| Wave | Task | Status | Retry/escalation |
|---|---|---|---|
| 1 | 23.1.1 Generalizing productivity response fields | pending | 0 |
| 1 | 23.1.2 Defining rating provenance contract | pending | 0 |
| 2 | 23.2.1 Scoring requested polygon productivity indexes | pending | 0 |
| 2 | 23.2.2 Correcting LESA routing and normalization | pending | 0 |
| 3 | 23.3.1 Testing generic polygon ratings | pending | 0 |
| 3 | 23.3.2 Testing corridor routing and propagation | pending | 0 |
| 3 | 23.3.3 Testing LESA fallback and invalid indexes | pending | 0 |
| 3 | 23.3.4 Updating public rating documentation | pending | 0 |
| 4 | 23.4.1 Running complete offline verification | pending | 0 |

## Task Reports

<!-- Workers append reports here, each no more than 15 lines. -->

## Verification Record

- Base/plan commit: to be recorded when the plan is approved and committed.
- Full-suite owner: 23.4.1; workers must not run the full suite or
  repository-wide Ruff.
- Escalation rule: one targeted-test retry; second failure escalates to a
  mid-tier worker and increments the task's retry/escalation column.
