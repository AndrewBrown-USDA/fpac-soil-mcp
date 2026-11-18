"""Tests for the shared coverage vocabularies in ``fpac_soil_mcp.models.coverage``."""

from __future__ import annotations

from typing import get_args

import pytest
from pydantic import BaseModel, ValidationError

from fpac_soil_mcp.models import coverage
from fpac_soil_mcp.models.coverage import RatingCoverage, SoilMappingCoverage
from fpac_soil_mcp.models.lesa import LandEvaluationSummary
from fpac_soil_mcp.models.soil import (
    FarmlandCategoryBreakdown,
    FarmlandClassificationResponse,
    QuerySource,
    SoilMapUnitAcreage,
)
from fpac_soil_mcp.models.spatial import CorridorCountySegment, PolygonFarmlandAnalysisResponse

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


@pytest.mark.parametrize("value", ["rated", "error"])
def test_land_evaluation_summary_accepts_rating_values(value):
    assert LandEvaluationSummary(coverage_status=value).coverage_status == value


@pytest.mark.parametrize("value", ["covered", *RETIRED_VALUES])
def test_land_evaluation_summary_rejects_mapping_and_retired_values(value):
    with pytest.raises(ValidationError):
        LandEvaluationSummary(coverage_status=value)


def _polygon_kwargs(**overrides):
    base = {
        "geometry_hash": "sha256:" + "0" * 64,
        "total_aoi_acres": 1.0,
        "coverage_status": "covered",
        "urban_screening": {},
        "farmland_summary": FarmlandCategoryBreakdown(),
        "tabular_csv": "",
        "source": QuerySource(timestamp_utc="2026-01-01T00:00:00Z"),
        "regulatory_notice": "notice",
    }
    base.update(overrides)
    return base


_UNIT = {"mukey": "1", "calculated_acres": 1.0, "percentage_of_aoi": 100.0}
_SEGMENT = {"state_fips": "19", "county_fips": "169", "county_name": "Story"}


@pytest.mark.parametrize(
    ("build", "value"),
    [
        (
            lambda v: FarmlandClassificationResponse(
                query_type="mukey",
                input_query={},
                coverage_status=v,
                source=QuerySource(timestamp_utc="2026-01-01T00:00:00Z"),
                regulatory_notice="notice",
            ),
            "no_data",
        ),
        (
            lambda v: PolygonFarmlandAnalysisResponse(**_polygon_kwargs(coverage_status=v)),
            "partially_covered",
        ),
        (
            lambda v: PolygonFarmlandAnalysisResponse(**_polygon_kwargs(coverage_status=v)),
            "invalid_request",
        ),
        (lambda v: CorridorCountySegment(**_SEGMENT, coverage_status=v), "partially_covered"),
        (lambda v: CorridorCountySegment(**_SEGMENT, productivity_coverage_status=v), "covered"),
        (lambda v: SoilMapUnitAcreage(**_UNIT, productivity_coverage_status=v), "no_coverage"),
        (lambda v: SoilMapUnitAcreage(**_UNIT, nccpi_baseline_coverage_status=v), "not_found"),
    ],
)
def test_public_models_reject_retired_values(build, value):
    with pytest.raises(ValidationError):
        build(value)


def test_nccpi_baseline_coverage_status_allows_null():
    assert SoilMapUnitAcreage(**_UNIT).nccpi_baseline_coverage_status is None


def test_land_evaluation_summary_default_is_unknown():
    assert LandEvaluationSummary().coverage_status == "unknown"
