# Architecture Guide

This guide describes the current implementation of the FPAC Soil MCP server: how MCP requests enter the service, how tool calls move through the domain and spatial layers, and how upstream datasets contribute screening evidence. It is an implementation map, not a record of project status or a substitute for the regulatory notices returned by the service.

## Component and Request Flow

```mermaid
flowchart TB
    HOST["MCP host or client"]

    subgraph SERVER["fpac-soil-mcp service"]
        TRANSPORT["FastMCP transport<br/>stdio | SSE | Streamable HTTP"]
        APP["mcp/app.py<br/>create_mcp_server()"]
        REG["Central registration"]
        TOOLREG["mcp/tools/<br/>tool groups"]
        RESREG["mcp/resources/<br/>FPPA reference resources"]
        PROMPTREG["mcp/prompts/<br/>guided FPPA workflows"]
        ROUTES["mcp/routes.py<br/>GET /health and GET /meta"]

        subgraph TOOLGROUPS["MCP tool adapters"]
            SOILTOOLS["Soil lookup<br/>point | mukey | interpretations"]
            SPATIALTOOLS["Spatial analysis<br/>polygon | soil geometry | corridor"]
            CDLTOOLS["CDL analysis<br/>histogram | area and surrounding zones"]
            FPPATOOLS["FPPA guidance<br/>scope | farmland classes"]
            EXEMPTTOOLS["Urban-area screening"]
            LESATOOLS["Preliminary LESA"]
        end

        subgraph DOMAIN["Domain workflows"]
            FPPA["domain/fppa.py<br/>classifications and scope"]
            POLYGON["domain/polygon_analyzer.py<br/>area sampling and aggregation"]
            CORRIDOR["domain/corridor_analyzer.py<br/>segments, buffers, alternatives"]
            LESA["domain/lesa.py and<br/>domain/site_assessment.py"]
            WORKFLOW["domain/workflow.py<br/>workflow guidance"]
        end

        GEO["spatial/geometry.py<br/>GeoJSON/WKT validation, transforms,<br/>acreage and geometry operations"]
        MAP["spatial/map_builder.py<br/>map-layer response construction"]

        subgraph SHARED["Shared policy, contracts, and configuration"]
            MODELS["models/<br/>soil | spatial | CDL | case | LESA"]
            CORE["core/<br/>authority | constants | privacy | errors"]
            CONFIG["core/config.py<br/>environment-backed settings"]
        end

        subgraph CLIENTS["Upstream client adapters"]
            HTTP["clients/http.py<br/>shared HTTP errors and retries"]
            SDA["clients/sda/<br/>SDA client, fixed SQL templates,<br/>SDV metadata registry"]
            CDL["clients/cdl.py<br/>CDL ImageServer client"]
            NASS["clients/nass.py<br/>QuickStats client"]
            TIGER["clients/tigerweb.py<br/>Census TIGERweb client"]
        end

        RESULT["Typed screening response<br/>source provenance | coverage/status<br/>caveats and limitations"]
    end

    subgraph SOURCES["External public data services"]
        SDAAPI["USDA NRCS Soil Data Access<br/>SSURGO tabular and spatial queries"]
        CDLAPI["USDA NASS Cropland Data Layer<br/>ImageServer metadata and class data"]
        NASSAPI["USDA NASS QuickStats<br/>county agricultural statistics"]
        CENSUSAPI["U.S. Census Bureau TIGERweb<br/>2020 Urban Areas and county boundaries"]
    end

    HOST <-->|"MCP messages"| TRANSPORT
    APP --> REG
    APP --> TRANSPORT
    REG --> TOOLREG
    REG --> RESREG
    REG --> PROMPTREG
    REG --> ROUTES
    TOOLREG --> TOOLGROUPS
    TRANSPORT --> TOOLGROUPS
    TRANSPORT --> RESREG
    TRANSPORT --> PROMPTREG
    TRANSPORT --> ROUTES

    SOILTOOLS --> FPPA
    SOILTOOLS --> SDA
    SPATIALTOOLS --> POLYGON
    SPATIALTOOLS --> CORRIDOR
    SPATIALTOOLS --> GEO
    SPATIALTOOLS --> MAP
    CDLTOOLS --> POLYGON
    CDLTOOLS --> CDL
    FPPATOOLS --> FPPA
    EXEMPTTOOLS --> TIGER
    LESATOOLS --> LESA
    LESATOOLS --> POLYGON
    LESATOOLS --> CORRIDOR
    LESA --> WORKFLOW

    FPPA --> MODELS
    POLYGON --> GEO
    POLYGON --> SDA
    POLYGON --> CDL
    POLYGON --> TIGER
    CORRIDOR --> GEO
    CORRIDOR --> SDA
    CORRIDOR --> TIGER
    CORRIDOR --> NASS
    LESA --> MODELS
    GEO --> MODELS
    CORE --> TOOLGROUPS
    CORE --> DOMAIN
    CONFIG --> CLIENTS
    CLIENTS --> HTTP

    SDA <-->|"queries and results"| SDAAPI
    CDL <-->|"metadata and class data"| CDLAPI
    NASS <-->|"statistics requests and results"| NASSAPI
    TIGER <-->|"boundary requests and results"| CENSUSAPI

    TOOLGROUPS --> RESULT
    DOMAIN --> RESULT
    MODELS --> RESULT
    RESULT --> TRANSPORT
```

