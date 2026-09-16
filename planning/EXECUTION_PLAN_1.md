# EXECUTION PLAN 1: FPAC Soil MCP Server for FPPA Screening

## Goal & Scope

### Goal
Build a minimal, robust, and standards-compliant FastMCP server (`fpac_soil_mcp`) based on the GSA MCP hackathon template that queries USDA NRCS Soil Data Access (SDA) to retrieve soil map units and NRCS Farmland Classifications (SSURGO `mapunit.farmlndcl`). The server supports preliminary Farmland Protection Policy Act (FPPA) screening by point (WGS84 lat/lon) and map unit key (`mukey`), while providing structured provenance metadata, clear regulatory notices, and strict separation between soil survey attributes and official FPPA determinations.

### In Scope
- **Template Adaptation**: Adapt GSA MCP hackathon template (`pyproject.toml`, `main.py`, `.env.example`, `manifest.yaml`, `server.json`, `Dockerfile`) into root repository under package `fpac_soil_mcp`.
- **SDA Client Layer**: Robust HTTPS client targeting `https://sdmdataaccess.nrcs.usda.gov/Tabular/post.rest` using `JSON+COLUMNNAME` format, fixed parameterized query templates, strict input validation, retry logic for transient HTTP/timeout errors, and zero arbitrary SQL exposure.
- **Pydantic Data Models**: Structured, typed response models for map units, SDA metadata, coverage status, limitations, and FPPA regulatory notices.
- **MCP Tools**:
  1. `get_farmland_classification_by_point`: WGS84 point-in-polygon query using SDA function `SDA_Get_Mukey_from_intersection_with_WktWgs84`.
  2. `get_farmland_classification_by_mukey`: Direct mapunit lookup by validated `mukey`.
  3. `explain_fppa_screening_scope`: Structured breakdown of FPPA screening vs. full Land Evaluation & Site Assessment (LESA) scoring (7 CFR Parts 657 & 658) with official citations.
  4. `list_farmland_classes`: Documented reference listing of standard SDA farmland classification categories with provenance notes.
- **MCP Resources & Prompts**: FastMCP resources (`fppa://regulatory-notice`, `fppa://screening-guidance`) and conversation prompts.
- **Testing Suite**: Unit tests with mocked HTTP responses covering validation, schema parsing, error handling, empty coverage, and MCP tool execution; plus an opt-in live SDA integration test suite (`@pytest.mark.live_sda`).
- **Comprehensive Documentation**: `README.md` with architecture Mermaid diagram, setup instructions, MCP client configuration, exact tool signatures, FPPA limitations, data provenance, and `py-soildb` reference disclosure.

### Out of Scope (Explicit Deferrals)
- Automated FPPA Form AD-1006 / NRCS-CPA-106 Part IV/V Site Assessment scoring (requires project footprint, zoning, local infrastructure, and land-use history not available in SDA).
- Arbitrary SQL execution or raw SQL passthrough MCP tools.
- User coordinate tracking or stateful database storage.
- External dependencies beyond standard template stack (`fastmcp`, `httpx`, `pydantic`, `pydantic-settings`).

### Verbatim Constraints
- "Do not fabricate an FPPA land-evaluation score, site-assessment score, or regulatory conclusion."
- "Preserve SDA's original classification text rather than silently converting it into a different regulatory category."
- "Do not expose a general-purpose 'run arbitrary SDA SQL' MCP tool. Use fixed query templates. Strictly validate all user-supplied values."
- "Tests should normally use mocks or recorded sanitized fixtures and must not depend on the live SDA service."
- "Do not push to a remote repository."

---

## Decision Log

- **2026-09-16**: Package naming set to `fpac_soil_mcp` rooted directly in repository (`src/fpac_soil_mcp/`).
- **2026-09-16**: Python version target set to `>=3.11` (tested with Python 3.13/3.14).
- **2026-09-16**: Tabular SDA endpoint defaulted to `https://sdmdataaccess.nrcs.usda.gov/Tabular/post.rest` using `JSON+COLUMNNAME` format.
- **2026-09-16**: Spatial lookup verified using `SDA_Get_Mukey_from_intersection_with_WktWgs84('POINT(lon lat)')`.
- **2026-09-16**: `py-soildb` strategy is `reference_only` (no extra external dependency added; referenced in README with attribution).
- **2026-09-16**: `explain_fppa_screening_scope` exposed as both an MCP Tool and an MCP Resource for maximum client flexibility.
- **2026-09-16**: `list_farmland_classes` tool included in scope.
- **2026-09-16**: Opt-in live SDA integration tests included under `@pytest.mark.live_sda` (mocked by default in CI).
- **2026-09-16**: Verification suite is `uv run pytest` and `uv run ruff check .`.
- **2026-09-16**: Commit discipline follows Conventional Commits format (`feat:`, `test:`, `docs:`, etc.).

