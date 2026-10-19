"""Unit tests for FPPA case management domain models."""

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
    StateTransitionEvent,
)


@pytest.fixture
def valid_utc_now() -> datetime:
    return datetime.now(UTC)


@pytest.fixture
def sample_agency() -> AgencyProfile:
    return AgencyProfile(
        agency_code="USDA-RD",
        agency_name="USDA Rural Development",
        program_name="Water and Waste Disposal Loan and Grant Program",
        office_identifier="RD-IA-01",
        state="IA",
        county="Story",
    )


@pytest.fixture
def sample_request(sample_agency, valid_utc_now) -> FppaRequest:
    return FppaRequest(
        request_id="REQ-001",
        case_id="CASE-001",
        project_name="Story County Water Main Extension",
        agency_profile=sample_agency,
        submitted_at_utc=valid_utc_now,
        project_description="Construction of 5-mile rural water distribution pipeline",
    )


@pytest.fixture
def sample_impact_area() -> ImpactArea:
    return ImpactArea(
        impact_id="IMP-001",
        impact_type=ImpactType.DIRECT,
        geometry=GeometryReference(
            kind=GeometryKind.CORRIDOR_CENTERLINE,
            geometry_hash="sha256:abc123def456",
            source_reference="gis_layers/corridor_v1.geojson",
        ),
        acreage=14.2,
        description="Main pipeline right-of-way",
    )


def test_agency_profile_validation():
    p = AgencyProfile(
        agency_code="FHWA",
        agency_name="Federal Highway Administration",
        state="NE",
    )
    assert p.agency_code == "FHWA"
    assert p.county is None

    # Empty required string
    with pytest.raises(ValidationError, match="non-empty string"):
        AgencyProfile(
            agency_code="",
            agency_name="Federal Highway Administration",
            state="NE",
        )


def test_impact_area_validation():
    geom = GeometryReference(
        kind=GeometryKind.POLYGON,
        geometry_hash="hash-99",
    )
    area = ImpactArea(
        impact_id="A-1",
        impact_type=ImpactType.DIRECT,
        geometry=geom,
        acreage=0.0,
    )
    assert area.acreage == 0.0

    # Negative acreage rejected
    with pytest.raises(ValidationError, match="non-negative"):
        ImpactArea(
            impact_id="A-1",
            impact_type=ImpactType.DIRECT,
            geometry=geom,
            acreage=-1.5,
        )


def test_fppa_request_validation(sample_agency, valid_utc_now):
    req = FppaRequest(
        request_id="REQ-1",
        case_id="CASE-1",
        project_name="Bridge Replacement",
        agency_profile=sample_agency,
        submitted_at_utc=valid_utc_now,
    )
    assert req.project_name == "Bridge Replacement"

    # Naive timestamp rejected
    with pytest.raises(ValidationError, match="timezone-aware"):
        FppaRequest(
            request_id="REQ-1",
            case_id="CASE-1",
            project_name="Bridge Replacement",
            agency_profile=sample_agency,
            submitted_at_utc=datetime.now().replace(tzinfo=None),
        )


def test_exemption_claim_authority(valid_utc_now):
    prov = Provenance(
        source_name="Census TIGERweb",
        source_reference="Urban Areas 2020",
        timestamp_utc=valid_utc_now,
        method_version="urban_screen_v1",
        configuration_version="default_v1",
    )
    claim = ExemptionClaim(
        claim_id="EX-1",
        citation="7 CFR 658.2(a)",
        rationale="Preliminary screening indicates 100% urban area intersection",
        evidence_references=["tigerweb:urban_areas:2020"],
        status=AuthorityValue.machine_estimate("preliminary_urban_screen", provenance=prov),
    )
    assert claim.status.authority == ValueAuthority.MACHINE_ESTIMATE

    # Attested claim
    att = Attestation(
        actor="Jane Official, USDA-RD",
        actor_category=ActorCategory.AGENCY_OFFICIAL,
        timestamp_utc=valid_utc_now,
        source_reference="Agency Record of Decision 2026-01",
        rationale="Certified existing urban footprint per local zoning documentation",
    )
    official_claim = ExemptionClaim(
        claim_id="EX-2",
        citation="7 CFR 658.2(a)",
        rationale="Existing urban land commitment verified",
        status=AuthorityValue.agency_approved("agency_certified_urban", attestation=att),
    )
    assert official_claim.status.authority == ValueAuthority.AGENCY_APPROVED


