# EXECUTION PLAN 16: Resolve Follow-Up PR #7 Code Review Findings on Evaluation & Documentation

## Goal & Scope

### Goal
Address all 7 follow-up code review findings on Pull Request #7 (`Add evaluation suite`) across benchmark test fixtures (`eval/prompt_test_cases.json`), evaluation runner tool detection (`eval/run_evals.py`), test harness response parsing (`eval/test_agent_eval.py`), documentation examples (`README.md`), and historical planning artifacts (`planning/EXECUTION_PLAN_14.md`, `planning/STATE_15.md`).

### In Scope
1. **Fixture Input/Tool Alignment (`eval/prompt_test_cases.json`)**:
   - For `PROMPT-01` (`fppa_screening_assistant`), adjust `expected_tools` to `["get_farmland_classification_by_point"]` since the user prompt provides point coordinates (`-93.88, 42.05`), or provide explicit geometry matching expected tool invocation.
   - Review and align `PROMPT-02`, `PROMPT-03`, and `PROMPT-04` so their prompts and `expected_tools` are 100% consistent with the screening assistant prompt behaviors.
2. **Robust Event & Tool Call Parsing (`eval/run_evals.py`, `eval/test_agent_eval.py`)**:
   - In `eval/run_evals.py`, restrict tool invocation extraction to actual event fields representing tool execution (`tool_call`, `call`, `tool_use`, function names in `content`/`tool` structures), rather than doing regex matching against full JSON serialization strings.
   - In `eval/test_agent_eval.py`, extract actual assistant response text / tool results from the parsed JSON event structures before checking keyword assertions, avoiding false matches on prompt text or parameter strings.
3. **Workflow Documentation & Example Consistency (`README.md`)**:
   - In `README.md` (Flow A: Linear Transmission Corridor), remove rigid pre-stated laydown acreage claims and present the calculated impact output directly from the spatial corridor calculation, and ensure Part VI Site Assessment criteria or scoring outputs are clearly presented as a complete illustrative evaluation without claiming unreconciled partial sums.
4. **Planning Artifact Consistency (`planning/`)**:
   - In `planning/EXECUTION_PLAN_14.md:56`, update the stale technical reconnaissance path `tests/test_agent_eval.py` to `eval/test_agent_eval.py`.
   - In `planning/STATE_15.md:5`, reconcile the baseline record to `192 passed, 12 deselected`.
5. **Quality & Validation**:
   - Verify 100% pass rate on offline test suite (`uv run pytest -m "not live_network and not agent_eval" -q`).
   - Verify code formatting and linting (`uv run ruff check .`, `uv run ruff format --check .`).

### Out of Scope
- Modifying underlying FastMCP server code or tools in `src/fpac_soil_mcp/`.
- Enabling full OS-level sandboxing (noted for future work via `https://github.com/brownag/pi-sandbox`).

### Verbatim Review Feedback Addressed
- *"This case requires analyze_farmland_by_polygon, but its prompt supplies only a point... a correct agent can call only get_farmland_classification_by_point and would be incorrectly marked as failed."* (`eval/prompt_test_cases.json:250`)
- *"This scan treats a tool name in any JSON event as an executed call... restrict the match to the pi event type/fields that represent an actual MCP tool execution."* (`eval/run_evals.py:219`)
- *"This searches the complete JSON event stream for response keywords... assert keywords against parsed assistant/tool-result content only."* (`eval/test_agent_eval.py:241`)
- *"The WKT rectangle supplied here is not a 12-acre yard... use a geometry whose area is 12 acres or remove the 12-acre/output claims."* (`README.md:279`)
- *"The shown scoring payload only supplies criteria 1–3... include the remaining criteria inputs or label these values as unrelated hypothetical output."* (`README.md:294`)
- *"The technical reconnaissance still points to tests/test_agent_eval.py... update to eval/test_agent_eval.py."* (`planning/EXECUTION_PLAN_14.md:56`)
- *"The baseline count on this line contradicts the later validation entries... record 12 deselected."* (`planning/STATE_15.md:5`)

