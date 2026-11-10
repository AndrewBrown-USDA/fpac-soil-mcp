"""Contract tests for the versioned Site Assessment registry."""

from __future__ import annotations

import importlib.resources
import json

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


def test_every_criterion_has_citation_maximum_and_valid_points() -> None:
    for criterion in SITE_ASSESSMENT_REGISTRY.criteria:
        assert criterion.citation
        assert criterion.max_points >= 0
        assert all(
            band.points is None or 0 <= band.points <= criterion.max_points
            for band in criterion.bands
        )


def test_unknown_and_deferred_inputs_remain_unavailable() -> None:
    criterion = SITE_ASSESSMENT_REGISTRY.criterion(2)
    assert criterion.deferred_source is True
    assert any(band.points is None for band in criterion.bands)
    assert any(
        band.points is None
        for number in (8, 9, 10, 11, 12)
        for band in SITE_ASSESSMENT_REGISTRY.criterion(number).bands
    )


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
