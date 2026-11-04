"""Multi-County Corridor Screening and Farmland Analysis Engine.

Orchestrates linear corridor centerline buffering, indirect staging area topological erasure,
Census TIGERweb county boundary partitioning, SDA spatial soil intersection, NASS agricultural
baseline querying, composite Land Evaluation rating calculation, and sum reconciliation.
"""

from __future__ import annotations

import csv
import io
import logging
import math
from datetime import UTC, datetime
from typing import Any

from shapely import wkt as shapely_wkt
from shapely.errors import GEOSException
from shapely.geometry import LineString, MultiLineString, MultiPolygon, Polygon

from fpac_soil_mcp.config import Settings
from fpac_soil_mcp.config import settings as map_settings
from fpac_soil_mcp.constants import (
    REGULATORY_LIMITATIONS,
    REGULATORY_NOTICE,
)
from fpac_soil_mcp.geometry import (
    _WKT_PREFIX_PATTERN,
    GeometryValidationError,
    buffer_centerline,
    calculate_acreage,
    compute_geometry_hash,
    erase_geometries,
    geometry_to_wkt,
    parse_geojson_geometry,
    validate_and_sanitize_line_wkt,
    validate_and_sanitize_polygon_wkt,
)
from fpac_soil_mcp.integration_models import CountyIdentifier, CountyPartitionGeometry
from fpac_soil_mcp.lesa import _normalize_productivity_index as _normalize_fixed_productivity_index
from fpac_soil_mcp.map_contract import (
    ALTERNATIVE_COLORS,
    CORRIDOR_DIRECT_COLOR,
    NEUTRAL_OUTLINE_COLOR,
    URBAN_CONTEXT_COLOR,
    GeometryWithProperties,
    MapBlock,
    MapLayer,
    build_layer,
    build_map_block,
    farmland_legend,
    features_from_sda_rows,
    single_legend,
)
from fpac_soil_mcp.models import (
    SUPPORTED_INDEX_MSG,
    VALIDATED_PRODUCTIVITY_INDEXES,
    CorridorAlternativeComparison,
    CorridorCountySegment,
    CorridorFarmlandAnalysisResponse,
    CorridorImpactBreakdown,
    FarmlandCategoryBreakdown,
    QuerySource,
    SoilMapUnitAcreage,
)
from fpac_soil_mcp.nass_client import NassClient
from fpac_soil_mcp.polygon_analysis import categorize_farmland_class
from fpac_soil_mcp.sda_client import (
    PRODUCTIVITY_PROVENANCE,
    PRODUCTIVITY_SEMANTICS,
    SDV_RATING_REGISTRY,
    SDAClient,
    SDAClientError,
)
from fpac_soil_mcp.tigerweb_client import TigerwebClient

logger = logging.getLogger(__name__)


# Sentinels, fallback provenance IDs, and the NCCPI rule come from the SDV
# registry in sda_client (single source of truth, ADR 0014).
_UNRATED_SENTINELS = PRODUCTIVITY_SEMANTICS["nccpi"]["sentinels"]
_INDEX_SENTINELS = {
    index: semantics["sentinels"] for index, semantics in PRODUCTIVITY_SEMANTICS.items()
}
_INDEX_SOURCES = dict(PRODUCTIVITY_PROVENANCE)
_NCCPI_RULE = SDV_RATING_REGISTRY["nccpi"].rule_name


def _normalize_corridor_rating(value: Any, is_rated: Any, productivity_index: str) -> float | None:
    """Return a valid rated productivity value, preserving zero ratings."""
    if is_rated is False:
        return None
    try:
        rating = float(value) if value is not None else None
    except (ValueError, TypeError):
        return None
    sentinels = _INDEX_SENTINELS.get(productivity_index, _UNRATED_SENTINELS)
    if rating is None or not math.isfinite(rating) or rating < 0 or rating in sentinels:
        return None
    return rating


def _get_corridor_ratings(
    sda_client: SDAClient,
    mukeys: list[str],
    productivity_index: str,
) -> dict[str, dict[str, Any]]:
    if not mukeys:
        return {}
    rows = list(sda_client.get_productivity_ratings(mukeys=mukeys, index_type=productivity_index))
    if not rows and productivity_index == "nccpi":
        rows = sda_client.get_interpretations(
            mukeys=mukeys,
            rule_name=_NCCPI_RULE,
            aggregation_method="Weighted Average",
        )
    return {str(row.get("mukey")): dict(row) for row in rows}


def _county_identifier(
    segment: dict[str, Any] | CountyPartitionGeometry,
) -> CountyIdentifier:
    """Build one validated county identity from a TIGERweb segment mapping or model."""
    if isinstance(segment, CountyPartitionGeometry):
        return CountyIdentifier(
            state_fips=segment.state_fips,
            county_fips=segment.county_fips,
            county_name=segment.county_name,
            state_name=segment.state_name,
        )
    return CountyIdentifier.from_dict(
        {
            "state_fips": str(segment.get("state_fips", "00")),
            "county_fips": str(segment.get("county_fips", "000")),
            "county_name": str(segment.get("county_name", "Unknown County")),
            "state_name": segment.get("state_name"),
        }
    )


