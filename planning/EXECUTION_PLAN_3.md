# EXECUTION PLAN 3: Phase 1 Domain, Governance, and Case State Model

## Goal & Scope

### Goal
Define the legal, data, governance, and lifecycle contracts for FPPA cases before adding polygon, corridor, scoring, form-generation, or persistence features. Phase 1 will add validated internal models and services for case data, authority states, workflow transitions, official-source metadata, privacy controls, public-data integration records, and capability-scoped integration configuration while preserving the server's preliminary-screening and human-authority boundaries.

### In Scope
- Pydantic models for `FppaCase`, `FppaRequest`, `AgencyProfile`, `ImpactArea`, `ExemptionClaim`, `CalculationRun`, and `DecisionRecord`.
- Value authority states: `machine_estimate`, `analyst_proposed`, `agency_approved`, and `nrcs_official`.
- An explicit attested human/import path for approved and official values that requires actor, timestamp, source reference, and rationale.
- Valid workflow transitions among `received`, `ready_for_analysis`, `analysis_complete`, `pending_nrcs_review`, `provisionally_complete`, and `closed`.
- A versioned, package-owned JSON registry for regulations, official form editions, and regional scoring configurations, validated through Pydantic models.
- Public-only request handling that rejects sensitive personal fields by default and provides an explicit sanitizer that reports removed fields.
- Provenance-bearing `UrbanExemptionRecord`, `CountyAgProfile`, and `SoilInterpretationRecord` models.
- Capability-scoped validated configuration for USDA NASS county profiles, Census TIGERweb urban-area screening, and SDA interpretations/NCCPI.
- Unit tests, cross-contract tests, and documentation for the internal Phase 1 contracts.

### Out of Scope
- New MCP case-management tools or other public MCP surface changes.
- Case persistence, SQLite schemas, migrations, audit-log storage, or authoritative agency database writes; these remain Phase 6 work.
- Live NASS, TIGERweb, or new SDA interpretation HTTP clients and requests; these remain Phases 2-4 work.
- Polygon/corridor geometry processing, acreage calculations, LE-SA scoring, alternatives comparison, form generation, and CPA-2 reporting.
- Authentication, role-based access control, ATO controls, or production authorization.
- Bundling invented regional scoring methods. The registry may represent that no approved regional configuration is currently available.

### Verbatim Constraints
- "Define the legal, data, and lifecycle state models before adding spatial and calculation features."
- "Automated code cannot set nrcs_official or agency_approved states."
- "Strip sensitive personal details from request payloads. Enforce public-only data handling."
- "Public-data records reject missing provenance, and integration configuration fails clearly when required settings are absent or invalid."
- "This service does not produce an official FPPA determination, LESA score, Form AD-1006, or NRCS-CPA-106."
- "Accept only validated coordinates or numeric positive mukey values. Do not add user-supplied SQL passthrough."
- "Do not make live SDA tests part of the default offline test path."

## Decision Log

- **2026-09-16**: Phase 1 adds internal models and services only; it does not expose MCP case-management tools.
- **2026-09-16**: `agency_approved` and `nrcs_official` values are admitted only through an explicit attested human/import path requiring actor, timestamp, source reference, and rationale.
- **2026-09-16**: Sensitive personal fields are rejected by default with field-specific errors. A separate explicit sanitizer may remove them but must return an audit of removed field paths.
- **2026-09-16**: Official-source registry data is stored as package-owned JSON and validated into Pydantic models at load time; no YAML dependency is added.
- **2026-09-16**: Orchestration may use up to three concurrent workers in isolated git worktrees. Full/shared test suites run serially at wave boundaries.
- **2026-09-16**: Workers use the cheapest capable model, with one verification retry followed by mid-tier escalation under the standard orchestration ladder.
- **2026-09-16**: Every wave closes with targeted task tests, then serial `uv run pytest -m "not live_sda"`, `uv run ruff check .`, and `uv run ruff format --check .`. The repository-wide format command has one recorded pre-existing failure in fenced examples in the research document; changed Python files must be clean and the known baseline must not worsen.
- **2026-09-16**: Integration configuration is capability-scoped. SDA-only startup remains valid; enabling or using NASS without its required API key fails clearly. TIGERweb and SDA interpretation settings have validated defaults.

## Technical Reconnaissance

