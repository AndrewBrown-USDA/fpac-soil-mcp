"""Fixed SQL query templates and dynamic SDV query builders for SDA.

Encapsulates all SQL formatting, parameterized query templates, and per-strategy
query generation for USDA NRCS Soil Data Access.
"""

from __future__ import annotations

import re
from typing import Any

from fpac_soil_mcp.clients.sda.client import SDAValidationError
from fpac_soil_mcp.clients.sda.sdv_registry import (
    ALLOWED_SDV_TABLES,
    SdvRatingSpec,
    _record_constraints,
    resolve_sdv_spec,
)

# ---------------------------------------------------------------------------
# Fixed SQL query templates - no user SQL passthrough allowed
# ---------------------------------------------------------------------------

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

# ---------------------------------------------------------------------------
# Validation helpers for query builders
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Strategy query builders
# ---------------------------------------------------------------------------


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
    if spec.nulls_as_zero and spec.table in ALLOWED_SDV_TABLES:
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
