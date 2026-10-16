---
id: "0010"
title: "Public Payload PII Detection & Sanitization"
status: "Accepted"
date: 2026-09-17
authors:
  - "Andrew G. Brown"
supersedes: null
superseded_by: null
source_context: "EXECUTION_PLAN_4; EXECUTION_PLAN_29 eval-retention scope"
---

# 10. Public Payload PII Detection & Sanitization

## Context and Problem Statement

The FPAC Soil MCP Server processes user-submitted request payloads that should
contain only public/operational project fields (coordinates, geometry, project
parameters). However, users or upstream systems might inadvertently include
personally identifiable information (PII) such as names, email addresses, phone
numbers, or Social Security numbers. Section 1619 of the Food, Conservation,
and Energy Act of 2008 (7 U.S.C. § 8791) requires protection of information
provided by agricultural producers to USDA. A dedicated module was needed to
detect and reject or sanitize prohibited personal data fields in request
payloads.

## Decision Drivers

* 7 U.S.C. § 8791 (Section 1619) requires protection of producer information.
* The server should not silently pass PII through to external API queries or
  include it in response payloads.
* Detection must be centralized and auditable, not scattered across tool
  implementations.
* The server processes public soil data; the PII risk is in user-submitted
  request fields, not in SDA/TIGERweb/NASS responses.

  This decision's public/production scope is distinct from the supported
  evaluation-harness exception: an operator may explicitly opt in to retaining
  raw local eval artifacts outside the repository for exact interrogation. That
  exception is governed by `planning\CAPTURE_CONTRACT_29.md`; it is not a public
  payload, production logging, or a relaxation of this decision.

## Considered Options

1. **Dedicated `privacy.py` module for PII field detection and sanitization** —
   maintain a frozen set of prohibited personal field-name patterns (email,
   phone, SSN, names, addresses), provide `validate_public_payload()` and
   `sanitize_public_payload()` functions that recursively inspect request
   payloads and reject or strip prohibited fields.
2. **Per-tool input validation** — each tool checks its own inputs for PII.
3. **No PII detection** — document the limitation in README only.

## Decision Outcome

Chosen option: **Dedicated `privacy.py` module**, because it makes PII
detection centralized, auditable, testable, and available as an explicit
validation call for any tool or workflow that processes user-submitted payloads.

The evaluation harness may separately retain raw evidence only when the
operator explicitly opts in, receives a sensitive-data warning, and uses a
repository-external root. Raw artifacts are prohibited in repository-local
paths and checked-in fixtures. This exception preserves exact local eval
interrogation; it does not pass unsanitized data through public or production
payloads.

### Consequences

* **Positive**: `PROHIBITED_PERSONAL_KEY_PATTERNS` provides a comprehensive
  frozen set of prohibited field names (email, phone, SSN, tax ID, names,
  addresses — 23 patterns). `validate_public_payload()` returns detected paths;
  `assert_public_payload()` raises `ProhibitedPersonalDataError`;
  `sanitize_public_payload()` returns a deep copy with prohibited fields removed.
* **Positive**: AGENTS.md Operational Rules reference `privacy.py` explicitly,
  ensuring future contributors are aware of the requirement.
* **Positive**: The module remained stable after initial creation — no
  remediation cycles required.
* **Negative**: The module detects PII by field name pattern matching, not by
  content analysis. A field named `notes` containing a phone number would not
  be caught. This is a practical trade-off for performance and simplicity.
* **Negative**: Coordinate privacy (preventing inference of producer locations
  from submitted AOI geometries) is a policy aspiration documented in AGENTS.md
  but is not implemented as automated enforcement in this module. Coordinate
  handling remains governed by operational rules rather than programmatic
  redaction.
* **Scoped exception**: Explicitly enabled local eval retention can contain
  sensitive prompt, tool, provider, or model data. Operators must protect and
  clean up the external artifacts. Bounded diagnostic copies may be truncated,
  but complete in-memory evaluation evidence remains distinct from those
  copies. No raw eval artifact may be committed or used as a repository-local
  fixture.

## Validation & Compliance

Privacy module referenced in AGENTS.md Operational Rules: "Enforce Section 1619
and coordinate privacy protections via `privacy.py` where agricultural producer
data or sensitive locations are processed." Module provides
`validate_public_payload()`, `assert_public_payload()`, and
`sanitize_public_payload()` for explicit integration into tool workflows.
These public/production guarantees remain in force regardless of eval
retention mode; the external raw-artifact exception is documented in
`planning\CAPTURE_CONTRACT_29.md`.
