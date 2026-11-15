from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from fpac_soil_mcp.core.authority import Provenance
from fpac_soil_mcp.models.cdl import (
    CDLAnalysisStatus,
    CDLHistogramBin,
    CDLHistogramResponse,
    CDLServiceMetadata,
)


def _provenance() -> Provenance:
    return Provenance(
        source_name="USDA NASS CDL ImageServer",
        source_reference="https://pdi.scinet.usda.gov/image/rest/services/CDL_WM/ImageServer",
        timestamp_utc=datetime.now(UTC),
        method_version="cdl-histogram-v1",
        configuration_version="default",
    )


def _metadata() -> CDLServiceMetadata:
    return CDLServiceMetadata(
        endpoint="https://pdi.scinet.usda.gov/image/rest/services/CDL_WM/ImageServer",
        capabilities=["Image", "Catalog"],
        retrieved_at_utc=datetime.now(UTC),
        response_hash="a" * 64,
    )


def test_successful_cdl_response_requires_and_preserves_evidence_fields():
    response = CDLHistogramResponse(
        status=CDLAnalysisStatus.SUCCESS,
        geometry_hash="b" * 64,
        histogram=[
            CDLHistogramBin(
                class_value=1,
                pixel_count=80,
                class_name="Corn",
                is_qualifying_agricultural=True,
            )
        ],
        total_pixel_count=100,
        nodata_pixel_count=0,
        coverage_pct=100,
        product_vintage="2025",
        vintage_verified=True,
        coverage_verified=True,
        qualifying_agricultural_pixel_pct=80,
        service_metadata=_metadata(),
        provenance=_provenance(),
    )

    assert response.status is CDLAnalysisStatus.SUCCESS
    assert response.histogram[0].is_qualifying_agricultural is True
    assert response.vintage_verified is True
    assert response.coverage_verified is True
    assert response.limitations[-1].startswith("This result does not constitute")


@pytest.mark.parametrize(
    "status", [CDLAnalysisStatus.INVALID, CDLAnalysisStatus.AMBIGUOUS, CDLAnalysisStatus.ERROR]
)
def test_failure_status_requires_error_message(status):
    with pytest.raises(ValidationError, match="error_message is required"):
        CDLHistogramResponse(status=status, geometry_hash="c" * 64)


def test_success_status_requires_provenance_and_measurement_fields():
    with pytest.raises(ValidationError, match="provenance is required"):
        CDLHistogramResponse(
            status=CDLAnalysisStatus.SUCCESS,
            geometry_hash="d" * 64,
            total_pixel_count=1,
            coverage_pct=100,
        )


def test_success_status_requires_verified_vintage_and_coverage():
    with pytest.raises(ValidationError, match="vintage_verified and coverage_verified"):
        CDLHistogramResponse(
            status=CDLAnalysisStatus.SUCCESS,
            geometry_hash="e" * 64,
            total_pixel_count=1,
            coverage_pct=100,
            vintage_verified=True,
            provenance=_provenance(),
        )


def test_histogram_counts_cannot_be_negative():
    with pytest.raises(ValidationError, match="pixel_count must be non-negative"):
        CDLHistogramBin(class_value=1, pixel_count=-1)
