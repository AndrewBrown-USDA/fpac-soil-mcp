"""Census TIGERweb 2020 Urban Areas MapServer Layer 6 REST client.

Screens geographic coordinates and polygon footprints against Census 2020 Urban Area
boundaries for preliminary statutory exemption review under 7 CFR § 658.2(a).
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

import httpx
from shapely.geometry import MultiPolygon, Polygon

from fpac_soil_mcp.authority import Provenance
from fpac_soil_mcp.config import settings
from fpac_soil_mcp.geometry import (
    GeometryValidationError,
    compute_geometry_hash,
    parse_geojson_geometry,
)
from fpac_soil_mcp.integration_models import IntegrationStatus, UrbanExemptionRecord

logger = logging.getLogger(__name__)


class TigerwebClientError(Exception):
    """Base exception for Census TIGERweb client errors."""


class TigerwebClient:
    """Client for US Census Bureau TIGERweb 2020 Urban Areas MapServer."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.base_url = (base_url or settings.tigerweb_rest_url).rstrip("/")
        self.timeout = timeout or settings.tigerweb_timeout_seconds
        self._http_client = http_client

    def check_urban_exemption(
        self,
        geometry_input: dict[str, Any] | str | Polygon | MultiPolygon,
    ) -> UrbanExemptionRecord:
        """Screen a polygon or geometry against 2020 Census Urban Areas (Layer 6).

        Args:
            geometry_input: GeoJSON dict/string or Shapely geometry.

        Returns:
            UrbanExemptionRecord containing screening status and intersected urban areas.
        """
        now = datetime.now(UTC)
        provenance = Provenance(
            source_name="US Census Bureau TIGERweb 2020 Urban Areas MapServer",
            source_reference=self.base_url,
            timestamp_utc=now,
            method_version="1.0.0",
            configuration_version="census_2020_layer6",
        )

        try:
            if isinstance(geometry_input, (Polygon, MultiPolygon)):
                geom = geometry_input
            else:
                geom = parse_geojson_geometry(geometry_input)

            geom_hash = compute_geometry_hash(geom)
            minx, miny, maxx, maxy = geom.bounds

            # Format ESRI polygon rings or envelope
            if isinstance(geom, Polygon):
                rings = [list(geom.exterior.coords)]
            else:
                rings = [list(p.exterior.coords) for p in geom.geoms]

            esri_geom = json.dumps({"rings": rings})

            params = {
                "geometry": esri_geom,
                "geometryType": "esriGeometryPolygon",
                "inSR": "4326",
                "spatialRel": "esriSpatialRelIntersects",
                "outFields": "GEOID,NAME,BASENAME,POP100,HU100",
                "returnGeometry": "false",
                "outSR": "4326",
                "f": "json",
            }

            query_url = f"{self.base_url}/query" if not self.base_url.endswith("/query") else self.base_url

            if self._http_client is not None:
                resp = self._http_client.post(query_url, data=params, timeout=self.timeout)
            else:
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.post(query_url, data=params)

            resp.raise_for_status()
            data = resp.json()

            if "error" in data:
                error_msg = data["error"].get("message", "Unknown TIGERweb error")
                return UrbanExemptionRecord(
                    status=IntegrationStatus.ERROR,
                    geometry_hash=geom_hash,
                    provenance=provenance,
                    error_message=f"TIGERweb MapServer error: {error_msg}",
                )

            features = data.get("features", [])
            is_intersected = len(features) > 0
            urban_names = [
                f.get("attributes", {}).get("NAME") or f.get("attributes", {}).get("BASENAME", "Unknown Urban Area")
                for f in features
                if f.get("attributes")
            ]

            return UrbanExemptionRecord(
                status=IntegrationStatus.SUCCESS,
                geometry_hash=geom_hash,
                provenance=provenance,
                source_layer="Urban Areas 2020 (Layer 6)",
                layer_version="2020",
                is_urban_intersected=is_intersected,
                urban_area_names=urban_names,
            )

        except (httpx.HTTPError, GeometryValidationError, ValueError, KeyError) as exc:
            logger.error("TIGERweb screening failed: %s", exc)
            fallback_hash = compute_geometry_hash(geom) if "geom" in locals() and geom else "sha256:0000000000000000000000000000000000000000000000000000000000000000"
            return UrbanExemptionRecord(
                status=IntegrationStatus.ERROR,
                geometry_hash=fallback_hash,
                provenance=provenance,
                error_message=f"Urban screening failed: {exc}",
            )
