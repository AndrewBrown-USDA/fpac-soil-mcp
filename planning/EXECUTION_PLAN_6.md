# EXECUTION PLAN 6: Master Plan Integration of ArcGIS Toolbox Parity & Streamlined Agent Workflows

## Goal & Scope

### Goal
Update `planning/MASTER_PLAN.md` with complete architectural and workflow parity details derived from the Colorado NRCS State GIS Specialist ArcGIS Python Toolbox research crosswalk (`planning/RESEARCH_ARCGIS_TOOLBOX_CROSSWALK.md`). Enhance the roadmap phases (Phases 3–6 and forward) to formalize streamlined natural-language agent interactions (AOI polygon/corridor centerline with buffer distance), live USDA NASS QuickStats and Census TIGERweb API baselines eliminating manual data preparation, relative Land Evaluation (LE) county normalization, 7 CFR § 658.5(c) corridor scoring rules, official Form AD-1006 / CPA-106 template tag mapping with clearance letters, and multi-agency Form CPA-2 annual reporting rollups.

### In Scope
1. **Master Plan Roadmap & Architecture Overhaul (`planning/MASTER_PLAN.md`)**:
   - **System Architecture & Principles**: Formalize the conversational AI agent paradigm shift eliminating desktop GIS (`arcpy`), manual CSV downloading, and local geodatabase maintenance in favor of on-demand authoritative REST endpoints (USDA SDA, NASS QuickStats, Census TIGERweb).
   - **Phase 3 Enhancement (Multi-County Corridor Analysis)**: Detail automated centerline buffering (`buffer_distance_feet`/`meters`/`miles`), geodesic equal-area reprojection, multi-county jurisdictional segmentation, urban corridor segment isolation, and 7 CFR § 658.5(c) scoring rules (Criteria 5 & 6 zeroed; Criteria 8 & 11 adjusted to 25 pts).
   - **Phase 4 Enhancement (Preliminary LE-SA Workbench)**: Incorporate relative value Land Evaluation normalization ($RR_i = \text{Rating}_i / \text{Max Rating}_{\text{county}}$, AOI weighted $RR_{\text{AOI}}$, and county percentile $\ge RR_{\text{AOI}}$), live NASS QuickStats agricultural baselines (irrigated acres, average farm size, farmable acres), and flexible state/county LE rating schedules (e.g. CSR2, CPI, Storie Index).
   - **Phase 5 Enhancement (Project Alternatives & Draft Form Generation)**: Add multi-alternative slot mapping (Site/Corridor B, C, D), watermarked draft `.docx`/`.pdf` generation for Form AD-1006 and Form NRCS-CPA-106 using canonical placeholder tags, and automated FPPA clearance letter generation (`Letter_Template.docx`).
   - **Phase 6 Enhancement (Case Archival & CPA-2 Annual Reporting)**: Expand SQLite case schema to track all 19 CPA-2 row indicators ($A$ through $H$) across the 22 standard Federal action agencies for automated fiscal year rollups.
2. **Task TODO Generation**:
   - Create granular micro-plan todo files in `planning/tasks/` for all Plan 6 tasks.
3. **Planning State & Prompt Artifacts**:
   - Create `planning/PROMPT_TEMPLATE_6.md` and `planning/STATE_6.md` conforming to wave orchestration specifications.

### Out of Scope
- Direct modifications to Python source code in `src/fpac_soil_mcp/` or test suites in `tests/` (strictly modifying planning artifacts in `planning/`).
- Writing raw binary template files (e.g. `.docx`, `.xlsx`, `.aprx`).

### Verbatim Constraints
- "just the master plan" (Scope focus strictly on planning and Master Plan documentation).
- "can add dedicated phases if needed but otherwise just enhance existing" (Enhance existing Phases 3 through 6 in-place and add explicit sub-sections and crosswalk references).
- "subagent_concurrency=2" (Max 2 concurrent subagents per wave).
- "produce your research document without altering any of the code in this repository, but write the final artifact as .md file in planning/ folder".
- "Preserve the preliminary-screening limitation in every soil-query response: this service does not produce an official FPPA determination, LESA score, Form AD-1006, or NRCS-CPA-106."

---

## Decision Log

- **2026-09-17**: Scope of Execution Plan 6 is dedicated to updating `planning/MASTER_PLAN.md` and related wave execution scaffolds, integrating all findings from `planning/RESEARCH_ARCGIS_TOOLBOX_CROSSWALK.md`.
- **2026-09-17**: Enhance Phases 3, 4, 5, and 6 in-place within `MASTER_PLAN.md` with explicit citations to `RESEARCH_ARCGIS_TOOLBOX_CROSSWALK.md`, mathematical LE/SA formulations, template placeholder mappings, and CPA-2 multi-agency indicators.
- **2026-09-17**: Set worker concurrency limit to 2 for Plan 6 wave execution.

