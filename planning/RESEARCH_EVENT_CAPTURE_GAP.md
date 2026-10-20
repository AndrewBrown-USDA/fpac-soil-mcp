# Research Report: Remaining Eval Failures and Pi Event Shapes

## Executive Summary

The referenced artifact is not a raw Pi event capture. `eval_20261005_3.txt` is a human-readable aggregate transcript containing case statuses, diagnostics, generated answers, and a final summary; it contains no serialized event objects, per-case raw streams, tool-call payloads, or MCP tool-list responses.[^1] The four failures (POINT-02, POLY-01, PROMPT-01, and LESA-02) therefore cannot be attributed to one exact unrecognized event shape from this artifact alone. The evidence does establish that the evaluator counted structured events but extracted no acceptable matching tool name, while several outputs were substantively tool-like. The safest conclusion is that the failures are either observability/parser misses in the unavailable raw stream, genuinely absent tool calls, or both; broadening the parser speculatively would risk converting prose or arbitrary nested data into false tool execution.

## Scope and Artifact Structure

The requested path is represented by the file:

`D:\workspace\fpac-soil-mcp-evals\.evals\eval_20261005_3.txt`

The `.evals` location contains three aggregate transcript files, a `.gitignore`, and no subdirectories, JSONL streams, per-case files, or raw event artifacts.[^1] The target transcript is 807 lines and follows this repeated structure:

1. Case header with status and duration.
2. Optional diagnostic line.
3. `[OUTPUT: CASE-ID]` block.
4. Separator before the next case.

The failed-case ranges are:

| Case | Lines | Diagnostic |
|---|---:|---|
| POINT-02 | 87-102 | Expected `get_farmland_classification_by_point`; `structured_events=298` |
| POLY-01 | 117-206 | Expected `analyze_farmland_by_polygon`; `structured_events=1837` |
| PROMPT-01 | 464-524 | Expected `get_farmland_classification_by_point`; `structured_events=1158` |
| LESA-02 | 690-779 | Expected `calculate_preliminary_lesa`; `structured_events=1814` |

The aggregate summary reports 16 passed and 4 failed.[^1]

## What the Evidence Proves

### POINT-02

POINT-02 failed with:

```text
Missing tools: get_farmland_classification_by_point;
configuration diagnostic: MCP tool list unavailable;
tool-list source=unknown;
advertised=unknown;
expected=['get_farmland_classification_by_point'];
structured_events=298
```

The generated answer contains the expected point-specific soil result, including coordinates, Genesee loam, MUKEY 159756, the conditional prime-farmland classification, and survey area IN121.[^2] That proves the model produced a detailed answer, but not that the expected MCP tool was invoked in a structured event.

### POLY-01

POLY-01 failed with the same unavailable-tool-list diagnostic and `structured_events=1837`.[^3] Its output contains a detailed polygon screening result, including the Story County geometry, acreage, SSURGO map units, farmland classifications, and NCCPI analysis.[^3] This is consistent with a successful tool-backed response, but the transcript omits the event that would prove it.

### PROMPT-01 and PROMPT-03

PROMPT-01 failed because no acceptable structured call to `get_farmland_classification_by_point` was detected; the diagnostic again says the tool list was unavailable and `structured_events=1158`.[^4] Its answer contains detailed soil, acreage, NCCPI, and urban-screening content, but prose is intentionally not sufficient evidence of tool execution.

PROMPT-03 passed and contains no missing-tool diagnostic.[^5] This contrast shows that the evaluator can recognize at least some event streams for related prompt cases; it does not identify the difference between the passing and failing raw streams.

### LESA-02

LESA-02 failed to expose `calculate_preliminary_lesa` as a recognized structured call, with `structured_events=1814` and unavailable tool advertisement.[^6] The answer contains a specific 45.02-acre footprint, protected acreage, NCCPI-rated acreage, candidate LE score, site-assessment criteria, threshold result, and alternatives conclusion.[^6] LESA-01 passed with the same expected tool name, so the failure is stream-dependent rather than a universal inability to recognize that tool.[^6]

## Current Extractor Compatibility

The current evaluator deliberately separates structured execution detection from assistant prose. It parses each stdout line as a JSON dictionary and unions names returned by structured extraction; the expected tool is then matched exactly or by supported server-prefix suffixes.[^3][^6] The existing recognized execution shapes include:

| Shape | Supported path |
|---|---|
| Direct tool event | `event.tool_name`, `event.tool`, `event.name`, `event.function_name`, `event.toolName` for tool-like event types |
| Pi assistant event | `event.assistantMessageEvent.toolCall.name` or related name fields |
| Tool execution start | `event.tool_name` / `event.name`, with `args` |
| Message tool calls | `event.message.tool_calls` or `toolCalls`, including `function.name` |
| Content blocks | `message.content[]` or top-level `content[]` with `toolCall`, `tool_call`, or `tool_use` |
| Direct argument wrapper | `args.tool` or `args.name`, with `arguments` or nested `args` |

