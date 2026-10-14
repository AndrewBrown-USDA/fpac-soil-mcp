---
id: "0003"
title: "Preliminary Screening Authority Boundary"
status: "Accepted"
date: 2026-09-16
authors:
  - "Andrew G. Brown"
supersedes: null
superseded_by: null
source_context: "EXECUTION_PLAN_1"
---

# 3. Preliminary Screening Authority Boundary

## Context and Problem Statement

The Farmland Protection Policy Act (FPPA) has formal determination procedures
administered by NRCS field staff involving signed forms (AD-1006, CPA-106),
official Land Evaluation scores, and legal exemption rulings. An AI-assisted
screening tool must clearly distinguish its machine-generated preliminary
estimates from binding agency actions to avoid users mistaking raw soil
attributes for official regulatory conclusions.

## Decision Drivers

* Legal liability: Presenting machine outputs as official NRCS determinations
  would be legally and professionally improper.
* User trust: Explicit boundaries prevent over-reliance on preliminary data.
* Regulatory framework: 7 CFR Parts 657 & 658 define who can issue formal
  FPPA determinations — this system is not among them.
* Consistency: The notice must appear in every tool response, not just some.

## Considered Options

1. **Mandatory regulatory notice in every response** — centralize `REGULATORY_NOTICE`
   in `constants.py`, embed it in every Pydantic response model, enforce via
   AGENTS.md operational rules.
2. **Disclaimer in README only** — document the limitation but not enforce it
   programmatically in responses.
3. **Per-tool opt-in notices** — let each tool decide whether to include a notice.

## Decision Outcome

Chosen option: **Mandatory regulatory notice in every response**, because it
makes the authority boundary programmatically enforceable, auditable, and
impossible to accidentally omit when adding new tools.

### Consequences

* **Positive**: The `REGULATORY_NOTICE` constant and its inclusion in all
  response envelopes was established in EP1 and propagated unchanged through
  EP4 (polygon), EP7 (corridor), EP17 (LESA), and all subsequent plans.
* **Positive**: AGENTS.md codifies this as a non-negotiable operational rule,
  ensuring any future contributor maintains the boundary.
* **Positive**: The watermarked/preliminary framing enables the system to
  calculate candidate scores (LE, SA, total LESA) without implying they are
  official agency determinations.
* **Negative**: Response payloads are slightly larger due to the repeated
  notice. This is negligible compared to the legal risk of omitting it.

## Validation & Compliance

Verbatim constraint in EXECUTION_PLAN_1: "Do not fabricate an FPPA
land-evaluation score, site-assessment score, or regulatory conclusion."
Enforced in `constants.py` REGULATORY_NOTICE, propagated through EP4, EP7,
EP17 verbatim constraints. Never relaxed across 207 commits.
