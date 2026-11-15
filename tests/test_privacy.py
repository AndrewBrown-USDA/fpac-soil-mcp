"""Unit tests for public-only privacy policy and payload sanitization."""

import pytest

from fpac_soil_mcp.core.privacy import (
    ProhibitedPersonalDataError,
    SanitizationResult,
    assert_public_payload,
    sanitize_public_payload,
    validate_public_payload,
)


@pytest.fixture
def clean_public_payload() -> dict:
    return {
        "case_id": "CASE-101",
        "project_name": "Rural Broadband Deployment",
        "agency": {
            "agency_code": "USDA-RD",
            "agency_name": "USDA Rural Development",
            "state": "CO",
            "county": "Weld",
            "office_identifier": "CO-RD-04",
        },
        "impact_areas": [
            {
                "impact_id": "IMP-1",
                "impact_type": "direct",
                "geometry_hash": "sha256:abc12345",
                "acreage": 22.4,
            }
        ],
    }


@pytest.fixture
def dirty_payload_with_pii() -> dict:
    return {
        "case_id": "CASE-102",
        "project_name": "County Highway Realignment",
        "agency": {
            "agency_code": "FHWA",
            "agency_name": "Federal Highway Administration",
            "contact_name": "John Doe",  # Prohibited
            "email": "john.doe@state.gov",  # Prohibited
            "phone_number": "555-123-4567",  # Prohibited
        },
        "landowners": [
            {
                "owner_name": "Jane Smith",  # Prohibited
                "street_address": "123 Farm Lane",  # Prohibited
                "parcel_acres": 80.0,
            }
        ],
    }


def test_validate_clean_payload(clean_public_payload):
    violations = validate_public_payload(clean_public_payload)
    assert violations == []
    # Assert should not raise
    assert_public_payload(clean_public_payload)


def test_validate_dirty_payload(dirty_payload_with_pii):
    violations = validate_public_payload(dirty_payload_with_pii)
    assert len(violations) == 5
    assert "agency.contact_name" in violations
    assert "agency.email" in violations
    assert "agency.phone_number" in violations
    assert "landowners[0].owner_name" in violations
    assert "landowners[0].street_address" in violations

    with pytest.raises(ProhibitedPersonalDataError) as exc_info:
        assert_public_payload(dirty_payload_with_pii)
    # Ensure error message lists field paths but not sensitive values
    err_msg = str(exc_info.value)
    assert "agency.contact_name" in err_msg
    assert "John Doe" not in err_msg
    assert "555-123-4567" not in err_msg


def test_sanitize_payload_does_not_mutate(dirty_payload_with_pii):
    # Verify input retains its fields
    res = sanitize_public_payload(dirty_payload_with_pii)
    assert isinstance(res, SanitizationResult)
    assert len(res.removed_field_paths) == 5

    # Original payload still contains dirty fields
    assert "email" in dirty_payload_with_pii["agency"]
    assert "contact_name" in dirty_payload_with_pii["agency"]

    # Sanitized payload does not
    assert "email" not in res.sanitized_payload["agency"]
    assert "contact_name" not in res.sanitized_payload["agency"]
    assert "phone_number" not in res.sanitized_payload["agency"]
    assert "owner_name" not in res.sanitized_payload["landowners"][0]
    assert "street_address" not in res.sanitized_payload["landowners"][0]

    # Permitted public fields are preserved
    assert res.sanitized_payload["project_name"] == "County Highway Realignment"
    assert res.sanitized_payload["agency"]["agency_code"] == "FHWA"
    assert res.sanitized_payload["landowners"][0]["parcel_acres"] == 80.0

    # Sanitized payload passes assert_public_payload
    assert_public_payload(res.sanitized_payload)


def test_invalid_payload_type():
    with pytest.raises(TypeError, match="must be a dictionary"):
        validate_public_payload("not a dict")  # type: ignore

    with pytest.raises(TypeError, match="must be a dictionary"):
        sanitize_public_payload(["not a dict"])  # type: ignore
