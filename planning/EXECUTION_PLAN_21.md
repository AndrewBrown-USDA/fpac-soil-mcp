# EXECUTION PLAN 21: Resolve Remaining PR #9 Review Findings

## Goal & Scope

**Goal**: Resolve all eight unresolved review findings from PR #9 without
regressing the green offline baseline. The work must preserve true separate
county accounting for multi-county AOIs, harden public SDA query builders,
correct sentinel and CPI interpretation behavior, and make the public LESA
corridor tool honor documented WKT and buffer inputs.

**In scope**
- SDA query-builder validation and SQL correctness.
- Polygon-analysis county partitioning, NCCPI opt-out, sentinel handling, and
  county benchmark lookup.
- LESA model/index fallback correctness.
- `calculate_preliminary_lesa` WKT and corridor routing behavior.
- Public corridor buffer parameters and propagation.
- Targeted regression tests, full offline verification, and Ruff checks.

**Out of scope**
- Reworking already-resolved or outdated PR #9 findings unless a regression
  test exposes them.
- Live-network execution as a required gate; live tests remain opt-in.
- Unrelated SDA clients, NASS/TIGERweb behavior, regulatory policy changes, or
  broad LESA scoring redesign.

**Verbatim constraints**
- “all unresolved comments should be addressed”
- “properly account for separate counties”
- “partition_and_weight”
- “Targeted offline tests + full offline suite and Ruff; live tests opt-in”

## Reconnaissance Log

- Repository: `D:\workspace\fpac-soil-mcp`; Python 3.11+, `uv`, pytest, Ruff.
- Conventions: root `AGENTS.md`; fixed SDA SQL, explicit validation/errors, no
  arbitrary SQL, and live tests excluded from the default path.
- Largest relevant files: `sda_client.py` 1174 lines, `lesa.py` 818,
  `soil_tools.py` 642, `models.py` 540, `polygon_analysis.py` 496.
  Workers must use grep anchors rather than whole-file reads.
- Baseline: `uv run pytest -m "not live_network"` => 254 passed, 12 deselected;
  `uv run ruff check .` passed; `uv run ruff format --check .` passed.
- Reference implementations: `corridor_analysis.py::analyze_corridor` and
  `geometry.py::buffer_centerline` already accept explicit buffer units;
  `SDAClient.validate_survey_area_symbol` is the validation pattern;
  `tests/test_polygon_analysis.py` contains the NCCPI opt-out and decimal
  sentinel patterns.
- Hazard: tasks touching the same source file are serialized. Full-suite
  verification is serial because external/shared resources can make concurrent
  suites flaky.

## Decision Log

- **2026-09-30**: Scope is all eight unresolved PR #9 findings; resolved and
  outdated findings are treated as shipped unless regression tests fail.
- **2026-09-30**: Wave order is SDA correctness, then polygon county analysis,
  then public LESA/tool behavior.
- **2026-09-30**: Multi-county AOIs must partition by distinct SDA area/county,
  fetch each partition's county maximum, normalize units within that partition,
  then acreage-weight the partition results.
- **2026-09-30**: Acceptance is targeted offline tests per task plus the full
  offline suite and Ruff checks; live SDA tests are opt-in.

## Wave & Dependency Table

| Wave | Task | Title | Files in scope | Depends on |
|---|---|---|---|---|
| 1 | 21.1.1 | Hardening SDA query builders and interpretation SQL | `src/fpac_soil_mcp/sda_client.py` | none |
| 1 | 21.1.2 | Adding SDA regression coverage | `tests/test_sda_client.py` | none |
| 2 | 21.2.1 | Partitioning polygon ratings by county | `src/fpac_soil_mcp/polygon_analysis.py` | 21.1.1 |
| 2 | 21.2.2 | Testing county partition and opt-out behavior | `tests/test_polygon_analysis.py` | 21.1.1 |
| 3 | 21.3.1 | Correcting LESA index fallback and sentinel behavior | `src/fpac_soil_mcp/lesa.py` | 21.2.1 |
| 3 | 21.3.2 | Wiring WKT and configurable corridor buffers | `src/fpac_soil_mcp/tools/soil_tools.py` | 21.2.1 |
| 4 | 21.3.3 | Testing LESA and corridor public inputs | `tests/test_lesa.py`, `tests/test_tools.py` | 21.3.1, 21.3.2 |
| 5 | 21.4.1 | Running final offline and lint verification | `planning/STATE_21.md` | 21.1.2, 21.2.2, 21.3.3 |

## Task Specifications

### 21.1.1 — Hardening SDA query builders and interpretation SQL
- **Repo**: `AndrewBrown-USDA/fpac-soil-mcp`
- **Files in scope**: `src/fpac_soil_mcp/sda_client.py`
- **Depends on**: none
- **Spec**: Validate and normalize `mukeys_csv` inside the public dynamic query
  builder using the existing positive-numeric rules; validate `areasymbol` at
  both builder boundaries; exclude negative sentinels in NCCPI SQL; make CPI
  matching exclude `NCCPI` (or select an exact CPI rule) in both query and
  county-max paths. Preserve fixed templates and explicit `SDAValidationError`.
- **Do not touch**: clients, public tool signatures, unrelated table allowlist
  policy, or live tests.
