"""USDA NRCS Soil Data Access (SDA) client and query engine.

Encapsulates HTTPS communication with the USDA NRCS Soil Data Access Tabular REST service
(https://sdmdataaccess.nrcs.usda.gov/Tabular/post.rest), implementing strict coordinate and
mukey validation, fixed parameterized query templates, matrix table response parsing,
and robust retry logic.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping

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

PRODUCTIVITY_PROVENANCE = {
    "nccpi": "SDA:NCCPI_V3",
    "csr2": "SDA:MAPUNIT_IACORNSR",
    "cpi": "SDA:COMPONENT_CROPPRODINDEX",
    "storie": "SDA:COINTERP_STORIE_CA",
}

PRODUCTIVITY_SEMANTICS = {
    "nccpi": {
        "aliases": frozenset({"nccpi", "nccpi_v3", "national commodity crop productivity index"}),
        "scale": "0-1",
        "precision": 3,
        "sentinels": frozenset({99.0, 999.0, -99.0, -999.0}),
        "provenance": PRODUCTIVITY_PROVENANCE["nccpi"],
    },
    "csr2": {
        "aliases": frozenset({"csr2", "iowa corn suitability rating csr2"}),
        "scale": "5-100",
        "precision": 0,
        "sentinels": frozenset({999.0, -99.0, -999.0}),
        "provenance": PRODUCTIVITY_PROVENANCE["csr2"],
    },
    "cpi": {
        "aliases": frozenset({"cpi", "crop productivity index"}),
        "scale": "1-100",
        "precision": 0,
        "sentinels": frozenset({999.0, -99.0, -999.0}),
        "provenance": PRODUCTIVITY_PROVENANCE["cpi"],
    },
    "storie": {
        "aliases": frozenset(
            {
                "storie",
                "california revised storie index",
                "agr - california revised storie index (ca)",
            }
        ),
        "scale": "0-1",
        "precision": 3,
        "sentinels": frozenset({99.0, 999.0, -99.0, -999.0}),
        "provenance": PRODUCTIVITY_PROVENANCE["storie"],
    },
}

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
            provenance_id=PRODUCTIVITY_PROVENANCE["nccpi"],
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
            scale=PRODUCTIVITY_SEMANTICS["nccpi"]["scale"],
            precision=PRODUCTIVITY_SEMANTICS["nccpi"]["precision"],
            sentinels=PRODUCTIVITY_SEMANTICS["nccpi"]["sentinels"],
            aliases=PRODUCTIVITY_SEMANTICS["nccpi"]["aliases"],
        ),
        "storie": SdvRatingSpec(
            spec_id="storie",
            provenance_id=PRODUCTIVITY_PROVENANCE["storie"],
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
            scale=PRODUCTIVITY_SEMANTICS["storie"]["scale"],
            precision=PRODUCTIVITY_SEMANTICS["storie"]["precision"],
            sentinels=PRODUCTIVITY_SEMANTICS["storie"]["sentinels"],
            aliases=PRODUCTIVITY_SEMANTICS["storie"]["aliases"],
        ),
        "csr2": SdvRatingSpec(
            spec_id="csr2",
            provenance_id=PRODUCTIVITY_PROVENANCE["csr2"],
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
            scale=PRODUCTIVITY_SEMANTICS["csr2"]["scale"],
            precision=PRODUCTIVITY_SEMANTICS["csr2"]["precision"],
            sentinels=PRODUCTIVITY_SEMANTICS["csr2"]["sentinels"],
            aliases=PRODUCTIVITY_SEMANTICS["csr2"]["aliases"],
        ),
        "cpi": SdvRatingSpec(
            spec_id="cpi",
            provenance_id=PRODUCTIVITY_PROVENANCE["cpi"],
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
            scale=PRODUCTIVITY_SEMANTICS["cpi"]["scale"],
            precision=PRODUCTIVITY_SEMANTICS["cpi"]["precision"],
            sentinels=PRODUCTIVITY_SEMANTICS["cpi"]["sentinels"],
            aliases=PRODUCTIVITY_SEMANTICS["cpi"]["aliases"],
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

SQL_PRODUCTIVITY_NCCPI = """\
WITH comp_rating AS (
    SELECT
        m.mukey,
        l.areasymbol,
        m.musym,
        m.muname,
        c.cokey,
        c.comppct_r,
        ci.interphr AS rating
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
    ROUND(SUM(CASE WHEN rating IS NOT NULL AND rating NOT IN (99, 999, -99, -999) THEN rating * comppct_r ELSE 0 END) / NULLIF(SUM(CASE WHEN rating IS NOT NULL AND rating NOT IN (99, 999, -99, -999) THEN comppct_r ELSE 0 END), 0), 3) AS numeric_rating,
    SUM(CASE WHEN rating IS NOT NULL AND rating NOT IN (99, 999, -99, -999) THEN comppct_r ELSE 0 END) AS rated_pct,
    SUM(comppct_r) AS total_pct
FROM comp_rating
GROUP BY mukey, areasymbol, musym, muname
"""

SQL_PRODUCTIVITY_COUNTY_MAX_NCCPI = """\
SELECT
    MAX(ci.interphr) AS max_county_rating
FROM legend AS l
INNER JOIN mapunit AS m ON m.lkey = l.lkey
INNER JOIN component AS c ON c.mukey = m.mukey
INNER JOIN cointerp AS ci ON ci.cokey = c.cokey
WHERE l.areasymbol = '{areasymbol}'
  AND ci.ruledepth = 0
  AND ci.mrulename = '{rule_name}'
  AND ci.interphr IS NOT NULL
  AND ci.interphr NOT IN (99, 999, -99, -999)
  AND c.compkind != 'miscellaneous area'
"""

# CSR2 is a mapunit-level attribute (not component-aggregated); rated_pct is synthetic.
SQL_PRODUCTIVITY_CSR2 = """\
SELECT
    m.mukey,
    l.areasymbol,
    m.musym,
    m.muname,
    CAST(m.iacornsr AS float) AS numeric_rating,
    CASE WHEN m.iacornsr IS NOT NULL THEN 100.0 ELSE 0.0 END AS rated_pct,
    100.0 AS total_pct
FROM legend AS l
INNER JOIN mapunit AS m ON m.lkey = l.lkey
WHERE m.mukey IN ({mukeys_csv})
"""

SQL_PRODUCTIVITY_COUNTY_MAX_CSR2 = """\
SELECT
    MAX(CAST(m.iacornsr AS float)) AS max_county_rating
FROM legend AS l
INNER JOIN mapunit AS m ON m.lkey = l.lkey
WHERE l.areasymbol = '{areasymbol}'
  AND m.iacornsr IS NOT NULL
"""

SQL_PRODUCTIVITY_CPI = """\
SELECT
    m.mukey,
    l.areasymbol,
    m.musym,
    m.muname,
    SUM(CASE WHEN c.cropprodindex IS NOT NULL
        THEN CAST(c.cropprodindex AS float) * c.comppct_r ELSE 0 END)
        / NULLIF(SUM(CASE WHEN c.cropprodindex IS NOT NULL
            THEN c.comppct_r ELSE 0 END), 0) AS numeric_rating,
    SUM(CASE WHEN c.cropprodindex IS NOT NULL THEN c.comppct_r ELSE 0 END) AS rated_pct,
    SUM(c.comppct_r) AS total_pct
FROM legend AS l
INNER JOIN mapunit AS m ON m.lkey = l.lkey
INNER JOIN component AS c ON c.mukey = m.mukey
WHERE m.mukey IN ({mukeys_csv})
  AND c.compkind != 'miscellaneous area'
GROUP BY m.mukey, l.areasymbol, m.musym, m.muname
"""

SQL_PRODUCTIVITY_COUNTY_MAX_CPI = """\
SELECT
    MAX(CAST(c.cropprodindex AS float)) AS max_county_rating
FROM legend AS l
INNER JOIN mapunit AS m ON m.lkey = l.lkey
INNER JOIN component AS c ON c.mukey = m.mukey
WHERE l.areasymbol = '{areasymbol}'
  AND c.cropprodindex IS NOT NULL
  AND c.compkind != 'miscellaneous area'
"""

ALLOWED_SDV_TABLES = {
    "chorizon",
    "cocropyld",
    "cointerp",
    "component",
    "mapunit",
}

_NCCPI_ALIASES = PRODUCTIVITY_SEMANTICS["nccpi"]["aliases"]
_CSR2_ALIASES = PRODUCTIVITY_SEMANTICS["csr2"]["aliases"]
_CPI_ALIASES = PRODUCTIVITY_SEMANTICS["cpi"]["aliases"]
_STORIE_ALIASES = PRODUCTIVITY_SEMANTICS["storie"]["aliases"]


def _normalize_productivity_index(index_type: str) -> str:
    """Normalize a fixed productivity selector and reject unsupported aliases."""
    selector = str(index_type).strip().lower()
    for normalized, semantics in PRODUCTIVITY_SEMANTICS.items():
        if selector in semantics["aliases"]:
            return normalized
    raise SDAValidationError(
        f"Unsupported productivity index type '{index_type}'. "
        f"{SUPPORTED_INDEX_MSG} "
        "Explicit attribute metadata is required for custom SDV queries."
    )


def _is_productivity_sentinel(value: float, norm_idx: str) -> bool:
    """Return whether a raw rating is an unrated sentinel for its index."""
    return value in _sentinels_for_index(norm_idx)


def _sentinels_for_index(norm_idx: str) -> frozenset[float]:
    """Return sentinels for a known index, or the complete SDA fallback set."""
    return PRODUCTIVITY_SEMANTICS.get(norm_idx, {}).get(
        "sentinels", frozenset({99.0, 999.0, -99.0, -999.0})
    )


def _dynamic_index_name(attribute_meta: dict[str, Any]) -> str:
    """Resolve a known productivity selector from SDV metadata when possible."""
    candidates = (
        str(attribute_meta.get("attributename", "")).strip().lower(),
        str(attribute_meta.get("nasisrulename", "")).strip().lower(),
    )
    for candidate in candidates:
        for normalized, semantics in PRODUCTIVITY_SEMANTICS.items():
            if candidate in semantics["aliases"] or normalized in candidate:
                return normalized
    return "custom"


def _sentinel_sql_predicate(expression: str, norm_idx: str) -> str:
    """Build an SQL predicate that excludes index-specific unrated sentinels."""
    sentinels = ", ".join(
        str(int(value)) if value.is_integer() else str(value)
        for value in sorted(_sentinels_for_index(norm_idx))
    )
    return f"{expression} IS NOT NULL AND {expression} NOT IN ({sentinels})"


def _round_for_index(value: float, norm_idx: str) -> float:
    """Round a productivity rating to the precision appropriate for its index type."""
    precision = PRODUCTIVITY_SEMANTICS.get(norm_idx, {}).get("precision", 2)
    return round(value, precision)


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
    """cointerp + Dominant Condition (Storie-style, D5)."""
    sentinel = _spec_sentinel_predicate(spec, "rating")
    rule = spec.rule_name.replace("'", "''")
    tiebreak_dir = "ASC" if spec.tiebreak_rule < 0 else "DESC"
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
    INNER JOIN cointerp AS ci ON ci.cokey = c.cokey
        AND ci.ruledepth = 0
        AND ci.mrulename = '{rule}'
    WHERE m.mukey IN ({mukeys_sql})
      AND c.compkind != 'miscellaneous area'
      AND {sentinel}
),
dominant AS (
    SELECT
        mukey,
        areasymbol,
        musym,
        muname,
        ROUND(rating, {spec.precision}) AS rating_val,
        SUM(comppct_r) AS pct_sum,
        ROW_NUMBER() OVER (
            PARTITION BY mukey
            ORDER BY SUM(comppct_r) DESC, rating {tiebreak_dir}
        ) AS rn,
        SUM(SUM(comppct_r)) OVER (PARTITION BY mukey) AS total_pct
    FROM comp_rating
    GROUP BY mukey, areasymbol, musym, muname, ROUND(rating, {spec.precision}), rating
)
SELECT
    mukey,
    areasymbol,
    musym,
    muname,
    rating_val AS numeric_rating,
    pct_sum AS rated_pct,
    total_pct
FROM dominant
WHERE rn = 1
"""


def _build_cointerp_dc_county_max(spec: SdvRatingSpec, areasymbol: str) -> str:
    """cointerp + Dominant Condition county max (D5)."""
    sentinel = _spec_sentinel_predicate(spec, f"ci.{spec.value_column}")
    rule = spec.rule_name.replace("'", "''")
    tiebreak_dir = "ASC" if spec.tiebreak_rule < 0 else "DESC"
    return f"""\
WITH mukey_dominant AS (
    SELECT
        m.mukey,
        ROUND(ci.{spec.value_column}, {spec.precision}) AS rating_val,
        SUM(c.comppct_r) AS pct_sum,
        ROW_NUMBER() OVER (
            PARTITION BY m.mukey
            ORDER BY SUM(c.comppct_r) DESC, ci.{spec.value_column} {tiebreak_dir}
        ) AS rn
    FROM legend AS l
    INNER JOIN mapunit AS m ON m.lkey = l.lkey
    INNER JOIN component AS c ON c.mukey = m.mukey
    INNER JOIN cointerp AS ci ON ci.cokey = c.cokey
    WHERE l.areasymbol = '{areasymbol}'
      AND ci.ruledepth = 0
      AND ci.mrulename = '{rule}'
      AND {sentinel}
      AND c.compkind != 'miscellaneous area'
    GROUP BY m.mukey, ROUND(ci.{spec.value_column}, {spec.precision}), ci.{spec.value_column}
)
SELECT MAX(rating_val) AS max_county_rating
FROM mukey_dominant
WHERE rn = 1
"""


def _build_component_wa_rating(spec: SdvRatingSpec, mukeys_sql: str) -> str:
    """component + Weighted Average (CPI-style)."""
    col = spec.value_column
    return f"""\
SELECT
    m.mukey,
    l.areasymbol,
    m.musym,
    m.muname,
    SUM(CASE WHEN c.{col} IS NOT NULL
        THEN CAST(c.{col} AS float) * c.comppct_r ELSE 0 END)
        / NULLIF(SUM(CASE WHEN c.{col} IS NOT NULL
            THEN c.comppct_r ELSE 0 END), 0) AS numeric_rating,
    SUM(CASE WHEN c.{col} IS NOT NULL THEN c.comppct_r ELSE 0 END) AS rated_pct,
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
    return f"""\
SELECT
    MAX(CAST(c.{col} AS float)) AS max_county_rating
FROM legend AS l
INNER JOIN mapunit AS m ON m.lkey = l.lkey
INNER JOIN component AS c ON c.mukey = m.mukey
WHERE l.areasymbol = '{areasymbol}'
  AND c.{col} IS NOT NULL
  AND c.compkind != 'miscellaneous area'
"""


def _build_mapunit_no_agg_rating(spec: SdvRatingSpec, mukeys_sql: str) -> str:
    """mapunit + No Aggregation Necessary (CSR2-style)."""
    col = spec.value_column
    sentinel = _spec_sentinel_predicate(spec, f"m.{col}")
    return f"""\
SELECT
    m.mukey,
    l.areasymbol,
    m.musym,
    m.muname,
    CAST(m.{col} AS float) AS numeric_rating,
    CASE WHEN {sentinel} THEN 100.0 ELSE 0.0 END AS rated_pct,
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
        c.comppct_r,
        m.mukey,
        l.areasymbol,
        m.musym,
        m.muname,
        SUM(CAST(ch.{col} AS float) * (CASE WHEN ch.hzdepb_r > {depth_bot} THEN {depth_bot} ELSE ch.hzdepb_r END - CASE WHEN ch.hzdept_r < {depth_top} THEN {depth_top} ELSE ch.hzdept_r END))
            AS attr_sum
    FROM legend AS l
    INNER JOIN mapunit AS m ON m.lkey = l.lkey
    INNER JOIN component AS c ON c.mukey = m.mukey
    INNER JOIN chorizon AS ch ON ch.cokey = c.cokey
    WHERE m.mukey IN ({mukeys_sql})
      AND c.compkind != 'miscellaneous area'
      AND ch.{col} IS NOT NULL
      AND ch.hzdepb_r > {depth_top}
      AND ch.hzdept_r < {depth_bot}
    GROUP BY c.cokey, c.comppct_r, m.mukey, l.areasymbol, m.musym, m.muname
)
SELECT
    mukey,
    areasymbol,
    musym,
    muname,
    ROUND(SUM(attr_sum * comppct_r) / NULLIF(SUM(comppct_r), 0), {spec.precision}) AS numeric_rating,
    SUM(CASE WHEN attr_sum IS NOT NULL THEN comppct_r ELSE 0 END) AS rated_pct,
    SUM(comppct_r) AS total_pct
