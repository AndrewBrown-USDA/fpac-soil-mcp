# EXECUTION PLAN 15: Resolve PR #7 Code Review Findings on Agent Evaluation Suite & Docs

## Goal & Scope

### Goal
Address all 12 code review findings raised on Pull Request #7 (`Add evaluation suite`) across the agent evaluation test harness (`eval/test_agent_eval.py`), evaluation CLI runner (`eval/run_evals.py`), test configuration (`pyproject.toml`), user documentation (`QUICKSTART.md`, `README.md`), and historical planning artifacts (`planning/EXECUTION_PLAN_14.md`, `planning/STATE_14.md`, `planning/tasks/14.*`), ensuring robust tool-call verification, proper exit codes on benchmark failures, accurate documentation examples, and reconciled planning metadata.

### In Scope
1. **Tool-Call & Assertion Rigor in Evaluation Runners (`eval/run_evals.py`, `eval/test_agent_eval.py`)**:
   - Update `eval/run_evals.py` to parse Pi event/JSON or tool output and verify that each case's `expected_tools` are actually invoked.
   - Update `eval/run_evals.py` to treat missing expected keywords or missing tools as failures (or error out with non-zero exit code on warnings).
   - Update `eval/test_agent_eval.py` to assert that MCP tools were called and initialized, avoiding false positives from hallucinated model responses.
   - Note sandboxing extensions for future reference (e.g. `https://github.com/brownag/pi-sandbox`).
2. **Pytest Discovery & Marker Configuration (`pyproject.toml`, `eval/test_agent_eval.py`)**:
   - Update `pyproject.toml` so `testpaths` includes `["tests", "eval"]` so that `uv run pytest -m agent_eval` discovers evaluation tests, while maintaining `addopts = "-m 'not live_network and not agent_eval'"` as the default offline filter.
   - Verify that test discovery and marker deselection behave consistently across both offline and evaluation runs.
3. **Documentation & Example Accuracy (`QUICKSTART.md`, `README.md`)**:
   - In `QUICKSTART.md` (Category 5), clarify that `analyze_corridor_fppa` requires Part VI `site_assessment_inputs` (or `criteria_inputs`) for non-automated criteria, explaining the defaults/prompt requirements.
   - In `README.md` (Flow A), correct the corridor acreage calculation for the 23.2-mile line with 100-foot buffer (or clarify hypothetical inputs/width to ensure mathematical consistency with the 181.82 acre / 182.2 LESA score example).
4. **Planning Artifact Consistency & Verification Logs (`planning/`)**:
   - Reconcile `planning/EXECUTION_PLAN_14.md` file paths (`eval/prompt_test_cases.json`, `eval/run_evals.py`) with actual PR implementation.
   - Reconcile deselected test counts across `planning/STATE_14.md` and task todo files (`planning/tasks/14.3.1.todo.md`, `planning/tasks/14.2.2.todo.md`).
5. **Quality & Validation**:
   - Verify 100% pass rate on offline test suite (`uv run pytest -m "not live_network and not agent_eval"`).
   - Verify code formatting and linting (`uv run ruff check .`, `uv run ruff format --check .`).

### Out of Scope
- Enabling full OS/container sandboxing runtime dependencies for Pi right now (noted as future enhancement).
- Modifying core FastMCP tool schemas or server business logic in `src/fpac_soil_mcp/`.
- Modifying live SDA / TIGERweb / NASS API clients.

### Verbatim Review Feedback Addressed
- *"Parse the pi event/JSON output and assert that every expected tool call is present."* (`eval/run_evals.py:166`)
- *"Treat this condition as a failure or make warnings produce a nonzero exit status."* (`eval/run_evals.py:210`)
- *"Parse the pi event output and assert the expected MCP calls before checking response keywords."* (`eval/test_agent_eval.py:184`)
- *"Include eval in the configured test paths or document an explicit file path as the only supported invocation."* (`pyproject.toml:36`)
- *"This copy-paste prompt asks for a threshold determination but provides only farm tract size... request those inputs instead of implying a complete LESA evaluation."* (`QUICKSTART.md:115`)
- *"Recalculate this output from the shown WKT or label the numbers as hypothetical; otherwise users may rely on a materially false example."* (`README.md:291`)
- *"Include the scoring payload or mark this output as hypothetical."* (`README.md:293`)
- *"This PR implements them at eval/prompt_test_cases.json and eval/run_evals.py. Reconcile execution plan."* (`planning/EXECUTION_PLAN_14.md:34`)
- *"Reconcile conflicting deselected test counts."* (`planning/STATE_14.md:6`)
- *"Correct deselected schema test verification."* (`planning/tasks/14.2.2.todo.md:13`)

