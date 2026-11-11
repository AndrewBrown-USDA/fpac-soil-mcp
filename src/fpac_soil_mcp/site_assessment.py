"""Versioned Site Assessment question and scoring registry."""

from __future__ import annotations

import importlib.resources
import itertools
import json
import math
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

AnswerType = Literal["percentage", "distance_miles", "qualitative"]


class SiteAssessmentBand(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    band_id: str = Field(alias="id", min_length=1)
    label: str = Field(min_length=1)
    points: float | None = Field(default=None, ge=0)
    minimum: float | None = Field(default=None, alias="min")
    maximum: float | None = Field(default=None, alias="max")
    minimum_inclusive: bool = Field(default=True, alias="min_inclusive")
    maximum_inclusive: bool = Field(default=True, alias="max_inclusive")
    point_range: tuple[float, float] | None = Field(default=None, min_length=2, max_length=2)
    representative_value_rule: str | None = None
    representative_point_rule: str | None = None

    @model_validator(mode="after")
    def validate_bounds(self) -> SiteAssessmentBand:
        if self.minimum is not None and self.maximum is not None and self.minimum > self.maximum:
            raise ValueError("band minimum must not exceed maximum")
        if self.points is None and (self.minimum is not None or self.maximum is not None):
            raise ValueError("unavailable bands must not define numeric bounds")
        if self.point_range is not None:
            if self.points is None or self.point_range[0] > self.point_range[1]:
                raise ValueError("point ranges require available points and ordered bounds")
            if self.points_range_invalid():
                raise ValueError("representative points must lie within the point range")
        return self

    def points_range_invalid(self) -> bool:
        assert self.point_range is not None and self.points is not None
        return not self.point_range[0] <= self.points <= self.point_range[1]

    def contains(self, value: str | float) -> bool:
        if self.minimum is None:
            return False
        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            return False
        lower_matches = numeric_value > self.minimum or (
            self.minimum_inclusive and numeric_value == self.minimum
        )
        upper_matches = (
            self.maximum is None
            or numeric_value < self.maximum
            or (self.maximum_inclusive and numeric_value == self.maximum)
        )
        return lower_matches and upper_matches


class SiteAssessmentCriterionDefinition(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    criterion_number: int = Field(ge=1, le=12)
    name: str = Field(min_length=1)
    question: str = Field(min_length=1)
    answer_type: AnswerType
    max_points: float = Field(ge=0)
    citation: str = Field(min_length=1)
    requires_rationale: bool
    requires_verification: bool
    deferred_source: bool = False
    score_direction: str = Field(min_length=1)
    range_convention: str | None = None
    accepted_input_sources: tuple[str, ...] = ()
    spatial_input_status: str | None = None
    bands: tuple[SiteAssessmentBand, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_bands(self) -> SiteAssessmentCriterionDefinition:
        seen_ids: set[str] = set()
        numeric: list[tuple[float, bool, float, bool, str]] = []
        has_unavailable = False
        for band in self.bands:
            if band.band_id in seen_ids:
                raise ValueError(f"duplicate band id '{band.band_id}'")
            seen_ids.add(band.band_id)
            if band.points is None:
                has_unavailable = True
                continue
            if band.points > self.max_points:
                raise ValueError(
                    f"band '{band.band_id}' points exceed criterion maximum {self.max_points}"
                )
            if self.answer_type == "qualitative":
                if band.minimum is not None or band.maximum is not None:
                    raise ValueError("qualitative bands cannot define numeric bounds")
            else:
                if band.minimum is None:
                    raise ValueError("numeric bands require a minimum")
                upper = band.maximum if band.maximum is not None else float("inf")
                numeric.append(
                    (
                        band.minimum,
                        band.minimum_inclusive,
                        upper,
                        band.maximum_inclusive,
                        band.band_id,
                    )
                )
        numeric.sort()
        for (_, _, previous_max, previous_max_inclusive, _), (
            current_min,
            current_min_inclusive,
            _,
            _,
            _,
        ) in itertools.pairwise(numeric):
            if current_min < previous_max or (
                current_min == previous_max and current_min_inclusive and previous_max_inclusive
            ):
                raise ValueError("numeric bands overlap")
        if self.deferred_source and not has_unavailable:
            raise ValueError("deferred criteria require an explicit unavailable band")
        if self.deferred_source and self.spatial_input_status != "deferred_unavailable":
            raise ValueError("deferred criteria must mark spatial input unavailable")
        if self.accepted_input_sources and not self.deferred_source:
            raise ValueError("accepted input sources are reserved for deferred criteria")
        return self

    def band_for(self, value: str | float | None) -> SiteAssessmentBand | None:
        """Return the matching band, preserving unknown and out-of-band states."""
        if value is None or (isinstance(value, str) and value.strip().lower() in {"", "unknown"}):
            return next((band for band in self.bands if band.band_id == "unknown"), None)
        if self.answer_type == "qualitative":
            normalized = str(value).strip().lower()
            return next(
                (
                    band
                    for band in self.bands
                    if normalized in {band.band_id.lower(), band.label.lower()}
                ),
                None,
            )
        return next((band for band in self.bands if band.contains(value)), None)

    def score_for_value(
        self, value: str | float | None, *, provenance: str | None = None
    ) -> float | None:
        """Resolve registry points; return None for unknown, out-of-band, or unproven input."""
        if self.criterion_number == 2 and not (provenance and provenance.strip()):
            return None
        band = self.band_for(value)
        if band is None or band.points is None:
            return None
        if band.point_range is None or band.minimum is None or band.maximum is None:
            return band.points
        numeric_value = float(value)
        low_points, high_points = band.point_range
        ratio = (numeric_value - band.minimum) / (band.maximum - band.minimum)
        return float(math.floor(low_points + ratio * (high_points - low_points) + 0.5))


class SiteAssessmentRegistry(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str = Field(min_length=1)
    registry_id: str = Field(min_length=1)
    citation: str = Field(min_length=1)
    criteria: tuple[SiteAssessmentCriterionDefinition, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_registry(self) -> SiteAssessmentRegistry:
        numbers = [criterion.criterion_number for criterion in self.criteria]
        if len(numbers) != len(set(numbers)):
            raise ValueError("duplicate criterion numbers")
        if set(numbers) != set(range(1, 13)):
            raise ValueError("registry must define criteria 1 through 12 exactly")
        return self

    def criterion(self, criterion_number: int) -> SiteAssessmentCriterionDefinition:
        for criterion in self.criteria:
            if criterion.criterion_number == criterion_number:
                return criterion
        raise KeyError(criterion_number)


def _load_resource(resource_path: str) -> dict[str, Any]:
    ref = importlib.resources.files("fpac_soil_mcp").joinpath(resource_path)
    with ref.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise TypeError("Site Assessment registry must be a JSON object")
    return payload


def load_site_assessment_registry(
    resource_path: str = "data/site_assessment.v1.json",
) -> SiteAssessmentRegistry:
    """Load and validate the bundled Site Assessment registry."""
    registry = SiteAssessmentRegistry.model_validate(_load_resource(resource_path))
    if registry.schema_version != "1.0":
        raise ValueError(f"Unsupported Site Assessment schema version '{registry.schema_version}'")
    return registry


SITE_ASSESSMENT_REGISTRY = load_site_assessment_registry()

__all__ = [
    "SITE_ASSESSMENT_REGISTRY",
    "AnswerType",
    "SiteAssessmentBand",
    "SiteAssessmentCriterionDefinition",
    "SiteAssessmentRegistry",
    "load_site_assessment_registry",
]
