"""Contract tests for the versioned Site Assessment registry."""

from __future__ import annotations

import importlib.resources
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from fpac_soil_mcp.site_assessment import (
    SITE_ASSESSMENT_REGISTRY,
    SiteAssessmentCriterionDefinition,
    SiteAssessmentRegistry,
    load_site_assessment_registry,
)


def test_registry_loads_deterministically_and_covers_all_criteria() -> None:
    first = load_site_assessment_registry()
    second = load_site_assessment_registry()
    assert first == second == SITE_ASSESSMENT_REGISTRY
    assert [criterion.criterion_number for criterion in first.criteria] == list(range(1, 13))


def _cfr_cases() -> dict[str, object]:
    return json.loads(
        (Path(__file__).parent / "fixtures" / "site_assessment_cfr_cases.json").read_text(
            encoding="utf-8"
        )
    )


def test_fixture_anchors_every_criterion_and_expected_score_to_cfr() -> None:
    fixture = _cfr_cases()
    cases = fixture["cases"]
    assert len(cases) == 12
    for case in cases:
        number = case["criterion_number"]
        criterion = SITE_ASSESSMENT_REGISTRY.criterion(number)
        assert case["citation"] == criterion.citation == f"7 CFR § 658.5(b)({number})"
        assert case["score_direction"] == criterion.score_direction
        assert criterion.max_points >= 0
        for example in case["cases"]:
            band = criterion.band_for(example["value"])
            assert band is not None
            assert band.band_id == example["band"]
            provenance = "analyst observation record" if number == 2 else None
            assert (
                criterion.score_for_value(example["value"], provenance=provenance)
                == example["points"]
            )


def test_numeric_out_of_band_is_distinct_from_unknown() -> None:
    criterion = SITE_ASSESSMENT_REGISTRY.criterion(1)
    assert criterion.band_for(None).band_id == "unknown"
    assert criterion.score_for_value(None) is None
    assert criterion.band_for(101) is None
    assert criterion.score_for_value(101) is None


def test_unknown_and_deferred_inputs_remain_unavailable() -> None:
    criterion = SITE_ASSESSMENT_REGISTRY.criterion(2)
    assert criterion.deferred_source is True
    assert criterion.spatial_input_status == "deferred_unavailable"
    assert criterion.accepted_input_sources == ("analyst_proposed_with_provenance",)
    assert any(band.points is None for band in criterion.bands)
    assert criterion.score_for_value(95) is None
    assert criterion.score_for_value(95, provenance="analyst interview notes") == 10
    assert criterion.score_for_value(None, provenance="analyst interview notes") is None


def test_cfr_ranges_define_representative_point_conventions() -> None:
    for number in (1, 2, 3, 7, 8, 9, 10, 11, 12):
        criterion = SITE_ASSESSMENT_REGISTRY.criterion(number)
        assert criterion.range_convention or any(
            band.point_range is not None
            or band.representative_point_rule is not None
            or band.representative_value_rule is not None
            for band in criterion.bands
        )


def test_criterion_9_service_availability_tracks_cfr_point_direction() -> None:
    criterion = SITE_ASSESSMENT_REGISTRY.criterion(9)
    assert criterion.score_direction == "more_services_more_points"
    assert criterion.score_for_value("all_available") == 5
    assert criterion.score_for_value("some_available") == 3
    assert criterion.score_for_value("none_available") == 0
    assert "ties upward" in criterion.band_for("some_available").representative_point_rule


def test_duplicate_bands_are_rejected() -> None:
    raw = SITE_ASSESSMENT_REGISTRY.criterion(1).model_dump(by_alias=True)
    raw["bands"] = [raw["bands"][0], raw["bands"][0]]
    with pytest.raises(ValidationError, match="duplicate band"):
        SiteAssessmentCriterionDefinition.model_validate(raw)


def test_overlapping_bands_are_rejected() -> None:
    raw = SITE_ASSESSMENT_REGISTRY.criterion(1).model_dump(by_alias=True)
    raw["bands"] = [
        {"id": "a", "label": "a", "min": 0, "max": 50, "points": 1},
        {"id": "b", "label": "b", "min": 50, "max": 100, "points": 2},
    ]
    with pytest.raises(ValidationError, match="overlap"):
        SiteAssessmentCriterionDefinition.model_validate(raw)


def test_missing_citation_is_rejected() -> None:
    raw = SITE_ASSESSMENT_REGISTRY.criterion(1).model_dump(by_alias=True)
    raw.pop("citation")
    with pytest.raises(ValidationError, match="citation"):
        SiteAssessmentCriterionDefinition.model_validate(raw)


def test_unavailable_band_cannot_map_to_zero() -> None:
    raw = SITE_ASSESSMENT_REGISTRY.criterion(2).model_dump(by_alias=True)
    raw["bands"] = [{"id": "unknown", "label": "Unknown", "min": 0, "max": 100, "points": 0}]
    with pytest.raises(ValidationError, match="deferred criteria"):
        SiteAssessmentCriterionDefinition.model_validate(raw)


def test_registry_json_is_valid_and_is_not_an_array() -> None:
    payload = json.loads(
        importlib.resources.files("fpac_soil_mcp")
        .joinpath("data/site_assessment.v1.json")
        .read_text(encoding="utf-8")
    )
    assert payload["schema_version"] == "1.0"


def test_registry_rejects_duplicate_criterion_numbers() -> None:
    raw = SITE_ASSESSMENT_REGISTRY.model_dump(by_alias=True)
    raw["criteria"][1]["criterion_number"] = 1
    with pytest.raises(ValidationError, match="duplicate criterion"):
        SiteAssessmentRegistry.model_validate(raw)
