# AGENTS.md - FPAC Soil MCP Server

## Quick Start

```powershell
# Install locked runtime and development dependencies
uv sync

# Run the MCP server over stdio (default)
uv run fpac-soil-mcp

# Run the mocked test suite
uv run pytest -m "not live_network"

# Run one test file
uv run pytest tests\test_sda_client.py

# Lint and check formatting
uv run ruff check .
uv run ruff format --check .

# Run the repository validation target
make check

# Build and run the container
docker build -t fpac-soil-mcp .
docker run -i --rm -e MCP_TRANSPORT=stdio fpac-soil-mcp
```

Live network tests require external network access:

```powershell
uv run pytest -m live_network
```

## Find Things

- `src\fpac_soil_mcp\app.py` - FastMCP factory, server assembly, and console-script entry point (`main()`).
- `main.py` - optional root-level development entry point script.
- `src\fpac_soil_mcp\config.py` - environment and `.env` settings.
- `src\fpac_soil_mcp\constants.py` - regulatory notices, limitations, citations, and farmland class definitions.
- `src\fpac_soil_mcp\models.py` - Pydantic response schemas for soil, query results, and validation.
- `src\fpac_soil_mcp\case_models.py` - Pydantic models for FPPA case records, reviews, site assessments, and corridor alternatives.
- `src\fpac_soil_mcp\integration_models.py` - Pydantic schemas for census geography, agricultural statistics, and integrated evaluation.
- `src\fpac_soil_mcp\authority.py` - statutory and regulatory authority references, determination categories, and legal thresholds.
- `src\fpac_soil_mcp\privacy.py` - data governance, section 1619 compliance, and coordinate redaction / privacy guardrails.
- `src\fpac_soil_mcp\workflow.py` - step-by-step workflow tracking and guidance for FPPA evaluation processes.
- `src\fpac_soil_mcp\official_sources.py` - registry and lookups for official federal dataset provenance, layers, and service endpoints.
- `src\fpac_soil_mcp\fppa.py` and `src\fpac_soil_mcp\lesa.py` - FPPA screening and preliminary LESA scoring domain logic.
- `src\fpac_soil_mcp\http_client.py` - base resilient HTTP client with retry logic, timeouts, and structured error handling.
- `src\fpac_soil_mcp\sda_client.py` - USDA SDA HTTP client, validation, fixed SQL templates, retries, and response parsing.
- `src\fpac_soil_mcp\tigerweb_client.py` - US Census Bureau TIGERweb API client for 2020 Urban Areas and County geography queries.
- `src\fpac_soil_mcp\nass_client.py` - USDA NASS QuickStats API client for county agricultural context and cropland statistics.
- `src\fpac_soil_mcp\geometry.py` - GeoJSON parsing, validation, WKT generation, bounding box extraction, and point sampling utilities.
- `src\fpac_soil_mcp\polygon_analysis.py` - multi-point sampling and weighted spatial aggregation across area-of-interest polygons.
- `src\fpac_soil_mcp\corridor_analysis.py` - linear infrastructure corridor segment sampling, buffer generation, and acreage summation.
- `src\fpac_soil_mcp\corridor_scoring.py` - multi-criteria alternative evaluation and comparative impact ranking for linear projects.
- `src\fpac_soil_mcp\tools\` - MCP tool implementations grouped by responsibility (`soil_lookup_tools.py`, `spatial_analysis_tools.py`, `fppa_tools.py`, `exemption_tools.py`, and `lesa_tools.py`) and centralized registration.
- `src\fpac_soil_mcp\resources\` - MCP resource implementations (`fppa_resources.py`) and URI endpoints.
- `src\fpac_soil_mcp\prompts\` - MCP prompt implementations (`fppa_prompts.py`) for guided workflows.
- `src\fpac_soil_mcp\routes.py` - HTTP-only `/health` and `/meta` routes.
- `src\fpac_soil_mcp\data\` - bundled official data registries and regional scoring references (`official_sources.v1.json`, `regional_scoring.v1.json`).
- `eval\common\` - harness-neutral matching, dataset loader, and validation code shared by Pi and Databricks tiers.
- `eval\contract\` - T0 offline contract tests over the in-memory FastMCP client.
- `eval\pi\` - Pi agent evaluation runner and evaluation tests.
- `eval\databricks\` - T1 Databricks-native agent loop, scorers, runner, notebook, and system prompts; see `eval\databricks\README.md`.
- `eval\fpac_soil_mcp_harness\` - local Node.js browser client/workbench; see its nested `AGENTS.md`.
- `apps\agent-fpac-soil-openai-sdk\` - Databricks chat agent app that calls the deployed MCP server; separate uv project; see its nested `AGENTS.md`.
- `tests\` - pytest test suite (unit, mocked API, integration, and live tests); shared mocks in `tests\conftest.py`.
- `docs\decisions\` - durable architecture decision records.
- `planning\` - delivery-planning artifacts; start with `planning\MASTER_PLAN.md` (product mission, target architecture, governance, server roadmap, and delivery tracks), then inspect the directory for execution-specific files.
- `pyproject.toml` - package metadata, dependencies, script entry point, pytest markers, and Ruff settings.
- `Makefile` - canonical install, run, test, evaluation, lint, format, and Docker targets.
- `requirements.txt` - generated pinned requirements export; update with `make requirements`.
- `.env.example` - supported environment variables and defaults.
- `Dockerfile` - production container build.
- `server.json` and `manifest.yaml` - MCP registry and capability metadata.
- `README.md` and `QUICKSTART.md` - user-facing setup, client configuration, API behavior, and regulatory scope.

## Workflows

### Add or Change an MCP Tool

1. Implement the domain, client, or analysis behavior under `src\fpac_soil_mcp\`.
2. Define or update response types in `models.py`, `case_models.py`, or `integration_models.py`.
3. Add the callable and its `mcp.tool(...)` registration under `src\fpac_soil_mcp\tools\`.
4. Export and register it through `src\fpac_soil_mcp\tools\__init__.py`; `app.create_mcp_server()` consumes the package registrar.
5. Add mocked tests under `tests\`; add a `live_network` test only when the behavior requires the real service.
6. Update `README.md`, `manifest.yaml`, and `server.json` when the public MCP surface changes.

### Add or Change Resources, Prompts, or HTTP Routes

- Resources: implement under `src\fpac_soil_mcp\resources\`, then wire through `resources\__init__.py`.
- Prompts: implement under `src\fpac_soil_mcp\prompts\`, then wire through `prompts\__init__.py`.
- Routes: register them in `src\fpac_soil_mcp\routes.py`; verify them with a network transport, not stdio.
- Keep all component registration centralized in `app.create_mcp_server()`.

### Add or Change Client or Domain Modules

1. Base HTTP communication on `http_client.py` or extend domain-specific clients (`sda_client.py`, `tigerweb_client.py`, `nass_client.py`).
2. Add domain algorithms or spatial routines in `geometry.py`, `polygon_analysis.py`, `corridor_analysis.py`, or `corridor_scoring.py`.
3. Centralize regulatory rules and governance policies in `constants.py`, `authority.py`, and `privacy.py`.
4. Add comprehensive mocked tests in `tests\` covering edge cases and error responses.

### Validate a Change

```powershell
make check
```

Run the Pi evaluation suite:

```powershell
make test-eval
```

Run T1 Databricks evaluation:

```powershell
make eval-databricks
```

Run `make test-live` separately when changing requests, SQL templates, parsing, retries, or live integration behavior.

Run `make app-check` when changing anything under `apps\agent-fpac-soil-openai-sdk\` (root `make check` skips `apps\`).

## Infrastructure

- Python: `>=3.11`; package and environment management use `uv` with `uv.lock`. Every uv project pins PyPI as its default index so lock files never record the Databricks package proxy (ADR 0013).
- Console entry point: `fpac-soil-mcp = fpac_soil_mcp.app:main`; `main.py` is the container/development entry point.
- Default transport: `stdio`.
- Network transports: set `MCP_TRANSPORT=sse` or `MCP_TRANSPORT=http`; default bind is `127.0.0.1:8000`. Use `make run-sse` or `make run-http`.
- Configuration loads from environment variables and an optional repository-root `.env`; copy `.env.example` for local overrides.
- External APIs and Upstream Services:
  - **USDA NRCS Soil Data Access (SDA)**: Tabular API for SSURGO/STATSGO2 soil survey queries, configured by `SDA_TABULAR_URL`.
  - **US Census Bureau TIGERweb**: 2020 Census Urban Areas and Counties (Layer 0) REST API for urbanized area screening and county FIPS resolution.
  - **USDA NASS QuickStats**: Agricultural statistics REST API for county-level farmland baseline contexts, configured by `NASS_API_KEY`.
- HTTP routes: `/health` and `/meta` are registered on the FastMCP application for network transports.
- Tests use mocked `httpx` transports by default. Tests marked `live_network` contact external services (USDA SDA, Census TIGERweb) and are opt-in.
- SDA responses use `JSON+COLUMNNAME`, where the first table row contains column names; parsing is centralized in `SDAClient`.
- Databricks Apps deployment uses `app.yaml` and Streamable HTTP on `/mcp`; container defaults are defined in `Dockerfile`.

### Operational Rules

- Preserve the preliminary-screening limitation in every soil-query response: this service does not produce an official FPPA determination, LESA score, Form AD-1006, or NRCS-CPA-106.
- Keep regulatory language and citations centralized in `constants.py`; do not duplicate divergent notices in tools.
- Accept only validated coordinates or numeric positive `mukey` values. Do not add user-supplied SQL passthrough.
- Keep SDA queries in fixed templates and retain explicit errors, retry behavior, source metadata, and coverage status.
- Enforce Section 1619 and coordinate privacy protections via `privacy.py` where agricultural producer data or sensitive locations are processed.
- Do not make live network tests part of the default offline test path.
- Do not commit `.env`, credentials, local virtual environments, caches, or generated bytecode.

## References

- `README.md` - architecture, MCP interface, configuration, client setup, and FPPA legal context.
- `QUICKSTART.md` - shortest installation and client connection path.
- `.env.example` - configuration reference.
- `manifest.yaml` - published MCP tools and resources.
- `server.json` - MCP server launch metadata.
- `planning\MASTER_PLAN.md` - product mission, target architecture, governance, server roadmap, and delivery tracks.
- `docs\decisions\` - architecture decision records.
- `docs\sdv-metadata-contract.md` - SDV metadata rating contract: registry records, validation, per-table behavior, provenance IDs, caveats.
- [FastMCP documentation](https://gofastmcp.com/)
- [USDA NRCS Soil Data Access](https://sdmdataaccess.nrcs.usda.gov/)
- [USDA Web Soil Survey](https://websoilsurvey.sc.egov.usda.gov/)
- [US Census Bureau TIGERweb REST Services](https://tigerweb.geo.census.gov/)
- [USDA NASS QuickStats API](https://quickstats.nass.usda.gov/api)

### Browser Evaluation Harness

- `eval\fpac_soil_mcp_harness\` is the local Node.js/Express browser harness for exercising the MCP server through stdio, SSE, or Streamable HTTP; see its nested `AGENTS.md` and `README.md`.
- `eval\prompt_test_cases.json` contains shared tool, resource, and prompt evaluation cases consumed by the harness and Python evaluation runners.
- From the repository root, use `Set-Location eval\fpac_soil_mcp_harness; npm install`, then `npm start` or `npm run dev`; run `npm run check` after JavaScript changes.
- The harness defaults to `http://127.0.0.1:3030` and is a local client/workbench, not a production deployment or official FPPA determination system.
