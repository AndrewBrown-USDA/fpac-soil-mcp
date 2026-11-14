"""USDA NRCS Soil Data Access (SDA) client package.

Provides client access to SDA tabular endpoints, fixed SQL query templates,
dynamic SDV query builders, and the metadata-driven rating contract registry.
"""

from __future__ import annotations

from fpac_soil_mcp.clients.sda.client import (
    SDAClient,
    SDAClientError,
    SDAQueryError,
    SDAServiceUnavailableError,
    SDATimeoutError,
    SDAValidationError,
)
from fpac_soil_mcp.clients.sda.sdv_registry import (
    ALLOWED_SDV_TABLES,
    PRODUCTIVITY_PROVENANCE,
    PRODUCTIVITY_SEMANTICS,
    SDV_CAVEATS,
    SDV_CONTRACT_FIELDS,
    SDV_RATING_REGISTRY,
    SDV_REGISTRY_VERSION,
    SUPPORTED_HORIZON_METHODS,
    SUPPORTED_SDV_ALGORITHMS,
    SdvRatingSpec,
    resolve_sdv_spec,
    validate_sdv_record,
)
from fpac_soil_mcp.clients.sda.sql_templates import (
    SQL_INTERPRETATION_CATALOG,
    SQL_INTERPRETATION_DOMINANT_COMP,
    SQL_INTERPRETATION_WEIGHTED_AVG,
    SQL_MUKEY_LOOKUP,
    SQL_POINT_LOOKUP,
    SQL_POLYGON_LOOKUP,
    SQL_SDV_ATTRIBUTE_LOOKUP,
    SQL_SPATIAL_INTERSECTION_CLIPPED,
    SQL_SPATIAL_INTERSECTION_OVERLAP,
    build_dynamic_sdv_county_max_query,
    build_dynamic_sdv_query,
    build_sdv_county_max_query,
    build_sdv_rating_query,
    validate_survey_area_symbol,
)

__all__ = [
    "ALLOWED_SDV_TABLES",
    "PRODUCTIVITY_PROVENANCE",
    "PRODUCTIVITY_SEMANTICS",
    "SDV_CAVEATS",
    "SDV_CONTRACT_FIELDS",
    "SDV_RATING_REGISTRY",
    "SDV_REGISTRY_VERSION",
    "SQL_INTERPRETATION_CATALOG",
    "SQL_INTERPRETATION_DOMINANT_COMP",
    "SQL_INTERPRETATION_WEIGHTED_AVG",
    "SQL_MUKEY_LOOKUP",
    "SQL_POINT_LOOKUP",
    "SQL_POLYGON_LOOKUP",
    "SQL_SDV_ATTRIBUTE_LOOKUP",
    "SQL_SPATIAL_INTERSECTION_CLIPPED",
    "SQL_SPATIAL_INTERSECTION_OVERLAP",
    "SUPPORTED_HORIZON_METHODS",
    "SUPPORTED_SDV_ALGORITHMS",
    "SDAClient",
    "SDAClientError",
    "SDAQueryError",
    "SDAServiceUnavailableError",
    "SDATimeoutError",
    "SDAValidationError",
    "SdvRatingSpec",
    "build_dynamic_sdv_county_max_query",
    "build_dynamic_sdv_query",
    "build_sdv_county_max_query",
    "build_sdv_rating_query",
    "resolve_sdv_spec",
    "validate_sdv_record",
    "validate_survey_area_symbol",
]
