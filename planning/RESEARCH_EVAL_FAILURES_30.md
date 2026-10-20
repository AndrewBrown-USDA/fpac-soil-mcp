# Research Summary — Pi Evaluation Failures

## Result

The 20-case run produced 17 passes and three failures: `RES-01`, `PROMPT-01`,
and `PROMPT-02`. The failures are evaluation/orchestration problems, not
missing production soil functionality.

## Findings

### RES-01

The resource `fppa://regulatory-notice` is registered and its payload contains
the exact canonical citations `7 CFR Part 657`, `7 CFR Part 658`, and
preliminary-screening language. The model summarized the citations as
`7 CFR Parts 657 and 658`, so the literal substring check did not find
`7 CFR Part 658`. Keep exact citation matching as the contract; improve the
resource-case instruction so citations are preserved rather than changing
production regulatory text.

Relevant anchors:

- `src\fpac_soil_mcp\resources\fppa_resources.py:12-23`
- `src\fpac_soil_mcp\constants.py:14-23,39-46`
- `eval\prompt_test_cases.json:292-302`
- `eval\run_evals.py:648-650`
- `tests\test_server.py:78-103`

### PROMPT-01

`get_farmland_classification_by_point` is implemented, exported, registered,
and covered by server tests. The prompt `fppa_screening_assistant` is also
registered and instructs the assistant to use the point tool. The artifact
shows the Pi gateway searching for the prompt as a tool and returning unrelated
tools instead of rendering the MCP prompt. The model therefore did not
reliably receive the prompt instructions or execute the expected point tool.

The `MCP tool list unavailable` diagnostic is also too broad: the evaluator
recognizes only limited direct initialization/list-tools shapes and may not
recognize gateway-mediated events.

Relevant anchors:

- `src\fpac_soil_mcp\prompts\fppa_prompts.py:8-39`
- `src\fpac_soil_mcp\tools\soil_tools.py:52-90,633-642`
- `src\fpac_soil_mcp\app.py:16-37`
- `eval\run_evals.py:262-291,418-460,637-658`
- `eval\prompt_test_cases.json:330-347`
- `tests\test_server.py:29-38,68-77`

### PROMPT-02

`fppa_corridor_screening_assistant` contains `7 CFR § 658.5(c)`, CPA-106
guidance, and the preliminary-screening limitation. The agent produced
generic request-for-input prose and omitted `658.5(c)`, indicating that it
did not reliably render/use the named MCP prompt. The fixture has no required
tool call, so it currently tests response keywords rather than prompt
transport.

Relevant anchors:

- `src\fpac_soil_mcp\prompts\fppa_prompts.py:50-85`
- `src\fpac_soil_mcp\constants.py:111-141`
- `src\fpac_soil_mcp\corridor_scoring.py:1-17,142-158,330-410`
- `eval\prompt_test_cases.json:345-354`
- `tests\test_server.py:180-213`

## Chosen remediation

- Keep prompts as MCP prompts; do not duplicate them as tools.
- Add deterministic `list_prompts()`/`render_prompt()` coverage in
  `tests\test_server.py`.
- Make prompt cases explicitly instruct Pi to invoke/render the named prompt,
  while retaining Pi as the end-to-end downstream-tool test.
- Broaden structured tool-list/gateway diagnostics without counting prose.
- Preserve exact RES-01 citation keywords and require citation preservation.
- Closure requires offline project tests, focused eval tests, Ruff,
  `git diff --check`, and one serial `agent_eval` run. Live network tests are
  deferred.

## Confidence and caveat

Confidence is high for the RES-01 literal mismatch and for production prompt
and tool registration. Confidence is moderate-to-high for the prompt
discovery diagnosis because it is based on the retained artifact trace. If a
future run predates commit `13fd3a0cfe812cd48e41d86a542ba7644cc07d98`, nested
Pi `mcpScript` calls may also be misclassified; compare the run commit before
interpreting missing-tool results.