- Repository: `D:\workspace\fpac-soil-mcp`; single Python package under `src\fpac_soil_mcp`.
- Next orchestration number is 3; Orchestrations 1 and 2 are complete.
- Current offline baseline: `42 passed, 3 deselected` from `uv run pytest -m "not live_sda" -q`.
- Current public surface is stateless point/mukey screening. Phase 1 should not modify tool registration, server manifests, or runtime routes.
- Existing model pattern: Pydantic `BaseModel` classes with `Field` descriptions in `src\fpac_soil_mcp\models.py`.
- Existing settings pattern: `pydantic-settings` `BaseSettings` with `.env` loading in `src\fpac_soil_mcp\config.py`.
- Existing regulatory language and citations are centralized in `src\fpac_soil_mcp\constants.py`; new registry data must not create divergent disclaimer text.
- Existing tests are offline pytest tests with mocked network behavior. Live SDA tests are marked `live_sda`.
- Key file sizes: `models.py` 77 lines, `config.py` 37, `fppa.py` 63, `constants.py` 103, `test_server.py` 115, `test_tools.py` 165, `test_sda_client.py` 178. No current file requires whole-file avoidance, but workers should still use the listed anchors.
- There is no persistence layer, identity provider, role system, NASS client, TIGERweb client, or interpretation engine to reuse.

## Hazards and Guardrails

- **Authority confusion**: Enum membership alone must not let automated constructors claim approval or official status. Privileged creation must require an attestation object and a distinct API.
- **Silent privacy loss**: Default request validation must reject sensitive fields rather than silently discard them. Sanitization must be explicit and auditable.
- **Premature persistence**: IDs and timestamps may be modeled, but no database, repository abstraction, or event store belongs in this phase.
- **Global-startup regression**: Missing NASS credentials must not break the existing SDA-only server import or startup path.
- **Registry drift**: Registry entries must cite authoritative URLs, carry edition/effective/version metadata, and validate uniqueness. Do not duplicate or replace `REGULATORY_NOTICE`.
- **Invented methods**: Regional scoring configuration schemas may be defined, but no method may be represented as approved without an authoritative source record.
- **Future geometry coupling**: `ImpactArea` should carry geometry identity/type and acreage categories without implementing spatial computation or importing a geometry stack.
- **Concurrency**: Workers in the same wave must use isolated worktrees. The orchestrator runs shared/full suites serially.

## Wave Dependency Graph

```text
3.1.1 Authority and Provenance Primitives
  ├── 3.2.1 FPPA Case Domain Models ──┐
  ├── 3.2.2 Public Integration Records│
  ├── 3.2.3 Public-Only Privacy Policy │
  ├── 3.2.4 Official Source Registry   ├── 3.3.1 Workflow State Machine
  └── 3.2.5 Integration Configuration  │
                                      └── 3.4.1 Phase 1 Contract Integration
```

## Wave Table

| Wave | Task ID | Title | Files in Scope | Depends On |
| --- | --- | --- | --- | --- |
| 1 | `3.1.1` | Authority and Provenance Primitives | `authority.py`, `test_authority.py` | None |
| 2 | `3.2.1` | FPPA Case Domain Models | `case_models.py`, `test_case_models.py` | `3.1.1` |
| 2 | `3.2.2` | Public Integration Records | `integration_models.py`, `test_integration_models.py` | `3.1.1` |
| 2 | `3.2.3` | Public-Only Privacy Policy | `privacy.py`, `test_privacy.py` | `3.1.1` |
| 2 | `3.2.4` | Official Source Registry | `official_sources.py`, `data\*.json`, `test_official_sources.py` | `3.1.1` |
| 2 | `3.2.5` | Integration Configuration | `config.py`, `.env.example`, `test_config.py` | `3.1.1` |
| 3 | `3.3.1` | Workflow State Machine | `workflow.py`, `test_workflow.py` | `3.2.1`, `3.2.3` |
| 4 | `3.4.1` | Phase 1 Contract Integration | `test_phase1_contracts.py`, `README.md` | `3.2.1`-`3.3.1` |

> Wave 2 has five file-disjoint tasks. Run at most three workers concurrently, then start the remaining workers as slots open.

## Task Specifications

### Task 3.1.1: Authority and Provenance Primitives

