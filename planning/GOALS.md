# Project Goals (`planning/GOALS.md`)

Last Updated: 2026-11-10
Source State: `planning/STATE_46.md`; `planning/MASTER_PLAN.md`; `planning/EXECUTION_PLAN_46.md`

## Current Milestone (Orchestration 46)

Waves 2 and 3 passed; the Wave 4 Criterion 2 evidence gate passed with
limitations. Task 46.4.2 is a five-run/two-worker manifest-only dry run, not
measured service performance: latency, failure, and retry metrics are null;
deployed `/mcp` and model-assisted results were not run. Wave 5 synchronizes
the evaluation and submission documentation. Final serial validation passed:
`make check` completed with 843 passed and 45 deselected, followed by
`make app-check` with 177 passed. `make test-eval` remains unrun pending Pi
provider authentication (`invalid_state`). The PR #79/CDL dependency and
adjacency deferral remain in force.

## Circled Goal (Active)

- **[G1]** A shared, versioned agent safety and evaluation contract governs the live agent app, FastMCP prompts, Pi evaluations, Databricks evaluations, and map summaries.
  - Why now: This is the highest-leverage bottleneck. It directly addresses the current scope-refusal gap, prevents unsafe non-prime farmland and siting interpretations, and defines the semantic contracts needed before performance evidence or broader MCP hardening can be trusted.
  - Exit criteria: One canonical policy is applied across all prompt surfaces; unrelated requests are refused; official determinations and siting recommendations are not produced; “not prime farmland” and urban overlap are not overinterpreted; outage/partial/unknown states remain explicit; adversarial tests and deterministic safety gates pass.
  - First action: add the shared policy text and versioned adversarial case schema to the execution plan’s Wave 1 scope, then implement the live/app prompt contract tests.

## Sequenced Goals (Dependency DAG)

- **[G2]** The shared adversarial evaluation corpus covers unrelated requests, official-determination requests, non-prime overinterpretation, relocation/site selection, urban exemption overclaims, missing data, partial outages, malformed inputs, prompt injection, privacy, and performance budgets.
  - Depends on: G1
- **[G3]** Deterministic scorers and harness predicates enforce refusal, prohibited-claim absence, semantic status, provenance, privacy non-echo, tool-call budgets, retry ceilings, and latency budgets.
  - Depends on: G2
- **[G4]** Public MCP tools expose strict Pydantic input contracts and structured, source-aware failure envelopes without changing the preliminary-authority boundary.
  - Depends on: G1
- **[G5]** The live map app preserves unknown/unmapped/partial/not-prime distinctions and prevents map/chat flows from implying suitability, exemption, clearance, or a preferred site.
  - Depends on: G1, G2
- **[G6]** Criterion 2 performance and reliability evidence reports reproducible inputs, environment, commit SHA, p50/p95/p99 latency, retries, failure rate, memory, repeated-run stability, bounded concurrency, and deployed transport results.
  - Depends on: G3, G4
- **[G7]** Evaluation and planning documentation publishes the test setup, inputs, results, limitations, and verification gates required for submission judging.
  - Depends on: G3, G5, G6
- **[G8]** PR #79 CDL integration is merged and validated before agricultural-land adjacency evaluation is expanded.
  - Depends on: existing PR #79 review/merge work

## Independent Backlog

- **[G9]** The agent-app map MVP remains deployable, tested, and documented with stable AOI session-context behavior.
- **[G10]** T2 evaluation against deployed `/mcp` reproduces applicable T1 cases with trace and provenance evidence.
  - Depends on: G3
- **[G11]** The MCP workbench exposes the shared adversarial cases and displays deterministic versus model-assisted results separately.
  - Depends on: G2, G3

## Deferred

- **[G12]** Additional agricultural-land adjacency sources and derived Criterion 2 scoring are expanded.
  - Trigger: PR #79/CDL integration is merged, validated, and the selected authoritative adjacency source is approved.
- **[G13]** Production map persistence, multiple AOIs, custom basemaps, and other M2/M4 features are implemented.
  - Trigger: G1, G5, and the current map contract are stable in deployed trials.

## Blocked / Pruned

- **[G14]** The agent issues official FPPA/LESA determinations, signs AD-1006/CPA-106, grants legal exemptions, or selects preferred alternatives.
  - Status: Pruned
  - Reason: The repository’s authority boundary permits preliminary screening and neutral comparison only.
- **[G15]** Criterion 2 performance claims are accepted without a reproducible benchmark artifact.
  - Status: Blocked / External Watch
  - Reason: Deployed latency and upstream reliability depend on external services and must be measured in the target environment.
