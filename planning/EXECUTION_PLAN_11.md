# EXECUTION PLAN 11: PR #5 Code Review Findings Remediation

## Goal & Scope

### Goal
Remediate the 5 code review findings identified on PR #5 across `http_client.py`, `nass_client.py`, `corridor_analysis.py`, and `tests/test_http_client.py`, ensuring complete backward compatibility, robust retry/error handling, and comprehensive unit test coverage with 0 regressions.

### In Scope
1. **HTTP Client Status Retry Disambiguation & Direct Tests (`http_client.py` & `tests/test_http_client.py`)**:
   - Fix `execute_http_request_with_retry` in `src/fpac_soil_mcp/http_client.py` to distinguish `retry_status_codes=None` (defaults to `{429, 500, 502, 503, 504}`) from an explicitly passed empty set/frozenset `set()` (which must disable status-based retries).
   - Create comprehensive unit test suite `tests/test_http_client.py` providing direct test coverage for success, retryable statuses, non-retryable statuses, disabled status retries (`retry_status_codes=set()`), request failures, max retry exhaustion, exponential backoff, injected client reuse, and transient client lifecycle/cleanup.
2. **NASS Client Positional Compatibility & 404 UNAVAILABLE Mapping (`nass_client.py` & `tests/test_nass_client.py`)**:
   - Restore legacy positional signature compatibility in `NassClient.get_county_ag_profile`: ensure `(state_fips, county_fips, county_name)` positional calls continue working cleanly alongside `county: CountyIdentifier` calls (e.g. supporting `get_county_ag_profile("19", "169", "Story")` as well as keyword-only or overloaded forms).
   - Update `get_county_ag_profile` error handling to catch `HttpStatusError` when status code is `404` and map it to `IntegrationStatus.UNAVAILABLE` with a clear explanation instead of generic `ERROR`.
   - Add unit tests in `tests/test_nass_client.py` verifying legacy 3-arg positional calls and 404 `HttpStatusError` returning `UNAVAILABLE`.
3. **Corridor Analysis Partition Geometry Attribute & Mapping Compatibility (`corridor_analysis.py` & `integration_models.py`)**:
   - Fix `_county_identifier` and loop processing in `src/fpac_soil_mcp/corridor_analysis.py` to seamlessly handle both `CountyPartitionGeometry` Pydantic model instances and dictionary mappings without raising `AttributeError` (using attribute access or mapping helpers safely).
   - Add or update tests in `tests/test_corridor_analysis.py` and `tests/test_tigerweb_client.py` ensuring corridor analysis succeeds when `partition_geometry_by_counties` returns real `CountyPartitionGeometry` objects.
4. **Full Suite Verification & Code Standards (`tests/` & Ruff)**:
   - Run full offline test suite across all Phase 1-3 features and tool contracts.
   - Run Ruff linter and format checks.

### Out of Scope
- Altering public MCP tool schemas, tool names, or JSON-RPC responses.
- Changes to statutory FPPA score algorithms or regulatory constants.
- Changes to live USDA SDA / TIGERweb endpoints.

### Verbatim Constraints
- "Preserve all existing MCP tool signatures, prompt templates, and Pydantic response models."
- "Maintain backward compatibility for callers of `SDAClient`, `TigerwebClient`, and `NassClient`."
- "Ensure 100% test suite passes without live network access on the standard test runner (`uv run pytest -m 'not live_sda'`)."
- "Max concurrent workers: 2."

---

## Decision Log

- **2026-09-21**: Remediate all 5 PR #5 code review discussion items.
- **2026-09-21**: In `http_client.py`, check `if retry_status_codes is None:` to apply default retry status codes, allowing `set()` or `frozenset()` to disable status retries.
- **2026-09-21**: In `nass_client.py`, support positional parameter compatibility by checking if first argument is a `CountyIdentifier` or string (or using `state_fips: str | CountyIdentifier | None = None, county_fips: str | None = None, ...` / dispatch).
- **2026-09-21**: In `nass_client.py`, intercept `HttpStatusError` with `status_code == 404` to return `IntegrationStatus.UNAVAILABLE`.
- **2026-09-21**: In `corridor_analysis.py`, ensure `_county_identifier` and acreage extraction access fields safely whether the segment item is a `CountyPartitionGeometry` model or a `dict`.
- **2026-09-21**: Create `tests/test_http_client.py` for comprehensive direct testing of the shared HTTP utility.

---

## Technical Reconnaissance

