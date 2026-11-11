# Review 46: Agent Safety, Evaluation, and Reliability Contract (PR #87)

## Scope and method

- **Reviewed:** `feature/agent-safety-eval1` at `524c53b` against `main`
  (merge-base `619b5da`); 25 commits, 80 files, +6,635/-144.
- **Method:** two-axis review (Standards, Spec), reported separately and not
  reranked across axes. Both axes were run serially by one reviewer, by
  reading the code; no tests or evaluations were run for this review.
- **Standards sources:** root `AGENTS.md`,
  `apps/agent-fpac-soil-openai-sdk/AGENTS.md`,
  `eval/fpac_soil_mcp_harness/AGENTS.md`, plus a baseline of Fowler code
  smells (always judgement calls; documented repo standards override them).
- **Spec sources:** `planning/EXECUTION_PLAN_46.md` (tasks 46.1.1-46.8.4,
  Decision Log, Hazard Notes) and `planning/STATE_46.md`.
- **Not verified here:** the README stale-status/test-count note and the
  PR description's "938 tests" figure.

## Standards

### Documented-standard findings

| ID | Severity | Finding | Standard |
|---|---|---|---|
| R46-S1 | Hard | Public tool input schemas changed (bounds, `Literal` enums, `SiteAssessmentInputs`, `CorridorAlternativeInput`, `ToolError`) but `manifest.yaml` and `server.json` are unchanged in the diff. Whether those files carry input schemas was not checked. | Root `AGENTS.md`, "Add or Change an MCP Tool" step 6 |
| R46-S2 | Judgement | `apps/.../agent_server/geo.py` L29 defines its own `NON_PRIME_LIMITATION`, worded differently from the server notice in `src/fpac_soil_mcp/constants.py` L220 ("does not authorize or recommend a site"). The app is a separate project (ADR 0012) and cannot import it, but the wording has diverged. | Root `AGENTS.md`, Operational Rules: keep regulatory language centralized, no divergent notices |

These pass: the live `system_prompt.txt` names no tools, and ADR 0015
lists the `farmlandClasses.ts` local change.

### Smell baseline (judgement calls)

| ID | Smell | Location | Note |
|---|---|---|---|
| R46-S3 | Duplicated Code | `src/fpac_soil_mcp/tools/soil_lookup_tools.py` | `ToolError(...)` construction repeated five times; the `get_soil_interpretations` copy inverts the conditional. Extract one helper. |
| R46-S4 | Primitive Obsession / inconsistent envelope | `soil_lookup_tools.py` | `get_soil_interpretations` now returns `list[dict] \| dict[str, Any]`; `get_soil_polygons_by_geometry` returns both a string `error` and a structured `error_details`. |
| R46-S5 | Speculative / dead code | `src/fpac_soil_mcp/tools/lesa_tools.py`; `spatial_analysis_tools.py` | After `SiteAssessmentInputs` validation, `lesa_tools` still checks `isinstance(raw_criteria_inputs, dict)`, and `norm_project_type = project_type` is a bare alias. The corridor tool still converts string criterion keys and tests `if site_assessment_inputs:` on a model instance. |
| R46-S6 | Repeated Switches | `eval/common/matching.py` `_PROHIBITED_BEHAVIOR_PATTERNS`; `eval/fpac_soil_mcp_harness/lib/evalAssertions.js` `patterns` | The same behavior-ID map exists in two languages and has drifted: JS lacks `sensitive_data_echo`. The Hazard Notes accept duplicated *prompts*, not duplicated scorer tables; derive both from one data file (for example `eval/common/policy_rules.v1.json`). |

## Spec

### Missing or partial requirements

