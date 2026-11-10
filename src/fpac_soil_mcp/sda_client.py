"""USDA NRCS Soil Data Access (SDA) client and query engine.

Encapsulates HTTPS communication with the USDA NRCS Soil Data Access Tabular REST service
(https://sdmdataaccess.nrcs.usda.gov/Tabular/post.rest), implementing strict coordinate and
mukey validation, fixed parameterized query templates, matrix table response parsing,
and robust retry logic.

The metadata-driven SDV rating contract is defined in ``SDV_RATING_REGISTRY`` (ADR 0014).
See ``docs/sdv-metadata-contract.md`` for the field-level contract, per-table behaviour,
provenance IDs, and the caveat catalogue.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

import httpx

from fpac_soil_mcp.config import settings
from fpac_soil_mcp.geometry import (
    GeometryValidationError,
    validate_and_sanitize_polygon_wkt,
)
from fpac_soil_mcp.http_client import (
    HttpRequestError,
    HttpStatusError,
    execute_http_request_with_retry,
)
from fpac_soil_mcp.models import SUPPORTED_INDEX_MSG

logger = logging.getLogger(__name__)

# Productivity provenance and semantics are derived from SDV_RATING_REGISTRY
# (defined below) to ensure a single source of truth.  The four public selectors
# (nccpi, csr2, cpi, storie) are re-exported here for backward compatibility.

# ---------------------------------------------------------------------------
# SDV metadata-driven rating contract (ADR 0014)
#
# Frozen, versioned registry of validated sdvattribute records.  Public callers
# still use the four fixed selectors (nccpi, csr2, cpi, storie); the registry
# adds internal support for Available Water Storage and crop yields.  See
# docs/sdv-metadata-contract.md for the field-level contract.
# ---------------------------------------------------------------------------

SDV_REGISTRY_VERSION = "1"

#: Fields the engine reads from sdvattribute (also the SELECT list for the
#: metadata lookup query).
SDV_CONTRACT_FIELDS = (
    "attributekey",
    "attributename",
    "attributetablename",
    "attributecolumnname",
    "attributelogicaldatatype",
    "nasisrulename",
    "ruledesign",
    "algorithmname",
    "horzaggmeth",
    "tiebreakrule",
    "depthqualifiermode",
    "layerdepthtotop",
    "layerdepthtobottom",
    "layerdepthuom",
    "interpnullsaszeroflag",
    "nullratingreplacementvalue",
    "primaryconcolname",
    "secondaryconcolname",
    "componentpercentcutoff",
    "resultcolumnname",
    "notratedphrase",
    "attributetype",
)

SUPPORTED_SDV_ALGORITHMS = frozenset(
    {"Weighted Average", "Dominant Condition", "No Aggregation Necessary"}
)

SUPPORTED_HORIZON_METHODS = frozenset({"Weighted Sum", "Weighted Average"})

_SDV_STRATEGY_TABLES = frozenset({"cointerp", "chorizon", "cocropyld", "component", "mapunit"})


@dataclass(frozen=True)
class SdvRatingSpec:
    """A frozen, validated SDV rating specification from the registry."""

    spec_id: str
    provenance_id: str
    attributename: str
    table: str
    column: str
    value_column: str
    rule_name: str
    algorithm: str
    horizon_method: str
    depth_top_cm: float | None
    depth_bottom_cm: float | None
    tiebreak_rule: int
    nulls_as_zero: bool
    required_constraints: tuple[str, ...]
    scale: str
    precision: int
    sentinels: frozenset[float]
    aliases: frozenset[str]


SDV_RATING_REGISTRY: MappingProxyType[str, SdvRatingSpec] = MappingProxyType(
    {
        "nccpi": SdvRatingSpec(
            spec_id="nccpi",
            provenance_id="SDA:NCCPI_V3",
            attributename="National Commodity Crop Productivity Index",
            table="cointerp",
            column="interphrc",
            value_column="interphr",
            rule_name="NCCPI - National Commodity Crop Productivity Index (Ver 3.0)",
            algorithm="Weighted Average",
            horizon_method="Weighted Average",
            depth_top_cm=None,
            depth_bottom_cm=None,
            tiebreak_rule=1,
            nulls_as_zero=False,
            required_constraints=(),
            scale="0-1",
            precision=3,
            sentinels=frozenset({99.0, 999.0, -99.0, -999.0}),
            aliases=frozenset({"nccpi", "nccpi_v3", "national commodity crop productivity index"}),
        ),
        "storie": SdvRatingSpec(
            spec_id="storie",
            provenance_id="SDA:COINTERP_STORIE_CA",
            attributename="California Revised Storie Index (CA)",
            table="cointerp",
            column="interphrc",
            value_column="interphr",
            rule_name="AGR - California Revised Storie Index (CA)",
            algorithm="Dominant Condition",
            horizon_method="Weighted Average",
            depth_top_cm=None,
            depth_bottom_cm=None,
            tiebreak_rule=-1,
            nulls_as_zero=False,
            required_constraints=(),
            scale="0-1",
            precision=3,
            sentinels=frozenset({99.0, 999.0, -99.0, -999.0}),
            aliases=frozenset(
                {
                    "storie",
                    "california revised storie index",
                    "agr - california revised storie index (ca)",
                }
            ),
        ),
        "csr2": SdvRatingSpec(
            spec_id="csr2",
            provenance_id="SDA:MAPUNIT_IACORNSR",
            attributename="Iowa Corn Suitability Rating CSR2 (IA)",
            table="mapunit",
            column="iacornsr",
            value_column="iacornsr",
            rule_name="",
            algorithm="No Aggregation Necessary",
            horizon_method="Weighted Average",
            depth_top_cm=None,
            depth_bottom_cm=None,
            tiebreak_rule=1,
            nulls_as_zero=False,
            required_constraints=(),
            scale="5-100",
            precision=0,
            sentinels=frozenset({999.0, -99.0, -999.0}),
            aliases=frozenset({"csr2", "iowa corn suitability rating csr2"}),
        ),
        "cpi": SdvRatingSpec(
            spec_id="cpi",
            provenance_id="SDA:COMPONENT_CROPPRODINDEX",
            attributename="Crop Productivity Index",
            table="component",
            column="cropprodindex",
            value_column="cropprodindex",
            rule_name="",
            algorithm="Weighted Average",
            horizon_method="Weighted Average",
            depth_top_cm=None,
            depth_bottom_cm=None,
            tiebreak_rule=1,
            nulls_as_zero=True,
            required_constraints=(),
            scale="1-100",
            precision=0,
            sentinels=frozenset({999.0, -99.0, -999.0}),
            aliases=frozenset({"cpi", "crop productivity index"}),
        ),
        "aws_0_100": SdvRatingSpec(
            spec_id="aws_0_100",
            provenance_id="SDA:CHORIZON_AWC_R_0_100",
            attributename="Available Water Storage",
            table="chorizon",
            column="awc_r",
            value_column="awc_r",
            rule_name="",
            algorithm="Weighted Average",
            horizon_method="Weighted Sum",
            depth_top_cm=0.0,
            depth_bottom_cm=100.0,
            tiebreak_rule=1,
            nulls_as_zero=False,
            required_constraints=(),
            scale="0-100 cm",
            precision=3,
            sentinels=frozenset(),
            aliases=frozenset(),
        ),
        "nonirr_crop_yield": SdvRatingSpec(
            spec_id="nonirr_crop_yield",
            provenance_id="SDA:COCROPYLD_NONIRRYIELD_R",
            attributename="Yields of Non-Irrigated Crops (Component)",
            table="cocropyld",
            column="nonirryield_r",
            value_column="nonirryield_r",
            rule_name="",
            algorithm="Weighted Average",
            horizon_method="Weighted Average",
            depth_top_cm=None,
            depth_bottom_cm=None,
            tiebreak_rule=1,
            nulls_as_zero=True,
            required_constraints=("cropname",),
            scale="varies",
            precision=2,
            sentinels=frozenset(),
            aliases=frozenset(),
        ),
    }
)

# ---------------------------------------------------------------------------
# Derived public constants (single source of truth = the registry)
# ---------------------------------------------------------------------------

_PUBLIC_SELECTOR_IDS = ("nccpi", "csr2", "cpi", "storie")

PRODUCTIVITY_PROVENANCE = {
    spec_id: SDV_RATING_REGISTRY[spec_id].provenance_id for spec_id in _PUBLIC_SELECTOR_IDS
}

PRODUCTIVITY_SEMANTICS = {
    spec_id: {
        "aliases": SDV_RATING_REGISTRY[spec_id].aliases,
        "scale": SDV_RATING_REGISTRY[spec_id].scale,
        "precision": SDV_RATING_REGISTRY[spec_id].precision,
        "sentinels": SDV_RATING_REGISTRY[spec_id].sentinels,
        "provenance": SDV_RATING_REGISTRY[spec_id].provenance_id,
    }
    for spec_id in _PUBLIC_SELECTOR_IDS
}

# ---------------------------------------------------------------------------
# Caveat catalogue (D8)
# ---------------------------------------------------------------------------

SDV_CAVEATS = {
    "dominant_condition": "Rating uses Dominant Condition aggregation.",
    "unrated_sentinel": "Map unit contains unrated placeholder/sentinel code ({value}).",
    "no_coverage": "Map unit has 0% rated component coverage.",
    "no_rating": "Map unit has no numeric productivity rating.",
    "partial_rating": "Partially rated map unit: {rated}% rated out of {total}% total component coverage.",
    "mixed_units": "Mixed yield units: {min_unit} and {max_unit}.",
    "aws_fixed_depth": "Available water storage computed for fixed depth range 0-100 cm.",
    "crop_specific": "Crop-specific yield for '{crop}'.",
    "not_found": "Map unit not found in SDA query results.",
    "unparseable": "Unparseable rating value '{value}'.",
}


_NULLS_AS_ZERO_TABLES = frozenset({"cocropyld", "component"})


def _build_sdv_provenance(
    spec: SdvRatingSpec, constraints: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    """Build the internal structured provenance record for a registry spec (D8).

    Crop yield records also carry ``cropname`` and ``yldunits`` (the latter is
    filled per map unit by the caller).
    """
    record: dict[str, Any] = {
        "id": spec.provenance_id,
        "registry_version": SDV_REGISTRY_VERSION,
        "spec_id": spec.spec_id,
        "attributename": spec.attributename,
        "table": spec.table,
        "column": spec.column,
        "value_column": spec.value_column,
        "rule_name": spec.rule_name,
        "algorithm": spec.algorithm,
        "horizon_method": spec.horizon_method,
        "depth_top_cm": spec.depth_top_cm,
        "depth_bottom_cm": spec.depth_bottom_cm,
        "tiebreak_rule": spec.tiebreak_rule,
        "nulls_as_zero": spec.nulls_as_zero,
        # The SDV flag is recorded as published; the engine applies it only for
        # tables in _NULLS_AS_ZERO_TABLES.
        "null_handling": (
            "nulls_as_zero"
            if spec.nulls_as_zero and spec.table in _NULLS_AS_ZERO_TABLES
            else "exclude_nulls"
        ),
        "scale": spec.scale,
        "precision": spec.precision,
    }
    if "cropname" in spec.required_constraints:
        record["cropname"] = (constraints or {}).get("cropname")
        record["yldunits"] = None
    return record


def _normalize_sdv_string(value: Any) -> str:
    """Normalize an sdvattribute field to a stripped string (empty for None)."""
    if value is None:
        return ""
    return str(value).strip()


def validate_sdv_record(record: Mapping[str, Any]) -> SdvRatingSpec:
    """Validate an sdvattribute record against the registry (two-gate).

    Gate 1: match on normalized attributename, table, column, and rule name.
    Gate 2: structural checks (required fields, supported algorithm, method
    fields equal the spec).

    Returns the matching SdvRatingSpec on success.
    Raises SDAValidationError with distinct messages for each failure mode.
    """
    attr_name = _normalize_sdv_string(record.get("attributename")).lower()
    table = _normalize_sdv_string(record.get("attributetablename")).lower()
    column = _normalize_sdv_string(record.get("attributecolumnname")).lower()
    rule = _normalize_sdv_string(record.get("nasisrulename")).lower()

    # Gate 1: registry match
    matched_spec: SdvRatingSpec | None = None
    for spec in SDV_RATING_REGISTRY.values():
        if (
            spec.attributename.lower() == attr_name
            and spec.table.lower() == table
            and spec.column.lower() == column
            and spec.rule_name.lower() == rule
        ):
            matched_spec = spec
            break

    if matched_spec is None:
        raise SDAValidationError(
            f"Unregistered SDV record: attributename='{attr_name}', "
            f"table='{table}', column='{column}', rule='{rule}'."
        )

    # Gate 2: structural validation
    algorithm = _normalize_sdv_string(record.get("algorithmname"))
    if algorithm not in SUPPORTED_SDV_ALGORITHMS:
        raise SDAValidationError(
            f"Unsupported aggregation method: '{algorithm}'. "
            f"Supported: {sorted(SUPPORTED_SDV_ALGORITHMS)}."
        )

    if algorithm != matched_spec.algorithm:
        raise SDAValidationError(
            f"Malformed SDV record: algorithmname '{algorithm}' "
            f"does not match registry value '{matched_spec.algorithm}' "
            f"for {matched_spec.spec_id}."
        )

    # Table must be a known strategy table
    if table not in _SDV_STRATEGY_TABLES:
        raise SDAValidationError(
            f"Malformed SDV record: table '{table}' is not a supported strategy table."
        )

    # Identifier columns must match identifier pattern
    for col_name in ("attributetablename", "attributecolumnname"):
        col_val = _normalize_sdv_string(record.get(col_name))
        if not re.fullmatch(r"[a-z_][a-z0-9_]*", col_val.lower()):
            raise SDAValidationError(
                f"Malformed SDV record: {col_name} '{col_val}' does not match identifier pattern."
            )

    # Horizon method check for chorizon
    horizon_method = _normalize_sdv_string(record.get("horzaggmeth"))
    if table == "chorizon":
        if horizon_method not in SUPPORTED_HORIZON_METHODS:
            raise SDAValidationError(
                f"Unsupported horizon method: '{horizon_method}'. "
                f"Supported: {sorted(SUPPORTED_HORIZON_METHODS)}."
            )
        if horizon_method != matched_spec.horizon_method:
            raise SDAValidationError(
                f"Malformed SDV record: horzaggmeth '{horizon_method}' "
                f"does not match registry value '{matched_spec.horizon_method}'."
            )

    # Tiebreak rule check
    tiebreak = record.get("tiebreakrule")
    if tiebreak is not None:
        try:
            tiebreak_int = int(tiebreak)
        except (ValueError, TypeError):
            raise SDAValidationError(
                f"Malformed SDV record: tiebreakrule '{tiebreak}' is not an integer."
            )
        if tiebreak_int != matched_spec.tiebreak_rule:
            raise SDAValidationError(
                f"Malformed SDV record: tiebreakrule {tiebreak_int} "
                f"does not match registry value {matched_spec.tiebreak_rule}."
            )

    return matched_spec


_CROP_RE = re.compile(r"^[A-Za-z0-9 ,()\-/'.]{1,80}$")


def _validate_crop(cropname: str) -> str:
    """Validate a crop name for SQL interpolation."""
    crop = str(cropname).strip()
    if not crop:
        raise SDAValidationError("Crop name is required for this rating.")
    if ";" in crop or "--" in crop:
        raise SDAValidationError(f"Invalid characters in crop name: '{cropname}'.")
    if not _CROP_RE.fullmatch(crop):
        raise SDAValidationError(f"Invalid crop name: '{cropname}'.")
    return crop


def resolve_sdv_spec(
    selector: str | None = None,
    record: Mapping[str, Any] | None = None,
    constraints: Mapping[str, Any] | None = None,
) -> tuple[SdvRatingSpec, dict[str, Any]]:
    """Resolve a rating specification from a selector or raw record.

    Exactly one of *selector* or *record* must be provided.

    - *selector* resolves via exact alias match against the registry.
    - *record* goes through validate_sdv_record (two-gate validation).

    Required constraints (e.g. cropname) are validated and returned in the
    resolved constraints dict.
    """
    if selector is not None and record is not None:
        raise SDAValidationError("Provide either a selector or a record, not both.")
    if selector is None and record is None:
        raise SDAValidationError("A selector or an SDV record is required.")

    if selector is not None:
        sel_lower = str(selector).strip().lower()
        spec: SdvRatingSpec | None = None
        for candidate_id, candidate_spec in SDV_RATING_REGISTRY.items():
            if sel_lower == candidate_id or sel_lower in candidate_spec.aliases:
                spec = candidate_spec
                break
        if spec is None:
            raise SDAValidationError(f"Unregistered SDV selector: '{selector}'.")
    else:
        assert record is not None
        spec = validate_sdv_record(record)

    resolved_constraints: dict[str, Any] = {}
    if constraints:
        for key, val in constraints.items():
            resolved_constraints[key] = val

    for req in spec.required_constraints:
        if req == "cropname":
            crop = resolved_constraints.get("cropname")
            if crop is None:
                raise SDAValidationError(f"Constraint '{req}' is required for {spec.spec_id}.")
            resolved_constraints["cropname"] = _validate_crop(crop)
        elif req not in resolved_constraints:
            raise SDAValidationError(f"Constraint '{req}' is required for {spec.spec_id}.")

    return spec, resolved_constraints


def _resolve_productivity_spec(
    index_type: str,
    attribute_meta: Mapping[str, Any] | None,
    constraints: Mapping[str, Any] | None,
) -> tuple[SdvRatingSpec, dict[str, Any]]:
    """Resolve the client entry points to one registry spec (one engine, D9).

    ``attribute_meta`` (explicit metadata selection) takes precedence; otherwise
    ``index_type`` must be one of the four public fixed selectors (D1).
    """
    if attribute_meta:
        return resolve_sdv_spec(
            record=attribute_meta,
            constraints=_record_constraints(attribute_meta, constraints),
        )
    selector = _normalize_productivity_index(index_type)
    return resolve_sdv_spec(selector=selector, constraints=constraints)


# Fixed SQL query templates - no user SQL passthrough allowed
SQL_POINT_LOOKUP = """\
SELECT
    m.mukey,
    m.musym,
    m.muname,
    m.farmlndcl,
    l.areasymbol
