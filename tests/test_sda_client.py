"""Unit tests for SDAClient validation, response parsing, retries, and errors."""

from __future__ import annotations

import httpx
import pytest

from fpac_soil_mcp.sda_client import (
    ALLOWED_SDV_TABLES,
    SQL_MUKEY_LOOKUP,
    SQL_POINT_LOOKUP,
    SDAClient,
    SDAQueryError,
    SDAServiceUnavailableError,
    SDAValidationError,
    build_dynamic_sdv_county_max_query,
    build_dynamic_sdv_query,
)


class TestSDAValidation:
    """Test coordinate and mukey validation rules."""

    def test_validate_coordinates_valid(self) -> None:
        lat, lon = SDAClient.validate_coordinates(39.7684, -86.1581)
        assert lat == 39.7684
        assert lon == -86.1581

    def test_validate_coordinates_boundary_values(self) -> None:
        assert SDAClient.validate_coordinates(-90.0, -180.0) == (-90.0, -180.0)
        assert SDAClient.validate_coordinates(90.0, 180.0) == (90.0, 180.0)
        assert SDAClient.validate_coordinates(0, 0) == (0.0, 0.0)

    def test_validate_coordinates_string_conversion(self) -> None:
        lat, lon = SDAClient.validate_coordinates("39.7684", "-86.1581")  # type: ignore[arg-type]
        assert lat == 39.7684
        assert lon == -86.1581

    def test_validate_coordinates_invalid_latitude_high(self) -> None:
        with pytest.raises(SDAValidationError, match="Latitude must be between -90.0 and 90.0"):
            SDAClient.validate_coordinates(90.1, -86.1581)

    def test_validate_coordinates_invalid_latitude_low(self) -> None:
        with pytest.raises(SDAValidationError, match="Latitude must be between -90.0 and 90.0"):
            SDAClient.validate_coordinates(-90.1, -86.1581)

    def test_validate_coordinates_invalid_longitude_high(self) -> None:
        with pytest.raises(SDAValidationError, match="Longitude must be between -180.0 and 180.0"):
            SDAClient.validate_coordinates(39.7684, 180.1)

    def test_validate_coordinates_invalid_longitude_low(self) -> None:
        with pytest.raises(SDAValidationError, match="Longitude must be between -180.0 and 180.0"):
            SDAClient.validate_coordinates(39.7684, -180.1)

    def test_validate_coordinates_non_numeric(self) -> None:
        with pytest.raises(SDAValidationError, match="Invalid coordinate format"):
            SDAClient.validate_coordinates("invalid", -86.1581)  # type: ignore[arg-type]

    def test_validate_mukey_valid_int(self) -> None:
        assert SDAClient.validate_mukey(412915) == "412915"

    def test_validate_mukey_valid_str(self) -> None:
        assert SDAClient.validate_mukey("412915") == "412915"
        assert SDAClient.validate_mukey(" 412915 ") == "412915"

    def test_validate_mukey_invalid_negative(self) -> None:
        with pytest.raises(SDAValidationError, match="must be a positive integer"):
            SDAClient.validate_mukey(-5)

    def test_validate_mukey_invalid_zero(self) -> None:
        with pytest.raises(SDAValidationError, match="must be a positive integer"):
            SDAClient.validate_mukey(0)

    def test_validate_mukey_invalid_alphanumeric(self) -> None:
        with pytest.raises(SDAValidationError, match="must be a positive integer"):
            SDAClient.validate_mukey("412915; DROP TABLE mapunit;--")

    def test_validate_wkt_invalid_malicious_input(self) -> None:
        with pytest.raises(SDAValidationError, match="Invalid or unparseable WKT"):
            SDAClient.validate_wkt("POLYGON((0 0, 1 1)); DROP TABLE mapunit;--")

    def test_validate_wkt_injection_attack_strings(self) -> None:
        malicious_inputs = [
            "POLYGON((0 0, 10 0, 10 10, 0 10, 0 0))' OR '1'='1",
            "POLYGON((0 0, 10 0, 10 10, 0 10, 0 0)); DROP TABLE mupolygon; --",
            "'; EXEC sp_msforeachtable 'DROP TABLE ?'--",
        ]
        for bad_wkt in malicious_inputs:
            with pytest.raises(SDAValidationError):
                SDAClient.validate_wkt(bad_wkt)

    def test_validate_wkt_non_polygon_rejected(self) -> None:
        with pytest.raises(SDAValidationError, match="must be a Polygon or MultiPolygon"):
            SDAClient.validate_wkt("POINT(-86.1581 39.7684)")

    def test_dynamic_sdv_query_rejects_invalid_mukeys(self) -> None:
        with pytest.raises(SDAValidationError):
            build_dynamic_sdv_query(
                {"attributetablename": "mapunit", "attributecolumnname": "nccpi"},
                ["123; DROP TABLE mapunit;--"],
            )

    def test_dynamic_sdv_query_rejects_direct_mukey_csv_injection(self) -> None:
        with pytest.raises(SDAValidationError):
            build_dynamic_sdv_query(
                {"attributetablename": "mapunit", "attributecolumnname": "nccpi"},
                "'123', '456' OR 1=1 --",
            )

    def test_dynamic_sdv_county_max_query_rejects_invalid_areasymbol(self) -> None:
        with pytest.raises(SDAValidationError):
            build_dynamic_sdv_county_max_query(
                {"attributetablename": "mapunit", "attributecolumnname": "nccpi"},
                "IA169'; DROP TABLE mapunit;--",
            )

    def test_dynamic_sdv_county_max_query_rejects_invalid_direct_areasymbol(self) -> None:
        with pytest.raises(SDAValidationError):
            build_dynamic_sdv_county_max_query(
                {"attributetablename": "mapunit", "attributecolumnname": "nccpi"},
                "IA 169",
            )

    def test_dynamic_sdv_table_allowlist_excludes_unsupported_tables(self) -> None:
        assert "corestrictions" not in ALLOWED_SDV_TABLES
        assert "muaggatt" not in ALLOWED_SDV_TABLES

    def test_dynamic_sdv_table_allowlist_includes_chorizon_and_cocropyld(self) -> None:
        assert "chorizon" in ALLOWED_SDV_TABLES
        assert "cocropyld" in ALLOWED_SDV_TABLES