class CorridorAnalyzer:
    """Orchestrates multi-county linear corridor screening and analysis."""

    def __init__(
        self,
        sda_client: SDAClient | None = None,
        tigerweb_client: TigerwebClient | None = None,
        nass_client: NassClient | None = None,
    ) -> None:
        self.sda_client = sda_client or SDAClient()
        self.tigerweb_client = tigerweb_client or TigerwebClient()
        self.nass_client = nass_client or NassClient()

    def analyze_corridor(
        self,
        centerline_input: dict[str, Any] | str,
        buffer_distance: float,
        buffer_units: str = "feet",
        indirect_geometry_input: dict[str, Any] | str | Polygon | MultiPolygon | None = None,
        alternatives: list[dict[str, Any]] | None = None,
        include_nccpi: bool = True,
        productivity_index: str = "nccpi",
        max_county_rating_override: float | None = None,
        include_map: bool = False,
    ) -> CorridorFarmlandAnalysisResponse:
        """Execute full multi-county corridor farmland screening and reconciliation.

        Args:
            centerline_input: GeoJSON dict, string, or WKT of the corridor centerline.
            buffer_distance: Distance to buffer on each side of the centerline.
            buffer_units: Units for buffer ('feet', 'meters', 'miles').
            indirect_geometry_input: Optional indirect staging/access areas.
            alternatives: Optional list of alternative alignment dicts:
                [{'alternative_id': 'B', 'centerline': ..., 'buffer_distance': ..., 'buffer_units': ...}]
            include_nccpi: Whether to retrieve component-weighted interpretations.
            productivity_index: Soil productivity index type ('nccpi').
            max_county_rating_override: Optional positive county maximum benchmark.
            include_map: Include display geometry in the ``map`` layers (ADR 0017).
                Numbers are computed from exact geometry either way.

        Returns:
            CorridorFarmlandAnalysisResponse with partitioned county segments, composite LE, and sum audit.
        """
        now = datetime.now(UTC)
        timestamp_str = now.isoformat()
        limitations = list(REGULATORY_LIMITATIONS)
        normalized_index = _normalize_fixed_productivity_index(productivity_index)
        if normalized_index not in VALIDATED_PRODUCTIVITY_INDEXES:
            raise ValueError(
                f"Unsupported productivity index type '{productivity_index}'. {SUPPORTED_INDEX_MSG}"
            )
        norm_idx = normalized_index.value.lower()
        if max_county_rating_override is not None and (
            not math.isfinite(max_county_rating_override) or max_county_rating_override <= 0
        ):
            raise ValueError("max_county_rating_override must be a positive finite number")
        ratings_requested = include_nccpi or norm_idx != "nccpi"

        # 1. Resolve direct centerline geometry and compute geometry hash from centerline
        try:
            if isinstance(centerline_input, (LineString, MultiLineString)):
                centerline_geom = centerline_input
            elif isinstance(centerline_input, str) and _WKT_PREFIX_PATTERN.match(
                centerline_input.strip()
            ):
                clean_line_wkt = validate_and_sanitize_line_wkt(centerline_input)
                centerline_geom = shapely_wkt.loads(clean_line_wkt)
            else:
                centerline_geom = parse_geojson_geometry(centerline_input, allow_line=True)
                if not isinstance(centerline_geom, (LineString, MultiLineString)):
                    raise GeometryValidationError(
                        f"Centerline geometry must be LineString or MultiLineString; received '{centerline_geom.geom_type}'."
                    )

            direct_hash = compute_geometry_hash(centerline_geom)

            direct_poly = buffer_centerline(
                centerline_input=centerline_geom,
                buffer_distance=buffer_distance,
                distance_unit=buffer_units,
            )
            direct_acres = calculate_acreage(direct_poly)
            perimeter_evidence = self.tigerweb_client.get_perimeter_evidence(direct_poly)
        except (GeometryValidationError, ValueError) as exc:
            logger.error("Centerline buffering failed: %s", exc)
            return CorridorFarmlandAnalysisResponse(
                query_type="corridor",
                geometry_hash="sha256:0000000000000000000000000000000000000000000000000000000000000000",
                buffer_distance=buffer_distance,
                buffer_units=buffer_units,
                impact_breakdown=CorridorImpactBreakdown(),
                composite_relative_rating=None,
                county_segments=[],
                reconciliation_summary={"status": "error", "error": str(exc)},
                alternatives=[],
                tabular_csv="",
                manifest={"error": str(exc)},
                source=QuerySource(
                    endpoint=self.sda_client.base_url,
                    timestamp_utc=timestamp_str,
                ),
                limitations=[*limitations, f"Centerline error: {exc}"],
                regulatory_notice=REGULATORY_NOTICE,
                map=_corridor_map(include_map=False),
            )

        # 2. Process indirect staging geometry if supplied (support Polygon/MultiPolygon, GeoJSON, or WKT)
        indirect_poly = None
        indirect_acres = 0.0
        if indirect_geometry_input is not None:
            try:
                if isinstance(indirect_geometry_input, (Polygon, MultiPolygon)):
                    parsed_indirect = indirect_geometry_input
                elif isinstance(indirect_geometry_input, str) and _WKT_PREFIX_PATTERN.match(
                    indirect_geometry_input.strip()
                ):
                    clean_poly_wkt = validate_and_sanitize_polygon_wkt(indirect_geometry_input)
                    parsed_indirect = shapely_wkt.loads(clean_poly_wkt)
                else:
                    parsed_indirect = parse_geojson_geometry(indirect_geometry_input)

                indirect_poly = erase_geometries(parsed_indirect, direct_poly)
                if indirect_poly is not None and not indirect_poly.is_empty:
                    indirect_acres = calculate_acreage(indirect_poly)
                else:
                    indirect_poly = None
                    indirect_acres = 0.0
            except (GeometryValidationError, ValueError) as exc:
                logger.warning("Indirect geometry processing failed: %s", exc)
                limitations.append(f"Indirect geometry warning: {exc}")

        # Total combined project footprint
        if indirect_poly is not None and not indirect_poly.is_empty:
            project_footprint = direct_poly.union(indirect_poly)
        else:
            project_footprint = direct_poly

        total_project_acres = direct_acres + indirect_acres
        impact_breakdown = CorridorImpactBreakdown(
            direct_acres=round(direct_acres, 2),
            indirect_acres=round(indirect_acres, 2),
            total_project_acres=round(total_project_acres, 2),
        )

        # 3. Intersect and partition footprint by counties via TIGERweb
        counties = self.tigerweb_client.get_intersecting_counties(project_footprint)
        county_fallback_occurred = False
        if not counties:
            county_fallback_occurred = True
            logger.warning(
                "No intersecting counties found from TIGERweb; treating footprint as single partition fallback."
            )
            counties = [
                {
                    "state_fips": "00",
                    "county_fips": "000",
                    "county_name": "Unspecified County",
                    "state_name": None,
                    "geometry": project_footprint,
                }
            ]

        segments_raw = self.tigerweb_client.partition_geometry_by_counties(
            geometry_input=project_footprint,
            counties=counties,
        )

        if not segments_raw:
            county_fallback_occurred = True
            # Fallback if spatial intersection produces empty segments
            logger.warning(
                "County partitioning produced no segments; treating footprint as single partition fallback."
            )
            segments_raw = [
                {
                    "state_fips": "00",
                    "county_fips": "000",
                    "county_name": "Unspecified County",
                    "state_name": None,
                    "geometry": project_footprint,
                    "calculated_acres": total_project_acres,
                }
            ]

        if county_fallback_occurred:
            fallback_msg = (
                "County boundary intersection/partitioning fallback occurred: "
                "TIGERweb county boundaries were unavailable or did not yield intersecting segments; "
                "treating project footprint as single unpartitioned segment."
            )
            limitations.append(fallback_msg)

        # 4. Analyze each county segment
        settings = Settings()
        county_segment_models: list[CorridorCountySegment] = []
        map_soil_rows: list[dict[str, Any]] = []
        map_county_features: list[GeometryWithProperties] = []
        map_urban_by_name: dict[str, Polygon | MultiPolygon] = {}
        map_alternatives: list[tuple[str, Polygon | MultiPolygon]] = []
        total_le_sum = 0.0
        total_le_weight = 0.0
        total_segment_acres_sum = 0.0
        sum_direct_acres = 0.0
        sum_indirect_acres = 0.0

        for seg in segments_raw:
            seg_geom = seg.geometry if isinstance(seg, CountyPartitionGeometry) else seg["geometry"]
            county = _county_identifier(seg)
            seg_state_fips = county.state_fips
            seg_county_fips = county.county_fips
            seg_county_name = county.county_name
            seg_state_name = county.state_name
            seg_total_acres = (
                seg.calculated_acres
                if isinstance(seg, CountyPartitionGeometry)
                else seg.get("calculated_acres", 0.0)
            )

            # Direct vs indirect within this segment
            seg_direct_acres = 0.0
            seg_indirect_acres = 0.0
            try:
                direct_inter = seg_geom.intersection(direct_poly)
                if not direct_inter.is_empty:
                    seg_direct_acres = calculate_acreage(direct_inter)
            except (GEOSException, ValueError, TypeError):
                seg_direct_acres = seg_total_acres

            if indirect_poly is not None and not indirect_poly.is_empty:
                try:
                    indirect_inter = seg_geom.intersection(indirect_poly)
                    if not indirect_inter.is_empty:
                        seg_indirect_acres = calculate_acreage(indirect_inter)
                except (GEOSException, ValueError, TypeError):
                    seg_indirect_acres = max(0.0, seg_total_acres - seg_direct_acres)

            sum_direct_acres += seg_direct_acres
            sum_indirect_acres += seg_indirect_acres
            total_segment_acres_sum += seg_total_acres

            # Weight of this segment relative to corridor footprint
            seg_weight_pct = (
                round((seg_total_acres / total_project_acres * 100.0), 2)
                if total_project_acres > 0
                else 0.0
            )

            # Urban screening for segment
            urban_rec, seg_urban_geometries = (
                self.tigerweb_client.check_urban_exemption_with_geometries(seg_geom)
            )
            urban_dict = urban_rec.model_dump(mode="json")
            for urban_name, urban_geom in seg_urban_geometries:
                map_urban_by_name.setdefault(urban_name, urban_geom)

            # SDA soils query for segment
            seg_wkt = geometry_to_wkt(seg_geom)
            raw_units: list[dict[str, Any]] = []
            try:
                raw_units = self.sda_client.get_spatial_intersection(
                    seg_wkt,
                    clip=True,
                    geom_acres=True,
                    return_geom=include_map,
                )
            except SDAClientError as exc:
                logger.error("SDA spatial query failed for county %s: %s", seg_county_name, exc)
                limitations.append(f"SDA error for {seg_county_name}: {exc}")

            # Selected productivity interpretations
            mukeys = list({str(r.get("mukey")) for r in raw_units if r.get("mukey")})
            interp_map: dict[str, dict[str, Any]] = {}
            if ratings_requested and mukeys:
                try:
                    interp_map = _get_corridor_ratings(self.sda_client, mukeys, norm_idx)
                except SDAClientError as exc:
                    logger.warning(
                        "Productivity interpretation error (%s) for %s: %s",
                        norm_idx,
                        seg_county_name,
                        exc,
                    )

            partition_max: dict[str, float] = {}
            if ratings_requested and max_county_rating_override is None:
                areasymbol = {
                    str(u.get("areasymbol")).strip() for u in raw_units if u.get("areasymbol")
                }
                for symbol in areasymbol:
                    try:
                        benchmark = self.sda_client.get_county_max_productivity_rating(
                            areasymbol=symbol,
                            index_type=norm_idx,
                        )
                        if benchmark is not None and benchmark > 0:
                            partition_max[symbol] = float(benchmark)
                    except SDAClientError as exc:
                        logger.warning("County max rating query failed for %s: %s", symbol, exc)

            # Map units & farmland categories
            grouped_units: dict[str, dict[str, Any]] = {}
            for u in raw_units:
                m_str = str(u.get("mukey", ""))
                if not m_str:
                    continue
                if m_str not in grouped_units:
                    grouped_units[m_str] = {
                        "mukey": m_str,
                        "musym": u.get("musym"),
                        "muname": u.get("muname"),
                        "farmlndcl": u.get("farmlndcl"),
                        "areasymbol": u.get("areasymbol"),
                        "area_ac": 0.0,
                    }
                try:
                    area_val = float(u.get("area_ac") or 0.0)
                except (ValueError, TypeError):
                    area_val = 0.0
                grouped_units[m_str]["area_ac"] += area_val

            category_acres: dict[str, float] = {
                "prime": 0.0,
                "conditional_prime": 0.0,
                "statewide": 0.0,
                "local": 0.0,
                "unique": 0.0,
                "not_prime": 0.0,
                "unmapped": 0.0,
            }

            unit_models: list[SoilMapUnitAcreage] = []
            total_mapped_acres = 0.0
            segment_le_sum = 0.0
            segment_le_weight = 0.0

            for m_str, u in grouped_units.items():
                farmlndcl_str = u.get("farmlndcl")
                calc_ac = round(u["area_ac"], 2)
                total_mapped_acres += calc_ac
                pct = round((calc_ac / seg_total_acres * 100.0) if seg_total_acres > 0 else 0.0, 2)

                interp_info = interp_map.get(m_str, {})
                cat = categorize_farmland_class(farmlndcl_str)
                category_acres[cat] += calc_ac

                numeric_rating = _normalize_corridor_rating(
                    interp_info.get("numeric_rating"),
                    interp_info.get("is_rated"),
                    norm_idx,
                )
                if numeric_rating is not None:
                    try:
                        benchmark = partition_max.get(
                            str(u.get("areasymbol")).strip(),
                            max_county_rating_override or 1.0,
                        )
                        le_score = min(1.0, max(0.0, numeric_rating / benchmark)) * 100.0
                        segment_le_sum += calc_ac * le_score
                        segment_le_weight += calc_ac
                    except (ValueError, TypeError):
                        numeric_rating = None

                unit_models.append(
                    SoilMapUnitAcreage(
                        mukey=m_str,
                        musym=u.get("musym"),
                        muname=u.get("muname"),
                        farmlndcl=farmlndcl_str,
                        areasymbol=u.get("areasymbol"),
                        calculated_acres=calc_ac,
                        percentage_of_aoi=pct,
                        productivity_rating=numeric_rating,
                        productivity_rating_class=(
                            interp_info.get("rating_class") if numeric_rating is not None else None
                        ),
                        productivity_rating_source=interp_info.get(
                            "productivity_rating_source",
                            _INDEX_SOURCES.get(norm_idx, f"SDA:{norm_idx.upper()}"),
                        ),
                    )
                )

            unmapped_rem = max(0.0, round(seg_total_acres - total_mapped_acres, 2))
            category_acres["unmapped"] += unmapped_rem

            total_seg_ac = seg_total_acres

            def _seg_pct(val: float, total: float = total_seg_ac) -> float:
                return round((val / total * 100.0) if total > 0 else 0.0, 2)

            fppa_acres = (
                category_acres["prime"]
                + category_acres["conditional_prime"]
                + category_acres["statewide"]
                + category_acres["local"]
                + category_acres["unique"]
            )

            farmland_summary = FarmlandCategoryBreakdown(
                prime_farmland_acres=round(category_acres["prime"], 2),
                prime_farmland_pct=_seg_pct(category_acres["prime"]),
                conditional_prime_acres=round(category_acres["conditional_prime"], 2),
                conditional_prime_pct=_seg_pct(category_acres["conditional_prime"]),
                statewide_importance_acres=round(category_acres["statewide"], 2),
                statewide_importance_pct=_seg_pct(category_acres["statewide"]),
                local_importance_acres=round(category_acres["local"], 2),
                local_importance_pct=_seg_pct(category_acres["local"]),
                unique_farmland_acres=round(category_acres["unique"], 2),
                unique_farmland_pct=_seg_pct(category_acres["unique"]),
                not_prime_acres=round(category_acres["not_prime"], 2),
                not_prime_pct=_seg_pct(category_acres["not_prime"]),
                unmapped_acres=round(category_acres["unmapped"], 2),
                unmapped_pct=_seg_pct(category_acres["unmapped"]),
                total_fppa_protected_acres=round(fppa_acres, 2),
                total_fppa_protected_pct=_seg_pct(fppa_acres),
            )

            # County-level weighted LE rating
            segment_relative_rating: float | None = None
            if segment_le_weight > 0:
                segment_relative_rating = round(segment_le_sum / segment_le_weight, 1)
                total_le_sum += segment_le_sum
                total_le_weight += segment_le_weight

            # USDA NASS Profile
            nass_profile = self.nass_client.get_county_ag_profile(
                county=county,
                census_year=settings.nass_census_year,
            )

            if not unit_models:
                coverage_status = "unmapped"
            elif unmapped_rem > 0:
                coverage_status = "partially_covered"
            else:
                coverage_status = "covered"

            if include_map:
                map_soil_rows.extend(raw_units)
                map_county_features.append(
                    (
                        seg_geom,
                        {
                            "county_name": seg_county_name,
                            "geoid": f"{seg_state_fips}{seg_county_fips}",
                            "state_fips": seg_state_fips,
                            "county_fips": seg_county_fips,
                        },
                    )
                )
            county_segment_models.append(
                CorridorCountySegment(
                    state_fips=seg_state_fips,
                    county_fips=seg_county_fips,
                    county_name=seg_county_name,
                    state_name=seg_state_name,
                    direct_acres=round(seg_direct_acres, 2),
                    indirect_acres=round(seg_indirect_acres, 2),
                    total_segment_acres=round(seg_total_acres, 2),
                    segment_weight_pct=seg_weight_pct,
                    coverage_status=coverage_status,
                    urban_screening=urban_dict,
                    farmland_summary=farmland_summary,
                    map_units=unit_models,
                    nass_profile=nass_profile.model_dump(mode="json"),
                    relative_rating_le=segment_relative_rating,
                )
            )

        # 5. Calculate Reconciled Area-Weighted Composite LE Rating
        composite_relative_rating: float | None = None
        if total_le_weight > 0:
            composite_relative_rating = round(total_le_sum / total_le_weight, 1)

        # 6. Perform Sum Reconciliation Audit
        acreage_delta = abs(total_segment_acres_sum - total_project_acres)
        delta_pct = (
            round((acreage_delta / total_project_acres * 100.0), 4)
            if total_project_acres > 0
            else 0.0
        )
        is_reconciled = delta_pct <= 0.1  # Reconciled within 0.1% tolerance

        if not is_reconciled:
            rec_warning = (
                f"Acreage sum reconciliation exceeded 0.1% tolerance limit: "
                f"buffered project footprint = {round(total_project_acres, 2)} ac, "
                f"sum of county partitions = {round(total_segment_acres_sum, 2)} ac "
                f"(direct = {round(sum_direct_acres, 2)} ac, indirect = {round(sum_indirect_acres, 2)} ac), "
                f"delta = {round(acreage_delta, 4)} ac ({delta_pct}%)."
            )
            logger.warning(
                "Acreage sum reconciliation failed: %s",
                {
                    "buffered_project_acres": round(total_project_acres, 2),
                    "sum_of_county_segments_acres": round(total_segment_acres_sum, 2),
                    "direct_acres_sum": round(sum_direct_acres, 2),
                    "indirect_acres_sum": round(sum_indirect_acres, 2),
                    "acreage_delta": round(acreage_delta, 4),
                    "variance_pct": delta_pct,
                    "tolerance_pct_limit": 0.1,
                },
            )
            limitations.append(rec_warning)

        reconciliation_summary = {
            "buffered_footprint_acres": round(total_project_acres, 2),
            "sum_of_county_segments_acres": round(total_segment_acres_sum, 2),
            "acreage_delta": round(acreage_delta, 4),
            "variance_pct": delta_pct,
            "reconciliation_passed": is_reconciled,
            "tolerance_pct_limit": 0.1,
            "counties_partitioned_count": len(county_segment_models),
        }

        # 7. Process Alternatives if provided
        alternative_comparisons: list[CorridorAlternativeComparison] = []
        if alternatives:
            for alt in alternatives:
                alt_id = str(alt.get("alternative_id", "Alt"))
                alt_centerline = alt.get("centerline")
                alt_buf_dist = float(alt.get("buffer_distance", buffer_distance))
                alt_buf_units = str(alt.get("buffer_units", buffer_units))
                alt_indirect = alt.get("indirect_geometry")

                if alt_centerline is None:
                    continue

                try:
                    if isinstance(alt_centerline, (LineString, MultiLineString)):
                        alt_centerline_geom = alt_centerline
                    elif isinstance(alt_centerline, str) and _WKT_PREFIX_PATTERN.match(
                        alt_centerline.strip()
                    ):
                        clean_alt_line_wkt = validate_and_sanitize_line_wkt(alt_centerline)
                        alt_centerline_geom = shapely_wkt.loads(clean_alt_line_wkt)
                    else:
                        alt_centerline_geom = parse_geojson_geometry(
                            alt_centerline, allow_line=True
                        )
                        if not isinstance(alt_centerline_geom, (LineString, MultiLineString)):
                            raise GeometryValidationError(
                                f"Centerline geometry must be LineString or MultiLineString; received '{alt_centerline_geom.geom_type}'."
                            )

                    alt_hash = compute_geometry_hash(alt_centerline_geom)

                    alt_direct_poly = buffer_centerline(
                        centerline_input=alt_centerline_geom,
                        buffer_distance=alt_buf_dist,
                        distance_unit=alt_buf_units,
                    )
                    alt_direct_ac = calculate_acreage(alt_direct_poly)
                    alt_indirect_ac = 0.0

                    if alt_indirect is not None:
                        if isinstance(alt_indirect, (Polygon, MultiPolygon)):
                            alt_parsed_ind = alt_indirect
                        elif isinstance(alt_indirect, str) and _WKT_PREFIX_PATTERN.match(
                            alt_indirect.strip()
                        ):
                            clean_alt_poly_wkt = validate_and_sanitize_polygon_wkt(alt_indirect)
                            alt_parsed_ind = shapely_wkt.loads(clean_alt_poly_wkt)
                        else:
                            alt_parsed_ind = parse_geojson_geometry(alt_indirect)

                        alt_ind_poly = erase_geometries(alt_parsed_ind, alt_direct_poly)
                        if alt_ind_poly is not None and not alt_ind_poly.is_empty:
                            alt_indirect_ac = calculate_acreage(alt_ind_poly)

                    alt_tot_ac = alt_direct_ac + alt_indirect_ac
                    alt_footprint = (
                        alt_direct_poly.union(alt_ind_poly)
                        if alt_indirect_ac > 0
                        else alt_direct_poly
                    )

                    alt_counties = self.tigerweb_client.get_intersecting_counties(alt_footprint)
                    if not alt_counties:
                        alt_counties = [
                            {
                                "state_fips": "00",
                                "county_fips": "000",
                                "county_name": "Unspecified County",
                                "state_name": None,
                                "geometry": alt_footprint,
                            }
                        ]

                    alt_county_names = [
                        c.get("county_name", "") for c in alt_counties if c.get("county_name")
                    ]

                    # Partition alternative footprint across intersected counties
                    alt_segments_raw = self.tigerweb_client.partition_geometry_by_counties(
                        geometry_input=alt_footprint,
                        counties=alt_counties,
                    )

                    if not alt_segments_raw:
                        alt_segments_raw = [
                            {
                                "state_fips": "00",
                                "county_fips": "000",
                                "county_name": "Unspecified County",
                                "state_name": None,
                                "geometry": alt_footprint,
                                "calculated_acres": alt_tot_ac,
                            }
                        ]

                    alt_fppa_ac = 0.0
                    alt_total_le_sum = 0.0
                    alt_total_le_weight = 0.0
                    alt_total_seg_acres = 0.0

                    for alt_seg in alt_segments_raw:
                        alt_seg_geom = (
                            alt_seg.geometry
                            if hasattr(alt_seg, "geometry")
                            else alt_seg.get("geometry")
                        )
                        alt_seg_ac = (
                            alt_seg.calculated_acres
                            if hasattr(alt_seg, "calculated_acres")
                            else alt_seg.get("calculated_acres", 0.0)
                        )
                        alt_total_seg_acres += alt_seg_ac

                        alt_seg_wkt = geometry_to_wkt(alt_seg_geom)
                        alt_raw_units: list[dict[str, Any]] = []
                        try:
                            alt_raw_units = self.sda_client.get_spatial_intersection(
                                alt_seg_wkt, clip=True, geom_acres=True, return_geom=False
                            )
                        except SDAClientError as exc:
                            logger.warning(
                                "Alternative %s SDA query failed for county segment: %s",
                                alt_id,
                                exc,
                            )

                        alt_mukeys = list(
                            {str(r.get("mukey")) for r in alt_raw_units if r.get("mukey")}
                        )
                        alt_interp_map: dict[str, dict[str, Any]] = {}
                        if ratings_requested and alt_mukeys:
                            try:
                                alt_interp_map = _get_corridor_ratings(
                                    self.sda_client,
                                    alt_mukeys,
                                    norm_idx,
                                )
                            except SDAClientError as exc:
                                logger.warning(
                                    "Alternative %s productivity interpretation error (%s): %s",
                                    alt_id,
                                    norm_idx,
                                    exc,
                                )

                        alt_partition_max: dict[str, float] = {}
                        if ratings_requested and max_county_rating_override is None:
                            alt_symbols = {
                                str(unit.get("areasymbol")).strip()
                                for unit in alt_raw_units
                                if unit.get("areasymbol")
                            }
                            for symbol in alt_symbols:
                                try:
                                    benchmark = self.sda_client.get_county_max_productivity_rating(
                                        areasymbol=symbol,
                                        index_type=norm_idx,
                                    )
                                    if benchmark is not None and benchmark > 0:
                                        alt_partition_max[symbol] = float(benchmark)
                                except SDAClientError as exc:
                                    logger.warning(
                                        "Alternative %s county max rating query failed for %s: %s",
                                        alt_id,
                                        symbol,
                                        exc,
                                    )

                        alt_seg_le_sum = 0.0
                        alt_seg_le_weight = 0.0
                        for au in alt_raw_units:
                            m_str = str(au.get("mukey", ""))
                            area_val = 0.0
                            try:
                                area_val = float(au.get("area_ac") or 0.0)
                            except (ValueError, TypeError):
                                area_val = 0.0

                            fcat = categorize_farmland_class(au.get("farmlndcl"))
                            if fcat in (
                                "prime",
                                "conditional_prime",
                                "statewide",
                                "local",
                                "unique",
                            ):
                                alt_fppa_ac += area_val

                            interp_info = alt_interp_map.get(m_str, {})
                            num_rating = _normalize_corridor_rating(
                                interp_info.get("numeric_rating"),
                                interp_info.get("is_rated"),
                                norm_idx,
                            )
                            if num_rating is not None:
                                try:
                                    benchmark = alt_partition_max.get(
                                        str(au.get("areasymbol")).strip(),
                                        max_county_rating_override or 1.0,
                                    )
                                    le_score = min(1.0, max(0.0, num_rating / benchmark)) * 100.0
                                    alt_seg_le_sum += area_val * le_score
                                    alt_seg_le_weight += area_val
                                except (ValueError, TypeError):
                                    pass

                        if alt_seg_le_weight > 0:
                            alt_total_le_sum += alt_seg_le_sum
                            alt_total_le_weight += alt_seg_le_weight

                    alt_composite_relative_rating: float | None = None
                    if alt_total_le_weight > 0:
                        alt_composite_relative_rating = round(
                            alt_total_le_sum / alt_total_le_weight, 1
                        )

                    alt_fppa_pct = (
                        round((alt_fppa_ac / alt_tot_ac * 100.0), 2) if alt_tot_ac > 0 else 0.0
                    )

                    map_alternatives.append((alt_id, alt_footprint))
                    alternative_comparisons.append(
                        CorridorAlternativeComparison(
                            alternative_id=alt_id,
                            geometry_hash=alt_hash,
                            total_project_acres=round(alt_tot_ac, 2),
                            direct_acres=round(alt_direct_ac, 2),
                            indirect_acres=round(alt_indirect_ac, 2),
                            total_fppa_protected_acres=round(alt_fppa_ac, 2),
                            total_fppa_protected_pct=alt_fppa_pct,
                            composite_relative_rating=alt_composite_relative_rating,
                            counties_traversed=alt_county_names,
                        )
                    )
                except (GeometryValidationError, ValueError, TypeError, GEOSException) as exc:
                    logger.warning("Failed to process alternative %s: %s", alt_id, exc)

        # 8. Generate Summary CSV
        csv_buffer = io.StringIO()
        writer = csv.writer(csv_buffer)
        writer.writerow(
            [
                "State_FIPS",
                "County_FIPS",
                "County_Name",
                "Direct_Acres",
                "Indirect_Acres",
                "Total_Segment_Acres",
                "Segment_Weight_Pct",
                "Prime_Acres",
                "Conditional_Prime_Acres",
                "Statewide_Acres",
                "Local_Acres",
                "Unique_Acres",
                "Not_Prime_Acres",
                "Total_FPPA_Protected_Acres",
                "Relative_Rating_LE",
            ]
        )
        for s in county_segment_models:
            writer.writerow(
                [
                    s.state_fips,
                    s.county_fips,
                    s.county_name,
                    s.direct_acres,
                    s.indirect_acres,
                    s.total_segment_acres,
                    s.segment_weight_pct,
                    s.farmland_summary.prime_farmland_acres,
                    s.farmland_summary.conditional_prime_acres,
                    s.farmland_summary.statewide_importance_acres,
                    s.farmland_summary.local_importance_acres,
                    s.farmland_summary.unique_farmland_acres,
                    s.farmland_summary.not_prime_acres,
                    s.farmland_summary.total_fppa_protected_acres,
                    s.relative_rating_le if s.relative_rating_le is not None else "N/A",
                ]
            )
        tabular_csv = csv_buffer.getvalue()

        # 9. Build Manifest
        manifest = {
            "direct_centerline_hash": direct_hash,
            "buffer_distance": buffer_distance,
            "buffer_units": buffer_units,
            "has_indirect_footprint": indirect_poly is not None,
            "county_partitions_count": len(county_segment_models),
            "reconciliation": reconciliation_summary,
            "alternatives_count": len(alternative_comparisons),
            "criterion_2_perimeter_evidence": perimeter_evidence,
            "generated_at_utc": timestamp_str,
        }

        return CorridorFarmlandAnalysisResponse(
            query_type="corridor",
            geometry_hash=direct_hash,
            buffer_distance=buffer_distance,
            buffer_units=buffer_units,
            impact_breakdown=impact_breakdown,
            composite_relative_rating=composite_relative_rating,
            county_segments=county_segment_models,
            reconciliation_summary=reconciliation_summary,
            alternatives=alternative_comparisons,
            tabular_csv=tabular_csv,
            manifest=manifest,
            source=QuerySource(
                endpoint=self.sda_client.base_url,
                timestamp_utc=timestamp_str,
            ),
            limitations=limitations,
            regulatory_notice=REGULATORY_NOTICE,
            map=_corridor_map(
                include_map=include_map,
                direct_poly=direct_poly,
                indirect_poly=indirect_poly,
                alternatives=map_alternatives,
                soil_rows=map_soil_rows,
                county_features=map_county_features,
                urban_by_name=map_urban_by_name,
            ),
        )