FROM SDA_Get_Mukey_from_intersection_with_WktWgs84('POINT({longitude} {latitude})') AS p
INNER JOIN mapunit AS m ON p.mukey = m.mukey
INNER JOIN legend AS l ON m.lkey = l.lkey
"""

SQL_MUKEY_LOOKUP = """\
SELECT
    m.mukey,
    m.musym,
    m.muname,
    m.farmlndcl,
    l.areasymbol
FROM mapunit AS m
INNER JOIN legend AS l ON m.lkey = l.lkey
WHERE m.mukey = '{mukey}'
"""

SQL_POLYGON_LOOKUP = """\
WITH geom_mukeys AS (
    SELECT DISTINCT mukey
    FROM SDA_Get_Mukey_from_intersection_with_WktWgs84('{wkt}')
)
SELECT
    m.mukey,
    m.musym,
    m.muname,
    m.farmlndcl,
    l.areasymbol
FROM geom_mukeys AS g
INNER JOIN mapunit AS m ON g.mukey = m.mukey
INNER JOIN legend AS l ON m.lkey = l.lkey
"""

SQL_SPATIAL_INTERSECTION_CLIPPED = """\
WITH geom_data (geom, mukey) AS (
    SELECT
        mupolygongeo.STIntersection(geometry::STGeomFromText('{wkt}', 4326)) AS geom,
        mukey
    FROM mupolygon
    WHERE mupolygongeo.STIntersects(geometry::STGeomFromText('{wkt}', 4326)) = 1
)
SELECT
    m.mukey,
    m.musym,
    m.muname,
    m.farmlndcl,
    l.areasymbol,
    {area_expr} AS area_ac{geom_column}