FROM hz_weighted
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

    null_handling = ""
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

_WAVE3_TABLES = frozenset({"cointerp", "component", "mapunit", "chorizon", "cocropyld"})


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

    For cointerp, component, and mapunit tables, validates the record against
    the registry and delegates to the per-strategy builder.  For chorizon and
    cocropyld, uses the legacy inline code path (to be migrated in a later wave).
    """
    table = str(attribute_meta.get("attributetablename", "")).strip().lower()
    if table not in ALLOWED_SDV_TABLES:
        raise SDAValidationError(
            f"Unsupported or unallowed SDV table '{table}'. Allowed: {sorted(ALLOWED_SDV_TABLES)}"
        )

    if table in _WAVE3_TABLES:
        try:
            spec = validate_sdv_record(attribute_meta)
            constraints = {}
            if spec.table == "cocropyld":
                cropname = str(attribute_meta.get("cropname", "")).strip()
                if cropname:
                    constraints["cropname"] = cropname
            return build_sdv_rating_query(spec, mukeys_csv, constraints)
        except SDAValidationError:
            pass  # Non-registered record: fall through to legacy path

    if isinstance(mukeys_csv, str):
        mukey_items = mukeys_csv.split(",")
    else:
        mukey_items = mukeys_csv
    try:
        clean_mukeys = [str(item).strip().strip("'") for item in mukey_items]
        if not clean_mukeys or any(
            not re.fullmatch(r"[1-9][0-9]*", mukey) for mukey in clean_mukeys
        ):
            raise ValueError
    except (TypeError, ValueError) as exc:
        raise SDAValidationError(
            f"Map unit keys must be positive numeric digits; received '{mukeys_csv}'"
        ) from exc
    mukeys_sql = ", ".join(f"'{mukey}'" for mukey in clean_mukeys)

    col = str(attribute_meta.get("attributecolumnname", "")).strip()
    rule_name = str(attribute_meta.get("nasisrulename", "")).strip()
    norm_idx = _dynamic_index_name(attribute_meta)

    if table == "cointerp" or rule_name:
        rule_clean = rule_name.replace("'", "''")
        rating_predicate = _sentinel_sql_predicate("rating", norm_idx)
        return f"""\