- **ID**: `3.1.1`
- **Repo**: `.`
- **Files in Scope**:
  - *Must create*: `src\fpac_soil_mcp\authority.py`, `tests\test_authority.py`, `planning\tasks\3.1.1.todo.md`
  - *May edit for report only*: `planning\STATE_3.md`
  - *Temp/scratch*: `.development\`
- **Depends on**: None
- **Spec Prose**: Define the shared governance vocabulary used by all Phase 1 models. Add string enums for value authority and actor category, a reusable provenance model requiring source name, source reference, retrieval/recorded timestamp, method version, and configuration version, and an attestation model requiring human actor identity, actor category, timestamp, source reference, and rationale. Provide a generic authority-bearing value model with ordinary constructors restricted to `machine_estimate` and `analyst_proposed`. Provide a clearly named attested constructor for `agency_approved` and `nrcs_official` that requires a valid attestation and rejects mismatched actor categories. Keep the model serialization stable and JSON-friendly.
- **Constraints / Do Not Touch**:
  - Do not edit existing `models.py`, `constants.py`, tools, routes, manifests, or documentation.
  - Do not add authentication or infer that an actor string proves authorization.
  - Do not allow a boolean bypass such as `trusted=True`.
- **Grep Anchors / References**:
  - Pattern-match Pydantic style in `src\fpac_soil_mcp\models.py` at `class QuerySource`.
  - Preserve authority language in `src\fpac_soil_mcp\constants.py` at `REGULATORY_NOTICE`.
  - Plan requirement: `### Phase 1: Domain, Governance & Case State Model`.
- **Acceptance & Targeted Test Command**:
  - Ordinary construction accepts only machine/analyst states.
  - Approved/official construction fails without complete attestation.
  - Actor category must correspond to the requested approved/official authority.
  - Provenance rejects missing/blank source, method, configuration, or timestamp data.
  - Run `uv run pytest tests\test_authority.py -q`.

### Task 3.2.1: FPPA Case Domain Models

- **ID**: `3.2.1`
- **Repo**: `.`
- **Files in Scope**:
  - *Must create*: `src\fpac_soil_mcp\case_models.py`, `tests\test_case_models.py`, `planning\tasks\3.2.1.todo.md`
  - *May edit for report only*: `planning\STATE_3.md`
  - *Temp/scratch*: `.development\`
- **Depends on**: `3.1.1`
- **Spec Prose**: Implement Pydantic models for `AgencyProfile`, `FppaRequest`, `ImpactArea`, `ExemptionClaim`, `CalculationRun`, `DecisionRecord`, and aggregate `FppaCase`. Use explicit identifiers and timezone-aware timestamps. Model impact type (direct, indirect, alternative, excluded), geometry kind/hash/reference, and optional nonnegative acreage without performing geometry calculations. Exemption claims remain claims and require citation, rationale, evidence references, and an authority-bearing status; they must never imply that software grants an exemption. Calculation runs record method/configuration versions, inputs/evidence references, status, outputs, and limitations. Decision records distinguish preliminary, agency, and NRCS records and use the authority primitives rather than free-form status strings. The aggregate preserves ordered history and validates unique record/run/impact identifiers and internal case/request consistency.
- **Constraints / Do Not Touch**:
  - Do not edit `src\fpac_soil_mcp\models.py`; existing public response schemas remain stable.
  - Do not implement storage, repositories, geometry parsing, calculations, MCP tools, or automatic official decisions.
  - Do not include personal contact fields in request or agency models.
- **Grep Anchors / References**:
  - `src\fpac_soil_mcp\models.py`: `class SoilMapUnit`, `class FarmlandClassificationResponse`.
  - `planning\MASTER_PLAN.md`: `1. **Domain Data Models**`.
  - `planning\MASTER_PLAN.md`: `9. **Track request lifecycle`.
- **Acceptance & Targeted Test Command**:
  - All seven named models validate representative minimal and complete payloads.
  - Negative acreage, naive timestamps, duplicate nested IDs, and inconsistent case/request IDs fail.
  - Exemption and decision models retain preliminary/human-authority distinctions.
  - Model round trips preserve enums, timestamps, provenance references, and ordered histories.
  - Run `uv run pytest tests\test_case_models.py -q`.

### Task 3.2.2: Public Integration Records

- **ID**: `3.2.2`
- **Repo**: `.`
- **Files in Scope**:
  - *Must create*: `src\fpac_soil_mcp\integration_models.py`, `tests\test_integration_models.py`, `planning\tasks\3.2.2.todo.md`
  - *May edit for report only*: `planning\STATE_3.md`
  - *Temp/scratch*: `.development\`
- **Depends on**: `3.1.1`
- **Spec Prose**: Define provenance-bearing `UrbanExemptionRecord`, `CountyAgProfile`, and `SoilInterpretationRecord` models for later NASS, TIGERweb, and SDA clients. Records must represent successful, unavailable, and error outcomes explicitly. Urban records carry geometry hash, source layer/version, intersection evidence, screened acreage when known, and a preliminary status that cannot become a legal determination. County profiles carry state/county identifiers, census year, optional metrics, unavailable-field notices, and NASS provenance. Interpretation records carry mukey, rule name/version, aggregation method, rating/class, rated and total component percentages, limiting reasons, and SDA provenance. Validate numeric ranges and require provenance even when data is unavailable.
- **Constraints / Do Not Touch**:
  - Do not create HTTP clients, issue network requests, add spatial dependencies, or calculate NCCPI/LE scores.
  - Do not copy the research report's illustrative client code verbatim.
  - Do not label urban screening as a granted legal exemption.
- **Grep Anchors / References**:
  - `planning\RESEARCH_PUBLIC_APIS_AND_INTERPRETATIONS.md`: `## 2. USDA-NASS Quick Stats API Integration`.
  - `planning\RESEARCH_PUBLIC_APIS_AND_INTERPRETATIONS.md`: `## 3. Census TIGERweb 2020 Urban Areas MapServer Integration`.
  - `planning\RESEARCH_PUBLIC_APIS_AND_INTERPRETATIONS.md`: `## 4. Soil Data Access (SDA) Interpretation Engine & NCCPI v3`.
