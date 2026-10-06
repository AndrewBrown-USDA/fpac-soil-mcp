"""Contract tests for generic productivity-rating models."""

from fpac_soil_mcp.models import SoilMapUnitAcreage


def test_soil_map_unit_uses_generic_rating_fields_and_sda_provenance():
    unit = SoilMapUnitAcreage(
        mukey="1",
        productivity_rating=0.88,
        productivity_rating_class="High",
        productivity_rating_source="NCCPI - National Commodity Crop Productivity Index (Ver 3.0)",
    )
    dumped = unit.model_dump()
    assert dumped["productivity_rating"] == 0.88
    assert dumped["productivity_rating_class"] == "High"
    assert dumped["productivity_rating_source"].startswith("NCCPI")
    assert "nccpi_rating" not in dumped
    assert "nccpi_class" not in dumped
    assert not hasattr(unit, "nccpi_rating")
    assert not hasattr(unit, "nccpi_class")
