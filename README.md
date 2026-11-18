# FPAC Soil MCP Server

[![CI](https://github.com/AndrewBrown-USDA/fpac-soil-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/AndrewBrown-USDA/fpac-soil-mcp/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastMCP](https://img.shields.io/badge/FastMCP-2.0+-green.svg)](https://github.com/jlowin/fastmcp)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An [MCP](https://modelcontextprotocol.io/) server that lets compatible assistants query USDA Natural Resources Conservation Service (NRCS) soil data, USDA National Agricultural Statistics Service (NASS) land-cover and agricultural data, and U.S. Census boundaries for preliminary **Farmland Protection Policy Act (FPPA)** screening.

---

## Table of Contents

- [Overview](#overview)
- [Architecture & Data Flow](#architecture--data-flow)
- [Features](#features)
- [Data Sources](#data-sources)
- [FPPA Regulatory Scope & Limitations](#fppa-regulatory-scope--limitations)
- [Installation & Setup](#installation--setup)
- [Execution Modes](#execution-modes)
- [Standard MCP Client Configuration](#standard-mcp-client-configuration)
- [Tool Reference](#tool-reference)
- [Resources, Prompts & HTTP Routes](#resources-prompts--http-routes)
- [Configuration](#configuration)
- [For Contributors](#for-contributors)
- [License](#license)

---

## Overview

Federal projects and environmental reviews may need preliminary information about **Prime Farmland**, **Unique Farmland**, or **Farmland of Statewide or Local Importance**. This MCP server lets compatible clients query official soil and related public datasets using a point, map-unit key, project area, or corridor.

The server reports source data and screening context to support review. It does not replace consultation with USDA NRCS or make an official FPPA determination.

---

## Architecture & Data Flow

The server exposes MCP tools, resources, and guided prompts through FastMCP. Tool handlers validate MCP inputs, coordinate domain and spatial operations, and call dedicated clients for USDA and Census services. Responses retain source provenance, coverage, and screening limitations. HTTP deployments also expose `/health` and `/meta`; these routes are separate from the MCP tool surface.

The implementation is organized into transport and registration (`mcp/`), domain workflows (`domain/`), shared geospatial operations (`spatial/`), upstream adapters (`clients/`), and typed contracts and policy (`models/`, `core/`). The detailed component diagram, data flows, and deployment boundaries are in the [Architecture Guide](docs/architecture.md).

---

## Features

- **Soil and farmland information**: Look up soil map units and USDA farmland classifications by point, map-unit key, or project-area boundary.
- **Project-area summaries**: Review mapped farmland categories and acreage, validated soil productivity ratings (NCCPI, CSR2, CPI, or STORIE), and whether an area intersects Census urban boundaries. `productivity_index` (nccpi, csr2, cpi, or storie) selects the index used for Land Evaluation scoring; NCCPI v3 is always included per map unit as national baseline context. The `include_nccpi` argument was removed (breaking change); calls that still send it are rejected.
- **Cropland Data Layer evidence**: Explore mapped CDL classes in an area and nearby bands. CDL is a land-cover dataset; it does not verify active farming or determine farmland classification.
- **Corridor screening**: Summarize soil and agricultural context along a line-based project corridor and compare alternatives.
- **Traceable results**: Responses identify sources, coverage, and limitations to help users interpret screening evidence.

---

## FPPA Regulatory Scope & Limitations

### 7 CFR Part 657 vs. 7 CFR Part 658

| Reference | What it covers | How this service uses it |
| :--- | :--- | :--- |
| **7 CFR Part 657** | USDA criteria for Prime, Unique, and Statewide or Local Important Farmland. | Reports the SSURGO farmland classification associated with queried soil map units. |
| **7 CFR Part 658** | FPPA review requirements, including formal evaluation and agency review. | Provides preliminary screening context only; it does not complete an official review or form. |

### Regulatory Notice

> **IMPORTANT LIMITATION**:
> Results are preliminary screening information, not an official FPPA determination. The server does not issue official Land Evaluation or Site Assessment scores, complete Form AD-1006 or NRCS-CPA-106, or replace review by USDA NRCS. Contact the appropriate USDA NRCS office for formal review.

---

## Data Sources

| Source | Information used | Important context |
| :--- | :--- | :--- |
| [USDA NRCS Soil Data Access (SDA)](https://sdmdataaccess.nrcs.usda.gov/) | SSURGO soil map units, farmland classifications, geometry, and selected soil interpretations. | Soil inventory data; not a site-specific agency determination. |
| [USDA NASS Cropland Data Layer (CDL)](https://www.nass.usda.gov/Research_and_Science/Cropland/Release/) | Annual mapped land-cover class distributions for project areas and nearby zones. | Mapped classes are not evidence of current activity, ownership, or official farmland status. |
| [USDA NASS Quick Stats](https://quickstats.nass.usda.gov/) | County-level agricultural statistics used for context in corridor screening. | Agricultural Census or survey summaries, not parcel-level measurements. |
| [U.S. Census Bureau TIGERweb](https://tigerweb.geo.census.gov/) | Census urban-area and county boundaries. | Boundary overlap is screening context and should be confirmed for formal review. |

CDL results include observed class codes and labels, class counts or shares, product vintage, coverage status, and source provenance. The context tool summarizes the area of interest, a one-mile exterior ring, and a 30-metre exterior band when complete coverage can be established. The histogram tool accepts caller-selected CDL class codes; neither tool assigns farmland classes or decides whether land is actively farmed.

These datasets describe different things: SSURGO farmland classes are soil-based classifications, soil productivity ratings describe selected soil interpretations, and CDL classes represent mapped land cover. They are complementary screening evidence and should not be treated as interchangeable.

---

## Installation & Setup

### Requirements

- **Python**: `>=3.11`
- **Package Manager**: [uv](https://docs.astral.sh/uv/) (recommended) or `pip`

### Using `uv` (Recommended)

```powershell
git clone https://github.com/AndrewBrown-USDA/fpac-soil-mcp.git
Set-Location fpac-soil-mcp
uv sync
```

### Using Standard `pip`

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
```

---

## Execution Modes

The server supports local MCP clients and network-hosted deployments:

- **Standard I/O (`stdio`)**: Default mode for a local MCP client.
- **Server-Sent Events (`sse`)** / **Streamable HTTP (`http`)**: Network modes for remote MCP clients.

### Local Stdio

```powershell
uv run fpac-soil-mcp
```

### Network SSE / HTTP

```powershell
$env:MCP_TRANSPORT="sse"
$env:MCP_HOST="0.0.0.0"
$env:MCP_PORT="8000"
uv run fpac-soil-mcp
```

### Docker Container

The repository includes a production multi-stage `Dockerfile` with dedicated build and slim runtime stages (`ghcr.io/astral-sh/uv:python3.11-bookworm-slim`), non-root `appuser` execution, and a built-in container health check.

```powershell
# Build container image
docker build -t fpac-soil-mcp .

# Run container over stdio
docker run -i --rm -e MCP_TRANSPORT=stdio fpac-soil-mcp

# Run container over SSE / HTTP
docker run -d --rm -p 8000:8000 -e MCP_TRANSPORT=sse -e MCP_HOST=0.0.0.0 -e MCP_PORT=8000 --name fpac-soil-mcp fpac-soil-mcp
```

### Docker Compose development stack

The root `compose.yaml` runs the MCP server, Python agent/map app, and JavaScript harness together. The agent uses local-development mode and needs an OpenAI-compatible model API; by default, it expects that API on the host at `http://host.docker.internal:8090/v1`.

```powershell
Copy-Item .env.compose.example .env.compose
# Edit .env.compose and set AGENT_MODEL to the model ID served by your model API.
docker compose --env-file .env.compose up --build
```

Open the agent/map app at `http://127.0.0.1:3000` and the MCP harness at `http://127.0.0.1:3030`. The MCP server is also available on `http://127.0.0.1:8000/mcp`. Published ports bind to loopback by default; change the `*_PUBLISHED_PORT` values in `.env.compose` to avoid local port conflicts.

The harness connects to the MCP service over Streamable HTTP and loads the shared evaluation corpus. The app and harness wait for the MCP health check before starting. The agent's explicit local MCP URL is restricted to the Compose `mcp` service hostname or loopback addresses.

To run the optional llama.cpp service, place a GGUF model in the configured model directory, set `LLAMA_CPP_MODEL_FILE`, change `LOCAL_LLM_BASE_URL` to `http://llama:8080/v1`, then start with the profile:

```powershell
docker compose --env-file .env.compose --profile llm up --build
```

Model files are mounted read-only and are not downloaded by Compose. The default stack does not start a model service. Stop the stack with `docker compose --env-file .env.compose down`.

---

## Standard MCP Client Configuration

Example configuration for an MCP client.

### Standard I/O (`stdio`) Boilerplate

```json
{
  "mcpServers": {
    "fpac-soil": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/fpac-soil-mcp",
        "run",
        "fpac-soil-mcp"
      ],
      "env": {
        "MCP_TRANSPORT": "stdio"
      }
    }
  }
}
```

*Note for Windows hosts: use Windows-style directory paths (e.g., `"D:\\workspace\\fpac-soil-mcp"`).*

### Network / Remote (`sse` or `http`) Boilerplate

```json
{
  "mcpServers": {
    "fpac-soil": {
      "url": "http://127.0.0.1:8000/sse"
    }
  }
}
```

---

## Tool Reference

Tools accept validated coordinates, map-unit keys, or GeoJSON geometries. Full input schemas are available through MCP tool discovery.

| Tool | What it does |
| :--- | :--- |
| `get_farmland_classification_by_point` | Look up soil map unit and farmland classification at a coordinate. |
| `get_farmland_classification_by_mukey` | Look up soil and farmland information by SSURGO map-unit key. |
| `analyze_farmland_by_polygon` | Summarize soil map units, farmland classes, acreage, urban context, and optional productivity ratings in a project area. |
| `get_soil_polygons_by_geometry` | Return intersecting SSURGO map-unit polygons and attributes. |
| `get_soil_interpretations` | Retrieve USDA soil interpretation ratings for map units. |
| `analyze_cdl_histogram` | Summarize selected Cropland Data Layer classes in a project area. |
| `analyze_cdl_context` | Summarize mapped Cropland Data Layer classes in the project area and two surrounding zones. |
| `check_urban_area_exemption` | Screen a point or project area against Census 2020 Urban Areas. |
| `calculate_preliminary_lesa` | Calculate preliminary LESA screening context from supplied project information and available soil data. |
| `analyze_corridor_fppa` | Summarize soil and agricultural context along a linear corridor, by county, with optional alternatives. |
| `explain_fppa_screening_scope` | Explain the difference between preliminary screening and formal FPPA review. |
| `list_farmland_classes` | List USDA NRCS farmland-class categories and regulatory references. |

**Coverage status values (0.6.0, breaking change).** Soil mapping coverage is `covered`, `partial`, `unmapped`, or `error`. Rating coverage (map-unit productivity, NCCPI baseline, corridor productivity, and Land Evaluation) is `rated`, `partial`, `unrated`, `unmapped`, `unknown`, or `error`. `error` means a query failed or the input was invalid; a failed query is never reported as `unmapped` or `unrated`. Renamed values: `partially_covered` -> `partial`; `no_data` and `invalid_request` -> `error`; rating `covered` -> `rated`; `no_coverage` -> `unrated`; `not_found` -> `unknown`. Field names are unchanged. See [ADR 0019](docs/decisions/0019-shared-coverage-vocabularies.md).

---

## Resources, Prompts & HTTP Routes

### Resources

- `fppa://regulatory-notice`: Regulatory scope and limitations.
- `fppa://screening-guidance`: Preliminary screening and formal-review context.
- `fppa://farmland-classes`: SSURGO farmland-class definitions and references.
- `fppa://site-assessment-criteria`: Site Assessment criteria and scoring references.

### Prompts

Four guided prompts cover general screening, corridor analysis, urban-area context, and site assessment. MCP clients can discover their available arguments and render them when needed.

### HTTP routes

For network transports, `GET /health` reports service health and `GET /meta` reports server capabilities.

---

## Configuration

The default transport is `stdio`, suitable for a local MCP client. For a network deployment, set `MCP_TRANSPORT` to `sse` or `http` and configure `MCP_HOST` and `MCP_PORT` for the deployment environment. See [`.env.example`](.env.example) for supported settings.

## For Contributors

See [`QUICKSTART.md`](QUICKSTART.md) for setup and client examples, [`docs/architecture.md`](docs/architecture.md) for component responsibilities and data flow, [`AGENTS.md`](AGENTS.md) for development and validation commands, and [`eval/fpac_soil_mcp_harness/README.md`](eval/fpac_soil_mcp_harness/README.md) for the local browser workbench. Evaluation and artifact-handling guidance is in [`docs/evaluation.md`](docs/evaluation.md).

---

## License

This project is in the worldwide public domain domestically under 17 U.S.C. § 105 and licensed under the [MIT License](LICENSE.md) internationally and for third-party contributions. See [INTENT.md](INTENT.md) and [LICENSE.md](LICENSE.md) for full licensing details and government notices.
