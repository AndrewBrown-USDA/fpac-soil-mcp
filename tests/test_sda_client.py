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
        assert "cocropyld" not in ALLOWED_SDV_TABLES
        assert "corestrictions" not in ALLOWED_SDV_TABLES


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

    def test_get_county_max_productivity_rating_csr2(self) -> None:
        mock_resp = {
            "Table": [
                ["max_county_rating"],
                [100.0],
            ]
        }

        def handler(request: httpx.Request) -> httpx.Response:
            assert b"CSR2" in request.content or b"cointerp" in request.content
            assert b"areasymbol = 'IA169'" in request.content
            return httpx.Response(200, json=mock_resp)

        client = SDAClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        val = client.get_county_max_productivity_rating("IA169", index_type="csr2")
        assert val == 100.0

    def test_get_county_max_productivity_rating_cpi(self) -> None:
        mock_resp = {
            "Table": [
                ["max_county_rating"],
                [99.0],
            ]
        }

        def handler(request: httpx.Request) -> httpx.Response:
            assert b"areasymbol = 'MN103'" in request.content
            return httpx.Response(200, json=mock_resp)

        client = SDAClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        # Note: CPI uses 99.0 as valid rating if <= 100, but in get_county_max_productivity_rating:
        # if val_float in (99.0, 999.0): returns None since 99 is often a sentinel in county max queries.
        # Let's test standard 100.0 or 98.0
        val = client.get_county_max_productivity_rating("MN103", index_type="cpi")
        assert val is None  # 99.0 is filtered as sentinel

    def test_get_county_max_productivity_rating_storie(self) -> None:
        mock_resp = {
            "Table": [
                ["max_county_rating"],
                [100.0],
            ]
        }

        def handler(request: httpx.Request) -> httpx.Response:
            assert b"areasymbol = 'CA019'" in request.content
            return httpx.Response(200, json=mock_resp)

        client = SDAClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        val = client.get_county_max_productivity_rating("CA019", index_type="storie")
        assert val == 100.0

    def test_get_county_max_productivity_rating_sentinels_and_nulls(self) -> None:
        mock_empty_resp = {"Table": []}
        mock_sentinel_resp = {"Table": [["max_county_rating"], [999.0]]}
        mock_zero_resp = {"Table": [["max_county_rating"], [0.0]]}

        client_empty = SDAClient(
            http_client=httpx.Client(
                transport=httpx.MockTransport(lambda r: httpx.Response(200, json=mock_empty_resp))
            )
        )
        assert client_empty.get_county_max_productivity_rating("IA169", "csr2") is None

        client_sentinel = SDAClient(
            http_client=httpx.Client(
                transport=httpx.MockTransport(
                    lambda r: httpx.Response(200, json=mock_sentinel_resp)
                )
            )
        )
        assert client_sentinel.get_county_max_productivity_rating("IA169", "csr2") is None

        client_zero = SDAClient(
            http_client=httpx.Client(
                transport=httpx.MockTransport(lambda r: httpx.Response(200, json=mock_zero_resp))
            )
        )
        assert client_zero.get_county_max_productivity_rating("IA169", "csr2") is None

    def test_get_county_max_productivity_rating_validation_errors(self) -> None:
        client = SDAClient()
        with pytest.raises(SDAValidationError, match="Invalid soil survey area symbol"):
            client.get_county_max_productivity_rating("INVALID-AREA!", "csr2")

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

    def test_get_productivity_ratings_csr2(self) -> None:
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
                    "comp_count",
                ],
                ["406439", "IA169", "138B", "Clarion loam", 89.0, 95, 100, 2],
            ]
        }

        def handler(request: httpx.Request) -> httpx.Response:
            assert b"CSR2" in request.content or b"cointerp" in request.content
            return httpx.Response(200, json=mock_resp)

        client = SDAClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        results = client.get_productivity_ratings(["406439"], index_type="csr2")
        assert len(results) == 1
        assert results[0]["mukey"] == "406439"
        assert results[0]["numeric_rating"] == 89.0
        assert results[0]["is_rated"] is True

    def test_get_productivity_ratings_cpi(self) -> None:
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
                    "comp_count",
                ],
                ["415201", "MN103", "L83A", "Webster clay loam", 93.0, 100, 100, 1],
            ]
        }

        def handler(request: httpx.Request) -> httpx.Response:
            assert b"CPI" in request.content or b"cointerp" in request.content
            return httpx.Response(200, json=mock_resp)

        client = SDAClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        results = client.get_productivity_ratings(["415201"], index_type="cpi")
        assert len(results) == 1
        assert results[0]["mukey"] == "415201"
        assert results[0]["numeric_rating"] == 93.0

    def test_get_productivity_ratings_storie(self) -> None:
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
                    "comp_count",
                ],
                ["462001", "CA019", "HdA", "Hanford sandy loam", 95.0, 100, 100, 1],
            ]
        }

        def handler(request: httpx.Request) -> httpx.Response:
            assert b"Storie" in request.content or b"storie" in request.content
            return httpx.Response(200, json=mock_resp)

        client = SDAClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        results = client.get_productivity_ratings(["462001"], index_type="storie")
        assert len(results) == 1
        assert results[0]["mukey"] == "462001"
        assert results[0]["numeric_rating"] == 95.0

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
        assert "rating NOT IN (99, 999, -99, -999)" in query

    def test_build_dynamic_sdv_query_cpi_does_not_match_nccpi(self) -> None:
        meta = {
            "attributetablename": "cointerp",
            "attributecolumnname": "interphr",
            "nasisrulename": "CPI - Crop Productivity Index",
        }
        query = build_dynamic_sdv_query(meta, "'1001'")
        assert "ci.mrulename = 'CPI - Crop Productivity Index'" in query
        assert "LIKE '%CPI%'" not in query
        assert "NCCPI" not in query

    def test_build_dynamic_sdv_county_max_cpi_does_not_match_nccpi(self) -> None:
        meta = {
            "attributetablename": "cointerp",
            "attributecolumnname": "interphr",
            "nasisrulename": "CPI - Crop Productivity Index",
        }
        query = build_dynamic_sdv_county_max_query(meta, "IA169")
        assert "ci.mrulename = 'CPI - Crop Productivity Index'" in query
        assert "LIKE '%CPI%'" not in query
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
            "ROUND(SUM(CASE WHEN rating IS NOT NULL AND rating NOT IN (99, 999) THEN rating * comppct_r ELSE 0 END)"
            in query
        )

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