WITH comp_rating AS (
    SELECT
        m.mukey,
        l.areasymbol,
        m.musym,
        m.muname,
        c.cokey,
        c.comppct_r,
        ci.interphr AS rating
    FROM legend AS l
    INNER JOIN mapunit AS m ON m.lkey = l.lkey
    INNER JOIN component AS c ON c.mukey = m.mukey
    LEFT JOIN cointerp AS ci ON ci.cokey = c.cokey
        AND ci.ruledepth = 0
        AND ci.mrulename = '{rule_clean}'
    WHERE m.mukey IN ({mukeys_sql})
      AND c.compkind != 'miscellaneous area'
)
SELECT
    mukey,
    areasymbol,
    musym,
    muname,
    ROUND(SUM(CASE WHEN {rating_predicate} THEN rating * comppct_r ELSE 0 END) / NULLIF(SUM(CASE WHEN {rating_predicate} THEN comppct_r ELSE 0 END), 0), 3) AS numeric_rating,
    SUM(CASE WHEN {rating_predicate} THEN comppct_r ELSE 0 END) AS rated_pct,
    SUM(comppct_r) AS total_pct
FROM comp_rating
GROUP BY mukey, areasymbol, musym, muname
"""

    if not col or not re.fullmatch(r"[a-zA-Z][a-zA-Z0-9_]*", col):
        raise SDAValidationError(f"Invalid column name '{col}' for SDV query generation.")

    if table == "chorizon":
        rating_predicate = _sentinel_sql_predicate(f"ch.{col}", norm_idx)
        return f"""\
