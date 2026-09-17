"""Unit tests for FPPA workflow state machine."""

from datetime import UTC, datetime

import pytest

from fpac_soil_mcp.authority import (
    AuthorityValue,
    Provenance,
)
from fpac_soil_mcp.case_models import (
    AgencyProfile,
    CalculationRun,
    CalculationStatus,
    CaseLifecycleState,
    DecisionRecord,
    DecisionType,
    FppaCase,
    FppaRequest,
    GeometryKind,
    GeometryReference,
    ImpactArea,
    ImpactType,
)
from fpac_soil_mcp.workflow import (
    WorkflowTransitionError,
    transition_case,
)


@pytest.fixture
def valid_utc_now() -> datetime:
    return datetime.now(UTC)


@pytest.fixture
def base_case(valid_utc_now) -> FppaCase:
    agency = AgencyProfile(
        agency_code="USDA-RD",
        agency_name="USDA Rural Development",
        state="IA",
        county="Story",
    )
    request = FppaRequest(
        request_id="REQ-100",
        case_id="CASE-100",
        project_name="Story County Water System",
        agency_profile=agency,
        submitted_at_utc=valid_utc_now,
    )
    return FppaCase(
        case_id="CASE-100",
        state=CaseLifecycleState.RECEIVED,
        request=request,
    )


@pytest.fixture
def sample_impact_area() -> ImpactArea:
    return ImpactArea(
        impact_id="IMP-001",
        impact_type=ImpactType.DIRECT,
        geometry=GeometryReference(
            kind=GeometryKind.POLYGON,
            geometry_hash="sha256:11223344",
        ),
        acreage=25.0,
    )


@pytest.fixture
def sample_calc_run(valid_utc_now) -> CalculationRun:
    return CalculationRun(
        run_id="CALC-001",
        method_version="nccpi_v3",
        configuration_version="default_wtd_avg",
        inputs_reference="hash:inputs",
        status=CalculationStatus.COMPLETED,
        timestamp_utc=valid_utc_now,
        outputs={"score": 85.0},
    )


@pytest.fixture
def sample_decision(valid_utc_now) -> DecisionRecord:
    prov = Provenance(
        source_name="USDA NRCS SDA",
        source_reference="mukey:12345",
        timestamp_utc=valid_utc_now,
        method_version="screening_v1",
        configuration_version="default_v1",
    )
    return DecisionRecord(
        decision_id="DEC-001",
        decision_type=DecisionType.PRELIMINARY_SCREENING,
        authority_value=AuthorityValue.machine_estimate("preliminary_complete", provenance=prov),
        rationale="Automated preliminary soil screening completed",
        timestamp_utc=valid_utc_now,
    )


def test_full_lifecycle_progression(
    base_case, sample_impact_area, sample_calc_run, sample_decision, valid_utc_now
):
    # 1. RECEIVED -> READY_FOR_ANALYSIS
    case1 = transition_case(
        case=base_case,
        to_state=CaseLifecycleState.READY_FOR_ANALYSIS,
        actor="system:ingestion",
        timestamp_utc=valid_utc_now,
        rationale="Public policy checks passed",
    )
    assert case1.state == CaseLifecycleState.READY_FOR_ANALYSIS
    assert len(case1.history) == 1
    assert base_case.state == CaseLifecycleState.RECEIVED  # Input unchanged

    # Add required analysis assets
    case1_with_assets = case1.model_copy(
        update={
            "impact_areas": [sample_impact_area],
            "calculation_runs": [sample_calc_run],
        }
    )

    # 2. READY_FOR_ANALYSIS -> ANALYSIS_COMPLETE
    case2 = transition_case(
        case=case1_with_assets,
        to_state=CaseLifecycleState.ANALYSIS_COMPLETE,
        actor="analyst:jsmith",
        timestamp_utc=valid_utc_now,
        rationale="Calculations completed",
    )
    assert case2.state == CaseLifecycleState.ANALYSIS_COMPLETE
    assert len(case2.history) == 2

    # 3. ANALYSIS_COMPLETE -> PENDING_NRCS_REVIEW
    case3 = transition_case(
        case=case2,
        to_state=CaseLifecycleState.PENDING_NRCS_REVIEW,
        actor="analyst:jsmith",
        timestamp_utc=valid_utc_now,
        rationale="Transmitted to NRCS state office",
    )
    assert case3.state == CaseLifecycleState.PENDING_NRCS_REVIEW
    assert len(case3.history) == 3

    # Add decision milestone
    case3_with_decision = case3.model_copy(update={"decision_records": [sample_decision]})

    # 4. PENDING_NRCS_REVIEW -> PROVISIONALLY_COMPLETE
    case4 = transition_case(
        case=case3_with_decision,
        to_state=CaseLifecycleState.PROVISIONALLY_COMPLETE,
        actor="nrcs:official",
        timestamp_utc=valid_utc_now,
        rationale="NRCS review received",
    )
    assert case4.state == CaseLifecycleState.PROVISIONALLY_COMPLETE
    assert len(case4.history) == 4

    # 5. PROVISIONALLY_COMPLETE -> CLOSED
    case5 = transition_case(
        case=case4,
        to_state=CaseLifecycleState.CLOSED,
        actor="agency:official",
        timestamp_utc=valid_utc_now,
        rationale="Case closed with formal record of decision",
    )
    assert case5.state == CaseLifecycleState.CLOSED
    assert len(case5.history) == 5


