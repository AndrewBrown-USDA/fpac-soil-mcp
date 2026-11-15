# Execution Plan 50: Layered Module Refactor (`G31`)

## Goal & Scope

- **Goal**: Refactor `src/fpac_soil_mcp` from a flat 28-file root into layered subpackages (`core/`, `models/`, `spatial/`, `clients/`, `domain/`, `mcp/`) with downward-only dependencies, unified LESA/corridor scoring in `domain/lesa.py`, and zero circular-import workarounds. Update all `tests/`, `eval/`, `pyproject.toml`, and `main.py` imports directly, and remove the old flat modules.
- **In scope**:
  - Package restructuring into `core/`, `models/`, `spatial/`, `clients/`, `domain/`, `mcp/`
  - Merging `corridor_scoring.py` into `domain/lesa.py`
  - Splitting `sda_client.py` into `clients/sda/{client,sdv_registry,sql_templates}.py`
  - Removing lazy/mid-file circular imports (`map_contract.py`, `lesa_tools.py`, `tigerweb_client.py`)
  - Updating `tests/`, `eval/`, `pyproject.toml`, and `main.py` imports directly
- **Out of scope**:
  - Changing MCP tool schemas, `_meta` / `ToolResult` adoption (`G32`), or tool argument/error normalization (`G33`)
  - Adding `fppa://map/{geometry_hash}/layers` resource templates (`G34`)
  - Modifying `apps/agent-fpac-soil-openai-sdk/` (it is a separate MCP client project communicating over `/mcp`)
- **Verbatim constraints**:
  - "Update all imports across `tests/` and `eval/` directly in the same orchestration with no top-level shims."
  - "Track planning artifacts in Git and commit them separately as `docs(planning):`."

## Decision Log

- **2026-11-14 (D1)**: Update all imports across `tests/` and `eval/` directly in Orchestration 50 with **no** top-level backwards-compatibility shims.
- **2026-11-14 (D2)**: Track `planning/EXECUTION_PLAN_50.md`, `PROMPT_TEMPLATE_50.md`, `STATE_50.md`, and `tasks/50.*` in Git; commit them separately as `docs(planning):`.
- **2026-11-14 (D3)**: Max 4 concurrent workers per wave (strictly disjoint file scopes), `flash` worker model, escalate to `hydrogen` / coordinator after 2 consecutive failures.
- **2026-11-14 (D4)**: Re-scoped `50.6.1` (escalation rung 4). Wave 5 left `try/except ImportError` fallbacks to flat modules in `clients/sda/client.py`, `clients/sda/sdv_registry.py`, `clients/tigerweb.py`, and `domain/lesa.py`, plus a lazy `constants` import in `tigerweb.py`. Those fallbacks now sit in 50.6.1's scope so the flat deletion does not break them or hide breakage. No new task; no shims remain.

## Wave Table

| Wave | Tasks | Parallelism | Focus |
| :--- | :--- | :--- | :--- |
| 1 | `50.1.1`, `50.1.2` | 2 parallel | `core/` and `models/` |
| 2 | `50.2.1`, `50.2.2`, `50.2.3` | 3 parallel | `spatial/` and `clients/` |
| 3 | `50.3.1`, `50.3.2`, `50.3.3` | 3 parallel | `domain/` (including unified `lesa.py`) |
| 4 | `50.4.1` | 1 | `mcp/` surface, `pyproject.toml`, `main.py` |
| 5 | `50.5.1`, `50.5.2` | 2 parallel | Update `tests/` and `eval/` imports |
| 6 | `50.6.1` | 1 | Remove old flat modules & run `make check` + `make test-eval` |

---

## Task Specs

### `50.1.1` — Create `core/` package
- **Repo**: `fpac-soil-mcp`
- **Files in scope**: Can create `src/fpac_soil_mcp/core/{__init__.py,config.py,constants.py,authority.py,privacy.py,errors.py}`. Do not touch existing root files.
- **Depends on**: None
- **Spec**: Move/port `config.py`, `constants.py`, `authority.py`, and `privacy.py` into `src/fpac_soil_mcp/core/`. Add `errors.py` with base `DomainError` / `ValidationError` / `UpstreamError` types. Ensure zero imports from `models`, `spatial`, `clients`, `domain`, or `mcp`.
- **Acceptance**: `uv run python -c "import fpac_soil_mcp.core.config, fpac_soil_mcp.core.constants, fpac_soil_mcp.core.authority, fpac_soil_mcp.core.privacy, fpac_soil_mcp.core.errors"` exits 0.

