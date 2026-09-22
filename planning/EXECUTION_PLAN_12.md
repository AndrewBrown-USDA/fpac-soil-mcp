# EXECUTION PLAN 12: Production Dockerfile Hardening & FastMCP Prompt Suite Expansion

## Goal & Scope

### Goal
Productionize the `Dockerfile` for enterprise container deployments (IBM Cloud / Databricks / OpenShift / local Docker) and expand the FastMCP Prompt suite in `src/fpac_soil_mcp/prompts/` to comprehensively cover all 9 tools across site screening, linear corridors, urban exemptions, and form/LESA drafting.

### In Scope
1. **Dockerfile Multi-Stage Optimization & Container Hardening (`Dockerfile`, `.dockerignore`)**:
   - Multi-stage build pattern using `ghcr.io/astral-sh/uv:python3.11-bookworm-slim` for the build stage and `python:3.11-slim-bookworm` for the minimal runtime image.
   - Non-root user `appuser` (UID 10001) with explicit `/app` ownership and execution permissions.
   - Layer-cached dependency installation (`COPY pyproject.toml uv.lock* ./`, `RUN uv sync --frozen --no-dev --no-install-project`, then copy sources and install project).
   - Inclusion of `README.md` and license files required for proper package metadata build.
   - Container default environment: `MCP_HOST=0.0.0.0`, `MCP_PORT=8000`, `MCP_TRANSPORT=sse`, `PYTHONUNBUFFERED=1`.
   - Explicit `EXPOSE 8000` port declaration.
   - Standard signal handling and entrypoint: `["fpac-soil-mcp"]` (or `python -m fpac_soil_mcp`).
   - Creation of `.dockerignore` to exclude git metadata, test caches, local `.venv`, `planning/`, and local temporary files.
2. **FastMCP Prompt Suite Expansion (`src/fpac_soil_mcp/prompts/fppa_prompts.py`)**:
   - Update `fppa_screening_assistant`: Refine guidance for point and polygon screening (`get_farmland_classification_by_point`, `get_farmland_classification_by_mukey`, `analyze_farmland_by_polygon`, `get_soil_interpretations`).
   - Add `fppa_corridor_screening_assistant`: Dedicated workflow prompt for multi-county linear infrastructure, centerline buffering, indirect staging area exclusion, Census county partitioning, and composite LE calculation (`analyze_corridor_fppa`).
   - Add `fppa_urban_exemption_assistant`: Dedicated prompt guiding users through statutory urban area exemption checks under 7 CFR § 658.2(a) using Census Bureau 2020 Urban Areas (`check_urban_area_exemption`).
   - Add `fppa_site_assessment_assistant`: Dedicated prompt guiding users through Part VI Site Assessment criteria (1-12 for non-corridor / 1-10 for corridor) under 7 CFR § 658.5, scoring threshold evaluations (160 / 220 points under 7 CFR § 658.4(c)), Form AD-1006 / NRCS-CPA-106 documentation, and project alternatives analysis.
3. **Comprehensive Prompt & Server Unit Test Suite (`tests/test_server.py`)**:
   - Extend `tests/test_server.py` to test registration, argument rendering, keyword placeholders, and regulatory safeguards for all 4 FastMCP prompts.
   - Verify prompt lists and rendered contents with mocked FastMCP instances.
4. **Manifest & Documentation Synchronization (`manifest.yaml`, `README.md`)**:
   - Update `manifest.yaml` to register all 4 prompts under the `prompts:` block.
   - Update `README.md` architecture diagrams, prompt reference tables, and Docker execution instructions to reflect multi-stage Docker and expanded prompts.

### Out of Scope
- Future Phase 4-6 features (SQLite DDL state management, Word/PDF docx populator engine, CPA-2 Excel rollup).
- Changing public MCP tool parameter signatures or Pydantic models.
- Upstream USDA SDA, TIGERweb, or NASS API modifications.

### Verbatim Constraints
- "Multi-stage Docker build with builder using `uv` and runtime using minimal `python:3.11-slim-bookworm`."
- "Non-root user `appuser` (UID 10001) with `/app` permissions."
- "Default container environment `MCP_HOST=0.0.0.0`, `MCP_PORT=8000`, `MCP_TRANSPORT=sse`."
- "4 focused, highly structured FastMCP prompts registered in `fppa_prompts.py`."
- "Preserve all existing MCP tool signatures and 184 passing unit tests."
- "Max concurrent workers: 2."

---

## Decision Log

