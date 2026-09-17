"""Unit tests for official source registry and regional scoring loader."""

import pytest
from pydantic import ValidationError

from fpac_soil_mcp.official_sources import (
    OfficialSourceRecord,
    SourceLifecycleStatus,
    load_official_sources,
    load_regional_scoring_configs,
)


def test_load_official_sources_from_package():
    sources = load_official_sources()
    assert isinstance(sources, dict)
    assert len(sources) >= 7

    assert "7_CFR_657" in sources
    assert "7_CFR_658" in sources
    assert "FORM_AD_1006" in sources
    assert "FORM_NRCS_CPA_106" in sources
    assert "SDA_SERVICE" in sources
    assert "USDA_NASS_QUICKSTATS" in sources
    assert "CENSUS_TIGERWEB_URBAN" in sources

    ad1006 = sources["FORM_AD_1006"]
    assert ad1006.publisher == "USDA NRCS"
    assert ad1006.status == SourceLifecycleStatus.ACTIVE
    assert ad1006.canonical_url.startswith("https://")


def test_load_regional_scoring_configs_empty():
    configs = load_regional_scoring_configs()
    assert isinstance(configs, dict)
    # Empty by design; no invented regional methods
    assert len(configs) == 0


def test_official_source_record_validation():
    rec = OfficialSourceRecord(
        source_id="TEST_SRC",
        schema_version="1.0",
        publisher="Test Agency",
        title="Test Regulation",
        citation="Test 123",
        canonical_url="https://example.gov/test",
        status=SourceLifecycleStatus.ACTIVE,
        retrieval_guidance="Direct URL",
    )
    assert rec.source_id == "TEST_SRC"

    # Invalid URL scheme
    with pytest.raises(ValidationError, match="valid HTTP/HTTPS URL"):
        OfficialSourceRecord(
            source_id="TEST_SRC",
            schema_version="1.0",
            publisher="Test Agency",
            title="Test Regulation",
            citation="Test 123",
            canonical_url="ftp://example.gov/test",
            status=SourceLifecycleStatus.ACTIVE,
            retrieval_guidance="Direct URL",
        )


def test_load_official_sources_missing_file():
    with pytest.raises(FileNotFoundError):
        load_official_sources("data/non_existent.json")