- **Target Files**:
  - `src/fpac_soil_mcp/http_client.py` (~90 lines)
  - `src/fpac_soil_mcp/nass_client.py` (~215 lines)
  - `src/fpac_soil_mcp/corridor_analysis.py` (~780 lines)
  - `src/fpac_soil_mcp/integration_models.py` (~340 lines)
  - `tests/test_http_client.py` (New file)
  - `tests/test_nass_client.py` (~180 lines)
  - `tests/test_corridor_analysis.py` (~320 lines)
- **Baseline Test Count**: 172 passed, 10 deselected.
- **Linter & Formatter**: Ruff clean.

---

## Hazards and Guardrails

- **Parameter Signature Hazard**: Any refactoring to `NassClient.get_county_ag_profile` signature must not break existing callers calling `get_county_ag_profile(state_fips="19", county_fips="169", county_name="Story")`, `get_county_ag_profile("19", "169", "Story")`, or `get_county_ag_profile(county=county_obj)`.
- **HTTP Exception Handling in Clients**: Because `execute_http_request_with_retry` raises `HttpStatusError` for 4xx/5xx responses, client-specific status handling (like 404 for NASS QuickStats) must catch `HttpStatusError` specifically before fallback logging.
- **Model vs Dict Polymorphism**: `CountyPartitionGeometry` is a Pydantic model with `__getitem__` and `.get()` helper methods, but `getattr(obj, "field", ...)` or `isinstance(obj, CountyPartitionGeometry)` makes corridor analysis completely resilient to both model instances and raw dicts.

---

## Wave Dependency Graph

```
+-------------------------------------------------------------+
| Wave 1: HTTP Client Retry Disambiguation & Direct Tests     |
| - Task 11.1.1: Fix http_client.py status retry check &      |
|                create tests/test_http_client.py             |
+-------------------------------------------------------------+
                               |
                               v
+-------------------------------------------------------------+
| Wave 2: NASS & Corridor Analysis Remediation (Parallel)     |
| - Task 11.2.1: Fix NassClient signature & 404 UNAVAILABLE   |
| - Task 11.2.2: Fix CorridorAnalyzer partition model handling|
+-------------------------------------------------------------+
                               |
                               v
+-------------------------------------------------------------+
| Wave 3: Final Regression & Standards Verification           |
| - Task 11.3.1: Full suite test run & Ruff checks            |
+-------------------------------------------------------------+
```

---

## Wave & Task Specifications

### Wave 1

#### Task 11.1.1: HTTP Client Retry Disambiguation & Unit Tests
- **Repo**: `D:\workspace\fpac-soil-mcp`
- **Files in scope**: `src/fpac_soil_mcp/http_client.py`, `tests/test_http_client.py`
- **Depends on**: None
- **Spec**:
  1. In `src/fpac_soil_mcp/http_client.py`, update `execute_http_request_with_retry`:
     - Change `retryable = retry_status_codes or frozenset({429, 500, 502, 503, 504})` to:
       ```python
       retryable = (
           retry_status_codes
           if retry_status_codes is not None
           else frozenset({429, 500, 502, 503, 504})
       )
       ```
     - Preserve all other retry, exponential backoff, client ownership, and error normalization behaviors.
  2. Create `tests/test_http_client.py`:
     - Test successful request with default settings.
     - Test retryable status codes (e.g. 503, 429) retrying up to `max_retries` and recovering on later attempt.
     - Test non-retryable 4xx status codes (e.g. 400, 401) failing immediately with `HttpStatusError` without retry.
     - Test explicitly passing `retry_status_codes=set()` or `frozenset()` disabling status retries on 500/503.
     - Test network error retries (`httpx.RequestError`) up to `max_retries` raising `HttpRequestError`.
     - Test exponential backoff calculation and invocation.
     - Test injected `httpx.Client` is NOT closed upon request completion (`owns_client == False`).
     - Test transient `httpx.Client` created when `client=None` IS closed upon exit (`owns_client == True`).
     - Test invalid arguments validation (`max_retries < 0`, `backoff_factor < 0`).
- **Grep Anchors**: `def execute_http_request_with_retry` in `src/fpac_soil_mcp/http_client.py`
- **Acceptance Command**: `uv run pytest tests/test_http_client.py`

---

### Wave 2

