# Research: Extending the Pi Eval Workflow to Databricks

Status: research note (no code changed)
Scope: `eval/` in this repo, `eval/` in `mcp-hackathon-template`, and the Databricks capabilities available in this workspace.
Companion: the template-side architecture review (Phoenix stub vs. Databricks/MLflow kit) supplied with the request. This note does not repeat it; it applies it to fpac-soil-mcp.

## 1. Summary

The current eval is a **Pi CLI harness**: it runs `pi` in a temp sandbox, launches this server over stdio with `uv`, and marks each of 21 prompts PASS/FAIL by checking that the expected tool name appears in Pi's JSON event stream and that expected keywords appear in the final text [S1][S2][S3]. It is a solid tool-routing smoke test, but it cannot run on Databricks: `pi` and `npm` are not installed on serverless compute, and the harness has no ground-truth answers, no LLM judging, and no persisted results [E1].

The template offers two patterns [S5][S6][S7]: a Phoenix/LangChain local harness (documented only, not implemented) and an MLflow GenAI offline kit that calls a **deployed** Databricks App over HTTPS with a service principal. Both depend on libraries that are not on serverless by default (`openai-agents`, `databricks-openai`, `langchain`, `phoenix`) [E1].

Recommendation: keep Pi as the laptop smoke test and add a **Databricks-native tier built on MLflow 3.12**, which is already installed [E1]. It has three layers that share one dataset:

| Tier | What it proves | Transport | Auth | New deps |
|---|---|---|---|---|
| T0 contract | Tools, resources, and prompts register and return the regulatory notice | FastMCP in-memory client | none | none beyond the package |
| T1 in-process agent eval | An LLM can pick and call the right tools and produce correct, compliant answers | FastMCP in-memory client + Databricks foundation model endpoint | notebook identity | `openai` (via `databricks-sdk[openai]`) |
| T2 deployed eval | The live `mcp-fpac-soil` App behaves the same as T1 | Streamable HTTP `/mcp` | SP OAuth M2M (template kit) or a Unity Gateway MCP service | as T1 + MCP HTTP client |

T1 avoids the template's main cost: you don't need a service principal, a generated agent, or the persistent event-loop workaround. The server runs in the evaluating process, and only the model call leaves it. T2 reuses the template kit almost unchanged once T1's dataset and scorers exist.

## 2. Current Pi workflow (fpac-soil-mcp)

### 2.1 Inventory

| File | Role |
|---|---|
| `eval/run_evals.py` | Release benchmark CLI: `--category`, `--case-id`, `--model` (default `AGENT_EVAL_MODEL` or `gpt-5.6-luna`), `--timeout 300`, `--verbose`, `--show-output` [S1 L35-76] |
| `eval/test_agent_eval.py` | Pytest harness: offline unit tests for event parsing + one live Pi test (POINT-01) behind `@pytest.mark.agent_eval` [S2] |
| `eval/prompt_test_cases.json` | v1.0.0 dataset: 21 cases with `id`, `category`, `target_type`, `target_name`, `user_prompt`, `expected_tools`, `expected_keywords`, optional `sample_geometry` [S3] |
| `pyproject.toml` | `testpaths = ["tests", "eval"]`; default `addopts` deselects `live_network` and `agent_eval` [S4 L45-52] |
| `Makefile` | `make test-eval` / `make eval` -> `python eval/run_evals.py` [S8 L44-47] |

### 2.2 Execution flow

1. `create_sandbox` writes `.mcp.json` and `mcp_config.json` to a temp dir. These register server `fpac-soil` as `uv --directory <repo> run fpac-soil-mcp` with `MCP_TRANSPORT=stdio` [S1 L119-145].
2. For each case, run `pi --no-session --mode json --mcp-config ... --append-system-prompt "<must call tools>" -p "Call the appropriate fpac-soil MCP tool/resource and <prompt>"` [S1 L342-355].
3. Parse JSONL events, then extract executed tool names from many possible event shapes and advertised tools from init/list events [S1 L159-309].
4. If an expected tool was advertised but not called, retry once with an explicit "execute tool X now" suffix [S1 L398-412].
5. PASS requires every expected tool to be called (suffix match `_name` / `:name`) and every keyword to appear in the normalized assistant text. Otherwise the result is FAIL, TIMEOUT, or ERROR [S1 L418-471].
6. Print a summary table and exit 1 on any failure [S1 L515-533].

