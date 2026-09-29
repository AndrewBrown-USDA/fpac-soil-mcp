"""Live integration tests for USDA NRCS Soil Data Access (SDA) API.

Tests real network queries against SDA Tabular REST endpoint.
Opt-in via: pytest -m live_network
"""

from __future__ import annotations

import httpx
import pytest

from fpac_soil_mcp.sda_client import SDAClient, SDAClientError

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

        assert len(rules) > 50
        assert "NCCPI - National Commodity Crop Productivity Index (Ver 3.0)" in rules
        assert any("Corn" in r for r in rules)

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

    def test_live_out_of_state_productivity_indices(self) -> None:
        """Verify state-specific indices return null/unrated when queried on out-of-state mukeys."""
        client = SDAClient()
        # 1. Fetch an Iowa mukey (Story County)
        ia_pts = client.get_by_point(latitude=42.0308, longitude=-93.6319)
        if not ia_pts or not ia_pts[0].get("mukey"):
            pytest.skip("Could not fetch Iowa mukey")
        ia_mukey = str(ia_pts[0]["mukey"])

        # 2. Fetch a California mukey (Fresno County)
        ca_pts = client.get_by_point(latitude=36.7468, longitude=-119.7726)
        if not ca_pts or not ca_pts[0].get("mukey"):
            pytest.skip("Could not fetch California mukey")
        ca_mukey = str(ca_pts[0]["mukey"])

        # Test 1: Query California Storie on Iowa mukey -> should return None/unrated rating
        ia_storie_res = client.get_productivity_ratings(mukeys=[ia_mukey], index_type="storie")
        assert len(ia_storie_res) >= 1
        assert ia_storie_res[0].get("numeric_rating") is None
        assert ia_storie_res[0].get("is_rated") is False

        # Test 2: Query California Storie on in-state California mukey -> should return valid rating or None cleanly
        ca_storie_res = client.get_productivity_ratings(mukeys=[ca_mukey], index_type="storie")
        assert len(ca_storie_res) >= 1
        assert "numeric_rating" in ca_storie_res[0]

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
