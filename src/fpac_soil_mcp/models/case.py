"""FPPA case management domain models.

Defines Pydantic models for AgencyProfile, FppaRequest, ImpactArea, ExemptionClaim,
CalculationRun, DecisionRecord, and aggregate FppaCase.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from fpac_soil_mcp.core.authority import (
    AuthorityValue,
    _validate_non_empty_str,
    _validate_tz_aware_datetime,
)


class ImpactType(str, Enum):
    """Classification of impact area."""

    DIRECT = "direct"
    INDIRECT = "indirect"
    ALTERNATIVE = "alternative"
    EXCLUDED = "excluded"


class GeometryKind(str, Enum):
    """Classification of geometry representation format."""

    GEOJSON = "geojson"
    WKT = "wkt"
    POINT = "point"
    BOUNDING_BOX = "bounding_box"
    CORRIDOR_CENTERLINE = "corridor_centerline"
    POLYGON = "polygon"


class GeometryReference(BaseModel):
    """Reference to project geometry without performing spatial computations."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: GeometryKind = Field(description="Format or type of geometry")
    geometry_hash: str = Field(description="Deterministic hash of geometry coordinates")
    source_reference: str | None = Field(
        default=None, description="Optional URL, layer, or external geometry reference"
    )

    @field_validator("geometry_hash")
    @classmethod
    def _validate_hash(cls, v: str) -> str:
        return _validate_non_empty_str(v, "geometry_hash")


class ImpactArea(BaseModel):
    """Distinct impact footprint or corridor segment for an FPPA case."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    impact_id: str = Field(description="Unique identifier for this impact area within the case")
    impact_type: ImpactType = Field(description="Direct, indirect, alternative, or excluded impact")
    geometry: GeometryReference = Field(description="Geometry metadata and hash reference")
    acreage: float | None = Field(
        default=None, description="Optional non-negative footprint acreage"
    )
    description: str | None = Field(default=None, description="Optional human-readable description")

    @field_validator("impact_id")
    @classmethod
    def _validate_id(cls, v: str) -> str:
        return _validate_non_empty_str(v, "impact_id")

    @field_validator("acreage")
    @classmethod
    def _validate_acreage(cls, v: float | None) -> float | None:
        if v is not None and v < 0:
            raise ValueError("acreage must be non-negative.")
        return v


class AgencyProfile(BaseModel):
    """Federal, state, or local agency requesting or managing the FPPA review."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    agency_code: str = Field(description="Standard agency code or acronym, e.g. USDA-RD, FHWA, HUD")
    agency_name: str = Field(description="Full legal or administrative agency name")
    program_name: str | None = Field(
        default=None, description="Funding program or project initiative"
    )
    office_identifier: str | None = Field(default=None, description="Regional or field office code")
    state: str = Field(description="Two-letter USPS state code or territorial abbreviation")
    county: str | None = Field(
        default=None, description="County or parish name if jurisdictionally specific"
    )

    @field_validator("agency_code", "agency_name", "state")
    @classmethod
    def _validate_required_strings(cls, v: str, info) -> str:
        return _validate_non_empty_str(v, info.field_name or "field")


class FppaRequest(BaseModel):
    """Core FPPA evaluation request metadata."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    request_id: str = Field(description="Unique request identifier")
    case_id: str = Field(description="Parent case identifier")
    project_name: str = Field(description="Official project title")
    agency_profile: AgencyProfile = Field(description="Requesting agency details")
    submitted_at_utc: datetime = Field(description="Timezone-aware timestamp of request submission")
    project_description: str | None = Field(default=None, description="Public project description")

    @field_validator("request_id", "case_id", "project_name")
    @classmethod
    def _validate_strings(cls, v: str, info) -> str:
        return _validate_non_empty_str(v, info.field_name or "field")

    @field_validator("submitted_at_utc")
    @classmethod
    def _validate_timestamp(cls, v: datetime, info) -> datetime:
        return _validate_tz_aware_datetime(v, info.field_name or "submitted_at_utc")


class ExemptionClaim(BaseModel):
    """Claimed statutory exemption under 7 CFR 658.2 (e.g., existing urban development)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    claim_id: str = Field(description="Unique exemption claim identifier")
    citation: str = Field(description="Statutory or regulatory citation, e.g. '7 CFR 658.2(a)'")
    rationale: str = Field(description="Justification for exemption claim")
    evidence_references: list[str] = Field(
        default_factory=list, description="References to supporting documents or layers"
    )
    status: AuthorityValue[str] = Field(
        description="Governed status of exemption claim (preliminary screening vs human attested determination)"
    )

    @field_validator("claim_id", "citation", "rationale")
    @classmethod
    def _validate_strings(cls, v: str, info) -> str:
        return _validate_non_empty_str(v, info.field_name or "field")