FROM geom_data
INNER JOIN mapunit AS m ON geom_data.mukey = m.mukey
INNER JOIN legend AS l ON m.lkey = l.lkey
"""

SQL_SPATIAL_INTERSECTION_OVERLAP = """\
WITH geom_data (geom, mukey) AS (
    SELECT
        mupolygongeo AS geom,
        mukey
    FROM mupolygon
    WHERE mupolygongeo.STIntersects(geometry::STGeomFromText('{wkt}', 4326)) = 1
)
SELECT
    m.mukey,
    m.musym,
    m.muname,
    m.farmlndcl,
    l.areasymbol,
    {area_expr} AS area_ac{geom_column}
FROM geom_data
INNER JOIN mapunit AS m ON geom_data.mukey = m.mukey
INNER JOIN legend AS l ON m.lkey = l.lkey
"""

SQL_INTERPRETATION_CATALOG = """\
SELECT DISTINCT nasisrulename AS mrulename
FROM sdvattribute
WHERE attributetablename = 'cointerp'
  AND nasisrulename IS NOT NULL
ORDER BY nasisrulename
"""

SQL_INTERPRETATION_WEIGHTED_AVG = """\
WITH comp_interp AS (
    SELECT
        m.mukey,
        l.areasymbol,
        m.musym,
        m.muname,
        c.cokey,
        c.comppct_r,
        ci.interphr,
        ci.interphrc
    FROM legend AS l
    INNER JOIN mapunit AS m ON m.lkey = l.lkey
    INNER JOIN component AS c ON c.mukey = m.mukey
    LEFT JOIN cointerp AS ci ON ci.cokey = c.cokey
        AND ci.ruledepth = 0
        AND ci.mrulename = '{rule_name}'
    WHERE m.mukey IN ({mukeys_csv})
      AND c.compkind != 'miscellaneous area'
)
SELECT
    mukey,
    areasymbol,
    musym,
    muname,
    ROUND(SUM(interphr * comppct_r) / NULLIF(SUM(CASE WHEN interphr IS NOT NULL THEN comppct_r ELSE 0 END), 0), 3) AS numeric_rating,
    MAX(interphrc) AS rating_class,
    SUM(CASE WHEN interphr IS NOT NULL THEN comppct_r ELSE 0 END) AS rated_pct,
    SUM(comppct_r) AS total_pct
FROM comp_interp
GROUP BY mukey, areasymbol, musym, muname
"""

SQL_INTERPRETATION_DOMINANT_COMP = """\
WITH ranked_components AS (
    SELECT
        m.mukey,
        l.areasymbol,
        m.musym,
        m.muname,
        c.cokey,
        c.compname,
        c.comppct_r,
        ci.interphr AS numeric_rating,
        ci.interphrc AS rating_class,
        ROW_NUMBER() OVER (PARTITION BY m.mukey ORDER BY c.comppct_r DESC, c.cokey ASC) AS rnk
    FROM legend AS l
    INNER JOIN mapunit AS m ON m.lkey = l.lkey
    INNER JOIN component AS c ON c.mukey = m.mukey
    LEFT JOIN cointerp AS ci ON ci.cokey = c.cokey
        AND ci.ruledepth = 0
        AND ci.mrulename = '{rule_name}'
    WHERE m.mukey IN ({mukeys_csv})
      AND c.compkind != 'miscellaneous area'
)
SELECT
    mukey,
    areasymbol,
    musym,
    muname,
    cokey,
    compname,
    comppct_r AS dominant_pct,
    numeric_rating,
    rating_class
FROM ranked_components
WHERE rnk = 1
"""

SQL_SDV_ATTRIBUTE_LOOKUP = """\
SELECT
    attributekey,
    attributename,
    attributetablename,
    attributecolumnname,
    attributelogicaldatatype,
    nasisrulename,
    ruledesign,
    algorithmname,
    horzaggmeth,
    tiebreakrule,
    depthqualifiermode,
    layerdepthtotop,
    layerdepthtobottom,
    layerdepthuom,
    interpnullsaszeroflag,
    nullratingreplacementvalue,
    primaryconcolname,
    secondaryconcolname,
    componentpercentcutoff,
    resultcolumnname,
    notratedphrase,
    attributetype
FROM sdvattribute
WHERE attributename LIKE '{pattern}'
   OR nasisrulename LIKE '{pattern}'
ORDER BY attributename
"""

# Productivity SQL is generated only by the per-strategy builders below
# (build_sdv_rating_query / build_sdv_county_max_query); the former fixed
# NCCPI/CSR2/CPI templates were retired after SQL parity was verified (D9).

# Tables with at least one registry record; derived so it cannot drift from the
# registry. A fast early check only: resolve_sdv_spec still rejects any record
# that is not registered.
ALLOWED_SDV_TABLES = frozenset(spec.table for spec in SDV_RATING_REGISTRY.values())


def _normalize_productivity_index(index_type: str) -> str:
    """Normalize a public fixed selector (nccpi, csr2, cpi, storie) by exact alias (D1)."""
    selector = str(index_type).strip().lower()
    for normalized, semantics in PRODUCTIVITY_SEMANTICS.items():
        if selector in semantics["aliases"]:
            return normalized
    raise SDAValidationError(
        f"Unsupported productivity index type '{index_type}'. "
        f"{SUPPORTED_INDEX_MSG} "
        "Explicit attribute metadata is required for custom SDV queries."
    )


def _record_constraints(
    attribute_meta: Mapping[str, Any] | None,
    constraints: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Merge explicit constraints with a legacy ``cropname`` key on the record."""
    merged: dict[str, Any] = {}
    if attribute_meta and attribute_meta.get("cropname"):
        merged["cropname"] = attribute_meta["cropname"]
    if constraints:
        merged.update(constraints)
    return merged or None


def validate_survey_area_symbol(areasymbol: str) -> str:
    """Validate and normalize a soil survey area symbol."""
    clean_area = str(areasymbol).strip().upper()
    if not re.fullmatch(r"[A-Z0-9]{2,10}", clean_area):
        raise SDAValidationError(f"Invalid soil survey area symbol '{areasymbol}'.")
    return clean_area


def _spec_sentinel_predicate(spec: SdvRatingSpec, expression: str) -> str:
    """Build an SQL sentinel predicate from a registry spec."""
    if not spec.sentinels:
        return f"{expression} IS NOT NULL"
    sentinels = ", ".join(str(int(v)) if v.is_integer() else str(v) for v in sorted(spec.sentinels))
    return f"{expression} IS NOT NULL AND {expression} NOT IN ({sentinels})"


def _validate_mukeys(mukeys: str | list[str | int]) -> str:
    """Validate mukeys and return a comma-quoted SQL list."""
    if isinstance(mukeys, str):
        items = mukeys.split(",")
    else:
        items = mukeys
    try:
        clean = [str(item).strip().strip("'") for item in items]
        if not clean or any(not re.fullmatch(r"[1-9][0-9]*", m) for m in clean):
            raise ValueError
    except (TypeError, ValueError) as exc:
        raise SDAValidationError(
            f"Map unit keys must be positive numeric digits; received '{mukeys}'"
        ) from exc
    return ", ".join(f"'{m}'" for m in clean)


