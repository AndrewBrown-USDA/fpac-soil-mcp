# STATE 19: PR #9 Code Review Remediation - Security, Sentinels, Model Consistency & Corridor Routing

## Green Baseline Checklist

- [x] Baseline test suite verified: `uv run pytest -m "not live_network and not agent_eval" -q` -> `245 passed, 10 deselected`.
- [x] Baseline lint verified: `uv run ruff check .` -> clean.
- [x] Baseline formatting verified: `uv run ruff format --check .` -> clean.

## PR #9 Code Review Findings Traceability

| Review Thread | Severity | Component | Finding | Planned Fix | Status |
|---|---|---|---|---|---|
| `r4127352625` | 🔴 High | `sda_client.py` | `build_dynamic_sdv_query` interpolates raw `mukeys_csv` without validation | Strict mukey digit regex validation | resolved |
| `r4127352683` | 🔴 High | `sda_client.py` | `build_dynamic_sdv_county_max_query` interpolates `areasymbol` without validation | Strict `validate_survey_area_symbol` check | resolved |
| `r4127352951` | 🟡 Medium | `sda_client.py` | `ALLOWED_SDV_TABLES` includes unsupported `cocropyld`/`corestrictions` | Prune unjoined tables from allowlist | resolved |
| `r4127352807` | 🟡 Medium | `models.py` | `PreliminaryLESAResponse` allows contradictory statutory threshold flag | `@model_validator` enforcing flag consistency | resolved |
| `r4127352729` | 🟡 Medium | `lesa.py` | `99.0` only treated as sentinel when `county_max <= 1.0` | Unconditional screening for `99.0`, `999.0` | resolved |
| `r4127352771` | 🟡 Medium | `lesa.py` | String index inputs fall back to NCCPI in `evaluate_lesa` | String-to-enum normalization | resolved |
| `r4127352850` | 🟡 Medium | `polygon_analysis.py` | `include_nccpi=False` opt-out ignored due to default index string | Gate query on explicit opt-in / index choice | resolved |
| `r4127352879` | 🟡 Medium | `polygon_analysis.py` | `str(num_r)` comparison misses float `99.0` sentinel | Numeric parsing and float sentinel screening | resolved |
| `r4127352922` | 🟡 Medium | `polygon_analysis.py` | Hard-coded `1.0` NCCPI benchmark understates candidate LE | Fetch live SDA county maximum rating | resolved |
| `r4127353024` | 🟡 Medium | `soil_tools.py` | Corridor LineStrings fail in `PolygonAnalyzer` | Route corridor geometries through buffer path | resolved |

## Wave Board

| Task ID | Wave | Title | Status | Worker | Assigned At | Completed At |
| --- | --- | --- | --- | --- | --- | --- |
| `19.1.1` | 1 | SQL Injection Hardening, Query Builder Validation & Allowlist Cleanup | done | worker-19-1-1 | 2026-09-28 | 2026-09-28 |
| `19.1.2` | 1 | LESA Response Model Statutory Consistency Validation | done | worker-19-1-2 | 2026-09-28 | 2026-09-28 |
| `19.2.1` | 2 | Sentinel Float Precision, Unconditional Screening & Index Normalization | done | worker-19-2-1 | 2026-09-28 | 2026-09-28 |
| `19.2.2` | 2 | Polygon Analysis NCCPI Opt-Out Gating, Float Sentinel Parsing & SDA Benchmark Lookup | done | worker-19-2-2 | 2026-09-28 | 2026-09-28 |
| `19.3.1` | 3 | Preliminary LESA Tool Corridor LineString Buffering & Routing | done | worker-19-3-1 | 2026-09-28 | 2026-09-28 |
| `19.3.2` | 3 | Comprehensive Unit, Mocked & Regression Test Suite Verification | done | worker-19-3-2 | 2026-09-28 | 2026-09-28 |
| `19.4.1` | 4 | End-to-End Test Suite Verification, State & PR Comment Matrix Finalization | done | orchestrator | 2026-09-28 | 2026-09-28 |

## Wave Gates

- **Wave 1**: Runs 2 independent tasks (`19.1.1`, `19.1.2`) across disjoint files (`src/fpac_soil_mcp/sda_client.py` and `src/fpac_soil_mcp/models.py`).
- **Wave 2**: Depends on Wave 1 and runs 2 independent tasks (`19.2.1`, `19.2.2`) across disjoint files (`src/fpac_soil_mcp/lesa.py` and `src/fpac_soil_mcp/polygon_analysis.py`).
- **Wave 3**: Depends on Wave 2 and runs 2 independent tasks (`19.3.1`, `19.3.2`) across disjoint files (`src/fpac_soil_mcp/tools/soil_tools.py` and `tests/`).
- **Wave 4**: Final verification and traceability matrix closure.
- At every wave boundary, run serially:
  - `uv run pytest -m "not live_network and not agent_eval" -q`
  - `uv run ruff check .`
  - `uv run ruff format --check .`

---

## Task Reports

### Task 19.1.1 Report: SQL Injection Hardening, Query Builder Validation & Allowlist Cleanup
- **Status**: done
- **Files**: `src/fpac_soil_mcp/sda_client.py`
- **Verification**: `uv run pytest tests/test_sda_client.py -q` passed (60 passed).

### Task 19.1.2 Report: LESA Response Model Statutory Consistency Validation
- **Status**: done
- **Files**: `src/fpac_soil_mcp/models.py`
- **Verification**: `uv run pytest tests/test_lesa.py -q` passed (31 passed).

### Task 19.2.1 Report: Sentinel Float Precision, Unconditional Screening & Index Normalization
- **Status**: done
- **Files**: `src/fpac_soil_mcp/lesa.py`
- **Verification**: `uv run pytest tests/test_lesa.py -q` passed (31 passed).

### Task 19.2.2 Report: Polygon Analysis NCCPI Opt-Out Gating, Float Sentinel Parsing & SDA Benchmark Lookup
- **Status**: done
- **Files**: `src/fpac_soil_mcp/polygon_analysis.py`
- **Verification**: `uv run pytest tests/test_polygon_analysis.py -q` passed (3 passed).

### Task 19.3.1 Report: Preliminary LESA Tool Corridor LineString Buffering & Routing
- **Status**: done
- **Files**: `src/fpac_soil_mcp/tools/soil_tools.py`
- **Verification**: `uv run pytest tests/test_tools.py -q` passed (17 passed).

### Task 19.3.2 Report: Comprehensive Unit, Mocked & Regression Test Suite Verification
- **Status**: done
- **Files**: `tests/`
- **Verification**: `uv run pytest -m "not live_network and not agent_eval" -q` passed (252 passed, 12 deselected).

### Task 19.4.1 Report: End-to-End Test Suite Verification, State & PR Comment Matrix Finalization
- **Status**: done
- **Files**: `planning/STATE_19.md`, `planning/tasks/19.4.1.todo.md`
- **Verification**: All 10 review findings verified and resolved; 100% clean test suite and linting.
