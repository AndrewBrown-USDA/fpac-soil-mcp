"""Polygon AOI Screening and Farmland Analysis Engine.

Orchestrates geometry validation, geodesic equal-area acreage calculation, Census 2020 Urban Area
screening, SDA spatial soil intersection, NCCPI interpretation fetching, and tabular summary generation.
"""

from __future__ import annotations

import csv
import io
import logging
from datetime import UTC, datetime
from typing import Any

from shapely.geometry import MultiPolygon, Polygon

from fpac_soil_mcp.constants import (
    REGULATORY_LIMITATIONS,
    REGULATORY_NOTICE,
)
from fpac_soil_mcp.geometry import (
    GeometryValidationError,
    calculate_acreage,
    compute_geometry_hash,
    geometry_to_wkt,
    parse_geojson_geometry,
)
from fpac_soil_mcp.models import (
    FarmlandCategoryBreakdown,
    PolygonFarmlandAnalysisResponse,
    QuerySource,
    SoilMapUnitAcreage,
)
from fpac_soil_mcp.sda_client import SDAClient, SDAClientError
from fpac_soil_mcp.tigerweb_client import TigerwebClient

logger = logging.getLogger(__name__)


def categorize_farmland_class(farmlndcl: str | None) -> str:
    """Classify a SSURGO farmlndcl string into normalized category key."""
    if not farmlndcl:
        return "unmapped"

    desc = farmlndcl.strip().lower()
    if desc == "all areas are prime farmland":
        return "prime"
    if "prime farmland if" in desc:
        return "conditional_prime"
    if "statewide importance" in desc:
        return "statewide"
    if "local importance" in desc:
        return "local"
    if "unique importance" in desc or "unique farmland" in desc:
        return "unique"
    if "not prime farmland" in desc:
        return "not_prime"
    return "not_prime"