WITH hz_weighted AS (
    SELECT
        c.cokey,
        c.comppct_r,
        m.mukey,
        l.areasymbol,
        m.musym,
        m.muname,
        SUM(CAST(ch.{col} AS float) * (ch.hzdepb_r - ch.hzdept_r))
            / NULLIF(SUM(ch.hzdepb_r - ch.hzdept_r), 0) AS hz_avg
    FROM legend AS l
    INNER JOIN mapunit AS m ON m.lkey = l.lkey
    INNER JOIN component AS c ON c.mukey = m.mukey
    INNER JOIN chorizon AS ch ON ch.cokey = c.cokey
    WHERE m.mukey IN ({mukeys_sql})
      AND c.compkind != 'miscellaneous area'
      AND {rating_predicate}
    GROUP BY c.cokey, c.comppct_r, m.mukey, l.areasymbol, m.musym, m.muname
)
SELECT
    mukey,
    areasymbol,
    musym,
    muname,
    ROUND(SUM(CASE WHEN hz_avg IS NOT NULL THEN hz_avg * comppct_r ELSE 0 END)
        / NULLIF(SUM(CASE WHEN hz_avg IS NOT NULL THEN comppct_r ELSE 0 END), 0), 3) AS numeric_rating,
    SUM(CASE WHEN hz_avg IS NOT NULL THEN comppct_r ELSE 0 END) AS rated_pct,
    SUM(comppct_r) AS total_pct
