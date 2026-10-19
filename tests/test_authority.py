"""Unit tests for authority, provenance, and attestation primitives."""

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


@pytest.fixture
def valid_utc_now() -> datetime:
    return datetime.now(UTC)


@pytest.fixture
def valid_provenance(valid_utc_now) -> Provenance:
    return Provenance(
        source_name="USDA NRCS Soil Data Access",
        source_reference="mukey:123456",
        timestamp_utc=valid_utc_now,
        method_version="sda_screening_v1",
        configuration_version="default_v1",
    )


@pytest.fixture
def valid_agency_attestation(valid_utc_now) -> Attestation:
    return Attestation(
        actor="Jane Doe, USDA Rural Development",
        actor_category=ActorCategory.AGENCY_OFFICIAL,
        timestamp_utc=valid_utc_now,
        source_reference="Form AD-1006 Part VI signature",
        rationale="Corridor alternative selected meets agency criteria",
    )


@pytest.fixture
def valid_nrcs_attestation(valid_utc_now) -> Attestation:
    return Attestation(
        actor="John Smith, NRCS State Soil Scientist",
        actor_category=ActorCategory.NRCS_OFFICIAL,
        timestamp_utc=valid_utc_now,
        source_reference="NRCS-CPA-106 Part III determination",
        rationale="Site review confirms prime farmland acreage",
    )


def test_provenance_validation(valid_utc_now):
    prov = Provenance(
        source_name="Census TIGERweb",
        source_reference="layer:Urban Areas 2020",
        timestamp_utc=valid_utc_now,
        method_version="urban_screening_v1",
        configuration_version="tigerweb_2020",
    )
    assert prov.source_name == "Census TIGERweb"
    assert prov.timestamp_utc == valid_utc_now

    # Naive timestamp rejection
    with pytest.raises(ValidationError, match="timezone-aware"):
        Provenance(
            source_name="Census TIGERweb",
            source_reference="layer:Urban Areas 2020",
            timestamp_utc=datetime.now().replace(tzinfo=None),  # naive
            method_version="urban_screening_v1",
            configuration_version="tigerweb_2020",
        )

    # Empty/whitespace string rejection
    with pytest.raises(ValidationError, match="non-empty string"):
        Provenance(
            source_name="   ",
            source_reference="layer:Urban Areas 2020",
            timestamp_utc=valid_utc_now,
            method_version="urban_screening_v1",
            configuration_version="tigerweb_2020",
        )


def test_attestation_validation(valid_utc_now):
    att = Attestation(
        actor="Analyst Alex",
        actor_category=ActorCategory.ANALYST,
        timestamp_utc=valid_utc_now,
        source_reference="Internal case notes v2",
        rationale="Preliminary acreage calculation",
    )
    assert att.actor == "Analyst Alex"
    assert att.actor_category == ActorCategory.ANALYST

    # Missing/blank field
    with pytest.raises(ValidationError, match="non-empty string"):
        Attestation(
            actor="Analyst Alex",
            actor_category=ActorCategory.ANALYST,
            timestamp_utc=valid_utc_now,
            source_reference="",
            rationale="Preliminary acreage calculation",
        )


def test_machine_estimate_creation(valid_provenance):
    val = AuthorityValue.machine_estimate(142.5, provenance=valid_provenance)
    assert val.value == 142.5
    assert val.authority == ValueAuthority.MACHINE_ESTIMATE
    assert val.provenance == valid_provenance
    assert val.attestation is None

    # Can construct directly
    val2 = AuthorityValue(
        value=142.5,
        authority=ValueAuthority.MACHINE_ESTIMATE,
        provenance=valid_provenance,
    )
    assert val2.authority == ValueAuthority.MACHINE_ESTIMATE


def test_analyst_proposed_creation(valid_provenance, valid_utc_now):
    val = AuthorityValue.analyst_proposed("Claim A", provenance=valid_provenance)
    assert val.value == "Claim A"
    assert val.authority == ValueAuthority.ANALYST_PROPOSED
    assert val.attestation is None

    # Analyst proposal with valid analyst attestation
    att = Attestation(
        actor="Analyst Alex",
        actor_category=ActorCategory.ANALYST,
        timestamp_utc=valid_utc_now,
        source_reference="Site inspection notes",
        rationale="Acreage measured from CAD drawings",
    )
    val_with_att = AuthorityValue.analyst_proposed("Claim A", attestation=att)
    assert val_with_att.attestation == att

    # Analyst proposal cannot be attested by NRCS official
    nrcs_att = Attestation(
        actor="John Smith",
        actor_category=ActorCategory.NRCS_OFFICIAL,
        timestamp_utc=valid_utc_now,
        source_reference="Formal review",
        rationale="Official review",
    )
    with pytest.raises(ValueError, match="actor_category 'analyst'"):
        AuthorityValue.analyst_proposed("Claim A", attestation=nrcs_att)


def test_approved_and_official_require_attestation(valid_provenance):
    # Direct creation without attestation must fail
    with pytest.raises(ValidationError, match="requires a complete Attestation"):
        AuthorityValue(
            value=100.0,
            authority=ValueAuthority.AGENCY_APPROVED,
        )

    with pytest.raises(ValidationError, match="requires a complete Attestation"):
        AuthorityValue(
            value=100.0,
            authority=ValueAuthority.NRCS_OFFICIAL,
        )


def test_approved_and_official_actor_mismatch(valid_agency_attestation, valid_nrcs_attestation):
    # Agency approval with NRCS official attestation must fail
    with pytest.raises(ValidationError, match="requires actor_category in \\[agency_official\\]"):
        AuthorityValue(
            value=100.0,
            authority=ValueAuthority.AGENCY_APPROVED,
            attestation=valid_nrcs_attestation,
        )

    # NRCS official with Agency official attestation must fail
    with pytest.raises(ValidationError, match="requires actor_category in \\[nrcs_official\\]"):
        AuthorityValue(
            value=100.0,
            authority=ValueAuthority.NRCS_OFFICIAL,
            attestation=valid_agency_attestation,
        )


def test_attested_constructors(valid_agency_attestation, valid_nrcs_attestation, valid_provenance):
    approved = AuthorityValue.agency_approved(
        value=50.0,
        attestation=valid_agency_attestation,
        provenance=valid_provenance,
    )
    assert approved.value == 50.0
    assert approved.authority == ValueAuthority.AGENCY_APPROVED
    assert approved.attestation == valid_agency_attestation
    assert approved.provenance == valid_provenance

    official = AuthorityValue.nrcs_official(
        value=75.0,
        attestation=valid_nrcs_attestation,
        provenance=valid_provenance,
    )
    assert official.value == 75.0
    assert official.authority == ValueAuthority.NRCS_OFFICIAL
    assert official.attestation == valid_nrcs_attestation


def test_create_attested_rejects_unprivileged(valid_agency_attestation):
    with pytest.raises(ValueError, match="create_attested\\(\\) is for privileged states"):
        AuthorityValue.create_attested(
            value=10.0,
            authority=ValueAuthority.MACHINE_ESTIMATE,
            attestation=valid_agency_attestation,
        )


def test_json_serialization_roundtrip(valid_nrcs_attestation, valid_provenance):
    val = AuthorityValue.nrcs_official(
        value=180.5,
        attestation=valid_nrcs_attestation,
        provenance=valid_provenance,
    )
    json_str = val.model_dump_json()
    reconstructed = AuthorityValue[float].model_validate_json(json_str)

    assert reconstructed.value == val.value
    assert reconstructed.authority == val.authority
    assert reconstructed.attestation == val.attestation
    assert reconstructed.provenance == val.provenance