def test_calculation_run_validation(valid_utc_now):
    run = CalculationRun(
        run_id="RUN-01",
        method_version="nrcs_nccpi_v3",
        configuration_version="ia_state_weights_2026",
        inputs_reference="hash:inputs_987",
        status=CalculationStatus.COMPLETED,
        timestamp_utc=valid_utc_now,
        outputs={"weighted_nccpi": 78.4, "prime_farmland_acres": 12.1},
        limitations=["Preliminary soil survey data; subject to field verification"],
    )
    assert run.status == CalculationStatus.COMPLETED
    assert run.outputs["weighted_nccpi"] == 78.4


def test_decision_record_attestation(valid_utc_now):
    att = Attestation(
        actor="John Smith, NRCS Soil Scientist",
        actor_category=ActorCategory.NRCS_OFFICIAL,
        timestamp_utc=valid_utc_now,
        source_reference="NRCS-CPA-106 Section IV",
        rationale="LE score of 82 assigned based on county soil survey",
    )
    decision = DecisionRecord(
        decision_id="DEC-01",
        decision_type=DecisionType.NRCS_LAND_EVALUATION,
        authority_value=AuthorityValue.nrcs_official("LE_SCORE:82", attestation=att),
        rationale="Land Evaluation completed per NRCS guidelines",
        timestamp_utc=valid_utc_now,
    )
    assert decision.authority_value.authority == ValueAuthority.NRCS_OFFICIAL


def test_fppa_case_aggregate_integrity(sample_request, sample_impact_area, valid_utc_now):
    case = FppaCase(
        case_id="CASE-001",
        state=CaseLifecycleState.RECEIVED,
        request=sample_request,
        impact_areas=[sample_impact_area],
        history=[
            StateTransitionEvent(
                from_state=CaseLifecycleState.RECEIVED,
                to_state=CaseLifecycleState.READY_FOR_ANALYSIS,
                timestamp_utc=valid_utc_now,
                actor="system:ingestion",
                rationale="Request payload validated against public policy",
            )
        ],
    )
    assert case.case_id == "CASE-001"
    assert len(case.impact_areas) == 1
    assert len(case.history) == 1

    # Inconsistent case_id in request
    bad_request = sample_request.model_copy(update={"case_id": "DIFFERENT-CASE"})
    with pytest.raises(ValidationError, match="does not match case"):
        FppaCase(
            case_id="CASE-001",
            request=bad_request,
        )

    # Duplicate impact IDs
    impact_dup = sample_impact_area.model_copy()
    with pytest.raises(ValidationError, match="Duplicate impact_id"):
        FppaCase(
            case_id="CASE-001",
            request=sample_request,
            impact_areas=[sample_impact_area, impact_dup],
        )


def test_fppa_case_serialization_roundtrip(sample_request, sample_impact_area, valid_utc_now):
    case = FppaCase(
        case_id="CASE-001",
        state=CaseLifecycleState.RECEIVED,
        request=sample_request,
        impact_areas=[sample_impact_area],
    )
    json_str = case.model_dump_json()
    reloaded = FppaCase.model_validate_json(json_str)

    assert reloaded.case_id == case.case_id
    assert reloaded.request.project_name == case.request.project_name
    assert (
        reloaded.impact_areas[0].geometry.geometry_hash == sample_impact_area.geometry.geometry_hash
    )
