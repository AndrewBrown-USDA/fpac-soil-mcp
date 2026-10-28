"""Tests for the SDV metadata-driven rating contract (ADR 0014)."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import httpx
import pytest

from fpac_soil_mcp import sda_client
from fpac_soil_mcp.sda_client import (
    SDV_CONTRACT_FIELDS,
    SDV_RATING_REGISTRY,
    SDV_REGISTRY_VERSION,
    SDAClient,
    SDAValidationError,
    build_sdv_county_max_query,
    build_sdv_rating_query,
    resolve_sdv_spec,
    validate_sdv_record,
)

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "sdv_attribute_records.json"
CASES_PATH = Path(__file__).parent / "fixtures" / "sdv_contract_cases.json"
_CASES = json.loads(CASES_PATH.read_text())["cases"]
_RECORDS = {r["attributename"]: r for r in json.loads(FIXTURE_PATH.read_text())["records"]}


def _sha(sql: str) -> str:
    """SHA-256 of whitespace-collapsed SQL."""
    return hashlib.sha256(" ".join(sql.split()).encode()).hexdigest()


def _canonical_sha(sql: str) -> str:
    """SHA-256 of whitespace-collapsed SQL with numeric NOT IN lists sorted."""

    def _sort(match: re.Match[str]) -> str:
        vals = sorted(float(v) for v in match.group(1).split(","))
        return "NOT IN (" + ", ".join(str(int(v)) if v.is_integer() else str(v) for v in vals) + ")"

    canon = re.sub(r"NOT IN \(([-0-9., ]+)\)", _sort, " ".join(sql.split()))
    return hashlib.sha256(canon.encode()).hexdigest()


def _mock_client(payload: dict) -> SDAClient:
    return SDAClient(
        http_client=httpx.Client(
            transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
        )
    )


def _case_inputs(case: dict) -> tuple[dict, dict | None]:
    return _RECORDS[case["attributename"]], (case["constraints"] or None)


@pytest.fixture
def fixture_records() -> list[dict]:
    """Load the live-captured sdvattribute records."""
    with FIXTURE_PATH.open() as f:
        data = json.load(f)
    return data["records"]


class TestRegistry:
    """Registry structure and value parity with PRODUCTIVITY_SEMANTICS."""

    def test_registry_version(self) -> None:
        assert SDV_REGISTRY_VERSION == "1"

    def test_registry_has_six_entries(self) -> None:
        assert len(SDV_RATING_REGISTRY) == 6

    def test_registry_keys(self) -> None:
        expected = {"nccpi", "storie", "csr2", "cpi", "aws_0_100", "nonirr_crop_yield"}
        assert set(SDV_RATING_REGISTRY) == expected

    def test_cointerp_value_column_is_interphr(self) -> None:
        """H4: attributecolumnname is interphrc but engine reads interphr."""
        for spec_id in ("nccpi", "storie"):
            spec = SDV_RATING_REGISTRY[spec_id]
            assert spec.column == "interphrc"
            assert spec.value_column == "interphr"

    def test_existing_selectors_match_productivity_semantics(self) -> None:
        from fpac_soil_mcp.sda_client import PRODUCTIVITY_SEMANTICS

        for key in ("nccpi", "csr2", "cpi", "storie"):
            spec = SDV_RATING_REGISTRY[key]
            sem = PRODUCTIVITY_SEMANTICS[key]
            assert spec.scale == sem["scale"]
            assert spec.precision == sem["precision"]
            assert spec.sentinels == sem["sentinels"]
            assert spec.aliases == sem["aliases"]

    def test_new_records_have_empty_aliases_and_sentinels(self) -> None:
        for key in ("aws_0_100", "nonirr_crop_yield"):
            spec = SDV_RATING_REGISTRY[key]
            assert spec.aliases == frozenset()
            assert spec.sentinels == frozenset()

    def test_nonirr_requires_cropname(self) -> None:
        spec = SDV_RATING_REGISTRY["nonirr_crop_yield"]
        assert "cropname" in spec.required_constraints

    def test_aws_pinned_depth(self) -> None:
        spec = SDV_RATING_REGISTRY["aws_0_100"]
        assert spec.depth_top_cm == 0.0
        assert spec.depth_bottom_cm == 100.0

    def test_storie_dominant_condition(self) -> None:
        spec = SDV_RATING_REGISTRY["storie"]
        assert spec.algorithm == "Dominant Condition"
        assert spec.tiebreak_rule == -1

    def test_contract_fields_are_subset_of_fixture_keys(self, fixture_records: list[dict]) -> None:
        fixture_keys = set(fixture_records[0])
        for field in SDV_CONTRACT_FIELDS:
            assert field in fixture_keys, f"Missing field {field} in fixture"


class TestValidateSdvRecord:
    """Two-gate validation of sdvattribute records."""

    def test_each_fixture_record_validates(self, fixture_records: list[dict]) -> None:
        for rec in fixture_records:
            spec = validate_sdv_record(rec)
            assert spec.attributename.lower() == rec["attributename"].lower()

    def test_unsupported_algorithm_raises(self, fixture_records: list[dict]) -> None:
        rec = dict(fixture_records[0])
        rec["algorithmname"] = "Dominant Component"
        with pytest.raises(SDAValidationError, match="Unsupported"):
            validate_sdv_record(rec)

    def test_algorithm_mismatch_raises(self, fixture_records: list[dict]) -> None:
        rec = dict(fixture_records[0])
        rec["algorithmname"] = "Dominant Condition"
        with pytest.raises(SDAValidationError, match="Malformed"):
            validate_sdv_record(rec)

    def test_unregistered_record_raises(self, fixture_records: list[dict]) -> None:
        rec = dict(fixture_records[0])
        rec["attributename"] = "Fake Index"
        with pytest.raises(SDAValidationError, match="Unregistered"):
            validate_sdv_record(rec)

    def test_horizon_method_mismatch_raises(self, fixture_records: list[dict]) -> None:
        aws_rec = next(
            r for r in fixture_records if r["attributename"] == "Available Water Storage"
        )
        rec = dict(aws_rec)
        rec["horzaggmeth"] = "Weighted Average"
        with pytest.raises(SDAValidationError, match="Malformed"):
            validate_sdv_record(rec)

    def test_tiebreak_mismatch_raises(self, fixture_records: list[dict]) -> None:
        rec = dict(fixture_records[0])
        rec["tiebreakrule"] = -1
        with pytest.raises(SDAValidationError, match="Malformed"):
            validate_sdv_record(rec)

    def test_malformed_table_raises_unregistered(self, fixture_records: list[dict]) -> None:
        """A non-identifier table fails gate 1 (registry match) first."""
        rec = dict(fixture_records[0])
        rec["attributetablename"] = "bad table!"
        with pytest.raises(SDAValidationError, match="Unregistered"):
            validate_sdv_record(rec)


class TestResolveSdvSpec:
    """Selector resolution and constraint validation."""

    @pytest.mark.parametrize("selector", ["nccpi", "NCCPI", "nccpi_v3"])
    def test_selector_aliases_resolve(self, selector: str) -> None:
        spec, _ = resolve_sdv_spec(selector=selector)
        assert spec.spec_id == "nccpi"

    @pytest.mark.parametrize("selector", ["storie", "Storie", "california revised storie index"])
    def test_storie_aliases_resolve(self, selector: str) -> None:
        spec, _ = resolve_sdv_spec(selector=selector)
        assert spec.spec_id == "storie"

    def test_csr2_alias_resolves(self) -> None:
        spec, _ = resolve_sdv_spec(selector="csr2")
        assert spec.spec_id == "csr2"

    def test_cpi_alias_resolves(self) -> None:
        spec, _ = resolve_sdv_spec(selector="cpi")
        assert spec.spec_id == "cpi"

    def test_aws_selector_resolves(self) -> None:
        spec, _ = resolve_sdv_spec(selector="aws_0_100")
        assert spec.spec_id == "aws_0_100"

    def test_record_path_validates(self, fixture_records: list[dict]) -> None:
        spec, _ = resolve_sdv_spec(record=fixture_records[0])
        assert spec.spec_id == "nccpi"

    def test_both_selector_and_record_raises(self, fixture_records: list[dict]) -> None:
        with pytest.raises(SDAValidationError, match="not both"):
            resolve_sdv_spec(selector="nccpi", record=fixture_records[0])

    def test_neither_raises(self) -> None:
        with pytest.raises(SDAValidationError, match="required"):
            resolve_sdv_spec()

    def test_unregistered_selector_raises(self) -> None:
        with pytest.raises(SDAValidationError, match="Unregistered"):
            resolve_sdv_spec(selector="fake_index")

    def test_crop_required_for_nonirr(self) -> None:
        with pytest.raises(SDAValidationError, match="required"):
            resolve_sdv_spec(selector="nonirr_crop_yield")

    def test_crop_validated(self) -> None:
        spec, constraints = resolve_sdv_spec(
            selector="nonirr_crop_yield", constraints={"cropname": "Corn"}
        )
        assert spec.spec_id == "nonirr_crop_yield"
        assert constraints["cropname"] == "Corn"

    def test_crop_injection_rejected(self) -> None:
        with pytest.raises(SDAValidationError, match="Invalid"):
            resolve_sdv_spec(
                selector="nonirr_crop_yield",
                constraints={"cropname": "Corn'; DROP TABLE--"},
            )

    def test_empty_crop_rejected(self) -> None:
        with pytest.raises(SDAValidationError, match="required"):
            resolve_sdv_spec(selector="nonirr_crop_yield", constraints={"cropname": ""})

    def test_long_crop_rejected(self) -> None:
        with pytest.raises(SDAValidationError, match="Invalid"):
            resolve_sdv_spec(
                selector="nonirr_crop_yield",
                constraints={"cropname": "A" * 81},
            )

    def test_no_constraints_needed_for_nccpi(self) -> None:
        spec, constraints = resolve_sdv_spec(selector="nccpi")
        assert spec.spec_id == "nccpi"
        assert constraints == {}

    def test_sdvattribute_not_in_allowed_tables(self) -> None:
        from fpac_soil_mcp.sda_client import ALLOWED_SDV_TABLES

        assert "sdvattribute" not in ALLOWED_SDV_TABLES
        assert "cointerp" in ALLOWED_SDV_TABLES
        assert "chorizon" in ALLOWED_SDV_TABLES
        assert "cocropyld" in ALLOWED_SDV_TABLES
        assert "component" in ALLOWED_SDV_TABLES
        assert "mapunit" in ALLOWED_SDV_TABLES


_CASE_IDS = [c["id"] for c in _CASES]


class TestGoldenContractCases:
    """One golden case per registry record: SQL fingerprint, values, provenance, caveats."""

    def test_cases_cover_every_registry_record(self) -> None:
        assert sorted(_CASE_IDS) == sorted(SDV_RATING_REGISTRY)

    @pytest.mark.parametrize("case", _CASES, ids=_CASE_IDS)
    def test_sql_fingerprints(self, case: dict) -> None:
        record, constraints = _case_inputs(case)
        spec, resolved = resolve_sdv_spec(record=record, constraints=constraints)
        assert spec.spec_id == case["id"]
        assert (
            _sha(build_sdv_rating_query(spec, case["mukeys"], resolved))
            == (case["rating_sql_sha256"])
        )
        assert (
            _sha(build_sdv_county_max_query(spec, case["areasymbol"], resolved))
            == (case["county_max_sql_sha256"])
        )

    @pytest.mark.parametrize("case", _CASES, ids=_CASE_IDS)
    def test_rating_outputs(self, case: dict) -> None:
        record, constraints = _case_inputs(case)
        client = _mock_client({"Table": [case["mock_header"], *case["mock_rows"]]})
        results = client.get_productivity_ratings(
            case["mukeys"], attribute_meta=record, constraints=constraints
        )
        assert [r["mukey"] for r in results] == case["mukeys"]
        for result in results:
            expected = case["expected"][result["mukey"]]
            assert result["numeric_rating"] == expected["numeric_rating"]
            assert result["is_rated"] is expected["is_rated"]
            assert result["caveats"] == expected["caveats"]
            assert (
                result["productivity_rating_source"]
                == (case["expected_productivity_rating_source"])
            )
            provenance = dict(case["expected_sdv_provenance"])
            if "yldunits" in expected:
                provenance["yldunits"] = expected["yldunits"]
            assert result["sdv_provenance"] == provenance

    @pytest.mark.parametrize("case", _CASES, ids=_CASE_IDS)
    def test_county_max_output(self, case: dict) -> None:
        record, constraints = _case_inputs(case)
        client = _mock_client({"Table": [["max_county_rating"], [case["county_max_raw"]]]})
        value = client.get_county_max_productivity_rating(
            case["areasymbol"], attribute_meta=record, constraints=constraints
        )
        assert value == case["expected_county_max"]


_LEGACY_CASES = [c for c in _CASES if "legacy_rating_sql_canonical_sha256" in c]


class TestLegacyTemplateParity:
    """NCCPI/CSR2/CPI builders reproduce the retired SQL_PRODUCTIVITY_* templates (D9)."""

    def test_legacy_cases_are_the_parity_indices(self) -> None:
        assert sorted(c["id"] for c in _LEGACY_CASES) == ["cpi", "csr2", "nccpi"]

    @pytest.mark.parametrize("case", _LEGACY_CASES, ids=[c["id"] for c in _LEGACY_CASES])
    def test_builder_sql_matches_retired_template(self, case: dict) -> None:
        spec, resolved = resolve_sdv_spec(selector=case["id"])
        assert (
            _canonical_sha(build_sdv_rating_query(spec, case["mukeys"], resolved))
            == (case["legacy_rating_sql_canonical_sha256"])
        )
        assert (
            _canonical_sha(build_sdv_county_max_query(spec, case["areasymbol"], resolved))
            == (case["legacy_county_max_sql_canonical_sha256"])
        )

    @pytest.mark.parametrize("name", ["NCCPI", "CSR2", "CPI"])
    def test_retired_templates_are_gone(self, name: str) -> None:
        assert not hasattr(sda_client, f"SQL_PRODUCTIVITY_{name}")
        assert not hasattr(sda_client, f"SQL_PRODUCTIVITY_COUNTY_MAX_{name}")


class TestOneEngine:
    """Fixed selectors and explicit metadata run the same engine path (D9)."""

    @pytest.mark.parametrize("selector", ["nccpi", "storie", "csr2", "cpi"])
    def test_selector_and_metadata_paths_agree(self, selector: str) -> None:
        case = next(c for c in _CASES if c["id"] == selector)
        record, _ = _case_inputs(case)
        payload = {"Table": [case["mock_header"], *case["mock_rows"]]}
        sent: list[bytes] = []

        def handler(request: httpx.Request) -> httpx.Response:
            sent.append(request.content)
            return httpx.Response(200, json=payload)

        client = SDAClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        by_selector = client.get_productivity_ratings(case["mukeys"], index_type=selector)
        by_record = client.get_productivity_ratings(case["mukeys"], attribute_meta=record)
        assert by_selector == by_record
        assert sent[0] == sent[1]

    @pytest.mark.parametrize("selector", ["aws_0_100", "nonirr_crop_yield"])
    def test_non_public_specs_not_reachable_by_selector(self, selector: str) -> None:
        with pytest.raises(SDAValidationError, match="Unsupported productivity index type"):
            SDAClient().get_productivity_ratings(["242959"], index_type=selector)

    def test_yield_requires_crop_constraint_before_query(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise AssertionError("must not reach SDA without a crop")

        client = SDAClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        record = _RECORDS["Yields of Non-Irrigated Crops (Component)"]
        with pytest.raises(SDAValidationError, match="Constraint 'cropname' is required"):
            client.get_productivity_ratings(["242959"], attribute_meta=record)