def _alternative_layer_suffix(alt_id: str) -> str:
    """Lower-case the alternative id and keep only ``[a-z0-9_]``."""
    suffix = "".join(ch if ch.isascii() and ch.isalnum() else "_" for ch in alt_id.lower())
    return suffix or "alt"


def _alternative_layer_ids(alt_ids: list[str]) -> list[str]:
    """Return one unique ``corridor_alternative_<suffix>`` layer id per alternative.

    Ids that clean up to the same suffix get ``_2``, ``_3``, ... in input order,
    skipping any suffix already taken.
    """
    used: set[str] = set()
    out: list[str] = []
    for alt_id in alt_ids:
        base = _alternative_layer_suffix(alt_id)
        suffix, n = base, 1
        while suffix in used:
            n += 1
            suffix = f"{base}_{n}"
        used.add(suffix)
        out.append(f"corridor_alternative_{suffix}")
    return out


def _corridor_map(
    *,
    include_map: bool,
    direct_poly: Polygon | MultiPolygon | None = None,
    indirect_poly: Polygon | MultiPolygon | None = None,
    alternatives: list[tuple[str, Polygon | MultiPolygon]] | None = None,
    soil_rows: list[dict[str, Any]] | None = None,
    county_features: list[GeometryWithProperties] | None = None,
    urban_by_name: dict[str, Polygon | MultiPolygon] | None = None,
) -> MapBlock:
    """Build the ADR 0017 corridor map block; geometry only when ``include_map`` is true.

    Layer order is the size-cap drop priority: urban context, then county
    segments, then farmland classes are dropped before the footprints.
    """
    include = include_map and direct_poly is not None
    tolerance = map_settings.map_simplify_tolerance_m

    def footprint(
        layer_id: str, title: str, geom, color: str, pattern: str = "outline"
    ) -> MapLayer:
        return build_layer(
            layer_id=layer_id,
            title=title,
            kind="polygon",
            authority="machine_estimate",
            source="Buffered corridor footprint",
            features=[(geom, {})] if include else None,
            include_map=include,
            legend=single_legend(layer_id, title, color, pattern),
        )

    layers = [
        footprint(
            "corridor_direct", "Direct corridor footprint", direct_poly, CORRIDOR_DIRECT_COLOR
        )
    ]
    if indirect_poly is not None and not indirect_poly.is_empty:
        layers.append(
            footprint(
                "corridor_indirect",
                "Indirect area",
                indirect_poly,
                CORRIDOR_DIRECT_COLOR,
                "dashed_outline",
            )
        )
    alt_list = alternatives or []
    alt_layer_ids = _alternative_layer_ids([alt_id for alt_id, _ in alt_list])
    for index, ((alt_id, alt_geom), alt_layer_id) in enumerate(
        zip(alt_list, alt_layer_ids, strict=True)
    ):
        layers.append(
            footprint(
                alt_layer_id,
                f"Alternative {alt_id} footprint",
                alt_geom,
                ALTERNATIVE_COLORS[index % len(ALTERNATIVE_COLORS)],
                "dashed_outline",
            )
        )
    layers.append(
        build_layer(
            layer_id="farmland_classes",
            title="Farmland classification",
            kind="polygon",
            authority="machine_estimate",
            source="USDA NRCS Soil Data Access (SDA)",
            features=features_from_sda_rows(soil_rows or []) if include else None,
            include_map=include,
            style_key="farmland_class",
            legend=farmland_legend(),
            simplify_tolerance_m=tolerance,
        )
    )
    layers.append(
        build_layer(
            layer_id="county_segments",
            title="County segments",
            kind="polygon",
            authority="reference_data",
            source="US Census Bureau TIGERweb",
            features=list(county_features or []) if include else None,
            include_map=include,
            data_vintage="TIGERweb counties (current)",
            legend=single_legend(
                "county_segment", "County segment", NEUTRAL_OUTLINE_COLOR, "dashed_outline"
            ),
            simplify_tolerance_m=tolerance,
        )
    )
    layers.append(
        build_layer(
            layer_id="urban_context",
            title="Census 2020 urban areas",
            kind="polygon",
            authority="reference_data",
            source="US Census Bureau TIGERweb",
            features=(
                [(geom, {"name": name}) for name, geom in (urban_by_name or {}).items()]
                if include
                else None
            ),
            include_map=include,
            data_vintage="Census 2020 Urban Areas",
            legend=single_legend(
                "urban", "Census 2020 urban area", URBAN_CONTEXT_COLOR, "dashed_outline"
            ),
            simplify_tolerance_m=tolerance,
        )
    )
    return build_map_block(layers, map_settings.map_max_geojson_bytes)