### `50.1.2` — Create `models/` package
- **Repo**: `fpac-soil-mcp`
- **Files in scope**: Can create `src/fpac_soil_mcp/models/{__init__.py,soil.py,spatial.py,lesa.py,integration.py,cdl.py,map.py,case.py}`. Do not touch existing root files.
- **Depends on**: None (imports only from `core/` or standard/pydantic types; if `50.1.1` runs in parallel, import `fpac_soil_mcp.core.authority` or `fpac_soil_mcp.authority`—prefer `fpac_soil_mcp.core.authority` and verify after Wave 1).
- **Spec**: Split `models.py`, `case_models.py`, `integration_models.py`, `cdl_models.py`, and the Pydantic models from `map_contract.py` (`MapLegendItem`, `MapLayer`, `MapBlock`, `ResultAuthority`, `MAP_SCHEMA_VERSION`, `DISPLAY_CRS`, `AUTHORITY_LABEL`) into `src/fpac_soil_mcp/models/`.
- **Acceptance**: `uv run python -c "import fpac_soil_mcp.models"` exits 0.

### `50.2.1` — Create `spatial/` package
- **Repo**: `fpac-soil-mcp`
- **Files in scope**: Can create `src/fpac_soil_mcp/spatial/{__init__.py,geometry.py,map_builder.py}`.
- **Depends on**: `50.1.1`, `50.1.2`
- **Spec**: Port `geometry.py` into `spatial/geometry.py` and the builder/simplification functions from `map_contract.py` into `spatial/map_builder.py`. Remove the lazy `from fpac_soil_mcp.polygon_analysis import categorize_farmland_class` by placing `categorize_farmland_class` in `spatial/map_builder.py` (or `core/constants.py`).
- **Acceptance**: `uv run python -c "import fpac_soil_mcp.spatial.geometry, fpac_soil_mcp.spatial.map_builder"` exits 0.

### `50.2.2` — Create `clients/` HTTP, TIGERweb, NASS, and CDL adapters
- **Repo**: `fpac-soil-mcp`
- **Files in scope**: Can create `src/fpac_soil_mcp/clients/{__init__.py,http.py,tigerweb.py,nass.py,cdl.py}`.
- **Depends on**: `50.1.1`, `50.1.2`, `50.2.1`
- **Spec**: Port `http_client.py`, `tigerweb_client.py`, `nass_client.py`, and `cdl_client.py` into `clients/`. Update imports to use `core/`, `models/`, and `spatial/` (no lazy `constants` import in `tigerweb.py`).
- **Acceptance**: `uv run python -c "import fpac_soil_mcp.clients.http, fpac_soil_mcp.clients.tigerweb, fpac_soil_mcp.clients.nass, fpac_soil_mcp.clients.cdl"` exits 0.

### `50.2.3` — Create `clients/sda/` package
- **Repo**: `fpac-soil-mcp`
- **Files in scope**: Can create `src/fpac_soil_mcp/clients/sda/{__init__.py,client.py,sdv_registry.py,sql_templates.py}`.
- **Depends on**: `50.1.1`, `50.1.2`, `50.2.1`
- **Spec**: Split `sda_client.py` into `sdv_registry.py` (`SDV_RATING_REGISTRY`, `SdvRatingSpec`, `PRODUCTIVITY_PROVENANCE`, `PRODUCTIVITY_SEMANTICS`), `sql_templates.py`, and `client.py` (`SDAClient` + exceptions). Re-export public symbols from `clients/sda/__init__.py`.
- **Acceptance**: `uv run python -c "from fpac_soil_mcp.clients.sda import SDAClient, SDV_RATING_REGISTRY"` exits 0.

### `50.3.1` — Create `domain/` governance & reference modules
- **Repo**: `fpac-soil-mcp`
- **Files in scope**: Can create `src/fpac_soil_mcp/domain/{__init__.py,fppa.py,official_sources.py,workflow.py,site_assessment.py}`.
- **Depends on**: `50.1.1`, `50.1.2`
- **Spec**: Port `fppa.py`, `official_sources.py`, `workflow.py`, and `site_assessment.py` into `domain/`. Update imports to `core/` and `models/`.
- **Acceptance**: `uv run python -c "import fpac_soil_mcp.domain.fppa, fpac_soil_mcp.domain.official_sources, fpac_soil_mcp.domain.workflow, fpac_soil_mcp.domain.site_assessment"` exits 0.