### 2.3 Dataset coverage

| Group | Cases | Expected tools | Notes |
|---|---|---|---|
| Discovery | DISC-01, DISC-02 | `explain_fppa_screening_scope`, `list_farmland_classes` | |
| Point / mukey | POINT-01, POINT-02, MUKEY-01 | point, mukey | POINT-01 checks exact coordinates in the pytest variant [S2 L595-604] |
| Polygon | POLY-01, POLY-02 | `analyze_farmland_by_polygon`, `get_soil_polygons_by_geometry` | |
| Urban / interp | URBAN-01, INTERP-01 | `check_urban_area_exemption`, `get_soil_interpretations` | |
| Corridor | CORR-01, CORR-02 | `analyze_corridor_fppa` | CORR-02 compares alternatives |
| Resources | RES-01..03 | none (empty list) | Keyword-only |
| Prompts | PROMPT-01..04 | 2 of 4 have a tool; 2 empty | Keyword-only for PROMPT-02/04 |
| LESA | LESA-01, LESA-02 | `calculate_preliminary_lesa` | Known ranges: LESA-01 about 181, LESA-02 68.38 (from project memory, user-confirmed) |

All 10 manifest tools, 3 resources, and 4 prompts have at least one case [S3][S9].

### 2.4 Defects and limits in the current harness

These are worth fixing whatever happens with Databricks:

1. **Encoding defect.** The `§` sign is stored as `\u00c2\u00a7` (mojibake `Â§`) in URBAN-01, CORR-01, PROMPT-02, and LESA-01 [S3]. NFKD normalization does not repair it, and models will see `Â§`.
2. **Coverage assertion misses a tool.** `test_prompt_dataset_schema_and_completeness` lists 9 expected tools and omits `calculate_preliminary_lesa` [S2 L504-514]. The manifest prompt description also says "all 9 tools" while 10 are published [S9 L40].
3. **`WARN` status is dead code, and would be double-counted if used.** No path sets `WARN`, but the summary counts `WARN` in both `warned` and `failed` [S1 L524-526].
4. **Duplicated parsing logic.** `normalize_text`, `extract_structured_tool_names`, and `extract_assistant_content` are copied between `run_evals.py` and `test_agent_eval.py`. `extract_tool_calls`, which captures arguments, exists only in the test module [S1][S2 L244-341].
5. **Keyword-only cases can pass from memory.** The 3 RES cases and PROMPT-02/04 have no expected tool, so any answer containing "AD-1006" and "NRCS-CPA-106" passes [S3].
6. **Forced tool use.** The prompt prefix and system suffix require tool calls [S1 L350-352]. This tests routing well, but it rules out testing scope refusals, which the template's scope judge exists to cover [S6].
7. **No ground truth.** No case asserts a mukey, farmland class, acreage, or score value. Correct values are known but not recorded (MUKEY-01 "statewide importance" is the closest).
8. **No persistence or variance tracking.** Results go to stdout only. Known LESA run-to-run variance cannot be tracked over time.

## 3. Template eval kit (mcp-hackathon-template)

These are the parts of the template kit [S5][S6][S7] that matter here:

* `eval/README.md` is a stub that points to an `mcp-eval` skill for an `eval/phoenix/` harness: a LangChain agent over stdio, XML-to-CSV datasets, correctness and scope judges, and versioned system prompts [S5]. No Phoenix code is present.
* `eval/databricks/agent_eval_offline.py` is an import-and-run notebook script [S6]:
  * CONFIG block: MCP URL, `MODEL = "databricks-claude-haiku-4-5"`, host, experiment, secret scope, and scorers `[Safety, RelevanceToQuery, Correctness, Guidelines(conciseness)]` [S6 L51-77].
  * Imports the Playground-generated `agent_server.agent`, overrides `MODEL`/`MCP_SERVERS`, and forces the Responses API [S6 L95-106].
  * Patches auth with `eval_auth.patch_agent_with_service_principal` [S6 L111-116][S7 L76-98].
  * Sets the experiment and an explicit trace destination [S6 L123-129].
  * Runs one persistent background event loop so the cached async client never crosses loops [S6 L152-176].
  * `@mlflow.trace(span_type="AGENT") predict(request)` then `mlflow.genai.evaluate` [S6 L209-222].
