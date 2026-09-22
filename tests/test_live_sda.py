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