class CalculationStatus(str, Enum):
    """Status of an algorithmic calculation run."""

    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class CalculationRun(BaseModel):
    """Record of an automated or assisted scoring / acreage calculation run."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str = Field(description="Unique calculation run identifier")
    method_version: str = Field(description="Version of calculation algorithm or formula")
    configuration_version: str = Field(description="Version of configuration or parameters applied")
    inputs_reference: str = Field(description="Identifier or hash of calculation inputs")
    status: CalculationStatus = Field(description="Execution status of calculation")
    timestamp_utc: datetime = Field(description="Timezone-aware timestamp of run completion")
    outputs: dict[str, Any] = Field(
        default_factory=dict, description="Calculated results dictionary"
    )
    limitations: list[str] = Field(
        default_factory=list, description="Methodological or data limitations"
    )

    @field_validator("run_id", "method_version", "configuration_version", "inputs_reference")
    @classmethod
    def _validate_strings(cls, v: str, info) -> str:
        return _validate_non_empty_str(v, info.field_name or "field")

    @field_validator("timestamp_utc")
    @classmethod
    def _validate_timestamp(cls, v: datetime, info) -> datetime:
        return _validate_tz_aware_datetime(v, info.field_name or "timestamp_utc")


class DecisionType(str, Enum):
    """Type of decision or evaluation milestone."""

    PRELIMINARY_SCREENING = "preliminary_screening"
    AGENCY_CORRIDOR_SELECTION = "agency_corridor_selection"
    NRCS_LAND_EVALUATION = "nrcs_land_evaluation"
    FINAL_AGENCY_DETERMINATION = "final_agency_determination"


class DecisionRecord(BaseModel):
    """Formal decision or review finding on an FPPA case."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    decision_id: str = Field(description="Unique decision record identifier")
    decision_type: DecisionType = Field(description="Classification of decision")
    authority_value: AuthorityValue[str] = Field(
        description="Governed decision value with required human attestation for approved/official states"
    )
    rationale: str = Field(description="Formal rationale or findings summary")
    timestamp_utc: datetime = Field(description="Timezone-aware timestamp of decision record")
    limitations: list[str] = Field(
        default_factory=list, description="Applicable limitations and disclaimers"
    )

    @field_validator("decision_id", "rationale")
    @classmethod
    def _validate_strings(cls, v: str, info) -> str:
        return _validate_non_empty_str(v, info.field_name or "field")

    @field_validator("timestamp_utc")
    @classmethod
    def _validate_timestamp(cls, v: datetime, info) -> datetime:
        return _validate_tz_aware_datetime(v, info.field_name or "timestamp_utc")


class CaseLifecycleState(str, Enum):
    """Workflow states for an FPPA case."""

    RECEIVED = "received"
    READY_FOR_ANALYSIS = "ready_for_analysis"
    ANALYSIS_COMPLETE = "analysis_complete"
    PENDING_NRCS_REVIEW = "pending_nrcs_review"
    PROVISIONALLY_COMPLETE = "provisionally_complete"
    CLOSED = "closed"


class StateTransitionEvent(BaseModel):
    """Audit log entry of a workflow state transition."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    from_state: CaseLifecycleState = Field(description="Previous state")
    to_state: CaseLifecycleState = Field(description="Target state")
    timestamp_utc: datetime = Field(description="Timezone-aware timestamp of transition")
    actor: str = Field(description="System component or human actor triggering transition")
    rationale: str | None = Field(default=None, description="Optional transition explanation")

    @field_validator("actor")
    @classmethod
    def _validate_actor(cls, v: str) -> str:
        return _validate_non_empty_str(v, "actor")

    @field_validator("timestamp_utc")
    @classmethod
    def _validate_timestamp(cls, v: datetime, info) -> datetime:
        return _validate_tz_aware_datetime(v, info.field_name or "timestamp_utc")


class FppaCase(BaseModel):
    """Aggregate root domain model representing an FPPA case."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    case_id: str = Field(description="Unique case identifier")
    state: CaseLifecycleState = Field(
        default=CaseLifecycleState.RECEIVED, description="Current lifecycle state"
    )
    request: FppaRequest = Field(description="Initial FPPA submission request")
    impact_areas: list[ImpactArea] = Field(
        default_factory=list, description="Configured impact areas and corridors"
    )
    exemption_claims: list[ExemptionClaim] = Field(
        default_factory=list, description="Claimed statutory exemptions"
    )
    calculation_runs: list[CalculationRun] = Field(
        default_factory=list, description="History of calculation runs"
    )
    decision_records: list[DecisionRecord] = Field(
        default_factory=list, description="Recorded decision milestones"
    )
    history: list[StateTransitionEvent] = Field(
        default_factory=list, description="Ordered audit log of state transitions"
    )

    @field_validator("case_id")
    @classmethod
    def _validate_case_id(cls, v: str) -> str:
        return _validate_non_empty_str(v, "case_id")

    @model_validator(mode="after")
    def _validate_case_integrity(self) -> FppaCase:
        # Ensure request.case_id matches parent case_id
        if self.request.case_id != self.case_id:
            raise ValueError(
                f"Request case_id '{self.request.case_id}' does not match case '{self.case_id}'."
            )

        # Check unique impact IDs
        impact_ids = [ia.impact_id for ia in self.impact_areas]
        if len(impact_ids) != len(set(impact_ids)):
            raise ValueError("Duplicate impact_id found in impact_areas.")

        # Check unique claim IDs
        claim_ids = [c.claim_id for c in self.exemption_claims]
        if len(claim_ids) != len(set(claim_ids)):
            raise ValueError("Duplicate claim_id found in exemption_claims.")

        # Check unique calculation run IDs
        run_ids = [r.run_id for r in self.calculation_runs]
        if len(run_ids) != len(set(run_ids)):
            raise ValueError("Duplicate run_id found in calculation_runs.")

        # Check unique decision IDs
        decision_ids = [d.decision_id for d in self.decision_records]
        if len(decision_ids) != len(set(decision_ids)):
            raise ValueError("Duplicate decision_id found in decision_records.")

        return self
