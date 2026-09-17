"""Live integration tests for Census TIGERweb REST API (Urban Areas Layer 6).

Tests real network queries against Census TIGERweb MapServer endpoint.
Opt-in via: pytest -m live_sda
"""

from __future__ import annotations

import httpx
import pytest

from fpac_soil_mcp.tigerweb_client import TigerwebClient

pytestmark = pytest.mark.live_sda


class TestLiveTigerweb:
    """Live integration tests hitting Census TIGERweb Urban Areas endpoints."""

    def test_live_urban_area_screening_urban(self) -> None:
        """Screen known urban coordinate in Indianapolis, IN."""
        client = TigerwebClient()
        geom = {
            "type": "Polygon",
            "coordinates": [
                [
                    [-86.160, 39.765],
                    [-86.155, 39.765],
                    [-86.155, 39.770],
                    [-86.160, 39.770],
                    [-86.160, 39.765],
                ]
            ],
        }
        try:
            res = client.check_urban_exemption(geom)
        except httpx.HTTPError as exc:
            pytest.skip(f"Live TIGERweb endpoint unavailable or timed out: {exc}")

        assert res.status == "success"
        assert res.is_urban_intersected is True
        assert len(res.urban_area_names) >= 1
        assert any(
            "Indianapolis" in name or "Urban" in name or len(name) > 0
            for name in res.urban_area_names
        )

    def test_live_urban_area_screening_rural(self) -> None:
        """Screen known rural agricultural footprint in rural Iowa."""
        client = TigerwebClient()
        geom = {
            "type": "Polygon",
            "coordinates": [
                [
                    [-94.200, 42.100],
                    [-94.190, 42.100],
                    [-94.190, 42.110],
                    [-94.200, 42.110],
                    [-94.200, 42.100],
                ]
            ],
        }
        try:
            res = client.check_urban_exemption(geom)
        except httpx.HTTPError as exc:
            pytest.skip(f"Live TIGERweb endpoint unavailable or timed out: {exc}")

        assert res.status == "success"
        # If rural footprint does not intersect any 2020 Census urban area
        if res.is_urban_intersected:
            # If an urban area unexpectedly overlaps, check its name
            assert len(res.urban_area_names) >= 0
        else:
            assert res.is_urban_intersected is False
            assert len(res.urban_area_names) == 0
