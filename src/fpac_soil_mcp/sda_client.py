"""USDA NRCS Soil Data Access (SDA) client and query engine.

Encapsulates HTTPS communication with the USDA NRCS Soil Data Access Tabular REST service
(https://sdmdataaccess.nrcs.usda.gov/Tabular/post.rest), implementing strict coordinate and
mukey validation, fixed parameterized query templates, matrix table response parsing,
and robust retry logic.
"""

from __future__ import annotations

import logging
import re
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

logger = logging.getLogger(__name__)

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
    nasisrulename
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

SQL_PRODUCTIVITY_CSR2 = """\
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
        AND (ci.mrulename LIKE '%CSR2%' OR ci.mrulename LIKE '%csr2%' OR ci.mrulename LIKE '%Corn Suitability Rating%')
    WHERE m.mukey IN ({mukeys_csv})
      AND c.compkind != 'miscellaneous area'
)
SELECT
    mukey,
    areasymbol,
    musym,
    muname,
    ROUND(SUM(CASE WHEN rating IS NOT NULL AND rating NOT IN (99, 999, -99, -999) THEN rating * comppct_r ELSE 0 END) / NULLIF(SUM(CASE WHEN rating IS NOT NULL AND rating NOT IN (99, 999, -99, -999) THEN comppct_r ELSE 0 END), 0), 2) AS numeric_rating,
    SUM(CASE WHEN rating IS NOT NULL AND rating NOT IN (99, 999, -99, -999) THEN comppct_r ELSE 0 END) AS rated_pct,
    SUM(comppct_r) AS total_pct
FROM comp_rating
GROUP BY mukey, areasymbol, musym, muname
"""

SQL_PRODUCTIVITY_CPI = """\
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
        AND (ci.mrulename LIKE '%CPI%' OR ci.mrulename LIKE '%Crop Productivity Index%')
        AND ci.mrulename NOT LIKE '%NCCPI%'
    WHERE m.mukey IN ({mukeys_csv})
      AND c.compkind != 'miscellaneous area'
)
SELECT
    mukey,
    areasymbol,
    musym,
    muname,
    ROUND(SUM(CASE WHEN rating IS NOT NULL AND rating NOT IN (99, 999, -99, -999) THEN rating * comppct_r ELSE 0 END) / NULLIF(SUM(CASE WHEN rating IS NOT NULL AND rating NOT IN (99, 999, -99, -999) THEN comppct_r ELSE 0 END), 0), 2) AS numeric_rating,
    SUM(CASE WHEN rating IS NOT NULL AND rating NOT IN (99, 999, -99, -999) THEN comppct_r ELSE 0 END) AS rated_pct,
    SUM(comppct_r) AS total_pct
FROM comp_rating
GROUP BY mukey, areasymbol, musym, muname
"""

SQL_PRODUCTIVITY_STORIE = """\
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
        AND (ci.mrulename LIKE '%Storie%' OR ci.mrulename LIKE '%storie%')
    WHERE m.mukey IN ({mukeys_csv})
      AND c.compkind != 'miscellaneous area'
)
SELECT
    mukey,
    areasymbol,
    musym,
    muname,
    ROUND(SUM(CASE WHEN rating IS NOT NULL AND rating NOT IN (99, 999, -99, -999) THEN rating * comppct_r ELSE 0 END) / NULLIF(SUM(CASE WHEN rating IS NOT NULL AND rating NOT IN (99, 999, -99, -999) THEN comppct_r ELSE 0 END), 0), 2) AS numeric_rating,
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

SQL_PRODUCTIVITY_COUNTY_MAX_CSR2 = """\
SELECT
    MAX(ci.interphr) AS max_county_rating
FROM legend AS l
INNER JOIN mapunit AS m ON m.lkey = l.lkey
INNER JOIN component AS c ON c.mukey = m.mukey
INNER JOIN cointerp AS ci ON ci.cokey = c.cokey
WHERE l.areasymbol = '{areasymbol}'
  AND ci.ruledepth = 0
  AND (ci.mrulename LIKE '%CSR2%' OR ci.mrulename LIKE '%csr2%' OR ci.mrulename LIKE '%Corn Suitability Rating%')
  AND ci.interphr IS NOT NULL
  AND ci.interphr NOT IN (99, 999, -99, -999)
  AND c.compkind != 'miscellaneous area'
