"""USDA NASS Cropland Data Layer ArcGIS ImageServer client."""

from __future__ import annotations

import hashlib
import json
import math
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from fpac_soil_mcp.authority import Provenance
from fpac_soil_mcp.cdl_models import (
    CDLAnalysisStatus,
    CDLHistogramBin,
    CDLHistogramResponse,
    CDLServiceMetadata,
)
from fpac_soil_mcp.config import settings
from fpac_soil_mcp.http_client import (
    HttpRequestError,
    HttpStatusError,
    execute_http_request_with_retry,
)


class CDLVintageUnavailable(ValueError):
    """Raised when a requested CDL vintage cannot be verified or selected."""


class CDLClient:
    """Client for validated NASS CDL ImageServer discovery and requests."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        metadata_cache_seconds: float | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.base_url = (base_url or settings.nass_cdl_image_server_url).rstrip("/")
        self.timeout = timeout or settings.request_timeout_seconds
        self.max_retries = settings.max_retries if max_retries is None else max_retries
        self.metadata_cache_seconds = (
            settings.nass_cdl_metadata_cache_seconds
            if metadata_cache_seconds is None
            else metadata_cache_seconds
        )
        if self.metadata_cache_seconds <= 0:
            raise ValueError("metadata_cache_seconds must be positive.")
        self._http_client = http_client
        self._metadata_cache: tuple[datetime, CDLServiceMetadata] | None = None
        self._raster_attribute_table_cache: dict[int, str] | None = None

    def get_service_metadata(self, *, force_refresh: bool = False) -> CDLServiceMetadata:
        """Fetch, validate, and cache ImageServer service metadata."""
        now = datetime.now(UTC)
        if (
            not force_refresh
            and self._metadata_cache is not None
            and now - self._metadata_cache[0] < timedelta(seconds=self.metadata_cache_seconds)
        ):
            return self._metadata_cache[1]

        payload = self._get_json(self.base_url, params={"f": "json"})
        metadata = self._parse_metadata(payload, retrieved_at=now)
        self._metadata_cache = (now, metadata)
        return metadata

    def get_catalog(self, *, where: str = "1=1") -> dict[str, Any]:
        """Inspect the ImageServer catalog without treating it as pixel data."""
        if not where.strip():
            raise ValueError("where must be a non-empty expression.")
        return self._get_json(
            f"{self.base_url}/query",
            params={
                "where": where,
                "outFields": "*",
                "returnGeometry": "false",
                "f": "json",
            },
        )

    def get_raster_attribute_table(self, *, force_refresh: bool = False) -> dict[int, str]:
        """Fetch live CDL numeric values and their raster attribute-table names."""
        if self._raster_attribute_table_cache is not None and not force_refresh:
            return dict(self._raster_attribute_table_cache)

        payload = self._get_json(f"{self.base_url}/rasterAttributeTable", params={"f": "json"})
        mapping: dict[int, str] = {}
        for feature in payload.get("features", []):
            attributes = feature.get("attributes", {})
            value = attributes.get("Value")
            class_name = attributes.get("Class_Names")
            if isinstance(value, int) and isinstance(class_name, str) and class_name.strip():
                mapping[value] = class_name.strip()
        if not mapping:
            raise ValueError("CDL raster attribute table did not contain Value/Class_Names rows.")
        self._raster_attribute_table_cache = mapping
        return dict(mapping)

    def compute_statistics_histograms(
        self,
        *,
        geometry: dict[str, Any],
        geometry_type: str = "esriGeometryPolygon",
        mosaic_rule: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Submit a bounded raw histogram request for later validated parsing."""
        if geometry_type != "esriGeometryPolygon":
            raise ValueError("Only esriGeometryPolygon is supported for CDL histograms.")
        if not isinstance(geometry, dict) or not geometry:
            raise ValueError("geometry must be a non-empty Esri polygon object.")

        data: dict[str, Any] = {
            "f": "json",
            "geometryType": geometry_type,
            "geometry": json.dumps(geometry, separators=(",", ":")),
        }
        if mosaic_rule is not None:
            data["mosaicRule"] = json.dumps(mosaic_rule, separators=(",", ":"))
        return self._post_json(f"{self.base_url}/computeStatisticsHistograms", data=data)

    def resolve_product_vintage(
        self, product_vintage: str, *, metadata: CDLServiceMetadata | None = None
    ) -> dict[str, Any]:
        """Resolve a requested year to one verified ImageServer catalog raster."""
        if not product_vintage.isdigit():
            raise CDLVintageUnavailable("product_vintage must be a numeric year.")
        service_metadata = metadata or self.get_service_metadata()
        time_field = service_metadata.time_field
        object_id_field = service_metadata.object_id_field
        if not time_field or not object_id_field:
            raise CDLVintageUnavailable(
                "ImageServer metadata does not expose a verifiable time and object ID field."
            )

        catalog = self.get_catalog(where=f"{time_field} = {int(product_vintage)}")
        features = catalog.get("features")
        if not isinstance(features, list) or len(features) != 1:
            raise CDLVintageUnavailable(
                f"ImageServer catalog did not identify exactly one raster for vintage {product_vintage}."
            )
        attributes = features[0].get("attributes")
        if not isinstance(attributes, dict):
            raise CDLVintageUnavailable("ImageServer catalog item has no valid attributes.")
        object_id = attributes.get(object_id_field)
        selected_vintage = attributes.get(time_field)
        if not isinstance(object_id, int) or selected_vintage != int(product_vintage):
            raise CDLVintageUnavailable(
                "ImageServer catalog item did not verify the requested vintage and object ID."
            )
        return {
            "mosaicMethod": "esriMosaicLockRaster",
            "lockRasterIds": [object_id],
        }

    def analyze_polygon_histogram(
        self,
        *,
        geometry: dict[str, Any],
        geometry_hash: str,
        product_vintage: str,
        qualifying_class_values: set[int],
        nodata_class_values: set[int] | None = None,
        mosaic_rule: dict[str, Any] | None = None,
    ) -> CDLHistogramResponse:
        """Fetch and validate categorical histogram evidence for a polygon."""
        now = datetime.now(UTC)
        provenance = Provenance(
            source_name="USDA NASS Cropland Data Layer ImageServer",
            source_reference=self.base_url,
            timestamp_utc=now,
            method_version="cdl-histogram-v1",
            configuration_version=f"product_{product_vintage}",
        )
        try:
            metadata = self.get_service_metadata()
            selected_mosaic_rule = self.resolve_product_vintage(product_vintage, metadata=metadata)
            class_names = self.get_raster_attribute_table()
            payload = self.compute_statistics_histograms(
                geometry=geometry,
                mosaic_rule=mosaic_rule or selected_mosaic_rule,
            )
            bins = parse_histogram_payload(
                payload,
                nodata_class_values=nodata_class_values or {0},
                class_names=class_names,
            )
            effective_nodata = nodata_class_values or {0}
            bins = [
                item.model_copy(
                    update={
                        "is_qualifying_agricultural": item.class_value
                        in (qualifying_class_values - effective_nodata)
                    }
                )
                for item in bins
            ]
            total = sum(item.pixel_count for item in bins)
            nodata = sum(item.pixel_count for item in bins if item.class_value in effective_nodata)
            valid = total - nodata
            if valid <= 0:
                return CDLHistogramResponse(
                    status=CDLAnalysisStatus.UNAVAILABLE,
                    geometry_hash=geometry_hash,
                    product_vintage=product_vintage,
                    service_metadata=metadata,
                    provenance=provenance,
                    error_message="Histogram contains no valid CDL pixels.",
                )
            qualifying = sum(
                item.pixel_count
                for item in bins
                if item.class_value in (qualifying_class_values - effective_nodata)
            )
            return CDLHistogramResponse(
                status=CDLAnalysisStatus.SUCCESS,
                geometry_hash=geometry_hash,
                histogram=bins,
                total_pixel_count=total,
                nodata_pixel_count=nodata,
                coverage_pct=(valid / total) * 100,
                product_vintage=product_vintage,
                vintage_verified=True,
                coverage_verified=True,
                qualifying_agricultural_pixel_pct=(qualifying / valid) * 100,
                service_metadata=metadata,
                provenance=provenance,
            )
        except CDLVintageUnavailable as exc:
            return CDLHistogramResponse(
                status=CDLAnalysisStatus.UNAVAILABLE,
                geometry_hash=geometry_hash,
                product_vintage=product_vintage,
                provenance=provenance,
                error_message=str(exc),
            )
        except (TypeError, ValueError) as exc:
            return CDLHistogramResponse(
                status=CDLAnalysisStatus.AMBIGUOUS,
                geometry_hash=geometry_hash,
                product_vintage=product_vintage,
                provenance=provenance,
                error_message=str(exc),
            )
        except RuntimeError as exc:
            return CDLHistogramResponse(
                status=CDLAnalysisStatus.ERROR,
                geometry_hash=geometry_hash,
                product_vintage=product_vintage,
                provenance=provenance,
                error_message=str(exc),
            )

    def _get_json(self, url: str, *, params: dict[str, str]) -> dict[str, Any]:
        try:
            response = execute_http_request_with_retry(
                "GET",
                url,
                params=params,
                timeout=self.timeout,
                max_retries=self.max_retries,
                client=self._http_client,
            )
            return self._require_object(response.json())
        except (HttpRequestError, HttpStatusError, TypeError, ValueError) as exc:
            raise RuntimeError(f"CDL ImageServer request failed: {exc}") from exc

    def _post_json(self, url: str, *, data: dict[str, Any]) -> dict[str, Any]:
        try:
            response = execute_http_request_with_retry(
                "POST",
                url,
                data=data,
                timeout=self.timeout,
                max_retries=self.max_retries,
                client=self._http_client,
            )
            return self._require_object(response.json())
        except (HttpRequestError, HttpStatusError, TypeError, ValueError) as exc:
            raise RuntimeError(f"CDL ImageServer request failed: {exc}") from exc

    @staticmethod
    def _require_object(payload: Any) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise TypeError("CDL ImageServer response must be a JSON object.")
        if "error" in payload:
            raise ValueError(f"CDL ImageServer returned an error payload: {payload['error']}")
        return payload

    def _parse_metadata(
        self, payload: dict[str, Any], *, retrieved_at: datetime
    ) -> CDLServiceMetadata:
        spatial_reference = payload.get("spatialReference") or {}
        spatial_reference_value = (
            spatial_reference.get("latestWkid")
            or spatial_reference.get("wkid")
            or spatial_reference.get("wkt")
        )
        extent = payload.get("fullExtent") or {}
        extent_keys = ("xmin", "ymin", "xmax", "ymax")
        selected_extent = None
        if all(
            isinstance(extent.get(key), (int, float)) and not isinstance(extent.get(key), bool)
            for key in extent_keys
        ):
            selected_extent = {key: float(extent[key]) for key in extent_keys}
        capabilities = payload.get("capabilities", "")
        if isinstance(capabilities, str):
            capability_values = [
                value.strip() for value in capabilities.split(",") if value.strip()
            ]
        elif isinstance(capabilities, list):
            capability_values = [str(value) for value in capabilities]
        else:
            capability_values = []
        canonical_payload = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        time_info = payload.get("timeInfo") or {}
        time_field = time_info.get("startTimeField")
        return CDLServiceMetadata(
            endpoint=self.base_url,
            capabilities=capability_values,
            spatial_reference=(str(spatial_reference_value) if spatial_reference_value else None),
            pixel_type=payload.get("pixelType"),
            band_count=payload.get("bandCount"),
            pixel_size_x=payload.get("pixelSizeX"),
            pixel_size_y=payload.get("pixelSizeY"),
            full_extent=selected_extent,
            object_id_field=payload.get("objectIdField"),
            time_field=time_field if isinstance(time_field, str) else None,
            retrieved_at_utc=retrieved_at,
            response_hash=hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest(),
        )


