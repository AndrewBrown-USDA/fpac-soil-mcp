"""Cross-contract integration tests for Phase 1 domain, governance, and state models.

Verifies end-to-end composition across:
- Authority and provenance primitives
- FPPA case models and lifecycle aggregate
- Public-data integration records
- Public-only privacy policy and sanitization
- Official source registry and regional scoring config loaders
- Capability-scoped configuration settings
- Pure workflow state machine transitions
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from fpac_soil_mcp.authority import (
    ActorCategory,
    Attestation,
    AuthorityValue,
    Provenance,
    ValueAuthority,
)
from fpac_soil_mcp.case_models import (
    AgencyProfile,
    CalculationRun,
    CalculationStatus,
    CaseLifecycleState,
    DecisionRecord,
    DecisionType,
    ExemptionClaim,
    FppaCase,
    FppaRequest,
    GeometryKind,
    GeometryReference,
    ImpactArea,
    ImpactType,
)
from fpac_soil_mcp.config import Settings
from fpac_soil_mcp.integration_models import (
    CountyAgProfile,
    IntegrationStatus,
    SoilInterpretationRecord,
    UrbanExemptionRecord,
)
from fpac_soil_mcp.official_sources import (
    load_official_sources,
    load_regional_scoring_configs,
)
from fpac_soil_mcp.privacy import (
    ProhibitedPersonalDataError,
    assert_public_payload,
    sanitize_public_payload,
    validate_public_payload,
)
from fpac_soil_mcp.workflow import (
    transition_case,
)


@pytest.fixture
def valid_utc_now() -> datetime:
    return datetime.now(UTC)


def test_phase1_complete_composition(valid_utc_now):
    # 1. Official Source Registry verification
    sources = load_official_sources()
    assert "7_CFR_658" in sources
    assert "FORM_AD_1006" in sources
    regional_configs = load_regional_scoring_configs(source_registry=sources)
    assert len(regional_configs) == 0  # No invented regional configs

    # 2. Capability-scoped settings verification
    settings = Settings(_env_file=None)
    assert settings.nass_enabled is False
    with pytest.raises(ValueError, match="requires 'nass_api_key'"):
        settings.validate_nass_capability()

    # 3. Request creation & Privacy enforcement
    raw_incoming_request = {
        "case_id": "CASE-2026-IA-001",
        "project_name": "Rural Water Pipeline Corridor Expansion",
        "agency": {
            "agency_code": "USDA-RD",
            "agency_name": "USDA Rural Development",
            "state": "IA",
            "county": "Story",
            "office_identifier": "RD-IA-01",
            "contact_name": "Prohibited Agent",  # PII
            "email": "agent@rd.usda.gov",  # PII
        },
        "description": "Corridor expansion across 15 miles",
    }

    # Verify assert_public_payload fails on raw request
    violations = validate_public_payload(raw_incoming_request)
    assert "agency.contact_name" in violations
    assert "agency.email" in violations
    with pytest.raises(ProhibitedPersonalDataError):
        assert_public_payload(raw_incoming_request)

    # Sanitize payload
    sanitization = sanitize_public_payload(raw_incoming_request)
    assert len(sanitization.removed_field_paths) == 2
    assert_public_payload(sanitization.sanitized_payload)

    # 4. Construct Case and Request Domain Models
    agency = AgencyProfile(
        agency_code=sanitization.sanitized_payload["agency"]["agency_code"],
        agency_name=sanitization.sanitized_payload["agency"]["agency_name"],
        state=sanitization.sanitized_payload["agency"]["state"],
        county=sanitization.sanitized_payload["agency"]["county"],
        office_identifier=sanitization.sanitized_payload["agency"]["office_identifier"],
    )
    request = FppaRequest(
        request_id="REQ-2026-001",
        case_id="CASE-2026-IA-001",
        project_name=sanitization.sanitized_payload["project_name"],
        agency_profile=agency,
        submitted_at_utc=valid_utc_now,
        project_description=sanitization.sanitized_payload["description"],
    )

    case = FppaCase(
        case_id="CASE-2026-IA-001",
        state=CaseLifecycleState.RECEIVED,
        request=request,
    )

    # 5. Public integration records creation
    tigerweb_prov = Provenance(
        source_name="Census TIGERweb 2020",
        source_reference="Layer 0: Urban Areas",
        timestamp_utc=valid_utc_now,
        method_version="tigerweb_rest_v1",
        configuration_version="urban_2020",
    )
    urban_screen = UrbanExemptionRecord(
        status=IntegrationStatus.SUCCESS,
        geometry_hash="sha256:corridor_hash_9988",
        provenance=tigerweb_prov,
        is_urban_intersected=False,
    )
    assert urban_screen.is_urban_intersected is False

    nass_prov = Provenance(
        source_name="USDA NASS Quick Stats",
        source_reference="Census of Agriculture 2022",
        timestamp_utc=valid_utc_now,
        method_version="quickstats_api_v1",
        configuration_version="county_ag_profile_v1",
    )
    county_profile = CountyAgProfile(
        status=IntegrationStatus.SUCCESS,
        state_fips="19",
        county_fips="169",
        county_name="Story",
        census_year=2022,
        provenance=nass_prov,
        land_in_farms_acres=330000.0,
        total_cropland_acres=305000.0,
    )

    sda_prov = Provenance(
        source_name="USDA NRCS SDA",
        source_reference="SDV_Interpretations:mukey:408013",
        timestamp_utc=valid_utc_now,
        method_version="nccpi_v3",
        configuration_version="wtd_avg",
    )
    interp_record = SoilInterpretationRecord(
        status=IntegrationStatus.SUCCESS,
        mukey="408013",
        rule_name="NCCPI - National Commodity Crop Productivity Index (Ver 3.0)",
        rule_version="3.0",
        provenance=sda_prov,
        numeric_rating=0.82,
        rated_component_pct=100.0,
        total_component_pct=100.0,
    )

    # Attach impact areas and exemption claims
    impact_area = ImpactArea(
        impact_id="IMP-001",
        impact_type=ImpactType.DIRECT,
        geometry=GeometryReference(
            kind=GeometryKind.CORRIDOR_CENTERLINE,
            geometry_hash="sha256:corridor_hash_9988",
        ),
        acreage=42.5,
    )

    claim = ExemptionClaim(
        claim_id="EX-001",
        citation="7 CFR 658.2(a)",
        rationale="Preliminary screening evaluated urban area overlap",
        evidence_references=["tigerweb:urban_2020:layer0"],
        status=AuthorityValue.machine_estimate("preliminary_non_urban", provenance=tigerweb_prov),
    )

    # 6. Workflow Progression: RECEIVED -> READY_FOR_ANALYSIS
    case = transition_case(
        case=case,
        to_state=CaseLifecycleState.READY_FOR_ANALYSIS,
        actor="system:validator",
        timestamp_utc=valid_utc_now,
        rationale="Public policy verified",
    )
    assert case.state == CaseLifecycleState.READY_FOR_ANALYSIS

    # Attach impact areas, claims, and completed calculation run
    calc_run = CalculationRun(
        run_id="CALC-001",
        method_version="nccpi_v3",
        configuration_version="default_wtd_avg",
        inputs_reference="hash:inputs_corridor",
        status=CalculationStatus.COMPLETED,
        timestamp_utc=valid_utc_now,
        outputs={
            "weighted_nccpi": interp_record.numeric_rating,
            "county_cropland_acres": county_profile.total_cropland_acres,
        },
    )

    case = case.model_copy(
        update={
            "impact_areas": [impact_area],
            "exemption_claims": [claim],
            "calculation_runs": [calc_run],
        }
    )

    # 7. Workflow Progression: READY_FOR_ANALYSIS -> ANALYSIS_COMPLETE
    case = transition_case(
        case=case,
        to_state=CaseLifecycleState.ANALYSIS_COMPLETE,
        actor="analyst:researcher",
        timestamp_utc=valid_utc_now,
        rationale="Acreage and NCCPI calculations complete",
    )
    assert case.state == CaseLifecycleState.ANALYSIS_COMPLETE

    # 8. Workflow Progression: ANALYSIS_COMPLETE -> PENDING_NRCS_REVIEW
    case = transition_case(
        case=case,
        to_state=CaseLifecycleState.PENDING_NRCS_REVIEW,
        actor="analyst:researcher",
        timestamp_utc=valid_utc_now,
        rationale="Submitted preliminary package to NRCS Iowa State Office",
    )
    assert case.state == CaseLifecycleState.PENDING_NRCS_REVIEW

    # 9. Authority enforcement: Automated path CANNOT create NRCS official decision without Attestation
    with pytest.raises(ValidationError, match="requires a complete Attestation"):
        AuthorityValue(
            value="LE_SCORE_85",
            authority=ValueAuthority.NRCS_OFFICIAL,
        )

    # Human attested NRCS determination
    nrcs_attestation = Attestation(
        actor="Dr. Sarah Johnson, NRCS Iowa State Soil Scientist",
        actor_category=ActorCategory.NRCS_OFFICIAL,
        timestamp_utc=valid_utc_now,
        source_reference="Form NRCS-CPA-106 Section IV",
        rationale="Certified Land Evaluation score based on official SSURGO ratings",
    )
    nrcs_decision = DecisionRecord(
        decision_id="DEC-NRCS-001",
        decision_type=DecisionType.NRCS_LAND_EVALUATION,
        authority_value=AuthorityValue.nrcs_official("LE_SCORE:85", attestation=nrcs_attestation),
        rationale="LE rating assigned",
        timestamp_utc=valid_utc_now,
    )

    case = case.model_copy(update={"decision_records": [nrcs_decision]})

    # 10. Workflow Progression: PENDING_NRCS_REVIEW -> PROVISIONALLY_COMPLETE
    case = transition_case(
        case=case,
        to_state=CaseLifecycleState.PROVISIONALLY_COMPLETE,
        actor="nrcs:official",
        timestamp_utc=valid_utc_now,
        rationale="Official NRCS Land Evaluation returned",
    )
    assert case.state == CaseLifecycleState.PROVISIONALLY_COMPLETE

    # 11. Workflow Progression: PROVISIONALLY_COMPLETE -> CLOSED
    case = transition_case(
        case=case,
        to_state=CaseLifecycleState.CLOSED,
        actor="Jane Official, USDA-RD Lead",
        timestamp_utc=valid_utc_now,
        rationale="Final Agency Corridor Selection and Record of Decision recorded",
    )
    assert case.state == CaseLifecycleState.CLOSED
    assert len(case.history) == 5

    # 12. Serialization round-trip verification
    serialized_json = case.model_dump_json()
    reconstituted_case = FppaCase.model_validate_json(serialized_json)
    assert reconstituted_case.case_id == case.case_id
    assert reconstituted_case.state == CaseLifecycleState.CLOSED
    assert len(reconstituted_case.decision_records) == 1
    assert (
        reconstituted_case.decision_records[0].authority_value.authority
        == ValueAuthority.NRCS_OFFICIAL
    )
