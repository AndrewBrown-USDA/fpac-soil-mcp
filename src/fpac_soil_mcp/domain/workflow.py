"""Pure, deterministic FPPA case workflow state machine.

Defines allowable state transitions and guards for FppaCase lifecycle progression:
received -> ready_for_analysis -> analysis_complete -> pending_nrcs_review -> provisionally_complete -> closed
"""

from datetime import datetime

from fpac_soil_mcp.core.authority import _validate_non_empty_str, _validate_tz_aware_datetime
from fpac_soil_mcp.core.errors import DomainError
from fpac_soil_mcp.core.privacy import validate_public_payload
from fpac_soil_mcp.models.case import (
    CalculationStatus,
    CaseLifecycleState,
    FppaCase,
    StateTransitionEvent,
)


class WorkflowTransitionError(DomainError, ValueError):
    """Raised when an invalid or unguarded workflow transition is attempted."""


# Explicit directed graph of allowable transitions: from_state -> set(to_state)
ALLOWED_TRANSITIONS: dict[CaseLifecycleState, set[CaseLifecycleState]] = {
    CaseLifecycleState.RECEIVED: {CaseLifecycleState.READY_FOR_ANALYSIS},
    CaseLifecycleState.READY_FOR_ANALYSIS: {CaseLifecycleState.ANALYSIS_COMPLETE},
    CaseLifecycleState.ANALYSIS_COMPLETE: {
        CaseLifecycleState.PENDING_NRCS_REVIEW,
        CaseLifecycleState.PROVISIONALLY_COMPLETE,
    },
    CaseLifecycleState.PENDING_NRCS_REVIEW: {CaseLifecycleState.PROVISIONALLY_COMPLETE},
    CaseLifecycleState.PROVISIONALLY_COMPLETE: {CaseLifecycleState.CLOSED},
    CaseLifecycleState.CLOSED: set(),  # Terminal state
}


def _guard_ready_for_analysis(case: FppaCase) -> None:
    # Must have valid public-only payload in request
    req_dict = case.request.model_dump()
    violations = validate_public_payload(req_dict)
    if violations:
        raise WorkflowTransitionError(
            f"Cannot transition to 'ready_for_analysis': Request violates public policy at [{', '.join(violations)}]."
        )


def _guard_analysis_complete(case: FppaCase) -> None:
    # Must have at least one impact area
    if not case.impact_areas:
        raise WorkflowTransitionError(
            "Cannot transition to 'analysis_complete': Case must have at least one configured impact area."
        )
    # Must have at least one completed calculation run
    completed_runs = [r for r in case.calculation_runs if r.status == CalculationStatus.COMPLETED]
    if not completed_runs:
        raise WorkflowTransitionError(
            "Cannot transition to 'analysis_complete': Case must have at least one completed calculation run."
        )


def _guard_pending_nrcs_review(case: FppaCase) -> None:
    # Requires an active analysis complete state with impact areas and calculations
    _guard_analysis_complete(case)


def _guard_provisionally_complete(case: FppaCase) -> None:
    # Must have at least one decision record (preliminary screening, LE, or corridor selection)
    if not case.decision_records:
        raise WorkflowTransitionError(
            "Cannot transition to 'provisionally_complete': Case must have at least one recorded decision milestone."
        )


def _guard_closed(case: FppaCase, rationale: str | None, actor: str) -> None:
    if not (rationale and rationale.strip()):
        raise WorkflowTransitionError(
            "Cannot transition to 'closed': Closure rationale is mandatory."
        )
    if not (actor and actor.strip()):
        raise WorkflowTransitionError(
            "Cannot transition to 'closed': A responsible actor must be identified."
        )


def transition_case(
    case: FppaCase,
    to_state: CaseLifecycleState,
    actor: str,
    timestamp_utc: datetime,
    rationale: str | None = None,
) -> FppaCase:
    """Transition an FPPA case to a target state, returning a new immutable FppaCase.

    Enforces transition DAG and guard conditions. Does not mutate the input case.
    """
    if not isinstance(case, FppaCase):
        raise TypeError("case must be an instance of FppaCase.")
    actor_clean = _validate_non_empty_str(actor, "actor")
    ts_clean = _validate_tz_aware_datetime(timestamp_utc, "timestamp_utc")

    from_state = case.state

    # Check DAG
    allowed_targets = ALLOWED_TRANSITIONS.get(from_state, set())
    if to_state not in allowed_targets:
        raise WorkflowTransitionError(
            f"Illegal state transition from '{from_state.value}' to '{to_state.value}'."
        )

    # Evaluate transition guards
    if to_state == CaseLifecycleState.READY_FOR_ANALYSIS:
        _guard_ready_for_analysis(case)
    elif to_state == CaseLifecycleState.ANALYSIS_COMPLETE:
        _guard_analysis_complete(case)
    elif to_state == CaseLifecycleState.PENDING_NRCS_REVIEW:
        _guard_pending_nrcs_review(case)
    elif to_state == CaseLifecycleState.PROVISIONALLY_COMPLETE:
        _guard_provisionally_complete(case)
    elif to_state == CaseLifecycleState.CLOSED:
        _guard_closed(case, rationale, actor_clean)

    # Create transition event
    event = StateTransitionEvent(
        from_state=from_state,
        to_state=to_state,
        timestamp_utc=ts_clean,
        actor=actor_clean,
        rationale=rationale,
    )

    new_history = list(case.history) + [event]

    # Return new instance with updated state and history
    return case.model_copy(
        update={
            "state": to_state,
            "history": new_history,
        }
    )
