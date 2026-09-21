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
| `10.2.1` | 2 | Refactor SDA, Tigerweb, NASS Clients | pending | | | |
| `10.2.2` | 2 | Refactor Corridor Analysis & Scoring Encapsulation | pending | | | |
| `10.3.1` | 3 | Full Test Suite Verification & Code Cleanliness | pending | | | |

## Wave Gates

- **Wave 1** depends on baseline. Task `10.1.1` runs solo.
- **Wave 2** depends on `10.1.1`. Tasks `10.2.1` and `10.2.2` touch disjoint files and run in parallel (max 2 workers).
- **Wave 3** depends on `10.2.1` and `10.2.2`. Task `10.3.1` runs solo.
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

