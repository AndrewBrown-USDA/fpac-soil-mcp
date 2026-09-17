"""Unit tests for configuration settings and capability validation."""

import pytest
from pydantic import ValidationError

from fpac_soil_mcp.config import Settings


def test_default_settings():
    s = Settings()
    assert s.sda_tabular_url.startswith("https://")
    assert s.request_timeout_seconds == 30.0
    assert s.max_retries == 3
    assert s.nass_enabled is False
    assert s.nass_api_key is None
    assert s.tigerweb_urban_layer_id == 6
    assert len(s.sda_interpretation_rules_allowed) > 0


def test_nass_capability_validation():
    # Disabled with no key -> capability check fails when called explicitly
    s = Settings(nass_enabled=False, nass_api_key=None)
    with pytest.raises(ValueError, match="requires 'nass_api_key'"):
        s.validate_nass_capability()

    # Enabled with key -> succeeds
    s_valid = Settings(nass_enabled=True, nass_api_key="TEST_API_KEY_123")
    s_valid.validate_nass_capability()
    assert s_valid.nass_enabled is True

    # Enabled with no key -> fails instantiation
    with pytest.raises(
        ValidationError, match="nass_api_key is required when nass_enabled is set to True"
    ):
        Settings(nass_enabled=True, nass_api_key=None)


def test_invalid_urls():
    with pytest.raises(ValidationError, match="must be a valid HTTP/HTTPS URL"):
        Settings(sda_tabular_url="ftp://invalid.url")

    with pytest.raises(ValidationError, match="must be a valid HTTP/HTTPS URL"):
        Settings(tigerweb_rest_url="not_a_url")


def test_invalid_numeric_settings():
    with pytest.raises(ValidationError, match="Timeout must be a positive number"):
        Settings(request_timeout_seconds=-5.0)

    with pytest.raises(ValidationError, match="max_retries cannot be negative"):
        Settings(max_retries=-1)

    with pytest.raises(ValidationError, match="outside valid range"):
        Settings(nass_census_year=1850)
