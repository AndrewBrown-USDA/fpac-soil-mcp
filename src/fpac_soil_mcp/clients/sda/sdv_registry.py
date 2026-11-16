"""SDV metadata-driven rating contract, registry, and validation helpers.

The metadata-driven SDV rating contract is defined in ``SDV_RATING_REGISTRY`` (ADR 0014).
See ``docs/sdv-metadata-contract.md`` for the field-level contract, per-table behaviour,
provenance IDs, and the caveat catalogue.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from fpac_soil_mcp.clients.sda.client import SDAValidationError
from fpac_soil_mcp.models.lesa import SUPPORTED_INDEX_MSG

# ---------------------------------------------------------------------------
# SDV metadata-driven rating contract (ADR 0014)
#
# Frozen, versioned registry of validated sdvattribute records.  Public callers
# still use the four fixed selectors (nccpi, csr2, cpi, storie); the registry
# adds internal support for Available Water Storage and crop yields.  See
# docs/sdv-metadata-contract.md for the field-level contract.
# ---------------------------------------------------------------------------

SDV_REGISTRY_VERSION = "1"

#: Fields the engine reads from sdvattribute (also the SELECT list for the
#: metadata lookup query).
SDV_CONTRACT_FIELDS = (
    "attributekey",
    "attributename",
    "attributetablename",
    "attributecolumnname",
    "attributelogicaldatatype",
    "nasisrulename",
    "ruledesign",
    "algorithmname",
    "horzaggmeth",
    "tiebreakrule",
    "depthqualifiermode",
    "layerdepthtotop",
    "layerdepthtobottom",
    "layerdepthuom",
    "interpnullsaszeroflag",
    "nullratingreplacementvalue",
    "primaryconcolname",
    "secondaryconcolname",
    "componentpercentcutoff",
    "resultcolumnname",
    "notratedphrase",
    "attributetype",
)

SUPPORTED_SDV_ALGORITHMS = frozenset(
    {"Weighted Average", "Dominant Condition", "No Aggregation Necessary"}
)

SUPPORTED_HORIZON_METHODS = frozenset({"Weighted Sum", "Weighted Average"})

_SDV_STRATEGY_TABLES = frozenset({"cointerp", "chorizon", "cocropyld", "component", "mapunit"})


@dataclass(frozen=True)
class SdvRatingSpec:
    """A frozen, validated SDV rating specification from the registry."""

    spec_id: str
    provenance_id: str
    attributename: str
    table: str
    column: str
    value_column: str
    rule_name: str
    algorithm: str
    horizon_method: str
    depth_top_cm: float | None
    depth_bottom_cm: float | None
    tiebreak_rule: int
    nulls_as_zero: bool
    required_constraints: tuple[str, ...]
    scale: str
    precision: int
    sentinels: frozenset[float]
    aliases: frozenset[str]


SDV_RATING_REGISTRY: MappingProxyType[str, SdvRatingSpec] = MappingProxyType(
    {
        "nccpi": SdvRatingSpec(
            spec_id="nccpi",
            provenance_id="SDA:NCCPI_V3",
            attributename="National Commodity Crop Productivity Index",
            table="cointerp",
            column="interphrc",
            value_column="interphr",
            rule_name="NCCPI - National Commodity Crop Productivity Index (Ver 3.0)",
            algorithm="Weighted Average",
            horizon_method="Weighted Average",
            depth_top_cm=None,
            depth_bottom_cm=None,
            tiebreak_rule=1,
            nulls_as_zero=False,
            required_constraints=(),
            scale="0-1",
            precision=3,
            sentinels=frozenset({99.0, 999.0, -99.0, -999.0}),
            aliases=frozenset({"nccpi", "nccpi_v3", "national commodity crop productivity index"}),
        ),
        "storie": SdvRatingSpec(
            spec_id="storie",
            provenance_id="SDA:COINTERP_STORIE_CA",
            attributename="California Revised Storie Index (CA)",
            table="cointerp",
            column="interphrc",
            value_column="interphr",
            rule_name="AGR - California Revised Storie Index (CA)",
            algorithm="Dominant Condition",
            horizon_method="Weighted Average",
            depth_top_cm=None,
            depth_bottom_cm=None,
            tiebreak_rule=-1,
            nulls_as_zero=False,
            required_constraints=(),
            scale="0-1",
            precision=3,
            sentinels=frozenset({99.0, 999.0, -99.0, -999.0}),
            aliases=frozenset(
                {
                    "storie",
                    "california revised storie index",
                    "agr - california revised storie index (ca)",
                }
            ),
        ),
        "csr2": SdvRatingSpec(
            spec_id="csr2",
            provenance_id="SDA:MAPUNIT_IACORNSR",
            attributename="Iowa Corn Suitability Rating CSR2 (IA)",
            table="mapunit",
            column="iacornsr",
            value_column="iacornsr",
            rule_name="",
            algorithm="No Aggregation Necessary",
            horizon_method="Weighted Average",
            depth_top_cm=None,
            depth_bottom_cm=None,
            tiebreak_rule=1,
            nulls_as_zero=False,
            required_constraints=(),
            scale="5-100",
            precision=0,
            sentinels=frozenset({999.0, -99.0, -999.0}),
            aliases=frozenset({"csr2", "iowa corn suitability rating csr2"}),
        ),
        "cpi": SdvRatingSpec(
            spec_id="cpi",
            provenance_id="SDA:COMPONENT_CROPPRODINDEX",
            attributename="Crop Productivity Index",
            table="component",
            column="cropprodindex",
            value_column="cropprodindex",
            rule_name="",
            algorithm="Weighted Average",
            horizon_method="Weighted Average",
            depth_top_cm=None,
            depth_bottom_cm=None,
            tiebreak_rule=1,
            nulls_as_zero=True,
            required_constraints=(),
            scale="1-100",
            precision=0,
            sentinels=frozenset({999.0, -99.0, -999.0}),
            aliases=frozenset({"cpi", "crop productivity index"}),
        ),
        "aws_0_100": SdvRatingSpec(
            spec_id="aws_0_100",
            provenance_id="SDA:CHORIZON_AWC_R_0_100",
            attributename="Available Water Storage",
            table="chorizon",
            column="awc_r",
            value_column="awc_r",
            rule_name="",
            algorithm="Weighted Average",
            horizon_method="Weighted Sum",
            depth_top_cm=0.0,
            depth_bottom_cm=100.0,
            tiebreak_rule=1,
            nulls_as_zero=False,
            required_constraints=(),
            scale="0-100 cm",
            precision=3,
            sentinels=frozenset(),
            aliases=frozenset(),
        ),
        "nonirr_crop_yield": SdvRatingSpec(
            spec_id="nonirr_crop_yield",
            provenance_id="SDA:COCROPYLD_NONIRRYIELD_R",
            attributename="Yields of Non-Irrigated Crops (Component)",
            table="cocropyld",
            column="nonirryield_r",
            value_column="nonirryield_r",
            rule_name="",
            algorithm="Weighted Average",
            horizon_method="Weighted Average",
            depth_top_cm=None,
            depth_bottom_cm=None,
            tiebreak_rule=1,
            nulls_as_zero=True,
            required_constraints=("cropname",),
            scale="varies",
            precision=2,
            sentinels=frozenset(),
            aliases=frozenset(),
        ),
    }
)

# ---------------------------------------------------------------------------
# Derived public constants (single source of truth = the registry)
# ---------------------------------------------------------------------------

_PUBLIC_SELECTOR_IDS = ("nccpi", "csr2", "cpi", "storie")

PRODUCTIVITY_PROVENANCE = {
    spec_id: SDV_RATING_REGISTRY[spec_id].provenance_id for spec_id in _PUBLIC_SELECTOR_IDS
}

PRODUCTIVITY_SEMANTICS = {
    spec_id: {
        "aliases": SDV_RATING_REGISTRY[spec_id].aliases,
        "scale": SDV_RATING_REGISTRY[spec_id].scale,
        "precision": SDV_RATING_REGISTRY[spec_id].precision,
        "sentinels": SDV_RATING_REGISTRY[spec_id].sentinels,
        "provenance": SDV_RATING_REGISTRY[spec_id].provenance_id,
    }
    for spec_id in _PUBLIC_SELECTOR_IDS
}

# ---------------------------------------------------------------------------
# Caveat catalogue (D8)
# ---------------------------------------------------------------------------

SDV_CAVEATS = {
    "dominant_condition": "Rating uses Dominant Condition aggregation.",
    "unrated_sentinel": "Map unit contains unrated placeholder/sentinel code ({value}).",
    "no_coverage": "Map unit has 0% rated component coverage.",
    "no_rating": "Map unit has no numeric productivity rating.",
    "partial_rating": "Partially rated map unit: {rated}% rated out of {total}% total component coverage.",
    "mixed_units": "Mixed yield units: {min_unit} and {max_unit}.",
    "aws_fixed_depth": "Available water storage computed for fixed depth range 0-100 cm.",
    "crop_specific": "Crop-specific yield for '{crop}'.",
    "not_found": "Map unit not found in SDA query results.",
    "unparseable": "Unparseable rating value '{value}'.",
}

_NULLS_AS_ZERO_TABLES = frozenset({"cocropyld", "component"})

# Tables with at least one registry record; derived so it cannot drift from the
# registry. A fast early check only: resolve_sdv_spec still rejects any record
# that is not registered.
ALLOWED_SDV_TABLES = frozenset(spec.table for spec in SDV_RATING_REGISTRY.values())


def _build_sdv_provenance(
    spec: SdvRatingSpec, constraints: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    """Build the internal structured provenance record for a registry spec (D8).

    Crop yield records also carry ``cropname`` and ``yldunits`` (the latter is
    filled per map unit by the caller).
    """
    record: dict[str, Any] = {
        "id": spec.provenance_id,
        "registry_version": SDV_REGISTRY_VERSION,
        "spec_id": spec.spec_id,
        "attributename": spec.attributename,
        "table": spec.table,
        "column": spec.column,
        "value_column": spec.value_column,
        "rule_name": spec.rule_name,
        "algorithm": spec.algorithm,
        "horizon_method": spec.horizon_method,
        "depth_top_cm": spec.depth_top_cm,
        "depth_bottom_cm": spec.depth_bottom_cm,
        "tiebreak_rule": spec.tiebreak_rule,
        "nulls_as_zero": spec.nulls_as_zero,
        # The SDV flag is recorded as published; the engine applies it only for
        # tables in _NULLS_AS_ZERO_TABLES.
        "null_handling": (
            "nulls_as_zero"
            if spec.nulls_as_zero and spec.table in _NULLS_AS_ZERO_TABLES
            else "exclude_nulls"
        ),
        "scale": spec.scale,
        "precision": spec.precision,
    }
    if "cropname" in spec.required_constraints:
        record["cropname"] = (constraints or {}).get("cropname")
        record["yldunits"] = None
    return record


def _normalize_sdv_string(value: Any) -> str:
    """Normalize an sdvattribute field to a stripped string (empty for None)."""
    if value is None:
        return ""
    return str(value).strip()


def validate_sdv_record(record: Mapping[str, Any]) -> SdvRatingSpec:
    """Validate an sdvattribute record against the registry (two-gate).

    Gate 1: match on normalized attributename, table, column, and rule name.
    Gate 2: structural checks (required fields, supported algorithm, method
    fields equal the spec).

    Returns the matching SdvRatingSpec on success.
    Raises SDAValidationError with distinct messages for each failure mode.
    """
    attr_name = _normalize_sdv_string(record.get("attributename")).lower()
    table = _normalize_sdv_string(record.get("attributetablename")).lower()
    column = _normalize_sdv_string(record.get("attributecolumnname")).lower()
    rule = _normalize_sdv_string(record.get("nasisrulename")).lower()

    # Gate 1: registry match
    matched_spec: SdvRatingSpec | None = None
    for spec in SDV_RATING_REGISTRY.values():
        if (
            spec.attributename.lower() == attr_name
            and spec.table.lower() == table
            and spec.column.lower() == column
            and spec.rule_name.lower() == rule
        ):
            matched_spec = spec
            break

    if matched_spec is None:
        raise SDAValidationError(
            f"Unregistered SDV record: attributename='{attr_name}', "
            f"table='{table}', column='{column}', rule='{rule}'."
        )

    # Gate 2: structural validation
    algorithm = _normalize_sdv_string(record.get("algorithmname"))
    if algorithm not in SUPPORTED_SDV_ALGORITHMS:
        raise SDAValidationError(
            f"Unsupported aggregation method: '{algorithm}'. "
            f"Supported: {sorted(SUPPORTED_SDV_ALGORITHMS)}."
        )

    if algorithm != matched_spec.algorithm:
        raise SDAValidationError(
            f"Malformed SDV record: algorithmname '{algorithm}' "
            f"does not match registry value '{matched_spec.algorithm}' "
            f"for {matched_spec.spec_id}."
        )

    # Table must be a known strategy table
    if table not in _SDV_STRATEGY_TABLES:
        raise SDAValidationError(
            f"Malformed SDV record: table '{table}' is not a supported strategy table."
        )

    # Identifier columns must match identifier pattern
    for col_name in ("attributetablename", "attributecolumnname"):
        col_val = _normalize_sdv_string(record.get(col_name))
        if not re.fullmatch(r"[a-z_][a-z0-9_]*", col_val.lower()):
            raise SDAValidationError(
                f"Malformed SDV record: {col_name} '{col_val}' does not match identifier pattern."
            )

    # Horizon method check for chorizon
    horizon_method = _normalize_sdv_string(record.get("horzaggmeth"))
    if table == "chorizon":
        if horizon_method not in SUPPORTED_HORIZON_METHODS:
            raise SDAValidationError(
                f"Unsupported horizon method: '{horizon_method}'. "
                f"Supported: {sorted(SUPPORTED_HORIZON_METHODS)}."
            )
        if horizon_method != matched_spec.horizon_method:
            raise SDAValidationError(
                f"Malformed SDV record: horzaggmeth '{horizon_method}' "
                f"does not match registry value '{matched_spec.horizon_method}'."
            )

    # Tiebreak rule check
    tiebreak = record.get("tiebreakrule")
    if tiebreak is not None:
        try:
            tiebreak_int = int(tiebreak)
        except (ValueError, TypeError):
            raise SDAValidationError(
                f"Malformed SDV record: tiebreakrule '{tiebreak}' is not an integer."
            )
        if tiebreak_int != matched_spec.tiebreak_rule:
            raise SDAValidationError(
                f"Malformed SDV record: tiebreakrule {tiebreak_int} "
                f"does not match registry value {matched_spec.tiebreak_rule}."
            )

    return matched_spec


_CROP_RE = re.compile(r"^[A-Za-z0-9 ,()\-/'.]{1,80}$")


def _validate_crop(cropname: str) -> str:
    """Validate a crop name for SQL interpolation."""
    crop = str(cropname).strip()
    if not crop:
        raise SDAValidationError("Crop name is required for this rating.")
    if ";" in crop or "--" in crop:
        raise SDAValidationError(f"Invalid characters in crop name: '{cropname}'.")
    if not _CROP_RE.fullmatch(crop):
        raise SDAValidationError(f"Invalid crop name: '{cropname}'.")
    return crop


def resolve_sdv_spec(
    selector: str | None = None,
    record: Mapping[str, Any] | None = None,
    constraints: Mapping[str, Any] | None = None,
) -> tuple[SdvRatingSpec, dict[str, Any]]:
    """Resolve a rating specification from a selector or raw record.

    Exactly one of *selector* or *record* must be provided.

    - *selector* resolves via exact alias match against the registry.
    - *record* goes through validate_sdv_record (two-gate validation).

    Required constraints (e.g. cropname) are validated and returned in the
    resolved constraints dict.
    """
    if selector is not None and record is not None:
        raise SDAValidationError("Provide either a selector or a record, not both.")
    if selector is None and record is None:
        raise SDAValidationError("A selector or an SDV record is required.")

    if selector is not None:
        sel_lower = str(selector).strip().lower()
        spec: SdvRatingSpec | None = None
        for candidate_id, candidate_spec in SDV_RATING_REGISTRY.items():
            if sel_lower == candidate_id or sel_lower in candidate_spec.aliases:
                spec = candidate_spec
                break
        if spec is None:
            raise SDAValidationError(f"Unregistered SDV selector: '{selector}'.")
    else:
        assert record is not None
        spec = validate_sdv_record(record)

    resolved_constraints: dict[str, Any] = {}
    if constraints:
        for key, val in constraints.items():
            resolved_constraints[key] = val

    for req in spec.required_constraints:
        if req == "cropname":
            crop = resolved_constraints.get("cropname")
            if crop is None:
                raise SDAValidationError(f"Constraint '{req}' is required for {spec.spec_id}.")
            resolved_constraints["cropname"] = _validate_crop(crop)
        elif req not in resolved_constraints:
            raise SDAValidationError(f"Constraint '{req}' is required for {spec.spec_id}.")

    return spec, resolved_constraints


def _normalize_productivity_index(index_type: str) -> str:
    """Normalize a public fixed selector (nccpi, csr2, cpi, storie) by exact alias (D1)."""
    selector = str(index_type).strip().lower()
    for normalized, semantics in PRODUCTIVITY_SEMANTICS.items():
        if selector in semantics["aliases"]:
            return normalized
    raise SDAValidationError(
        f"Unsupported productivity index type '{index_type}'. "
        f"{SUPPORTED_INDEX_MSG} "
        "Explicit attribute metadata is required for custom SDV queries."
    )


def _record_constraints(
    attribute_meta: Mapping[str, Any] | None,
    constraints: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Merge explicit constraints with a legacy ``cropname`` key on the record."""
    merged: dict[str, Any] = {}
    if attribute_meta and attribute_meta.get("cropname"):
        merged["cropname"] = attribute_meta["cropname"]
    if constraints:
        merged.update(constraints)
    return merged or None


def _resolve_productivity_spec(
    index_type: str,
    attribute_meta: Mapping[str, Any] | None,
    constraints: Mapping[str, Any] | None,
) -> tuple[SdvRatingSpec, dict[str, Any]]:
    """Resolve the client entry points to one registry spec (one engine, D9).

    ``attribute_meta`` (explicit metadata selection) takes precedence; otherwise
    ``index_type`` must be one of the four public fixed selectors (D1).
    """
    if attribute_meta:
        return resolve_sdv_spec(
            record=attribute_meta,
            constraints=_record_constraints(attribute_meta, constraints),
        )
    selector = _normalize_productivity_index(index_type)
    return resolve_sdv_spec(selector=selector, constraints=constraints)
