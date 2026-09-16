# EXECUTION PLAN 2: Research-Informed Roadmap Amendments

## Goal & Scope

### Goal
Amend `planning/MASTER_PLAN.md` so each roadmap phase accounts for the authoritative public API and SDA interpretation deliverables identified in `planning/RESEARCH_PUBLIC_APIS_AND_INTERPRETATIONS.md`, with mechanically checkable exit criteria and concise references back to the research document instead of duplicated implementation detail.

### In Scope
- Add a roadmap-level reference explaining that integration details, query patterns, source endpoints, and automation feasibility live in `planning/RESEARCH_PUBLIC_APIS_AND_INTERPRETATIONS.md`.
- Amend Phases 1, 2, 3, 4, 5, and 7 with the relevant research-derived deliverables.
- Add or strengthen exit criteria for each affected phase, including failure behavior, provenance, fixtures, and benchmark expectations.
- Preserve Phase 6 unless a minimal cross-phase dependency clarification is required.
- Keep the master plan strategic and implementation-neutral; do not copy SQL, endpoint parameter lists, or API response examples from the research document.

### Out of Scope
- Editing the research report.
- Implementing clients, models, tools, tests, or runtime behavior.
- Changing the phase sequence.
- Rewriting unrelated roadmap, ownership, or definition-of-done content.

---

## Wave Dependency Graph & Table

| Wave | Task ID | Title | Repo | Files in Scope | Depends On |
| --- | --- | --- | --- | --- | --- |
| **Wave 1** | `2.1.1` | Amend Master Plan from Public API Research | `.` | `planning/MASTER_PLAN.md`, `planning/tasks/2.1.1.todo.md`, `planning/STATE_2.md` | None |

---

## Task Specifications

### Wave 1

#### Task 2.1.1: Amend Master Plan from Public API Research
- **ID**: `2.1.1`
- **Repo**: `.`
- **Files in Scope**:
  - *Must edit*: `planning/MASTER_PLAN.md`, `planning/STATE_2.md`
  - *Must create*: `planning/tasks/2.1.1.todo.md`
  - *Temp/scratch*: `.development/`
- **Depends on**: None
- **Spec Prose**: Review the phase roadmap in `planning/MASTER_PLAN.md` against the architectural findings and exact breadcrumbs in `planning/RESEARCH_PUBLIC_APIS_AND_INTERPRETATIONS.md`. Amend Phases 1, 2, 3, 4, 5, and 7 so they explicitly account for the NASS county agricultural profile, Census TIGERweb urban-area screening, SDA soil interpretations/NCCPI, their provenance and configuration, their role in corridor and LE-SA workflows, generated review-package evidence, and offline evaluation fixtures. Every affected phase must have concrete deliverables and exit criteria. Reference the research report by path for technical specifics rather than repeating endpoints, SQL, detailed parameters, or long regulatory explanations. Preserve the preliminary-screening and human-authority boundaries. Correct only tightly coupled wording defects encountered in the amended phase sections.
- **Grep Anchors**:
  - `## 3. Phased Delivery Roadmap`
  - `### Phase 1: Domain, Governance & Case State Model`
  - `### Phase 2: Polygon AOI Screening & Farmland Analysis`
  - `### Phase 3: Multi-County Corridor Analysis (CPA-106)`
  - `### Phase 4: Preliminary Land Evaluation & Site Assessment Workbench`
  - `### Phase 5: Project Alternatives & Draft Form Generation`
  - `### Phase 7: Hardening, Evaluation Corpus & Hackathon Submission`
  - Research report: `## 6. Exact Breadcrumbs & Updates for planning/MASTER_PLAN.md`
- **Acceptance & Targeted Checks**:
  - Each affected phase contains at least one research-derived deliverable and one corresponding measurable exit criterion.
  - `planning/MASTER_PLAN.md` directly references `planning/RESEARCH_PUBLIC_APIS_AND_INTERPRETATIONS.md`.
  - The master plan does not duplicate SQL templates, endpoint URLs, or detailed API parameter matrices from the research report.
  - Run `git diff --check -- planning/MASTER_PLAN.md planning/STATE_2.md planning/tasks/2.1.1.todo.md`.

