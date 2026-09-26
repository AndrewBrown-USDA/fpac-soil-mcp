# EXECUTION PLAN 14: Prompt Documentation Enhancement & Pi Agent Evaluation Suite

## Goal & Scope

### Goal
Implement the prompt and documentation enhancements defined in `planning/RESEARCH_PROMPT_EXAMPLE_ENHANCE.md` across `QUICKSTART.md`, `README.md`, `manifest.yaml`, and `server.json`, and establish a dedicated, isolated evaluation test suite and runner script using the `pi` coding agent CLI to test natural-language prompt scenarios against the live/mocked MCP server between releases without contaminating standard unit test runs.

### In Scope
1. **Documentation & Manifest Enhancement (`QUICKSTART.md`, `README.md`, `manifest.yaml`, `server.json`)**:
   - Update `QUICKSTART.md` with the full 6-category enhanced prompt catalog covering Phase 1 (point/mukey/scope), Phase 2 (polygon screening & SSURGO polygon retrieval), and Phase 3 (Census 2020 urban exemption, NCCPI soil interpretations, multi-county corridor screening, Form NRCS-CPA-106 LESA evaluation, and all 4 assistant prompts).
   - Update `README.md` to document the 4 MCP prompts, multi-turn conversational workflow examples (e.g. multi-county transmission corridor analysis), and clear usage instructions.
   - Synchronize tool descriptions, resource URIs, and prompt parameters across `manifest.yaml` and `server.json`.
2. **Structured Prompt Test Fixtures (`eval/prompt_test_cases.json`)**:
   - Create a structured JSON dataset under `eval/` containing test cases for each tool, resource, and assistant prompt.
   - Include prompt text, target tool name, required input parameters, expected output key facts (e.g., FARMLNDCL, mukey, acres, LESA score, statutory disclaimer), and category metadata.
3. **Pi Agent Evaluation Harness & Pytest Suite (`eval/test_agent_eval.py`, `pyproject.toml`)**:
   - Add `agent_eval` marker to `pyproject.toml` with default exclusion instructions (`-m "not agent_eval and not live_network"`).
   - Implement `eval/test_agent_eval.py` that sets up an isolated temporary workspace outside the repository (preventing the agent from reading source code directly), generates an ephemeral `.mcp.json` pointing to `fpac-soil-mcp`, executes `pi` in non-interactive mode (`--mode json -p`), verifies MCP tool loading, and asserts on tool call chains and expected outputs.
4. **Standalone Release Evaluation CLI Script (`eval/run_evals.py`)**:
   - Create `eval/run_evals.py` allowing developers to execute agent evaluation benchmarks between releases with configurable models (`AGENT_EVAL_MODEL`), filtered test categories, timing metrics, and summary reporting.
5. **Quality & Validation**:
   - Verify all unit tests remain green (`uv run pytest -m "not live_network and not agent_eval"`).
   - Verify code formatting and linting (`uv run ruff check .`, `uv run ruff format --check .`).

### Out of Scope
- Modifying underlying FastMCP tool signatures or core calculation algorithms in `src/fpac_soil_mcp/`.
- Running agent evaluation tests automatically in standard offline CI runs (they require `pi` CLI and API keys and are scoped to release evaluations).
- Committing API keys or ephemeral agent session logs.

### Verbatim Constraints
- "JSON format for prompt dataset, located at `eval/prompt_test_cases.json`, shared with docs, at least 1 example that targets each tool."
- "Isolation strategy: `temp_sandbox_dir`, MCP config generation: `temp_mcp_config` so the agent cannot cheat by reading repository source files."
- "Pytest marker: `agent_eval`, default exclusion: true, runner helper script: `eval/run_evals.py`."
- "Execution mode: `json_mode`, model override env var: `AGENT_EVAL_MODEL`, tool verification: `verify_mcp_and_assertion`."
- "Preserve all existing 192 unit tests green and lint clean."

---

## Decision Log

- **2026-09-23**: Prompt test cases structured in JSON format at `eval/prompt_test_cases.json` representing all 9 tools, 3 resources, and 4 assistant prompts.
- **2026-09-23**: Documentation (`QUICKSTART.md`, `README.md`) updated with Phase 1–3 categorized prompt examples, inline GeoJSON/WKT geometries, and multi-turn transmission line corridor workflow.
- **2026-09-23**: `pyproject.toml` updated with `@pytest.mark.agent_eval` marker for release-time evaluation runs.
- **2026-09-23**: Pi agent evaluation harness built with temporary isolated working directories (`temp_sandbox_dir`), ephemeral MCP configuration, and `--mode json -p` invocation.
- **2026-09-23**: CLI evaluation script `eval/run_evals.py` created for standalone test runs between releases.
- **2026-09-23**: 3-wave execution plan designed to maintain strict disjoint file boundaries across parallel workers.

---

## Technical Reconnaissance

