# PR #83 Deferred Work Review for Plan 46

## Recommendation

Add a small follow-up wave to Plan 46 for DB45-10 and DB45-E3; do not reopen
the completed Waves 1-5. DB45-E4 should be tracked only if its existing Plan 44
follow-up is confirmed incomplete. N1-N3 are operational/environment notes,
not independent implementation tasks.

## Findings

| PR #83 item | Finding | Plan 46 disposition |
|---|---|---|
| DB45-10 | PR #83 explicitly defers the `evaluate_site_assessment(None, ...)` path, which can return `complete` while 11 criteria are unavailable; it labels the path low priority and unreachable through the MCP tool. The current PR-head implementation still has a `criteria_inputs is None` branch with this behavior ([PR body](https://github.com/AndrewBrown-USDA/fpac-soil-mcp/pull/83); [PR-head `lesa.py`](https://github.com/AndrewBrown-USDA/fpac-soil-mcp/blob/feature/semiquant-sa1/src/fpac_soil_mcp/lesa.py#L723-L773)). | Add a bounded follow-up after the completed 46.3.1 contract gate: ensure completion status reflects unavailable criteria and add direct-call regression coverage. |
| DB45-E3 | The review reports a model-judge false positive for `fppa_compliance` despite an explicit non-official-determination disclaimer, plus null correctness/guidelines scores when expected facts are absent ([review finding](https://github.com/AndrewBrown-USDA/fpac-soil-mcp/blob/feature/semiquant-sa1/planning/REVIEW_45_DATABRICKS.md#L302-L306)). Plan 46 separates deterministic contract evidence from judge observations, but did not add a regression for this specific observation ([46.2.2 spec](https://github.com/AndrewBrown-USDA/fpac-soil-mcp/blob/feature/semiquant-sa1/planning/EXECUTION_PLAN_46.md#L208-L230); [T1 contract](https://github.com/AndrewBrown-USDA/fpac-soil-mcp/blob/feature/semiquant-sa1/tests/eval/test_phase4_databricks_contract.py#L117-L128)). | Add a narrow evaluation follow-up to preserve the known compliant-response case and clarify null-score interpretation. Keep judge results explicitly model-assisted; do not treat them as deterministic safety proof or retune a judge from one observation. |
| DB45-E4 | PR #83 groups E4 with the deferred evaluation/tool-error items ([PR body](https://github.com/AndrewBrown-USDA/fpac-soil-mcp/pull/83)). The review identifies the WKT argument error as an existing Plan 44 follow-up, not a new Plan 45 defect ([review finding](https://github.com/AndrewBrown-USDA/fpac-soil-mcp/blob/feature/semiquant-sa1/planning/REVIEW_45_DATABRICKS.md#L307-L311)). Plan 46 added malformed-geometry cases and public contract checks, but does not establish whether that specific Plan 44 follow-up is closed. | Do not duplicate it in a new wave unless the owning Plan 44 follow-up is confirmed incomplete. |
| DB45-N1–N3 | The review's notes concern Databricks environment/credentials, the Pi `PYTHONPATH` invocation, and expected offline skips ([review notes](https://github.com/AndrewBrown-USDA/fpac-soil-mcp/blob/feature/semiquant-sa1/planning/REVIEW_45_DATABRICKS.md#L313-L323)). Plan 46 records unavailable Pi provider authentication and does not claim model-assisted results ([state](https://github.com/AndrewBrown-USDA/fpac-soil-mcp/blob/planning/agent-safety-eval/planning/STATE_46.md#L128-L153); [closeout](46.5.1-closeout.md)). | No implementation wave needed. Keep invocation and environment constraints in documentation; update only if a concrete instruction is missing. |

## Suggested Follow-up Wave

If these remaining findings are to be closed under Plan 46, add a new,
post-closeout Wave 6 with two independent tasks:

1. **DB45-10 — Correct unavailable Site Assessment completion status.**
   Likely scope: `src\fpac_soil_mcp\lesa.py` and `tests\test_lesa.py` (or the
   existing focused evaluator test module). Use the established status
   vocabulary, preserve valid evaluation behavior, and assert that unavailable
   criteria do not produce a complete status.
2. **DB45-E3 — Preserve and interpret the judge observation.** Likely scope:
   `eval\prompt_test_cases.json`, focused Databricks scorer tests, and
   evaluation guidance if needed. Keep the case synthetic, preserve the
   deterministic-versus-model-assisted distinction, and test the null-score
   interpretation without requiring provider access in the default suite.

Both tasks depend only on already-completed Plan 46 gates (46.3.1 for DB45-10;
the Wave 2 evaluation gate for DB45-E3), so they may be in the same wave if
their final file lists remain disjoint. The PR #83 body confirms these
deferred items and their descriptions: [PR #83](https://github.com/AndrewBrown-USDA/fpac-soil-mcp/pull/83).

## Pi 1.5.2 Diagnostic Addendum

The current Pi CLI reports version `1.5.2`. Model discovery lists
`github-copilot` as the provider for `gpt-5.6-luna` (`pi --list-models
gpt-5.6-luna`). Therefore the original unqualified check was not a valid
provider readiness result: `pi auth check --model gpt-5.6-luna --json
--no-refresh` returned `invalid`, while
`pi auth check --model github-copilot/gpt-5.6-luna --json --no-refresh`
returned `ready` with OAuth. No credential output was requested or retained.

The repository's one-case runner attempt,
`uv run python eval\pi\run_evals.py --case-id POINT-01 --no-show-output`,
failed before any provider request with `Unknown option: --mcp-config`.
Pi 1.5.2 exposes built-in `pi mcp` support and no longer documents that
option in `pi --help`. The immediate blocker is runner CLI compatibility, not
provider authentication. No eval artifacts or model response were retained.