"""

SQL_PRODUCTIVITY_COUNTY_MAX_CPI = """\
SELECT
    MAX(ci.interphr) AS max_county_rating
FROM legend AS l
INNER JOIN mapunit AS m ON m.lkey = l.lkey
INNER JOIN component AS c ON c.mukey = m.mukey
INNER JOIN cointerp AS ci ON ci.cokey = c.cokey
WHERE l.areasymbol = '{areasymbol}'
  AND ci.ruledepth = 0
  AND (ci.mrulename LIKE '%CPI%' OR ci.mrulename LIKE '%Crop Productivity Index%')
  AND ci.mrulename NOT LIKE '%NCCPI%'
  AND ci.interphr IS NOT NULL
  AND ci.interphr NOT IN (99, 999, -99, -999)
  AND c.compkind != 'miscellaneous area'
"""

SQL_PRODUCTIVITY_COUNTY_MAX_STORIE = """\
SELECT
    MAX(ci.interphr) AS max_county_rating
FROM legend AS l
INNER JOIN mapunit AS m ON m.lkey = l.lkey
INNER JOIN component AS c ON c.mukey = m.mukey
INNER JOIN cointerp AS ci ON ci.cokey = c.cokey
WHERE l.areasymbol = '{areasymbol}'
  AND ci.ruledepth = 0
  AND (ci.mrulename LIKE '%Storie%' OR ci.mrulename LIKE '%storie%')
  AND ci.interphr IS NOT NULL
  AND ci.interphr NOT IN (99, 999, -99, -999)
  AND c.compkind != 'miscellaneous area'
"""


ALLOWED_SDV_TABLES = {
    "cointerp",
    "component",
    "mapunit",
    "sdvattribute",
}


def validate_survey_area_symbol(areasymbol: str) -> str:
    """Validate and normalize a soil survey area symbol."""
    clean_area = str(areasymbol).strip().upper()
    if not re.fullmatch(r"[A-Z0-9]{2,10}", clean_area):
        raise SDAValidationError(f"Invalid soil survey area symbol '{areasymbol}'.")
    return clean_area


def build_dynamic_sdv_query(
    attribute_meta: dict[str, Any],
    mukeys_csv: str | list[str | int],
) -> str:
    """Dynamically build an SDA query from an sdvattribute metadata record.

    Inspects attributetablename, attributecolumnname, and nasisrulename to construct
    an injection-safe SQL query for component-weighted or mapunit values.
    """
    table = str(attribute_meta.get("attributetablename", "")).strip().lower()
    if table not in ALLOWED_SDV_TABLES:
        raise SDAValidationError(
            f"Unsupported or unallowed SDV table '{table}'. Allowed: {sorted(ALLOWED_SDV_TABLES)}"
        )

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

    if table == "cointerp" or rule_name:
        rule_clean = rule_name.replace("'", "''")
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
    ROUND(SUM(CASE WHEN rating IS NOT NULL AND rating NOT IN (99, 999, -99, -999) THEN rating * comppct_r ELSE 0 END) / NULLIF(SUM(CASE WHEN rating IS NOT NULL AND rating NOT IN (99, 999, -99, -999) THEN comppct_r ELSE 0 END), 0), 3) AS numeric_rating,
    SUM(CASE WHEN rating IS NOT NULL AND rating NOT IN (99, 999, -99, -999) THEN comppct_r ELSE 0 END) AS rated_pct,
    SUM(comppct_r) AS total_pct
FROM comp_rating
GROUP BY mukey, areasymbol, musym, muname
"""

    if not col or not col.isalnum():
        raise SDAValidationError(f"Invalid column name '{col}' for SDV query generation.")

    if table == "mapunit":
        return f"""\
SELECT
    m.mukey,
    l.areasymbol,
    m.musym,
    m.muname,
    ROUND(CAST(m.{col} AS float), 2) AS numeric_rating,
    CASE WHEN m.{col} IS NOT NULL AND m.{col} NOT IN (99, 999) THEN 100.0 ELSE 0.0 END AS rated_pct,
    100.0 AS total_pct
FROM legend AS l
INNER JOIN mapunit AS m ON m.lkey = l.lkey
WHERE m.mukey IN ({mukeys_sql})
"""

    # Default to component-level attribute
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
    ROUND(SUM(CASE WHEN rating IS NOT NULL AND rating NOT IN (99, 999) THEN rating * comppct_r ELSE 0 END) / NULLIF(SUM(CASE WHEN rating IS NOT NULL AND rating NOT IN (99, 999) THEN comppct_r ELSE 0 END), 0), 2) AS numeric_rating,
    SUM(CASE WHEN rating IS NOT NULL AND rating NOT IN (99, 999) THEN comppct_r ELSE 0 END) AS rated_pct,
    SUM(comppct_r) AS total_pct