---

## Decision Log

- **2026-09-25**: Sandboxing approach left as lightweight cwd isolation for now; future container/pi-sandbox integration noted (e.g. `https://github.com/brownag/pi-sandbox`).
- **2026-09-25**: Evaluation runner updated to parse pi `--mode json` tool executions and enforce non-zero exit code on missing keywords or missing tools.
- **2026-09-25**: `pyproject.toml` updated with `testpaths = ["tests", "eval"]` to allow seamless `uv run pytest -m agent_eval` execution.
- **2026-09-25**: Documentation examples updated to provide mathematically consistent corridor acreage and explicit LESA criteria inputs.
- **2026-09-25**: Planning artifacts from Wave 14 updated to accurately reflect final repository paths and test deselection counts.

---

## Wave Table

| Wave | Task ID | Title | Files in Scope | Dependencies |
| --- | --- | --- | --- | --- |
| 1 | `15.1.1` | Update Pytest Config & Test Discovery | `pyproject.toml` | None |
| 1 | `15.1.2` | Fix Documentation Prompt Examples & Corridor Calculations | `QUICKSTART.md`, `README.md` | None |
| 1 | `15.1.3` | Reconcile Plan 14 Documentation & Todo Records | `planning/EXECUTION_PLAN_14.md`, `planning/STATE_14.md`, `planning/tasks/14.2.2.todo.md`, `planning/tasks/14.3.1.todo.md` | None |
| 2 | `15.2.1` | Implement Tool Call Verification & Exit Codes in Evaluation Runner | `eval/run_evals.py` | `15.1.1` |
| 2 | `15.2.2` | Implement Tool Call Verification in Pytest Agent Eval Harness | `eval/test_agent_eval.py` | `15.1.1` |
| 3 | `15.3.1` | Validate Full Test Suite, Formatting, and Consistency Checks | `planning/STATE_15.md`, `planning/tasks/15.3.1.todo.md` | `15.1.2`, `15.1.3`, `15.2.1`, `15.2.2` |

---

## Task Specifications

### Task 15.1.1: Update Pytest Config & Test Discovery
- **Task ID**: `15.1.1`
- **Files in Scope**: `pyproject.toml`
- **Dependencies**: None
- **Spec Prose**:
  1. In `pyproject.toml`, update `tool.pytest.ini_options.testpaths` to `["tests", "eval"]`.
  2. Maintain `addopts = "-m 'not live_network and not agent_eval'"` so default pytest invocations still exclude agent eval tests automatically.
  3. Verify that running `uv run pytest` runs the 192 offline unit tests and deselected tests include agent_eval tests.
- **Constraints**: Do not break offline default test suite or addopts filtering.
- **Grep Anchors**: `testpaths = ["tests"]` in `pyproject.toml`
- **Acceptance Command**: `uv run pytest -q`

---

### Task 15.1.2: Fix Documentation Prompt Examples & Corridor Calculations
- **Task ID**: `15.1.2`
- **Files in Scope**: `QUICKSTART.md`, `README.md`
- **Dependencies**: None
- **Spec Prose**:
  1. In `QUICKSTART.md` (Category 5 transmission line example):
     - Update the prompt to clearly state that Site Assessment inputs (such as non-agricultural land use percentages, zoning, and parcel sizes) must be provided in `criteria_inputs` for full Form NRCS-CPA-106 scoring, or clearly explain that omitted criteria default to zero.
  2. In `README.md` (Flow A: Transmission Line Corridor & Form NRCS-CPA-106):
     - Check the centerline geometry and buffer width. Ensure that the documented acreage either matches the true geometric calculation (approx 281 ac direct + 12 ac yard = 293 ac total for a 23.2-mile line with 100-ft buffer) or explicitly adjusts the centerline / buffer parameters / labeling to be mathematically consistent.
     - Include the sample `site_assessment_inputs` payload in the invocation text or clarify that the LESA score example reflects the complete inputs provided.