---

## Technical Reconnaissance & Hazards

- **SDA POST Endpoint**: `https://sdmdataaccess.nrcs.usda.gov/Tabular/post.rest`. Payload: `{"query": "...", "format": "JSON+COLUMNNAME"}`.
- **SDA Output Structure**: Returns JSON `{"Table": [ [col1, col2, ...], [val1, val2, ...], ... ]}` where the first row contains column names.
- **Spatial Coordinates in WKT**: Note longitude precedes latitude in WKT: `POINT(longitude latitude)`. WGS84 coordinates must be bounded: Longitude [-180, 180], Latitude [-90, 90].
- **Map Unit Schema**: `mapunit.mukey` (numeric string), `mapunit.musym` (symbol), `mapunit.muname` (name), `mapunit.farmlndcl` (classification text), joined to `legend.areasymbol` via `lkey`.
- **FastMCP Registration**: Use modular registration functions: `register_tools(mcp)`, `register_resources(mcp)`, `register_prompts(mcp)`, `register_routes(mcp)`.

---

## Wave Dependency Graph & Table

| Wave | Task ID | Title | Repo | Files in Scope | Depends On |
| --- | --- | --- | --- | --- | --- |
| **Wave 1** | `1.1.1` | Project Scaffolding & Configuration | `.` | `pyproject.toml`, `main.py`, `.env.example`, `manifest.yaml`, `server.json`, `Dockerfile`, `src/fpac_soil_mcp/__init__.py`, `src/fpac_soil_mcp/config.py` | None |
| **Wave 1** | `1.1.2` | FPPA Scope, Constants & Citations | `.` | `src/fpac_soil_mcp/constants.py`, `src/fpac_soil_mcp/fppa.py` | None |
| **Wave 2** | `1.2.1` | Pydantic Models & Response Schemas | `.` | `src/fpac_soil_mcp/models.py` | `1.1.1`, `1.1.2` |
| **Wave 2** | `1.2.2` | SDA Client & Query Engine | `.` | `src/fpac_soil_mcp/sda_client.py` | `1.1.1`, `1.1.2` |
| **Wave 3** | `1.3.1` | MCP Tools Registration & Implementation | `.` | `src/fpac_soil_mcp/tools/__init__.py`, `src/fpac_soil_mcp/tools/soil_tools.py`, `src/fpac_soil_mcp/tools/fppa_tools.py` | `1.2.1`, `1.2.2` |
| **Wave 3** | `1.3.2` | MCP Prompts, Resources, Routes & App Entry | `.` | `src/fpac_soil_mcp/resources/__init__.py`, `src/fpac_soil_mcp/resources/fppa_resources.py`, `src/fpac_soil_mcp/prompts/__init__.py`, `src/fpac_soil_mcp/prompts/fppa_prompts.py`, `src/fpac_soil_mcp/routes.py`, `src/fpac_soil_mcp/app.py` | `1.2.1`, `1.2.2` |
| **Wave 4** | `1.4.1` | Unit & Integration Test Suite | `.` | `tests/__init__.py`, `tests/conftest.py`, `tests/test_sda_client.py`, `tests/test_tools.py`, `tests/test_server.py` | `1.3.1`, `1.3.2` |
| **Wave 4** | `1.4.2` | Comprehensive Documentation & Quickstart | `.` | `README.md`, `QUICKSTART.md` | `1.3.1`, `1.3.2` |

---

## Task Specifications

### Wave 1

#### Task 1.1.1: Project Scaffolding & Configuration
- **ID**: `1.1.1`
- **Repo**: `.`
- **Files in Scope**:
  - *Must create*: `pyproject.toml`, `main.py`, `.env.example`, `manifest.yaml`, `server.json`, `Dockerfile`, `src/fpac_soil_mcp/__init__.py`, `src/fpac_soil_mcp/config.py`
  - *Can create*: `.gitignore`, `.python-version`
  - *Temp/scratch*: `.development/`
- **Depends on**: None
- **Spec Prose**: Initialize project configuration and settings module for `fpac_soil_mcp`. Define `pyproject.toml` with `fastmcp>=2.0.0`, `httpx>=0.27.0`, `pydantic>=2.0.0`, `pydantic-settings>=2.0.0`, dev dependencies (`pytest`, `pytest-asyncio`, `ruff`). Create `src/fpac_soil_mcp/config.py` using `pydantic-settings` to define configurable settings (`sda_tabular_url`, `request_timeout_seconds`, `max_retries`, `mcp_transport`, `mcp_host`, `mcp_port`). Provide `main.py` entrypoint.
- **Grep Anchors**: `class Settings`, `mcp_transport`, `sda_tabular_url`.
- **Acceptance & Targeted Test**:
  - `uv sync` succeeds.
  - `python -c "from fpac_soil_mcp.config import settings; print(settings.sda_tabular_url)"` outputs default SDA URL.

