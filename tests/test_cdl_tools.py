from datetime import UTC, datetime

from fpac_soil_mcp.core.authority import Provenance
from fpac_soil_mcp.mcp.tools import cdl_tools
from fpac_soil_mcp.models.cdl import (
    CDLAnalysisStatus,
    CDLHistogramBin,
    CDLHistogramResponse,
    CDLServiceMetadata,
)


class FakeCDLClient:
    submitted_geometry = None

    def get_service_metadata(self):
        return CDLServiceMetadata(
            endpoint="https://example.test/ImageServer",
            spatial_reference="4326",
            full_extent={"xmin": -10, "ymin": -10, "xmax": 10, "ymax": 10},
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
            vintage_verified=True,
            coverage_verified=True,
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
    monkeypatch.setattr(cdl_tools, "_get_cdl_client", lambda: fake)

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


def test_cdl_tool_combines_all_polygon_features_in_feature_collection(monkeypatch):
    fake = FakeCDLClient()
    monkeypatch.setattr(cdl_tools, "_get_cdl_client", lambda: fake)

    response = cdl_tools.analyze_cdl_histogram(
        {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]],
                    },
                },
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[2, 0], [3, 0], [3, 1], [2, 0]]],
                    },
                },
            ],
        },
        "2025",
        [1],
    )

    assert response.status is CDLAnalysisStatus.SUCCESS
    assert len(fake.submitted_geometry["rings"]) == 2


def test_cdl_tool_rejects_feature_collection_with_invalid_later_feature(monkeypatch):
    fake = FakeCDLClient()
    monkeypatch.setattr(cdl_tools, "_get_cdl_client", lambda: fake)

    response = cdl_tools.analyze_cdl_histogram(
        {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]],
                    },
                },
                {"type": "Feature", "geometry": {"type": "Point", "coordinates": [2, 2]}},
            ],
        },
        "2025",
        [1],
    )

    assert response.status is CDLAnalysisStatus.INVALID
    assert "Unsupported geometry type" in response.error_message
    assert fake.submitted_geometry is None


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
    monkeypatch.setattr(cdl_tools, "_get_cdl_client", OutOfExtentCDLClient)

    response = cdl_tools.analyze_cdl_histogram(
        {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]},
        "2025",
        [1],
    )

    assert response.status is CDLAnalysisStatus.UNAVAILABLE
    assert "Complete AOI coverage" in response.error_message


def test_cdl_tool_reports_unavailable_without_complete_extent(monkeypatch):
    class MissingExtentCDLClient(FakeCDLClient):
        def get_service_metadata(self):
            return super().get_service_metadata().model_copy(update={"full_extent": None})

    monkeypatch.setattr(cdl_tools, "_get_cdl_client", MissingExtentCDLClient)

    response = cdl_tools.analyze_cdl_histogram(
        {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]},
        "2025",
        [1],
    )

    assert response.status is CDLAnalysisStatus.UNAVAILABLE
    assert "Complete AOI coverage" in response.error_message


def test_cdl_tool_reuses_client_across_public_calls(monkeypatch, request):
    cdl_tools._get_cdl_client.cache_clear()
    request.addfinalizer(cdl_tools._get_cdl_client.cache_clear)
    fake = FakeCDLClient()
    created = []

    def factory():
        created.append(fake)
        return fake

    monkeypatch.setattr(cdl_tools, "CDLClient", factory)
    geometry = {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]}

    first = cdl_tools.analyze_cdl_histogram(geometry, "2025", [1])
    second = cdl_tools.analyze_cdl_histogram(geometry, "2025", [1])

    assert first.status is CDLAnalysisStatus.SUCCESS
    assert second.status is CDLAnalysisStatus.SUCCESS
    assert created == [fake]
