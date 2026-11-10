# Orchestration 46 State

## Baseline

- **Repository:** `D:\workspace\fpac-soil-mcp`
- **Branch:** `planning/agent-safety-eval`
- **Plan date:** 2026-11-09
- **Offline baseline:** `uv run pytest -q -m "not live_network and not agent_eval"` ->
  764 passed, 45 deselected, 181 warnings.
- **Required gates:** targeted tests per task; final `make check`,
  `make app-check`, `make test-eval`; deployed measurements opt-in.
- **Active constraints:** ADR 0002, 0003, 0011, 0012, 0014, 0015, 0016, 0017.
- **Concurrency limit:** two workers maximum; shared gates run serially.

## Wave board

| Wave | Task | Status |
|---|---|---|
| 1 | 46.1.1 Harden prompt policy | pending |
| 1 | 46.1.2 Add policy assertions | pending |
| 1 | gate prompt policy | pending |
| 2 | 46.2.1 Add adversarial corpus | pending |
| 2 | 46.2.2 Add deterministic scorers | pending |
| 2 | gate adversarial evaluation | pending |
| 3 | 46.3.1 Harden MCP contracts | pending |
| 3 | 46.3.2 Preserve map semantics | pending |
| 3 | gate MCP/map safety | pending |
| 4 | 46.4.1 Instrument benchmarks | pending |
| 4 | 46.4.2 Run performance evidence | pending |
| 4 | gate Criterion 2 evidence | pending |
| 5 | 46.5.1 Synchronize documentation | pending |
| 5 | gate final validation | pending |

## Task Reports

<!-- Append one report per task, maximum 15 lines. -->

## Gate Evidence Convention

Each completed task/gate entry must record: status, exact command, pass/fail
counts, changed files or evidence artifact, commit/artifact identifier, and
dependency confirmation. A dependent task may not leave `pending` until its
prerequisite gate has an explicit passing entry.

## Deferred / Blocked

- **PR #79/CDL-dependent adjacency work:** deferred until PR #79 is merged,
  validated, and an authoritative adjacency source is approved.
- **Deployed `/mcp` measurements:** blocked when credentials, deployment, or
  upstream services are unavailable; record explicit unavailable fields rather
  than substituting local timings.
- **Map persistence, multiple AOIs, custom basemaps, and other M2/M4 work:**
  deferred until the current map contract and safety gate are stable.

## Gate Evidence Scaffold

| Gate | Status | Exact command | Counts/artifact | Dependency confirmation |
|---|---|---|---|---|
| Prompt policy | pending | - | - | - |
| Adversarial evaluation | pending | - | - | - |
| MCP/map safety | pending | - | - | - |
| Criterion 2 evidence | pending | - | - | - |
| Final validation | pending | - | - | - |