FROM hz_weighted
GROUP BY mukey, areasymbol, musym, muname
"""

    if table == "cocropyld":
        rating_predicate = _sentinel_sql_predicate(f"cy.{col}", norm_idx)
        cropname = str(attribute_meta.get("cropname", "")).strip()
        crop_filter = ""
        if cropname:
            crop_clean = cropname.replace("'", "''")
            crop_filter = f"AND cy.cropname = '{crop_clean}'"
        return f"""\
WITH comp_yield AS (
    SELECT
        m.mukey,
        l.areasymbol,
        m.musym,
        m.muname,
        c.cokey,
        c.comppct_r,
        CAST(cy.{col} AS float) AS rating,
        cy.cropname,
        cy.yldunits
    FROM legend AS l
    INNER JOIN mapunit AS m ON m.lkey = l.lkey
    INNER JOIN component AS c ON c.mukey = m.mukey
    INNER JOIN cocropyld AS cy ON cy.cokey = c.cokey
    WHERE m.mukey IN ({mukeys_sql})
      AND c.compkind != 'miscellaneous area'
      AND {rating_predicate}
      {crop_filter}
)
SELECT
    mukey,
    areasymbol,
    musym,
    muname,
    ROUND(SUM(CASE WHEN rating IS NOT NULL THEN rating * comppct_r ELSE 0 END)
        / NULLIF(SUM(CASE WHEN rating IS NOT NULL THEN comppct_r ELSE 0 END), 0), 2) AS numeric_rating,
    SUM(CASE WHEN rating IS NOT NULL THEN comppct_r ELSE 0 END) AS rated_pct,
    SUM(comppct_r) AS total_pct,
    MAX(cropname) AS cropname,
    MAX(yldunits) AS yldunits
