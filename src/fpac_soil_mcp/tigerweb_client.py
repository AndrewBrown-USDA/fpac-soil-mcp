"""Census TIGERweb 2020 Urban Areas MapServer Layer 0 REST client.

Screens geographic coordinates and polygon footprints against Census 2020 Urban Area
boundaries for preliminary statutory exemption review under 7 CFR § 658.2(a).
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any, TypedDict

import httpx
from shapely.errors import GEOSException
from shapely.geometry import (
    GeometryCollection,
    LinearRing,
    LineString,
    MultiLineString,
    MultiPolygon,
    Point,
    Polygon,
)
from shapely.ops import unary_union
from shapely.validation import make_valid

from fpac_soil_mcp.authority import Provenance
from fpac_soil_mcp.config import settings
from fpac_soil_mcp.geometry import (
    GeometryValidationError,
    calculate_acreage,
    calculate_geodesic_length,
    compute_geometry_hash,
    normalize_ring_winding,
    parse_geojson_geometry,
)
from fpac_soil_mcp.geometry import polygon_to_esri_rings as _polygon_to_esri_rings
from fpac_soil_mcp.http_client import (
    HttpRequestError,
    HttpStatusError,
    execute_http_request_with_retry,
)
from fpac_soil_mcp.integration_models import (
    CountyPartitionGeometry,
    IntegrationStatus,
    UrbanExemptionRecord,
)

logger = logging.getLogger(__name__)


def _normalize_ring_winding(ring: LinearRing, clockwise: bool = True) -> list[list[float]]:
    """Preserve the historical TIGERweb helper name for callers and tests."""
    return normalize_ring_winding(ring, clockwise=clockwise)


# Default TIGERweb State and County Boundaries MapServer (Layer 1: Counties)
DEFAULT_TIGERWEB_COUNTY_URL = (
    "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer/1"
)


def _lineal_parts(geom: Any) -> list[LineString | MultiLineString]:
    """Extract lineal components from a boundary intersection."""
    if isinstance(geom, (LineString, MultiLineString)):
        return [geom]
    if isinstance(geom, GeometryCollection):
        parts: list[LineString | MultiLineString] = []
        for component in geom.geoms:
            parts.extend(_lineal_parts(component))
        return parts
    return []


def _esri_rings_to_geometry(
    rings: list[list[list[float]]],
) -> Polygon | MultiPolygon | None:
    """Reconstruct Shapely Polygon or MultiPolygon from ArcGIS REST JSON rings.

    According to the ArcGIS REST API polygon specification:
    - Exterior rings are oriented clockwise (CW, where LinearRing.is_ccw is False).
    - Interior rings (holes) are oriented counterclockwise (CCW, where LinearRing.is_ccw is True).

    This function separates exterior rings from interior hole rings and assigns each
    hole to the exterior ring that geometrically contains it. If standard winding
    order is not observed (e.g. all rings have the same winding), it falls back to
    containment-based exterior/hole classification or single-ring polygons.

    Args:
        rings: List of coordinate rings from an ArcGIS geometry dictionary.

    Returns:
        Shapely Polygon, MultiPolygon, or None if no valid geometry could be created.
    """
    if not rings:
        return None

    linear_rings: list[LinearRing] = []
    for ring_coords in rings:
        if len(ring_coords) >= 4:
            try:
                lr = LinearRing(ring_coords)
                if lr.is_valid and not lr.is_empty:
                    linear_rings.append(lr)
            except (ValueError, GEOSException) as exc:
                logger.debug("Skipping invalid LinearRing coordinates: %s", exc)

    if not linear_rings:
        return None

    # Classify by winding order
    # ArcGIS convention: CW = exterior (not is_ccw), CCW = hole (is_ccw)
    exteriors = [r for r in linear_rings if not r.is_ccw]
    holes = [r for r in linear_rings if r.is_ccw]

    # Fallback if winding is non-standard (e.g. all CCW or all CW)
    # If all rings share the same orientation, classify exterior vs hole using geometric containment
    if not exteriors or (len(linear_rings) > 1 and not holes):
        temp_polys = [(Polygon(r), r) for r in linear_rings]
        # Sort by area descending
        temp_polys.sort(key=lambda p: p[0].area, reverse=True)

        assigned_exteriors: list[LinearRing] = []
        assigned_holes: list[LinearRing] = []

        for poly, ring in temp_polys:
            # If ring is contained inside any already assigned exterior, it's a hole
            is_contained = any(Polygon(ext).contains(poly) for ext in assigned_exteriors)
            if is_contained:
                assigned_holes.append(ring)
            else:
                assigned_exteriors.append(ring)

        exteriors = assigned_exteriors
        holes = assigned_holes

    # Group holes with their containing exterior ring
    poly_list: list[Polygon] = []
    exterior_polys = [Polygon(ext) for ext in exteriors]
    exterior_holes: list[list[LinearRing]] = [[] for _ in exteriors]

    for hole in holes:
        hole_poly = Polygon(hole)
        # Find which exterior polygon contains this hole
        matched = False
        for idx, ext_poly in enumerate(exterior_polys):
            if ext_poly.contains(hole_poly):
                exterior_holes[idx].append(hole)
                matched = True
                break
        if not matched:
            # If hole is not strictly contained by any exterior (e.g. touches boundary or disjoint),
            # check intersection or envelope containment, otherwise treat as separate exterior
            for idx, ext_poly in enumerate(exterior_polys):
                if ext_poly.intersects(hole_poly) and not ext_poly.equals(hole_poly):
                    exterior_holes[idx].append(hole)
                    matched = True
                    break
            if not matched:
                # If truly standalone, promote to an exterior polygon
                poly_list.append(Polygon(hole))

    for ext_ring, h_list in zip(exteriors, exterior_holes):
        poly_list.append(Polygon(shell=ext_ring, holes=h_list if h_list else None))

    valid_polys = []
    for p in poly_list:
        if not p.is_valid:
            fixed = make_valid(p)
            if isinstance(fixed, (Polygon, MultiPolygon)):
                if isinstance(fixed, Polygon):
                    valid_polys.append(fixed)
                else:
                    valid_polys.extend([g for g in fixed.geoms if isinstance(g, Polygon)])
        else:
            valid_polys.append(p)

    if not valid_polys:
        return None
    if len(valid_polys) == 1:
        return valid_polys[0]
    return MultiPolygon(valid_polys)


def _polygonal_parts(geometry: Any) -> list[Polygon]:
    """Extract polygon members from a polygonal or collection geometry."""
    if isinstance(geometry, Polygon):
        return [geometry]
    if isinstance(geometry, MultiPolygon):
        return list(geometry.geoms)
    if isinstance(geometry, GeometryCollection):
        parts: list[Polygon] = []
        for member in geometry.geoms:
            parts.extend(_polygonal_parts(member))
        return parts
    return []


class TigerwebClientError(Exception):
    """Base exception for Census TIGERweb client errors."""


class PerimeterEvidence(TypedDict):
    """Preliminary Criterion 2 perimeter evidence from TIGERweb."""

    normalized_ratio: float | None
    evidence_status: str
    rule_reference: str
    rule_version: str
    source_provenance: list[str]
    is_verified: bool
    geometry_hash: str
    total_perimeter_meters: float | None
    urban_adjacent_perimeter_meters: float | None
    error_message: str | None


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
                "returnGeometry": "false" if isinstance(geom, Point) else "true",
                "outSR": "4326",
                "f": "json",
            }

            query_url = (
                f"{self.base_url}/query" if not self.base_url.endswith("/query") else self.base_url
            )

            resp = execute_http_request_with_retry(
                "POST", query_url, data=params, timeout=self.timeout, client=self._http_client
            )
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
            screened_acreage: float | None = None
            if not isinstance(geom, Point):
                urban_geometries: list[Polygon | MultiPolygon] = []
                for feature in features:
                    feature_rings = feature.get("geometry", {}).get("rings", [])
                    urban_geometry = _esri_rings_to_geometry(feature_rings)
                    if urban_geometry is not None and not urban_geometry.is_empty:
                        urban_geometries.append(urban_geometry)

                if urban_geometries:
                    urban_union = unary_union(urban_geometries)
                    overlap = geom.intersection(urban_union)
                    if not overlap.is_empty:
                        if not overlap.is_valid:
                            overlap = make_valid(overlap)
                        polygon_parts = _polygonal_parts(overlap)
                        if polygon_parts:
                            screened_acreage = calculate_acreage(unary_union(polygon_parts))
                if screened_acreage is None:
                    screened_acreage = 0.0

            return UrbanExemptionRecord(
                status=IntegrationStatus.SUCCESS,
                geometry_hash=geom_hash,
                provenance=provenance,
                source_layer="2020 Urban Areas",
                layer_version="2020",
                is_urban_intersected=is_intersected,
                urban_area_names=urban_names,
                screened_acreage=screened_acreage,
            )

        except (
            HttpRequestError,
            HttpStatusError,
            GeometryValidationError,
            ValueError,
            KeyError,
        ) as exc:
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

    def get_perimeter_evidence(
        self,
        geometry_input: dict[str, Any] | str | Polygon | MultiPolygon,
    ) -> PerimeterEvidence:
        """Return preliminary non-urban perimeter evidence for Criterion 2."""
        from fpac_soil_mcp.constants import CRITERION_2_RULE_REFERENCE, CRITERION_2_RULE_VERSION

        provenance = [f"US Census Bureau TIGERweb 2020 Urban Areas MapServer: {self.base_url}"]
        fallback_hash = "sha256:" + "0" * 64
        try:
            if isinstance(geometry_input, (Polygon, MultiPolygon)):
                geom = geometry_input
            else:
                geom = parse_geojson_geometry(geometry_input)
            geom_hash = compute_geometry_hash(geom)
            total = calculate_geodesic_length(geom.boundary)
            if total <= 0.0:
                raise GeometryValidationError("Geometry perimeter must be positive.")

            params = {
                "geometry": json.dumps({"rings": _polygon_to_esri_rings(geom)}),
                "geometryType": "esriGeometryPolygon",
                "inSR": "4326",
                "spatialRel": "esriSpatialRelIntersects",
                "outFields": "GEOID,NAME,BASENAME",
                "returnGeometry": "true",
                "outSR": "4326",
                "f": "json",
            }
            query_url = (
                f"{self.base_url}/query" if not self.base_url.endswith("/query") else self.base_url
            )
            resp = execute_http_request_with_retry(
                "POST", query_url, data=params, timeout=self.timeout, client=self._http_client
            )
            data = resp.json()
            if "error" in data:
                return {
                    "normalized_ratio": None,
                    "evidence_status": "error",
                    "rule_reference": CRITERION_2_RULE_REFERENCE,
                    "rule_version": CRITERION_2_RULE_VERSION,
                    "source_provenance": provenance,
                    "is_verified": False,
                    "geometry_hash": geom_hash,
                    "total_perimeter_meters": total,
                    "urban_adjacent_perimeter_meters": None,
                    "error_message": f"TIGERweb MapServer error: {data['error'].get('message', 'Unknown error')}",
                }

            features = data.get("features")
            if not isinstance(features, list):
                return {
                    "normalized_ratio": None,
                    "evidence_status": "unavailable",
                    "rule_reference": CRITERION_2_RULE_REFERENCE,
                    "rule_version": CRITERION_2_RULE_VERSION,
                    "source_provenance": provenance,
                    "is_verified": False,
                    "geometry_hash": geom_hash,
                    "total_perimeter_meters": total,
                    "urban_adjacent_perimeter_meters": None,
                    "error_message": "TIGERweb response omitted a valid features list.",
                }
            urban_geometries = []
            for feature in features:
                if not isinstance(feature, dict):
                    continue
                feature_geometry = feature.get("geometry")
                if not isinstance(feature_geometry, dict):
                    continue
                rings = feature_geometry.get("rings", [])
                parsed = _esri_rings_to_geometry(rings)
                if parsed is not None and not parsed.is_empty:
                    urban_geometries.append(parsed)
            if features and not urban_geometries:
                status = "unavailable"
                error = "TIGERweb returned intersecting features without usable geometry."
                ratio = None
                adjacent = None
            else:
                urban_union = unary_union(urban_geometries) if urban_geometries else None
                adjacent_geom = geom.boundary.intersection(urban_union) if urban_union else None
                adjacent = sum(
                    calculate_geodesic_length(part)
                    for part in _lineal_parts(adjacent_geom)
                    if not part.is_empty
                )
                ratio = max(0.0, min(1.0, 1.0 - (adjacent / total)))
                status = "measured"
                error = None
            return {
                "normalized_ratio": ratio,
                "evidence_status": status,
                "rule_reference": CRITERION_2_RULE_REFERENCE,
                "rule_version": CRITERION_2_RULE_VERSION,
                "source_provenance": provenance,
                "is_verified": status == "measured",
                "geometry_hash": geom_hash,
                "total_perimeter_meters": total,
                "urban_adjacent_perimeter_meters": adjacent,
                "error_message": error,
            }
        except (
            HttpRequestError,
            HttpStatusError,
            GeometryValidationError,
            ValueError,
            KeyError,
        ) as exc:
            return {
                "normalized_ratio": None,
                "evidence_status": "error",
                "rule_reference": CRITERION_2_RULE_REFERENCE,
                "rule_version": CRITERION_2_RULE_VERSION,
                "source_provenance": provenance,
                "is_verified": False,
                "geometry_hash": compute_geometry_hash(geometry_input)
                if isinstance(geometry_input, (Polygon, MultiPolygon))
                else fallback_hash,
                "total_perimeter_meters": None,
                "urban_adjacent_perimeter_meters": None,
                "error_message": f"Perimeter evidence failed: {exc}",
            }

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

            resp = execute_http_request_with_retry(
                "POST", query_url, data=params, timeout=self.timeout, client=self._http_client
            )
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

                # Reconstruct Shapely Polygon/MultiPolygon from ESRI rings respecting winding and holes
                county_shape = _esri_rings_to_geometry(rings)

                if county_shape is None or county_shape.is_empty:
                    continue

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

        except (HttpRequestError, HttpStatusError, ValueError, KeyError) as exc:
            logger.error("Failed to query intersecting counties from TIGERweb: %s", exc)
            return []

    def partition_geometry_by_counties(
        self,
        geometry_input: dict[str, Any] | str | Polygon | MultiPolygon,
        counties: list[dict[str, Any]] | None = None,
    ) -> list[CountyPartitionGeometry]:
        """Spatially intersect and partition a project footprint into county segments.

        Args:
            geometry_input: GeoJSON dict/string or Shapely Polygon/MultiPolygon.
            counties: Optional pre-fetched county features list. If None, queries TIGERweb.

        Returns:
            List of CountyPartitionGeometry records containing:
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
                CountyPartitionGeometry(
                    state_fips="00",
                    county_fips="000",
                    county_name="Unsegmented Area",
                    state_name=None,
                    geometry=geom,
                    calculated_acres=calculate_acreage(geom),
                )
            ]

        segments: list[CountyPartitionGeometry] = []
        for county in counties:
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
                CountyPartitionGeometry(
                    state_fips=county["state_fips"],
                    county_fips=county["county_fips"],
                    county_name=county["county_name"],
                    state_name=county.get("state_name"),
                    geometry=seg_shape,
                    calculated_acres=seg_acres,
                )
            )

        return segments
