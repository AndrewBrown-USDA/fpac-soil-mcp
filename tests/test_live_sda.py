"""Live integration tests for USDA NRCS Soil Data Access (SDA) API.

Tests real network queries against SDA Tabular REST endpoint.
Opt-in via: pytest -m live_network
"""

from __future__ import annotations

import httpx
import pytest

from fpac_soil_mcp.sda_client import SDAClient, SDAClientError, SDAValidationError

pytestmark = pytest.mark.live_network


class TestLiveSDA:
    """Live integration tests hitting live SDA web services."""

    def test_live_point_lookup_prime_farmland(self) -> None:
        """Query known prime farmland coordinate in Story County, IA (Clarion / Webster soils)."""
        client = SDAClient()
        try:
            results = client.get_by_point(latitude=42.0308, longitude=-93.6319)
        except (SDAClientError, httpx.HTTPError) as exc:
            pytest.skip(f"Live SDA endpoint unavailable or timed out: {exc}")

        assert len(results) >= 1
        res = results[0]
        assert "mukey" in res
        assert "musym" in res
        assert "muname" in res
        assert "farmlndcl" in res
        assert res.get("areasymbol") == "IA169"

    def test_live_spatial_intersection_clipping(self) -> None:
        """Query real 100m square polygon in Iowa and test STIntersection clipped acreage."""
        client = SDAClient()
        wkt_polygon = "POLYGON((-93.632 42.030, -93.630 42.030, -93.630 42.032, -93.632 42.032, -93.632 42.030))"
        try:
            results = client.get_spatial_intersection(
                wkt_polygon, clip=True, geom_acres=True, return_geom=False
            )
        except (SDAClientError, httpx.HTTPError) as exc:
            pytest.skip(f"Live SDA endpoint unavailable or timed out: {exc}")

        assert len(results) >= 1
        for row in results:
            assert "mukey" in row
            assert "musym" in row
            assert "muname" in row
            assert "area_ac" in row
            assert float(row["area_ac"]) > 0.0

    def test_live_interpretation_nccpi_v3(self) -> None:
        """Query live NCCPI v3 interpretation for known map unit."""
        client = SDAClient()
        try:
            # First lookup real mukey from point
            pt_res = client.get_by_point(latitude=42.0308, longitude=-93.6319)
            if not pt_res or not pt_res[0].get("mukey"):
                pytest.skip("Could not fetch test mukey from point")
            test_mukey = str(pt_res[0]["mukey"])

            results = client.get_interpretations(
                mukeys=[test_mukey],
                rule_name="NCCPI - National Commodity Crop Productivity Index (Ver 3.0)",
                aggregation_method="Weighted Average",
            )
        except (SDAClientError, httpx.HTTPError) as exc:
            pytest.skip(f"Live SDA endpoint unavailable or timed out: {exc}")

        assert len(results) >= 1
        res = results[0]
        assert "mukey" in res
        assert res.get("mukey") == test_mukey
        assert res.get("numeric_rating") is not None

    def test_live_cointerp_rule_catalog(self) -> None:
        """Query live cointerp rule catalog from sdvattribute metadata table."""
        client = SDAClient()
        try:
            rules = client.get_available_interpretation_rules(refresh=True)
        except (SDAClientError, httpx.HTTPError) as exc:
            pytest.skip(f"Live SDA endpoint unavailable or timed out: {exc}")

        assert "NCCPI - National Commodity Crop Productivity Index (Ver 3.0)" in rules

    def test_fixed_selector_rejects_unsupported_value(self) -> None:
        """The public fixed selector rejects unsupported values."""
        client = SDAClient()
        with pytest.raises(SDAValidationError, match="Unsupported productivity index type"):
            client.get_productivity_ratings(mukeys=["402001"], index_type="unsupported")

    def test_live_geometry_extraction(self) -> None:
        """Query live geometry extraction returning WKT polygon shapes."""
        client = SDAClient()
        wkt_polygon = "POLYGON((-93.632 42.030, -93.630 42.030, -93.630 42.032, -93.632 42.032, -93.632 42.030))"
        try:
            results = client.get_spatial_intersection(
                wkt_polygon, clip=True, geom_acres=True, return_geom=True
            )
        except (SDAClientError, httpx.HTTPError) as exc:
            pytest.skip(f"Live SDA endpoint unavailable or timed out: {exc}")

        assert len(results) >= 1
        for row in results:
            assert "geom" in row
            assert row["geom"].startswith(("POLYGON", "MULTIPOLYGON"))

    def test_live_dynamic_sdv_queries_and_unrated_water_urban(self) -> None:
        """Verify dynamic SDV query generation on live SDA with real attribute metadata."""
        client = SDAClient()
        # Query water/urban area (e.g. Lake Michigan coordinates near Chicago: 41.90, -87.60)
        water_pts = client.get_by_point(latitude=41.9000, longitude=-87.6000)
        if water_pts and water_pts[0].get("mukey"):
            water_mukey = str(water_pts[0]["mukey"])
            nccpi_res = client.get_interpretations(
                mukeys=[water_mukey],
                rule_name="NCCPI - National Commodity Crop Productivity Index (Ver 3.0)",
            )
            if nccpi_res:
                # In water/urban land, numeric rating is None or sentinel (99/999)
                assert nccpi_res[0].get("numeric_rating") is None or nccpi_res[0].get(
                    "numeric_rating"
                ) in (99, 999, 99.0, 999.0)

        # Query dynamic SDV county maximum for NCCPI in Iowa
        max_val = client.get_county_max_productivity_rating(areasymbol="IA169", index_type="nccpi")
        assert max_val is not None
        assert max_val > 0.0

    def test_live_csr2_productivity_ratings_iowa(self) -> None:
        """Query CSR2 (mapunit.iacornsr) for known Iowa mukeys — Story County, IA."""
        client = SDAClient()
        try:
            pt_res = client.get_by_point(latitude=42.0308, longitude=-93.6319)
            if not pt_res or not pt_res[0].get("mukey"):
                pytest.skip("Could not fetch test mukey from point")
            test_mukey = str(pt_res[0]["mukey"])

            results = client.get_productivity_ratings(mukeys=[test_mukey], index_type="csr2")
        except (SDAClientError, httpx.HTTPError) as exc:
            pytest.skip(f"Live SDA endpoint unavailable or timed out: {exc}")

        assert len(results) == 1
        res = results[0]
        assert res["index_type"] == "csr2"
        assert res["productivity_rating_source"] == "SDA:MAPUNIT_IACORNSR"
        # Iowa soils should have CSR2 values in range 5-100
        if res["is_rated"]:
            assert 5 <= res["numeric_rating"] <= 100

    def test_live_csr2_county_max_iowa(self) -> None:
        """CSR2 county max for IA169 (Story County) — research found max=96."""
        client = SDAClient()
        try:
            max_val = client.get_county_max_productivity_rating(
                areasymbol="IA169", index_type="csr2"
            )
        except (SDAClientError, httpx.HTTPError) as exc:
            pytest.skip(f"Live SDA endpoint unavailable or timed out: {exc}")

        assert max_val is not None
        assert 90 <= max_val <= 100  # known IA169 max is 96

    def test_live_csr2_county_max_non_iowa_is_null(self) -> None:
        """CSR2 should return None for non-Iowa counties (iacornsr is Iowa-only)."""
        client = SDAClient()
        try:
            max_val = client.get_county_max_productivity_rating(
                areasymbol="IL019", index_type="csr2"
            )
        except (SDAClientError, httpx.HTTPError) as exc:
            pytest.skip(f"Live SDA endpoint unavailable or timed out: {exc}")

        assert max_val is None

    def test_live_cpi_county_max_minnesota(self) -> None:
        """CPI county max for MN167 (Wilkin County) — research found max=100."""
        client = SDAClient()
        try:
            max_val = client.get_county_max_productivity_rating(
                areasymbol="MN167", index_type="cpi"
            )
        except (SDAClientError, httpx.HTTPError) as exc:
            pytest.skip(f"Live SDA endpoint unavailable or timed out: {exc}")

        assert max_val is not None
        # Research found MN167 max=100
        assert 90 <= max_val <= 100

    def test_live_cpi_productivity_ratings_minnesota(self) -> None:
        """Query CPI (component.cropprodindex) for a real Wilkin County mukey."""
        client = SDAClient()
        try:
            pt_res = client.get_by_point(latitude=46.28, longitude=-96.58)
            if not pt_res or not pt_res[0].get("mukey"):
                pytest.skip("Could not fetch test mukey from point")
            test_mukey = str(pt_res[0]["mukey"])

            results = client.get_productivity_ratings(
                mukeys=[test_mukey], index_type="cpi"
            )
        except (SDAClientError, httpx.HTTPError) as exc:
            pytest.skip(f"Live SDA endpoint unavailable or timed out: {exc}")

        assert len(results) == 1
        res = results[0]
        assert res["index_type"] == "cpi"
        assert res["productivity_rating_source"] == "SDA:COMPONENT_CROPPRODINDEX"
        if res["is_rated"]:
            assert 0 < res["numeric_rating"] <= 100

    def test_live_cpi_county_max_non_populated_county(self) -> None:
        """CPI may be NULL in metro MN counties (e.g. Hennepin MN053)."""
        client = SDAClient()
        try:
            max_val = client.get_county_max_productivity_rating(
                areasymbol="MN053", index_type="cpi"
            )
        except (SDAClientError, httpx.HTTPError) as exc:
            pytest.skip(f"Live SDA endpoint unavailable or timed out: {exc}")

        # MN053 (Hennepin) may have no CPI data
        # If it returns something, it should be in valid range
        if max_val is not None:
            assert 0 < max_val <= 100

    def test_live_cpi_county_max_non_mn_is_null(self) -> None:
        """CPI should return None for non-MN/ND/SD counties."""
        client = SDAClient()
        try:
            max_val = client.get_county_max_productivity_rating(
                areasymbol="CA077", index_type="cpi"
            )
        except (SDAClientError, httpx.HTTPError) as exc:
            pytest.skip(f"Live SDA endpoint unavailable or timed out: {exc}")

        assert max_val is None

    def test_live_storie_county_max_california(self) -> None:
        """Storie county max for CA077 (San Joaquin) — research found max ~0.995."""
        client = SDAClient()
        try:
            max_val = client.get_county_max_productivity_rating(
                areasymbol="CA077", index_type="storie"
            )
        except (SDAClientError, httpx.HTTPError) as exc:
            pytest.skip(f"Live SDA endpoint unavailable or timed out: {exc}")

        assert max_val is not None
        assert 0.9 <= max_val <= 1.0  # known CA077 max ~0.995

    def test_live_storie_county_max_non_ca_is_null(self) -> None:
        """Storie should return None for non-California counties."""
        client = SDAClient()
        try:
            max_val = client.get_county_max_productivity_rating(
                areasymbol="IA169", index_type="storie"
            )
        except (SDAClientError, httpx.HTTPError) as exc:
            pytest.skip(f"Live SDA endpoint unavailable or timed out: {exc}")

        assert max_val is None

    def test_live_storie_ratings_california(self) -> None:
        """Query Storie ratings for a known CA077 mukey."""
        client = SDAClient()
        try:
            # Use a known San Joaquin County point to get a CA mukey
            pt_res = client.get_by_point(latitude=37.95, longitude=-121.29)
            if not pt_res or not pt_res[0].get("mukey"):
                pytest.skip("Could not fetch test mukey from CA point")
            test_mukey = str(pt_res[0]["mukey"])

            results = client.get_productivity_ratings(mukeys=[test_mukey], index_type="storie")
        except (SDAClientError, httpx.HTTPError) as exc:
            pytest.skip(f"Live SDA endpoint unavailable or timed out: {exc}")

        assert len(results) == 1
        res = results[0]
        assert res["index_type"] == "storie"
        assert res["productivity_rating_source"] == "SDA:COINTERP_STORIE_CA"
        if res["is_rated"]:
            assert 0 < res["numeric_rating"] <= 1.0