class TestSDAParsing:
    """Test parsing of SDA JSON table responses."""

    def test_parse_table_response_valid(self) -> None:
        data = {
            "Table": [
                ["mukey", "musym", "muname", "farmlndcl", "areasymbol"],
                ["412915", "MmA", "Miami silt loam", "All areas are prime farmland", "IN097"],
            ]
        }
        results = SDAClient._parse_table_response(data)
        assert len(results) == 1
        assert results[0] == {
            "mukey": "412915",
            "musym": "MmA",
            "muname": "Miami silt loam",
            "farmlndcl": "All areas are prime farmland",
            "areasymbol": "IN097",
        }

    def test_parse_table_response_multiple_rows(self) -> None:
        data = {
            "Table": [
                ["mukey", "musym"],
                ["100", "A"],
                ["200", "B"],
            ]
        }
        results = SDAClient._parse_table_response(data)
        assert len(results) == 2
        assert results[0] == {"mukey": "100", "musym": "A"}
        assert results[1] == {"mukey": "200", "musym": "B"}

    def test_parse_table_response_empty_table(self) -> None:
        data = {"Table": []}
        results = SDAClient._parse_table_response(data)
        assert results == []

    def test_parse_table_response_headers_only(self) -> None:
        data = {"Table": [["mukey", "musym", "muname"]]}
        results = SDAClient._parse_table_response(data)
        assert results == []

    def test_parse_table_response_missing_table_key(self) -> None:
        data: dict = {}
        results = SDAClient._parse_table_response(data)
        assert results == []

    def test_parse_table_response_error_payload(self) -> None:
        data = {"ErrorMessage": "Query timed out"}
        with pytest.raises(SDAQueryError, match="SDA returned error: Query timed out"):
            SDAClient._parse_table_response(data)

    def test_parse_table_response_error_key(self) -> None:
        data = {"Error": "Syntax error in SQL"}
        with pytest.raises(SDAQueryError, match="SDA returned error: Syntax error in SQL"):
            SDAClient._parse_table_response(data)

    def test_parse_table_response_non_dict(self) -> None:
        with pytest.raises(SDAQueryError, match="Unexpected SDA response format"):
            SDAClient._parse_table_response("invalid json text")  # type: ignore[arg-type]

    def test_parse_table_response_invalid_table_type(self) -> None:
        with pytest.raises(SDAQueryError, match="Unexpected 'Table' structure"):
            SDAClient._parse_table_response({"Table": "not-a-list"})