---

## Decision Log

- **2026-09-25**: For `PROMPT-01`, aligned `expected_tools` with point screening (`get_farmland_classification_by_point`) which accurately reflects prompt input.
- **2026-09-25**: In `eval/run_evals.py` and `eval/test_agent_eval.py`, implemented structured tool extraction and message content extraction across all Pi event formats.
- **2026-09-25**: In `README.md`, removed rigid pre-stated 12-acre claim on the staging yard polygon and presented the workflow output cleanly with complete illustrative criteria inputs.
- **2026-09-25**: Reconciled historical plan references in `EXECUTION_PLAN_14.md` and baseline counts in `STATE_15.md`.

---

## Wave Table

| Wave | Task ID | Title | Files in Scope | Dependencies |
| --- | --- | --- | --- | --- |
| 1 | `16.1.1` | Align Prompt Test Case Fixtures & Expected Tools | `eval/prompt_test_cases.json` | None |
| 1 | `16.1.2` | Clean Up README Corridor Example Geometry & Scoring Payload | `README.md` | None |
| 1 | `16.1.3` | Reconcile Historical Plan References & Baseline Counts | `planning/EXECUTION_PLAN_14.md`, `planning/STATE_15.md` | None |
| 2 | `16.2.1` | Implement Structured Tool Event Inspection in Evaluation Runner | `eval/run_evals.py` | `16.1.1` |
| 2 | `16.2.2` | Implement Assistant Response Content Parsing in Pytest Harness | `eval/test_agent_eval.py` | `16.1.1` |
| 3 | `16.3.1` | Final Validation, Formatting, and State Documentation | `planning/STATE_16.md`, `planning/tasks/16.3.1.todo.md` | `16.1.2`, `16.1.3`, `16.2.1`, `16.2.2` |

---

## Task Specifications

### Task 16.1.1: Align Prompt Test Case Fixtures & Expected Tools
- **Task ID**: `16.1.1`
- **Files in Scope**: `eval/prompt_test_cases.json`
- **Dependencies**: None
- **Spec Prose**:
  1. In `eval/prompt_test_cases.json`, review cases `PROMPT-01`, `PROMPT-02`, `PROMPT-03`, `PROMPT-04`.
  2. In `PROMPT-01`, change `expected_tools` from `["get_farmland_classification_by_point", "analyze_farmland_by_polygon"]` to `["get_farmland_classification_by_point"]` because the user prompt only supplies point coordinates (`-93.88, 42.05`).
  3. Verify that `PROMPT-02`, `PROMPT-03`, and `PROMPT-04` have appropriate and realistic `expected_tools` matching the actions implied by their user prompt inputs.
- **Constraints**: Valid JSON; do not break schema completeness.
- **Grep Anchors**: `PROMPT-01` in `eval/prompt_test_cases.json`
- **Acceptance Command**: `python -c "import json; data=json.load(open('eval/prompt_test_cases.json')); assert len(data['test_cases']) >= 16; print('Valid fixtures')"`

---

### Task 16.1.2: Clean Up README Corridor Example Geometry & Scoring Payload
- **Task ID**: `16.1.2`
- **Files in Scope**: `README.md`
- **Dependencies**: None
- **Spec Prose**:
  1. In `README.md` (Flow A: Linear Transmission Corridor & CPA-106 LESA):
     - Remove specific pre-asserted acreage claims (e.g. "12-acre laydown yard") and describe the staging yard simply as a laydown yard polygon.
     - Show the complete illustrative criteria payload in the invocation (or clarify that Criteria 1, 2, 3, 4, 8, 9, 10, 11, 12 are evaluated to reach the illustrative score).
     - Present the output clearly as an illustrative corridor screening result.
