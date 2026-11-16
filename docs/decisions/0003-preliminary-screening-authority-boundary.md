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
official Land Evaluation scores, and legal exemption rulings. An automated
screening tool must clearly distinguish its machine-generated preliminary
estimates from binding agency actions to avoid users mistaking raw soil
attributes for official regulatory conclusions.

## Decision Drivers

* Legal liability: Presenting machine outputs as official NRCS determinations
  would be legally and professionally improper.
* User trust: Explicit boundaries prevent over-reliance on preliminary data.
* Regulatory framework: 7 CFR Parts 657 & 658 define who can issue formal
  FPPA determinations — this system is not among them.
* Consistency: The notice must appear in all primary screening responses.

## Considered Options

1. **Mandatory regulatory notice on all primary screening responses** —
   centralize `REGULATORY_NOTICE` in `constants.py`, embed it in primary
   Pydantic response models (`FarmlandClassificationResponse`,
   `PolygonFarmlandAnalysisResponse`, `CorridorFarmlandAnalysisResponse`,
   `PreliminaryLESAResponse`), enforce as policy via AGENTS.md operational
   rules.
2. **Disclaimer in README only** — document the limitation but not enforce it
   programmatically in responses.
3. **Per-tool opt-in notices** — let each tool decide whether to include a notice.

## Decision Outcome

Chosen option: **Mandatory regulatory notice on all primary screening
responses**, because it makes the authority boundary programmatically present
in every substantive soil-analysis output and establishes a clear policy for
new tools to follow.

### Consequences

* **Positive**: All primary screening response models carry a `regulatory_notice`
  field (`FarmlandClassificationResponse`, `PolygonFarmlandAnalysisResponse`,
  `CorridorFarmlandAnalysisResponse`, `PreliminaryLESAResponse`). This was
  established in EP1 and propagated through EP4, EP7, and EP17.
* **Positive**: AGENTS.md codifies this as a non-negotiable operational rule,
  ensuring any future contributor maintains the boundary.
* **Positive**: The watermarked/preliminary framing enables the system to
  calculate candidate scores (LE, SA, total LESA) without implying they are
  official agency determinations.
* **Negative**: Auxiliary reference responses (e.g., `FarmlandClassListResponse`,
  raw interpretation dictionaries) do not carry the notice field. The policy
  requires it on screening outputs; reference lookups are not screening results.
  Future tools producing screening-level outputs must include the notice.

## Validation & Compliance

Verbatim constraint in EXECUTION_PLAN_1: "Do not fabricate an FPPA
land-evaluation score, site-assessment score, or regulatory conclusion."
Enforced in `constants.py` REGULATORY_NOTICE, propagated through EP4, EP7,
EP17 verbatim constraints. Never relaxed across 207 commits.
