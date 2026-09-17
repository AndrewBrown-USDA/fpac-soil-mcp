"""Unit tests for SDAClient validation, response parsing, retries, and errors."""

from __future__ import annotations

import httpx
import pytest

from fpac_soil_mcp.sda_client import (
    SQL_MUKEY_LOOKUP,
    SQL_POINT_LOOKUP,
    SDAClient,
    SDAQueryError,
    SDAValidationError,
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
