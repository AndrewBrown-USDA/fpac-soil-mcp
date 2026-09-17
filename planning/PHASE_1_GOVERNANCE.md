# Phase 1 Domain & Governance Architecture

This document records the internal domain, lifecycle, and governance model established in Phase 1 for structured FPPA workflows.

## Scope & Design Invariants

Phase 1 sets up internal domain contracts, governance invariants, public data models, and privacy policies. It does not expose public case-management MCP tools, persistent databases, or automated official determinations.

### Core Modules & Responsibilities

1. **Authority & Provenance Primitives (`src/fpac_soil_mcp/authority.py`)**:
   - `ValueAuthority` classifies values as `machine_estimate`, `analyst_proposed`, `agency_approved`, or `nrcs_official`.
   - Automated evaluation paths only produce `machine_estimate` or `analyst_proposed`.
   - `agency_approved` and `nrcs_official` values require an `Attestation` record with an appropriate `ActorCategory` (`agency_official` or `nrcs_official`).
   - `Provenance` records source names, references, timestamps, and algorithm versions.

2. **FPPA Case Domain Models (`src/fpac_soil_mcp/case_models.py`)**:
   - Pydantic models: `AgencyProfile`, `FppaRequest`, `ImpactArea`, `ExemptionClaim`, `CalculationRun`, and `DecisionRecord`.
   - Aggregate root `FppaCase` tracks structured case assets, lifecycle state, and immutable transition history.

3. **Public Integration Records (`src/fpac_soil_mcp/integration_models.py`)**:
   - Provenance models for public datasets: `UrbanExemptionRecord` (Census TIGERweb Layer 6), `CountyAgProfile` (USDA NASS Quick Stats), and `SoilInterpretationRecord` (USDA NRCS SDA NCCPI / interpretations).
   - Urban screening remains strictly preliminary under 7 CFR § 658.2(a) and does not constitute a granted legal exemption.

4. **Public Privacy Policy (`src/fpac_soil_mcp/privacy.py`)**:
   - Rejects sensitive personal data (personal names, personal emails, phone numbers, SSNs, street addresses).
   - `sanitize_public_payload()` reports removed field paths while preserving permitted public and project fields.

5. **Official Source Registry (`src/fpac_soil_mcp/official_sources.py`)**:
   - Package-owned JSON registries (`data/official_sources.v1.json`, `data/regional_scoring.v1.json`) catalog citations, form editions (AD-1006, CPA-106), regulations (7 CFR 657, 7 CFR 658), and endpoints.
   - Regional scoring configurations validate jurisdiction and approval authority.

6. **Workflow State Machine (`src/fpac_soil_mcp/workflow.py`)**:
   - State transitions: `received` -> `ready_for_analysis` -> `analysis_complete` -> `pending_nrcs_review` -> `provisionally_complete` -> `closed`.
   - Enforces transition guards (privacy checks, completed calculations, decision records, closure rationale) with immutable state transitions.