class TestSDAClientExecution:
    """Test SDAClient query execution, retries, and network behavior."""

    def test_get_by_point_success(self, mock_sda_prime_response: dict) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert b"POINT(-86.1581 39.7684)" in request.content
            return httpx.Response(200, json=mock_sda_prime_response)

        client = SDAClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        results = client.get_by_point(39.7684, -86.1581)
        assert len(results) == 1
        assert results[0]["mukey"] == "412915"
        assert results[0]["farmlndcl"] == "All areas are prime farmland"

    def test_get_by_mukey_success(self, mock_sda_prime_response: dict) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert b"m.mukey = '412915'" in request.content
            return httpx.Response(200, json=mock_sda_prime_response)

        client = SDAClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        results = client.get_by_mukey(412915)
        assert len(results) == 1
        assert results[0]["mukey"] == "412915"

    def test_client_error_4xx_not_retried(self) -> None:
        attempts = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempts
            attempts += 1
            return httpx.Response(400, text="Bad Request")

        client = SDAClient(
            max_retries=3,
            http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        )
        with pytest.raises(SDAQueryError, match="SDA client error"):
            client.get_by_point(39.7684, -86.1581)

        assert attempts == 1  # 4xx errors should fail immediately without retries

    def test_server_error_5xx_retries_and_fails(self) -> None:
        attempts = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempts
            attempts += 1
            return httpx.Response(500, text="Internal Server Error")

        client = SDAClient(
            max_retries=3,
            http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        )
        with pytest.raises(SDAQueryError, match="Failed to query SDA after 3 attempts"):
            client.get_by_point(39.7684, -86.1581)

        assert attempts == 3

    def test_maintenance_html_raises_service_unavailable(self) -> None:
        html = (
            "<html><body><h1>Site is under daily maintenance from "
            "12:30 AM CST to 12:45 AM CST. Please try after 12:45 AM CST."
            "</h1></body></html>"
        )

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, text=html, headers={"content-type": "text/html"})

        client = SDAClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        with pytest.raises(SDAServiceUnavailableError, match="maintenance"):
            client.get_by_point(39.7684, -86.1581)

    def test_non_json_non_maintenance_raises_query_error(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, text="<html>unexpected</html>")

        client = SDAClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        with pytest.raises(SDAQueryError, match="non-JSON response"):
            client.get_by_point(39.7684, -86.1581)

    def test_retry_eventual_success(self, mock_sda_prime_response: dict) -> None:
        attempts = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempts
            attempts += 1
            if attempts < 2:
                return httpx.Response(503, text="Service Unavailable")
            return httpx.Response(200, json=mock_sda_prime_response)

        client = SDAClient(
            max_retries=3,
            http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        )
        results = client.get_by_point(39.7684, -86.1581)
        assert attempts == 2
        assert len(results) == 1
        assert results[0]["mukey"] == "412915"

    def test_query_templates(self) -> None:
        # Verify SQL templates have expected fixed structures
        point_sql = SQL_POINT_LOOKUP.format(latitude=39.7684, longitude=-86.1581)
        assert "SDA_Get_Mukey_from_intersection_with_WktWgs84" in point_sql
        assert "POINT(-86.1581 39.7684)" in point_sql

        mukey_sql = SQL_MUKEY_LOOKUP.format(mukey="412915")
        assert "WHERE m.mukey = '412915'" in mukey_sql

    def test_get_by_polygon_success(self, mock_sda_prime_response: dict) -> None:
        wkt = "POLYGON((-93.5 42.0, -93.4 42.0, -93.4 42.1, -93.5 42.1, -93.5 42.0))"

        def handler(request: httpx.Request) -> httpx.Response:
            assert b"POLYGON" in request.content
            return httpx.Response(200, json=mock_sda_prime_response)

        client = SDAClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        results = client.get_by_polygon(wkt)
        assert len(results) == 1
        assert results[0]["mukey"] == "412915"

    def test_get_interpretations_weighted_avg_success(self) -> None:
        mock_interp_resp = {
            "Table": [
                [
                    "mukey",
                    "areasymbol",
                    "musym",
                    "muname",
                    "numeric_rating",
                    "rating_class",
                    "rated_pct",
                    "total_pct",
                ],
                ["412915", "IN097", "MmA", "Miami silt loam", 0.78, "High", 95, 100],
            ]
        }

        def handler(request: httpx.Request) -> httpx.Response:
            assert b"comp_interp" in request.content
            return httpx.Response(200, json=mock_interp_resp)

        client = SDAClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        results = client.get_interpretations(["412915"])
        assert len(results) == 1
        assert results[0]["mukey"] == "412915"
        assert results[0]["numeric_rating"] == 0.78
        assert results[0]["rating_class"] == "High"

    def test_get_interpretations_unsupported_aggregation_method(self) -> None:
        client = SDAClient()
        with pytest.raises(
            SDAValidationError, match="Aggregation method 'Dominant Condition' is not in allowed"
        ):
            client.get_interpretations(["412915"], aggregation_method="Dominant Condition")

    def test_get_interpretations_fresh_client_catalog_lookup(self) -> None:
        mock_catalog_resp = {
            "Table": [
                ["mrulename"],
                ["Custom Soil Productivity Index"],
            ]
        }
        mock_interp_resp = {
            "Table": [
                [
                    "mukey",
                    "areasymbol",
                    "musym",
                    "muname",
                    "numeric_rating",
                    "rating_class",
                    "rated_pct",
                    "total_pct",
                ],
                ["412915", "IN097", "MmA", "Miami silt loam", 0.85, "High", 95, 100],
            ]
        }

        def handler(request: httpx.Request) -> httpx.Response:
            if b"sdvattribute" in request.content:
                return httpx.Response(200, json=mock_catalog_resp)
            return httpx.Response(200, json=mock_interp_resp)

        client = SDAClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        assert client._cached_rule_names is None
        results = client.get_interpretations(["412915"], rule_name="Custom Soil Productivity Index")
        assert len(results) == 1
        assert results[0]["numeric_rating"] == 0.85

    def test_get_interpretations_invalid_catalog_rule_rejected(self) -> None:
        mock_catalog_resp = {
            "Table": [
                ["mrulename"],
                ["Allowed Rule A"],
            ]
        }

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=mock_catalog_resp)

        client = SDAClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        with pytest.raises(SDAValidationError, match="not found in SDA cointerp rule catalog"):
            client.get_interpretations(["412915"], rule_name="Nonexistent Custom Rule")

    def test_get_spatial_intersection_clipped(self) -> None:
        wkt = "POLYGON((-93.5 42.0, -93.4 42.0, -93.4 42.1, -93.5 42.1, -93.5 42.0))"
        mock_spatial_resp = {
            "Table": [
                ["mukey", "musym", "muname", "farmlndcl", "areasymbol", "area_ac"],
                ["412915", "138B", "Clarion loam", "All areas are prime farmland", "IA169", 25.4],
            ]
        }

        def handler(request: httpx.Request) -> httpx.Response:
            assert b"STIntersection" in request.content
            assert b"STArea()" in request.content
            return httpx.Response(200, json=mock_spatial_resp)

        client = SDAClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        results = client.get_spatial_intersection(wkt, clip=True, geom_acres=True)
        assert len(results) == 1
        assert results[0]["mukey"] == "412915"
        assert results[0]["area_ac"] == 25.4

    def test_get_spatial_intersection_without_geom_acres(self) -> None:
        wkt = "POLYGON((-93.5 42.0, -93.4 42.0, -93.4 42.1, -93.5 42.1, -93.5 42.0))"
        mock_spatial_resp = {
            "Table": [
                ["mukey", "musym", "muname", "farmlndcl", "areasymbol", "area_ac"],
                ["412915", "138B", "Clarion loam", "All areas are prime farmland", "IA169", None],
            ]
        }

        def handler(request: httpx.Request) -> httpx.Response:
            assert b"STIntersection" in request.content
            assert b"CAST(NULL AS float) AS area_ac" in request.content
            assert b"STArea()" not in request.content
            return httpx.Response(200, json=mock_spatial_resp)

        client = SDAClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        results = client.get_spatial_intersection(wkt, clip=True, geom_acres=False)
        assert len(results) == 1
        assert results[0]["mukey"] == "412915"
        assert results[0]["area_ac"] is None

    def test_get_spatial_intersection_with_geometry(self) -> None:
        wkt = "POLYGON((-93.5 42.0, -93.4 42.0, -93.4 42.1, -93.5 42.1, -93.5 42.0))"
        mock_spatial_resp = {
            "Table": [
                ["mukey", "musym", "muname", "farmlndcl", "areasymbol", "area_ac", "geom"],
                [
                    "412915",
                    "138B",
                    "Clarion loam",
                    "All areas are prime farmland",
                    "IA169",
                    25.4,
                    "POLYGON((-93.5 42.0, -93.4 42.0, -93.4 42.1, -93.5 42.1, -93.5 42.0))",
                ],
            ]
        }

        def handler(request: httpx.Request) -> httpx.Response:
            assert b"STAsText() AS geom" in request.content
            return httpx.Response(200, json=mock_spatial_resp)

        client = SDAClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        results = client.get_spatial_intersection(wkt, clip=True, return_geom=True)
        assert len(results) == 1
        assert results[0]["geom"].startswith("POLYGON")

    def test_get_available_interpretation_rules(self) -> None:
        mock_catalog_resp = {
            "Table": [
                ["mrulename"],
                ["NCCPI - National Commodity Crop Productivity Index (Ver 3.0)"],
                ["Farmland Classification"],
            ]
        }

        def handler(request: httpx.Request) -> httpx.Response:
            assert b"sdvattribute" in request.content
            return httpx.Response(200, json=mock_catalog_resp)

        client = SDAClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        rules = client.get_available_interpretation_rules()
        assert "Farmland Classification" in rules
        assert len(rules) == 2

    def test_get_county_max_productivity_rating_nccpi(self) -> None:
        mock_resp = {
            "Table": [
                ["max_county_rating"],
                [0.94],
            ]
        }

        def handler(request: httpx.Request) -> httpx.Response:
            assert b"areasymbol = 'IL019'" in request.content
            return httpx.Response(200, json=mock_resp)

        client = SDAClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        val = client.get_county_max_productivity_rating("IL019", index_type="nccpi")
        assert val == 0.94

    def test_get_county_max_productivity_rating_rejects_unsupported_without_sda_call(
        self,
    ) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise AssertionError("unsupported selector must not reach SDA")

        client = SDAClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        with pytest.raises(SDAValidationError, match="Unsupported productivity index type"):
            client.get_county_max_productivity_rating("IA169", index_type="unsupported")

    def test_get_county_max_productivity_rating_sentinels_and_nulls(self) -> None:
        client = SDAClient()
        with pytest.raises(SDAValidationError):
            client.get_county_max_productivity_rating("IA169", "unsupported")

    def test_get_county_max_productivity_rating_validation_errors(self) -> None:
        client = SDAClient()
        with pytest.raises(SDAValidationError, match="Invalid soil survey area symbol"):
            client.get_county_max_productivity_rating("INVALID-AREA!", "unsupported")

        with pytest.raises(SDAValidationError, match="Unsupported productivity index type"):
            client.get_county_max_productivity_rating("IA169", "unknown_index")

    def test_get_productivity_ratings_nccpi(self) -> None:
        mock_resp = {
            "Table": [
                [
                    "mukey",
                    "areasymbol",
                    "musym",
                    "muname",
                    "numeric_rating",
                    "rating_class",
                    "rated_pct",
                    "total_pct",
                    "comp_count",
                ],
                ["402001", "IL019", "152A", "Drummer silty clay loam", 0.89, "High", 95, 100, 3],
            ]
        }

        def handler(request: httpx.Request) -> httpx.Response:
            assert b"cointerp" in request.content
            return httpx.Response(200, json=mock_resp)

        client = SDAClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        results = client.get_productivity_ratings(["402001"], index_type="nccpi")
        assert len(results) == 1
        assert results[0]["mukey"] == "402001"
        assert results[0]["numeric_rating"] == 0.89
        assert results[0]["is_rated"] is True
        assert results[0]["index_type"] == "nccpi"

    def test_get_productivity_ratings_rejects_unsupported_without_sda_call(
        self,
    ) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise AssertionError("unsupported selector must not reach SDA")

        client = SDAClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        with pytest.raises(SDAValidationError, match="Unsupported productivity index type"):
            client.get_productivity_ratings(["406439"], index_type="unsupported")

    def test_get_productivity_ratings_unrated_and_missing(self) -> None:
        mock_resp = {
            "Table": [
                [
                    "mukey",
                    "areasymbol",
                    "musym",
                    "muname",
                    "numeric_rating",
                    "rating_class",
                    "rated_pct",
                    "total_pct",
                    "comp_count",
                ],
                ["402099", "IL019", "W", "Water", None, None, 0, 100, 1],
            ]
        }

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=mock_resp)

        client = SDAClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        # Request both 402099 (in table with None) and 999999 (not in table)
        results = client.get_productivity_ratings(["402099", "999999"], index_type="nccpi")
        assert len(results) == 2
        r_water = next(r for r in results if r["mukey"] == "402099")
        assert r_water["is_rated"] is False
        assert r_water["numeric_rating"] is None

        r_missing = next(r for r in results if r["mukey"] == "999999")
        assert r_missing["is_rated"] is False
        assert "Map unit not found" in r_missing["caveats"][0]

    def test_get_productivity_ratings_empty_input(self) -> None:
        client = SDAClient()
        assert client.get_productivity_ratings([]) == []

    def test_get_productivity_ratings_invalid_index(self) -> None:
        client = SDAClient()
        with pytest.raises(SDAValidationError, match="Unsupported productivity index type"):
            client.get_productivity_ratings(["402001"], index_type="invalid_index")

    def test_lookup_sdv_attribute_success(self) -> None:
        mock_resp = {
            "Table": [
                [
                    "attributekey",
                    "attributename",
                    "attributetablename",
                    "attributecolumnname",
                    "nasisrulename",
                ],
                [1, "Farmland Classification", "mapunit", "farmlndcl", None],
            ]
        }

        def handler(request: httpx.Request) -> httpx.Response:
            assert b"LIKE '%Farmland%'" in request.content
            return httpx.Response(200, json=mock_resp)

        client = SDAClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        results = client.lookup_sdv_attribute("Farmland")
        assert len(results) == 1
        assert results[0]["attributename"] == "Farmland Classification"

    def test_lookup_sdv_attribute_injection_check(self) -> None:
        client = SDAClient()
        with pytest.raises(
            SDAValidationError, match="Invalid characters in attribute search pattern"
        ):
            client.lookup_sdv_attribute("Farmland; DROP TABLE sdvattribute;--")

    def test_build_dynamic_sdv_query_cointerp(self) -> None:
        from fpac_soil_mcp.sda_client import build_dynamic_sdv_query

        meta = {
            "attributename": "National Commodity Crop Productivity Index",
            "attributetablename": "cointerp",
            "attributecolumnname": "interphr",
            "nasisrulename": "NCCPI - National Commodity Crop Productivity Index (Ver 3.0)",
        }
        query = build_dynamic_sdv_query(meta, "'1001', '1002'")
        assert "cointerp" in query
        assert "NCCPI - National Commodity Crop Productivity Index" in query
        assert "WHERE m.mukey IN ('1001', '1002')" in query

    def test_build_dynamic_sdv_query_nccpi_excludes_negative_sentinels(self) -> None:
        meta = {
            "attributetablename": "cointerp",
            "attributecolumnname": "interphr",
            "nasisrulename": "NCCPI - National Commodity Crop Productivity Index (Ver 3.0)",
        }
        query = build_dynamic_sdv_query(meta, "'1001'")
        assert "rating IS NOT NULL AND rating NOT IN (-999, -99, 99, 999)" in query

    def test_build_dynamic_sdv_query_uses_exact_rule_name(self) -> None:
        meta = {
            "attributetablename": "cointerp",
            "attributecolumnname": "interphr",
            "nasisrulename": "Future Validated Rule",
        }
        query = build_dynamic_sdv_query(meta, "'1001'")
        assert "ci.mrulename = 'Future Validated Rule'" in query
        assert "LIKE '%Future Validated Rule%'" not in query
        assert "NCCPI" not in query

    def test_build_dynamic_sdv_county_max_uses_exact_rule_name(self) -> None:
        meta = {
            "attributetablename": "cointerp",
            "attributecolumnname": "interphr",
            "nasisrulename": "Future Validated Rule",
        }
        query = build_dynamic_sdv_county_max_query(meta, "IA169")
        assert "ci.mrulename = 'Future Validated Rule'" in query
        assert "LIKE '%Future Validated Rule%'" not in query
        assert "NCCPI" not in query

    def test_build_dynamic_sdv_query_component(self) -> None:
        from fpac_soil_mcp.sda_client import build_dynamic_sdv_query

        meta = {
            "attributename": "Corn Yield",
            "attributetablename": "component",
            "attributecolumnname": "cornyld",
        }
        query = build_dynamic_sdv_query(meta, "'1001'")
        assert "c.cornyld" in query
        assert "CAST(c.cornyld AS float) AS rating" in query
        assert (
            "ROUND(SUM(CASE WHEN rating IS NOT NULL AND rating NOT IN (-999, -99, 99, 999) THEN rating * comppct_r ELSE 0 END)"
            in query
        )

    def test_dynamic_sdv_query_chorizon_filters_sentinels_before_weighting(self) -> None:
        query = build_dynamic_sdv_query(
            {
                "attributename": "NCCPI",
                "attributetablename": "chorizon",
                "attributecolumnname": "awc_r",
            },
            "'1001'",
        )
        assert "ch.awc_r IS NOT NULL AND ch.awc_r NOT IN (-999, -99, 99, 999)" in query

    def test_dynamic_sdv_query_cocropyld_filters_sentinels_before_weighting(self) -> None:
        query = build_dynamic_sdv_query(
            {
                "attributename": "CPI",
                "attributetablename": "cocropyld",
                "attributecolumnname": "nonirryield_r",
            },
            "'1001'",
        )
        assert "cy.nonirryield_r IS NOT NULL AND cy.nonirryield_r NOT IN (-999, -99, 999)" in query

    def test_dynamic_sdv_query_preserves_valid_state_index_99(self) -> None:
        query = build_dynamic_sdv_query(
            {
                "attributename": "CSR2",
                "attributetablename": "mapunit",
                "attributecolumnname": "iacornsr",
            },
            "'1001'",
        )
        assert "m.iacornsr IS NOT NULL AND m.iacornsr NOT IN (-999, -99, 999)" in query
        assert "m.iacornsr NOT IN (-999, -99, 99, 999)" not in query

    def test_build_dynamic_sdv_query_mapunit(self) -> None:
        from fpac_soil_mcp.sda_client import build_dynamic_sdv_query

        meta = {
            "attributename": "Map Unit Farmland Class",
            "attributetablename": "mapunit",
            "attributecolumnname": "farmlndcl",
        }
        query = build_dynamic_sdv_query(meta, "'1001'")
        assert "m.farmlndcl" in query

    def test_build_dynamic_sdv_query_invalid_table(self) -> None:
        from fpac_soil_mcp.sda_client import build_dynamic_sdv_query

        meta = {
            "attributetablename": "unauthorized_table",
            "attributecolumnname": "col",
        }
        with pytest.raises(SDAValidationError, match="Unsupported or unallowed SDV table"):
            build_dynamic_sdv_query(meta, "'1001'")

    def test_build_dynamic_sdv_query_chorizon(self) -> None:
        from fpac_soil_mcp.sda_client import build_dynamic_sdv_query

        meta = {
            "attributename": "Available Water Capacity",
            "attributetablename": "chorizon",
            "attributecolumnname": "awc_r",
        }
        query = build_dynamic_sdv_query(meta, "'1001', '1002'")
        assert "chorizon AS ch" in query
        assert "ch.awc_r" in query
        assert "ch.hzdepb_r - ch.hzdept_r" in query  # depth weighting
        assert "WHERE m.mukey IN ('1001', '1002')" in query
        assert "hz_weighted" in query  # CTE name

    def test_build_dynamic_sdv_query_cocropyld(self) -> None:
        from fpac_soil_mcp.sda_client import build_dynamic_sdv_query

        meta = {
            "attributename": "Yields of Non-Irrigated Crops",
            "attributetablename": "cocropyld",
            "attributecolumnname": "nonirryield_r",
            "cropname": "Corn",
        }
        query = build_dynamic_sdv_query(meta, "'1001'")
        assert "cocropyld AS cy" in query
        assert "cy.nonirryield_r" in query
        assert "cy.cropname = 'Corn'" in query
        assert "WHERE m.mukey IN ('1001')" in query

    def test_build_dynamic_sdv_query_cocropyld_no_cropname(self) -> None:
        from fpac_soil_mcp.sda_client import build_dynamic_sdv_query

        meta = {
            "attributetablename": "cocropyld",
            "attributecolumnname": "nonirryield_r",
        }
        query = build_dynamic_sdv_query(meta, "'1001'")
        assert "cocropyld AS cy" in query
        assert "cropname =" not in query  # no crop filter when not specified

    def test_build_dynamic_sdv_county_max_chorizon(self) -> None:
        from fpac_soil_mcp.sda_client import build_dynamic_sdv_county_max_query

        meta = {
            "attributetablename": "chorizon",
            "attributecolumnname": "awc_r",
        }
        query = build_dynamic_sdv_county_max_query(meta, "IA169")
        assert "chorizon AS ch" in query
        assert "ch.awc_r" in query
        assert "l.areasymbol = 'IA169'" in query
        assert "max_county_rating" in query.lower()
        assert "ch.awc_r IS NOT NULL AND ch.awc_r NOT IN (-999, -99, 99, 999)" in query

    def test_build_dynamic_sdv_county_max_cocropyld(self) -> None:
        from fpac_soil_mcp.sda_client import build_dynamic_sdv_county_max_query

        meta = {
            "attributetablename": "cocropyld",
            "attributecolumnname": "nonirryield_r",
            "cropname": "Soybeans",
        }
        query = build_dynamic_sdv_county_max_query(meta, "IA169")
        assert "cocropyld AS cy" in query
        assert "cy.nonirryield_r" in query
        assert "cy.cropname = 'Soybeans'" in query
        assert "l.areasymbol = 'IA169'" in query
        assert (
            "cy.nonirryield_r IS NOT NULL AND cy.nonirryield_r NOT IN (-999, -99, 99, 999)" in query
        )

    def test_get_productivity_ratings_with_attribute_meta(self) -> None:
        mock_resp = {
            "Table": [
                [
                    "mukey",
                    "areasymbol",
                    "musym",
                    "muname",
                    "numeric_rating",
                    "rated_pct",
                    "total_pct",
                ],
                ["1001", "IA169", "138B", "Clarion loam", 91.0, 95.0, 100.0],
            ]
        }

        def handler(request: httpx.Request) -> httpx.Response:
            assert b"c.cornyld" in request.content
            return httpx.Response(200, json=mock_resp)

        meta = {
            "attributename": "Corn Yield",
            "attributetablename": "component",
            "attributecolumnname": "cornyld",
        }
        client = SDAClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        results = client.get_productivity_ratings(["1001"], attribute_meta=meta)
        assert len(results) == 1
        assert results[0]["numeric_rating"] == 91.0
        assert results[0]["is_rated"] is True

    @pytest.mark.parametrize(
        ("meta", "raw_rating", "expected_rating", "expected_rated"),
        [
            (
                {
                    "attributename": "CPI",
                    "attributetablename": "component",
                    "attributecolumnname": "cropprodindex",
                },
                99.0,
                99.0,
                True,
            ),
            (
                {
                    "attributename": "NCCPI",
                    "attributetablename": "component",
                    "attributecolumnname": "nccpi",
                },
                99.0,
                None,
                False,
            ),
            (
                {
                    "attributename": "Corn Yield",
                    "attributetablename": "component",
                    "attributecolumnname": "cornyld",
                },
                -999.0,
                None,
                False,
            ),
        ],
        ids=["cpi-valid-99", "nccpi-sentinel-99", "custom-sentinel-negative"],
    )
    def test_get_productivity_ratings_dynamic_sentinel_classification(
        self,
        meta: dict[str, str],
        raw_rating: float,
        expected_rating: float | None,
        expected_rated: bool,
    ) -> None:
        mock_resp = {
            "Table": [
                ["mukey", "areasymbol", "numeric_rating", "rated_pct", "total_pct"],
                ["100001", "XX001", raw_rating, 100.0, 100.0],
            ]
        }

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=mock_resp)

        client = SDAClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        result = client.get_productivity_ratings(["100001"], attribute_meta=meta)[0]
        assert result["numeric_rating"] == expected_rating
        assert result["is_rated"] is expected_rated

    def test_get_productivity_ratings_csr2(self) -> None:
        """CSR2 uses mapunit.iacornsr — a direct mapunit column, not cointerp."""
        mock_resp = {
            "Table": [
                [
                    "mukey",
                    "areasymbol",
                    "musym",
                    "muname",
                    "numeric_rating",
                    "rated_pct",
                    "total_pct",
                ],
                ["406439", "IA169", "138B", "Clarion loam", 92.0, 100.0, 100.0],
            ]
        }

        def handler(request: httpx.Request) -> httpx.Response:
            assert b"iacornsr" in request.content
            assert b"cointerp" not in request.content
            return httpx.Response(200, json=mock_resp)

        client = SDAClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        results = client.get_productivity_ratings(["406439"], index_type="csr2")
        assert len(results) == 1
        assert results[0]["mukey"] == "406439"
        assert results[0]["numeric_rating"] == 92.0
        assert results[0]["is_rated"] is True
        assert results[0]["index_type"] == "csr2"
        assert results[0]["productivity_rating_source"] == "SDA:MAPUNIT_IACORNSR"

    def test_get_productivity_ratings_csr2_alias(self) -> None:
        """CSR2 accepts the long-form alias."""
        mock_resp = {
            "Table": [
                [
                    "mukey",
                    "areasymbol",
                    "musym",
                    "muname",
                    "numeric_rating",
                    "rated_pct",
                    "total_pct",
                ],
                ["406439", "IA169", "138B", "Clarion loam", 92.0, 100.0, 100.0],
            ]
        }

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=mock_resp)

        client = SDAClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        results = client.get_productivity_ratings(
            ["406439"], index_type="Iowa Corn Suitability Rating CSR2"
        )
        assert len(results) == 1
        assert results[0]["index_type"] == "csr2"

    def test_get_county_max_productivity_rating_csr2(self) -> None:
        """CSR2 county max uses mapunit.iacornsr MAX query."""
        mock_resp = {
            "Table": [
                ["max_county_rating"],
                [96.0],
            ]
        }

        def handler(request: httpx.Request) -> httpx.Response:
            assert b"iacornsr" in request.content
            assert b"areasymbol = 'IA169'" in request.content
            return httpx.Response(200, json=mock_resp)

        client = SDAClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        val = client.get_county_max_productivity_rating("IA169", index_type="csr2")
        # CSR2 is integer scale, rounded to 0 decimals
        assert val == 96.0

    def test_get_county_max_productivity_rating_csr2_null(self) -> None:
        """Non-Iowa counties may have NULL iacornsr everywhere."""
        mock_resp = {"Table": [["max_county_rating"], [None]]}

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=mock_resp)

        client = SDAClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        val = client.get_county_max_productivity_rating("IL019", index_type="csr2")
        assert val is None

    def test_csr2_sql_template_uses_mapunit_table(self) -> None:
        """Verify SQL_PRODUCTIVITY_CSR2 queries mapunit.iacornsr directly."""
        from fpac_soil_mcp.sda_client import SQL_PRODUCTIVITY_CSR2

        sql = SQL_PRODUCTIVITY_CSR2.format(mukeys_csv="'406439'")
        assert "m.iacornsr" in sql
        assert "mapunit AS m" in sql
        assert "legend AS l" in sql
        # Must NOT join cointerp or component
        assert "cointerp" not in sql
        assert "component" not in sql

    def test_get_productivity_ratings_cpi(self) -> None:
        """CPI uses component.cropprodindex — component-weighted average."""
        mock_resp = {
            "Table": [
                [
                    "mukey",
                    "areasymbol",
                    "musym",
                    "muname",
                    "numeric_rating",
                    "rated_pct",
                    "total_pct",
                ],
                ["660750", "MN167", "L32A", "Barnes loam", 85.0, 90.0, 100.0],
            ]
        }

        def handler(request: httpx.Request) -> httpx.Response:
            assert b"cropprodindex" in request.content
            assert b"component AS c" in request.content
            assert b"cointerp" not in request.content
            return httpx.Response(200, json=mock_resp)

        client = SDAClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        results = client.get_productivity_ratings(["660750"], index_type="cpi")
        assert len(results) == 1
        assert results[0]["mukey"] == "660750"
        assert results[0]["numeric_rating"] == 85.0
        assert results[0]["is_rated"] is True
        assert results[0]["index_type"] == "cpi"
        assert results[0]["productivity_rating_source"] == "SDA:COMPONENT_CROPPRODINDEX"

    def test_get_productivity_ratings_cpi_alias(self) -> None:
        """CPI accepts 'crop productivity index' long-form alias."""
        mock_resp = {
            "Table": [
                [
                    "mukey",
                    "areasymbol",
                    "musym",
                    "muname",
                    "numeric_rating",
                    "rated_pct",
                    "total_pct",
                ],
                ["660750", "MN167", "L32A", "Barnes loam", 85.0, 90.0, 100.0],
            ]
        }

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=mock_resp)

        client = SDAClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        results = client.get_productivity_ratings(["660750"], index_type="Crop Productivity Index")
        assert len(results) == 1
        assert results[0]["index_type"] == "cpi"

    def test_get_county_max_productivity_rating_cpi(self) -> None:
        """CPI county max uses component.cropprodindex MAX query."""
        mock_resp = {
            "Table": [
                ["max_county_rating"],
                [100.0],
            ]
        }

        def handler(request: httpx.Request) -> httpx.Response:
            assert b"cropprodindex" in request.content
            assert b"areasymbol = 'MN167'" in request.content
            return httpx.Response(200, json=mock_resp)

        client = SDAClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        val = client.get_county_max_productivity_rating("MN167", index_type="cpi")
        assert val == 100.0

    def test_get_county_max_productivity_rating_cpi_null(self) -> None:
        """Metro MN counties may have NULL cropprodindex everywhere."""
        mock_resp = {"Table": [["max_county_rating"], [None]]}

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=mock_resp)

        client = SDAClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        val = client.get_county_max_productivity_rating("MN053", index_type="cpi")
        assert val is None

    def test_cpi_sql_template_uses_component_table(self) -> None:
        """Verify SQL_PRODUCTIVITY_CPI queries component.cropprodindex."""
        from fpac_soil_mcp.sda_client import SQL_PRODUCTIVITY_CPI

        sql = SQL_PRODUCTIVITY_CPI.format(mukeys_csv="'660750'")
        assert "c.cropprodindex" in sql
        assert "component AS c" in sql
        assert "comppct_r" in sql
        # Must NOT use cointerp or mapunit.iacornsr
        assert "cointerp" not in sql
        assert "iacornsr" not in sql

    def test_get_productivity_ratings_storie(self) -> None:
        """Storie reuses NCCPI cointerp SQL with a different rule name."""
        mock_resp = {
            "Table": [
                [
                    "mukey",
                    "areasymbol",
                    "musym",
                    "muname",
                    "numeric_rating",
                    "rated_pct",
                    "total_pct",
                ],
                ["461792", "CA077", "154", "San Joaquin sandy loam", 0.82, 95.0, 100.0],
            ]
        }

        def handler(request: httpx.Request) -> httpx.Response:
            assert b"cointerp" in request.content
            assert b"AGR - California Revised Storie Index (CA)" in request.content
            return httpx.Response(200, json=mock_resp)

        client = SDAClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        results = client.get_productivity_ratings(["461792"], index_type="storie")
        assert len(results) == 1
        assert results[0]["mukey"] == "461792"
        assert results[0]["numeric_rating"] == 0.82
        assert results[0]["is_rated"] is True
        assert results[0]["index_type"] == "storie"
        assert results[0]["productivity_rating_source"] == "SDA:COINTERP_STORIE_CA"

    def test_get_productivity_ratings_storie_alias(self) -> None:
        """Storie accepts long-form alias."""
        mock_resp = {
            "Table": [
                [
                    "mukey",
                    "areasymbol",
                    "musym",
                    "muname",
                    "numeric_rating",
                    "rated_pct",
                    "total_pct",
                ],
                ["461792", "CA077", "154", "San Joaquin sandy loam", 0.82, 95.0, 100.0],
            ]
        }

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=mock_resp)

        client = SDAClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        results = client.get_productivity_ratings(
            ["461792"], index_type="California Revised Storie Index"
        )
        assert len(results) == 1
        assert results[0]["index_type"] == "storie"

    def test_get_county_max_productivity_rating_storie(self) -> None:
        """Storie county max reuses NCCPI cointerp MAX template."""
        mock_resp = {
            "Table": [
                ["max_county_rating"],
                [0.995],
            ]
        }

        def handler(request: httpx.Request) -> httpx.Response:
            assert b"AGR - California Revised Storie Index (CA)" in request.content
            assert b"areasymbol = 'CA077'" in request.content
            return httpx.Response(200, json=mock_resp)

        client = SDAClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        val = client.get_county_max_productivity_rating("CA077", index_type="storie")
        assert val == 0.995

    def test_get_county_max_productivity_rating_storie_null(self) -> None:
        """Non-CA counties should have no Storie data."""
        mock_resp = {"Table": [["max_county_rating"]]}

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=mock_resp)

        client = SDAClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        val = client.get_county_max_productivity_rating("IA169", index_type="storie")
        assert val is None

    def test_storie_uses_nccpi_cointerp_template(self) -> None:
        """Verify Storie routing reuses SQL_PRODUCTIVITY_NCCPI with Storie rule name."""
        from fpac_soil_mcp.sda_client import SQL_PRODUCTIVITY_NCCPI

        sql = SQL_PRODUCTIVITY_NCCPI.format(
            mukeys_csv="'461792'",
            rule_name="AGR - California Revised Storie Index (CA)",
        )
        assert "cointerp" in sql
        assert "AGR - California Revised Storie Index (CA)" in sql
        assert "461792" in sql

    @pytest.mark.parametrize(
        "index_type,raw_value,expected",
        [
            ("nccpi", 0.82567, 0.826),
            ("csr2", 92.456, 92.0),
            ("cpi", 87.654, 88.0),
            ("storie", 0.95678, 0.957),
        ],
        ids=["nccpi", "csr2", "cpi", "storie"],
    )
    def test_get_productivity_ratings_rounding_precision(
        self, index_type: str, raw_value: float, expected: float
    ) -> None:
        """Each index type rounds to its appropriate precision."""
        cols = [
            "mukey",
            "areasymbol",
            "musym",
            "muname",
            "numeric_rating",
            "rated_pct",
            "total_pct",
        ]
        mock_resp = {
            "Table": [cols, ["100001", "XX001", "1A", "Test Soil", raw_value, 100.0, 100.0]]
        }

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=mock_resp)

        client = SDAClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        results = client.get_productivity_ratings(["100001"], index_type=index_type)
        assert len(results) == 1
        assert results[0]["numeric_rating"] == expected
        assert results[0]["is_rated"] is True

    @pytest.mark.parametrize(
        "index_type,raw_value,expected",
        [
            ("nccpi", 0.99567, 0.996),
            ("csr2", 96.456, 96.0),
            ("cpi", 100.789, 101.0),
            ("storie", 0.99512, 0.995),
        ],
        ids=["nccpi", "csr2", "cpi", "storie"],
    )
    def test_get_county_max_rounding_precision(
        self, index_type: str, raw_value: float, expected: float
    ) -> None:
        """County max rounding respects each index type's precision."""
        mock_resp = {"Table": [["max_county_rating"], [raw_value]]}

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=mock_resp)

        client = SDAClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        val = client.get_county_max_productivity_rating("XX001", index_type=index_type)
        assert val == expected

    def test_get_productivity_ratings_zero_rating_is_unrated(self) -> None:
        """A raw rating of 0.0 should yield is_rated=False (B4 sentinel fix)."""
        cols = [
            "mukey",
            "areasymbol",
            "musym",
            "muname",
            "numeric_rating",
            "rated_pct",
            "total_pct",
        ]
        mock_resp = {"Table": [cols, ["100001", "XX001", "1A", "Test Soil", 0.0, 100.0, 100.0]]}

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=mock_resp)

        client = SDAClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        results = client.get_productivity_ratings(["100001"], index_type="nccpi")
        assert len(results) == 1
        assert results[0]["is_rated"] is False
        assert results[0]["numeric_rating"] is None

    @pytest.mark.parametrize("index_type", ["csr2", "cpi"])
    def test_get_productivity_ratings_accepts_valid_99_for_state_indexes(
        self, index_type: str
    ) -> None:
        mock_resp = {
            "Table": [
                ["mukey", "areasymbol", "numeric_rating", "rated_pct", "total_pct"],
                ["100001", "XX001", 99.0, 100.0, 100.0],
            ]
        }

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=mock_resp)

        client = SDAClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        result = client.get_productivity_ratings(["100001"], index_type=index_type)[0]
        assert result["numeric_rating"] == 99.0
        assert result["is_rated"] is True
