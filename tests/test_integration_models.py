"""Unit tests for public data integration models."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from fpac_soil_mcp.authority import Provenance
from fpac_soil_mcp.integration_models import (
    CountyAgProfile,
    IntegrationStatus,
    SoilInterpretationRecord,
    UrbanExemptionRecord,
)


@pytest.fixture
def valid_utc_now() -> datetime:
    return datetime.now(UTC)


@pytest.fixture
def tigerweb_prov(valid_utc_now) -> Provenance:
    return Provenance(
        source_name="Census TIGERweb 2020",
        source_reference="Layer 6: Urban Areas",
        timestamp_utc=valid_utc_now,
        method_version="tigerweb_rest_v1",
        configuration_version="urban_2020",
    )


@pytest.fixture
def nass_prov(valid_utc_now) -> Provenance:
    return Provenance(
        source_name="USDA NASS Quick Stats",
        source_reference="Census of Agriculture 2022",
        timestamp_utc=valid_utc_now,
        method_version="quickstats_api_v1",
        configuration_version="county_ag_profile_v1",
    )


@pytest.fixture
def sda_prov(valid_utc_now) -> Provenance:
    return Provenance(
        source_name="USDA NRCS Soil Data Access",
        source_reference="SDA Post REST: SDV_Interpretations",
        timestamp_utc=valid_utc_now,
        method_version="nccpi_v3",
        configuration_version="default_wtd_avg",
    )


def test_urban_exemption_record_success(tigerweb_prov):
    rec = UrbanExemptionRecord(
        status=IntegrationStatus.SUCCESS,
        geometry_hash="sha256:abcd1234",
        provenance=tigerweb_prov,
        is_urban_intersected=True,
        urban_area_names=["Ames, IA Urban Area"],
        screened_acreage=5.5,
    )
    assert rec.status == IntegrationStatus.SUCCESS
    assert rec.is_urban_intersected is True
    assert rec.screened_acreage == 5.5
    assert len(rec.limitations) > 0


def test_urban_exemption_record_requires_provenance():
    with pytest.raises(ValidationError, match="provenance"):
        UrbanExemptionRecord(
            status=IntegrationStatus.SUCCESS,
            geometry_hash="sha256:abcd1234",
            is_urban_intersected=False,
        )


def test_urban_exemption_record_error_state(tigerweb_prov):
    rec = UrbanExemptionRecord(
        status=IntegrationStatus.ERROR,
        geometry_hash="sha256:abcd1234",
        provenance=tigerweb_prov,
        error_message="TIGERweb service endpoint timed out after 10s",
    )
    assert rec.status == IntegrationStatus.ERROR
    assert rec.error_message is not None

    # Error without message fails
    with pytest.raises(ValidationError, match="error_message must be provided"):
        UrbanExemptionRecord(
            status=IntegrationStatus.ERROR,
            geometry_hash="sha256:abcd1234",
            provenance=tigerweb_prov,
        )


def test_county_ag_profile_metrics(nass_prov):
    profile = CountyAgProfile(
        status=IntegrationStatus.SUCCESS,
        state_fips="19",
        county_fips="169",
        county_name="Story",
        census_year=2022,
        provenance=nass_prov,
        land_in_farms_acres=330000.0,
        total_cropland_acres=305000.0,
        farm_count=950,
        average_farm_size_acres=347.4,
    )
    assert profile.land_in_farms_acres == 330000.0

    # Negative acreage fails
    with pytest.raises(ValidationError, match="Acreage values must be non-negative"):
        CountyAgProfile(
            status=IntegrationStatus.SUCCESS,
            state_fips="19",
            county_fips="169",
            county_name="Story",
            census_year=2022,
            provenance=nass_prov,
            land_in_farms_acres=-50.0,
        )

    # Invalid year fails
    with pytest.raises(ValidationError, match="outside valid historical range"):
        CountyAgProfile(
            status=IntegrationStatus.SUCCESS,
            state_fips="19",
            county_fips="169",
            county_name="Story",
            census_year=1850,
            provenance=nass_prov,
        )


def test_soil_interpretation_record_validation(sda_prov):
    interp = SoilInterpretationRecord(
        status=IntegrationStatus.SUCCESS,
        mukey="123456",
        rule_name="NCCPI - National Commodity Crop Productivity Index (v3)",
        rule_version="3.0",
        provenance=sda_prov,
        aggregation_method="Weighted Average",
        rating_class="Moderately high productivity",
        numeric_rating=0.78,
        rated_component_pct=95.0,
        total_component_pct=100.0,
        limiting_reasons=["Slope gradient 5-9%"],
    )
    assert interp.numeric_rating == 0.78

    # Rating out of [0.0, 1.0] range fails
    with pytest.raises(ValidationError, match="must be between 0.0 and 1.0"):
        SoilInterpretationRecord(
            status=IntegrationStatus.SUCCESS,
            mukey="123456",
            rule_name="NCCPI",
            rule_version="3.0",
            provenance=sda_prov,
            numeric_rating=1.5,
        )

    # Percentage out of [0, 100] fails
    with pytest.raises(ValidationError, match="must be between 0.0 and 100.0 percent"):
        SoilInterpretationRecord(
            status=IntegrationStatus.SUCCESS,
            mukey="123456",
            rule_name="NCCPI",
            rule_version="3.0",
            provenance=sda_prov,
            numeric_rating=0.8,
            rated_component_pct=105.0,
        )
