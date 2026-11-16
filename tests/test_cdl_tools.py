from datetime import UTC, datetime

from pyproj import CRS

from fpac_soil_mcp.authority import Provenance
from fpac_soil_mcp.cdl_models import (
    CDLAnalysisStatus,
    CDLHistogramBin,
    CDLHistogramResponse,
    CDLServiceMetadata,
)
from fpac_soil_mcp.tools import cdl_tools


class FakeCDLClient:
    def __init__(self):
        self.submitted_geometry = None
        self.submitted_histograms = []
        self.coverage_pct = 100
        self.failed_zones = set()

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
        self.submitted_histograms.append(kwargs)
        if kwargs["geometry_hash"] in self.failed_zones:
            return CDLHistogramResponse(
                status=CDLAnalysisStatus.ERROR,
                geometry_hash=kwargs["geometry_hash"],
                product_vintage=kwargs["product_vintage"],
                error_message="mock upstream failure",
            )
        return CDLHistogramResponse(
            status=CDLAnalysisStatus.SUCCESS,
            geometry_hash=kwargs["geometry_hash"],
            histogram=[CDLHistogramBin(class_value=1, pixel_count=4)],
            total_pixel_count=4,
            coverage_pct=self.coverage_pct,
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

    def resolve_latest_product_vintage(self, *, metadata):
        return "2025"


class OutOfExtentCDLClient(FakeCDLClient):
    def get_service_metadata(self):
        metadata = super().get_service_metadata()
        return metadata.model_copy(
            update={"full_extent": {"xmin": 10, "ymin": 10, "xmax": 11, "ymax": 11}}
        )


class WktSpatialReferenceCDLClient(FakeCDLClient):
    def get_service_metadata(self):
        return (
            super()
            .get_service_metadata()
            .model_copy(
                update={
                    "spatial_reference": CRS.from_epsg(3857).to_wkt(),
                    "full_extent": {
                        "xmin": -1_000_000,
                        "ymin": -1_000_000,
                        "xmax": 1_000_000,
                        "ymax": 1_000_000,
                    },
                }
            )
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


def test_cdl_tool_reprojects_geometry_for_wkt_spatial_reference(monkeypatch):
    fake = WktSpatialReferenceCDLClient()
    monkeypatch.setattr(cdl_tools, "_get_cdl_client", lambda: fake)

    response = cdl_tools.analyze_cdl_histogram(
        {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]},
        "2025",
        [1],
    )

    assert response.status is CDLAnalysisStatus.SUCCESS
    assert fake.submitted_geometry["spatialReference"] == {"wkt": CRS.from_epsg(3857).to_wkt()}
    assert max(point[0] for ring in fake.submitted_geometry["rings"] for point in ring) > 100_000


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


def test_cdl_context_uses_one_vintage_for_three_non_overlapping_zones(monkeypatch):
    fake = FakeCDLClient()
    fake.submitted_histograms = []
    monkeypatch.setattr(cdl_tools, "_get_cdl_client", lambda: fake)

    response = cdl_tools.analyze_cdl_context(
        {"type": "Polygon", "coordinates": [[[0, 0], [0.001, 0], [0.001, 0.001], [0, 0]]]}
    )

    assert response.status is CDLAnalysisStatus.SUCCESS
    assert response.product_vintage == "2025"
    assert [
        item.zone for item in (response.aoi, response.one_mile_ring, response.thirty_meter_band)
    ] == [
        "aoi",
        "one_mile_ring",
        "thirty_meter_band",
    ]
    assert {call["product_vintage"] for call in fake.submitted_histograms} == {"2025"}
    assert all(call["qualifying_class_values"] is None for call in fake.submitted_histograms)
    assert [
        item.classes[0].class_value
        for item in (response.aoi, response.one_mile_ring, response.thirty_meter_band)
    ] == [
        1,
        1,
        1,
    ]
    assert len({call["geometry_hash"] for call in fake.submitted_histograms}) == 3


def test_cdl_context_reprojects_each_zone_for_wkt_spatial_reference(monkeypatch):
    fake = WktSpatialReferenceCDLClient()
    monkeypatch.setattr(cdl_tools, "_get_cdl_client", lambda: fake)

    response = cdl_tools.analyze_cdl_context(
        {"type": "Polygon", "coordinates": [[[0, 0], [0.001, 0], [0.001, 0.001], [0, 0]]]}
    )

    assert response.status is CDLAnalysisStatus.SUCCESS
    assert len(fake.submitted_histograms) == 3
    assert all(
        call["geometry"]["spatialReference"] == {"wkt": CRS.from_epsg(3857).to_wkt()}
        for call in fake.submitted_histograms
    )
    assert all(
        max(abs(point[0]) for ring in call["geometry"]["rings"] for point in ring) > 100
        for call in fake.submitted_histograms
    )


def test_cdl_context_marks_incomplete_coverage_and_upstream_errors(monkeypatch):
    fake = FakeCDLClient()
    fake.submitted_histograms = []
    fake.coverage_pct = 80
    monkeypatch.setattr(cdl_tools, "_get_cdl_client", lambda: fake)

    partial = cdl_tools.analyze_cdl_context(
        {"type": "Polygon", "coordinates": [[[0, 0], [0.001, 0], [0.001, 0.001], [0, 0]]]}
    )

    assert partial.status is CDLAnalysisStatus.PARTIAL
    assert partial.aoi.coverage_pct == 80
    assert partial.aoi.status is CDLAnalysisStatus.PARTIAL
    assert partial.aoi.classes[0].share_pct == 100

    fake.coverage_pct = 100
    fake.failed_zones = {partial.aoi.geometry_hash}
    failed = cdl_tools.analyze_cdl_context(
        {"type": "Polygon", "coordinates": [[[0, 0], [0.001, 0], [0.001, 0.001], [0, 0]]]}
    )
    assert failed.status is CDLAnalysisStatus.PARTIAL
    assert failed.aoi.status is CDLAnalysisStatus.ERROR
    assert failed.aoi.error_message == "mock upstream failure"


def test_cdl_context_reports_vintage_ambiguity(monkeypatch):
    from fpac_soil_mcp.cdl_client import CDLVintageAmbiguous

    class AmbiguousVintageClient(FakeCDLClient):
        def resolve_latest_product_vintage(self, *, metadata):
            raise CDLVintageAmbiguous("multiple latest vintages")

    monkeypatch.setattr(cdl_tools, "_get_cdl_client", AmbiguousVintageClient)
    response = cdl_tools.analyze_cdl_context(
        {"type": "Polygon", "coordinates": [[[0, 0], [0.001, 0], [0.001, 0.001], [0, 0]]]}
    )
    assert response.status is CDLAnalysisStatus.AMBIGUOUS
    assert response.error_message == "multiple latest vintages"