def parse_histogram_payload(
    payload: dict[str, Any],
    *,
    nodata_class_values: set[int],
    class_names: dict[int, str] | None = None,
) -> list[CDLHistogramBin]:
    """Parse only explicit categorical histogram representations."""
    histograms = payload.get("histograms")
    if not isinstance(histograms, list) or len(histograms) != 1:
        raise ValueError("Histogram response must contain exactly one histogram.")
    histogram = histograms[0]
    if not isinstance(histogram, dict):
        raise TypeError("Histogram entry must be an object.")

    raw_bins = histogram.get("bins")
    if isinstance(raw_bins, list):
        parsed: list[CDLHistogramBin] = []
        for raw_bin in raw_bins:
            if not isinstance(raw_bin, dict):
                raise TypeError("Histogram bins must be objects.")
            class_value = raw_bin.get("value", raw_bin.get("classValue"))
            pixel_count = raw_bin.get("count", raw_bin.get("pixelCount"))
            if (
                not isinstance(class_value, int)
                or isinstance(class_value, bool)
                or not isinstance(pixel_count, int)
                or isinstance(pixel_count, bool)
            ):
                raise TypeError("Histogram bins must expose integer value and count fields.")
            parsed.append(
                CDLHistogramBin(
                    class_value=class_value,
                    pixel_count=pixel_count,
                    class_name=(class_names or {}).get(class_value),
                )
            )
        return parsed

    raw_counts = histogram.get("counts")
    minimum = histogram.get("min")
    maximum = histogram.get("max")
    size = histogram.get("size")
    if isinstance(raw_counts, dict):
        items = raw_counts.items()
    elif isinstance(raw_counts, list):
        if not (
            isinstance(minimum, (int, float))
            and not isinstance(minimum, bool)
            and isinstance(maximum, (int, float))
            and not isinstance(maximum, bool)
            and isinstance(size, int)
            and not isinstance(size, bool)
        ):
            raise TypeError(
                "Histogram counts require numeric min and max and integer size metadata."
            )
        if not all(math.isfinite(value) for value in (minimum, maximum)):
            raise ValueError("Histogram min and max metadata must be finite.")
        if size <= 0 or size != len(raw_counts):
            raise ValueError("Histogram size must equal the positive count-array length.")
        if (
            maximum <= minimum
            or not math.isclose((maximum - minimum) / size, 1, rel_tol=0, abs_tol=1e-9)
            or not _is_integer_center(minimum)
            or not _is_integer_center(maximum)
        ):
            raise ValueError(
                "Histogram counts must use unit-width buckets centered on integer classes."
            )
        items = ((int(minimum + offset + 0.5), count) for offset, count in enumerate(raw_counts))
    else:
        raise TypeError("Histogram must expose explicit bins or validated counts metadata.")

    parsed = []
    for raw_value, raw_count in items:
        if not isinstance(raw_value, int) or isinstance(raw_value, bool):
            raise TypeError("Histogram class values must be integers.")
        if not isinstance(raw_count, int) or isinstance(raw_count, bool):
            raise TypeError("Histogram counts must be integers.")
        class_value = raw_value
        pixel_count = raw_count
        parsed.append(
            CDLHistogramBin(
                class_value=class_value,
                pixel_count=pixel_count,
                class_name=(class_names or {}).get(class_value),
            )
        )
    return parsed


def _is_integer_center(edge: float) -> bool:
    """Return whether a half-pixel edge is centered on an integer class."""
    return math.isclose(edge - 0.5, round(edge - 0.5), rel_tol=0, abs_tol=1e-9)
