# STATE 10: Code Smell Remediation & Client Refactoring

## Green Baseline Checklist

- [x] Orchestrations 1 through 9 complete.
- [x] Baseline test suite verified: `uv run pytest -m "not live_sda" -q` -> `170 passed, 10 deselected`.
- [x] Baseline lint verified: `uv run ruff check .` -> clean.
- [x] Baseline formatting verified: `uv run ruff format --check .` -> clean.

## Wave Board

| Task ID | Wave | Title | Status | Worker | Assigned At | Completed At |
| --- | --- | --- | --- | --- | --- | --- |
| `10.1.1` | 1 | Shared HTTP Client Helper & Integration Models | complete | Subagent 10.1.1 | 2026-09-21T12:59:00 | 2026-09-21T13:02:00 |
| `10.2.1` | 2 | Refactor SDA, Tigerweb, NASS Clients | complete | Subagent 10.2.1 | 2026-09-21T13:17:00 | 2026-09-21T13:21:00 |
| `10.2.2` | 2 | Refactor Corridor Analysis & Scoring Encapsulation | complete | Subagent 10.2.2 | 2026-09-21T13:17:00 | 2026-09-21T13:21:00 |
| `10.3.1` | 3 | Full Test Suite Verification & Code Cleanliness | complete | Subagent 10.3.1 | 2026-09-21T13:22:00 | 2026-09-21T13:25:00 |
| `10.4.1` | 4 | CountyIdentifier Constructors & Caller Cleanup | pending | | | |
| `10.4.2` | 4 | Clean calculate_composite_le Overload Signatures | pending | | | |
| `10.5.1` | 5 | Final Regression & Standards Verification | pending | | | |

## Wave Gates

- **Wave 1** depends on baseline. Task `10.1.1` runs solo.
- **Wave 2** depends on `10.1.1`. Tasks `10.2.1` and `10.2.2` touch disjoint files and run in parallel (max 2 workers).
- **Wave 3** depends on `10.2.1` and `10.2.2`. Task `10.3.1` runs solo.
- **Wave 4** depends on `10.3.1`. Tasks `10.4.1` and `10.4.2` touch disjoint files and run in parallel (max 2 workers).
- **Wave 5** depends on `10.4.1` and `10.4.2`. Task `10.5.1` runs solo.
- At every wave boundary, run serially:
  - `uv run pytest -m "not live_sda"`
  - `uv run ruff check .`
  - `uv run ruff format --check .`

---

## Task Reports

### 10.1.1
- **Status**: complete
- **Changes**:
  - Implemented `src/fpac_soil_mcp/http_client.py` with `execute_http_request_with_retry`, supporting configurable retries, exponential backoff, status code validation, transient/injected `httpx.Client`, and normalized `HttpClientError` exceptions.
  - Added frozen `CountyIdentifier` model in `src/fpac_soil_mcp/integration_models.py` with FIPS validators and `full_fips` property.
- **Verification**: `uv run pytest -m "not live_sda" -q` (170 passed, 10 deselected) + `ruff check` + `ruff format --check` clean.

### 10.2.1
- **Status**: complete
- **Changes**:
  - Refactored `SDAClient._execute_query`, `TigerwebClient._post_query` / `_get_layer`, and `NassClient` HTTP requests to use shared `execute_http_request_with_retry`.
  - Added `CountyIdentifier` support to `NassClient.get_county_ag_profile` with backwards-compatible argument parsing.
- **Verification**: `uv run pytest tests/test_sda_client.py tests/test_tigerweb_client.py tests/test_nass_client.py` (62 passed).

### 10.2.2
- **Status**: complete
- **Changes**:
  - Adopted `CountyIdentifier` in `src/fpac_soil_mcp/corridor_analysis.py` for internal county passing.
  - Encapsulated corridor score evaluation and LESA aggregation in `src/fpac_soil_mcp/corridor_scoring.py` to remove feature envy.
- **Verification**: `uv run pytest tests/test_corridor_analysis.py tests/test_corridor_scoring.py` (17 passed).

### 10.3.1
- **Status**: complete
- **Changes**:
  - Verified full offline test suite across all Phase 1-3 features and tool contracts.
  - Verified Ruff linter and code formatting cleanliness across the entire repository.
- **Verification**: `uv run pytest -m "not live_sda"` (170 passed, 10 deselected) + `uv run ruff check .` + `uv run ruff format --check .` (clean).



