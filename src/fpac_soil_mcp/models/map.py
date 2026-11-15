"""Map result contract models and constants (ADR 0017)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

MAP_SCHEMA_VERSION = "1.0"
DISPLAY_CRS = "EPSG:4326"
AUTHORITY_LABEL = "Preliminary Machine Estimate"

LayerKind = Literal["polygon", "line", "point"]
LayerDelivery = Literal["inline_geojson", "omitted"]
LayerAuthority = Literal["user_input", "machine_estimate", "reference_data"]
LegendPattern = Literal[
    "solid", "diagonal_hatch", "cross_hatch", "dot_stipple", "outline", "dashed_outline"
]


class MapLegendItem(BaseModel):
    """One legend entry; ``value`` matches the layer's ``style_key`` property."""

    value: str = Field(description="Feature property value this entry styles")
    label: str = Field(description="Display label")
    color: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$", description="Hex colour")
    pattern: LegendPattern = Field(default="solid", description="Secondary visual cue")
    code: str | None = Field(default=None, description="Text code shown with the colour")


class MapLayer(BaseModel):
    """One drawable layer of a map result."""

    id: str = Field(description="Stable layer id (ADR 0017)")
    title: str = Field(description="Display title")
    kind: LayerKind = Field(description="Geometry kind")
    delivery: LayerDelivery = Field(
        default="omitted", description="inline_geojson when features are included"
    )
    authority: LayerAuthority = Field(description="Authority level of the layer content")
    source: str = Field(description="Data source service name")
    data_vintage: str | None = Field(default=None, description="Data vintage when known")
    style_key: str | None = Field(
        default=None, description="Feature property that legend values match"
    )
    legend: list[MapLegendItem] = Field(default_factory=list, description="Server legend")
    simplified: bool = Field(default=False, description="Display copy was simplified")
    simplify_tolerance_m: float | None = Field(
        default=None, description="Simplification tolerance in metres (EPSG:6933)"
    )
    truncated: bool = Field(default=False, description="Features dropped by the size cap")
    feature_count: int | None = Field(
        default=None, description="Features in feature_collection; null when omitted"
    )
    feature_collection: dict[str, Any] | None = Field(
        default=None, description="GeoJSON FeatureCollection; null when omitted"
    )


class MapBlock(BaseModel):
    """Map result block: display CRS, bounds of inline layers, layers, warnings."""

    display_crs: str = Field(default=DISPLAY_CRS, description="CRS of inline geometry")
    bounds: list[float] | None = Field(
        default=None,
        description="[min_lon, min_lat, max_lon, max_lat] of inline layers; null if none",
    )
    layers: list[MapLayer] = Field(default_factory=list, description="Layers, bottom to top")
    warnings: list[str] = Field(default_factory=list, description="Display warnings")

    @model_validator(mode="wrap")
    @classmethod
    def _validate_map_block(cls, value: Any, handler) -> MapBlock:
        if isinstance(value, BaseModel) and value.__class__.__name__ == "MapBlock":
            return handler(value.model_dump())
        return handler(value)


class ResultAuthority(BaseModel):
    """Authority of an analysis result: always a preliminary machine estimate."""

    level: Literal["machine_estimate"] = "machine_estimate"
    label: str = AUTHORITY_LABEL
    official_filing: Literal[False] = False

    @model_validator(mode="wrap")
    @classmethod
    def _validate_result_authority(cls, value: Any, handler) -> ResultAuthority:
        if isinstance(value, BaseModel) and value.__class__.__name__ == "ResultAuthority":
            return handler(value.model_dump())
        return handler(value)