- **Target Files & Locations**:
  - Documentation: `QUICKSTART.md`, `README.md`, `manifest.yaml`, `server.json`
  - Fixtures: `eval/prompt_test_cases.json`
  - Test Suite & Config: `pyproject.toml`, `eval/test_agent_eval.py`
  - Scripts: `eval/run_evals.py`
- **Existing Tests Baseline**: `192 passed, 12 deselected`
- **Pi CLI Check**: `pi` version 0.87.1 installed at `C:\Users\Andrew.G.Brown\AppData\Roaming\npm\pi.cmd`.
- **Linter Baseline**: `uv run ruff check .` clean; `uv run ruff format --check .` clean.

---

## Wave Table

| Wave | Task ID | Title | Files in Scope | Dependencies |
| --- | --- | --- | --- | --- |
| 1 | `14.1.1` | Create Structured Prompt Test Fixtures Dataset | `eval/prompt_test_cases.json` | None |
| 1 | `14.1.2` | Update `manifest.yaml` and `server.json` Metadata | `manifest.yaml`, `server.json` | None |
| 2 | `14.2.1` | Update `QUICKSTART.md` and `README.md` Prompt Documentation | `QUICKSTART.md`, `README.md` | `14.1.1` |
| 2 | `14.2.2` | Implement Pi Agent Evaluation Test Suite & Pytest Marker | `pyproject.toml`, `eval/test_agent_eval.py` | `14.1.1` |
| 2 | `14.2.3` | Implement Release Evaluation CLI Runner Script | `eval/run_evals.py` | `14.1.1` |
| 3 | `14.3.1` | Validate Full Test Suite, Formatting, and Documentation Integrity | `planning/STATE_14.md`, `planning/tasks/14.3.1.todo.md` | `14.2.1`, `14.2.2`, `14.2.3` |

---

## Task Specifications

### Task 14.1.1: Create Structured Prompt Test Fixtures Dataset
- **Task ID**: `14.1.1`
- **Files in Scope**: `eval/prompt_test_cases.json`
- **Dependencies**: None
- **Spec Prose**:
  1. Create directory `eval/` if not present.
  2. Author `eval/prompt_test_cases.json` with a structured list of prompt test cases covering:
     - All 9 Tools: `get_farmland_classification_by_point`, `get_farmland_classification_by_mukey`, `explain_fppa_screening_scope`, `list_farmland_classes`, `analyze_farmland_by_polygon`, `get_soil_polygons_by_geometry`, `check_urban_area_exemption`, `get_soil_interpretations`, `analyze_corridor_fppa`.
     - All 3 Resources: `fppa://regulatory-notice`, `fppa://screening-guidance`, `fppa://farmland-classes`.
     - All 4 Prompts: `fppa_screening_assistant`, `fppa_corridor_screening_assistant`, `fppa_urban_exemption_assistant`, `fppa_site_assessment_assistant`.
  3. Each entry must define: `id`, `category` (Phase 1/2/3/Workflow), `target_type` (`tool`/`resource`/`prompt`), `target_name`, `user_prompt`, `expected_tools` (list of tool names), `expected_keywords` (key phrases, e.g. "Prime Farmland", "7 CFR 658", "LESA"), and optional `sample_geometry`.
- **Constraints**: Use valid JSON; ensure realistic coordinates and geometries matching research doc.
- **Grep Anchors**: `eval/prompt_test_cases.json`
- **Acceptance Command**: `python -c "import json; data=json.load(open('eval/prompt_test_cases.json')); assert len(data['test_cases']) >= 16; print(f'Loaded {len(data[\"test_cases\"])} prompt cases')"`

---

### Task 14.1.2: Update `manifest.yaml` and `server.json` Metadata
- **Task ID**: `14.1.2`
- **Files in Scope**: `manifest.yaml`, `server.json`
- **Dependencies**: None
- **Spec Prose**:
  1. Review `manifest.yaml` and `server.json` against all 9 tools, 3 resources, and 4 prompts in `src/fpac_soil_mcp/`.
  2. Ensure parameter names, prompt argument descriptions, and tool definitions are complete and synchronized.
  3. Keep formatting clean and consistent with FastMCP schema standards.
- **Constraints**: Do not alter existing valid keys or remove required schema elements.
- **Grep Anchors**: `manifest.yaml`, `server.json`
- **Acceptance Command**: `uv run pytest tests/test_server.py -m "not live_network and not agent_eval"`

---