FROM comp_yield
GROUP BY mukey, areasymbol, musym, muname
"""

    if table == "mapunit":
        rating_predicate = _sentinel_sql_predicate(f"m.{col}", norm_idx)
        return f"""\
SELECT
    m.mukey,
    l.areasymbol,
    m.musym,
    m.muname,
    ROUND(CAST(m.{col} AS float), 2) AS numeric_rating,
    CASE WHEN {rating_predicate} THEN 100.0 ELSE 0.0 END AS rated_pct,
    100.0 AS total_pct
FROM legend AS l
INNER JOIN mapunit AS m ON m.lkey = l.lkey
WHERE m.mukey IN ({mukeys_sql})
"""

    # Default to component-level attribute
    rating_predicate = _sentinel_sql_predicate("rating", norm_idx)
    return f"""\
WITH comp_rating AS (
    SELECT
        m.mukey,
        l.areasymbol,
        m.musym,
        m.muname,
        c.cokey,
        c.comppct_r,
        CAST(c.{col} AS float) AS rating
    FROM legend AS l
    INNER JOIN mapunit AS m ON m.lkey = l.lkey
    INNER JOIN component AS c ON c.mukey = m.mukey
    WHERE m.mukey IN ({mukeys_sql})
      AND c.compkind != 'miscellaneous area'
)
SELECT
    mukey,
    areasymbol,
    musym,
    muname,
    ROUND(SUM(CASE WHEN {rating_predicate} THEN rating * comppct_r ELSE 0 END) / NULLIF(SUM(CASE WHEN {rating_predicate} THEN comppct_r ELSE 0 END), 0), 2) AS numeric_rating,
    SUM(CASE WHEN {rating_predicate} THEN comppct_r ELSE 0 END) AS rated_pct,
    SUM(comppct_r) AS total_pct
FROM comp_rating
GROUP BY mukey, areasymbol, musym, muname
"""


def build_dynamic_sdv_county_max_query(
    attribute_meta: dict[str, Any],
    areasymbol: str,
) -> str:
    """Dynamically build an SDA query for maximum county rating from sdvattribute metadata.

    For cointerp, component, and mapunit tables, validates the record against
    the registry and delegates to the per-strategy county max builder.  For
    chorizon and cocropyld, uses the legacy inline code path.
    """
    areasymbol = validate_survey_area_symbol(areasymbol)
    table = str(attribute_meta.get("attributetablename", "")).strip().lower()

    if table in _WAVE3_TABLES:
        try:
            spec = validate_sdv_record(attribute_meta)
            constraints = {}
            if spec.table == "cocropyld":
                cropname = str(attribute_meta.get("cropname", "")).strip()
                if cropname:
                    constraints["cropname"] = cropname
            return build_sdv_county_max_query(spec, areasymbol, constraints)
        except SDAValidationError:
            pass  # Non-registered record: fall through to legacy path

    col = str(attribute_meta.get("attributecolumnname", "")).strip()
    rule_name = str(attribute_meta.get("nasisrulename", "")).strip()
    norm_idx = _dynamic_index_name(attribute_meta)

    if table not in ALLOWED_SDV_TABLES:
        raise SDAValidationError(
            f"Unsupported or unallowed SDV table '{table}'. Allowed: {sorted(ALLOWED_SDV_TABLES)}"
        )

    if table == "cointerp" or rule_name:
        rule_clean = rule_name.replace("'", "''")
        rating_predicate = _sentinel_sql_predicate("ci.interphr", norm_idx)
        return f"""\
SELECT
    MAX(ci.interphr) AS max_county_rating
