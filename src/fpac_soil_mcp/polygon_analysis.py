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

from fpac_soil_mcp.config import settings
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
from fpac_soil_mcp.lesa import _normalize_productivity_index
from fpac_soil_mcp.map_contract import (
    NEUTRAL_OUTLINE_COLOR,
    URBAN_CONTEXT_COLOR,
    MapBlock,
    build_layer,
    build_map_block,
    farmland_legend,
    features_from_sda_rows,
    productivity_by_mukey,
    single_legend,
    with_productivity,
)
from fpac_soil_mcp.models import (
    SUPPORTED_INDEX_MSG,
    VALIDATED_PRODUCTIVITY_INDEXES,
    FarmlandCategoryBreakdown,
    LandEvaluationSummary,
    PolygonFarmlandAnalysisResponse,
    QuerySource,
    SoilMapUnitAcreage,
)
from fpac_soil_mcp.sda_client import (
    PRODUCTIVITY_PROVENANCE,
    PRODUCTIVITY_SEMANTICS,
    SDAClient,
    SDAClientError,
)
from fpac_soil_mcp.tigerweb_client import TigerwebClient

logger = logging.getLogger(__name__)

_UNRATED_SENTINELS = {99.0, 999.0, -99.0, -999.0}


def _normalize_numeric_rating(value: Any, productivity_index: str = "nccpi") -> float | None:
    """Return a usable productivity rating, excluding SDA sentinel values."""
    try:
        rating = float(value) if value is not None else None
    except (ValueError, TypeError):
        return None
    sentinels = PRODUCTIVITY_SEMANTICS.get(productivity_index, {}).get(
        "sentinels", _UNRATED_SENTINELS
    )
    if rating is None or rating in sentinels:
        return None
    return rating


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
        productivity_index: str = "nccpi",
        max_county_rating_override: float | None = None,
        include_map: bool = False,
    ) -> PolygonFarmlandAnalysisResponse:
        """Execute full farmland screening on a polygon or multipolygon AOI.

        Args:
            geojson_input: GeoJSON dict/string or Shapely geometry.
            include_nccpi: Whether to retrieve component-weighted interpretations.
            productivity_index: Soil productivity index type ('nccpi', 'csr2', 'cpi', 'storie').
            max_county_rating_override: Optional user-supplied maximum county rating benchmark.
            include_map: Include display geometry in the ``map`` layers (ADR 0017).
                Numbers are computed from exact geometry either way.

        Returns:
            PolygonFarmlandAnalysisResponse with complete acreage breakdowns, urban screening, LE summary, and provenance.
        """
        now = datetime.now(UTC)
        timestamp_str = now.isoformat()

        idx_enum = _normalize_productivity_index(productivity_index)
        if idx_enum not in VALIDATED_PRODUCTIVITY_INDEXES:
            raise ValueError(
                f"Unsupported productivity index type '{productivity_index}'. {SUPPORTED_INDEX_MSG}"
            )
        norm_idx = idx_enum.value.lower()

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
                map=self._polygon_map(False, None, [], []),
            )

        geom_hash = compute_geometry_hash(geom)
        total_acres = calculate_acreage(geom)
        wkt_str = geometry_to_wkt(geom)

        # 2. Census Urban Area Pre-Screening
        urban_rec, urban_geometries = self.tigerweb_client.check_urban_exemption_with_geometries(
            geom
        )
        urban_dict = urban_rec.model_dump(mode="json")
        perimeter_evidence = self.tigerweb_client.get_perimeter_evidence(geom)

        # 3. SDA Spatial Intersection Query with Exact Clipping
        raw_units: list[dict[str, Any]] = []
        limitations = list(REGULATORY_LIMITATIONS)
        try:
            raw_units = self.sda_client.get_spatial_intersection(
                wkt_str,
                clip=True,
                geom_acres=True,
                return_geom=include_map,
            )
        except SDAClientError as exc:
            logger.error("SDA spatial query failed: %s", exc)
            limitations.append(f"SDA spatial query error: {exc}")

        # 4. Ingest Productivity Ratings if requested
        mukeys = list({str(r.get("mukey")) for r in raw_units if r.get("mukey")})
        rating_map: dict[str, dict[str, Any]] = {}
        ratings_requested = include_nccpi or norm_idx != "nccpi"
        if ratings_requested and mukeys:
            if norm_idx == "nccpi":
                try:
                    interp_rows = self.sda_client.get_interpretations(
                        mukeys=mukeys,
                        rule_name="NCCPI - National Commodity Crop Productivity Index (Ver 3.0)",
                        aggregation_method="Weighted Average",
                    )
                    for irow in interp_rows:
                        mukey_val = str(irow.get("mukey"))
                        num_r = irow.get("numeric_rating")
                        parsed_num_r = _normalize_numeric_rating(num_r, norm_idx)
                        rating_map[mukey_val] = {
                            "mukey": mukey_val,
                            "numeric_rating": parsed_num_r,
                            "rating_class": irow.get("rating_class"),
                            "productivity_rating_source": (
                                "NCCPI - National Commodity Crop Productivity Index (Ver 3.0)"
                            ),
                            "rated_pct": irow.get("rated_pct"),
                            "total_pct": irow.get("total_pct"),
                            "is_rated": parsed_num_r is not None,
                            "caveats": [],
                        }
                except SDAClientError as exc:
                    logger.warning("NCCPI interpretation query failed: %s", exc)
                    limitations.append(f"NCCPI interpretation warning: {exc}")
            else:
                try:
                    prod_ratings = self.sda_client.get_productivity_ratings(
                        mukeys=mukeys,
                        index_type=norm_idx,
                    )
                    for pr in prod_ratings:
                        mukey_val = str(pr.get("mukey"))
                        rating_map[mukey_val] = dict(pr)
                except SDAClientError as exc:
                    logger.warning("Productivity rating query failed (%s): %s", norm_idx, exc)
                    limitations.append(f"Productivity rating warning ({norm_idx}): {exc}")

        # Determine county max benchmark
        county_max = max_county_rating_override
        partition_max: dict[str, float] = {}
        if ratings_requested and county_max is None and raw_units:
            areasymbols = {
                str(u.get("areasymbol")).strip() for u in raw_units if u.get("areasymbol")
            }
            for areasymbol in areasymbols:
                try:
                    benchmark = self.sda_client.get_county_max_productivity_rating(
                        areasymbol=areasymbol,
                        index_type="nccpi" if norm_idx == "nccpi" else norm_idx,
                    )
                    if benchmark is not None and benchmark > 0:
                        partition_max[areasymbol] = float(benchmark)
                except SDAClientError as exc:
                    logger.warning("County max rating query failed for %s: %s", areasymbol, exc)
                    limitations.append(f"County max rating query warning: {exc}")

        default_county_max = 1.0 if norm_idx == "nccpi" else 100.0
        if county_max is not None and county_max > 0:
            default_county_max = float(county_max)
        county_max = default_county_max

        # 5. Build Map Unit Acreage models & compute LE scores
        unit_models: list[SoilMapUnitAcreage] = []
        grouped_units: dict[tuple[str, str], dict[str, Any]] = {}
        for u in raw_units:
            mukey_str = str(u.get("mukey", ""))
            if not mukey_str:
                continue
            areasymbol = str(u.get("areasymbol") or "").strip()
            unit_key = (mukey_str, areasymbol)
            if unit_key not in grouped_units:
                grouped_units[unit_key] = {
                    "mukey": mukey_str,
                    "musym": u.get("musym"),
                    "muname": u.get("muname"),
                    "farmlndcl": u.get("farmlndcl"),
                    "areasymbol": areasymbol or None,
                    "area_ac": 0.0,
                }
            try:
                raw_area = float(u.get("area_ac") or 0.0)
            except (ValueError, TypeError):
                raw_area = 0.0
            grouped_units[unit_key]["area_ac"] += raw_area

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
        rated_le_acres = 0.0
        weighted_rr_sum = 0.0
        unrated_le_acres = 0.0
        le_notices: list[str] = []

        for (mukey_str, areasymbol), u in grouped_units.items():
            farmlndcl_str = u.get("farmlndcl")
            calc_ac = round(u["area_ac"], 2)
            total_mapped_acres += calc_ac
            pct = round((calc_ac / total_acres * 100.0) if total_acres > 0 else 0.0, 2)

            rating_info = rating_map.get(mukey_str, {})
            cat = categorize_farmland_class(farmlndcl_str)
            category_acres[cat] += calc_ac

            numeric_rating = _normalize_numeric_rating(rating_info.get("numeric_rating"), norm_idx)

            is_rated = rating_info.get(
                "is_rated", numeric_rating is not None and numeric_rating >= 0
            )
            if is_rated and numeric_rating is not None and numeric_rating >= 0:
                benchmark = partition_max.get(areasymbol, county_max)
                rel_rating = min(1.0, max(0.0, numeric_rating / benchmark))
                rated_le_acres += calc_ac
                weighted_rr_sum += rel_rating * calc_ac
            else:
                unrated_le_acres += calc_ac

            for cav in rating_info.get("caveats", []):
                if cav not in le_notices:
                    le_notices.append(cav)

            unit_models.append(
                SoilMapUnitAcreage(
                    mukey=mukey_str,
                    musym=u.get("musym"),
                    muname=u.get("muname"),
                    farmlndcl=farmlndcl_str,
                    areasymbol=u.get("areasymbol"),
                    calculated_acres=calc_ac,
                    percentage_of_aoi=pct,
                    productivity_rating=numeric_rating,
                    productivity_rating_class=(
                        None if numeric_rating is None else rating_info.get("rating_class")
                    ),
                    productivity_rating_source=rating_info.get("productivity_rating_source")
                    or PRODUCTIVITY_PROVENANCE.get(norm_idx),
                )
            )

        # Handle any unmapped remainder / slivers
        unmapped_remainder = max(0.0, round(total_acres - total_mapped_acres, 2))
        category_acres["unmapped"] += unmapped_remainder
        unrated_le_acres += unmapped_remainder

        # Compute Land Evaluation summary metrics
        rated_le_acres = round(rated_le_acres, 2)
        unrated_le_acres = round(unrated_le_acres, 2)
        if rated_le_acres > 0:
            aoi_rr = round(weighted_rr_sum / rated_le_acres, 4)
            candidate_le = round(aoi_rr * 100.0, 2)
            cov_pct = round((rated_le_acres / total_acres * 100.0) if total_acres > 0 else 0.0, 2)
        else:
            aoi_rr = None
            candidate_le = None
            cov_pct = 0.0

        if county_max != (1.0 if norm_idx == "nccpi" else 100.0):
            le_notices.append(
                f"Normalized against county max {norm_idx.upper()} benchmark of {county_max}."
            )
        if unrated_le_acres > 0:
            le_notices.append(
                f"Partial productivity coverage: {rated_le_acres:.2f} rated acres ({cov_pct}%), {unrated_le_acres:.2f} unrated acres excluded from Land Evaluation weighting."
            )

        le_summary = LandEvaluationSummary(
            productivity_index=idx_enum,
            aoi_relative_rating=(min(1.0, max(0.0, aoi_rr)) if aoi_rr is not None else None),
            candidate_le_score=(
                min(100.0, max(0.0, candidate_le)) if candidate_le is not None else None
            ),
            county_farmland_percentile_higher=None,
            rated_acreage=rated_le_acres,
            unrated_acreage=unrated_le_acres,
            total_acreage=round(total_acres, 2),
            coverage_percent=min(100.0, max(0.0, cov_pct)),
            rating_source_provenance=[
                PRODUCTIVITY_PROVENANCE.get(norm_idx, f"SDA:{norm_idx.upper()}")
            ],
            notices=le_notices,
        )

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
        le_coverage_status = (
            "unknown"
            if total_acres <= 0
            else "unmapped"
            if not unit_models
            else "unrated"
            if rated_le_acres <= 0
            else "covered"
            if rated_le_acres >= total_acres
            else "partial"
        )
        le_summary.coverage_status = le_coverage_status

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
                "productivity_rating",
                "productivity_rating_class",
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
                    um.productivity_rating if um.productivity_rating is not None else "",
                    um.productivity_rating_class or "",
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
            "interpretation_rule": f"Productivity Index: {idx_enum.value} ({norm_idx})",
            "productivity_index": idx_enum.value,
            "county_max_rating": county_max,
            "candidate_le_score": le_summary.candidate_le_score,
            "urban_screening_layer": "Census 2020 Urban Areas Layer 0",
            "criterion_2_perimeter_evidence": perimeter_evidence,
            "statutory_authority": "Farmland Protection Policy Act (7 U.S.C. 4201 et seq., 7 CFR Part 658)",
            "land_evaluation": le_summary.model_dump(mode="json"),
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
            map=self._polygon_map(
                include_map,
                geom,
                with_productivity(raw_units, productivity_by_mukey(unit_models, rating_map)),
                urban_geometries,
            ),
        )

    @staticmethod
    def _polygon_map(
        include_map: bool,
        geom: Polygon | MultiPolygon | None,
        raw_units: list[dict[str, Any]],
        urban_geometries: list[tuple[str, Polygon | MultiPolygon]],
    ) -> MapBlock:
        """Build the ADR 0017 map block; geometry only when ``include_map`` is true.

        Layer order is the size-cap drop priority: urban context first, then
        farmland classes; the AOI outline is kept.
        """
        include = include_map and geom is not None
        tolerance = settings.map_simplify_tolerance_m
        layers = [
            build_layer(
                layer_id="aoi",
                title="Area of interest",
                kind="polygon",
                authority="user_input",
                source="User-supplied area of interest",
                features=[(geom, {})] if include else None,
                include_map=include,
                legend=single_legend("aoi", "Area of interest", NEUTRAL_OUTLINE_COLOR),
            ),
            build_layer(
                layer_id="farmland_classes",
                title="Farmland classification",
                kind="polygon",
                authority="machine_estimate",
                source="USDA NRCS Soil Data Access (SDA)",
                features=features_from_sda_rows(raw_units) if include else None,
                include_map=include,
                style_key="farmland_class",
                legend=farmland_legend(),
                simplify_tolerance_m=tolerance,
            ),
            build_layer(
                layer_id="urban_context",
                title="Census 2020 urban areas",
                kind="polygon",
                authority="reference_data",
                source="US Census Bureau TIGERweb",
                features=(
                    [(urban, {"name": name}) for name, urban in urban_geometries]
                    if include
                    else None
                ),
                include_map=include,
                data_vintage="Census 2020 Urban Areas",
                legend=single_legend(
                    "urban", "Census 2020 urban area", URBAN_CONTEXT_COLOR, "dashed_outline"
                ),
                simplify_tolerance_m=tolerance,
            ),
        ]
        return build_map_block(layers, settings.map_max_geojson_bytes)

    def analyze_polygon_sync(
        self,
        geojson_input: dict[str, Any] | str | Polygon | MultiPolygon,
        include_nccpi: bool = True,
        productivity_index: str = "nccpi",
        max_county_rating_override: float | None = None,
        include_map: bool = False,
    ) -> PolygonFarmlandAnalysisResponse:
        """Synchronous wrapper for analyze_polygon."""
        return self.analyze_polygon(
            geojson_input=geojson_input,
            include_nccpi=include_nccpi,
            productivity_index=productivity_index,
            max_county_rating_override=max_county_rating_override,
            include_map=include_map,
        )

    async def analyze_polygon_async(
        self,
        geojson_input: dict[str, Any] | str | Polygon | MultiPolygon,
        include_nccpi: bool = True,
        productivity_index: str = "nccpi",
        max_county_rating_override: float | None = None,
        include_map: bool = False,
    ) -> PolygonFarmlandAnalysisResponse:
        """Asynchronous wrapper for analyze_polygon."""
        return self.analyze_polygon(
            geojson_input=geojson_input,
            include_nccpi=include_nccpi,
            productivity_index=productivity_index,
            max_county_rating_override=max_county_rating_override,
            include_map=include_map,
        )