## Responsibilities and Boundaries

- **MCP assembly (`src/fpac_soil_mcp/mcp/`)** creates the FastMCP server and registers tool groups, resources, prompts, and custom HTTP routes. The same server supports `stdio`, SSE, and Streamable HTTP transports; route handlers are available on network transports.
- **Tool adapters (`mcp/tools/`)** expose the public MCP functions and organize them by soil lookup, spatial analysis, CDL, FPPA guidance, exemptions, and LESA. They connect the MCP contract to domain operations rather than acting as independent data stores.
- **Domain workflows (`domain/`)** combine soil, geography, and agricultural context for point, map-unit, polygon, corridor, and preliminary LESA workflows. Polygon analysis aggregates spatial samples; corridor analysis works with linear segments, county partitions, buffers, and alternatives.
- **Spatial operations (`spatial/`)** validate and normalize geometry, produce safe WKT for service queries, calculate area and length, and prepare map-layer responses. These operations are shared by multiple workflows.
- **Clients (`clients/`)** isolate external request and response behavior. The shared HTTP helper normalizes request/status errors and retries configured transient failures. The SDA client uses fixed query templates and parses SDA's `JSON+COLUMNNAME` response format; clients do not accept arbitrary user SQL.
- **Contracts and policy (`models/`, `core/`)** hold response schemas, authority and provenance types, configuration, error types, regulatory notices, and privacy protections. Results should communicate partial coverage and unavailable upstream data rather than imply unsupported completeness.
- **Resources and prompts** provide discoverable FPPA notices, screening guidance, farmland classes, assessment criteria, and guided workflow templates. They complement tools and do not replace formal review.
- **HTTP routes** are operational endpoints: `/health` reports service health and `/meta` reports server metadata. They are distinct from MCP tools.

## Data Sources

| Adapter | Source | Role in screening |
| --- | --- | --- |
| `SDAClient` | USDA NRCS Soil Data Access (SDA) | SSURGO map units, farmland classes, soil interpretations, and spatial soil intersections/clipping. |
| `CDLClient` | USDA NASS Cropland Data Layer (CDL) ImageServer | Validated raster vintage and mapped class evidence for an area and configured surrounding zones. |
| `NassClient` | USDA NASS QuickStats | County agricultural statistics used as context in corridor and related assessments; the integration requires its configured capability and API key. |
| `TigerwebClient` | U.S. Census Bureau TIGERweb | 2020 Urban Area screening and county-boundary queries/partitioning. |

These sources describe different things. SSURGO farmland classes are soil-based classifications, soil interpretations are selected productivity or other ratings, CDL is mapped land cover, QuickStats is county-level agricultural context, and TIGERweb supplies boundary geometry. None independently establishes current farming, parcel ownership, or an official FPPA determination.

## Deployment and Evaluation Boundaries

The console entry point is `fpac_soil_mcp.mcp.app:main`. Local MCP clients commonly use `stdio`; network deployments select SSE or Streamable HTTP using configuration. The root Dockerfile packages the server with a non-root runtime user and health check. The Databricks App configuration runs the same server over Streamable HTTP at `/mcp`; the separate application under `apps/agent-fpac-soil-openai-sdk/` is an MCP client, not part of the server's domain or data-access layers.

Automated checks use mocked upstream HTTP responses by default. Offline contract and evaluation suites exercise MCP behavior without requiring live federal services; live-network tests and deployment-specific evaluations are opt-in. The browser harness under `eval/fpac_soil_mcp_harness/` is a local client/workbench for connecting to the server.

## Source Map

| Area | Location |
| --- | --- |
| Server assembly and transport entry point | `src/fpac_soil_mcp/mcp/app.py` |
| Tool, resource, prompt, and route registration | `src/fpac_soil_mcp/mcp/` |
| Domain operations | `src/fpac_soil_mcp/domain/` |
| Geometry and map response construction | `src/fpac_soil_mcp/spatial/` |
| External service clients | `src/fpac_soil_mcp/clients/` |
| Response models, configuration, policy, and errors | `src/fpac_soil_mcp/models/`, `src/fpac_soil_mcp/core/` |
| Evaluation and fixtures | `eval/` |