FROM legend AS l
INNER JOIN mapunit AS m ON m.lkey = l.lkey
INNER JOIN component AS c ON c.mukey = m.mukey
INNER JOIN cointerp AS ci ON ci.cokey = c.cokey
WHERE l.areasymbol = '{areasymbol}'
  AND ci.ruledepth = 0
  AND ci.mrulename = '{rule_clean}'
  AND {rating_predicate}
  AND c.compkind != 'miscellaneous area'
"""

    if not col or not re.fullmatch(r"[a-zA-Z][a-zA-Z0-9_]*", col):
        raise SDAValidationError(f"Invalid column name '{col}' for county max query generation.")

    if table == "chorizon":
        rating_predicate = _sentinel_sql_predicate(f"ch.{col}", norm_idx)
        return f"""\
SELECT
    MAX(hz_avg) AS max_county_rating
FROM (
    SELECT
        SUM(CAST(ch.{col} AS float) * (ch.hzdepb_r - ch.hzdept_r))
            / NULLIF(SUM(ch.hzdepb_r - ch.hzdept_r), 0) AS hz_avg
    FROM legend AS l
    INNER JOIN mapunit AS m ON m.lkey = l.lkey
    INNER JOIN component AS c ON c.mukey = m.mukey
    INNER JOIN chorizon AS ch ON ch.cokey = c.cokey
    WHERE l.areasymbol = '{areasymbol}'
      AND c.compkind != 'miscellaneous area'
      AND {rating_predicate}
    GROUP BY c.cokey
) AS hz_agg
"""

    if table == "cocropyld":
        rating_predicate = _sentinel_sql_predicate(f"cy.{col}", norm_idx)
        cropname = str(attribute_meta.get("cropname", "")).strip()
        crop_filter = ""
        if cropname:
            crop_clean = cropname.replace("'", "''")
            crop_filter = f"AND cy.cropname = '{crop_clean}'"
        return f"""\
SELECT
    MAX(CAST(cy.{col} AS float)) AS max_county_rating
FROM legend AS l
INNER JOIN mapunit AS m ON m.lkey = l.lkey
INNER JOIN component AS c ON c.mukey = m.mukey
INNER JOIN cocropyld AS cy ON cy.cokey = c.cokey
WHERE l.areasymbol = '{areasymbol}'
  AND c.compkind != 'miscellaneous area'
  AND {rating_predicate}
  {crop_filter}
"""

    if table == "mapunit":
        rating_predicate = _sentinel_sql_predicate(f"m.{col}", norm_idx)
        return f"""\
SELECT
    MAX(CAST(m.{col} AS float)) AS max_county_rating
FROM legend AS l
INNER JOIN mapunit AS m ON m.lkey = l.lkey
WHERE l.areasymbol = '{areasymbol}'
  AND {rating_predicate}
"""

    rating_predicate = _sentinel_sql_predicate(f"c.{col}", norm_idx)
    return f"""\
SELECT
    MAX(CAST(c.{col} AS float)) AS max_county_rating
FROM legend AS l
INNER JOIN mapunit AS m ON m.lkey = l.lkey
INNER JOIN component AS c ON c.mukey = m.mukey
WHERE l.areasymbol = '{areasymbol}'
  AND {rating_predicate}
  AND c.compkind != 'miscellaneous area'