def _build_cointerp_wa_rating(spec: SdvRatingSpec, mukeys_sql: str) -> str:
    """cointerp + Weighted Average (NCCPI-style)."""
    sentinel = _spec_sentinel_predicate(spec, "rating")
    rule = spec.rule_name.replace("'", "''")
    return f"""\
WITH comp_rating AS (
    SELECT
        m.mukey,
        l.areasymbol,
        m.musym,
        m.muname,
        c.cokey,
        c.comppct_r,
        ci.{spec.value_column} AS rating
    FROM legend AS l
    INNER JOIN mapunit AS m ON m.lkey = l.lkey
    INNER JOIN component AS c ON c.mukey = m.mukey
    LEFT JOIN cointerp AS ci ON ci.cokey = c.cokey
        AND ci.ruledepth = 0
        AND ci.mrulename = '{rule}'
    WHERE m.mukey IN ({mukeys_sql})
      AND c.compkind != 'miscellaneous area'
)
SELECT
    mukey,
    areasymbol,
    musym,
    muname,
    ROUND(SUM(CASE WHEN {sentinel} THEN rating * comppct_r ELSE 0 END) / NULLIF(SUM(CASE WHEN {sentinel} THEN comppct_r ELSE 0 END), 0), {spec.precision}) AS numeric_rating,
    SUM(CASE WHEN {sentinel} THEN comppct_r ELSE 0 END) AS rated_pct,
    SUM(comppct_r) AS total_pct
FROM comp_rating
GROUP BY mukey, areasymbol, musym, muname
"""


def _build_cointerp_wa_county_max(spec: SdvRatingSpec, areasymbol: str) -> str:
    """cointerp + Weighted Average county max (NCCPI-style)."""
    sentinel = _spec_sentinel_predicate(spec, f"ci.{spec.value_column}")
    rule = spec.rule_name.replace("'", "''")
    return f"""\
SELECT
    MAX(ci.{spec.value_column}) AS max_county_rating
FROM legend AS l
INNER JOIN mapunit AS m ON m.lkey = l.lkey
INNER JOIN component AS c ON c.mukey = m.mukey
INNER JOIN cointerp AS ci ON ci.cokey = c.cokey
WHERE l.areasymbol = '{areasymbol}'
  AND ci.ruledepth = 0
  AND ci.mrulename = '{rule}'
  AND {sentinel}
  AND c.compkind != 'miscellaneous area'
"""


def _build_cointerp_dc_rating(spec: SdvRatingSpec, mukeys_sql: str) -> str:
    """cointerp + Dominant Condition (Storie-style, D5).

    The rounded ``interphr`` value is the condition class.  Per map unit the
    class with the largest summed ``comppct_r`` wins; ties follow
    ``tiebreakrule`` (-1 lower wins, 1 higher wins).  ``rated_pct`` and
    ``total_pct`` keep their Weighted Average meaning (rated vs all non-misc
    components); ``dominant_pct`` is the winning class's summed percent.  Map
    units with no rated component still return a row with a NULL rating.
    """
    col = spec.value_column
    sentinel = _spec_sentinel_predicate(spec, f"ci.{col}")
    rule = spec.rule_name.replace("'", "''")
    tiebreak_dir = "ASC" if spec.tiebreak_rule < 0 else "DESC"
    return f"""\
WITH comp_rating AS (
    SELECT
        m.mukey,
        l.areasymbol,
        m.musym,
        m.muname,
        c.comppct_r,
        CASE WHEN {sentinel} THEN ROUND(ci.{col}, {spec.precision}) END AS rating_val
    FROM legend AS l
    INNER JOIN mapunit AS m ON m.lkey = l.lkey
    INNER JOIN component AS c ON c.mukey = m.mukey
    LEFT JOIN cointerp AS ci ON ci.cokey = c.cokey
        AND ci.ruledepth = 0
        AND ci.mrulename = '{rule}'
    WHERE m.mukey IN ({mukeys_sql})
      AND c.compkind != 'miscellaneous area'
),
mu_totals AS (
    SELECT
        mukey,
        areasymbol,
        musym,
        muname,
        SUM(CASE WHEN rating_val IS NOT NULL THEN comppct_r ELSE 0 END) AS rated_pct,
        SUM(comppct_r) AS total_pct
    FROM comp_rating
    GROUP BY mukey, areasymbol, musym, muname
),
classes AS (
    SELECT
        mukey,
        rating_val,
        SUM(comppct_r) AS class_pct,
        ROW_NUMBER() OVER (
            PARTITION BY mukey
            ORDER BY SUM(comppct_r) DESC, rating_val {tiebreak_dir}
        ) AS rn
    FROM comp_rating
    WHERE rating_val IS NOT NULL
    GROUP BY mukey, rating_val
)
SELECT
    t.mukey,
    t.areasymbol,
    t.musym,
    t.muname,
    d.rating_val AS numeric_rating,
    d.class_pct AS dominant_pct,
    t.rated_pct,
    t.total_pct
FROM mu_totals AS t
LEFT JOIN classes AS d ON d.mukey = t.mukey AND d.rn = 1
"""


def _build_cointerp_dc_county_max(spec: SdvRatingSpec, areasymbol: str) -> str:
    """cointerp + Dominant Condition county max: MAX of per-mukey dominant classes (D5)."""
    col = spec.value_column
    sentinel = _spec_sentinel_predicate(spec, f"ci.{col}")
    rule = spec.rule_name.replace("'", "''")
    tiebreak_dir = "ASC" if spec.tiebreak_rule < 0 else "DESC"
    return f"""\
WITH comp_rating AS (
    SELECT
        m.mukey,
        c.comppct_r,
        ROUND(ci.{col}, {spec.precision}) AS rating_val
    FROM legend AS l
    INNER JOIN mapunit AS m ON m.lkey = l.lkey
    INNER JOIN component AS c ON c.mukey = m.mukey
    INNER JOIN cointerp AS ci ON ci.cokey = c.cokey
    WHERE l.areasymbol = '{areasymbol}'
      AND ci.ruledepth = 0
      AND ci.mrulename = '{rule}'
      AND {sentinel}
      AND c.compkind != 'miscellaneous area'
),
classes AS (
    SELECT
        mukey,
        rating_val,
        ROW_NUMBER() OVER (
            PARTITION BY mukey
            ORDER BY SUM(comppct_r) DESC, rating_val {tiebreak_dir}
        ) AS rn
    FROM comp_rating
    GROUP BY mukey, rating_val
)
SELECT MAX(rating_val) AS max_county_rating
FROM classes
WHERE rn = 1
"""


def _build_component_wa_rating(spec: SdvRatingSpec, mukeys_sql: str) -> str:
    """component + Weighted Average (CPI-style).

    With the SDV nulls-as-zero flag, null-rated components count as 0 in a
    map unit that has at least one rated component; a map unit with no rated
    component stays null (unrated).  ``rated_pct`` is always the percent of
    components with a non-null value.
    """
    col = spec.value_column
    valid_value = f"c.{col} IS NOT NULL AND {_spec_sentinel_predicate(spec, f'c.{col}')}"
    if spec.nulls_as_zero and spec.table in _NULLS_AS_ZERO_TABLES:
        rating_sql = f"""\
    CASE WHEN SUM(CASE WHEN {valid_value} THEN 1 ELSE 0 END) > 0
        THEN SUM(CASE WHEN {valid_value}
            THEN CAST(c.{col} AS float) * c.comppct_r ELSE 0 END)
            / NULLIF(SUM(c.comppct_r), 0)
    END AS numeric_rating,"""
    else:
        rating_sql = f"""\
    SUM(CASE WHEN {valid_value}
        THEN CAST(c.{col} AS float) * c.comppct_r ELSE 0 END)
        / NULLIF(SUM(CASE WHEN {valid_value}
            THEN c.comppct_r ELSE 0 END), 0) AS numeric_rating,"""
    return f"""\
SELECT
    m.mukey,
    l.areasymbol,
    m.musym,
    m.muname,
{rating_sql}
    SUM(CASE WHEN {valid_value} THEN c.comppct_r ELSE 0 END) AS rated_pct,
    SUM(c.comppct_r) AS total_pct
FROM legend AS l
INNER JOIN mapunit AS m ON m.lkey = l.lkey
INNER JOIN component AS c ON c.mukey = m.mukey
WHERE m.mukey IN ({mukeys_sql})
  AND c.compkind != 'miscellaneous area'
GROUP BY m.mukey, l.areasymbol, m.musym, m.muname
"""


def _build_component_wa_county_max(spec: SdvRatingSpec, areasymbol: str) -> str:
    """component + Weighted Average county max (CPI-style)."""
    col = spec.value_column
    valid_value = _spec_sentinel_predicate(spec, f"c.{col}")
    return f"""\
SELECT
    MAX(CAST(c.{col} AS float)) AS max_county_rating
FROM legend AS l
INNER JOIN mapunit AS m ON m.lkey = l.lkey
INNER JOIN component AS c ON c.mukey = m.mukey
WHERE l.areasymbol = '{areasymbol}'
  AND {valid_value}
  AND c.compkind != 'miscellaneous area'
"""


