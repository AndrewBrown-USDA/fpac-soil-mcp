"""Official source registry and regional scoring configuration loader.

Provides validated models and package-resource loaders for official statutory,
regulatory, form edition, and public API source records.
"""

import importlib.resources
import json
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from fpac_soil_mcp.authority import _validate_non_empty_str


class SourceLifecycleStatus(str, Enum):
    """Lifecycle status of an official source document or endpoint."""

    ACTIVE = "active"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"


class OfficialSourceRecord(BaseModel):
    """Catalog record for a legal authority, official form, or public data service."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_id: str = Field(description="Unique identifier for the source record")
    schema_version: str = Field(description="Registry schema version (e.g. '1.0')")
    publisher: str = Field(description="Publishing authority or federal agency")
    title: str = Field(description="Full title of statute, regulation, form, or service")
    citation: str = Field(description="Standard legal or bibliographic citation")
    canonical_url: str = Field(description="Authoritative public URL")
    edition: str | None = Field(
        default=None, description="Form edition or API version if applicable"
    )
    effective_date: str | None = Field(
        default=None, description="Effective date in YYYY-MM-DD format if known"
    )
    status: SourceLifecycleStatus = Field(description="Current lifecycle status")
    retrieval_guidance: str = Field(description="Guidance on accessing or querying the source")

    @field_validator(
        "source_id",
        "schema_version",
        "publisher",
        "title",
        "citation",
        "canonical_url",
        "retrieval_guidance",
    )
    @classmethod
    def _validate_strings(cls, v: str, info) -> str:
        return _validate_non_empty_str(v, info.field_name or "field")

    @field_validator("canonical_url")
    @classmethod
    def _validate_url(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError(f"canonical_url '{v}' must be a valid HTTP/HTTPS URL.")
        return v


class RegionalScoringConfig(BaseModel):
    """State or regional LESA scoring configuration and weighting rules."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    config_id: str = Field(description="Unique configuration identifier")
    schema_version: str = Field(description="Registry schema version (e.g. '1.0')")
    jurisdiction: str = Field(description="State FIPS, state USPS abbreviation, or regional code")
    method_name: str = Field(description="Official name of regional scoring methodology")
    method_version: str = Field(description="Version of regional method")
    source_record_id: str = Field(description="Foreign key link to OfficialSourceRecord")
    effective_start: str = Field(description="Effective start date YYYY-MM-DD")
    effective_end: str | None = Field(
        default=None, description="Optional effective expiration date"
    )
    approval_authority: str = Field(description="Approving agency / official body")

    @field_validator(
        "config_id",
        "schema_version",
        "jurisdiction",
        "method_name",
        "method_version",
        "source_record_id",
        "effective_start",
        "approval_authority",
    )
    @classmethod
    def _validate_strings(cls, v: str, info) -> str:
        return _validate_non_empty_str(v, info.field_name or "field")


def _load_json_resource(package_subpath: str) -> Any:
    """Load JSON content from installed package data resources."""
    try:
        ref = importlib.resources.files("fpac_soil_mcp").joinpath(package_subpath)
        with ref.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        raise FileNotFoundError(
            f"Failed to load package resource '{package_subpath}': {exc}"
        ) from exc


def load_official_sources(
    resource_path: str = "data/official_sources.v1.json",
) -> dict[str, OfficialSourceRecord]:
    """Load and validate all official source records from package data.

    Returns a mapping of source_id -> OfficialSourceRecord.
    """
    raw_data = _load_json_resource(resource_path)
    if not isinstance(raw_data, list):
        raise TypeError("Official sources registry must be a JSON array.")

    records: dict[str, OfficialSourceRecord] = {}
    for item in raw_data:
        record = OfficialSourceRecord.model_validate(item)
        if record.schema_version != "1.0":
            raise ValueError(
                f"Unsupported schema_version '{record.schema_version}' for source '{record.source_id}'."
            )
        if record.source_id in records:
            raise ValueError(f"Duplicate source_id '{record.source_id}' found in registry.")
        records[record.source_id] = record

    return records


def load_regional_scoring_configs(
    resource_path: str = "data/regional_scoring.v1.json",
    source_registry: dict[str, OfficialSourceRecord] | None = None,
) -> dict[str, RegionalScoringConfig]:
    """Load and validate regional scoring configurations from package data.

    Returns a mapping of config_id -> RegionalScoringConfig.
    """
    raw_data = _load_json_resource(resource_path)
    if not isinstance(raw_data, list):
        raise TypeError("Regional scoring registry must be a JSON array.")

    if source_registry is None:
        source_registry = load_official_sources()

    configs: dict[str, RegionalScoringConfig] = {}
    for item in raw_data:
        config = RegionalScoringConfig.model_validate(item)
        if config.schema_version != "1.0":
            raise ValueError(
                f"Unsupported schema_version '{config.schema_version}' for config '{config.config_id}'."
            )
        if config.config_id in configs:
            raise ValueError(
                f"Duplicate config_id '{config.config_id}' in regional scoring registry."
            )
        if config.source_record_id not in source_registry:
            raise ValueError(
                f"Regional config '{config.config_id}' references unknown source_record_id '{config.source_record_id}'."
            )
        configs[config.config_id] = config

    return configs