- **Acceptance & Targeted Test Command**:
  - Each record rejects absent provenance.
  - Success/unavailable/error states enforce coherent required and forbidden fields.
  - Percentages and normalized ratings reject out-of-range values.
  - Urban outputs remain explicitly preliminary.
  - Run `uv run pytest tests\test_integration_models.py -q`.

### Task 3.2.3: Public-Only Privacy Policy

- **ID**: `3.2.3`
- **Repo**: `.`
- **Files in Scope**:
  - *Must create*: `src\fpac_soil_mcp\privacy.py`, `tests\test_privacy.py`, `planning\tasks\3.2.3.todo.md`
  - *May edit for report only*: `planning\STATE_3.md`
  - *Temp/scratch*: `.development\`
- **Depends on**: `3.1.1`
- **Spec Prose**: Implement a narrow public-data policy for request payload mappings. Maintain an explicit case-insensitive set of prohibited personal-data field names and defensively detect nested occurrences, including common email, phone, person-name/contact, and street-address keys. Default validation returns field-specific paths and rejects the payload. Provide a separate sanitizer that returns a sanitized copy plus a structured list of removed field paths; it must not mutate the caller's object. Preserve operational/public organization fields such as agency name, project name, county, state, public office identifier, and geometry references.
- **Constraints / Do Not Touch**:
  - Do not silently sanitize during ordinary validation.
  - Do not inspect arbitrary string values with broad regexes that could flag public project text.
  - Do not add logging of rejected sensitive values.
  - Do not add third-party privacy dependencies.
- **Grep Anchors / References**:
  - `planning\MASTER_PLAN.md`: `5. **Security & Privacy Baseline**`.
  - `AGENTS.md`: `Surface errors explicitly`.
- **Acceptance & Targeted Test Command**:
  - Nested prohibited keys produce deterministic dotted/indexed field paths.
  - Sanitizer removes only prohibited fields, preserves allowed public fields, and leaves input unchanged.
  - Error/report objects never echo sensitive values.
  - Run `uv run pytest tests\test_privacy.py -q`.

### Task 3.2.4: Official Source Registry

- **ID**: `3.2.4`
- **Repo**: `.`
- **Files in Scope**:
  - *Must create*: `src\fpac_soil_mcp\official_sources.py`, `src\fpac_soil_mcp\data\official_sources.v1.json`, `src\fpac_soil_mcp\data\regional_scoring.v1.json`, `tests\test_official_sources.py`, `planning\tasks\3.2.4.todo.md`
  - *May edit for report only*: `planning\STATE_3.md`
  - *Temp/scratch*: `.development\`
- **Depends on**: `3.1.1`
- **Spec Prose**: Create versioned package JSON registries and a validated loader for regulations, official form editions, external public-data sources, and regional scoring configurations. Seed official source entries for 7 CFR Parts 657 and 658, AD-1006, NRCS-CPA-106, SDA, NASS Quick Stats, and Census TIGERweb using the citations and endpoints already documented in the repository. Each entry requires stable ID, registry schema version, authority/publisher, title, edition or effective date where applicable, canonical URL, retrieval guidance, and lifecycle status. Regional scoring configurations require jurisdiction, method/version, source record link, effective period, and approval authority; ship an empty configuration list rather than inventing an approved method. Fail clearly on missing files, malformed JSON, duplicate IDs, unsupported schema versions, and dangling source references.
- **Constraints / Do Not Touch**:
  - Do not edit or replace `REGULATORY_NOTICE` or `CITATIONS`.
  - Do not add YAML or another dependency.
  - Do not claim a form edition/effective date unless supported by repository research; represent unknown metadata explicitly.
- **Grep Anchors / References**:
  - `src\fpac_soil_mcp\constants.py`: `CITATIONS`.
  - `planning\RESEARCH_PUBLIC_APIS_AND_INTERPRETATIONS.md`: `## 1. System Architecture & External Integration Flow`.
  - `planning\MASTER_PLAN.md`: `4. **Official Source Registry**`.
