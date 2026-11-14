"""Authority, provenance, attestation, and governance primitives for FPPA data.

Defines enums and models to ensure that automated paths can produce only
machine estimates or analyst proposals, while agency-approved and NRCS-official
values require explicit, attested human/import records with matching actor categories.
"""

from datetime import datetime
from enum import Enum
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ValueAuthority(str, Enum):
    """Authority classification for a data value or decision."""

    MACHINE_ESTIMATE = "machine_estimate"
    ANALYST_PROPOSED = "analyst_proposed"
    AGENCY_APPROVED = "agency_approved"
    NRCS_OFFICIAL = "nrcs_official"


class ActorCategory(str, Enum):
    """Category of actor creating or attesting to a value or decision."""

    AUTOMATED_SYSTEM = "automated_system"
    ANALYST = "analyst"
    AGENCY_OFFICIAL = "agency_official"
    NRCS_OFFICIAL = "nrcs_official"


def _validate_non_empty_str(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"'{field_name}' must be a non-empty string.")
    return value.strip()


def _validate_tz_aware_datetime(dt: datetime, field_name: str) -> datetime:
    if not isinstance(dt, datetime):
        raise TypeError(f"'{field_name}' must be a valid datetime.")
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        raise ValueError(f"'{field_name}' must be timezone-aware.")
    return dt


class Provenance(BaseModel):
    """Provenance tracking for automated and imported data items."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_name: str = Field(
        description="Authoritative source name, e.g. USDA NRCS SDA or Census TIGERweb"
    )
    source_reference: str = Field(description="Query, layer, endpoint, or document reference")
    timestamp_utc: datetime = Field(
        description="Timezone-aware timestamp when the record was retrieved or generated"
    )
    method_version: str = Field(
        description="Version of the algorithm, query template, or service method"
    )
    configuration_version: str = Field(
        description="Version or identifier of the configuration used"
    )

    @field_validator("source_name", "source_reference", "method_version", "configuration_version")
    @classmethod
    def _validate_strings(cls, v: str, info) -> str:
        return _validate_non_empty_str(v, info.field_name or "field")

    @field_validator("timestamp_utc")
    @classmethod
    def _validate_timestamp(cls, v: datetime, info) -> datetime:
        return _validate_tz_aware_datetime(v, info.field_name or "timestamp_utc")


class Attestation(BaseModel):
    """Human or formal import attestation required for approved and official values."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    actor: str = Field(
        description="Identifier or name of the individual actor or official authority"
    )
    actor_category: ActorCategory = Field(description="Classification of the actor")
    timestamp_utc: datetime = Field(
        description="Timezone-aware timestamp when attestation occurred"
    )
    source_reference: str = Field(
        description="Official document, correspondence, or signature reference"
    )
    rationale: str = Field(
        description="Explanation or justification for approval/official determination"
    )

    @field_validator("actor", "source_reference", "rationale")
    @classmethod
    def _validate_strings(cls, v: str, info) -> str:
        return _validate_non_empty_str(v, info.field_name or "field")

    @field_validator("timestamp_utc")
    @classmethod
    def _validate_timestamp(cls, v: datetime, info) -> datetime:
        return _validate_tz_aware_datetime(v, info.field_name or "timestamp_utc")


T = TypeVar("T")

# Explicit mapping of allowed actor categories for approved/official authority states
_PRIVILEGED_AUTHORITY_ACTOR_MAP: dict[ValueAuthority, set[ActorCategory]] = {
    ValueAuthority.AGENCY_APPROVED: {ActorCategory.AGENCY_OFFICIAL},
    ValueAuthority.NRCS_OFFICIAL: {ActorCategory.NRCS_OFFICIAL},
}

_UNPRIVILEGED_AUTHORITY_ACTOR_MAP: dict[ValueAuthority, set[ActorCategory]] = {
    ValueAuthority.MACHINE_ESTIMATE: {ActorCategory.AUTOMATED_SYSTEM, ActorCategory.ANALYST},
    ValueAuthority.ANALYST_PROPOSED: {ActorCategory.ANALYST},
}