def _build_mapunit_no_agg_rating(spec: SdvRatingSpec, mukeys_sql: str) -> str:
    """mapunit + No Aggregation Necessary (CSR2-style)."""
    col = spec.value_column
    # Parity with the retired CSR2 template: rated_pct reflects non-null only;
    # sentinels are screened client-side so the reported rated_pct is unchanged.
    return f"""\
SELECT
    m.mukey,
    l.areasymbol,
    m.musym,
    m.muname,
    CAST(m.{col} AS float) AS numeric_rating,
    CASE WHEN m.{col} IS NOT NULL THEN 100.0 ELSE 0.0 END AS rated_pct,
    100.0 AS total_pct
FROM legend AS l
INNER JOIN mapunit AS m ON m.lkey = l.lkey
WHERE m.mukey IN ({mukeys_sql})
"""


def _build_mapunit_no_agg_county_max(spec: SdvRatingSpec, areasymbol: str) -> str:
    """mapunit + No Aggregation Necessary county max (CSR2-style)."""
    col = spec.value_column
    return f"""\
SELECT
    MAX(CAST(m.{col} AS float)) AS max_county_rating
FROM legend AS l
INNER JOIN mapunit AS m ON m.lkey = l.lkey
WHERE l.areasymbol = '{areasymbol}'
  AND m.{col} IS NOT NULL
"""


def _build_chorizon_ws_rating(spec: SdvRatingSpec, mukeys_sql: str) -> str:
    """chorizon + Weighted Average + horizon Weighted Sum (D6, 0-100 cm)."""
    col = spec.value_column
    depth_top = int(spec.depth_top_cm) if spec.depth_top_cm is not None else 0
    depth_bot = int(spec.depth_bottom_cm) if spec.depth_bottom_cm is not None else 100
    return f"""\
WITH hz_weighted AS (
    SELECT
        c.cokey,
        SUM(CAST(ch.{col} AS float) * (CASE WHEN ch.hzdepb_r > {depth_bot} THEN {depth_bot} ELSE ch.hzdepb_r END - CASE WHEN ch.hzdept_r < {depth_top} THEN {depth_top} ELSE ch.hzdept_r END))
            AS attr_sum
    FROM component AS c
    INNER JOIN chorizon AS ch ON ch.cokey = c.cokey
    WHERE ch.{col} IS NOT NULL
      AND ch.hzdepb_r > {depth_top}
      AND ch.hzdept_r < {depth_bot}
    GROUP BY c.cokey
),
component_values AS (
    SELECT
        m.mukey,
        l.areasymbol,
        m.musym,
        m.muname,
        c.comppct_r,
        h.attr_sum
    FROM legend AS l
    INNER JOIN mapunit AS m ON m.lkey = l.lkey
    INNER JOIN component AS c ON c.mukey = m.mukey
    LEFT JOIN hz_weighted AS h ON h.cokey = c.cokey
    WHERE m.mukey IN ({mukeys_sql})
      AND c.compkind != 'miscellaneous area'
)
SELECT
    mukey,
    areasymbol,
    musym,
    muname,
    ROUND(SUM(CASE WHEN attr_sum IS NOT NULL THEN attr_sum * comppct_r ELSE 0 END)
        / NULLIF(SUM(CASE WHEN attr_sum IS NOT NULL THEN comppct_r ELSE 0 END), 0), {spec.precision}) AS numeric_rating,
    SUM(CASE WHEN attr_sum IS NOT NULL THEN comppct_r ELSE 0 END) AS rated_pct,
    SUM(comppct_r) AS total_pct
FROM component_values
GROUP BY mukey, areasymbol, musym, muname
"""


def _build_chorizon_ws_county_max(spec: SdvRatingSpec, areasymbol: str) -> str:
    """chorizon + Weighted Average + horizon Weighted Sum county max (D6)."""
    col = spec.value_column
    depth_top = int(spec.depth_top_cm) if spec.depth_top_cm is not None else 0
    depth_bot = int(spec.depth_bottom_cm) if spec.depth_bottom_cm is not None else 100
    return f"""\
WITH hz_weighted AS (
    SELECT
        c.cokey,
        c.comppct_r,
        m.mukey,
        SUM(CAST(ch.{col} AS float) * (CASE WHEN ch.hzdepb_r > {depth_bot} THEN {depth_bot} ELSE ch.hzdepb_r END - CASE WHEN ch.hzdept_r < {depth_top} THEN {depth_top} ELSE ch.hzdept_r END))
            AS attr_sum
    FROM legend AS l
    INNER JOIN mapunit AS m ON m.lkey = l.lkey
    INNER JOIN component AS c ON c.mukey = m.mukey
    INNER JOIN chorizon AS ch ON ch.cokey = c.cokey
    WHERE l.areasymbol = '{areasymbol}'
      AND c.compkind != 'miscellaneous area'
      AND ch.{col} IS NOT NULL
      AND ch.hzdepb_r > {depth_top}
      AND ch.hzdept_r < {depth_bot}
    GROUP BY c.cokey, c.comppct_r, m.mukey
),
mukey_val AS (
    SELECT mukey, SUM(attr_sum * comppct_r) / NULLIF(SUM(comppct_r), 0) AS mukey_rating
    FROM hz_weighted
    GROUP BY mukey
)
SELECT MAX(mukey_rating) AS max_county_rating
FROM mukey_val
"""


def _build_cocropyld_wa_rating(
    spec: SdvRatingSpec, mukeys_sql: str, constraints: dict[str, Any] | None = None
) -> str:
    """cocropyld + Weighted Average (D7, crop filter, nulls-as-zero, mixed-unit detection)."""
    col = spec.value_column
    crop = ""
    if constraints and "cropname" in constraints:
        crop = constraints["cropname"].replace("'", "''")
    if not crop:
        raise SDAValidationError("Crop name is required for crop yield ratings.")

    if spec.nulls_as_zero:
        # nulls-as-zero: COALESCE nulls to 0 in both numerator and denominator
        rating_expr = f"COALESCE(CAST(cy.{col} AS float), 0)"
        weight_expr = "c.comppct_r"
    else:
        # Exclude nulls
        rating_expr = f"CAST(cy.{col} AS float)"
        weight_expr = "CASE WHEN cy.{col} IS NOT NULL THEN c.comppct_r ELSE 0 END"

    if spec.nulls_as_zero:
        return f"""\
WITH comp_yield AS (
    SELECT
        m.mukey,
        l.areasymbol,
        m.musym,
        m.muname,
        c.comppct_r,
        {rating_expr} AS rating,
        cy.yldunits
    FROM legend AS l
    INNER JOIN mapunit AS m ON m.lkey = l.lkey
    INNER JOIN component AS c ON c.mukey = m.mukey
    INNER JOIN cocropyld AS cy ON cy.cokey = c.cokey
    WHERE m.mukey IN ({mukeys_sql})
      AND c.compkind != 'miscellaneous area'
      AND cy.cropname = '{crop}'
)
SELECT
    mukey,
    areasymbol,
    musym,
    muname,
    ROUND(SUM(rating * comppct_r) / NULLIF(SUM(comppct_r), 0), {spec.precision}) AS numeric_rating,
    SUM(comppct_r) AS rated_pct,
    SUM(comppct_r) AS total_pct,
    COUNT(DISTINCT yldunits) AS unit_count,
    MIN(yldunits) AS yldunits_min,
    MAX(yldunits) AS yldunits_max
FROM comp_yield
GROUP BY mukey, areasymbol, musym, muname
"""
    else:
        return f"""\
WITH comp_yield AS (
    SELECT
        m.mukey,
        l.areasymbol,
        m.musym,
        m.muname,
        c.comppct_r,
        {rating_expr} AS rating,
        cy.yldunits
    FROM legend AS l
    INNER JOIN mapunit AS m ON m.lkey = l.lkey
    INNER JOIN component AS c ON c.mukey = m.mukey
    INNER JOIN cocropyld AS cy ON cy.cokey = c.cokey
    WHERE m.mukey IN ({mukeys_sql})
      AND c.compkind != 'miscellaneous area'
      AND cy.cropname = '{crop}'
      AND cy.{col} IS NOT NULL
)
SELECT
    mukey,
    areasymbol,
    musym,
    muname,
    ROUND(SUM(rating * comppct_r) / NULLIF(SUM({weight_expr}), 0), {spec.precision}) AS numeric_rating,
    SUM({weight_expr}) AS rated_pct,
    SUM(comppct_r) AS total_pct,
    COUNT(DISTINCT yldunits) AS unit_count,
    MIN(yldunits) AS yldunits_min,
    MAX(yldunits) AS yldunits_max
FROM comp_yield
GROUP BY mukey, areasymbol, musym, muname
"""