- **Constraints**: Maintain accurate statutory citations (7 CFR § 658.5(c)) and disclaimer requirements.
- **Grep Anchors**:
  - `## Category 5: Multi-County Corridor Analysis` in `QUICKSTART.md`
  - `Flow A: Multi-County Transmission Line Corridor` in `README.md`
- **Acceptance Command**: `uv run ruff check .`

---

### Task 15.1.3: Reconcile Plan 14 Documentation & Todo Records
- **Task ID**: `15.1.3`
- **Files in Scope**: `planning/EXECUTION_PLAN_14.md`, `planning/STATE_14.md`, `planning/tasks/14.2.2.todo.md`, `planning/tasks/14.3.1.todo.md`
- **Dependencies**: None
- **Spec Prose**:
  1. In `planning/EXECUTION_PLAN_14.md`, update references from `tests/fixtures/prompts/prompt_test_cases.json` and `scripts/run_agent_evals.py` to `eval/prompt_test_cases.json` and `eval/run_evals.py`.
  2. In `planning/STATE_14.md`, `planning/tasks/14.2.2.todo.md`, and `planning/tasks/14.3.1.todo.md`, reconcile the deselected test count and verify command syntax (noting that `eval/test_agent_eval.py` has `@pytest.mark.agent_eval` on both test functions).
- **Constraints**: Maintain historical traceability while resolving contradictions.
- **Grep Anchors**: `EXECUTION_PLAN_14.md`, `STATE_14.md`
- **Acceptance Command**: `python -c "assert True"`

---

### Task 15.2.1: Implement Tool Call Verification & Exit Codes in Evaluation Runner
- **Task ID**: `15.2.1`
- **Files in Scope**: `eval/run_evals.py`
- **Dependencies**: `15.1.1`
- **Spec Prose**:
  1. In `eval/run_evals.py`:
     - Update pi execution to use `--mode json` (or inspect pi output events) to extract executed tool calls (`call` events / tool names).
     - Compare executed tools against `expected_tools` defined in each test case.
     - If expected tools are missing or not executed, mark the case status as `FAIL` (or fail on warning).
     - Treat missing expected keywords as `FAIL` (or ensure `WARN` produces non-zero exit code).
     - Ensure failure summary accurately counts failed tool assertions and exits with code 1 on any test failure.
     - Add code comments noting future extension points for container-based sandboxing (`https://github.com/brownag/pi-sandbox`).
- **Constraints**: Ensure cross-platform compatibility on Windows/Linux.
- **Grep Anchors**: `def run_case` in `eval/run_evals.py`
- **Acceptance Command**: `python eval/run_evals.py --help`

---

### Task 15.2.2: Implement Tool Call Verification in Pytest Agent Eval Harness
- **Task ID**: `15.2.2`
- **Files in Scope**: `eval/test_agent_eval.py`
- **Dependencies**: `15.1.1`
- **Spec Prose**:
  1. In `eval/test_agent_eval.py`:
     - Update `test_pi_point_screening_evaluation` to invoke pi with `--mode json`.
     - Parse the JSON stream of events to verify MCP server initialization and assert that `get_farmland_classification_by_point` was invoked with expected parameters.
     - Verify both tool invocation and response content assertions.
- **Constraints**: Must be decorated with `@pytest.mark.agent_eval` and skip gracefully if `pi` is not on PATH.
- **Grep Anchors**: `def test_pi_point_screening_evaluation` in `eval/test_agent_eval.py`
- **Acceptance Command**: `uv run pytest eval/test_agent_eval.py -m "not agent_eval"`

---

### Task 15.3.1: Validate Full Test Suite, Formatting, and Consistency Checks
- **Task ID**: `15.3.1`
- **Files in Scope**: `planning/STATE_15.md`, `planning/tasks/15.3.1.todo.md`
- **Dependencies**: `15.1.2`, `15.1.3`, `15.2.1`, `15.2.2`
- **Spec Prose**:
  1. Run the offline test suite: `uv run pytest -m "not live_network and not agent_eval"`.
  2. Run linter and formatter: `uv run ruff check .` and `uv run ruff format --check .`.
  3. Create `planning/STATE_15.md` and task todo records to document completion of all 12 review comments.
- **Constraints**: 100% clean test and lint passes.
- **Grep Anchors**: `planning/STATE_15.md`
- **Acceptance Command**: `uv run pytest -m "not live_network and not agent_eval"`
