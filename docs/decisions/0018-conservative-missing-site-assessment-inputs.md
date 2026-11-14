---
id: "0018"
title: "Conservative Bounds for Missing Site Assessment Inputs"
status: "Accepted"
date: "2026-11-13"
authors:
  - "Andrew G. Brown"
supersedes: null
superseded_by: null
source_context: "EXECUTION_PLAN_51"
---

# 18. Conservative Bounds for Missing Site Assessment Inputs

## Context and Problem Statement

Missing Site Assessment facts currently remain unscored. That makes an
incomplete assessment's zero-valued criterion points easy to misread as
substantive zero-point findings, while providing no conservative indication
of the greatest possible combined score given the missing information.
Missing data must remain distinguishable from measured or analyst-supported
facts, and must not yield a completed LESA score or threshold determination.

## Decision Drivers

* Missing or skipped criteria are not evidence and cannot support an actual
  criterion award.
* Users need a distinct conservative ceiling to understand the possible
  range while the actual result remains undetermined.
* All assumptions must derive from the existing Site Assessment registry and
  its project-type-specific maximum points; registry bands and CFR references
  remain unchanged.
* Preliminary screening must not be presented as an official determination,
  completed LESA score, or threshold outcome.

## Considered Options

1. **Keep missing values unscored without a bound** — maximally avoid inferred
   values but provide no upper-bound context.
2. **Treat missing values as actual maximum awards** — produces a number but
   improperly makes assumptions indistinguishable from evidence-based scoring
   and can imply a completed assessment.
3. **Record registry maxima as explicit assumptions and report a separate
   conservative bound** — retain actual points and completeness as
   undetermined/incomplete while separately computing an upper bound.

## Decision Outcome

Chosen option: **Record registry maxima as explicit assumptions and report a
separate conservative bound.** For omitted, unknown, unavailable, or skipped
Site Assessment criteria, the result records the applicable registry maximum
in `assumed_points`, labels the status `assumed (no evidence)`, and records
the assumption's policy provenance separately from evidence provenance.
Assumptions do not populate `awarded_points`, qualify as evidence, or mark the
input verified. The actual Site Assessment remains incomplete and the actual
total LESA score and threshold remain unevaluated. When Land Evaluation is
available, the response may expose `conservative_total_lesa_upper_bound` as a
separate upper bound; it is not an actual or official score.

Known evidence retains existing registry-driven scoring. No registry bands or
regulatory text are changed. This rule does not authorize estimating missing
facts, supplying invented evidence, or making official FPPA determinations.

## Consequences

* **Positive**: Missing criteria are not silently represented as zero-point
  evidence, and their assumed maximums are inspectable independently.
* **Positive**: The actual result remains incomplete, so an upper bound cannot
  be mistaken for an evaluated LESA score or 160-point threshold result.
* **Negative**: Consumers must distinguish the actual incomplete result from
  the optional conservative upper-bound field and its per-criterion
  assumptions.

## Validation & Compliance

Decision established in EXECUTION_PLAN_51. Focused tests verify that missing
and unknown inputs are labelled assumptions, preserve the incomplete actual
result, and expose a separate conservative bound while known evidence retains
its scoring behavior.
