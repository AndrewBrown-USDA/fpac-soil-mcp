"""Versioned Site Assessment question and scoring registry."""

from __future__ import annotations

import importlib.resources
import itertools
import json
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

    @model_validator(mode="after")
    def validate_bounds(self) -> SiteAssessmentBand:
        if self.minimum is not None and self.maximum is not None and self.minimum > self.maximum:
            raise ValueError("band minimum must not exceed maximum")
        if self.points is None and (self.minimum is not None or self.maximum is not None):
            raise ValueError("unavailable bands must not define numeric bounds")
        return self


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
    bands: tuple[SiteAssessmentBand, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_bands(self) -> SiteAssessmentCriterionDefinition:
        seen_ids: set[str] = set()
        numeric: list[tuple[float, float, str]] = []
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
                numeric.append((band.minimum, upper, band.band_id))
        numeric.sort()
        for (_, previous_max, _), (current_min, _, _) in itertools.pairwise(numeric):
            if current_min <= previous_max:
                raise ValueError("numeric bands overlap")
        if self.deferred_source and not has_unavailable:
            raise ValueError("deferred criteria require an explicit unavailable band")
        return self


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
