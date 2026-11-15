"""Live integration tests for Census TIGERweb REST API (Urban Areas Layer 0).

Tests real network queries against Census TIGERweb MapServer endpoint.
Opt-in via: pytest -m live_network
"""

from __future__ import annotations

import httpx
import pytest

from fpac_soil_mcp.clients.tigerweb import TigerwebClient
from fpac_soil_mcp.models.integration import IntegrationStatus

pytestmark = pytest.mark.live_network


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

        if res.status in (
            IntegrationStatus.ERROR,
            IntegrationStatus.UNAVAILABLE,
            "error",
            "unavailable",
        ):
            pytest.skip(f"Live TIGERweb returned error: {res.error_message}")

        assert res.status == IntegrationStatus.SUCCESS
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

        if res.status in (
            IntegrationStatus.ERROR,
            IntegrationStatus.UNAVAILABLE,
            "error",
            "unavailable",
        ):
            pytest.skip(f"Live TIGERweb returned error: {res.error_message}")

        assert res.status == IntegrationStatus.SUCCESS
        assert res.is_urban_intersected is False
        assert len(res.urban_area_names) == 0

    def test_live_perimeter_evidence_rural(self) -> None:
        """Measure Criterion 2 perimeter evidence for a known rural footprint."""
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
            res = client.get_perimeter_evidence(geom)
        except httpx.HTTPError as exc:
            pytest.skip(f"Live TIGERweb endpoint unavailable or timed out: {exc}")

        if res["evidence_status"] in {"error", "unavailable"}:
            pytest.skip(f"Live TIGERweb returned error: {res['error_message']}")

        assert res["evidence_status"] == "measured"
        assert 0.0 <= res["normalized_ratio"] <= 1.0
        assert res["is_verified"] is True
        assert res["source_provenance"]
        assert res["geometry_hash"].startswith("sha256:")