- **2026-09-22**: Multi-stage Docker pattern chosen: `ghcr.io/astral-sh/uv:python3.11-bookworm-slim` as builder to create `/app/.venv`, then copied to a clean `python:3.11-slim-bookworm` runtime image.
- **2026-09-22**: Security hardening: runtime runs as non-root user `appuser` (UID 10001) to satisfy OpenShift, Kubernetes, and enterprise container security policies.
- **2026-09-22**: Default container transport is `sse` on `0.0.0.0:8000` to enable out-of-the-box container/cloud agent connectivity, while preserving standard stdio execution when `MCP_TRANSPORT=stdio` is passed.
- **2026-09-22**: 4 FastMCP prompts registered: `fppa_screening_assistant`, `fppa_corridor_screening_assistant`, `fppa_urban_exemption_assistant`, and `fppa_site_assessment_assistant`.

---

## Technical Reconnaissance

- **Target Files**:
  - `Dockerfile` (~16 lines -> multi-stage)
  - `.dockerignore` (New file)
  - `src/fpac_soil_mcp/prompts/fppa_prompts.py` (~40 lines -> 4 comprehensive prompts)
  - `tests/test_server.py` (~150 lines -> prompt assertions for all 4 prompts)
  - `manifest.yaml` (~30 lines -> prompts block update)
  - `README.md` (~350 lines -> documentation & diagram update)
- **Baseline Test Count**: 184 passed, 10 deselected.
- **Linter & Formatter**: Ruff clean.

---

## Hazards and Guardrails

- **Virtual Environment Path in Multi-stage Docker**: In Python slim images, copying `/app/.venv` requires matching Python major.minor versions (`3.11`) and putting `/app/.venv/bin` at the beginning of `PATH`.
- **FastMCP Prompt Signatures**: FastMCP prompts must have clear typed arguments with default values (`None`) so LLM clients can inspect and invoke them with or without parameters.
- **Prompt Isolation & Zero Hallucination**: Prompts must maintain strict FPPA statutory boundaries (7 CFR Parts 657 & 658), instruct assistants never to fabricate LE/SA scores, and direct users to USDA NRCS for official determinations.

---

## Wave Dependency Graph

```
+--------------------------------------------------------------------+
| Wave 1: Foundations (Parallel)                                     |
| - Task 12.1.1: Production Dockerfile Enhancement (Dockerfile)      |
| - Task 12.1.2: FastMCP Prompt Suite Expansion (fppa_prompts.py)    |
+--------------------------------------------------------------------+
                               |
                               v
+--------------------------------------------------------------------+
| Wave 2: Integration, Tests & Documentation (Parallel)              |
| - Task 12.2.1: FastMCP Prompt & Server Test Suite (test_server.py) |
| - Task 12.2.2: Manifest & Documentation Sync (manifest, README)    |
+--------------------------------------------------------------------+
```

---

## Wave & Task Specifications

### Wave 1

#### Task 12.1.1: Production Dockerfile Enhancement & .dockerignore
- **Repo**: `D:\workspace\fpac-soil-mcp`
- **Files in scope**: `Dockerfile`, `.dockerignore`
- **Depends on**: None
- **Spec**:
  1. Create `.dockerignore` excluding `.git`, `.venv`, `__pycache__`, `*.pyc`, `.pytest_cache`, `.ruff_cache`, `planning/`, `tests/`, `.env`, and temporary files.
  2. Rewrite `Dockerfile` into a hardened multi-stage build:
     - **Stage 1 (`builder`)**: `FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder`
       - Set `ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy`
       - `WORKDIR /app`
       - Copy `pyproject.toml`, `uv.lock*`, `README.md`
       - Run `uv sync --frozen --no-dev --no-install-project`
       - Copy `src/` and `main.py`
       - Run `uv sync --frozen --no-dev`
     - **Stage 2 (`runtime`)**: `FROM python:3.11-slim-bookworm AS runtime`
       - Set `ENV PYTHONUNBUFFERED=1 MCP_HOST=0.0.0.0 MCP_PORT=8000 MCP_TRANSPORT=sse PATH="/app/.venv/bin:$PATH"`
       - Create non-root system user and group `appuser` with UID/GID 10001
       - `WORKDIR /app`
       - Copy `--from=builder /app/.venv /app/.venv`
       - Copy `--from=builder /app/src /app/src`
       - Copy `--from=builder /app/main.py /app/main.py`
       - Set ownership of `/app` to `appuser:appuser`
       - `USER appuser`
       - `EXPOSE 8000`
       - `ENTRYPOINT ["python", "-m", "fpac_soil_mcp"]`
- **Grep Anchors**: `FROM python:3.11-slim-bookworm` and `USER appuser` in `Dockerfile`
- **Acceptance Command**: `uv run ruff check . ; if ($?) { uv run ruff format --check . }`

