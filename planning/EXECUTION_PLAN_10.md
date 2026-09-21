# EXECUTION PLAN 10: Code Smell Remediation & Client Refactoring

## Goal & Scope

### Goal
Refactor domain abstractions, data clumps, feature envy, and HTTP client duplication identified in the code review across `src/fpac_soil_mcp`, preserving 100% public MCP tool interfaces, schema backwards compatibility, and test suite integrity.

### In Scope
1. **Shared HTTP Client / Retry Helper (`http_client.py`)**:
   - Extract common HTTP retry, backoff, status validation, and error normalization into a shared utility or base client (`src/fpac_soil_mcp/http_client.py`).
   - Refactor `SDAClient`, `TigerwebClient`, and `NassClient` to use the shared HTTP helper/pattern without changing public method signatures.
2. **County Identifier Value Object (`integration_models.py` & `corridor_analysis.py`)**:
   - Define a `CountyIdentifier` or `CountyLocation` frozen model in `integration_models.py` bundling `(state_fips, county_fips, county_name, state_name, state_alpha)`.
   - Use `CountyIdentifier` across `tigerweb_client.py`, `corridor_analysis.py`, and `nass_client.py` internal helpers while preserving legacy parameter compatibility.
3. **Encapsulate Corridor Domain Calculations (`corridor_scoring.py` & `corridor_analysis.py`)**:
   - Eliminate Feature Envy in `corridor_scoring.py` by placing score and rating aggregations directly on container/result classes or dedicated calculation methods.
4. **Validation & Regression Verification**:
   - Ensure all 170+ unit and contract tests pass with zero regressions.
   - Run Ruff linter and formatting checks.

### Out of Scope
- Changes to external API endpoints, SQL templates, or statutory FPPA constants.
- Changes to MCP tool names, parameter schemas, or JSON-RPC contracts.
- Modifying Phase 4/5 roadmap deliverables.

### Verbatim Constraints
- "Preserve all existing MCP tool signatures, prompt templates, and Pydantic response models."
- "Maintain backward compatibility for callers of `SDAClient`, `TigerwebClient`, and `NassClient`."
- "Ensure 100% test suite passes without live network access on the standard test runner (`uv run pytest -m 'not live_sda'`)."

---

## Decision Log

- **2026-09-21**: Remediate all 3 code smells identified in review: Primitive Obsession / Data Clumps, Feature Envy, and Duplicated HTTP Client logic.
- **2026-09-21**: Parallelism limit set to max 2 concurrent workers.
- **2026-09-21**: Implement shared HTTP helper in `src/fpac_soil_mcp/http_client.py` and import into SDA, TIGERweb, and NASS clients.
- **2026-09-21**: Centralize `CountyIdentifier` in `src/fpac_soil_mcp/integration_models.py`.

---

## Technical Reconnaissance

- **Key Files & Sizes**:
  - `src/fpac_soil_mcp/integration_models.py`: ~220 lines.
  - `src/fpac_soil_mcp/sda_client.py`: ~450 lines.
  - `src/fpac_soil_mcp/tigerweb_client.py`: ~315 lines.
  - `src/fpac_soil_mcp/nass_client.py`: ~200 lines.
  - `src/fpac_soil_mcp/corridor_analysis.py`: ~780 lines.
  - `src/fpac_soil_mcp/corridor_scoring.py`: ~450 lines.
- **Baseline Test Suite**: 170 passed, 10 deselected in ~2.7s (`uv run pytest -m "not live_sda"`).
- **Linter & Formatter**: Ruff check and format are clean.

---

## Hazards and Guardrails

- **Client Mock Breaking Hazard**: `tests/conftest.py` and test suites mock `httpx.Client.post` and `httpx.Client.get`. The shared HTTP helper must continue utilizing `httpx.Client` or existing injected client instances so mock transports in `conftest.py` and `test_sda_client.py` / `test_tigerweb_client.py` / `test_nass_client.py` operate seamlessly.
- **Pydantic Model Schema Stability**: Do not remove existing fields on `CountyPartitionGeometry` or `CountyAgProfile`. Add `CountyIdentifier` as a composable model or attribute without breaking dict/keyword unpacking.
- **Method Signature Backward Compatibility**: Keep existing keyword arguments on public methods (`get_county_ag_profile`, `get_intersecting_counties`, etc.) and adapt them internally to use `CountyIdentifier`.

---

## Wave Dependency Graph

```text
10.1.1 Shared HTTP Client Helper & Integration Models (http_client.py, integration_models.py)
  ├── 10.2.1 Refactor SDAClient, TigerwebClient, and NassClient to Shared HTTP & CountyIdentifier (sda_client.py, tigerweb_client.py, nass_client.py)
  └── 10.2.2 Refactor Corridor Analysis & Scoring Encapsulation (corridor_analysis.py, corridor_scoring.py)
         └── 10.3.1 Full Test Suite Verification & Code Cleanliness (tests/)
```

---

## Tasks