- **Acceptance & Targeted Test Command**:
  - Packaged registries load from an installed/importable package path, not the current working directory.
  - Duplicate IDs, bad schema versions, malformed URLs, and dangling references fail.
  - Empty regional configuration is valid and does not imply an approved method exists.
  - Run `uv run pytest tests\test_official_sources.py -q`.

### Task 3.2.5: Integration Configuration

- **ID**: `3.2.5`
- **Repo**: `.`
- **Files in Scope**:
  - *Must edit*: `src\fpac_soil_mcp\config.py`, `.env.example`
  - *Must create*: `tests\test_config.py`, `planning\tasks\3.2.5.todo.md`
  - *May edit for report only*: `planning\STATE_3.md`
  - *Temp/scratch*: `.development\`
- **Depends on**: `3.1.1`
- **Spec Prose**: Extend settings with grouped, validated configuration for NASS county agricultural profiles, TIGERweb 2020 Urban Areas Layer 6, and SDA interpretations/NCCPI. Preserve current environment variable names and startup behavior. Add an optional NASS API key and explicit enablement/capability validation so base SDA-only startup succeeds without a key but enabled NASS use fails clearly without one. Add validated HTTPS endpoint defaults, positive timeouts/retry limits, NASS census year, TIGERweb layer identifier/spatial references, and an allowlist of supported SDA interpretation rule names and aggregation modes. Update `.env.example` without inserting credentials.
- **Constraints / Do Not Touch**:
  - Do not add clients, network calls, dependencies, or tool registration.
  - Do not make `USDA_NASS_API_KEY` mandatory for importing `settings`.
  - Preserve existing `SDA_TABULAR_URL`, timeout, retry, transport, host, and port compatibility.
- **Grep Anchors / References**:
  - `src\fpac_soil_mcp\config.py`: `class Settings`.
  - `.env.example`: `SDA_TABULAR_URL`.
  - `planning\RESEARCH_PUBLIC_APIS_AND_INTERPRETATIONS.md`: `### 2.1 API Overview & Authentication`, `### 3.1 Service Specification & Endpoints`, `### 4.2 SSURGO Interpretation Schema`.
- **Acceptance & Targeted Test Command**:
  - Existing default settings and environment overrides still validate.
  - Base startup/import succeeds with no NASS key.
  - Enabled NASS validation fails with a clear missing-key error.
  - Invalid URLs, years, spatial references, timeouts, retries, rule names, and aggregation modes fail.
  - Run `uv run pytest tests\test_config.py tests\test_server.py -q -m "not live_sda"`.

### Task 3.3.1: Workflow State Machine