#### Task 1.1.2: FPPA Scope, Constants & Citations
- **ID**: `1.1.2`
- **Repo**: `.`
- **Files in Scope**:
  - *Must create*: `src/fpac_soil_mcp/constants.py`, `src/fpac_soil_mcp/fppa.py`
  - *Temp/scratch*: `.development/`
- **Depends on**: None
- **Spec Prose**: Define static domain constants, official citations (7 CFR Part 657 & 658, NRCS FPPA manual, Form AD-1006 / NRCS-CPA-106), standard farmland classification values, standard disclaimer / regulatory notice text, and detailed scope distinction explanation functions in `fppa.py` and `constants.py`.
- **Grep Anchors**: `REGULATORY_NOTICE`, `FARMLAND_CLASS_DEFINITIONS`, `explain_fppa_scope`.
- **Acceptance & Targeted Test**:
  - `python -c "from fpac_soil_mcp.fppa import get_fppa_scope_explanation; print(len(get_fppa_scope_explanation()))"` executes without error and returns authoritative scope text.

---

### Wave 2

#### Task 1.2.1: Pydantic Models & Response Schemas
- **ID**: `1.2.1`
- **Repo**: `.`
- **Files in Scope**:
  - *Must create*: `src/fpac_soil_mcp/models.py`
  - *Temp/scratch*: `.development/`
- **Depends on**: `1.1.1`, `1.1.2`
- **Spec Prose**: Implement strong Pydantic models for request validation and structured responses. Create models for `SoilMapUnit` (mukey, musym, muname, farmlndcl, areasymbol), `QuerySource` (service_name, endpoint, timestamp_utc, documentation_urls), `FarmlandClassificationResponse` (query_type, input_query, coverage_status, map_units, source, limitations, regulatory_notice), `FppaScopeResponse`, and `FarmlandClassListResponse`.
- **Grep Anchors**: `class SoilMapUnit`, `class FarmlandClassificationResponse`.
- **Acceptance & Targeted Test**:
  - `python -c "from fpac_soil_mcp.models import FarmlandClassificationResponse, SoilMapUnit; print(SoilMapUnit.model_fields.keys())"` outputs expected schema fields.

#### Task 1.2.2: SDA Client & Query Engine
- **ID**: `1.2.2`
- **Repo**: `.`
- **Files in Scope**:
  - *Must create*: `src/fpac_soil_mcp/sda_client.py`
  - *Temp/scratch*: `.development/`
- **Depends on**: `1.1.1`, `1.1.2`
- **Spec Prose**: Implement `SDAClient` encapsulating HTTP communication with SDA Tabular REST service. Features:
  1. Fixed SQL templates for point lookup (`SDA_Get_Mukey_from_intersection_with_WktWgs84`) and mukey lookup (`WHERE m.mukey = ...`).
  2. Strict input validation: latitude [-90, 90], longitude [-180, 180], mukey (positive numeric integer string).
  3. POST payload format: `{"query": query_str, "format": "JSON+COLUMNNAME"}`.
  4. Parser converting SDA table array matrix into list of dicts/models.
  5. Error handling: HTTP timeouts, non-200 responses, SDA SQL error messages, empty table rows.
  6. Retry policy for transient HTTP 5xx or connection timeouts with backoff.
- **Grep Anchors**: `class SDAClient`, `get_by_point`, `get_by_mukey`, `_execute_query`.
- **Acceptance & Targeted Test**:
  - `python -c "from fpac_soil_mcp.sda_client import SDAClient; client = SDAClient(); print(client.validate_coordinates(42.03, -93.62))"` returns validated tuple without error.

---

### Wave 3

#### Task 1.3.1: MCP Tools Registration & Implementation
- **ID**: `1.3.1`
- **Repo**: `.`
- **Files in Scope**:
  - *Must create*: `src/fpac_soil_mcp/tools/__init__.py`, `src/fpac_soil_mcp/tools/soil_tools.py`, `src/fpac_soil_mcp/tools/fppa_tools.py`
  - *Temp/scratch*: `.development/`
- **Depends on**: `1.2.1`, `1.2.2`
- **Spec Prose**: Implement FastMCP tool registration in `src/fpac_soil_mcp/tools/`.
  1. `get_farmland_classification_by_point(latitude: float, longitude: float) -> FarmlandClassificationResponse`: Validates lat/lon, calls `SDAClient.get_by_point`, returns structured response.
  2. `get_farmland_classification_by_mukey(mukey: str) -> FarmlandClassificationResponse`: Validates mukey, calls `SDAClient.get_by_mukey`, returns structured response.
  3. `explain_fppa_screening_scope() -> FppaScopeResponse`: Returns comprehensive scope explanation and citations.
  4. `list_farmland_classes() -> FarmlandClassListResponse`: Returns known SDA farmland classification categories with provenance.
  5. `register_tools(mcp: FastMCP)` aggregator function in `__init__.py`.
