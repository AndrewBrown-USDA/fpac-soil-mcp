"""Census TIGERweb 2020 Urban Areas MapServer Layer 0 REST client.

Screens geographic coordinates and polygon footprints against Census 2020 Urban Area
boundaries for preliminary statutory exemption review under 7 CFR § 658.2(a).
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

import httpx
from shapely.errors import GEOSException
from shapely.geometry import LinearRing, MultiPolygon, Point, Polygon
from shapely.validation import make_valid

from fpac_soil_mcp.authority import Provenance
from fpac_soil_mcp.config import settings
from fpac_soil_mcp.geometry import (
    GeometryValidationError,
    calculate_acreage,
    compute_geometry_hash,
    parse_geojson_geometry,
)
from fpac_soil_mcp.integration_models import IntegrationStatus, UrbanExemptionRecord

logger = logging.getLogger(__name__)

# Default TIGERweb State and County Boundaries MapServer (Layer 1: Counties)
DEFAULT_TIGERWEB_COUNTY_URL = (
    "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer/1"
)


def _normalize_ring_winding(ring: LinearRing, clockwise: bool = True) -> list[list[float]]:
    """Normalize ring coordinate winding for ArcGIS REST JSON polygon specification.

    ArcGIS polygon JSON requires exterior rings to be clockwise (cw) and interior
    rings (holes) to be counterclockwise (ccw).

    Args:
        ring: Shapely LinearRing.
        clockwise: If True, orient clockwise; if False, orient counterclockwise.

    Returns:
        List of [x, y] or [x, y, z] coordinate lists.
    """
    coords = list(ring.coords)
    is_ccw = ring.is_ccw
    if (clockwise and is_ccw) or (not clockwise and not is_ccw):
        coords.reverse()
    return [list(c) for c in coords]


def _polygon_to_esri_rings(geom: Polygon | MultiPolygon) -> list[list[list[float]]]:
    """Convert Polygon or MultiPolygon to ArcGIS REST rings with normalized winding.

    Args:
        geom: Shapely Polygon or MultiPolygon.

    Returns:
        List of rings where exterior rings are clockwise and interior rings are counterclockwise.
    """
    rings: list[list[list[float]]] = []
    polygons = [geom] if isinstance(geom, Polygon) else list(geom.geoms)

    for poly in polygons:
        # Exterior ring -> Clockwise
        rings.append(_normalize_ring_winding(poly.exterior, clockwise=True))
        # Interior rings (holes) -> Counterclockwise
        for interior in poly.interiors:
            rings.append(_normalize_ring_winding(interior, clockwise=False))

    return rings


class TigerwebClientError(Exception):
    """Base exception for Census TIGERweb client errors."""


class TigerwebClient:
    """Client for US Census Bureau TIGERweb 2020 Urban Areas MapServer."""

    def __init__(
        self,
        base_url: str | None = None,
        county_url: str | None = None,
        timeout: float | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.base_url = (base_url or settings.tigerweb_rest_url).rstrip("/")
        self.county_url = (county_url or DEFAULT_TIGERWEB_COUNTY_URL).rstrip("/")
        self.timeout = timeout or settings.tigerweb_timeout_seconds
        self._http_client = http_client

    def check_urban_exemption(
        self,
        geometry_input: dict[str, Any] | str | Polygon | MultiPolygon,
    ) -> UrbanExemptionRecord:
        """Screen a polygon or geometry against 2020 Census Urban Areas (Layer 0).

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
            configuration_version="census_2020_layer0",
        )

        try:
            if isinstance(geometry_input, (Polygon, MultiPolygon, Point)):
                geom = geometry_input
            else:
                geom = parse_geojson_geometry(geometry_input, allow_point=True)

            geom_hash = compute_geometry_hash(geom)

            # Format ESRI geometry based on type
            if isinstance(geom, Point):
                esri_geom = json.dumps({"x": geom.x, "y": geom.y})
                geom_type_str = "esriGeometryPoint"
            else:
                rings = _polygon_to_esri_rings(geom)
                esri_geom = json.dumps({"rings": rings})
                geom_type_str = "esriGeometryPolygon"

            params = {
                "geometry": esri_geom,
                "geometryType": geom_type_str,
                "inSR": "4326",
                "spatialRel": "esriSpatialRelIntersects",
                "outFields": "GEOID,NAME,BASENAME,POP100,HU100",
                "returnGeometry": "false",
                "outSR": "4326",
                "f": "json",
            }

            query_url = (
                f"{self.base_url}/query" if not self.base_url.endswith("/query") else self.base_url
            )

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
                f.get("attributes", {}).get("NAME")
                or f.get("attributes", {}).get("BASENAME", "Unknown Urban Area")
                for f in features
                if f.get("attributes")
            ]

            return UrbanExemptionRecord(
                status=IntegrationStatus.SUCCESS,
                geometry_hash=geom_hash,
                provenance=provenance,
                source_layer="2020 Urban Areas",
                layer_version="2020",
                is_urban_intersected=is_intersected,
                urban_area_names=urban_names,
            )

        except (httpx.HTTPError, GeometryValidationError, ValueError, KeyError) as exc:
            logger.error("TIGERweb screening failed: %s", exc)
            fallback_hash = (
                compute_geometry_hash(geom)
                if "geom" in locals() and geom
                else "sha256:0000000000000000000000000000000000000000000000000000000000000000"
            )
            return UrbanExemptionRecord(
                status=IntegrationStatus.ERROR,
                geometry_hash=fallback_hash,
                provenance=provenance,
                error_message=f"Urban screening failed: {exc}",
            )

    def get_intersecting_counties(
        self,
        geometry_input: dict[str, Any] | str | Polygon | MultiPolygon,
    ) -> list[dict[str, Any]]:
        """Query Census TIGERweb State & County MapServer for counties intersecting the geometry.

        Args:
            geometry_input: GeoJSON dict/string or Shapely Polygon/MultiPolygon.

        Returns:
            List of county dicts containing:
                - state_fips: 2-digit state FIPS code
                - county_fips: 3-digit county FIPS code
                - geoid: 5-digit combined FIPS code
                - county_name: County or parish name (e.g. 'Story')
                - geometry: Shapely Polygon or MultiPolygon of the county boundary
        """
        try:
            if isinstance(geometry_input, (Polygon, MultiPolygon, Point)):
                geom = geometry_input
            else:
                geom = parse_geojson_geometry(geometry_input, allow_point=True)

            if isinstance(geom, Point):
                esri_geom = json.dumps({"x": geom.x, "y": geom.y})
                geom_type_str = "esriGeometryPoint"
            else:
                rings = _polygon_to_esri_rings(geom)
                esri_geom = json.dumps({"rings": rings})
                geom_type_str = "esriGeometryPolygon"

            params = {
                "geometry": esri_geom,
                "geometryType": geom_type_str,
                "inSR": "4326",
                "spatialRel": "esriSpatialRelIntersects",
                "outFields": "GEOID,NAME,STATE,COUNTY,BASENAME",
                "returnGeometry": "true",
                "outSR": "4326",
                "f": "json",
            }

            query_url = (
                f"{self.county_url}/query"
                if not self.county_url.endswith("/query")
                else self.county_url
            )

            if self._http_client is not None:
                resp = self._http_client.post(query_url, data=params, timeout=self.timeout)
            else:
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.post(query_url, data=params)

            resp.raise_for_status()
            data = resp.json()

            if "error" in data:
                error_msg = data["error"].get("message", "Unknown TIGERweb error")
                logger.error("TIGERweb county query error: %s", error_msg)
                return []

            features = data.get("features", [])
            counties: list[dict[str, Any]] = []

            for f in features:
                attrs = f.get("attributes", {})
                esri_geom_dict = f.get("geometry", {})
                rings = esri_geom_dict.get("rings", [])

                if not rings:
                    continue

                # Reconstruct Shapely Polygon/MultiPolygon from ESRI rings
                polys = []
                for ring in rings:
                    if len(ring) >= 4:
                        polys.append(Polygon(ring))

                if not polys:
                    continue

                if len(polys) == 1:
                    county_shape = polys[0]
                else:
                    county_shape = MultiPolygon(polys)

                if not county_shape.is_valid:
                    county_shape = make_valid(county_shape)

                geoid = str(attrs.get("GEOID", "")).zfill(5)
                state_fips = str(attrs.get("STATE", geoid[:2])).zfill(2)
                county_fips = str(attrs.get("COUNTY", geoid[2:])).zfill(3)
                county_name = attrs.get("BASENAME") or attrs.get("NAME", f"County {county_fips}")

                counties.append(
                    {
                        "state_fips": state_fips,
                        "county_fips": county_fips,
                        "geoid": geoid,
                        "county_name": county_name,
                        "geometry": county_shape,
                    }
                )

            return counties

        except (httpx.HTTPError, ValueError, KeyError) as exc:
            logger.error("Failed to query intersecting counties from TIGERweb: %s", exc)
            return []

    def partition_geometry_by_counties(
        self,
        geometry_input: dict[str, Any] | str | Polygon | MultiPolygon,
        counties: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """Spatially intersect and partition a project footprint into county segments.

        Args:
            geometry_input: GeoJSON dict/string or Shapely Polygon/MultiPolygon.
            counties: Optional pre-fetched county features list. If None, queries TIGERweb.

        Returns:
            List of segment dictionaries containing:
                - segment_id: Sequential identifier (e.g. 'segment_1')
                - state_fips: 2-digit state FIPS
                - county_fips: 3-digit county FIPS
                - county_name: Name of county
                - geometry: Shapely Polygon or MultiPolygon of this segment
                - calculated_acres: Geodesic acreage of this segment
        """
        if isinstance(geometry_input, (Polygon, MultiPolygon)):
            geom = geometry_input
        else:
            geom = parse_geojson_geometry(geometry_input)

        if counties is None:
            counties = self.get_intersecting_counties(geom)

        if not counties:
            # Fallback: single unsegmented county record if county boundaries unavailable
            return [
                {
                    "segment_id": "segment_1",
                    "state_fips": "00",
                    "county_fips": "000",
                    "county_name": "Unsegmented Area",
                    "geometry": geom,
                    "calculated_acres": calculate_acreage(geom),
                }
            ]

        segments: list[dict[str, Any]] = []
        for i, county in enumerate(counties, start=1):
            county_geom = county["geometry"]
            try:
                intersected = geom.intersection(county_geom)
            except (GEOSException, ValueError, TypeError) as exc:
                logger.warning(
                    "Intersection failed with county %s: %s", county.get("county_name"), exc
                )
                continue

            if intersected.is_empty:
                continue

            if not intersected.is_valid:
                intersected = make_valid(intersected)

            if isinstance(intersected, (Polygon, MultiPolygon)):
                seg_shape = intersected
            elif hasattr(intersected, "geoms"):
                poly_parts = [
                    g for g in intersected.geoms if isinstance(g, (Polygon, MultiPolygon))
                ]
                if not poly_parts:
                    continue
                seg_shape = poly_parts[0] if len(poly_parts) == 1 else MultiPolygon(poly_parts)
            else:
                continue

            seg_acres = calculate_acreage(seg_shape)
            if seg_acres <= 0.001:
                continue

            segments.append(
                {
                    "segment_id": f"segment_{i}",
                    "state_fips": county["state_fips"],
                    "county_fips": county["county_fips"],
                    "county_name": county["county_name"],
                    "geometry": seg_shape,
                    "calculated_acres": seg_acres,
                }
            )

        return segments