- **Constraints**: Keep statutory citations (7 CFR § 658.5(c), 7 CFR § 658.4(c)(2)) intact.
- **Grep Anchors**: `Flow A: Multi-County Transmission Line Corridor` in `README.md`
- **Acceptance Command**: `uv run ruff check .`

---

### Task 16.1.3: Reconcile Historical Plan References & Baseline Counts
- **Task ID**: `16.1.3`
- **Files in Scope**: `planning/EXECUTION_PLAN_14.md`, `planning/STATE_15.md`
- **Dependencies**: None
- **Spec Prose**:
  1. In `planning/EXECUTION_PLAN_14.md:56`, change `tests/test_agent_eval.py` to `eval/test_agent_eval.py`.
  2. In `planning/STATE_15.md:5`, change `192 passed, 10 deselected` to `192 passed, 12 deselected`.
- **Constraints**: Maintain accurate historical records.
- **Grep Anchors**: `tests/test_agent_eval.py` in `planning/EXECUTION_PLAN_14.md`, `10 deselected` in `planning/STATE_15.md`
- **Acceptance Command**: `python -c "assert True"`

---

### Task 16.2.1: Implement Structured Tool Event Inspection in Evaluation Runner
- **Task ID**: `16.2.1`
- **Files in Scope**: `eval/run_evals.py`
- **Dependencies**: `16.1.1`
- **Spec Prose**:
  1. In `eval/run_evals.py`, inspect the structure of each JSON event emitted by Pi:
     - Check event types such as `tool_call`, `tool_use`, `call`, `tool_execution`, or `tool` objects.
     - Extract tool names specifically from dedicated name/function fields (e.g., `event.get("name")`, `event.get("tool")`, `event.get("tool_name")`, `event.get("tool_call", {}).get("name")`, `event.get("function", {}).get("name")`), or from `tool_call` blocks in message items.
     - Avoid matching tool names found only in general text/commentary or prompt echo.
  2. Verify observed tools against `expected_tools` and fail if any are missing.
  3. Extract model response content from assistant message events before verifying `expected_keywords`.
- **Constraints**: Handle all JSON event variants gracefully without throwing unhandled exceptions.
- **Grep Anchors**: `def run_case` in `eval/run_evals.py`
- **Acceptance Command**: `python eval/run_evals.py --help`

---

### Task 16.2.2: Implement Assistant Response Content Parsing in Pytest Harness
- **Task ID**: `16.2.2`
- **Files in Scope**: `eval/test_agent_eval.py`
- **Dependencies**: `16.1.1`
- **Spec Prose**:
  1. In `eval/test_agent_eval.py`:
     - Update helper functions to extract assistant text messages from events (e.g., `event.get("type") in ("message", "text", "assistant")` or `event.get("content")`).
     - Assert expected keywords against the extracted assistant response text and tool results, rather than searching the raw JSON event dump.
     - Ensure tool call verification inspects tool name fields on call events.
- **Constraints**: Decorated with `@pytest.mark.agent_eval`.
- **Grep Anchors**: `def test_pi_point_screening_evaluation` in `eval/test_agent_eval.py`
- **Acceptance Command**: `uv run pytest eval/test_agent_eval.py -m "not agent_eval"`

---

### Task 16.3.1: Final Validation, Formatting, and State Documentation
- **Task ID**: `16.3.1`
- **Files in Scope**: `planning/STATE_16.md`, `planning/tasks/16.3.1.todo.md`
- **Dependencies**: `16.1.2`, `16.1.3`, `16.2.1`, `16.2.2`
- **Spec Prose**:
  1. Run offline test suite: `uv run pytest -m "not live_network and not agent_eval" -q`.
  2. Run linter: `uv run ruff check .` and `uv run ruff format --check .`.
  3. Create `planning/STATE_16.md` and `planning/tasks/16.3.1.todo.md` recording task completions and verification metrics.
- **Constraints**: 100% clean test and lint passes.
- **Grep Anchors**: `planning/STATE_16.md`
- **Acceptance Command**: `uv run pytest -m "not live_network and not agent_eval" -q`
