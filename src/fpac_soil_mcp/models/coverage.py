"""Shared coverage vocabularies for every ``coverage_status`` field.

Two dimensions are reported separately. ``SoilMappingCoverage`` says whether the
evaluated area has SSURGO map units. ``RatingCoverage`` says whether the mapped
soil supports a productivity rating (SDA rating rows, NCCPI baseline, Land
Evaluation). A failed request or upstream query is always ``error``, never
``unmapped`` or ``unrated``, so an outage is not read as "no soils" or "no rating".

| Type                | Value    | Meaning                                                         |
| ------------------- | -------- | --------------------------------------------------------------- |
| SoilMappingCoverage | covered  | All evaluated area has SSURGO map units                         |
|                     | partial  | Some evaluated area has no map unit                             |
|                     | unmapped | Query succeeded; no map units returned                          |
|                     | error    | Invalid request or upstream query failed; cause in limitations  |
|                     |          | (and in the error field where the response has one)             |
| RatingCoverage      | rated    | All mapped area / component share supports the rating           |
|                     | partial  | Rating supported for part of the area / components              |
|                     | unrated  | Mapped soil, but no usable rating                               |
|                     | unmapped | No mapped soil to rate                                          |
|                     | unknown  | Nothing evaluated (zero acreage) or no SDA row for the map unit |
|                     | error    | Rating query failed; cause in limitations                       |

Retired values (0.6.0, no aliases): ``partially_covered`` -> ``partial``;
``no_data`` and ``invalid_request`` -> ``error``; rating ``covered`` -> ``rated``;
SDA status ``no_coverage`` -> ``unrated``; SDA status ``not_found`` -> ``unknown``.
An NCCPI baseline with no SDA row stays ``null``.

SDV caveat keys and reason codes are unchanged: reason ``no_coverage`` is reported
with status ``unrated``, and reason ``not_found`` with status ``unknown``.
"""

from __future__ import annotations

from typing import Final, Literal, get_args

SoilMappingCoverage = Literal["covered", "partial", "unmapped", "error"]
RatingCoverage = Literal["rated", "partial", "unrated", "unmapped", "unknown", "error"]

MAPPING_COVERED: Final = "covered"
MAPPING_PARTIAL: Final = "partial"
MAPPING_UNMAPPED: Final = "unmapped"
MAPPING_ERROR: Final = "error"

RATING_RATED: Final = "rated"
RATING_PARTIAL: Final = "partial"
RATING_UNRATED: Final = "unrated"
RATING_UNMAPPED: Final = "unmapped"
RATING_UNKNOWN: Final = "unknown"
RATING_ERROR: Final = "error"

SOIL_MAPPING_COVERAGE_VALUES: Final[frozenset[str]] = frozenset(get_args(SoilMappingCoverage))
RATING_COVERAGE_VALUES: Final[frozenset[str]] = frozenset(get_args(RatingCoverage))

__all__ = [
    "MAPPING_COVERED",
    "MAPPING_ERROR",
    "MAPPING_PARTIAL",
    "MAPPING_UNMAPPED",
    "RATING_COVERAGE_VALUES",
    "RATING_ERROR",
    "RATING_PARTIAL",
    "RATING_RATED",
    "RATING_UNKNOWN",
    "RATING_UNMAPPED",
    "RATING_UNRATED",
    "SOIL_MAPPING_COVERAGE_VALUES",
    "RatingCoverage",
    "SoilMappingCoverage",
]
