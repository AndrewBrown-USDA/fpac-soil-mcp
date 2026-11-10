from fpac_soil_mcp.constants import (
    LESA_ACTION_AVOID_MINIMIZE_CONVERSION,
    LESA_ACTION_REDUCE_FOOTPRINT,
    REGULATORY_NOTICE,
    SITE_CRITERIA_NAMES,
    STATUTORY_DETERMINATIONS,
)
from fpac_soil_mcp.fppa import get_fppa_scope_explanation


def test_site_assessment_uses_registry_wording_and_part_vi() -> None:
    assert SITE_CRITERIA_NAMES[6] == "Distance to municipal water/sewer"
    assert (
        SITE_CRITERIA_NAMES[12] == "Compatibility of site project with existing agricultural uses"
    )
    scope = get_fppa_scope_explanation()
    required = scope["lesa_determination_scope"]["what_is_required_for_official_fppa"]
    assert any(item.startswith("Part V: Land Evaluation") for item in required)
    assert any(item.startswith("Part VI: Site Assessment") for item in required)
    assert "Part VI" in REGULATORY_NOTICE


def test_threshold_language_is_authoritative_without_siting_recommendation() -> None:
    exceeded = STATUTORY_DETERMINATIONS["THRESHOLD_EXCEEDED"].format(total_lesa=180)
    below = STATUTORY_DETERMINATIONS["THRESHOLD_NOT_EXCEEDED"].format(total_lesa=120)
    for text in (
        exceeded,
        below,
        LESA_ACTION_AVOID_MINIMIZE_CONVERSION,
        LESA_ACTION_REDUCE_FOOTPRINT,
    ):
        assert "preliminary" in text.lower() or "screening" in text.lower()
        assert "recommend" in text.lower() or "does not prescribe" in text.lower()
    assert "in-depth consideration" in exceeded
    assert "does not trigger" in below