- **Grep Anchors**: `get_farmland_classification_by_point`, `get_farmland_classification_by_mukey`, `register_tools`.
- **Acceptance & Targeted Test**:
  - `python -c "from fastmcp import FastMCP; from fpac_soil_mcp.tools import register_tools; mcp = FastMCP('test'); register_tools(mcp)"` registers tools without error.

#### Task 1.3.2: MCP Prompts, Resources, Routes & App Entry
- **ID**: `1.3.2`
- **Repo**: `.`
- **Files in Scope**:
  - *Must create*: `src/fpac_soil_mcp/resources/__init__.py`, `src/fpac_soil_mcp/resources/fppa_resources.py`, `src/fpac_soil_mcp/prompts/__init__.py`, `src/fpac_soil_mcp/prompts/fppa_prompts.py`, `src/fpac_soil_mcp/routes.py`, `src/fpac_soil_mcp/app.py`
  - *Temp/scratch*: `.development/`
- **Depends on**: `1.2.1`, `1.2.2`
- **Spec Prose**: Complete MCP server infrastructure in `src/fpac_soil_mcp/`.
  1. Resources: Register `fppa://regulatory-notice` and `fppa://screening-guidance`.
  2. Prompts: Register `fppa_screening_assistant` prompt guiding an AI agent on proper screening steps and caveats.
  3. Routes: Healthcheck route `GET /health` and metadata endpoint.
  4. App entry: `src/fpac_soil_mcp/app.py` creating the FastMCP instance, calling all registration functions, and providing transport runner (`main()`).
- **Grep Anchors**: `register_resources`, `register_prompts`, `register_routes`, `mcp = FastMCP`.
- **Acceptance & Targeted Test**:
  - `python -c "from fpac_soil_mcp.app import mcp; print(mcp.name)"` prints server name.

---

### Wave 4

#### Task 1.4.1: Unit & Integration Test Suite
- **ID**: `1.4.1`
- **Repo**: `.`
- **Files in Scope**:
  - *Must create*: `tests/__init__.py`, `tests/conftest.py`, `tests/test_sda_client.py`, `tests/test_tools.py`, `tests/test_server.py`
  - *Temp/scratch*: `.development/`
- **Depends on**: `1.3.1`, `1.3.2`
- **Spec Prose**: Build comprehensive automated test suite using `pytest` and `pytest-asyncio`.
  1. `test_sda_client.py`: Test coordinate validation bounds, mukey validation, query template generation, JSON+COLUMNNAME response parsing, empty results handling, HTTP timeout/500 retry handling, and malformed responses (all using `httpx` mock transport or `unittest.mock`).
  2. `test_tools.py`: Test MCP tool invocation for point lookup, mukey lookup, scope explanation, and class listing using mocked SDA client.
  3. `test_server.py`: Smoke tests verifying FastMCP initialization, tool listing, resource listing, and prompt listing.
  4. Live integration tests marked with `@pytest.mark.live_sda` testing real queries to SDA (skipping if offline or disabled).
- **Grep Anchors**: `test_coordinate_validation`, `test_sda_response_parsing`, `test_get_farmland_classification_by_point`.
- **Acceptance & Targeted Test**:
  - `uv run pytest -m "not live_sda"` runs and passes 100% of unit tests.
  - `uv run ruff check .` passes with zero lint errors.

#### Task 1.4.2: Comprehensive Documentation & Quickstart
- **ID**: `1.4.2`
- **Repo**: `.`
- **Files in Scope**:
  - *Must create/edit*: `README.md`, `QUICKSTART.md`
  - *Temp/scratch*: `.development/`
- **Depends on**: `1.3.1`, `1.3.2`
- **Spec Prose**: Write complete, authoritative documentation:
  1. Project purpose & architecture with Mermaid diagram (`MCP Client -> FastMCP Tool -> SDAClient -> USDA NRCS SDA`).
  2. Setup and execution instructions (uv run, stdio, streamable-http).
  3. MCP client configuration examples for Claude Desktop, Zed, and Cursor.
  4. Detailed tool documentation with input parameters, response schemas, and sample outputs.
  5. FPPA legal/regulatory background (7 CFR 657/658, Form AD-1006) and explicit limitations (SDA soil data != FPPA site assessment).
  6. Data provenance disclosure and `py-soildb` reference disclosure.
  7. Quality assurance commands (`pytest`, `ruff`).
- **Grep Anchors**: ````mermaid`, `get_farmland_classification_by_point`, `Farmland Protection Policy Act`.
- **Acceptance & Targeted Test**:
  - Verify all documentation links, commands, and code blocks are accurate and syntax-checked.