"""


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
    ) -> float | None:
        """Query maximum baseline productivity rating for a specific county/soil survey area.

        Args:
            areasymbol: 5-character soil survey area symbol (e.g. 'IA169', 'IN097', 'CA001').
            index_type: Fixed productivity selector ('nccpi').
            attribute_meta: Optional sdvattribute record for dynamic query generation.

        Returns:
            Maximum rating float if found, else None.

        Raises:
            SDAValidationError: If areasymbol or index_type is invalid.
            SDAQueryError: If query execution fails.
        """
        clean_area = validate_survey_area_symbol(areasymbol)

        if attribute_meta:
            query = build_dynamic_sdv_county_max_query(attribute_meta, clean_area)
            norm_idx = _dynamic_index_name(attribute_meta)
        else:
            norm_idx = _normalize_productivity_index(index_type)
            if norm_idx == "nccpi":
                query = SQL_PRODUCTIVITY_COUNTY_MAX_NCCPI.format(
                    areasymbol=clean_area,
                    rule_name="NCCPI - National Commodity Crop Productivity Index (Ver 3.0)",
                )
            elif norm_idx == "csr2":
                query = SQL_PRODUCTIVITY_COUNTY_MAX_CSR2.format(areasymbol=clean_area)
            elif norm_idx == "cpi":
                query = SQL_PRODUCTIVITY_COUNTY_MAX_CPI.format(areasymbol=clean_area)
            elif norm_idx == "storie":
                query = SQL_PRODUCTIVITY_COUNTY_MAX_NCCPI.format(
                    areasymbol=clean_area,
                    rule_name="AGR - California Revised Storie Index (CA)",
                )

        rows = self._execute_query(query)
        if not rows:
            return None

        val = rows[0].get("max_county_rating")
        if val is None or val in ("", "None"):
            return None
        try:
            val_float = float(val)
            if _is_productivity_sentinel(val_float, norm_idx) or val_float <= 0:
                return None
            return (
                _round_for_index(val_float, norm_idx)
                if norm_idx in PRODUCTIVITY_SEMANTICS
                else round(val_float, 2)
            )
        except (ValueError, TypeError):
            return None

    def get_productivity_ratings(
        self,
        mukeys: list[str | int],
        index_type: str = "nccpi",
        areasymbol: str | None = None,
        attribute_meta: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Query map unit and component-level productivity ratings with unrated screening.

        Args:
            mukeys: List of map unit keys (integers or numeric strings).
            index_type: Fixed productivity selector ('nccpi').
            areasymbol: Optional county/survey area symbol filter or override.
            attribute_meta: Optional sdvattribute record for dynamic query generation.

        Returns:
            List of structured rating dictionaries with component rated percentages,
            caveats, and ``productivity_rating_source`` identifying the selected
            SDA interpretation.

        Raises:
            SDAValidationError: If mukeys or index_type are invalid.
            SDAQueryError: If SDA query fails.
        """
        if not mukeys:
            return []

        clean_mukeys = [self.validate_mukey(k) for k in mukeys]
        mukeys_csv = ", ".join(f"'{k}'" for k in clean_mukeys)

        if attribute_meta:
            norm_idx = _dynamic_index_name(attribute_meta)
            productivity_rating_source = "SDA:SDVATTRIBUTE"
            query = build_dynamic_sdv_query(attribute_meta, mukeys_csv)
        else:
            norm_idx = _normalize_productivity_index(index_type)
            if norm_idx == "nccpi":
                productivity_rating_source = PRODUCTIVITY_PROVENANCE["nccpi"]
                query = SQL_PRODUCTIVITY_NCCPI.format(
                    mukeys_csv=mukeys_csv,
                    rule_name="NCCPI - National Commodity Crop Productivity Index (Ver 3.0)",
                )
            elif norm_idx == "csr2":
                productivity_rating_source = PRODUCTIVITY_PROVENANCE["csr2"]
                query = SQL_PRODUCTIVITY_CSR2.format(mukeys_csv=mukeys_csv)
            elif norm_idx == "cpi":
                productivity_rating_source = PRODUCTIVITY_PROVENANCE["cpi"]
                query = SQL_PRODUCTIVITY_CPI.format(mukeys_csv=mukeys_csv)
            elif norm_idx == "storie":
                productivity_rating_source = PRODUCTIVITY_PROVENANCE["storie"]
                query = SQL_PRODUCTIVITY_NCCPI.format(
                    mukeys_csv=mukeys_csv,
                    rule_name="AGR - California Revised Storie Index (CA)",
                )

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
                        "productivity_rating_source": productivity_rating_source,
                        "numeric_rating": None,
                        "rated_pct": 0.0,
                        "total_pct": 0.0,
                        "is_rated": False,
                        "caveats": ["Map unit not found in SDA query results."],
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
                    if _is_productivity_sentinel(r_val, norm_idx) or r_val <= 0:
                        caveats.append(
                            f"Map unit contains unrated placeholder/sentinel code ({raw_rating})."
                        )
                    elif rated_pct <= 0:
                        caveats.append("Map unit has 0% rated component coverage.")
                    else:
                        numeric_rating = _round_for_index(r_val, norm_idx)
                        is_rated = True
                except (ValueError, TypeError):
                    caveats.append(f"Unparseable rating value '{raw_rating}'.")
            else:
                caveats.append("Map unit has no numeric productivity rating.")

            if is_rated and total_pct > 0 and rated_pct < total_pct:
                caveats.append(
                    f"Partially rated map unit: {round(rated_pct, 1)}% rated out of {round(total_pct, 1)}% total component coverage."
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
                    "productivity_rating_source": productivity_rating_source,
                    "numeric_rating": numeric_rating,
                    "rated_pct": round(rated_pct, 2),
                    "total_pct": round(total_pct, 2),
                    "is_rated": is_rated,
                    "caveats": caveats,
                }
            )

        return results