### `50.3.2` — Create unified `domain/lesa.py`
- **Repo**: `fpac-soil-mcp`
- **Files in scope**: Can create `src/fpac_soil_mcp/domain/lesa.py`.
- **Depends on**: `50.1.1`, `50.1.2`, `50.3.1`
- **Spec**: Merge `lesa.py` and `corridor_scoring.py` into `domain/lesa.py`, preserving all public functions and classes (`evaluate_lesa`, `evaluate_corridor_lesa`, `evaluate_corridor_site_assessment`, `LESAEvaluationResult`, etc.) without duplicate criterion evaluators.
- **Acceptance**: `uv run python -c "from fpac_soil_mcp.domain.lesa import evaluate_lesa, evaluate_corridor_lesa, evaluate_corridor_site_assessment"` exits 0.

### `50.3.3` — Create `domain/polygon_analyzer.py` and `domain/corridor_analyzer.py`
- **Repo**: `fpac-soil-mcp`
- **Files in scope**: Can create `src/fpac_soil_mcp/domain/{polygon_analyzer.py,corridor_analyzer.py}`.
- **Depends on**: `50.2.1`, `50.2.2`, `50.2.3`, `50.3.2`
- **Spec**: Port `polygon_analysis.py` and `corridor_analysis.py` into `domain/`, updating all imports to `core/`, `models/`, `spatial/`, `clients/`, and `domain/lesa.py`.
- **Acceptance**: `uv run python -c "from fpac_soil_mcp.domain.polygon_analyzer import PolygonAnalyzer; from fpac_soil_mcp.domain.corridor_analyzer import CorridorAnalyzer"` exits 0.

### `50.4.1` — Create `mcp/` surface and update entry points
- **Repo**: `fpac-soil-mcp`
- **Files in scope**: Can create `src/fpac_soil_mcp/mcp/{__init__.py,app.py,routes.py,context.py}` and `src/fpac_soil_mcp/mcp/{tools,resources,prompts}/__init__.py` + submodules. Must edit `pyproject.toml`, `main.py`, `src/fpac_soil_mcp/__init__.py`.
- **Depends on**: `50.3.1`, `50.3.2`, `50.3.3`
- **Spec**: Port `app.py`, `routes.py`, `tools/*`, `resources/*`, `prompts/*` into `mcp/`. Add `mcp/context.py` (stub for `G32`). Remove tool-to-tool import in `mcp/tools/lesa.py` (call `CorridorAnalyzer` / `domain.lesa` directly). Update `pyproject.toml` console script to `fpac_soil_mcp.mcp.app:main` and `main.py` to import from `fpac_soil_mcp.mcp.app`.
- **Acceptance**: `uv run python -c "from fpac_soil_mcp.mcp.app import create_mcp_server; s = create_mcp_server()"` exits 0.

### `50.5.1` — Update `tests/` imports
- **Repo**: `fpac-soil-mcp`
- **Files in scope**: Must edit `tests/**/*.py` where old flat module paths are imported.
- **Depends on**: `50.4.1`
- **Spec**: Update all `from fpac_soil_mcp.<old>` imports in `tests/` to the new `core/`, `models/`, `spatial/`, `clients/`, `domain/`, `mcp/` paths.
- **Acceptance**: `uv run --group dev pytest tests/ -m "not live_network and not agent_eval"` passes.

### `50.5.2` — Update `eval/` imports
- **Repo**: `fpac-soil-mcp`
- **Files in scope**: Must edit `eval/**/*.py` where old flat module paths are imported.
- **Depends on**: `50.4.1`
- **Spec**: Update all `from fpac_soil_mcp.<old>` imports in `eval/` to the new `core/`, `models/`, `spatial/`, `clients/`, `domain/`, `mcp/` paths.
- **Acceptance**: `uv run --group dev pytest eval/ -m "not live_network and not agent_eval"` passes.

### `50.6.1` — Remove old flat modules & full verification
- **Repo**: `fpac-soil-mcp`
- **Files in scope**: Must edit `src/fpac_soil_mcp/clients/sda/client.py`, `clients/sda/sdv_registry.py`, `clients/tigerweb.py`, `domain/lesa.py` (re-scope D4: remove fallbacks to flat modules). Delete old flat files in `src/fpac_soil_mcp/` (keeping `__init__.py`, `data/`, and the 6 new subpackages).
- **Depends on**: `50.5.1`, `50.5.2`
- **Spec**: Replace each `try/except ImportError` fallback to a flat module with the direct layered import. Move `tigerweb.py`'s lazy `constants` import to module top via `core.constants`. Remove the superseded flat `.py` files and old `tools/`, `resources/`, `prompts/` directories under `src/fpac_soil_mcp/`. Run `make check` and `make test-eval` to verify zero regressions.
- **Acceptance**: `make check && make test-eval` exits 0.
