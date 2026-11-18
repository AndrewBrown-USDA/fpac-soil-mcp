"""NCCPI national baseline: supplementary per-map-unit productivity context.

NCCPI v3 is the only nationally applicable, cross-state-comparable productivity
index, so every polygon and corridor analysis reports it per map unit next to the
primary ``productivity_index``. The baseline never feeds Land Evaluation scoring.
Missing, sentinel, or unparseable ratings are reported as ``None``, never as 0.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from typing import Any

from fpac_soil_mcp.clients.sda import SDAClient, SDAClientError
from fpac_soil_mcp.clients.sda.sdv_registry import SDV_RATING_REGISTRY

_NCCPI_SPEC = SDV_RATING_REGISTRY["nccpi"]
NCCPI_BASELINE_RULE = _NCCPI_SPEC.rule_name
_NCCPI_SENTINELS = _NCCPI_SPEC.sentinels

NCCPI_BASELINE_FIELDS: tuple[str, ...] = (
    "nccpi_baseline_rating",
    "nccpi_baseline_rating_class",
    "nccpi_baseline_rating_source",
    "nccpi_baseline_coverage_status",
    "nccpi_baseline_rated_pct",
    "nccpi_baseline_total_pct",
)
"""``SoilMapUnitAcreage`` field names populated by :func:`nccpi_baseline_fields`."""


def fetch_nccpi_baseline(
    sda_client: SDAClient,
    mukeys: Iterable[str],
    *,
    primary_index: str,
    primary_rows: Mapping[str, Mapping[str, Any]],
) -> tuple[dict[str, dict[str, Any]], str | None]:
    """Return NCCPI rows keyed by mukey plus an optional limitation message.

    When the primary index is NCCPI, the already-fetched ``primary_rows`` are
    reused and SDA is not called again. Otherwise one weighted-average NCCPI
    interpretation query runs for ``mukeys``. An SDA failure yields no rows and a
    limitation; the caller's primary ratings are unaffected.
    """
    keys = [str(mukey) for mukey in mukeys if mukey]
    if not keys:
        return {}, None
    if primary_index.strip().lower() == "nccpi":
        return {k: dict(primary_rows[k]) for k in keys if k in primary_rows}, None
    try:
        rows = sda_client.get_interpretations(
            mukeys=keys,
            rule_name=NCCPI_BASELINE_RULE,
            aggregation_method="Weighted Average",
        )
    except SDAClientError as exc:
        return {}, f"NCCPI national baseline unavailable: {exc}"
    return {str(row.get("mukey")): dict(row) for row in rows if row.get("mukey")}, None


def _finite_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def nccpi_baseline_fields(row: Mapping[str, Any] | None) -> dict[str, Any]:
    """Map one NCCPI row to the ``SoilMapUnitAcreage`` baseline fields.

    No row gives all ``None``. A row whose rating is missing, unparseable, or an
    unrated sentinel (e.g. a miscellaneous non-soil map unit) keeps rating and
    class ``None`` and reports coverage ``'unrated'``.
    """
    if row is None:
        return dict.fromkeys(NCCPI_BASELINE_FIELDS)
    rating = _finite_float(row.get("numeric_rating"))
    if rating is not None and rating in _NCCPI_SENTINELS:
        rating = None
    rated_pct = _finite_float(row.get("rated_pct"))
    total_pct = _finite_float(row.get("total_pct"))
    if rating is None:
        coverage = "unrated"
    elif rated_pct is not None and total_pct is not None and rated_pct < total_pct:
        coverage = "partial"
    else:
        coverage = "rated"
    rating_class = row.get("rating_class") if rating is not None else None
    return {
        "nccpi_baseline_rating": rating,
        "nccpi_baseline_rating_class": str(rating_class) if rating_class else None,
        "nccpi_baseline_rating_source": row.get("productivity_rating_source")
        or NCCPI_BASELINE_RULE,
        "nccpi_baseline_coverage_status": coverage,
        "nccpi_baseline_rated_pct": rated_pct,
        "nccpi_baseline_total_pct": total_pct,
    }