#### Task 11.2.1: NASS Client Positional Compatibility & 404 Mapping
- **Repo**: `D:\workspace\fpac-soil-mcp`
- **Files in scope**: `src/fpac_soil_mcp/nass_client.py`, `tests/test_nass_client.py`
- **Depends on**: Task 11.1.1
- **Spec**:
  1. In `src/fpac_soil_mcp/nass_client.py`:
     - Update `get_county_ag_profile` method signature and dispatch logic:
       ```python
       def get_county_ag_profile(
           self,
           state_fips: str | CountyIdentifier | None = None,
           county_fips: str | None = None,
           county_name: str | None = None,
           state_alpha: str | None = None,
           census_year: int | None = None,
           *,
           county: CountyIdentifier | None = None,
       ) -> CountyAgProfile:
       ```
     - If the first positional argument `state_fips` is an instance of `CountyIdentifier`, unpack its `state_fips`, `county_fips`, `county_name`, and `state_alpha`.
     - If `county` keyword argument is provided, unpack its values.
     - Verify positional calls `get_county_ag_profile("19", "169", "Story")` work without error.
     - Handle `HttpStatusError` when `exc.status_code == 404`: return `CountyAgProfile` with `status=IntegrationStatus.UNAVAILABLE` and explanatory error message.
  2. In `tests/test_nass_client.py`:
     - Add test for positional argument calling `client.get_county_ag_profile("19", "169", "Story")`.
     - Add test for passing `CountyIdentifier` positionally as first argument.
     - Add test for 404 response returning `IntegrationStatus.UNAVAILABLE`.
- **Grep Anchors**: `def get_county_ag_profile` in `src/fpac_soil_mcp/nass_client.py`
- **Acceptance Command**: `uv run pytest tests/test_nass_client.py`

#### Task 11.2.2: Corridor Analysis Partition Geometry & Segment Compatibility
- **Repo**: `D:\workspace\fpac-soil-mcp`
- **Files in scope**: `src/fpac_soil_mcp/corridor_analysis.py`, `tests/test_corridor_analysis.py`
- **Depends on**: Task 11.1.1
- **Spec**:
  1. In `src/fpac_soil_mcp/corridor_analysis.py`:
     - Update `_county_identifier(segment: dict[str, Any] | CountyPartitionGeometry) -> CountyIdentifier` to handle both `CountyPartitionGeometry` objects and dictionary mappings:
       ```python
       def _county_identifier(segment: dict[str, Any] | CountyPartitionGeometry) -> CountyIdentifier:
           """Build one validated county identity from a TIGERweb segment mapping or model."""
           if isinstance(segment, CountyPartitionGeometry):
               return CountyIdentifier(
                   state_fips=segment.state_fips,
                   county_fips=segment.county_fips,
                   county_name=segment.county_name,
                   state_name=segment.state_name,
               )
           return CountyIdentifier.from_dict(
               {
                   "state_fips": str(segment.get("state_fips", "00")),
                   "county_fips": str(segment.get("county_fips", "000")),
                   "county_name": str(segment.get("county_name", "Unknown County")),
                   "state_name": segment.get("state_name"),
               }
           )
       ```
     - In `analyze_corridor`, ensure segment geometry and calculated acres extraction cleanly support both `CountyPartitionGeometry` instances (using `seg.geometry` / `seg.calculated_acres`) and dictionary keys (using `seg["geometry"]` / `seg.get("calculated_acres")`).
  2. In `tests/test_corridor_analysis.py`:
     - Add a test verifying `analyze_corridor` works seamlessly when `tigerweb_client.partition_geometry_by_counties` returns real `CountyPartitionGeometry` instances.
- **Grep Anchors**: `def _county_identifier` and `for seg in segments_raw:` in `src/fpac_soil_mcp/corridor_analysis.py`
- **Acceptance Command**: `uv run pytest tests/test_corridor_analysis.py`

---

### Wave 3

#### Task 11.3.1: Full Suite Verification & Code Cleanliness
- **Repo**: `D:\workspace\fpac-soil-mcp`
- **Files in scope**: Entire repository
- **Depends on**: Task 11.2.1, Task 11.2.2
- **Spec**:
  1. Execute full offline test suite: `uv run pytest -m "not live_sda"` and verify 100% pass rate.
  2. Run Ruff linter: `uv run ruff check .` and ensure 0 violations.
  3. Run Ruff format check: `uv run ruff format --check .` and ensure 100% formatting compliance.
- **Acceptance Command**: `uv run pytest -m "not live_sda" ; if ($?) { uv run ruff check . } ; if ($?) { uv run ruff format --check . }`

