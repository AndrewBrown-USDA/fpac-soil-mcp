"""Live integration tests for USDA NRCS Soil Data Access (SDA) API.

Tests real network queries against SDA Tabular REST endpoint.
Opt-in via: pytest -m live_network
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

import httpx
import pytest

from fpac_soil_mcp.sda_client import (
    SDV_CONTRACT_FIELDS,
    SDAClient,
    SDAClientError,
    SDAQueryError,
    SDAValidationError,
    validate_sdv_record,
)

pytestmark = pytest.mark.live_network

_FIXTURES = Path(__file__).parent / "fixtures"
_CASES = json.loads((_FIXTURES / "sdv_contract_cases.json").read_text(encoding="utf-8"))["cases"]
_RECORDS = {
    r["attributename"]: r
    for r in json.loads((_FIXTURES / "sdv_attribute_records.json").read_text(encoding="utf-8"))[
        "records"
    ]
}
_BENCHMARKS = [c for c in _CASES if "live_benchmark" in c]
_VALUE_BENCHMARKS = [c for c in _BENCHMARKS if "mukeys" in c["live_benchmark"]]
_MAX_BENCHMARKS = [c for c in _BENCHMARKS if "county_max" in c["live_benchmark"]]
_MIXED_UNITS_PREFIX = "Mixed yield units"

_T = TypeVar("_T")


def _live(call: Callable[[], _T]) -> _T:
    """Run a live call; skip only on network/SDA availability errors, never on validation."""
    try:
        return call()
    except (SDAQueryError, httpx.HTTPError) as exc:
        pytest.skip(f"Live SDA endpoint unavailable or timed out: {exc}")


def _engine_kwargs(case: dict[str, Any]) -> dict[str, Any]:
    """Fixed selector when the benchmark names one, else the captured sdvattribute record."""
    selector = case["live_benchmark"]["selector"]
    if selector:
        return {"index_type": selector}
    kwargs: dict[str, Any] = {"attribute_meta": dict(_RECORDS[case["attributename"]])}
    if case["constraints"]:
        kwargs["constraints"] = dict(case["constraints"])
    return kwargs


def _norm(value: Any) -> str:
    """Compare SDA string output with captured values (numbers as floats, None as empty)."""
    if value is None:
        return ""
    text = str(value).strip()
    try:
        return repr(float(text))
    except ValueError:
        return text


def _area_mukeys(client: SDAClient, areasymbol: str) -> list[str]:
    query = (
        "SELECT m.mukey FROM legend AS l INNER JOIN mapunit AS m ON m.lkey = l.lkey "
        f"WHERE l.areasymbol = '{areasymbol}' ORDER BY m.mukey"
    )
    return [str(r["mukey"]) for r in _live(lambda: client._execute_query(query))]


@pytest.mark.parametrize("case", _BENCHMARKS, ids=[c["id"] for c in _BENCHMARKS])
def test_live_sdv_record_matches_capture(case: dict[str, Any]) -> None:
    """Drift guard: the live sdvattribute record still equals the capture and validates."""
    captured = _RECORDS[case["attributename"]]
    client = SDAClient()
    rows = _live(lambda: client.lookup_sdv_attribute(case["attributename"]))
    live = [
        r
        for r in rows
        if _norm(r.get("attributename")) == _norm(captured["attributename"])
        and _norm(r.get("nasisrulename")) == _norm(captured.get("nasisrulename"))
    ]
    assert len(live) == 1, f"expected one live record for {case['attributename']}, got {len(live)}"
    drift = {
        f: (captured.get(f), live[0].get(f))
        for f in SDV_CONTRACT_FIELDS
        if _norm(captured.get(f)) != _norm(live[0].get(f))
    }
    assert not drift, f"sdvattribute drift for {case['id']}: {drift}"
    assert validate_sdv_record(live[0]).spec_id == case["id"]


@pytest.mark.parametrize("case", _MAX_BENCHMARKS, ids=[c["id"] for c in _MAX_BENCHMARKS])
def test_live_sdv_county_max_benchmark(case: dict[str, Any]) -> None:
    """County maximum stays within the recorded tolerance of the 39.1.1 benchmark."""
    bench = case["live_benchmark"]
    client = SDAClient()
    max_val = _live(
        lambda: client.get_county_max_productivity_rating(
            areasymbol=bench["areasymbol"], **_engine_kwargs(case)
        )
    )
    assert max_val is not None
    assert abs(max_val - bench["county_max"]) <= bench["tolerance"]


@pytest.mark.parametrize("case", _VALUE_BENCHMARKS, ids=[c["id"] for c in _VALUE_BENCHMARKS])
def test_live_sdv_sample_mukey_benchmarks(case: dict[str, Any]) -> None:
    """Sample map unit values, source ID, and spec stay within the recorded tolerance."""
    bench = case["live_benchmark"]
    expected = bench["mukeys"]
    client = SDAClient()
    rows = _live(
        lambda: client.get_productivity_ratings(mukeys=list(expected), **_engine_kwargs(case))
    )
    by_mukey = {r["mukey"]: r for r in rows}
    assert set(by_mukey) == set(expected)
    for mukey, value in expected.items():
        row = by_mukey[mukey]
        assert row["is_rated"], f"{case['id']} {mukey} unrated: {row['caveats']}"
        assert abs(row["numeric_rating"] - value) <= bench["tolerance"], (
            f"{case['id']} {mukey}: live {row['numeric_rating']} vs benchmark {value}"
        )
        assert row["spec_id"] == case["id"]
        assert row["productivity_rating_source"] == case["expected_productivity_rating_source"]
        if case["id"] == "storie":
            assert "Rating uses Dominant Condition aggregation." in row["caveats"]
        if "expected_yldunits" in bench:
            assert row["sdv_provenance"]["yldunits"] == bench["expected_yldunits"]


def test_live_storie_dominant_condition_differs_from_legacy_weighted_average() -> None:
    """Storie now follows Dominant Condition: per-mukey values match the new, not the old, method."""
    case = next(c for c in _CASES if c["id"] == "storie")
    bench = case["live_benchmark"]
    client = SDAClient()
    rows = _live(
        lambda: client.get_productivity_ratings(mukeys=list(bench["mukeys"]), index_type="storie")
    )
    for row in rows:
        old = bench["legacy_weighted_average"][row["mukey"]]
        new = bench["mukeys"][row["mukey"]]
        assert abs(row["numeric_rating"] - new) <= bench["tolerance"]
        assert abs(row["numeric_rating"] - old) > bench["tolerance"]


def test_live_aws_0_100_matches_muaggatt_aws0100wta() -> None:
    """D6/D11: AWS 0-100 cm agrees with muaggatt.aws0100wta on a county sample."""
    case = next(c for c in _CASES if c["id"] == "aws_0_100")
    bench = case["live_benchmark"]
    check = bench["muaggatt_cross_check"]
    client = SDAClient()
    query = (
        f"SELECT TOP {int(check['sample_size'])} m.mukey, ma.{check['column']} AS reference "
        "FROM legend AS l INNER JOIN mapunit AS m ON m.lkey = l.lkey "
        "INNER JOIN muaggatt AS ma ON ma.mukey = m.mukey "
        f"WHERE l.areasymbol = '{bench['areasymbol']}' AND ma.{check['column']} IS NOT NULL "
        "ORDER BY m.mukey"
    )
    reference = {
        str(r["mukey"]): float(r["reference"]) for r in _live(lambda: client._execute_query(query))
    }
    rows = _live(
        lambda: client.get_productivity_ratings(mukeys=list(reference), **_engine_kwargs(case))
    )
    compared = [r for r in rows if r["is_rated"]]
    assert len(compared) >= check["min_compared"]
    mismatches = [
        (r["mukey"], r["numeric_rating"], reference[r["mukey"]])
        for r in compared
        if abs(r["numeric_rating"] - reference[r["mukey"]]) > check["max_diff_cm"]
    ]
    assert len(mismatches) / len(compared) <= check["max_mismatch_fraction"], mismatches
    for row in compared:
        assert "Available water storage computed for fixed depth range 0-100 cm." in row["caveats"]


def test_live_corn_yield_mixed_units_are_unrated() -> None:
    """D7: across the county, mixed-unit map units are unrated and rare; others carry one unit."""
    case = next(c for c in _CASES if c["id"] == "nonirr_crop_yield")
    bench = case["live_benchmark"]
    client = SDAClient()
    mukeys = _area_mukeys(client, bench["areasymbol"])
    assert mukeys
    rows = _live(lambda: client.get_productivity_ratings(mukeys=mukeys, **_engine_kwargs(case)))
    with_crop = [r for r in rows if not r["caveats"] or "not found" not in r["caveats"][0]]
    assert with_crop
    mixed = [r for r in with_crop if any(c.startswith(_MIXED_UNITS_PREFIX) for c in r["caveats"])]
    for row in mixed:
        assert row["is_rated"] is False
        assert row["numeric_rating"] is None
        assert row["sdv_provenance"]["yldunits"] is None
    for row in with_crop:
        if row["is_rated"]:
            assert row["sdv_provenance"]["yldunits"] == bench["expected_yldunits"]
            assert row["sdv_provenance"]["cropname"] == "Corn"
    assert len(mixed) / len(with_crop) <= bench["max_mixed_unit_fraction"]


def test_live_cpi_nulls_as_zero_keeps_unpopulated_map_units_unrated() -> None:
    """D12: CPI nulls count as zero only beside rated components; MN053 has no CPI data."""
    client = SDAClient()
    mukeys = _area_mukeys(client, "MN053")[:40]
    assert mukeys
    rows = _live(lambda: client.get_productivity_ratings(mukeys=mukeys, index_type="cpi"))
    assert rows
    for row in rows:
        assert row["is_rated"] is False
        assert row["numeric_rating"] is None
        assert row["sdv_provenance"]["null_handling"] == "nulls_as_zero"


class TestLiveSDA:
    """Live integration tests hitting live SDA web services."""

    def test_live_point_lookup_prime_farmland(self) -> None:
        """Query known prime farmland coordinate in Story County, IA (Clarion / Webster soils)."""
        client = SDAClient()
        try:
            results = client.get_by_point(latitude=42.0308, longitude=-93.6319)
        except (SDAClientError, httpx.HTTPError) as exc:
            pytest.skip(f"Live SDA endpoint unavailable or timed out: {exc}")

        assert len(results) >= 1
        res = results[0]
        assert "mukey" in res
        assert "musym" in res
        assert "muname" in res
        assert "farmlndcl" in res
        assert res.get("areasymbol") == "IA169"

    def test_live_spatial_intersection_clipping(self) -> None:
        """Query real 100m square polygon in Iowa and test STIntersection clipped acreage."""
        client = SDAClient()
        wkt_polygon = "POLYGON((-93.632 42.030, -93.630 42.030, -93.630 42.032, -93.632 42.032, -93.632 42.030))"
        try:
            results = client.get_spatial_intersection(
                wkt_polygon, clip=True, geom_acres=True, return_geom=False
            )
        except (SDAClientError, httpx.HTTPError) as exc:
            pytest.skip(f"Live SDA endpoint unavailable or timed out: {exc}")

        assert len(results) >= 1
        for row in results:
            assert "mukey" in row
            assert "musym" in row
            assert "muname" in row
            assert "area_ac" in row
            assert float(row["area_ac"]) > 0.0

    def test_live_interpretation_nccpi_v3(self) -> None:
        """Query live NCCPI v3 interpretation for known map unit."""
        client = SDAClient()
        try:
            # First lookup real mukey from point
            pt_res = client.get_by_point(latitude=42.0308, longitude=-93.6319)
            if not pt_res or not pt_res[0].get("mukey"):
                pytest.skip("Could not fetch test mukey from point")
            test_mukey = str(pt_res[0]["mukey"])

            results = client.get_interpretations(
                mukeys=[test_mukey],
                rule_name="NCCPI - National Commodity Crop Productivity Index (Ver 3.0)",
                aggregation_method="Weighted Average",
            )
        except (SDAClientError, httpx.HTTPError) as exc:
            pytest.skip(f"Live SDA endpoint unavailable or timed out: {exc}")

        assert len(results) >= 1
        res = results[0]
        assert "mukey" in res
        assert res.get("mukey") == test_mukey
        assert res.get("numeric_rating") is not None

    def test_live_cointerp_rule_catalog(self) -> None:
        """Query live cointerp rule catalog from sdvattribute metadata table."""
        client = SDAClient()
        try:
            rules = client.get_available_interpretation_rules(refresh=True)
        except (SDAClientError, httpx.HTTPError) as exc:
            pytest.skip(f"Live SDA endpoint unavailable or timed out: {exc}")

        assert "NCCPI - National Commodity Crop Productivity Index (Ver 3.0)" in rules

    def test_fixed_selector_rejects_unsupported_value(self) -> None:
        """The public fixed selector rejects unsupported values."""
        client = SDAClient()
        with pytest.raises(SDAValidationError, match="Unsupported productivity index type"):
            client.get_productivity_ratings(mukeys=["402001"], index_type="unsupported")

    def test_live_geometry_extraction(self) -> None:
        """Query live geometry extraction returning WKT polygon shapes."""
        client = SDAClient()
        wkt_polygon = "POLYGON((-93.632 42.030, -93.630 42.030, -93.630 42.032, -93.632 42.032, -93.632 42.030))"
        try:
            results = client.get_spatial_intersection(
                wkt_polygon, clip=True, geom_acres=True, return_geom=True
            )
        except (SDAClientError, httpx.HTTPError) as exc:
            pytest.skip(f"Live SDA endpoint unavailable or timed out: {exc}")

        assert len(results) >= 1
        for row in results:
            assert "geom" in row
            assert row["geom"].startswith(("POLYGON", "MULTIPOLYGON"))

    def test_live_dynamic_sdv_queries_and_unrated_water_urban(self) -> None:
        """Verify dynamic SDV query generation on live SDA with real attribute metadata."""
        client = SDAClient()
        # Query water/urban area (e.g. Lake Michigan coordinates near Chicago: 41.90, -87.60)
        water_pts = client.get_by_point(latitude=41.9000, longitude=-87.6000)
        if water_pts and water_pts[0].get("mukey"):
            water_mukey = str(water_pts[0]["mukey"])
            nccpi_res = client.get_interpretations(
                mukeys=[water_mukey],
                rule_name="NCCPI - National Commodity Crop Productivity Index (Ver 3.0)",
            )
            if nccpi_res:
                # In water/urban land, numeric rating is None or sentinel (99/999)
                assert nccpi_res[0].get("numeric_rating") is None or nccpi_res[0].get(
                    "numeric_rating"
                ) in (99, 999, 99.0, 999.0)

        # Query dynamic SDV county maximum for NCCPI in Iowa
        max_val = client.get_county_max_productivity_rating(areasymbol="IA169", index_type="nccpi")
        assert max_val is not None
        assert max_val > 0.0

    def test_live_csr2_productivity_ratings_iowa(self) -> None:
        """Query CSR2 (mapunit.iacornsr) for known Iowa mukeys — Story County, IA."""
        client = SDAClient()
        try:
            pt_res = client.get_by_point(latitude=42.0308, longitude=-93.6319)
            if not pt_res or not pt_res[0].get("mukey"):
                pytest.skip("Could not fetch test mukey from point")
            test_mukey = str(pt_res[0]["mukey"])

            results = client.get_productivity_ratings(mukeys=[test_mukey], index_type="csr2")
        except (SDAClientError, httpx.HTTPError) as exc:
            pytest.skip(f"Live SDA endpoint unavailable or timed out: {exc}")

        assert len(results) == 1
        res = results[0]
        assert res["index_type"] == "csr2"
        assert res["productivity_rating_source"] == "SDA:MAPUNIT_IACORNSR"
        # Iowa soils should have CSR2 values in range 5-100
        if res["is_rated"]:
            assert 5 <= res["numeric_rating"] <= 100

    def test_live_csr2_county_max_iowa(self) -> None:
        """CSR2 county max for IA169 (Story County) — research found max=96."""
        client = SDAClient()
        try:
            max_val = client.get_county_max_productivity_rating(
                areasymbol="IA169", index_type="csr2"
            )
        except (SDAClientError, httpx.HTTPError) as exc:
            pytest.skip(f"Live SDA endpoint unavailable or timed out: {exc}")

        assert max_val is not None
        assert 90 <= max_val <= 100  # known IA169 max is 96

    def test_live_csr2_county_max_non_iowa_is_null(self) -> None:
        """CSR2 should return None for non-Iowa counties (iacornsr is Iowa-only)."""
        client = SDAClient()
        try:
            max_val = client.get_county_max_productivity_rating(
                areasymbol="IL019", index_type="csr2"
            )
        except (SDAClientError, httpx.HTTPError) as exc:
            pytest.skip(f"Live SDA endpoint unavailable or timed out: {exc}")

        assert max_val is None

    def test_live_cpi_county_max_minnesota(self) -> None:
        """CPI county max for MN167 (Wilkin County) — research found max=100."""
        client = SDAClient()
        try:
            max_val = client.get_county_max_productivity_rating(
                areasymbol="MN167", index_type="cpi"
            )
        except (SDAClientError, httpx.HTTPError) as exc:
            pytest.skip(f"Live SDA endpoint unavailable or timed out: {exc}")

        assert max_val is not None
        # Research found MN167 max=100
        assert 90 <= max_val <= 100

    def test_live_cpi_productivity_ratings_minnesota(self) -> None:
        """Query CPI (component.cropprodindex) for a real Wilkin County mukey."""
        client = SDAClient()
        try:
            pt_res = client.get_by_point(latitude=46.28, longitude=-96.58)
            if not pt_res or not pt_res[0].get("mukey"):
                pytest.skip("Could not fetch test mukey from point")
            test_mukey = str(pt_res[0]["mukey"])

            results = client.get_productivity_ratings(mukeys=[test_mukey], index_type="cpi")
        except (SDAClientError, httpx.HTTPError) as exc:
            pytest.skip(f"Live SDA endpoint unavailable or timed out: {exc}")

        assert len(results) == 1
        res = results[0]
        assert res["index_type"] == "cpi"
        assert res["productivity_rating_source"] == "SDA:COMPONENT_CROPPRODINDEX"
        if res["is_rated"]:
            assert 0 < res["numeric_rating"] <= 100

    def test_live_cpi_county_max_non_populated_county(self) -> None:
        """CPI may be NULL in metro MN counties (e.g. Hennepin MN053)."""
        client = SDAClient()
        try:
            max_val = client.get_county_max_productivity_rating(
                areasymbol="MN053", index_type="cpi"
            )
        except (SDAClientError, httpx.HTTPError) as exc:
            pytest.skip(f"Live SDA endpoint unavailable or timed out: {exc}")

        # MN053 (Hennepin) may have no CPI data
        # If it returns something, it should be in valid range
        if max_val is not None:
            assert 0 < max_val <= 100

    def test_live_cpi_county_max_non_mn_is_null(self) -> None:
        """CPI should return None for non-MN/ND/SD counties."""
        client = SDAClient()
        try:
            max_val = client.get_county_max_productivity_rating(
                areasymbol="CA077", index_type="cpi"
            )
        except (SDAClientError, httpx.HTTPError) as exc:
            pytest.skip(f"Live SDA endpoint unavailable or timed out: {exc}")

        assert max_val is None

    def test_live_storie_county_max_california(self) -> None:
        """Storie county max for CA077 (San Joaquin) — research found max ~0.995."""
        client = SDAClient()
        try:
            max_val = client.get_county_max_productivity_rating(
                areasymbol="CA077", index_type="storie"
            )
        except (SDAClientError, httpx.HTTPError) as exc:
            pytest.skip(f"Live SDA endpoint unavailable or timed out: {exc}")

        assert max_val is not None
        # Dominant Condition county max; unchanged from the old weighted method (STATE_39 39.5.1)
        assert abs(max_val - 0.995) <= 0.003

    def test_live_storie_county_max_non_ca_is_null(self) -> None:
        """Storie should return None for non-California counties."""
        client = SDAClient()
        try:
            max_val = client.get_county_max_productivity_rating(
                areasymbol="IA169", index_type="storie"
            )
        except (SDAClientError, httpx.HTTPError) as exc:
            pytest.skip(f"Live SDA endpoint unavailable or timed out: {exc}")

        assert max_val is None

    def test_live_storie_ratings_california(self) -> None:
        """Query Storie ratings for a known CA077 mukey."""
        client = SDAClient()
        try:
            # Use a known San Joaquin County point to get a CA mukey
            pt_res = client.get_by_point(latitude=37.95, longitude=-121.29)
            if not pt_res or not pt_res[0].get("mukey"):
                pytest.skip("Could not fetch test mukey from CA point")
            test_mukey = str(pt_res[0]["mukey"])

            results = client.get_productivity_ratings(mukeys=[test_mukey], index_type="storie")
        except (SDAClientError, httpx.HTTPError) as exc:
            pytest.skip(f"Live SDA endpoint unavailable or timed out: {exc}")

        assert len(results) == 1
        res = results[0]
        assert res["index_type"] == "storie"
        assert res["productivity_rating_source"] == "SDA:COINTERP_STORIE_CA"
        assert res["algorithm"] == "Dominant Condition"
        assert "Rating uses Dominant Condition aggregation." in res["caveats"]
        if res["is_rated"]:
            assert 0 < res["numeric_rating"] <= 1.0