FROM comp_rating
GROUP BY mukey, areasymbol, musym, muname
"""


def build_dynamic_sdv_county_max_query(
    attribute_meta: dict[str, Any],
    areasymbol: str,
) -> str:
    """Dynamically build an SDA query for maximum county rating from sdvattribute metadata."""
    areasymbol = validate_survey_area_symbol(areasymbol)
    table = str(attribute_meta.get("attributetablename", "")).strip().lower()
    col = str(attribute_meta.get("attributecolumnname", "")).strip()
    rule_name = str(attribute_meta.get("nasisrulename", "")).strip()

    if table not in ALLOWED_SDV_TABLES:
        raise SDAValidationError(
            f"Unsupported or unallowed SDV table '{table}'. Allowed: {sorted(ALLOWED_SDV_TABLES)}"
        )

    if table == "cointerp" or rule_name:
        rule_clean = rule_name.replace("'", "''")
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
  AND ci.interphr IS NOT NULL
  AND ci.interphr NOT IN (99, 999, -99, -999)
  AND c.compkind != 'miscellaneous area'
"""

    if not col or not col.isalnum():
        raise SDAValidationError(f"Invalid column name '{col}' for county max query generation.")

    if table == "mapunit":
        return f"""\
SELECT
    MAX(CAST(m.{col} AS float)) AS max_county_rating
FROM legend AS l
INNER JOIN mapunit AS m ON m.lkey = l.lkey
WHERE l.areasymbol = '{areasymbol}'
  AND m.{col} IS NOT NULL
  AND m.{col} NOT IN (99, 999)
"""

    return f"""\
SELECT
    MAX(CAST(c.{col} AS float)) AS max_county_rating
FROM legend AS l
INNER JOIN mapunit AS m ON m.lkey = l.lkey
INNER JOIN component AS c ON c.mukey = m.mukey
WHERE l.areasymbol = '{areasymbol}'
  AND c.{col} IS NOT NULL
  AND c.{col} NOT IN (99, 999)
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
            return self._parse_table_response(response.json())
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
            index_type: Productivity index type ('nccpi', 'csr2', 'cpi', 'storie') or custom attribute.
            attribute_meta: Optional sdvattribute record for dynamic query generation.

        Returns:
            Maximum rating float if found, else None.

        Raises:
            SDAValidationError: If areasymbol or index_type is invalid.
            SDAQueryError: If query execution fails.
        """
        clean_area = validate_survey_area_symbol(areasymbol)

        idx = index_type.strip().lower()
        if attribute_meta:
            query = build_dynamic_sdv_county_max_query(attribute_meta, clean_area)
        elif idx in ("nccpi", "nccpi_v3", "national commodity crop productivity index"):
            query = SQL_PRODUCTIVITY_COUNTY_MAX_NCCPI.format(
                areasymbol=clean_area,
                rule_name="NCCPI - National Commodity Crop Productivity Index (Ver 3.0)",
            )
        elif idx in ("csr2", "iacsr2", "iowa csr2"):
            query = SQL_PRODUCTIVITY_COUNTY_MAX_CSR2.format(areasymbol=clean_area)
        elif idx in ("cpi", "minnesota cpi"):
            query = SQL_PRODUCTIVITY_COUNTY_MAX_CPI.format(areasymbol=clean_area)
        elif idx in ("storie", "storie_index", "california storie"):
            query = SQL_PRODUCTIVITY_COUNTY_MAX_STORIE.format(areasymbol=clean_area)
        else:
            # Attempt dynamic lookup by pattern if index_type looks like an attribute name
            matched_attrs = self.lookup_sdv_attribute(index_type)
            if matched_attrs:
                query = build_dynamic_sdv_county_max_query(matched_attrs[0], clean_area)
            else:
                raise SDAValidationError(
                    f"Unsupported productivity index type '{index_type}'. Supported: 'nccpi', 'csr2', 'cpi', 'storie' or valid sdvattribute."
                )

        rows = self._execute_query(query)
        if not rows:
            return None

        val = rows[0].get("max_county_rating")
        if val is None or val in ("", "None", 99, 999, "99", "999"):
            return None
        try:
            val_float = float(val)
            if val_float in (99.0, 999.0) or val_float <= 0:
                return None
            return round(val_float, 3 if idx.startswith("nccpi") else 2)
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
            index_type: 'nccpi', 'csr2', 'cpi', 'storie', or custom attribute name.
            areasymbol: Optional county/survey area symbol filter or override.
            attribute_meta: Optional sdvattribute record for dynamic query generation.

        Returns:
            List of structured rating dictionaries with component rated percentages and caveats.

        Raises:
            SDAValidationError: If mukeys or index_type are invalid.
            SDAQueryError: If SDA query fails.
        """
        if not mukeys:
            return []

        clean_mukeys = [self.validate_mukey(k) for k in mukeys]
        mukeys_csv = ", ".join(f"'{k}'" for k in clean_mukeys)

        idx = index_type.strip().lower()
        if attribute_meta:
            norm_idx = str(attribute_meta.get("attributename", index_type)).lower()
            query = build_dynamic_sdv_query(attribute_meta, mukeys_csv)
        elif idx in ("nccpi", "nccpi_v3", "national commodity crop productivity index"):
            norm_idx = "nccpi"
            query = SQL_PRODUCTIVITY_NCCPI.format(
                mukeys_csv=mukeys_csv,
                rule_name="NCCPI - National Commodity Crop Productivity Index (Ver 3.0)",
            )
        elif idx in ("csr2", "iacsr2", "iowa csr2"):
            norm_idx = "csr2"
            query = SQL_PRODUCTIVITY_CSR2.format(mukeys_csv=mukeys_csv)
        elif idx in ("cpi", "minnesota cpi"):
            norm_idx = "cpi"
            query = SQL_PRODUCTIVITY_CPI.format(mukeys_csv=mukeys_csv)
        elif idx in ("storie", "storie_index", "california storie"):
            norm_idx = "storie"
            query = SQL_PRODUCTIVITY_STORIE.format(mukeys_csv=mukeys_csv)
        else:
            matched_attrs = self.lookup_sdv_attribute(index_type)
            if matched_attrs:
                norm_idx = str(matched_attrs[0].get("attributename", index_type)).lower()
                query = build_dynamic_sdv_query(matched_attrs[0], mukeys_csv)
            else:
                raise SDAValidationError(
                    f"Unsupported productivity index type '{index_type}'. Supported: 'nccpi', 'csr2', 'cpi', 'storie' or valid sdvattribute."
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
                    if r_val in (99.0, 999.0) or r_val < 0:
                        caveats.append(
                            f"Map unit contains unrated placeholder/sentinel code ({raw_rating})."
                        )
                    elif rated_pct <= 0:
                        caveats.append("Map unit has 0% rated component coverage.")
                    else:
                        numeric_rating = round(r_val, 3 if norm_idx == "nccpi" else 2)
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
                    "numeric_rating": numeric_rating,
                    "rated_pct": round(rated_pct, 2),
                    "total_pct": round(total_pct, 2),
                    "is_rated": is_rated,
                    "caveats": caveats,
                }
            )

        return results
