# Research: Agent Safety, MCP Design, and Criterion 2/3 Evaluation

Date: 2026-11-09

## Decision Summary

The highest-leverage next goal is a shared, versioned, test-enforced agent
safety and evaluation contract. Current prompts preserve preliminary-screening
limitations but do not explicitly refuse unrelated requests, prohibit project
siting/relocation recommendations, or explain that “not prime farmland” is only
a soil-inventory classification. Databricks evaluation documentation also
defers scope-refusal cases.

## Current Strengths

- Production and evaluation prompts already prohibit fabricated values and
  distinguish preliminary screening from official FPPA/LESA determinations.
- MCP registration is centralized, and T0 checks manifest/runtime parity,
  schemas, notices, and selected invalid inputs.
- Pi handles startup errors, malformed output, timeouts, retries, and partial
  artifacts.
- The app has fail-closed MCP availability behavior and geometry-free,
  allowlisted map summaries.
- Authority models distinguish machine estimates, analyst proposals, agency
  approval, and NRCS official values.

## Priority Gaps

1. No explicit unrelated-request refusal contract.
2. No explicit non-prime farmland or urban-overlap anti-overinterpretation rule.
3. No deterministic semantic scorer for prohibited claims or neutral comparison.
4. Public MCP inputs include loosely typed dictionaries and arbitrary strings.
5. Some tool failures remain generic rather than structured and source-aware.
6. Map classification fallback can visually treat unrecognized text as
   `not_prime`.
7. Criterion 2 has no committed p50/p95/memory/repeated-run/load/deployed
   evidence package.

## Canonical Policy Requirements

The policy must require:

- FPPA/soil-screening scope only;
- refusal of unrelated work and official determinations;
- exact preservation of conditional and unknown classifications;
- no inference from “not prime farmland” to suitability, exemption, safety,
  low impact, or preferred siting;
- urban intersection as screening evidence, never automatic exemption;
- neutral reporting of user-supplied alternatives without choosing one;
- explicit disclosure of tool failure, no data, partial coverage, and
  unavailable sources;
- untrusted treatment of user metadata and tool-result free text;
- no estimates or invented values.

## Evaluation Evidence

The adversarial corpus should include unrelated requests, official form/signing
requests, non-prime inference, relocation, corridor choice, urban exemption,
conditional classes, missing values, MCP outages, partial source outages,
malformed geometry, prompt injection, privacy non-echo, and repeated
multi-county performance.

Release gates should be deterministic. Model-judge results and deployed
performance should be published as separate evidence tiers with exact inputs,
environment, prompt/eval versions, commit SHA, latency percentiles, retry and
failure counts, and known limitations.

## Source References

- `planning\EXECUTION_PLAN_45.md`
- `planning\MASTER_PLAN.md`
- `eval\databricks\README.md`
- `eval\databricks\scorers.py`
- `eval\pi\run_evals.py`
- `eval\eval_cases.v1.json`
- `eval\prompt_test_cases.json`
- `apps\agent-fpac-soil-openai-sdk\agent_server\prompts\system_prompt.txt`
- `apps\agent-fpac-soil-openai-sdk\agent_server\geo.py`
- `src\fpac_soil_mcp\authority.py`
- `src\fpac_soil_mcp\constants.py`
