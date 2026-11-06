from datetime import UTC, datetime

from fpac_soil_mcp.authority import Provenance
from fpac_soil_mcp.cdl_models import (
    CDLAnalysisStatus,
    CDLHistogramBin,
    CDLHistogramResponse,
    CDLServiceMetadata,
)
from fpac_soil_mcp.tools import cdl_tools


class FakeCDLClient:
    submitted_geometry = None

    def get_service_metadata(self):
        return CDLServiceMetadata(
            endpoint="https://example.test/ImageServer",
            spatial_reference="4326",
            retrieved_at_utc=datetime.now(UTC),
            response_hash="a" * 64,
        )

    def analyze_polygon_histogram(self, **kwargs):
        self.submitted_geometry = kwargs["geometry"]
        return CDLHistogramResponse(
            status=CDLAnalysisStatus.SUCCESS,
            geometry_hash=kwargs["geometry_hash"],
            histogram=[CDLHistogramBin(class_value=1, pixel_count=4)],
            total_pixel_count=4,
            coverage_pct=100,
            product_vintage=kwargs["product_vintage"],
            provenance=Provenance(
                source_name="USDA NASS CDL ImageServer",
                source_reference="https://example.test/ImageServer",
                timestamp_utc=datetime.now(UTC),
                method_version="test",
                configuration_version="test",
            ),
        )


class OutOfExtentCDLClient(FakeCDLClient):
    def get_service_metadata(self):
        metadata = super().get_service_metadata()
        return metadata.model_copy(
            update={"full_extent": {"xmin": 10, "ymin": 10, "xmax": 11, "ymax": 11}}
        )


def test_cdl_tool_validates_geometry_and_propagates_histogram(monkeypatch):
    fake = FakeCDLClient()
    monkeypatch.setattr(cdl_tools, "CDLClient", lambda: fake)

    response = cdl_tools.analyze_cdl_histogram(
        {
            "type": "Polygon",
            "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]],
        },
        "2025",
        [1],
    )

    assert response.status is CDLAnalysisStatus.SUCCESS
    assert response.product_vintage == "2025"
    assert fake.submitted_geometry["rings"]
    assert fake.submitted_geometry["spatialReference"] == {"wkid": 4326}


def test_cdl_tool_rejects_invalid_geometry_and_missing_class_policy():
    invalid_geometry = cdl_tools.analyze_cdl_histogram("not-json", "2025", [1])
    missing_policy = cdl_tools.analyze_cdl_histogram(
        {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]},
        "2025",
        [],
    )

    assert invalid_geometry.status is CDLAnalysisStatus.INVALID
    assert missing_policy.status is CDLAnalysisStatus.INVALID
    assert "qualifying_class_values" in missing_policy.error_message


def test_cdl_tool_reports_out_of_extent_aoi(monkeypatch):
    monkeypatch.setattr(cdl_tools, "CDLClient", OutOfExtentCDLClient)

    response = cdl_tools.analyze_cdl_histogram(
        {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]},
        "2025",
        [1],
    )

    assert response.status is CDLAnalysisStatus.UNAVAILABLE
    assert "outside" in response.error_message