---

## Hazard Notes from Reconnaissance

- **Master Plan Consistency**: Ensure updated phase deliverables match existing completed Phase 0, Phase 1, and Phase 2 architectures (FastMCP, Pydantic models, server-side spatial clipping) without regressing previous architectural decisions.
- **Regulatory Precision**: Strictly maintain non-binding advisory disclaimers and human authority boundaries in all revised phase specifications.

---

## Wave Dependency Table

```
Wave 1 (Corridor & LESA Phase Specifications)
  ├── 6.1.1: Enhance Master Plan Phase 3 (Corridor Analysis) & Phase 4 (LE-SA Workbench) (MASTER_PLAN.md)

Wave 2 (Form Generation, CPA-2 Archival & Agent Interaction)
  ├── 6.2.1: Enhance Master Plan Phase 5 (Form & Letter Generation) & Phase 6 (CPA-2 Reporting) (MASTER_PLAN.md)

Wave 3 (Synthesis, Overview & Architecture Alignment)
  ├── 6.3.1: Update Master Plan Architecture, Principles & Tool Surface (MASTER_PLAN.md)
  ├── 6.3.2: Synchronize Planning Artifacts & Verification (PROMPT_TEMPLATE_6.md, STATE_6.md)
```

| Task ID | Wave | Title | Files in Scope | Depends On |
| --- | --- | --- | --- | --- |
| `6.1.1` | 1 | Enhance Master Plan Phase 3 & Phase 4 Specifications | `planning/MASTER_PLAN.md`, `planning/tasks/6.1.1.todo.md` | None |
| `6.2.1` | 2 | Enhance Master Plan Phase 5 & Phase 6 Specifications | `planning/MASTER_PLAN.md`, `planning/tasks/6.2.1.todo.md` | `6.1.1` |
| `6.3.1` | 3 | Update Master Plan Architecture & Tool Surface | `planning/MASTER_PLAN.md`, `planning/tasks/6.3.1.todo.md` | `6.2.1` |
| `6.3.2` | 3 | Synchronize Planning Artifacts & Verification | `planning/PROMPT_TEMPLATE_6.md`, `planning/STATE_6.md`, `planning/tasks/6.3.2.todo.md` | `6.2.1` |

---

## Task Specifications

### Task 6.1.1: Enhance Master Plan Phase 3 & Phase 4 Specifications
- **ID**: `6.1.1`
- **Repo**: `.`
- **Files in Scope**:
  - *Must edit*: `planning/MASTER_PLAN.md`
  - *Must create*: `planning/tasks/6.1.1.todo.md`
  - *May edit for report only*: `planning/STATE_6.md`
- **Depends on**: None
- **Spec Prose**: 
  1. In `planning/MASTER_PLAN.md`, expand **Phase 3: Multi-County Corridor Analysis (CPA-106)**:
     - Detail plain-language corridor centerline ingestion (`LineString`/`MultiLineString`) with automated geodesic buffering (`buffer_distance_feet`, `buffer_units`).
     - Define spatial segmentation across county and soil survey area boundaries, computing direct vs. indirect impact acreages.
     - Specify implementation of 7 CFR § 658.5(c) corridor scoring rules (Criteria 5 and 6 zeroed; Criteria 8 and 11 adjusted to 25 points each).
     - Detail live NASS QuickStats integration per intersected county.
  2. Expand **Phase 4: Preliminary Land Evaluation & Site Assessment Workbench**:
     - Formalize relative value Land Evaluation scoring ($RR_i = \text{Rating}_i / \text{Max Rating}_{\text{county}}$, weighted AOI $RR_{\text{AOI}}$, and % county farmland $\ge RR_{\text{AOI}}$).
     - Specify dynamic Soil Data Viewer (`sdvattribute`) routing for state productivity indexes (CSR2 in Iowa, CPI in Minnesota, Storie Index in California) and fallback to NCCPI v3.
     - Formalize objective Site Assessment calculations (perimeter agricultural ratio via TIGERweb, farm size ratio via NASS QuickStats) alongside explicit human-judgment Part VI slots.
     - Include reference to `planning/RESEARCH_ARCGIS_TOOLBOX_CROSSWALK.md`.
- **Constraints / Do Not Touch**:
  - Do not alter Python source files in `src/`.
  - Do not remove existing Phase 0, 1, or 2 completed deliverables.
- **Grep Anchors / References**:
  - `planning/MASTER_PLAN.md` -> `### Phase 3: Multi-County Corridor Analysis`
  - `planning/MASTER_PLAN.md` -> `### Phase 4: Preliminary Land Evaluation`
  - `planning/RESEARCH_ARCGIS_TOOLBOX_CROSSWALK.md` Sections 2, 3, and 5.