The deterministic tests document observed or intended Pi forms for `assistantMessageEvent.toolCall`, `tool_execution_start`, and `message_end.message.content[]` tool-call blocks.[^3] Namespaced forms such as `fpac-soil_analyze_farmland_by_polygon` are intended to match bare expected names through `_` or `:` suffix matching.[^3]

## Compatibility Matrix

| Area | Finding from the artifact | Confidence |
|---|---|---|
| Exact alternate event type | Not recoverable; no raw event `type` values are present | High |
| Exact alternate name path | Not recoverable; no raw tool-call objects are present | High |
| Exact argument encoding | Not recoverable; no raw argument payloads are present | High |
| Advertised tool extraction | Fails observably in four cases (`advertised=unknown`) | High |
| Namespaced tool matching | Expected names are bare; parser supports common `_`/`:` suffix forms | Medium-high |
| Parser shallow traversal as a risk | Plausible because traversal is allow-listed and non-recursive, but unproven for these runs | Medium |
| Genuine absent invocation | Possible, especially for PROMPT-01; not distinguishable from an unrecognized event shape | Medium |
| Prose substitution | Must not be used; would weaken correctness and create false positives | High |

## Most Likely Explanations

The artifact supports three hypotheses:

1. **Unrecognized execution envelope.** A tool call may be nested deeper than the supported paths, use a provider-specific event type, or store its name under a different field. The current parser is intentionally shallow and allow-listed, so such a shape would be missed. This is plausible but cannot be proven without raw events.[^3]
2. **Missing or differently wrapped tool-list advertisement.** All four failed diagnostics report `advertised=unknown`. The advertised-tool parser only recognizes a limited set of initialization/list event names and locations, so the tool list may be absent or nested elsewhere. The transcript cannot distinguish those cases.[^7]
3. **No actual structured invocation.** A detailed answer does not prove tool execution. PROMPT-01 in particular has no evidence of a retry or structured call in the artifact, so a genuinely absent call remains possible.[^4]

The model output quality alone cannot select among these hypotheses.

## Recommended Next Investigation

The next step should be evidence capture, not speculative parser expansion:

1. Preserve the raw stdout/event JSON for one failing case and one passing case in a non-aggregate artifact.
2. Capture the initialization/tool-list events and the first expected tool invocation separately.
3. Compare POINT-02 against POINT-01, POLY-01 against POLY-02, and LESA-02 against LESA-01.
4. Record the exact event type, full nesting path, tool-name field, namespace separator, and argument encoding.
5. Add one minimal deterministic fixture for the confirmed shape.
6. Keep prose-only names excluded and retain strict structured-call matching.

Until raw events are available, the current four failures should be classified as **unresolved structured-observability failures**, not conclusively as “another Pi event-shape variant.”

## Confidence Assessment

**Certain:** The supplied artifact is an aggregate transcript; raw event shapes are absent. Four cases failed structured tool detection, all four report unavailable tool advertisements, and the final suite result is 16 passed/4 failed.[^1] The generated outputs for the failed cases are detailed but do not prove structured invocation.[^2][^3][^4][^6]

**Likely:** At least some failures may result from parser coverage gaps or unavailable/nested tool-list events, because the current parser uses shallow, allow-listed paths and the failures are case-specific.[^3][^7]

**Uncertain:** The exact Pi event-shape variant, whether each model response actually invoked an MCP tool, and whether the four cases share one schema. The referenced artifact cannot answer those questions.

## Footnotes

[^1]: `D:\workspace\fpac-soil-mcp-evals\.evals\eval_20261005_3.txt:1-8,10-807` — artifact inventory, transcript structure, case boundaries, and aggregate result.
[^2]: `D:\workspace\fpac-soil-mcp-evals\.evals\eval_20261005_3.txt:87-102` — POINT-02 failure diagnostic and generated point-result output.
[^3]: `D:\workspace\fpac-soil-mcp-evals\.evals\eval_20261005_3.txt:117-127,207-218`; `D:\workspace\fpac-soil-mcp\eval\run_evals.py:159-255,277-351,487-547`; `D:\workspace\fpac-soil-mcp\eval\test_agent_eval.py:189-238`.
[^4]: `D:\workspace\fpac-soil-mcp-evals\.evals\eval_20261005_3.txt:464-524` — PROMPT-01 failure diagnostic and generated output.
[^5]: `D:\workspace\fpac-soil-mcp-evals\.evals\eval_20261005_3.txt:558-588` — PROMPT-03 passing result.
[^6]: `D:\workspace\fpac-soil-mcp-evals\.evals\eval_20261005_3.txt:659-798` — LESA-01/LESA-02 comparison and LESA-02 failure/output.
[^7]: `D:\workspace\fpac-soil-mcp\eval\run_evals.py:390-419` — advertised-tool extraction and bounded retry conditions.
