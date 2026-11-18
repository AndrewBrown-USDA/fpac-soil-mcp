"""Tests for the NCCPI national baseline helper and model fields."""

from __future__ import annotations

import json
from typing import Any

import pytest

from fpac_soil_mcp.clients.sda import SDAClientError
from fpac_soil_mcp.domain.nccpi_baseline import (
    NCCPI_BASELINE_FIELDS,
    NCCPI_BASELINE_RULE,
    fetch_nccpi_baseline,
    nccpi_baseline_fields,
)
from fpac_soil_mcp.models.soil import SoilMapUnitAcreage


class FakeSDA:
    """Records NCCPI interpretation calls and returns canned rows."""

    def __init__(self, rows: list[dict[str, Any]] | None = None, error: Exception | None = None):
        self.rows = rows or []
        self.error = error
        self.calls: list[dict[str, Any]] = []

    def get_interpretations(self, **kwargs: Any) -> list[dict[str, Any]]:
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return self.rows


NCCPI_ROWS = [
    {
        "mukey": "1",
        "numeric_rating": 0.72,
        "rating_class": "High",
        "rated_pct": 85,
        "total_pct": 85,
    },
    {
        "mukey": "2",
        "numeric_rating": None,
        "rating_class": "Not rated",
        "rated_pct": 0,
        "total_pct": 100,
    },
]


def test_nccpi_primary_reuses_rows_without_sda_call() -> None:
    sda = FakeSDA()
    primary = {"1": {"mukey": "1", "numeric_rating": 0.5, "rating_class": "Moderate"}}
    rows, limitation = fetch_nccpi_baseline(
        sda, ["1", "9"], primary_index="nccpi", primary_rows=primary
    )
    assert sda.calls == []
    assert limitation is None
    assert rows == {"1": primary["1"]}


@pytest.mark.parametrize("index", ["csr2", "cpi", "storie", "CSR2"])
def test_non_nccpi_primary_makes_one_nccpi_query(index: str) -> None:
    sda = FakeSDA(rows=NCCPI_ROWS)
    rows, limitation = fetch_nccpi_baseline(
        sda, ["1", "2"], primary_index=index, primary_rows={"1": {"numeric_rating": 80.0}}
    )
    assert len(sda.calls) == 1
    assert sda.calls[0]["rule_name"] == NCCPI_BASELINE_RULE
    assert sda.calls[0]["aggregation_method"] == "Weighted Average"
    assert sorted(sda.calls[0]["mukeys"]) == ["1", "2"]
    assert limitation is None
    assert rows["1"]["numeric_rating"] == 0.72


def test_empty_mukeys_skip_query() -> None:
    sda = FakeSDA(rows=NCCPI_ROWS)
    assert fetch_nccpi_baseline(sda, [], primary_index="csr2", primary_rows={}) == ({}, None)
    assert sda.calls == []


def test_sda_error_returns_limitation_and_no_rows() -> None:
    sda = FakeSDA(error=SDAClientError("SDA down"))
    rows, limitation = fetch_nccpi_baseline(sda, ["1"], primary_index="csr2", primary_rows={})
    assert rows == {}
    assert limitation == "NCCPI national baseline unavailable: SDA down"


def test_rated_row_maps_all_fields() -> None:
    fields = nccpi_baseline_fields(NCCPI_ROWS[0])
    assert fields == {
        "nccpi_baseline_rating": 0.72,
        "nccpi_baseline_rating_class": "High",
        "nccpi_baseline_rating_source": NCCPI_BASELINE_RULE,
        "nccpi_baseline_coverage_status": "rated",
        "nccpi_baseline_rated_pct": 85.0,
        "nccpi_baseline_total_pct": 85.0,
    }


def test_partial_coverage() -> None:
    fields = nccpi_baseline_fields(
        {"numeric_rating": "0.4", "rating_class": "Low", "rated_pct": 60, "total_pct": 90}
    )
    assert fields["nccpi_baseline_rating"] == 0.4
    assert fields["nccpi_baseline_coverage_status"] == "partial"


def test_miscellaneous_non_soil_unit_is_null_not_zero() -> None:
    fields = nccpi_baseline_fields(NCCPI_ROWS[1])
    assert fields["nccpi_baseline_rating"] is None
    assert fields["nccpi_baseline_rating_class"] is None
    assert fields["nccpi_baseline_coverage_status"] == "unrated"


@pytest.mark.parametrize("value", [99, 99.0, "999", -99, -999.0, "n/a", float("nan"), True])
def test_sentinel_or_unparseable_rating_is_null(value: Any) -> None:
    fields = nccpi_baseline_fields({"numeric_rating": value, "rating_class": "Not rated"})
    assert fields["nccpi_baseline_rating"] is None
    assert fields["nccpi_baseline_rating_class"] is None


def test_missing_pcts_stay_null() -> None:
    fields = nccpi_baseline_fields({"numeric_rating": 0.3, "rating_class": "Low"})
    assert fields["nccpi_baseline_rated_pct"] is None
    assert fields["nccpi_baseline_total_pct"] is None
    assert fields["nccpi_baseline_coverage_status"] == "rated"


def test_provenance_from_row_is_preserved() -> None:
    fields = nccpi_baseline_fields({"numeric_rating": 0.3, "productivity_rating_source": "SDA:X"})
    assert fields["nccpi_baseline_rating_source"] == "SDA:X"


def test_no_row_gives_all_null() -> None:
    assert nccpi_baseline_fields(None) == dict.fromkeys(NCCPI_BASELINE_FIELDS)


def test_model_fields_default_to_json_null() -> None:
    unit = SoilMapUnitAcreage(mukey="1")
    payload = json.loads(unit.model_dump_json())
    assert set(NCCPI_BASELINE_FIELDS) <= set(SoilMapUnitAcreage.model_fields)
    assert all(payload[name] is None for name in NCCPI_BASELINE_FIELDS)


def test_model_accepts_helper_output() -> None:
    unit = SoilMapUnitAcreage(mukey="2", **nccpi_baseline_fields(NCCPI_ROWS[1]))
    assert unit.nccpi_baseline_rating is None
    assert unit.nccpi_baseline_rated_pct == 0.0
    assert unit.nccpi_baseline_total_pct == 100.0