class AuthorityValue(BaseModel, Generic[T]):
    """Generic wrapper for values bearing governance and authority classification."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    value: T = Field(description="The underlying governed value")
    authority: ValueAuthority = Field(description="Authority state of this value")
    provenance: Provenance | None = Field(
        default=None,
        description="Optional provenance metadata for estimates and automated values",
    )
    attestation: Attestation | None = Field(
        default=None,
        description="Mandatory attestation for agency_approved and nrcs_official values",
    )

    @model_validator(mode="after")
    def _validate_authority_and_attestation(self) -> "AuthorityValue[T]":
        if self.authority in (ValueAuthority.AGENCY_APPROVED, ValueAuthority.NRCS_OFFICIAL):
            if self.attestation is None:
                raise ValueError(
                    f"Authority state '{self.authority.value}' requires a complete Attestation."
                )
            allowed_actors = _PRIVILEGED_AUTHORITY_ACTOR_MAP[self.authority]
            if self.attestation.actor_category not in allowed_actors:
                allowed_str = ", ".join(sorted(a.value for a in allowed_actors))
                raise ValueError(
                    f"Authority state '{self.authority.value}' requires actor_category in [{allowed_str}], "
                    f"but got '{self.attestation.actor_category.value}'."
                )
        else:
            if self.attestation is not None:
                # If an attestation is supplied on an analyst/machine value, verify actor category consistency
                allowed_actors = _UNPRIVILEGED_AUTHORITY_ACTOR_MAP.get(self.authority, set())
                if allowed_actors and self.attestation.actor_category not in allowed_actors:
                    allowed_str = ", ".join(sorted(a.value for a in allowed_actors))
                    raise ValueError(
                        f"Authority state '{self.authority.value}' cannot be attested by "
                        f"actor_category '{self.attestation.actor_category.value}' (expected [{allowed_str}])."
                    )
        return self

    @classmethod
    def machine_estimate(
        cls,
        value: T,
        provenance: Provenance | None = None,
    ) -> "AuthorityValue[T]":
        """Construct a machine estimate value."""
        return cls(
            value=value,
            authority=ValueAuthority.MACHINE_ESTIMATE,
            provenance=provenance,
            attestation=None,
        )

    @classmethod
    def analyst_proposed(
        cls,
        value: T,
        provenance: Provenance | None = None,
        attestation: Attestation | None = None,
    ) -> "AuthorityValue[T]":
        """Construct an analyst proposed value."""
        if attestation is not None and attestation.actor_category != ActorCategory.ANALYST:
            raise ValueError(
                f"Analyst proposed value attestation must have actor_category '{ActorCategory.ANALYST.value}'."
            )
        return cls(
            value=value,
            authority=ValueAuthority.ANALYST_PROPOSED,
            provenance=provenance,
            attestation=attestation,
        )

    @classmethod
    def create_attested(
        cls,
        value: T,
        authority: ValueAuthority,
        attestation: Attestation,
        provenance: Provenance | None = None,
    ) -> "AuthorityValue[T]":
        """Construct an attested approved or official value.

        Requires an explicit Attestation with an actor category matching the target authority.
        """
        if authority not in (ValueAuthority.AGENCY_APPROVED, ValueAuthority.NRCS_OFFICIAL):
            raise ValueError(
                f"create_attested() is for privileged states ({ValueAuthority.AGENCY_APPROVED.value}, "
                f"{ValueAuthority.NRCS_OFFICIAL.value}), use machine_estimate() or analyst_proposed() instead."
            )
        return cls(
            value=value,
            authority=authority,
            attestation=attestation,
            provenance=provenance,
        )

    @classmethod
    def agency_approved(
        cls,
        value: T,
        attestation: Attestation,
        provenance: Provenance | None = None,
    ) -> "AuthorityValue[T]":
        """Convenience constructor for agency-approved values."""
        return cls.create_attested(
            value=value,
            authority=ValueAuthority.AGENCY_APPROVED,
            attestation=attestation,
            provenance=provenance,
        )

    @classmethod
    def nrcs_official(
        cls,
        value: T,
        attestation: Attestation,
        provenance: Provenance | None = None,
    ) -> "AuthorityValue[T]":
        """Convenience constructor for NRCS-official values."""
        return cls.create_attested(
            value=value,
            authority=ValueAuthority.NRCS_OFFICIAL,
            attestation=attestation,
            provenance=provenance,
        )
