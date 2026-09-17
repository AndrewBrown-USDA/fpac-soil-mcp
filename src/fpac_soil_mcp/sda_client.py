"""USDA NRCS Soil Data Access (SDA) client and query engine.

Encapsulates HTTPS communication with the USDA NRCS Soil Data Access Tabular REST service
(https://sdmdataaccess.nrcs.usda.gov/Tabular/post.rest), implementing strict coordinate and
mukey validation, fixed parameterized query templates, matrix table response parsing,
and robust retry logic.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from fpac_soil_mcp.config import settings

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


class SDAClientError(Exception):
    """Base exception for SDA Client errors."""


class SDAValidationError(SDAClientError):
    """Raised when coordinate or mukey validation fails."""


class SDAQueryError(SDAClientError):
    """Raised when SDA returns an API-level error or invalid response."""


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
        last_exception: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                if self._http_client is not None:
                    response = self._http_client.post(
                        self.base_url,
                        json=payload,
                        timeout=self.timeout,
                    )
                else:
                    with httpx.Client(timeout=self.timeout) as client:
                        response = client.post(
                            self.base_url,
                            json=payload,
                        )

                response.raise_for_status()
                data = response.json()
                return self._parse_table_response(data)

            except httpx.HTTPStatusError as exc:
                last_exception = exc
                logger.warning(
                    "SDA HTTP status error on attempt %d/%d: %s",
                    attempt,
                    self.max_retries,
                    exc,
                )
                if exc.response.status_code < 500:
                    # Client errors (4xx) are not retried
                    raise SDAQueryError(
                        f"SDA client error ({exc.response.status_code}): {exc.response.text}"
                    ) from exc
            except (httpx.RequestError, httpx.TimeoutException) as exc:
                last_exception = exc
                logger.warning(
                    "SDA request error on attempt %d/%d: %s",
                    attempt,
                    self.max_retries,
                    exc,
                )
            except SDAQueryError:
                raise

            if attempt < self.max_retries:
                backoff_delay = 0.5 * (2 ** (attempt - 1))
                time.sleep(backoff_delay)

        raise SDAQueryError(
            f"Failed to query SDA after {self.max_retries} attempts: {last_exception}"
        ) from last_exception

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
        wkt = str(wkt_geometry).strip()
        if not wkt.upper().startswith(("POLYGON", "MULTIPOLYGON")):
            raise SDAValidationError(
                f"Geometry must be a POLYGON or MULTIPOLYGON WKT string; received '{wkt[:30]}...'"
            )
        # Verify basic character whitelist to prevent injection
        if any(c in wkt for c in [";", "--", "/*", "*/", "DROP", "EXEC"]):
            raise SDAValidationError("Invalid characters detected in WKT geometry string.")

        query = SQL_POLYGON_LOOKUP.format(wkt=wkt)
        return self._execute_query(query)

    def get_interpretations(
        self,
        mukeys: list[str | int],
        rule_name: str = "NCCPI - National Commodity Crop Productivity Index (v3)",
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

        if rule_name not in settings.sda_interpretation_rules_allowed:
            raise SDAValidationError(
                f"Rule '{rule_name}' is not in allowed SDA interpretation rules: {settings.sda_interpretation_rules_allowed}"
            )

        if aggregation_method not in settings.sda_aggregation_methods_allowed:
            raise SDAValidationError(
                f"Aggregation method '{aggregation_method}' is not in allowed methods: {settings.sda_aggregation_methods_allowed}"
            )

        if aggregation_method == "Dominant Component":
            query = SQL_INTERPRETATION_DOMINANT_COMP.format(
                mukeys_csv=mukeys_csv,
                rule_name=rule_name,
            )
        else:
            query = SQL_INTERPRETATION_WEIGHTED_AVG.format(
                mukeys_csv=mukeys_csv,
                rule_name=rule_name,
            )

        return self._execute_query(query)