* `setup-eval-sp.sh` provisions an SP, the `workspace-access` entitlement, `CAN_USE` on the app, an OAuth secret, and a secret scope (requires workspace admin) [S10].

What carries over: dataset row shape (`inputs` + `expectations.expected_facts`), scorer CONFIG block, explicit trace destination, SP M2M for the deployed hop, and `MLFLOW_GENAI_EVAL_MAX_WORKERS` tuning [S6 L131-133].

What does not carry over cleanly:

* The generated agent is an external artifact that is regenerated in the Playground, so it doesn't fit this repo's PR review flow.
* Placeholder dataset.
* No tool-call scoring. The template scores only the final text, while the Pi harness's strength is tool-call verification.

## 4. Databricks environment facts (verified in this workspace)

Checked on serverless compute during this research [E1]:

| Item | Finding |
|---|---|
| MLflow | 3.12.0 preinstalled |
| Built-in scorers available | `Correctness`, `Guidelines`, `ExpectationsGuidelines`, `RelevanceToQuery`, `Safety`, `Completeness`, `Equivalence`, `Fluency`, `ToolCallCorrectness`, `ToolCallEfficiency`, conversation scorers, retrieval scorers |
| Scorer data contracts | `ToolCallCorrectness` / `ToolCallEfficiency` require `trace` with `TOOL` spans; `Correctness` / `Guidelines` need `inputs` + `outputs` |
| Other GenAI APIs | `mlflow.genai.datasets.create_dataset`, `make_judge`, `register_prompt` / `load_prompt`, `LabelingSession`, `ConversationSimulator`, `optimize_prompts` |
| Foundation model endpoints | 56 serving endpoints, including `databricks-gpt-5-6-luna` (same family as Pi's default `gpt-5.6-luna`), `databricks-claude-sonnet-4-5`/`4-6`/`5`, `databricks-claude-haiku-4-5`, `databricks-gemini-3-*-flash`, `databricks-gpt-oss-120b`, Llama 3.3 70B |
| CLIs | `pi` missing; `npm`/`npx` missing; `node` present; `uv` present |
| Python libs | `openai`, `databricks_openai`, `agents`, `databricks_mcp`, `langchain`, `phoenix`, `fastmcp` not importable by default (`fastmcp` arrives with this package); `databricks-sdk` 0.122.0 |
| Deployed app | `mcp-fpac-soil` RUNNING, compute ACTIVE |

Relevant platform guidance:

* `ToolCallCorrectness` accepts `expectations.expected_tool_calls` (name-only or name+arguments, fuzzy or exact, optionally ordered) [D1].
* `WorkspaceClient().serving_endpoints.get_open_ai_client()` returns an authenticated OpenAI client for foundation model endpoints [D2].
* An App-hosted MCP server needs `CAN USE` on the app plus the app's OAuth scopes. Servers registered as Unity Gateway MCP services are reached at `https://<workspace>/ai-gateway/mcp-services/<catalog>.<schema>.<service>`, and access is granted as a Unity Catalog securable [D3][D4][D5].

## 5. Why Pi alone cannot be the Databricks path

* Pi is a Node CLI and npm is unavailable on serverless. Installing it would require a custom environment or an init script [E1].
* Pi's output is a vendor event stream. The harness spends about 150 lines guessing its shape [S1 L159-309], and those guesses would need to be ported into MLflow traces anyway.
* Pi's model routing is configured outside the repo. The default `gpt-5.6-luna` matches the Databricks endpoint family, but this research did not confirm whether Pi already routes through Databricks (open question Q1).

Pi is still worth keeping. It is the only harness that exercises a real third-party MCP client, which tests client-side tool naming such as `fpac-soil_read_get_regulatory_notice_resource` [S3]. That is a real compatibility signal and should stay as the local tier.

## 6. Proposed Databricks-native design

### 6.1 T0: deterministic contract checks (no LLM)

Use FastMCP's in-memory client (`fastmcp.Client(create_mcp_server())`) to list tools, resources, and prompts, then call a few cheap tools [D6]. Assert the following:

* The tool, resource, and prompt sets equal `manifest.yaml`. This would have caught defect 2.4.2.
* Every soil-query response carries the preliminary-screening limitation (AGENTS.md operational rule).
* Invalid inputs (bad coordinates, non-numeric mukey) return structured errors.

These checks run as normal pytest (offline with the mocked `httpx` transports in `tests/conftest.py`) and in Databricks. The in-memory API should be checked against the installed FastMCP version before you build on it.

### 6.2 T1: in-process agent eval with MLflow (primary new work)

Components, all in `eval/databricks/` (or `eval/mlflow/`):

1. **Thin agent loop (about 100 lines, no generated code).**
   * Discover tools from the in-memory FastMCP client and convert them to OpenAI function-tool schemas.
   * Expose resources as a `read_resource(uri)` tool and prompts as `get_prompt(name, args)`. This lets RES and PROMPT cases assert a real call instead of keywords alone (fixes 2.4.5).
   * Call `get_open_ai_client()` against a configurable endpoint (default `databricks-gpt-5-6-luna` for parity with Pi; also run a Claude endpoint).
   * Run the loop until the model stops calling tools, with a max-turn cap.
2. **Tracing.**
   * Decorate the entry point with `@mlflow.trace(span_type="AGENT")`.
   * Wrap each tool dispatch in `mlflow.start_span(span_type="TOOL")` with name and arguments, which satisfies the `ToolCallCorrectness` contract.
   * Alternatively, use `mlflow.openai.autolog()` for LLM spans.
   * Set the experiment and an explicit trace destination as the template does [S6 L123-129].
3. **Predict function.** `predict(request: str) -> str` matches the row key `inputs.request`, which the template requires [S6 L139-141].
4. **Scorers.** See 6.4.
5. **Run surfaces.**
   * Notebook for interactive work.
   * Lakeflow Job on serverless for scheduled runs from the team-03 prod clone, which tracks `main`.

Why in-process:

* No SP, secret scope, or app ACL is needed.
* No async event-loop workaround is needed, because the loop is synchronous.
* The server code under test is the checked-out commit, which makes branch comparisons straightforward.
* Upstream SDA, TIGERweb, and NASS calls still go live, so T1 is a `live_network` eval.

### 6.3 T2: deployed-app eval

Run the same dataset and scorers, but replace the in-memory transport with Streamable HTTP to `https://mcp-fpac-soil-7474654188777746.aws.databricksapps.com/mcp`. There are two auth options:

* **Template SP path:** reuse `eval_auth.build_service_principal_client` and `setup-eval-sp.sh` [S7][S10]. Note the template review's warnings: ACL replace vs. merge, and secrets passed as CLI arguments.
* **Unity Gateway path:** register the app as an MCP service, which is already the next step in the deployment plan. Grant the eval identity on the securable and call `/ai-gateway/mcp-services/...` [D4][D5]. This option fits the team-03 grant model better. Verify that a notebook or job identity can call it before adopting it.

Comparing T1 and T2 results on the same rows separates code defects (both fail) from deployment, auth, or runtime defects (only T2 fails).

### 6.4 Scorer mapping (Pi check to MLflow)

| Current Pi check / need | MLflow implementation | Type |
|---|---|---|
| Expected tool was called (suffix match) | `@scorer required_tools_called(trace, expectations)` that ports `_tool_matches` | deterministic bool |
| Expected tool with correct arguments (POINT-01 coordinates) | `ToolCallCorrectness(should_exact_match=False)` with `expected_tool_calls` [D1]; plus a deterministic numeric-tolerance check for coordinates | judge + bool |
| Expected keywords present | `@scorer keywords_present(outputs, expectations)` that ports `normalize_text` | deterministic bool |
| (new) Factually correct answer | `Correctness()` with `expected_facts` | judge |
| (new) Regulatory compliance | `Guidelines` (or `ExpectationsGuidelines` per row): "States that results are preliminary screening and not an official FPPA determination, LESA score, AD-1006, or NRCS-CPA-106" | judge |
| (new) Numeric ground truth (LESA total, acres) | `@scorer numeric_within_tolerance(trace, expectations)` that reads the tool span output, not prose | deterministic bool |
| (new) Tool efficiency / no redundant SDA calls | `ToolCallEfficiency()` | judge |
| (new) Scope refusal | `Guidelines` on new out-of-scope rows (run without the forced-tool prefix) | judge |
| Safety | `Safety()` | judge |

Prefer the deterministic scorers. They are cheaper, and they match the Pi semantics, so results stay comparable across tiers. Validate every scorer on a three-row dry run so you see non-null values before a full run.

## 7. Shared dataset: `prompt_test_cases.json` v2

Keep one source of truth in the repo. Extend it in a backward-compatible way so Pi keeps working:

| v1 field | v2 addition | Consumed by |
|---|---|---|
| `user_prompt` | (unchanged) maps to `inputs.request` | Pi, MLflow |
| `expected_tools` | `expected_tool_calls: [{name, arguments?}]` | Pi (names), `ToolCallCorrectness` |
| `expected_keywords` | (unchanged) | Pi, keyword scorer |
| (none) | `expected_facts: [str]` | `Correctness` |
| (none) | `numeric_expectations: [{path, value, abs_tol}]` (for example, LESA-01 total about 181 with tolerance, LESA-02 LE 68.38) | numeric scorer |
| (none) | `guidelines: [str]` per row | `ExpectationsGuidelines` |
| (none) | `force_tool_use: bool` (default true; false for scope rows) | both runners |
| (none) | `live_data_sensitive: bool` (SDA refreshes can shift values) | reporting |

A small loader converts rows to MLflow records. Optionally, sync them into a versioned MLflow evaluation dataset (`mlflow.genai.datasets.create_dataset`, UC-backed) so runs reference a dataset version. The JSON file stays the source of truth for review.

Ground-truth authoring is still the largest effort, as noted in earlier project memory. Start with deterministic values that can be read from SDA directly: mukey, farmland class, and NCCPI for POINT-01, MUKEY-01, and INTERP-01. Use LESA values only within the observed variance.

## 8. Operational considerations

* **Rate limits and live data.**
  * T1 and T2 call SDA, TIGERweb, and NASS live. Set `MLFLOW_GENAI_EVAL_MAX_WORKERS` to 1 or 2 [S6 L131-133].
  * Keep these runs out of the default offline test path, per the AGENTS.md rule.
  * Tag rows whose values drift with upstream data refreshes.
* **Cost estimate.**
  * About 21 rows × (1 agent run with 1-4 LLM turns + 3-4 judge calls) is roughly 100-150 model calls per run.
  * The default scheduled cadence should be nightly or per PR merge, not hourly.
  * Use a fixed judge endpoint that differs from the agent endpoint to reduce self-preference bias [S5].
* **Privacy (Section 1619).**
  * Traces store prompts, tool arguments, and tool outputs, including coordinates and geometries.
  * The current fixtures are synthetic, but any future producer-derived case must go through `privacy.py` redaction before it is logged.
  * Limit experiment ACLs to team-03.
* **Where to run.**
  * Scheduled jobs should run from the shared prod clone (`/Workspace/Users/Groups/team-03/fpac-soil-mcp`, always on `main`).
  * Branch comparisons should run from personal clones into the same experiment, tagged with `git_sha` and branch.
* **Environment.**
  * Install the package from the repo (`%pip install -e .` or `requirements.txt` `.`) plus `databricks-sdk[openai]`.
  * Previous serverless runs needed a shapely reinstall (project memory). Pin that in the job environment.
* **Prompt versioning.**
  * The template's v1/v2 system-prompt idea [S5] maps to `mlflow.genai.register_prompt` / `load_prompt`.
  * The current forced-tool suffix becomes prompt `v1`, and a scope-aware prompt becomes `v2`.

## 9. Proposed layout

```text
eval/
├── prompt_test_cases.json      # v2, shared source of truth
├── run_evals.py                # Pi local tier (unchanged CLI)
├── test_agent_eval.py          # Pi pytest tier
├── common/
│   ├── dataset.py              # load/validate v2, to_mlflow_records()
│   └── matching.py             # normalize_text, tool-name matching, extract_tool_calls (dedup of 2.4.4)
├── contract/
│   └── test_contract.py        # T0, in-memory FastMCP
└── databricks/
    ├── agent.py                # thin OpenAI tool loop over a pluggable MCP transport
    ├── scorers.py              # deterministic + configured judges
    ├── run_mlflow_eval.py      # notebook/job entry: tier=T1|T2, model, judge, experiment
    └── eval_auth.py            # copied from template for T2 SP path
```

No generated Playground agent is committed. If the team later deploys a Playground agent, T2 can wrap it with the template's `agent_eval_offline.py` unchanged.

## 10. Suggested rollout

1. **Fix the harness defects in 2.4.1-2.4.4.** These are small, and they unblock everything else.
2. **Add the T0 contract tests** to the default offline suite.
3. **Define the v2 dataset schema and loader.** Author ground truth for 5-6 deterministic cases first.
4. **Build the T1 agent loop, scorers, and notebook.** Do a five-case pipeline check, then the full 21.
5. **Schedule T1 as a serverless job** from the prod clone with results in a shared experiment.
6. **Add T2.** First decide between SP M2M and the Unity Gateway MCP service.
7. **Expand the dataset** toward 50+ rows and add out-of-scope rows. Optionally add a labeling session so FPAC SMEs can align the compliance judge.

## 11. Open questions

* Q1: Does Pi's `gpt-5.6-luna` already route through Databricks foundation model endpoints or AI Gateway, or through another provider? This determines whether Pi and T1 results are model-comparable.
* Q2: For T2, is a dedicated eval SP acceptable, or should eval wait for Unity Gateway MCP service registration?
* Q3: Which experiment location (workspace path vs. UC trace storage) and which catalog/schema should hold eval traces?
* Q4: Who signs off on ground-truth values for LESA cases given the observed run-to-run variance?

## Sources

Repository (workspace clones; line numbers as of this research):

* [S1] `fpac-soil-mcp/eval/run_evals.py`
* [S2] `fpac-soil-mcp/eval/test_agent_eval.py`
* [S3] `fpac-soil-mcp/eval/prompt_test_cases.json`
* [S4] `fpac-soil-mcp/pyproject.toml`
* [S5] `mcp-hackathon-template/eval/README.md` and `.agents/skills/mcp-eval/SKILL.md` (as summarized in the companion review)
* [S6] `mcp-hackathon-template/eval/databricks/agent_eval_offline.py`
* [S7] `mcp-hackathon-template/eval/databricks/agent_server/eval_auth.py`
* [S8] `fpac-soil-mcp/Makefile`
* [S9] `fpac-soil-mcp/manifest.yaml`
* [S10] `mcp-hackathon-template/eval/databricks/README.md` and `setup-eval-sp.sh`

Environment:

* [E1] Runtime introspection on serverless compute in this workspace: MLflow version, `mlflow.genai.scorers` surface and `required_columns`, `serving_endpoints.list()`, CLI and package availability, `apps.get("mcp-fpac-soil")`.

Documentation:

* [D1] [ToolCallCorrectness Judge](https://mlflow.org/docs/latest/genai/eval-monitor/scorers/llm-judge/tool-call/correctness/index.html)
* [D2] [Authentication for agents (Model Serving)](https://docs.databricks.com/aws/en/agents/custom-agents/model-serving/agent-authentication-model-serving/)
* [D3] [MCP authentication and networking](https://docs.databricks.com/aws/en/agents/mcp-tools/authentication-networking/)
* [D4] [Authentication for agents: MCP Services](https://docs.databricks.com/aws/en/agents/custom-agents/agent-authentication/)
* [D5] [External MCP servers (register an MCP service)](https://docs.databricks.com/aws/en/ai-gateway/register-mcp-service/)
* [D6] [FastMCP documentation](https://gofastmcp.com/) (client transports / in-memory testing; verify against installed version)
* [D7] [Custom MCP servers on Databricks Apps](https://docs.databricks.com/aws/en/agents/mcp-tools/custom-mcp/)