| ID | Severity | Task | Finding |
|---|---|---|---|
| R46-P1 | High | 46.2.1 / 46.2.2 | All 14 `ADV-*` cases (in both `eval/eval_cases.v1.json` and `eval/prompt_test_cases.json`) have zero `assertions.predicates`, so the harness runs no status, behavior, or budget checks for them. Six prohibited-behavior IDs have no Python pattern (`fabricated_rating_or_provenance`, `fabricated_subjective_score`, `malformed_geometry_accepted`, `off_topic_answer`, `retry_budget_exceeded`, `silent_partial_failure`); JS also lacks `sensitive_data_echo`. Unknown IDs fail closed (spec: "Unknown harness predicates must continue to fail closed"), so the affected cases cannot pass. Spec: "Add `expected_status`, required/prohibited behaviors ... and latency budget fields" and "Add ... required behavior/status checks". |
| R46-P2 | High | 46.3.2 | Spec: "Ensure unknown/unrecognized/absent classifications never fall through to `not_prime`". `src/fpac_soil_mcp/polygon_analysis.py` `categorize_farmland_class` still ends `return "not_prime"` (L96), the map renders the server-supplied `farmland_class`, and `withFarmlandClass` in `farmlandClasses.ts` has no callers. The task also forbade touching "MCP server tool implementations", so it could not be met within its file scope; it needed re-planning. |
| R46-P3 | Medium | 46.8.3 | Spec: "disable forced tool use and prompt rendering for zero-call cases; expose case tool-use/budget controls to Databricks". In `eval/databricks/agent.py` the zero-call budget is only a system-prompt instruction (L245); `tools=tool_specs` is still passed (L259), and no budget check was found at tool dispatch (L180). `predict(..., force_tool_use=True)` (L306) overrides the `build_agent` default. |
| R46-P4 | Medium | 46.2.2 / 46.8.3 | Spec: "max tool/retry calls". `eval/pi/run_evals.py` L726 adds names from both `tool_execution_start` and `tool_execution_end` events (`extract_structured_tool_names`, L272-284), so one call can count twice against `max_tool_calls` (checked L613). |
| R46-P5 | Medium | 46.2.2 | Spec: "required ... status checks". `required_status_matches` reads status through `_status(outputs)` (`eval/databricks/scorers.py` L78-88), which only inspects dicts; the Databricks agent's final output is text. Not run to confirm. |
| R46-P6 | Low | 46.6.1 | The wave table lists `src/fpac_soil_mcp/lesa.py` as *must edit*; it is unchanged, and only `tests/test_lesa.py` changed. The spec-named `test_complete_factual_criterion_seven_remains_scored` was renamed and now expects `incomplete`; confirm "Preserve the existing Criterion 7 machine estimate" is still covered. |
| R46-P7 | Low | D5 / 46.8.x | `STATE_46.md` records the Wave 8 gate as "fail; 14 of 38 cases failed". The targeted reruns (9 of 14 passed) are not a full-suite result, and five failure causes remain undiagnosed. |
| R46-P8 | Low | 46.3.1 | Spec: "strict Pydantic models/enums/bounds". `CriterionPointInput.awarded_points` is bounded `le=160` (the Site Assessment total), not per-criterion maxima; out-of-range per-criterion points are left to downstream handling. |

### Behavior not in the spec (scope creep)

- **R46-P9:** commit `524c53b` ("address post-merge findings from PRs #79
  and #83") changes `docs/decisions/0015`, `eval/common/matching.py`,
  `eval/contract/test_contract.py`, `system_prompt_v3.txt`, and the 46.3.1
  evidence; no Plan 46 task covers it. Either add a task to the plan or move
  it to its own PR.

### Optional artifacts not created

`apps/.../tests/fixtures/geo_semantics.json` (46.3.2) and
`planning/evidence/46.4.1-fixture-manifest.md` (46.4.1) were listed as *can
create* and were not created; this is not a finding. The Criterion 2 fixture
manifest contains all four required IDs with every required field.

## Summary

- **Standards:** 2 documented-standard findings and 4 smells. Worst:
  R46-S1, `manifest.yaml`/`server.json` not updated for the changed public
  tool surface.
- **Spec:** 8 missing/partial findings and 1 scope-creep item. Worst:
  R46-P1, the adversarial corpus has no active predicates and uses unmapped
  behavior IDs, so those cases cannot pass.
- **Recommendation:** do not merge until R46-P1 and R46-P2 are resolved and
  R46-P3/P4 are fixed or explicitly deferred in `STATE_46.md`.

## Triage

| ID | Decision | Owner | Notes |
|---|---|---|---|
| R46-S1 | | | |
| R46-S2 | | | |
| R46-S3 | | | |
| R46-S4 | | | |
| R46-S5 | | | |
| R46-S6 | | | |
| R46-P1 | | | |
| R46-P2 | | | |
| R46-P3 | | | |
| R46-P4 | | | |
| R46-P5 | | | |
| R46-P6 | | | |
| R46-P7 | | | |
| R46-P8 | | | |
| R46-P9 | | | |
