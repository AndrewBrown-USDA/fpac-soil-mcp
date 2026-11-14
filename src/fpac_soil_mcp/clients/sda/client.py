"""USDA NRCS Soil Data Access (SDA) client and query engine.

Encapsulates HTTPS communication with the USDA NRCS Soil Data Access Tabular REST service
(https://sdmdataaccess.nrcs.usda.gov/Tabular/post.rest), implementing strict coordinate and
mukey validation, fixed parameterized query templates, matrix table response parsing,
and robust retry logic.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import httpx

try:
    from fpac_soil_mcp.core.config import settings
except ImportError:
    from fpac_soil_mcp.config import settings

try:
    from fpac_soil_mcp.core.errors import DomainError, UpstreamError, ValidationError
except ImportError:
    DomainError = Exception  # type: ignore[assignment,misc]
    ValidationError = ValueError  # type: ignore[assignment,misc]
    UpstreamError = Exception  # type: ignore[assignment,misc]

try:
    from fpac_soil_mcp.spatial.geometry import (
        GeometryValidationError,
        validate_and_sanitize_polygon_wkt,
    )
except ImportError:
    from fpac_soil_mcp.geometry import (
        GeometryValidationError,
        validate_and_sanitize_polygon_wkt,
    )

try:
    from fpac_soil_mcp.clients.http import (
        HttpRequestError,
        HttpStatusError,
        execute_http_request_with_retry,
    )
except ImportError:
    from fpac_soil_mcp.http_client import (
        HttpRequestError,
        HttpStatusError,
        execute_http_request_with_retry,
    )

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------


class SDAClientError(DomainError):
    """Base exception for SDA Client errors."""


class SDAValidationError(SDAClientError, ValidationError):
    """Raised when coordinate, mukey, or registry validation fails."""


class SDAQueryError(SDAClientError, UpstreamError):
    """Raised when SDA returns an API-level error or invalid response."""


class SDATimeoutError(SDAClientError, UpstreamError):
    """Raised when an SDA request times out."""


class SDAServiceUnavailableError(SDAClientError, UpstreamError):
    """Raised when SDA is temporarily unavailable (e.g. daily maintenance window)."""


# Import sibling modules after exceptions are defined to avoid circular import issues
from fpac_soil_mcp.clients.sda import sdv_registry, sql_templates


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
        query = sql_templates.SQL_POINT_LOOKUP.format(latitude=lat, longitude=lon)
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
        query = sql_templates.SQL_MUKEY_LOOKUP.format(mukey=valid_mukey)
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

        query = sql_templates.SQL_POLYGON_LOOKUP.format(wkt=wkt)
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
        template = (
            sql_templates.SQL_SPATIAL_INTERSECTION_CLIPPED
            if clip
            else sql_templates.SQL_SPATIAL_INTERSECTION_OVERLAP
        )
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

        results = self._execute_query(sql_templates.SQL_INTERPRETATION_CATALOG)
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
            query = sql_templates.SQL_INTERPRETATION_DOMINANT_COMP.format(
                mukeys_csv=mukeys_csv,
                rule_name=rule_clean,
            )
        else:
            query = sql_templates.SQL_INTERPRETATION_WEIGHTED_AVG.format(
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

        query = sql_templates.SQL_SDV_ATTRIBUTE_LOOKUP.format(pattern=pattern_clean)
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
        clean_area = sql_templates.validate_survey_area_symbol(areasymbol)
        spec, resolved = sdv_registry._resolve_productivity_spec(
            index_type, attribute_meta, constraints
        )
        query = sql_templates.build_sdv_county_max_query(spec, clean_area, resolved)

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

        spec, resolved = sdv_registry._resolve_productivity_spec(
            index_type, attribute_meta, constraints
        )
        norm_idx = spec.spec_id
        provenance = sdv_registry._build_sdv_provenance(spec, resolved)
        query = sql_templates.build_sdv_rating_query(spec, mukeys_csv, resolved)

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
                        "caveats": [sdv_registry.SDV_CAVEATS["not_found"]],
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
                        caveats.append(
                            sdv_registry.SDV_CAVEATS["unrated_sentinel"].format(value=raw_rating)
                        )
                    elif rated_pct <= 0:
                        caveats.append(sdv_registry.SDV_CAVEATS["no_coverage"])
                    else:
                        numeric_rating = round(r_val, spec.precision)
                        is_rated = True
                except (ValueError, TypeError):
                    caveats.append(sdv_registry.SDV_CAVEATS["unparseable"].format(value=raw_rating))
            else:
                caveats.append(sdv_registry.SDV_CAVEATS["no_rating"])

            if is_rated and total_pct > 0 and rated_pct < total_pct:
                caveats.append(
                    sdv_registry.SDV_CAVEATS["partial_rating"].format(
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
                        sdv_registry.SDV_CAVEATS["mixed_units"].format(
                            min_unit=yld_min, max_unit=yld_max
                        )
                    )
                    row_provenance["yldunits"] = None
                else:
                    row_provenance["yldunits"] = yld_min

            if is_rated:
                coverage_status = "partial" if total_pct > 0 and rated_pct < total_pct else "rated"
            else:
                coverage_status = "unrated" if rated_pct > 0 or total_pct > 0 else "no_coverage"

            # Method and scope caveats, fixed order.
            if spec.algorithm == "Dominant Condition":
                caveats.append(sdv_registry.SDV_CAVEATS["dominant_condition"])
            if spec.table == "chorizon":
                caveats.append(sdv_registry.SDV_CAVEATS["aws_fixed_depth"])
            if spec.table == "cocropyld":
                caveats.append(
                    sdv_registry.SDV_CAVEATS["crop_specific"].format(
                        crop=(resolved or {}).get("cropname", "")
                    )
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