- **Grep anchors**: `SQL_PRODUCTIVITY_NCCPI`, `SQL_PRODUCTIVITY_CPI`,
  `build_dynamic_sdv_query`, `build_dynamic_sdv_county_max_query`,
  `validate_survey_area_symbol`.
- **Acceptance**: `uv run pytest tests/test_sda_client.py`.

### 21.1.2 — Adding SDA regression coverage
- **Files in scope**: `tests/test_sda_client.py`
- **Depends on**: none
- **Spec**: Add assertions for direct builder mukey injection rejection, direct
  areasymbol validation, negative-sentinel SQL exclusion, and CPI/NCCPI
  disambiguation. Match existing test style.
- **Do not touch**: source code or live-network tests.
- **Grep anchors**: `TestSDAValidation`, `build_dynamic_sdv_query`,
  `build_dynamic_sdv_county_max_query`.
- **Acceptance**: `uv run pytest tests/test_sda_client.py`.

### 21.2.1 — Partitioning polygon ratings by county
- **Files in scope**: `src/fpac_soil_mcp/polygon_analysis.py`
- **Depends on**: 21.1.1
- **Spec**: Preserve the `include_nccpi=False` short circuit for both rating and
  benchmark calls; normalize decimal and negative sentinels as unrated; replace
  first-area-symbol normalization with distinct area/county partitions. Fetch
  one benchmark per partition, assign each map unit to its partition, compute
  partition LE values, then acreage-weight them into the existing aggregate.
  Retain explicit warnings/fallbacks and existing response shape.
- **Do not touch**: SDA SQL, tool signatures, or unrelated geometry.
- **Grep anchors**: `include_nccpi`, `rating_map`, `county_max`,
  `primary_areasymbol`, `candidate_le_score`.
- **Acceptance**: `uv run pytest tests/test_polygon_analysis.py`.

### 21.2.2 — Testing county partition and opt-out behavior
- **Files in scope**: `tests/test_polygon_analysis.py`
- **Depends on**: 21.1.1
- **Spec**: Add mocked tests proving separate area symbols receive separate
  county maxima and produce an acreage-weighted result; prove opt-out makes no
  interpretation or benchmark request; cover `99.0`, `999.0`, `-99.0`, and
  `-999.0` as unrated.
- **Do not touch**: production code or shared fixtures outside this file.
- **Grep anchors**: `test_analyze_polygon_include_nccpi_false_skips_rating_query`,
  `test_analyze_polygon_treats_decimal_99_as_unrated_nccpi`.
- **Acceptance**: `uv run pytest tests/test_polygon_analysis.py`.

### 21.3.1 — Correcting LESA index fallback and sentinel behavior
- **Files in scope**: `src/fpac_soil_mcp/lesa.py`
- **Depends on**: 21.2.1
- **Spec**: Treat raw 99/999 and negative sentinels as unrated independent of
  county scale; normalize supported string productivity indexes to
  `ProductivityIndexType` before constructing either fallback summary so the
  public result never silently reports NCCPI for CSR2/CPI/Storie.
- **Do not touch**: statutory thresholds, SA scoring, or unrelated models.
- **Grep anchors**: sentinel normalization near the rating parser,
  `evaluate_lesa`, `LandEvaluationSummary`, `ProductivityIndexType`.
- **Acceptance**: `uv run pytest tests/test_lesa.py`.

### 21.3.2 — Wiring WKT and configurable corridor buffers
- **Files in scope**: `src/fpac_soil_mcp/tools/soil_tools.py`
- **Depends on**: 21.2.1
- **Spec**: Make `calculate_preliminary_lesa` accept documented WKT polygon and
  line strings through existing geometry helpers; route corridor lines through
  corridor buffering/analysis rather than forcing `PolygonAnalyzer`; expose
  explicit corridor buffer distance and units with the existing default
  behavior, and pass them through to buffering and analysis.
- **Do not touch**: `corridor_analysis.py`, geometry algorithms, or unrelated
  MCP tools.
- **Grep anchors**: `calculate_preliminary_lesa`, `parse_geojson_geometry`,
  `buffer_centerline`, `analyze_corridor_fppa`.
- **Acceptance**: `uv run pytest tests/test_tools.py`.

### 21.3.3 — Testing LESA and corridor public inputs
- **Files in scope**: `tests/test_lesa.py`, `tests/test_tools.py`
- **Depends on**: 21.3.1, 21.3.2
- **Spec**: Add regression coverage for string productivity-index fallback,
  unconditional sentinel handling, WKT polygon/line inputs, corridor routing,
  and explicit buffer distance/unit propagation. Use mocked clients and existing
  fixtures; do not require network access.
- **Do not touch**: production code or live tests.
- **Grep anchors**: `evaluate_lesa`, `calculate_preliminary_lesa`,
  `analyze_corridor_fppa`.
- **Acceptance**: `uv run pytest tests/test_lesa.py tests/test_tools.py`.

### 21.4.1 — Running final offline and lint verification
- **Files in scope**: `planning/STATE_21.md`
- **Depends on**: 21.1.2, 21.2.2, 21.3.3
- **Spec**: Run the complete offline suite and both Ruff checks serially, record
  exact counts and outcomes in STATE_21, and note live SDA tests as opt-in.
- **Do not touch**: source or test files.
- **Acceptance**: `uv run pytest -m "not live_network"`; `uv run ruff check .`;
  `uv run ruff format --check .`.