class PolygonAnalyzer:
    """Coordinates spatial validation, external data retrieval, and farmland analysis for polygon AOIs."""

    def __init__(
        self,
        sda_client: SDAClient | None = None,
        tigerweb_client: TigerwebClient | None = None,
    ) -> None:
        self.sda_client = sda_client or SDAClient()
        self.tigerweb_client = tigerweb_client or TigerwebClient()

    def analyze_polygon(
        self,
        geojson_input: dict[str, Any] | str | Polygon | MultiPolygon,
        include_nccpi: bool = True,
    ) -> PolygonFarmlandAnalysisResponse:
        """Execute full farmland screening on a polygon or multipolygon AOI.

        Args:
            geojson_input: GeoJSON dict/string or Shapely geometry.
            include_nccpi: Whether to retrieve component-weighted NCCPI v3 interpretations.

        Returns:
            PolygonFarmlandAnalysisResponse with complete acreage breakdowns, urban screening, and provenance.
        """
        now = datetime.now(UTC)
        timestamp_str = now.isoformat()

        # 1. Parse and validate geometry
        try:
            if isinstance(geojson_input, (Polygon, MultiPolygon)):
                geom = geojson_input
            else:
                geom = parse_geojson_geometry(geojson_input)
        except GeometryValidationError as exc:
            return PolygonFarmlandAnalysisResponse(
                query_type="polygon",
                geometry_hash="sha256:0000000000000000000000000000000000000000000000000000000000000000",
                total_aoi_acres=0.0,
                coverage_status="invalid_request",
                urban_screening={"status": "error", "error": str(exc)},
                farmland_summary=FarmlandCategoryBreakdown(),
                map_units=[],
                tabular_csv="",
                source=QuerySource(
                    endpoint=self.sda_client.base_url,
                    timestamp_utc=timestamp_str,
                ),
                limitations=[*REGULATORY_LIMITATIONS, f"Geometry validation error: {exc}"],
                regulatory_notice=REGULATORY_NOTICE,
            )

        geom_hash = compute_geometry_hash(geom)
        total_acres = calculate_acreage(geom)
        wkt_str = geometry_to_wkt(geom)

        # 2. Census Urban Area Pre-Screening
        urban_rec = self.tigerweb_client.check_urban_exemption(geom)
        urban_dict = urban_rec.model_dump(mode="json")

        # 3. SDA Spatial Intersection Query with Exact Clipping
        raw_units: list[dict[str, Any]] = []
        limitations = list(REGULATORY_LIMITATIONS)
        try:
            raw_units = self.sda_client.get_spatial_intersection(
                wkt_str,
                clip=True,
                geom_acres=True,
                return_geom=False,
            )
        except SDAClientError as exc:
            logger.error("SDA spatial query failed: %s", exc)
            limitations.append(f"SDA spatial query error: {exc}")

        # 4. Ingest Interpretations (NCCPI v3) if requested
        mukeys = list({str(r.get("mukey")) for r in raw_units if r.get("mukey")})
        interp_map: dict[str, dict[str, Any]] = {}
        if include_nccpi and mukeys:
            try:
                interp_rows = self.sda_client.get_interpretations(
                    mukeys=mukeys,
                    rule_name="NCCPI - National Commodity Crop Productivity Index (Ver 3.0)",
                    aggregation_method="Weighted Average",
                )
                for irow in interp_rows:
                    mukey_val = str(irow.get("mukey"))
                    interp_map[mukey_val] = irow
            except SDAClientError as exc:
                logger.warning("NCCPI interpretation query failed: %s", exc)
                limitations.append(f"NCCPI interpretation warning: {exc}")

        # 5. Build Map Unit Acreage models
        # Group spatial intersection fragments by mukey, summing exact clipped acreage
        unit_models: list[SoilMapUnitAcreage] = []
        grouped_units: dict[str, dict[str, Any]] = {}
        for u in raw_units:
            mukey_str = str(u.get("mukey", ""))
            if not mukey_str:
                continue
            if mukey_str not in grouped_units:
                grouped_units[mukey_str] = {
                    "mukey": mukey_str,
                    "musym": u.get("musym"),
                    "muname": u.get("muname"),
                    "farmlndcl": u.get("farmlndcl"),
                    "areasymbol": u.get("areasymbol"),
                    "area_ac": 0.0,
                }
            try:
                raw_area = float(u.get("area_ac") or 0.0)
            except (ValueError, TypeError):
                raw_area = 0.0
            grouped_units[mukey_str]["area_ac"] += raw_area

        category_acres: dict[str, float] = {
            "prime": 0.0,
            "conditional_prime": 0.0,
            "statewide": 0.0,
            "local": 0.0,
            "unique": 0.0,
            "not_prime": 0.0,
            "unmapped": 0.0,
        }

        total_mapped_acres = 0.0
        for mukey_str, u in grouped_units.items():
            farmlndcl_str = u.get("farmlndcl")
            calc_ac = round(u["area_ac"], 2)
            total_mapped_acres += calc_ac
            pct = round((calc_ac / total_acres * 100.0) if total_acres > 0 else 0.0, 2)

            interp_info = interp_map.get(mukey_str, {})
            cat = categorize_farmland_class(farmlndcl_str)
            category_acres[cat] += calc_ac

            numeric_rating = interp_info.get("numeric_rating")
            if numeric_rating is not None:
                try:
                    numeric_rating = float(numeric_rating)
                except (ValueError, TypeError):
                    numeric_rating = None

            unit_models.append(
                SoilMapUnitAcreage(
                    mukey=mukey_str,
                    musym=u.get("musym"),
                    muname=u.get("muname"),
                    farmlndcl=farmlndcl_str,
                    areasymbol=u.get("areasymbol"),
                    calculated_acres=calc_ac,
                    percentage_of_aoi=pct,
                    nccpi_rating=numeric_rating,
                    nccpi_class=interp_info.get("rating_class"),
                )
            )

        # Handle any unmapped remainder / slivers
        unmapped_remainder = max(0.0, round(total_acres - total_mapped_acres, 2))
        category_acres["unmapped"] += unmapped_remainder

        # Compute summary percentages
        def _pct(val: float) -> float:
            return round((val / total_acres * 100.0) if total_acres > 0 else 0.0, 2)

        protected_acres = (
            category_acres["prime"]
            + category_acres["conditional_prime"]
            + category_acres["statewide"]
            + category_acres["local"]
            + category_acres["unique"]
        )

        summary = FarmlandCategoryBreakdown(
            prime_farmland_acres=round(category_acres["prime"], 2),
            prime_farmland_pct=_pct(category_acres["prime"]),
            conditional_prime_acres=round(category_acres["conditional_prime"], 2),
            conditional_prime_pct=_pct(category_acres["conditional_prime"]),
            statewide_importance_acres=round(category_acres["statewide"], 2),
            statewide_importance_pct=_pct(category_acres["statewide"]),
            local_importance_acres=round(category_acres["local"], 2),
            local_importance_pct=_pct(category_acres["local"]),
            unique_farmland_acres=round(category_acres["unique"], 2),
            unique_farmland_pct=_pct(category_acres["unique"]),
            not_prime_acres=round(category_acres["not_prime"], 2),
            not_prime_pct=_pct(category_acres["not_prime"]),
            unmapped_acres=round(category_acres["unmapped"], 2),
            unmapped_pct=_pct(category_acres["unmapped"]),
            total_fppa_protected_acres=round(protected_acres, 2),
            total_fppa_protected_pct=_pct(protected_acres),
        )

        if not unit_models:
            coverage_status = "unmapped"
        elif unmapped_remainder > 0.0:
            coverage_status = "partially_covered"
        else:
            coverage_status = "covered"

        # 6. Generate CSV table
        output_io = io.StringIO()
        writer = csv.writer(output_io)
        writer.writerow(
            [
                "mukey",
                "musym",
                "muname",
                "farmlndcl",
                "areasymbol",
                "acres",
                "pct_of_aoi",
                "nccpi_rating",
                "nccpi_class",
            ]
        )
        for um in unit_models:
            writer.writerow(
                [
                    um.mukey,
                    um.musym or "",
                    um.muname or "",
                    um.farmlndcl or "",
                    um.areasymbol or "",
                    um.calculated_acres,
                    um.percentage_of_aoi,
                    um.nccpi_rating if um.nccpi_rating is not None else "",
                    um.nccpi_class or "",
                ]
            )
        csv_str = output_io.getvalue()

        # 7. Build Execution Manifest
        manifest = {
            "execution_timestamp_utc": timestamp_str,
            "geometry_hash": geom_hash,
            "total_aoi_acres": total_acres,
            "mapped_soil_units_count": len(unit_models),
            "spatial_clipping_engine": "USDA NRCS SDA STIntersection / STArea",
            "interpretation_rule": "NCCPI - National Commodity Crop Productivity Index (Ver 3.0)",
            "urban_screening_layer": "Census 2020 Urban Areas Layer 0",
            "statutory_authority": "Farmland Protection Policy Act (7 U.S.C. 4201 et seq., 7 CFR Part 658)",
        }

        return PolygonFarmlandAnalysisResponse(
            query_type="polygon",
            geometry_hash=geom_hash,
            total_aoi_acres=total_acres,
            coverage_status=coverage_status,
            urban_screening=urban_dict,
            farmland_summary=summary,
            map_units=unit_models,
            tabular_csv=csv_str,
            manifest=manifest,
            source=QuerySource(
                endpoint=self.sda_client.base_url,
                timestamp_utc=timestamp_str,
            ),
            limitations=limitations,
            regulatory_notice=REGULATORY_NOTICE,
        )
