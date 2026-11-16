---
id: "0009"
title: "Shared HTTP Request Helper with Retry Composition"
status: "Accepted"
date: 2026-09-21
authors:
  - "Andrew G. Brown"
supersedes: null
superseded_by: null
source_context: "EXECUTION_PLAN_10"
---

# 9. Shared HTTP Request Helper with Retry Composition

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
  meaningful to assistants, not raw HTTP failures).
* DRY principle: retry/timeout logic should be written once.

## Considered Options

1. **Shared `execute_http_request_with_retry()` function in `http_client.py`** —
   a standalone function handling retry logic, exponential backoff, timeout
   management, and structured error types. Domain clients call this function
   (composition), owning their own request formatting and response parsing.
2. **Base HTTP client class with domain-specific subclasses** — centralize
   retry logic in a base class; domain clients inherit from it.
3. **External retry library (tenacity)** — use a third-party retry decorator
   library for all HTTP calls.

## Decision Outcome

Chosen option: **Shared function via composition**, because it provides the
retry/timeout/error pattern without imposing an inheritance hierarchy on
domain clients that have fundamentally different request shapes (POST with
SQL payloads for SDA, GET with query parameters for TIGERweb and NASS).

### Consequences

* **Positive**: Adding `NassClient` (EP7) and extending `TigerwebClient` for
  county boundaries required no changes to the shared retry/timeout logic —
  each client calls `execute_http_request_with_retry()` with its own parameters.
* **Positive**: All three clients produce consistent structured error types
  (`HttpRequestError`, `HttpStatusError`) that MCP tools can surface.
* **Positive**: The NASS client's graceful `UNAVAILABLE` fallback when the API
  key is not configured was implemented as domain-specific logic around the
  shared function, not a special case in the retry layer.
* **Negative**: Each domain client must independently construct the correct
  `execute_http_request_with_retry()` call signature. This is a modest
  duplication cost for the flexibility of composition over inheritance.

## Validation & Compliance

All three domain clients use mocked `httpx` transports in the offline test
suite, verifying retry behavior, timeout handling, and error response structure.
Live network tests (opt-in via `@pytest.mark.live_network`) validate actual
endpoint behavior. Shared helper extracted in EP10 (commit `d1e88d3`); client
adoption in `41debf4`. Referenced in AGENTS.md: domain clients "base HTTP
communication on `http_client.py`."
