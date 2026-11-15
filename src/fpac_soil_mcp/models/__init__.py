"""FPAC Soil MCP data and response models package.

Re-exports domain models, integration schemas, map contracts, case models,
and evaluation schemas across structured submodules.
"""

from __future__ import annotations

from fpac_soil_mcp.models.case import (
    AgencyProfile,
    CalculationRun,
    CalculationStatus,
    CaseLifecycleState,
    DecisionRecord,
    DecisionType,
    ExemptionClaim,
    FppaCase,
    FppaRequest,
    GeometryKind,
    GeometryReference,
    ImpactArea,
    ImpactType,
    StateTransitionEvent,
)
from fpac_soil_mcp.models.cdl import (
    CDLAnalysisStatus,
    CDLHistogramBin,
    CDLHistogramResponse,
    CDLServiceMetadata,
)
from fpac_soil_mcp.models.integration import (
    CountyAgProfile,
    CountyIdentifier,
    CountyPartitionGeometry,
    IntegrationStatus,
    SoilInterpretationRecord,
    UrbanExemptionRecord,
)
from fpac_soil_mcp.models.lesa import (
    SUPPORTED_INDEX_MSG,
    VALIDATED_PRODUCTIVITY_INDEXES,
    CriterionFactInput,
    CriterionPointInput,
    LandEvaluationSummary,
    MapUnitProductivityRating,
    PreliminaryLESAResponse,
    ProductivityIndexType,
    SiteAssessmentCriterion,
    SiteAssessmentInputs,
    SiteAssessmentSummary,
)
from fpac_soil_mcp.models.map import (
    AUTHORITY_LABEL,
    DISPLAY_CRS,
    MAP_SCHEMA_VERSION,
    LayerAuthority,
    LayerDelivery,
    LayerKind,
    LegendPattern,
    MapBlock,
    MapLayer,
    MapLegendItem,
    ResultAuthority,
)
from fpac_soil_mcp.models.soil import (
    FarmlandCategoryBreakdown,
    FarmlandClassificationResponse,
    FarmlandClassItem,
    FarmlandClassListResponse,
    FppaScopeResponse,
    QuerySource,
    SoilMapUnit,
    SoilMapUnitAcreage,
    ToolError,
)
from fpac_soil_mcp.models.spatial import (
    CorridorAlternativeComparison,
    CorridorAlternativeInput,
    CorridorCountySegment,
    CorridorFarmlandAnalysisResponse,
    CorridorImpactBreakdown,
    PolygonFarmlandAnalysisResponse,
)

__all__ = [
    # map
    "AUTHORITY_LABEL",
    "DISPLAY_CRS",
    "MAP_SCHEMA_VERSION",
    "SUPPORTED_INDEX_MSG",
    "VALIDATED_PRODUCTIVITY_INDEXES",
    # case
    "AgencyProfile",
    # cdl
    "CDLAnalysisStatus",
    "CDLHistogramBin",
    "CDLHistogramResponse",
    "CDLServiceMetadata",
    "CalculationRun",
    "CalculationStatus",
    "CaseLifecycleState",
    # spatial
    "CorridorAlternativeComparison",
    "CorridorAlternativeInput",
    "CorridorCountySegment",
    "CorridorFarmlandAnalysisResponse",
    "CorridorImpactBreakdown",
    # integration
    "CountyAgProfile",
    "CountyIdentifier",
    "CountyPartitionGeometry",
    # lesa
    "CriterionFactInput",
    "CriterionPointInput",
    "DecisionRecord",
    "DecisionType",
    "ExemptionClaim",
    # soil
    "FarmlandCategoryBreakdown",
    "FarmlandClassItem",
    "FarmlandClassListResponse",
    "FarmlandClassificationResponse",
    "FppaCase",
    "FppaRequest",
    "FppaScopeResponse",
    "GeometryKind",
    "GeometryReference",
    "ImpactArea",
    "ImpactType",
    "IntegrationStatus",
    "LandEvaluationSummary",
    "LayerAuthority",
    "LayerDelivery",
    "LayerKind",
    "LegendPattern",
    "MapBlock",
    "MapLayer",
    "MapLegendItem",
    "MapUnitProductivityRating",
    "PolygonFarmlandAnalysisResponse",
    "PreliminaryLESAResponse",
    "ProductivityIndexType",
    "QuerySource",
    "ResultAuthority",
    "SiteAssessmentCriterion",
    "SiteAssessmentInputs",
    "SiteAssessmentSummary",
    "SoilInterpretationRecord",
    "SoilMapUnit",
    "SoilMapUnitAcreage",
    "StateTransitionEvent",
    "ToolError",
    "UrbanExemptionRecord",
]
