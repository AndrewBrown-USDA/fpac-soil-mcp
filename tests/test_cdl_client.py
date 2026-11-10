import httpx
import pytest

from fpac_soil_mcp.cdl_client import CDLClient, parse_histogram_payload
from fpac_soil_mcp.cdl_models import CDLAnalysisStatus


def test_cdl_client_discovers_and_caches_service_metadata():
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            200,
            json={
                "capabilities": "Image, Catalog, Mensuration",
                "spatialReference": {"wkid": 3857},
                "pixelType": "U8",
                "bandCount": 1,
                "pixelSizeX": 30,
                "pixelSizeY": 30,
                "fullExtent": {"xmin": -1, "ymin": -2, "xmax": 3, "ymax": 4},
            },
        )

    client = CDLClient(
        base_url="https://example.test/ImageServer",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    metadata = client.get_service_metadata()
    cached = client.get_service_metadata()

    assert metadata.capabilities == ["Image", "Catalog", "Mensuration"]
    assert metadata.spatial_reference == "3857"
    assert metadata.band_count == 1
    assert metadata.full_extent == {"xmin": -1, "ymin": -2, "xmax": 3, "ymax": 4}
    assert metadata.response_hash
    assert cached == metadata
    assert calls == 1


def test_cdl_client_inspects_catalog_and_posts_histogram_request():
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("/query"):
            return httpx.Response(200, json={"features": [{"attributes": {"Year": 2025}}]})
        return httpx.Response(200, json={"histograms": [{"counts": [1, 2]}]})

    client = CDLClient(
        base_url="https://example.test/ImageServer",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    catalog = client.get_catalog()
    histogram = client.compute_statistics_histograms(
        geometry={"rings": [[[0, 0], [1, 0], [1, 1], [0, 0]]]},
        mosaic_rule={"mosaicMethod": "esriMosaicNone"},
    )

    assert catalog["features"][0]["attributes"]["Year"] == 2025
    assert histogram["histograms"][0]["counts"] == [1, 2]
    assert requests[0].method == "GET"
    assert requests[1].method == "POST"
    assert "geometryType=esriGeometryPolygon" in requests[1].content.decode()


def test_cdl_client_resolves_vintage_to_locked_catalog_raster():
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("/ImageServer"):
            return httpx.Response(
                200,
                json={
                    "objectIdField": "OBJECTID",
                    "timeInfo": {"startTimeField": "Year"},
                },
            )
        return httpx.Response(
            200,
            json={"features": [{"attributes": {"OBJECTID": 42, "Year": 2025}}]},
        )

    client = CDLClient(
        base_url="https://example.test/ImageServer",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    metadata = client.get_service_metadata()
    mosaic_rule = client.resolve_product_vintage("2025", metadata=metadata)

    assert mosaic_rule == {
        "mosaicMethod": "esriMosaicLockRaster",
        "lockRasterIds": [42],
    }
    assert requests[1].url.params["where"] == "Year = 2025"


@pytest.mark.parametrize(
    "catalog_payload",
    [
        {"features": []},
        {
            "features": [
                {"attributes": {"OBJECTID": 1, "Year": 2024}},
                {"attributes": {"OBJECTID": 2, "Year": 2025}},
            ]
        },
        {"features": [{"attributes": {"OBJECTID": 42, "Year": 2024}}]},
    ],
)
def test_cdl_client_rejects_unverified_vintage(catalog_payload):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/ImageServer"):
            return httpx.Response(
                200,
                json={
                    "objectIdField": "OBJECTID",
                    "timeInfo": {"startTimeField": "Year"},
                },
            )
        return httpx.Response(200, json=catalog_payload)

    client = CDLClient(
        base_url="https://example.test/ImageServer",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(ValueError, match="ImageServer catalog"):
        client.resolve_product_vintage("2025")


def test_cdl_client_rejects_empty_catalog_filter():
    client = CDLClient(base_url="https://example.test/ImageServer")

    with pytest.raises(ValueError, match="where must be a non-empty expression"):
        client.get_catalog(where=" ")


def test_cdl_client_returns_validated_histogram_evidence_with_nodata():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/ImageServer"):
            return httpx.Response(
                200,
                json={
                    "capabilities": "Image",
                    "objectIdField": "OBJECTID",
                    "timeInfo": {"startTimeField": "Year"},
                },
            )
        if request.url.path.endswith("/query"):
            return httpx.Response(
                200,
                json={"features": [{"attributes": {"OBJECTID": 42, "Year": 2025}}]},
            )
        if request.url.path.endswith("/rasterAttributeTable"):
            return httpx.Response(
                200,
                json={
                    "features": [
                        {"attributes": {"Value": 0, "Class_Names": "Background"}},
                        {"attributes": {"Value": 1, "Class_Names": "Corn"}},
                    ]
                },
            )
        return httpx.Response(
            200,
            json={"histograms": [{"bins": [{"value": 0, "count": 2}, {"value": 1, "count": 8}]}]},
        )

    client = CDLClient(
        base_url="https://example.test/ImageServer",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    response = client.analyze_polygon_histogram(
        geometry={"rings": [[[0, 0], [1, 0], [1, 1], [0, 0]]]},
        geometry_hash="a" * 64,
        product_vintage="2025",
        qualifying_class_values={1},
    )

    assert response.status is CDLAnalysisStatus.SUCCESS
    assert response.total_pixel_count == 10
    assert response.nodata_pixel_count == 2
    assert response.coverage_pct == 80
    assert response.qualifying_agricultural_pixel_pct == 100
    assert response.histogram[0].is_qualifying_agricultural is False
    assert response.histogram[1].is_qualifying_agricultural is True
    assert response.histogram[0].class_name == "Background"
    assert response.histogram[1].class_name == "Corn"


def test_cdl_client_excludes_nodata_from_qualifying_evidence():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/ImageServer"):
            return httpx.Response(
                200,
                json={
                    "capabilities": "Image",
                    "objectIdField": "OBJECTID",
                    "timeInfo": {"startTimeField": "Year"},
                },
            )
        if request.url.path.endswith("/query"):
            return httpx.Response(
                200,
                json={"features": [{"attributes": {"OBJECTID": 42, "Year": 2025}}]},
            )
        if request.url.path.endswith("/rasterAttributeTable"):
            return httpx.Response(
                200,
                json={
                    "features": [
                        {"attributes": {"Value": 0, "Class_Names": "Background"}},
                        {"attributes": {"Value": 1, "Class_Names": "Corn"}},
                    ]
                },
            )
        return httpx.Response(
            200,
            json={"histograms": [{"bins": [{"value": 0, "count": 2}, {"value": 1, "count": 8}]}]},
        )

    client = CDLClient(
        base_url="https://example.test/ImageServer",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    response = client.analyze_polygon_histogram(
        geometry={"rings": [[[0, 0], [1, 0], [1, 1], [0, 0]]]},
        geometry_hash="c" * 64,
        product_vintage="2025",
        qualifying_class_values={0, 1},
    )

    assert response.qualifying_agricultural_pixel_pct == 100
    assert response.histogram[0].is_qualifying_agricultural is False
    assert response.histogram[1].is_qualifying_agricultural is True


def test_cdl_client_rejects_ambiguous_histogram_shape():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/ImageServer"):
            return httpx.Response(
                200,
                json={
                    "capabilities": "Image",
                    "objectIdField": "OBJECTID",
                    "timeInfo": {"startTimeField": "Year"},
                },
            )
        if request.url.path.endswith("/query"):
            return httpx.Response(
                200,
                json={"features": [{"attributes": {"OBJECTID": 42, "Year": 2025}}]},
            )
        if request.url.path.endswith("/rasterAttributeTable"):
            return httpx.Response(
                200,
                json={"features": [{"attributes": {"Value": 1, "Class_Names": "Corn"}}]},
            )
        return httpx.Response(200, json={"histograms": [{"counts": [1, 2]}]})

    client = CDLClient(
        base_url="https://example.test/ImageServer",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    response = client.analyze_polygon_histogram(
        geometry={"rings": [[[0, 0], [1, 0], [1, 1], [0, 0]]]},
        geometry_hash="b" * 64,
        product_vintage="2025",
        qualifying_class_values={1},
    )

    assert response.status is CDLAnalysisStatus.AMBIGUOUS
    assert "Histogram counts require" in response.error_message


def test_parse_histogram_payload_derives_integer_classes_from_valid_edges():
    bins = parse_histogram_payload(
        {
            "histograms": [
                {
                    "min": -0.5,
                    "max": 2.5,
                    "size": 1,
                    "counts": [2, 8, 3],
                }
            ]
        },
        nodata_class_values={0},
    )

    assert [(item.class_value, item.pixel_count) for item in bins] == [(0, 2), (1, 8), (2, 3)]


@pytest.mark.parametrize(
    "histogram",
    [
        {"min": -0.5, "max": 3.5, "size": 2, "counts": [2, 8]},
        {"min": -0.5, "max": 2.5, "size": 1, "counts": [2, 8]},
        {"min": 0, "max": 2, "size": 1, "counts": [2, 8]},
        {"min": -0.5, "max": 2.5, "size": 1, "counts": [2, 8, 3, 1]},
    ],
)
def test_parse_histogram_payload_rejects_ambiguous_count_edges(histogram):
    with pytest.raises((TypeError, ValueError)):
        parse_histogram_payload(
            {"histograms": [histogram]},
            nodata_class_values={0},
        )


@pytest.mark.parametrize("count", [8.9, -1, -0.5, True])
def test_parse_histogram_payload_rejects_invalid_counts(count):
    with pytest.raises((TypeError, ValueError)):
        parse_histogram_payload(
            {
                "histograms": [
                    {"bins": [{"value": 1, "count": count}]},
                ]
            },
            nodata_class_values={0},
        )


@pytest.mark.parametrize("failure", ["status", "request", "malformed"])
def test_cdl_client_normalizes_upstream_failures(failure):
    def handler(request: httpx.Request) -> httpx.Response:
        if failure == "status":
            return httpx.Response(503)
        if failure == "request":
            raise httpx.ConnectError("offline", request=request)
        return httpx.Response(200, content=b"not-json")

    client = CDLClient(
        base_url="https://example.test/ImageServer",
        max_retries=0,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(RuntimeError, match="CDL ImageServer request failed"):
        client.get_service_metadata()