def _build_cocropyld_wa_county_max(
    spec: SdvRatingSpec, areasymbol: str, constraints: dict[str, Any] | None = None
) -> str:
    """cocropyld + Weighted Average county max (D7)."""
    col = spec.value_column
    crop = ""
    if constraints and "cropname" in constraints:
        crop = constraints["cropname"].replace("'", "''")
    if not crop:
        raise SDAValidationError("Crop name is required for crop yield ratings.")

    return f"""\
SELECT
    MAX(CAST(cy.{col} AS float)) AS max_county_rating
FROM legend AS l
INNER JOIN mapunit AS m ON m.lkey = l.lkey
INNER JOIN component AS c ON c.mukey = m.mukey
INNER JOIN cocropyld AS cy ON cy.cokey = c.cokey
WHERE l.areasymbol = '{areasymbol}'
  AND c.compkind != 'miscellaneous area'
  AND cy.cropname = '{crop}'
  AND cy.{col} IS NOT NULL
"""


_BUILDERS_RATING = {
    ("cointerp", "Weighted Average"): _build_cointerp_wa_rating,
    ("cointerp", "Dominant Condition"): _build_cointerp_dc_rating,
    ("component", "Weighted Average"): _build_component_wa_rating,
    ("mapunit", "No Aggregation Necessary"): _build_mapunit_no_agg_rating,
    ("chorizon", "Weighted Average"): _build_chorizon_ws_rating,
    ("cocropyld", "Weighted Average"): _build_cocropyld_wa_rating,
}

_BUILDERS_COUNTY_MAX = {
    ("cointerp", "Weighted Average"): _build_cointerp_wa_county_max,
    ("cointerp", "Dominant Condition"): _build_cointerp_dc_county_max,
    ("component", "Weighted Average"): _build_component_wa_county_max,
    ("mapunit", "No Aggregation Necessary"): _build_mapunit_no_agg_county_max,
    ("chorizon", "Weighted Average"): _build_chorizon_ws_county_max,
    ("cocropyld", "Weighted Average"): _build_cocropyld_wa_county_max,
}


def build_sdv_rating_query(
    spec: SdvRatingSpec,
    mukeys: str | list[str | int],
    constraints: dict[str, Any] | None = None,
) -> str:
    """Build a per-mukey rating SQL query from a validated SDV rating spec.

    Dispatches on (spec.table, spec.algorithm) to the appropriate template.
    Raises SDAValidationError for unsupported table+algorithm combinations.
    """
    mukeys_sql = _validate_mukeys(mukeys)
    key = (spec.table, spec.algorithm)
    builder = _BUILDERS_RATING.get(key)
    if builder is None:
        raise SDAValidationError(
            f"Unsupported aggregation method: table='{spec.table}', algorithm='{spec.algorithm}'."
        )
    if spec.table == "cocropyld":
        return builder(spec, mukeys_sql, constraints)
    return builder(spec, mukeys_sql)


def build_sdv_county_max_query(
    spec: SdvRatingSpec,
    areasymbol: str,
    constraints: dict[str, Any] | None = None,
) -> str:
    """Build a county-max rating SQL query from a validated SDV rating spec.

    Dispatches on (spec.table, spec.algorithm) to the appropriate template.
    Raises SDAValidationError for unsupported table+algorithm combinations.
    """
    clean_area = validate_survey_area_symbol(areasymbol)
    key = (spec.table, spec.algorithm)
    builder = _BUILDERS_COUNTY_MAX.get(key)
    if builder is None:
        raise SDAValidationError(
            f"Unsupported aggregation method: table='{spec.table}', algorithm='{spec.algorithm}'."
        )
    if spec.table == "cocropyld":
        return builder(spec, clean_area, constraints)
    return builder(spec, clean_area)


def build_dynamic_sdv_query(
    attribute_meta: dict[str, Any],
    mukeys_csv: str | list[str | int],
) -> str:
    """Dynamically build an SDA query from an sdvattribute metadata record.

    Thin wrapper: the record must pass two-gate registry validation
    (``validate_sdv_record``); unregistered records raise before any SQL is
    built (D2).  A legacy ``cropname`` key on the record is honoured.
    """
    table = str(attribute_meta.get("attributetablename", "")).strip().lower()
    if table not in ALLOWED_SDV_TABLES:
        raise SDAValidationError(
            f"Unsupported or unallowed SDV table '{table}'. Allowed: {sorted(ALLOWED_SDV_TABLES)}"
        )

    spec, resolved = resolve_sdv_spec(
        record=attribute_meta, constraints=_record_constraints(attribute_meta)
    )
    return build_sdv_rating_query(spec, mukeys_csv, resolved)


def build_dynamic_sdv_county_max_query(
    attribute_meta: dict[str, Any],
    areasymbol: str,
) -> str:
    """Dynamically build an SDA query for maximum county rating from sdvattribute metadata.

    Thin wrapper over ``build_sdv_county_max_query``; unregistered records
    raise before any SQL is built (D2).
    """
    areasymbol = validate_survey_area_symbol(areasymbol)
    table = str(attribute_meta.get("attributetablename", "")).strip().lower()

    if table not in ALLOWED_SDV_TABLES:
        raise SDAValidationError(
            f"Unsupported or unallowed SDV table '{table}'. Allowed: {sorted(ALLOWED_SDV_TABLES)}"
        )

    spec, resolved = resolve_sdv_spec(
        record=attribute_meta, constraints=_record_constraints(attribute_meta)
    )
    return build_sdv_county_max_query(spec, areasymbol, resolved)


class SDAClientError(Exception):
    """Base exception for SDA Client errors."""


class SDAValidationError(SDAClientError):
    """Raised when coordinate or mukey validation fails."""


class SDAQueryError(SDAClientError):
    """Raised when SDA returns an API-level error or invalid response."""


class SDATimeoutError(SDAClientError):
    """Raised when an SDA request times out."""


class SDAServiceUnavailableError(SDAClientError):
    """Raised when SDA is temporarily unavailable (e.g. daily maintenance window)."""


