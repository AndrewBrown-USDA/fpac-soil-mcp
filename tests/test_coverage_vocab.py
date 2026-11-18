"""Tests for the shared coverage vocabularies in ``fpac_soil_mcp.models.coverage``."""

from __future__ import annotations

from typing import get_args

import pytest
from pydantic import BaseModel, ValidationError

from fpac_soil_mcp.models import coverage
from fpac_soil_mcp.models.coverage import RatingCoverage, SoilMappingCoverage
from fpac_soil_mcp.models.lesa import LandEvaluationSummary

RETIRED_VALUES = ("partially_covered", "no_data")


class _MappingModel(BaseModel):
    status: SoilMappingCoverage


class _RatingModel(BaseModel):
    status: RatingCoverage


def test_soil_mapping_values_are_exact():
    assert set(get_args(SoilMappingCoverage)) == {"covered", "partial", "unmapped", "error"}
    assert coverage.SOIL_MAPPING_COVERAGE_VALUES == frozenset(get_args(SoilMappingCoverage))


def test_rating_values_are_exact():
    assert set(get_args(RatingCoverage)) == {
        "rated",
        "partial",
        "unrated",
        "unmapped",
        "unknown",
        "error",
    }
    assert coverage.RATING_COVERAGE_VALUES == frozenset(get_args(RatingCoverage))


def test_constants_match_vocabularies():
    mapping = {getattr(coverage, name) for name in dir(coverage) if name.startswith("MAPPING_")}
    rating = {
        getattr(coverage, name)
        for name in dir(coverage)
        if name.startswith("RATING_") and name != "RATING_COVERAGE_VALUES"
    }
    assert mapping == set(get_args(SoilMappingCoverage))
    assert rating == set(get_args(RatingCoverage))


@pytest.mark.parametrize("value", sorted(get_args(SoilMappingCoverage)))
def test_mapping_model_accepts_vocabulary(value):
    assert _MappingModel(status=value).status == value


@pytest.mark.parametrize("value", sorted(get_args(RatingCoverage)))
def test_rating_model_accepts_vocabulary(value):
    assert _RatingModel(status=value).status == value


@pytest.mark.parametrize("model", [_MappingModel, _RatingModel])
@pytest.mark.parametrize("value", RETIRED_VALUES)
def test_models_reject_retired_values(model, value):
    with pytest.raises(ValidationError):
        model(status=value)


def test_rating_model_rejects_mapping_only_value():
    with pytest.raises(ValidationError):
        _RatingModel(status="covered")


@pytest.mark.parametrize("value", ["rated", "error", "covered"])
def test_land_evaluation_summary_transitional_values(value):
    assert LandEvaluationSummary(coverage_status=value).coverage_status == value


def test_land_evaluation_summary_default_is_unknown():
    assert LandEvaluationSummary().coverage_status == "unknown"