### Task 10.1.1: Shared HTTP Client Helper & Integration Models
- **ID**: `10.1.1`
- **Files in scope**: `src/fpac_soil_mcp/http_client.py`, `src/fpac_soil_mcp/integration_models.py`
- **Depends on**: None (Wave 1)
- **Spec prose**:
  1. Create `src/fpac_soil_mcp/http_client.py` providing a robust, reusable request helper (e.g. `execute_http_request_with_retry` or a lightweight `BaseHttpClient`) that encapsulates exponential backoff, retry handling, status code checking, and error normalization for `httpx.Client`.
  2. In `src/fpac_soil_mcp/integration_models.py`, define a `CountyIdentifier` frozen Pydantic model with fields: `state_fips: str`, `county_fips: str`, `county_name: str`, `state_name: str | None = None`, `state_alpha: str | None = None`, along with helper constructors from dict or FIPS strings.
- **Constraints**:
  - Do not break existing model fields or validations on `CountyPartitionGeometry`, `CountyAgProfile`, or `UrbanExemptionRecord`.
- **Grep anchors**:
  - `class IntegrationStatus` in `src/fpac_soil_mcp/integration_models.py`
- **Acceptance command**:
  `uv run pytest tests/test_integration_models.py tests/test_config.py`

---

### Task 10.2.1: Refactor Clients to use Shared HTTP Helper & CountyIdentifier
- **ID**: `10.2.1`
- **Files in scope**: `src/fpac_soil_mcp/sda_client.py`, `src/fpac_soil_mcp/tigerweb_client.py`, `src/fpac_soil_mcp/nass_client.py`, `tests/test_sda_client.py`, `tests/test_tigerweb_client.py`, `tests/test_nass_client.py`
- **Depends on**: `10.1.1` (Wave 2)
- **Spec prose**:
  1. Refactor `SDAClient._execute_query` to use the shared HTTP helper from `src/fpac_soil_mcp/http_client.py`.
  2. Refactor `TigerwebClient` HTTP requests (`_post_query`, `_get_layer`) to use the shared HTTP helper.
  3. Refactor `NassClient` HTTP requests to use the shared HTTP helper and accept `CountyIdentifier` (with backward-compatible `*args`/`**kwargs` or optional overload).
  4. Ensure all client unit tests pass with mocked httpx transports.
- **Constraints**:
  - Do not change public method signatures or error exception classes raised (`SDAClientError`, `TigerwebClientError`, `NassClientError`).
- **Grep anchors**:
  - `class SDAClient:` in `src/fpac_soil_mcp/sda_client.py`
  - `class TigerwebClient:` in `src/fpac_soil_mcp/tigerweb_client.py`
  - `class NassClient:` in `src/fpac_soil_mcp/nass_client.py`
- **Acceptance command**:
  `uv run pytest tests/test_sda_client.py tests/test_tigerweb_client.py tests/test_nass_client.py`

---

### Task 10.2.2: Refactor Corridor Analysis & Scoring Encapsulation
- **ID**: `10.2.2`
- **Files in scope**: `src/fpac_soil_mcp/corridor_analysis.py`, `src/fpac_soil_mcp/corridor_scoring.py`, `tests/test_corridor_analysis.py`, `tests/test_corridor_scoring.py`
- **Depends on**: `10.1.1` (Wave 2)
- **Spec prose**:
  1. In `src/fpac_soil_mcp/corridor_analysis.py`, use `CountyIdentifier` in place of loose `(county_fips, state_fips, county_name, state_name)` parameter tuples in internal helper methods.
  2. In `src/fpac_soil_mcp/corridor_scoring.py`, resolve Feature Envy by encapsulating aggregation logic (e.g. composite LE calculation, site assessment score compilation) into cleanly structured methods or container evaluation helpers.
  3. Verify all existing corridor scoring and multi-county analysis behaviors and tolerance checks remain exact.
- **Constraints**:
  - Do not modify statutory 7 CFR § 658.5(c) rules or maximum points in `constants.py`.
  - Preserve 0.1% sum reconciliation tolerance.
- **Grep anchors**:
  - `class CorridorAnalyzer:` in `src/fpac_soil_mcp/corridor_analysis.py`
  - `def calculate_composite_le(` in `src/fpac_soil_mcp/corridor_scoring.py`
- **Acceptance command**:
  `uv run pytest tests/test_corridor_analysis.py tests/test_corridor_scoring.py`

---

### Task 10.3.1: Full Test Suite Verification & Code Cleanliness
- **ID**: `10.3.1`
- **Files in scope**: `tests/test_phase3_contracts.py`, `tests/test_tools.py`, `tests/test_server.py`
- **Depends on**: `10.2.1`, `10.2.2` (Wave 3)
- **Spec prose**:
  1. Run the entire offline test suite and verify end-to-end contracts and tool registrations.
  2. Verify that Ruff linting and formatting pass without warnings.
- **Constraints**:
  - No changes to MCP tool schemas or tool names.
- **Acceptance command**:
  `uv run pytest -m "not live_sda" && uv run ruff check . && uv run ruff format --check .`
