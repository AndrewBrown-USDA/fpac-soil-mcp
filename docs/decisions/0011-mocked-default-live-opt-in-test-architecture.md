---
id: "0011"
title: "Mocked Default, Live Opt-In Test Architecture"
status: "Accepted"
date: 2026-09-16
authors:
  - "Andrew G. Brown"
supersedes: null
superseded_by: null
source_context: "EXECUTION_PLAN_1, EXECUTION_PLAN_13"
---

# 11. Mocked Default, Live Opt-In Test Architecture

## Context and Problem Statement

The test suite must run reliably in CI/CD and local development without
depending on the availability of three external federal APIs (USDA SDA, Census
TIGERweb, USDA NASS QuickStats). At the same time, live integration tests are
needed to validate actual endpoint behavior, response format changes, and
network resilience. The test architecture had to support both modes with clear
separation.

## Decision Drivers

* Federal APIs are intermittently unavailable; CI must not fail due to external
  outages.
* Mocked tests using `httpx` transport mocks provide fast, deterministic,
  offline execution.
* Live tests are essential for validating real API behavior and catching format
  changes.
* The marker convention must be clear and consistent across all three API clients.

## Considered Options

1. **All tests mocked by default; live and agent-eval tests opt-in via pytest
   markers** — configure `pyproject.toml` `addopts` to exclude `live_network`
   and `agent_eval` markers by default; developers explicitly opt in for
   network or agent integration testing.
2. **All tests mocked by default; live tests in a separate test directory** —
   physical separation instead of marker-based separation.
3. **Record/replay with VCR cassettes** — record live API responses and replay
   them in CI, with periodic cassette refresh.

## Decision Outcome

Chosen option: **Mocked default with pytest marker opt-in**, because it keeps
live and mocked tests co-located for each module (easier to maintain), uses
pytest's native marker system, and requires zero additional tooling.

### Consequences

* **Positive**: The default test command (`uv run pytest`) uses the configured
  `addopts = "-m 'not live_network and not agent_eval'"` to exclude both live
  network and agent evaluation tests, running entirely offline with zero external
  dependencies. This was the verification gate at every wave boundary across all
  26 execution plans.
* **Positive**: Live tests validate actual SDA, TIGERweb, and NASS endpoint
  behavior and are explicitly documented as opt-in.
* **Positive**: The marker name evolved from `live_sda` to `live_network` in
  EP13 (commit `ba8a5540`) when TIGERweb and NASS clients were added, reflecting
  the multi-service scope without breaking the architecture.
* **Positive**: The `agent_eval` marker provides a separate opt-in gate for
  agentic integration tests that invoke external tooling, keeping them out of
  the default offline suite.
* **Negative**: Mocked tests can drift from actual API behavior if fixtures are
  not periodically refreshed. Live tests serve as the refresh mechanism.
* **Negative**: The two-tier system means a test can pass mocked but fail live;
  developers must run live tests when changing HTTP communication logic.

## Validation & Compliance

Default verification command configured in `pyproject.toml`:
`addopts = "-m 'not live_network and not agent_eval'"`. Codified in AGENTS.md:
`uv run pytest -m "not live_network"`. Used as gate at every wave boundary from
EP1 through EP26. Marker renamed from `live_sda` to `live_network` in EP13
(commit `ba8a5540`, 2026-09-22). Final offline suite: 309+ tests passing,
12 deselected (live + agent_eval).