def test_illegal_state_transition_skips(base_case, valid_utc_now):
    # Cannot skip directly from RECEIVED to ANALYSIS_COMPLETE
    with pytest.raises(WorkflowTransitionError, match="Illegal state transition"):
        transition_case(
            case=base_case,
            to_state=CaseLifecycleState.ANALYSIS_COMPLETE,
            actor="tester",
            timestamp_utc=valid_utc_now,
        )

    # Cannot transition backward from CLOSED
    closed_case = base_case.model_copy(update={"state": CaseLifecycleState.CLOSED})
    with pytest.raises(WorkflowTransitionError, match="Illegal state transition"):
        transition_case(
            case=closed_case,
            to_state=CaseLifecycleState.READY_FOR_ANALYSIS,
            actor="tester",
            timestamp_utc=valid_utc_now,
        )


def test_guard_analysis_complete_missing_runs(base_case, sample_impact_area, valid_utc_now):
    ready_case = base_case.model_copy(
        update={
            "state": CaseLifecycleState.READY_FOR_ANALYSIS,
            "impact_areas": [sample_impact_area],
            "calculation_runs": [],  # missing calculation runs
        }
    )
    with pytest.raises(WorkflowTransitionError, match="at least one completed calculation run"):
        transition_case(
            case=ready_case,
            to_state=CaseLifecycleState.ANALYSIS_COMPLETE,
            actor="analyst",
            timestamp_utc=valid_utc_now,
        )


def test_guard_provisionally_complete_missing_decision(
    base_case, sample_impact_area, sample_calc_run, valid_utc_now
):
    analysis_case = base_case.model_copy(
        update={
            "state": CaseLifecycleState.ANALYSIS_COMPLETE,
            "impact_areas": [sample_impact_area],
            "calculation_runs": [sample_calc_run],
            "decision_records": [],  # missing decision
        }
    )
    with pytest.raises(WorkflowTransitionError, match="at least one recorded decision milestone"):
        transition_case(
            case=analysis_case,
            to_state=CaseLifecycleState.PROVISIONALLY_COMPLETE,
            actor="analyst",
            timestamp_utc=valid_utc_now,
        )


def test_guard_closed_requires_rationale_and_actor(base_case, sample_decision, valid_utc_now):
    prov_case = base_case.model_copy(
        update={
            "state": CaseLifecycleState.PROVISIONALLY_COMPLETE,
            "decision_records": [sample_decision],
        }
    )
    with pytest.raises(WorkflowTransitionError, match="Closure rationale is mandatory"):
        transition_case(
            case=prov_case,
            to_state=CaseLifecycleState.CLOSED,
            actor="agency:lead",
            timestamp_utc=valid_utc_now,
            rationale="",  # empty rationale
        )