- **ID**: `3.3.1`
- **Repo**: `.`
- **Files in Scope**:
  - *Must create*: `src\fpac_soil_mcp\workflow.py`, `tests\test_workflow.py`, `planning\tasks\3.3.1.todo.md`
  - *May edit for report only*: `planning\STATE_3.md`
  - *Temp/scratch*: `.development\`
- **Depends on**: `3.2.1`, `3.2.3`
- **Spec Prose**: Implement a pure, deterministic FPPA case workflow state machine for `received`, `ready_for_analysis`, `analysis_complete`, `pending_nrcs_review`, `provisionally_complete`, and `closed`. Define the allowed directed transitions, reject skips and backward transitions, and return a new case/state event rather than mutating the input. Transition guards must validate the minimum case evidence appropriate to each step: public-only request validation before analysis readiness; at least one completed calculation run before analysis completion; explicit pending-review evidence before NRCS review; a preliminary or attested decision before provisional completion; and closure rationale plus an attested human actor before closure. Automated callers must not create agency-approved or NRCS-official decisions as a side effect of transitioning.
- **Constraints / Do Not Touch**:
  - Do not implement persistence, reopen behavior, deletion, role authentication, scoring, or network calls.
  - Do not mutate `FppaCase` instances in place.
  - Do not infer approvals from workflow state names.
- **Grep Anchors / References**:
  - `src\fpac_soil_mcp\case_models.py`: `class FppaCase`, `class CalculationRun`, `class DecisionRecord`.
  - `src\fpac_soil_mcp\privacy.py`: public payload validator.
  - `planning\MASTER_PLAN.md`: `3. **Workflow State Machine**`.
- **Acceptance & Targeted Test Command**:
  - Every allowed transition passes with its required evidence.
  - Every unlisted skip/backward transition fails deterministically.
  - Missing readiness, calculation, review, decision, or closure evidence blocks the relevant transition.
  - Transition results preserve prior case data and append ordered transition history without mutating input.
  - No transition can synthesize `agency_approved` or `nrcs_official`.
  - Run `uv run pytest tests\test_workflow.py -q`.

### Task 3.4.1: Phase 1 Contract Integration

- **ID**: `3.4.1`
- **Repo**: `.`
- **Files in Scope**:
  - *Must edit*: `README.md`
  - *Must create*: `tests\test_phase1_contracts.py`, `planning\tasks\3.4.1.todo.md`
  - *May edit for report only*: `planning\STATE_3.md`
  - *Temp/scratch*: `.development\`
- **Depends on**: `3.2.1`, `3.2.2`, `3.2.3`, `3.2.4`, `3.2.5`, `3.3.1`
- **Spec Prose**: Add cross-contract tests proving the Phase 1 pieces compose: construct a public-only case, attach provenance-bearing public-data records, exercise valid workflow progression, verify automated official-value creation is blocked, load the official-source registry, and validate capability-scoped integration settings. Update README architecture/configuration sections to describe the internal case/governance model, authority boundary, public-data provenance records, privacy behavior, source registry, and new environment settings. Clearly state that no case persistence, public case-management MCP tools, official determinations, live integrations, or LESA calculations are added in Phase 1.
- **Constraints / Do Not Touch**:
  - Do not edit MCP tools, manifests, `server.json`, `QUICKSTART.md`, or runtime app registration.
  - Do not broaden integration tests into live network tests.
  - Do not duplicate the detailed research report.
- **Grep Anchors / References**:
  - `README.md`: `Architecture`, `Configuration`, `Limitations` or nearest equivalent headings.
  - `planning\MASTER_PLAN.md`: Phase 1 goal, deliverables, and exit criteria.
  - `planning\RESEARCH_PUBLIC_APIS_AND_INTERPRETATIONS.md`: `## Executive Summary`.
- **Acceptance & Targeted Test Command**:
  - Cross-contract test covers all Phase 1 exit criteria.
  - README documents every new setting and internal contract without claiming new MCP tools.
  - Run `uv run pytest tests\test_phase1_contracts.py -q`.

## Orchestrator Verification and Commit Rules

- Before Wave 1, record `git status --short`, Python/uv versions, and the baseline commands in `planning\STATE_3.md`.
- Workers run only their task's targeted tests. The orchestrator runs, serially after every wave:
  - `uv run pytest -m "not live_sda"`
  - `uv run ruff check .`
  - `uv run ruff format --check` on changed Python files
  - `uv run ruff format --check .` to verify the only repository-wide failure remains the recorded pre-existing research-document examples
- Live SDA, NASS, and TIGERweb tests are deferred because Phase 1 adds no network behavior.
- Inspect every task diff for out-of-scope files and authority/privacy language before approval.
- Use one conventional commit per task, one sentence, with no orchestration or wave number. Follow [[git-workflow-standards]](../../git-workflow-standards/SKILL.md).
- Apply the standard escalation ladder: two off-spec micro-plans trigger an orchestrator-authored plan; one failed verification retry triggers mid-tier re-execution; malformed reports get one correction attempt; out-of-scope edits require re-scoping the plan rather than widening worker permissions.