### Task 14.2.1: Update `QUICKSTART.md` and `README.md` Prompt Documentation
- **Task ID**: `14.2.1`
- **Files in Scope**: `QUICKSTART.md`, `README.md`
- **Dependencies**: `14.1.1`
- **Spec Prose**:
  1. In `QUICKSTART.md`, replace Section 4 with the comprehensive 6-category prompt catalog from `planning/RESEARCH_PROMPT_EXAMPLE_ENHANCE.md`:
     - Category 1: Discovery, Capabilities & Regulatory Scope
     - Category 2: Point & Map Unit Lookups (Phase 1)
     - Category 3: Polygon AOI & Spatial Screening (Phase 2)
     - Category 4: Statutory Urban Exemption & Soil Interpretations (Phase 3)
     - Category 5: Multi-County Corridor Analysis & Form NRCS-CPA-106 LESA (Phase 3)
     - Category 6: Guided Assistant Prompts & Multi-Turn Workflows
  2. Include inline GeoJSON polygon and WKT linestring examples for immediate copy-paste testing.
  3. In `README.md`, expand the Prompts Registry and add a detailed multi-turn workflow walkthrough (Flow A: Transmission Line Corridor & CPA-106 scoring) and data provenance summary.
- **Constraints**: Ensure all markdown links, code blocks, and regulatory disclaimers conform to project documentation standards.
- **Grep Anchors**:
  - `## 4. Try These Prompts in Your LLM` in `QUICKSTART.md`
  - `## Prompts Registry` in `README.md`
- **Acceptance Command**: `uv run ruff check .`

---

### Task 14.2.2: Implement Pi Agent Evaluation Test Suite & Pytest Marker
- **Task ID**: `14.2.2`
- **Files in Scope**: `pyproject.toml`, `eval/test_agent_eval.py`
- **Dependencies**: `14.1.1`
- **Spec Prose**:
  1. In `pyproject.toml`, register the `agent_eval` marker in `tool.pytest.ini_options.markers`:
     `"agent_eval: marks agentic integration tests invoking pi coding agent CLI (deselect with -m 'not agent_eval')"`
  2. Create `eval/test_agent_eval.py`:
     - Mark all tests in module with `@pytest.mark.agent_eval`.
     - Implement helper to check if `pi` CLI is installed (`shutil.which("pi")`), skipping gracefully if unavailable.
     - Implement fixture/context manager creating a temporary sandbox directory outside repo root.
     - Generate ephemeral `.mcp.json` in the sandbox pointing to `uv run --directory <repo_root> fpac-soil-mcp`.
     - Load prompt test cases from `eval/prompt_test_cases.json`.
     - Execute `pi` with `--mode json -p` (or plain text if preferred), passing the prompt.
     - Parse output to verify MCP server initialized, tool calls were made as expected, and statutory disclaimers/expected findings appear in response.
- **Constraints**: Do not allow `pi` to execute in the repository directory where it could read source code. Keep standard `pytest -m "not live_network and not agent_eval"` fast and offline.
- **Grep Anchors**:
  - `agent_eval` in `pyproject.toml`
  - `def test_pi_prompt_evaluation` in `eval/test_agent_eval.py`
- **Acceptance Command**: `uv run pytest eval/test_agent_eval.py -m "not agent_eval"`

---

### Task 14.2.3: Implement Release Evaluation CLI Runner Script
- **Task ID**: `14.2.3`
- **Files in Scope**: `eval/run_evals.py`
- **Dependencies**: `14.1.1`
- **Spec Prose**:
  1. Create directory `eval/` if not present.
  2. Implement `eval/run_evals.py` with CLI arguments:
     - `--category`: Filter by prompt category (e.g. `point`, `polygon`, `corridor`, `exemption`, `all`).
     - `--model`: Model to use (defaults to env `AGENT_EVAL_MODEL` or provider default).
     - `--case-id`: Run a specific test case ID from `eval/prompt_test_cases.json`.
     - `--timeout`: Per-case execution timeout (default 60s).
     - `--verbose`: Detailed stdout stream.
  3. Script will spin up the isolated sandbox, launch `pi`, iterate over selected test cases, score results against assertions, and print a formatted summary report table with pass/fail counts and durations.
- **Constraints**: Make script executable and well-documented with `--help`.
- **Grep Anchors**: `eval/run_evals.py`
- **Acceptance Command**: `python eval/run_evals.py --help`

---

### Task 14.3.1: Validate Full Test Suite, Formatting, and Documentation Integrity
- **Task ID**: `14.3.1`
- **Files in Scope**: `planning/STATE_14.md`, `planning/tasks/14.3.1.todo.md`
- **Dependencies**: `14.2.1`, `14.2.2`, `14.2.3`
- **Spec Prose**:
  1. Verify all unit tests pass with `uv run pytest -m "not live_network and not agent_eval"`.
  2. Verify linters and formatters: `uv run ruff check .` and `uv run ruff format --check .`.
  3. Validate that `eval/prompt_test_cases.json`, `QUICKSTART.md`, and `README.md` contain 100% consistent examples.
  4. Record task execution summaries in `planning/STATE_14.md` and task todo files.
- **Constraints**: Ensure zero regressions on baseline 192 tests.
- **Grep Anchors**: `planning/STATE_14.md`
- **Acceptance Command**: `uv run pytest -m "not live_network and not agent_eval"`
