"""Urban-area exemption screening tool."""

from __future__ import annotations

from fpac_soil_mcp.clients.tigerweb import TigerwebClient
from fpac_soil_mcp.models.integration import UrbanExemptionRecord


def check_urban_area_exemption(
    geojson: dict | str,
) -> UrbanExemptionRecord:
    """Screen a project footprint against Census Bureau 2020 Urban Area boundaries (Layer 0).

    Provides automated spatial screening under 7 CFR § 658.2(a) without issuing a binding legal determination.

    Args:
        geojson: GeoJSON geometry dict or string (Polygon, MultiPolygon, or Point).

    Returns:
        UrbanExemptionRecord with screening outcome and intersected urban areas.
    """
    client = TigerwebClient()
    return client.check_urban_exemption(geojson)
