---
id: "0001"
title: "FastMCP Server Framework & src-Layout Package Structure"
status: "Accepted"
date: 2026-09-16
authors:
  - "Andrew G. Brown"
supersedes: null
superseded_by: null
source_context: "EXECUTION_PLAN_1"
---

# 1. FastMCP Server Framework & src-Layout Package Structure

## Context and Problem Statement

The FPAC Soil MCP Server needed a Model Context Protocol (MCP) framework capable
of exposing soil-query tools, regulatory resources, guided prompts, and HTTP
health routes to assistants. The project was bootstrapped from a GSA MCP
hackathon template that already used FastMCP, but the long-term framework choice
and package layout had to accommodate a multi-phase roadmap spanning point
queries, polygon analysis, multi-county corridor partitioning, and LESA scoring.

## Decision Drivers

* Must support MCP tools, resources, prompts, and HTTP routes in a single server.
* Must integrate cleanly with `uv`, `pyproject.toml`, and Python >=3.11.
* Must allow modular registration so domain teams can add tools independently.
* GSA hackathon template already provided a proven FastMCP scaffold.

## Considered Options

1. **FastMCP with modular registration and `src/` layout** — adapt the GSA
   template, place all code under `src/fpac_soil_mcp/`, expose domain via
   `register_tools()`, `register_resources()`, `register_prompts()`,
   `register_routes()` functions consumed by a single `create_mcp_server()`
   factory.
2. **Raw MCP SDK with flat package layout** — use the low-level MCP Python SDK
   directly, organize code at the repository root without a `src/` directory.
3. **LangChain / LangServe wrapper** — wrap soil logic in LangChain tools and
   expose via LangServe HTTP, translating to MCP externally.

## Decision Outcome

Chosen option: **FastMCP with modular registration and `src/` layout**, because
it provided immediate MCP compliance, preserved the proven GSA template patterns,
and established a clean registration boundary between domain modules and the
server surface.

### Consequences

* **Positive**: The modular registration pattern (`register_tools(mcp)` etc.)
  proved stable across all 26 execution plans — zero architectural refactoring of
  the registration layer. New tools (polygon, corridor, LESA) were added by
  implementing domain logic in separate modules and wiring a single function call.
* **Positive**: The `src/` layout prevented import ambiguity and kept test
  fixtures cleanly separated from production code.
* **Negative**: FastMCP's opinionated conventions required learning its decorator
  patterns, but this was a one-time cost paid in EP1.
* **Neutral**: The `src/` layout added one directory level compared to flat, but
  this is standard Python packaging practice.

## Validation & Compliance

Validated through 207 commits across 26 plans with no registration architecture
changes. Commit evidence: `ca02c890` (Initial commit, 2026-09-16).