- **Acceptance & Targeted Test Command**:
  - `git diff planning/MASTER_PLAN.md` contains updated Phase 3 and Phase 4 sections.

---

### Task 6.2.1: Enhance Master Plan Phase 5 & Phase 6 Specifications
- **ID**: `6.2.1`
- **Repo**: `.`
- **Files in Scope**:
  - *Must edit*: `planning/MASTER_PLAN.md`
  - *Must create*: `planning/tasks/6.2.1.todo.md`
  - *May edit for report only*: `planning/STATE_6.md`
- **Depends on**: `6.1.1`
- **Spec Prose**:
  1. In `planning/MASTER_PLAN.md`, expand **Phase 5: Project Alternatives & Draft Form Generation**:
     - Detail multi-alternative slot mapping for Site and Corridor Alternatives B, C, and D.
     - Specify watermarked draft Form AD-1006 (parcels) and Form NRCS-CPA-106 (corridors) generation using canonical placeholder tags matching the Colorado Toolbox (`{Project Name}`, `{Direct Relative Rating Value}`, etc.).
     - Specify automated FPPA clearance and determination letter generation (`Letter_Template.docx` equivalent) mapping statutory exemption reasons to standard NRCS statements.
  2. Expand **Phase 6: Case Archival & CPA-2 Annual Reporting**:
     - Structure SQLite case schema to track all 19 CPA-2 row indicators ($A$ through $H$) across the 22 standard Federal action agencies.
     - Detail automated annual aggregation generating Form NRCS-CPA-2 Excel workbooks with full drill-down traceability back to case UUIDs.
- **Constraints / Do Not Touch**:
  - Do not alter Python source files in `src/`.
- **Grep Anchors / References**:
  - `planning/MASTER_PLAN.md` -> `### Phase 5: Project Alternatives`
  - `planning/MASTER_PLAN.md` -> `### Phase 6: Case Archival`
  - `planning/RESEARCH_ARCGIS_TOOLBOX_CROSSWALK.md` Sections 2, 6, and 7.
- **Acceptance & Targeted Test Command**:
  - `git diff planning/MASTER_PLAN.md` contains updated Phase 5 and Phase 6 sections.

---

### Task 6.3.1: Update Master Plan Architecture & Tool Surface
- **ID**: `6.3.1`
- **Repo**: `.`
- **Files in Scope**:
  - *Must edit*: `planning/MASTER_PLAN.md`
  - *Must create*: `planning/tasks/6.3.1.todo.md`
  - *May edit for report only*: `planning/STATE_6.md`
- **Depends on**: `6.2.1`
- **Spec Prose**:
  1. In `planning/MASTER_PLAN.md`, update Section 1 (Problem and Goals) and Section 2 (System Architecture):
     - Incorporate the architectural paradigm shift from desktop GIS (`arcpy`, manual CSVs, local GDBs) to headless, cloud-native on-demand federal REST APIs.
     - Update Mermaid architecture diagram to include the live NASS QuickStats client and Census TIGERweb client.
     - Update roadmap summary table and tool surface inventory to include `analyze_corridor_fppa`, `calculate_preliminary_lesa`, `compare_alternatives`, `generate_draft_form`, and `generate_cpa2_report`.
- **Constraints / Do Not Touch**:
  - Do not modify non-goals or regulatory authority boundaries.
- **Grep Anchors / References**:
  - `planning/MASTER_PLAN.md` -> `## 2. System Architecture`
  - `planning/RESEARCH_ARCGIS_TOOLBOX_CROSSWALK.md` Section 1 and Section 5.
- **Acceptance & Targeted Test Command**:
  - `git diff planning/MASTER_PLAN.md` shows updated system diagrams and tool tables.

---

### Task 6.3.2: Synchronize Planning Artifacts & Verification
- **ID**: `6.3.2`
- **Repo**: `.`
- **Files in Scope**:
  - *Must edit*: `planning/PROMPT_TEMPLATE_6.md`, `planning/STATE_6.md`
  - *Must create*: `planning/tasks/6.3.2.todo.md`
- **Depends on**: `6.2.1`
- **Spec Prose**:
  1. Finalize `planning/PROMPT_TEMPLATE_6.md` and `planning/STATE_6.md` ensuring all tasks (`6.1.1`, `6.2.1`, `6.3.1`, `6.3.2`) are correctly indexed with dependencies, verification commands, and task report scaffolds.
  2. Verify markdown formatting across all planning documents.
- **Constraints / Do Not Touch**:
  - Do not edit prior execution plans (`EXECUTION_PLAN_1..5.md`).
- **Grep Anchors / References**:
  - `planning/STATE_6.md`
  - `planning/PROMPT_TEMPLATE_6.md`
- **Acceptance & Targeted Test Command**:
  - All tasks in `STATE_6.md` accurately reflect `EXECUTION_PLAN_6.md`.