#### Task 12.1.2: FastMCP Prompt Suite Expansion
- **Repo**: `D:\workspace\fpac-soil-mcp`
- **Files in scope**: `src/fpac_soil_mcp/prompts/fppa_prompts.py`
- **Depends on**: None
- **Spec**:
  1. In `src/fpac_soil_mcp/prompts/fppa_prompts.py`, expand `register_fppa_prompts(mcp: FastMCP)`:
     - Enhance `fppa_screening_assistant(project_name: str | None = None, location: str | None = None, geometry_type: str | None = None) -> str`:
       - Guides point (`get_farmland_classification_by_point`), mukey (`get_farmland_classification_by_mukey`), and polygon (`analyze_farmland_by_polygon`, `get_soil_interpretations`) screening.
       - Enforces 7 CFR 657 farmland classification distinction vs 7 CFR 658 formal determinations.
     - Add `fppa_corridor_screening_assistant(project_name: str | None = None, corridor_description: str | None = None, state_county: str | None = None) -> str`:
       - Guides multi-county linear corridor screening using `analyze_corridor_fppa`.
       - Explains centerline buffering, indirect staging area exclusion, Census county partitioning, composite LE score calculation, Criterion 7 farm size benchmarks, and alternative route comparison.
     - Add `fppa_urban_exemption_assistant(project_name: str | None = None, location_description: str | None = None) -> str`:
       - Guides statutory 7 CFR § 658.2(a) urban area exemption screening using `check_urban_area_exemption`.
       - Explains Census 2020 Urban Area boundaries (Layer 0), committed urban development criteria, and FPPA non-applicability findings.
     - Add `fppa_site_assessment_assistant(project_name: str | None = None, project_type: str | None = None, federal_agency: str | None = None) -> str`:
       - Guides completion and review of USDA Form AD-1006 / NRCS-CPA-106 Site Assessment criteria (Part VI / 7 CFR § 658.5).
       - Explains the 160-point threshold (combined LE+SA < 160 requires minimal protection; >= 160 requires alternative consideration; >= 220 requires comprehensive avoidance).
       - Instructs coordination with local USDA NRCS state/county offices.
- **Grep Anchors**: `fppa_screening_assistant`, `fppa_corridor_screening_assistant`, `fppa_urban_exemption_assistant`, `fppa_site_assessment_assistant` in `src/fpac_soil_mcp/prompts/fppa_prompts.py`
- **Acceptance Command**: `uv run ruff check src/fpac_soil_mcp/prompts/fppa_prompts.py`

---

### Wave 2

#### Task 12.2.1: Comprehensive FastMCP Prompt & Server Test Suite
- **Repo**: `D:\workspace\fpac-soil-mcp`
- **Files in scope**: `tests/test_server.py`
- **Depends on**: Task 12.1.2
- **Spec**:
  1. In `tests/test_server.py`:
     - Update and expand `TestResourcesAndPrompts`:
       - Test registration of all 4 prompts (`fppa_screening_assistant`, `fppa_corridor_screening_assistant`, `fppa_urban_exemption_assistant`, `fppa_site_assessment_assistant`).
       - Test `fppa_screening_assistant` with project name, location, and geometry types.
       - Test `fppa_corridor_screening_assistant` with corridor name, description, and state/county context, verifying mentions of `analyze_corridor_fppa`, 7 CFR § 658.5(c), and CPA-106.
       - Test `fppa_urban_exemption_assistant` with project details, verifying mentions of `check_urban_area_exemption`, 7 CFR § 658.2(a), and Census 2020 Urban Areas.
       - Test `fppa_site_assessment_assistant` with federal agency context, verifying mentions of 7 CFR § 658.5, Form AD-1006 / NRCS-CPA-106, and 160/220 scoring thresholds.
       - Verify regulatory warning notices and anti-hallucination guardrails across all 4 prompt templates.
- **Grep Anchors**: `test_fppa_corridor_screening_assistant_prompt`, `test_fppa_urban_exemption_assistant_prompt`, `test_fppa_site_assessment_assistant_prompt` in `tests/test_server.py`
- **Acceptance Command**: `uv run pytest tests/test_server.py`

#### Task 12.2.2: Manifest & Documentation Synchronization
- **Repo**: `D:\workspace\fpac-soil-mcp`
- **Files in scope**: `manifest.yaml`, `README.md`
- **Depends on**: Task 12.1.1, Task 12.1.2
- **Spec**:
  1. In `manifest.yaml`:
     - Update `prompts:` block to list all 4 prompts with titles, descriptions, and argument schemas.
  2. In `README.md`:
     - Update architecture diagram and text to reference 4 Prompts.
     - Update "Resources, Prompts & HTTP Routes" section to document all 4 prompts with their parameters and use cases.
     - Update Docker instructions to highlight the multi-stage non-root container deployment.
- **Grep Anchors**: `fppa_corridor_screening_assistant` in `manifest.yaml` and `README.md`
- **Acceptance Command**: `uv run pytest -m "not live_sda" ; if ($?) { uv run ruff check . } ; if ($?) { uv run ruff format --check . }`

