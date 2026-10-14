---
id: "0009"
title: "Resilient HTTP Client with Retry Architecture"
status: "Accepted"
date: 2026-09-17
authors:
  - "Andrew G. Brown"
supersedes: null
superseded_by: null
source_context: "EXECUTION_PLAN_4, EXECUTION_PLAN_7"
---

# 9. Resilient HTTP Client with Retry Architecture

## Context and Problem Statement

The server queries three independent federal APIs (USDA SDA, Census TIGERweb,
USDA NASS QuickStats), each with different reliability profiles, rate limits,
and error response formats. Government APIs are subject to intermittent outages,
slow responses, and transient HTTP errors. Each domain client needed retry logic,
timeout handling, and structured error responses, but duplicating this across
three clients would create maintenance burden and inconsistent error behavior.

## Decision Drivers

* Three federal APIs with different reliability characteristics.
* Transient HTTP errors (timeouts, 500s, connection resets) are common on
  government endpoints.
* Structured error handling needed for MCP tool responses (errors must be
  meaningful to AI assistants, not raw HTTP failures).
* DRY principle: retry/timeout logic should be written once.

## Considered Options

1. **Base `http_client.py` with domain-specific subclasses** — centralize
   retry logic, timeouts, and structured error handling in a base class;
   domain clients (`SDAClient`, `TigerwebClient`, `NassClient`) extend it
   with API-specific request formatting and response parsing.
2. **Per-client retry logic** — each client implements its own retry and
   timeout handling independently.
3. **External retry library (tenacity)** — use a third-party retry decorator
   library for all HTTP calls.

## Decision Outcome

Chosen option: **Base `http_client.py` with domain-specific subclasses**,
because it centralizes the retry/timeout/error pattern once while allowing each
client to own its request formatting, response parsing, and API-specific error
interpretation.

### Consequences

* **Positive**: Adding `NassClient` (EP7) and extending `TigerwebClient` for
  county boundaries required no changes to the base retry/timeout logic.
* **Positive**: All three clients produce consistent structured error responses
  that MCP tools can surface to AI assistants.
* **Positive**: The NASS client's graceful `UNAVAILABLE` fallback when the API
  key is not configured was implemented as a domain-specific concern on top of
  the shared error framework.
* **Negative**: The base client abstraction adds one inheritance level. This is
  a modest complexity cost for significant deduplication.

## Validation & Compliance

All three domain clients use mocked `httpx` transports in the offline test
suite, verifying retry behavior, timeout handling, and error response structure.
Live network tests (opt-in via `@pytest.mark.live_network`) validate actual
endpoint behavior. Evidence: `http_client.py` creation (EP4-7 era),
`sda_client.py`, `tigerweb_client.py`, `nass_client.py` hierarchy visible in
AGENTS.md.
