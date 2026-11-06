"""USDA NASS Cropland Data Layer ArcGIS ImageServer client."""

from __future__ import annotations

import hashlib
import json
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
            payload = self.compute_statistics_histograms(geometry=geometry, mosaic_rule=mosaic_rule)
            bins = parse_histogram_payload(payload, nodata_class_values=nodata_class_values or {0})
            bins = [
                item.model_copy(
                    update={
                        "is_qualifying_agricultural": item.class_value in qualifying_class_values
                    }
                )
                for item in bins
            ]
            total = sum(item.pixel_count for item in bins)
            nodata = sum(
                item.pixel_count
                for item in bins
                if item.class_value in (nodata_class_values or {0})
            )
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
                item.pixel_count for item in bins if item.class_value in qualifying_class_values
            )
            return CDLHistogramResponse(
                status=CDLAnalysisStatus.SUCCESS,
                geometry_hash=geometry_hash,
                histogram=bins,
                total_pixel_count=total,
                nodata_pixel_count=nodata,
                coverage_pct=(valid / total) * 100,
                product_vintage=product_vintage,
                qualifying_agricultural_pixel_pct=(qualifying / valid) * 100,
                service_metadata=metadata,
                provenance=provenance,
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
        selected_extent = {
            key: extent[key]
            for key in ("xmin", "ymin", "xmax", "ymax")
            if isinstance(extent.get(key), (int, float))
        }
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
        return CDLServiceMetadata(
            endpoint=self.base_url,
            capabilities=capability_values,
            spatial_reference=(str(spatial_reference_value) if spatial_reference_value else None),
            pixel_type=payload.get("pixelType"),
            band_count=payload.get("bandCount"),
            pixel_size_x=payload.get("pixelSizeX"),
            pixel_size_y=payload.get("pixelSizeY"),
            full_extent=selected_extent or None,
            retrieved_at_utc=retrieved_at,
            response_hash=hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest(),
        )


def parse_histogram_payload(
    payload: dict[str, Any], *, nodata_class_values: set[int]
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
            if not isinstance(class_value, int) or not isinstance(pixel_count, int):
                raise TypeError("Histogram bins must expose integer value and count fields.")
            parsed.append(
                CDLHistogramBin(
                    class_value=class_value,
                    pixel_count=pixel_count,
                )
            )
        return parsed

    raw_counts = histogram.get("counts")
    minimum = histogram.get("min")
    if isinstance(raw_counts, dict):
        items = raw_counts.items()
    elif isinstance(raw_counts, list) and isinstance(minimum, int):
        items = ((minimum + offset, count) for offset, count in enumerate(raw_counts))
    else:
        raise TypeError("Histogram must expose explicit bins or counts with an integer min.")

    parsed = []
    for raw_value, raw_count in items:
        try:
            class_value = int(raw_value)
            pixel_count = int(raw_count)
        except (TypeError, ValueError) as exc:
            raise ValueError("Histogram class values and counts must be integers.") from exc
        parsed.append(
            CDLHistogramBin(
                class_value=class_value,
                pixel_count=pixel_count,
            )
        )
    return parsed