class SDAClient:
    """Client for USDA NRCS Soil Data Access (SDA) REST service."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url or settings.sda_tabular_url
        self.timeout = timeout or settings.request_timeout_seconds
        self.max_retries = max_retries if max_retries is not None else settings.max_retries
        self._http_client = http_client
        self._cached_rule_names: list[str] | None = None

    @staticmethod
    def validate_coordinates(latitude: float, longitude: float) -> tuple[float, float]:
        """Validate and return WGS84 geographic coordinates.

        Args:
            latitude: Latitude in decimal degrees [-90.0, 90.0].
            longitude: Longitude in decimal degrees [-180.0, 180.0].

        Returns:
            Validated (latitude, longitude) float tuple.

        Raises:
            SDAValidationError: If coordinates are out of valid geographic range or non-numeric.
        """
        try:
            lat = float(latitude)
            lon = float(longitude)
        except (TypeError, ValueError) as exc:
            raise SDAValidationError(
                f"Invalid coordinate format: lat={latitude}, lon={longitude}"
            ) from exc

        if not (-90.0 <= lat <= 90.0):
            raise SDAValidationError(
                f"Latitude must be between -90.0 and 90.0 degrees; received {lat}"
            )
        if not (-180.0 <= lon <= 180.0):
            raise SDAValidationError(
                f"Longitude must be between -180.0 and 180.0 degrees; received {lon}"
            )

        return lat, lon

    @staticmethod
    def validate_mukey(mukey: str | int) -> str:
        """Validate and return a normalized SSURGO map unit key (mukey).

        Args:
            mukey: Positive numeric identifier string or integer.

        Returns:
            Clean string representation of mukey.

        Raises:
            SDAValidationError: If mukey is not a valid positive integer string.
        """
        mukey_str = str(mukey).strip()
        if not mukey_str.isdigit() or int(mukey_str) <= 0:
            raise SDAValidationError(
                f"Map unit key (mukey) must be a positive integer; received '{mukey}'"
            )
        return mukey_str

    @staticmethod
    def validate_wkt(wkt_geometry: str) -> str:
        """Validate and sanitize a WGS84 WKT Polygon or MultiPolygon string.

        Args:
            wkt_geometry: WKT string.

        Returns:
            Normalized WKT string.

        Raises:
            SDAValidationError: If WKT is invalid or not Polygon/MultiPolygon.
        """
        try:
            return validate_and_sanitize_polygon_wkt(wkt_geometry)
        except GeometryValidationError as exc:
            raise SDAValidationError(f"Invalid or unparseable WKT: {exc}") from exc

    def _execute_query(self, query: str) -> list[dict[str, Any]]:
        """Execute SQL query against SDA endpoint with retry logic and parse table array.

        Args:
            query: SQL query string formatted for SDA.

        Returns:
            List of row dictionaries keyed by column name.

        Raises:
            SDAQueryError: If query execution or response parsing fails after retries.
        """
        payload = {"query": query, "format": "JSON+COLUMNNAME"}
        try:
            response = execute_http_request_with_retry(
                "POST",
                self.base_url,
                json=payload,
                timeout=self.timeout,
                max_retries=max(0, self.max_retries - 1),
                client=self._http_client,
            )
            try:
                data = response.json()
            except Exception as json_exc:
                body = response.text[:500]
                if "maintenance" in body.lower():
                    raise SDAServiceUnavailableError(
                        "SDA is temporarily unavailable (daily maintenance window). "
                        "Retry after a few minutes."
                    ) from json_exc
                raise SDAQueryError(
                    f"SDA returned non-JSON response (HTTP {response.status_code}): {body}"
                ) from json_exc
            return self._parse_table_response(data)
        except HttpStatusError as exc:
            text = exc.response.text
            if exc.status_code < 500:
                raise SDAQueryError(f"SDA client error ({exc.status_code}): {text}") from exc
            raise SDAQueryError(
                f"Failed to query SDA after {self.max_retries} attempts: {exc}"
            ) from exc
        except HttpRequestError as exc:
            if isinstance(exc.__cause__, httpx.TimeoutException) or "timed out" in str(exc).lower():
                raise SDATimeoutError(f"SDA request timed out: {exc}") from exc
            raise SDAQueryError(
                f"Failed to query SDA after {self.max_retries} attempts: {exc}"
            ) from exc

    @staticmethod
    def _parse_table_response(data: Any) -> list[dict[str, Any]]:
        """Parse SDA JSON+COLUMNNAME response format into list of dictionaries.

        SDA returns format:
        {"Table": [["col1", "col2"], ["val1", "val2"], ...]}
        or
        {"Table": []} if no rows found.

        Args:
            data: Raw deserialized JSON response from SDA.

        Returns:
            List of row dicts keyed by column name.

        Raises:
            SDAQueryError: If response contains error message or unexpected structure.
        """
        if not isinstance(data, dict):
            raise SDAQueryError(f"Unexpected SDA response format (expected dict): {data}")

        if "Error" in data or "ErrorMessage" in data:
            error_msg = data.get("ErrorMessage") or data.get("Error")
            raise SDAQueryError(f"SDA returned error: {error_msg}")

        table = data.get("Table")
        if table is None:
            # Check for alternative error keys or empty response
            return []

        if not isinstance(table, list):
            raise SDAQueryError(f"Unexpected 'Table' structure in SDA response: {table}")

        if len(table) < 2:
            # 0 rows (empty table) or 1 row (only headers with no records)
            return []

        headers = [str(col).lower() for col in table[0]]
        rows = table[1:]

        results: list[dict[str, Any]] = []
        for row in rows:
            if isinstance(row, list):
                row_dict = {
                    headers[i]: (row[i] if i < len(row) else None) for i in range(len(headers))
                }
                results.append(row_dict)

        return results

    def get_by_point(self, latitude: float, longitude: float) -> list[dict[str, Any]]:
        """Query SDA for soil map unit at given WGS84 point coordinates.

        Args:
            latitude: Latitude in decimal degrees [-90.0, 90.0].
            longitude: Longitude in decimal degrees [-180.0, 180.0].

        Returns:
            List of map unit records intersecting the point.

        Raises:
            SDAValidationError: If coordinates are invalid.
            SDAQueryError: If SDA query fails.
        """
        lat, lon = self.validate_coordinates(latitude, longitude)
        query = SQL_POINT_LOOKUP.format(latitude=lat, longitude=lon)
        return self._execute_query(query)

    def get_by_mukey(self, mukey: str | int) -> list[dict[str, Any]]:
        """Query SDA for soil map unit by map unit key (mukey).

        Args:
            mukey: Map unit key (positive integer).

        Returns:
            List of matching map unit records.

        Raises:
            SDAValidationError: If mukey is invalid.
            SDAQueryError: If SDA query fails.
        """
        valid_mukey = self.validate_mukey(mukey)
        query = SQL_MUKEY_LOOKUP.format(mukey=valid_mukey)
        return self._execute_query(query)

    def get_by_polygon(self, wkt_geometry: str) -> list[dict[str, Any]]:
        """Query SDA for soil map units intersecting a WGS84 WKT Polygon or MultiPolygon.

        Args:
            wkt_geometry: Validated WGS84 WKT geometry string.

        Returns:
            List of intersecting map unit records.

        Raises:
            SDAValidationError: If WKT format is invalid or contains unexpected characters.
            SDAQueryError: If SDA query fails.
        """
        try:
            wkt = validate_and_sanitize_polygon_wkt(wkt_geometry)
        except GeometryValidationError as exc:
            raise SDAValidationError(f"Invalid WKT geometry: {exc}") from exc

        query = SQL_POLYGON_LOOKUP.format(wkt=wkt)
        return self._execute_query(query)

    def get_spatial_intersection(
        self,
        wkt_geometry: str,
        clip: bool = True,
        geom_acres: bool = True,
        return_geom: bool = False,
    ) -> list[dict[str, Any]]:
        """Query SDA for spatial intersection with SSURGO map units.

        Calculates exact clipped or overlapping acreage and optionally returns geometry WKT.

        Args:
            wkt_geometry: Validated WGS84 WKT Polygon or MultiPolygon.
            clip: True to clip geometries to AOI boundary; False to return overlapping polygons.
            geom_acres: True to compute area_ac using geodesic STArea().
            return_geom: True to return WKT geometry string in 'geom' column.

        Returns:
            List of map unit records with calculated 'area_ac' and optional 'geom'.

        Raises:
            SDAValidationError: If WKT is invalid.
            SDAQueryError: If SDA query fails.
        """
        try:
            wkt = validate_and_sanitize_polygon_wkt(wkt_geometry)
        except GeometryValidationError as exc:
            raise SDAValidationError(f"Invalid WKT geometry: {exc}") from exc

        area_expr = (
            "GEOGRAPHY::STGeomFromWKB(geom_data.geom.STUnion(geom_data.geom.STStartPoint()).STAsBinary(), 4326).MakeValid().STArea() * 0.000247105"
            if geom_acres
            else "CAST(NULL AS float)"
        )
        geom_col = ", geom_data.geom.STAsText() AS geom" if return_geom else ""
        template = SQL_SPATIAL_INTERSECTION_CLIPPED if clip else SQL_SPATIAL_INTERSECTION_OVERLAP
        query = template.format(wkt=wkt, area_expr=area_expr, geom_column=geom_col)
        return self._execute_query(query)

    def get_available_interpretation_rules(self, refresh: bool = False) -> list[str]:
        """Fetch all available soil interpretation rule names (mrulename) from SDA cointerp.

        Results are cached in memory on the client instance.

        Args:
            refresh: If True, forces a fresh query to SDA.

        Returns:
            Alphabetical list of supported rule names.

        Raises:
            SDAQueryError: If query fails.
        """
        if self._cached_rule_names is not None and not refresh:
            return self._cached_rule_names

        results = self._execute_query(SQL_INTERPRETATION_CATALOG)
        rule_names = [
            str(row["mrulename"]).strip()
            for row in results
            if row.get("mrulename") and str(row.get("mrulename")).strip()
        ]
        self._cached_rule_names = rule_names
        return rule_names

    def get_interpretations(
        self,
        mukeys: list[str | int],
        rule_name: str = "NCCPI - National Commodity Crop Productivity Index (Ver 3.0)",
        aggregation_method: str = "Weighted Average",
    ) -> list[dict[str, Any]]:
        """Query component-level soil interpretations for specified map unit keys.

        Args:
            mukeys: List of positive integer map unit keys.
            rule_name: Allowed interpretation rule name.
            aggregation_method: 'Weighted Average' or 'Dominant Component'.

        Returns:
            List of parsed interpretation rows per mukey.

        Raises:
            SDAValidationError: If mukeys or rule/aggregation names are invalid.
            SDAQueryError: If SDA query fails.
        """
        if not mukeys:
            return []

        clean_mukeys = [self.validate_mukey(k) for k in mukeys]
        mukeys_csv = ", ".join(f"'{k}'" for k in clean_mukeys)

        # Validation: Check against allowed config list or cached rule names or safe format
        rule_clean = str(rule_name).strip()
        if any(c in rule_clean for c in [";", "--", "/*", "*/", "DROP", "EXEC", "'"]):
            raise SDAValidationError(
                f"Invalid characters in interpretation rule name: '{rule_name}'"
            )

        if rule_clean not in settings.sda_interpretation_rules_allowed:
            # If not in default allowlist, verify against cached or live catalog
            try:
                available = self.get_available_interpretation_rules()
                if rule_clean not in available:
                    raise SDAValidationError(
                        f"Rule '{rule_clean}' not found in SDA cointerp rule catalog."
                    )
            except Exception as exc:
                if isinstance(exc, SDAValidationError):
                    raise
                # If catalog check fails (e.g. offline/mocked), ensure rule matches standard characters
                logger.warning(
                    "Could not verify rule against live catalog (%s); checking format", exc
                )
                if not all(c.isalnum() or c in " -_().,/" for c in rule_clean):
                    raise SDAValidationError(f"Invalid rule name format: '{rule_clean}'") from exc

        if aggregation_method not in ("Weighted Average", "Dominant Component"):
            raise SDAValidationError(
                f"Aggregation method '{aggregation_method}' is not in allowed methods: {settings.sda_aggregation_methods_allowed}"
            )

        if aggregation_method == "Dominant Component":
            query = SQL_INTERPRETATION_DOMINANT_COMP.format(
                mukeys_csv=mukeys_csv,
                rule_name=rule_clean,
            )
        else:
            query = SQL_INTERPRETATION_WEIGHTED_AVG.format(
                mukeys_csv=mukeys_csv,
                rule_name=rule_clean,
            )

        return self._execute_query(query)

    def lookup_sdv_attribute(self, search_pattern: str) -> list[dict[str, Any]]:
        """Look up Soil Data Viewer (SDV) attribute table and column metadata.

        Args:
            search_pattern: Substring or SQL LIKE pattern to match against attributename or nasisrulename.

        Returns:
            List of matching attribute metadata records.

        Raises:
            SDAValidationError: If search pattern contains invalid characters.
            SDAQueryError: If SDA query fails.
        """
        pattern_clean = str(search_pattern).strip()
        if any(c in pattern_clean for c in [";", "--", "/*", "*/", "DROP", "EXEC", "'"]):
            raise SDAValidationError(
                f"Invalid characters in attribute search pattern: '{search_pattern}'"
            )
        if not ("%" in pattern_clean or "_" in pattern_clean):
            pattern_clean = f"%{pattern_clean}%"

        query = SQL_SDV_ATTRIBUTE_LOOKUP.format(pattern=pattern_clean)
        return self._execute_query(query)

    def get_county_max_productivity_rating(
        self,
        areasymbol: str,
        index_type: str = "nccpi",
        attribute_meta: dict[str, Any] | None = None,
        constraints: Mapping[str, Any] | None = None,
    ) -> float | None:
        """Query maximum baseline productivity rating for a specific county/soil survey area.

        Fixed selectors and explicit ``attribute_meta`` records both resolve to a
        registry spec via ``resolve_sdv_spec`` and run the same builder path (D9).
        Unregistered records raise ``SDAValidationError`` before any query (D2).

        Args:
            areasymbol: 5-character soil survey area symbol (e.g. 'IA169', 'IN097', 'CA001').
            index_type: Fixed productivity selector ('nccpi', 'csr2', 'cpi', 'storie').
            attribute_meta: Optional sdvattribute record (explicit metadata selection).
            constraints: Optional constraints such as ``{"cropname": "Corn"}``.

        Returns:
            Maximum rating float if found, else None.

        Raises:
            SDAValidationError: If areasymbol or index_type are invalid.
            SDAQueryError: If query execution fails.
        """
        clean_area = validate_survey_area_symbol(areasymbol)
        spec, resolved = _resolve_productivity_spec(index_type, attribute_meta, constraints)
        query = build_sdv_county_max_query(spec, clean_area, resolved)

        rows = self._execute_query(query)
        if not rows:
            return None

        val = rows[0].get("max_county_rating")
        if val is None or val in ("", "None"):
            return None
        try:
            val_float = float(val)
            if val_float in spec.sentinels or val_float <= 0:
                return None
            return round(val_float, spec.precision)
        except (ValueError, TypeError):
            return None

    def get_productivity_ratings(
        self,
        mukeys: list[str | int],
        index_type: str = "nccpi",
        areasymbol: str | None = None,
        attribute_meta: dict[str, Any] | None = None,
        constraints: Mapping[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Query map unit and component-level productivity ratings with unrated screening.

        Fixed selectors and explicit ``attribute_meta`` records both resolve to a
        registry spec via ``resolve_sdv_spec`` and run the same builder path (D9).
        Unregistered records raise ``SDAValidationError`` before any query (D2).

        Args:
            mukeys: List of map unit keys (integers or numeric strings).
            index_type: Fixed productivity selector ('nccpi', 'csr2', 'cpi', 'storie').
            areasymbol: Optional county/survey area symbol filter or override.
            attribute_meta: Optional sdvattribute record (explicit metadata selection).
            constraints: Optional constraints such as ``{"cropname": "Corn"}``.

        Returns:
            List of structured rating dictionaries with component rated percentages,
            caveats (from ``SDV_CAVEATS``), ``productivity_rating_source`` (stable
            provenance ID) and ``sdv_provenance`` (structured record, D8).

        Raises:
            SDAValidationError: If mukeys or index_type are invalid.
            SDAQueryError: If SDA query fails.
        """
        if not mukeys:
            return []

        clean_mukeys = [self.validate_mukey(k) for k in mukeys]
        mukeys_csv = ", ".join(f"'{k}'" for k in clean_mukeys)

        spec, resolved = _resolve_productivity_spec(index_type, attribute_meta, constraints)
        norm_idx = spec.spec_id
        provenance = _build_sdv_provenance(spec, resolved)
        query = build_sdv_rating_query(spec, mukeys_csv, resolved)

        raw_rows = self._execute_query(query)
        rows_by_mukey = {str(r.get("mukey")): r for r in raw_rows}

        results: list[dict[str, Any]] = []
        for k in clean_mukeys:
            row = rows_by_mukey.get(k)
            if not row:
                results.append(
                    {
                        "mukey": k,
                        "areasymbol": areasymbol,
                        "musym": None,
                        "muname": None,
                        "index_type": norm_idx,
                        "productivity_rating_source": spec.provenance_id,
                        "spec_id": spec.spec_id,
                        "algorithm": spec.algorithm,
                        "table": spec.table,
                        "rule_name": spec.rule_name,
                        "value_column": spec.value_column,
                        "numeric_rating": None,
                        "rated_pct": 0.0,
                        "total_pct": 0.0,
                        "coverage_status": "not_found",
                        "is_rated": False,
                        "caveats": [SDV_CAVEATS["not_found"]],
                        "sdv_provenance": dict(provenance),
                    }
                )
                continue

            raw_rating = row.get("numeric_rating")
            raw_rated_pct = row.get("rated_pct")
            raw_total_pct = row.get("total_pct")

            rated_pct = float(raw_rated_pct) if raw_rated_pct is not None else 0.0
            total_pct = float(raw_total_pct) if raw_total_pct is not None else 0.0

            numeric_rating: float | None = None
            is_rated = False
            caveats: list[str] = []

            if raw_rating is not None and str(raw_rating).strip() not in ("", "None"):
                try:
                    r_val = float(raw_rating)
                    if r_val in spec.sentinels or r_val <= 0:
                        caveats.append(SDV_CAVEATS["unrated_sentinel"].format(value=raw_rating))
                    elif rated_pct <= 0:
                        caveats.append(SDV_CAVEATS["no_coverage"])
                    else:
                        numeric_rating = round(r_val, spec.precision)
                        is_rated = True
                except (ValueError, TypeError):
                    caveats.append(SDV_CAVEATS["unparseable"].format(value=raw_rating))
            else:
                caveats.append(SDV_CAVEATS["no_rating"])

            if is_rated and total_pct > 0 and rated_pct < total_pct:
                caveats.append(
                    SDV_CAVEATS["partial_rating"].format(
                        rated=round(rated_pct, 1), total=round(total_pct, 1)
                    )
                )

            if is_rated:
                coverage_status = "partial" if rated_pct < total_pct else "rated"
            elif rated_pct > 0 or total_pct > 0:
                coverage_status = "unrated"
            else:
                coverage_status = "no_coverage"

            row_provenance = dict(provenance)

            # Crop yields (D7): a single yldunits per map unit, otherwise unrated.
            if spec.table == "cocropyld":
                unit_count = row.get("unit_count")
                yld_min = row.get("yldunits_min")
                yld_max = row.get("yldunits_max")
                if unit_count is not None and int(unit_count) > 1:
                    numeric_rating = None
                    is_rated = False
                    caveats.append(
                        SDV_CAVEATS["mixed_units"].format(min_unit=yld_min, max_unit=yld_max)
                    )
                    row_provenance["yldunits"] = None
                else:
                    row_provenance["yldunits"] = yld_min

            # Method and scope caveats, fixed order.
            if spec.algorithm == "Dominant Condition":
                caveats.append(SDV_CAVEATS["dominant_condition"])
            if spec.table == "chorizon":
                caveats.append(SDV_CAVEATS["aws_fixed_depth"])
            if spec.table == "cocropyld":
                caveats.append(
                    SDV_CAVEATS["crop_specific"].format(crop=(resolved or {}).get("cropname", ""))
                )

            results.append(
                {
                    "mukey": str(row.get("mukey", k)),
                    "areasymbol": str(row.get("areasymbol"))
                    if row.get("areasymbol")
                    else areasymbol,
                    "musym": str(row.get("musym")) if row.get("musym") else None,
                    "muname": str(row.get("muname")) if row.get("muname") else None,
                    "index_type": norm_idx,
                    "productivity_rating_source": spec.provenance_id,
                    "spec_id": spec.spec_id,
                    "algorithm": spec.algorithm,
                    "table": spec.table,
                    "rule_name": spec.rule_name,
                    "value_column": spec.value_column,
                    "numeric_rating": numeric_rating,
                    "rated_pct": round(rated_pct, 2),
                    "total_pct": round(total_pct, 2),
                    "coverage_status": coverage_status,
                    "is_rated": is_rated,
                    "caveats": caveats,
                    "sdv_provenance": row_provenance,
                }
            )

        return results
