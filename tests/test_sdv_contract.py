"""Tests for the SDV metadata-driven rating contract (ADR 0014)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fpac_soil_mcp.sda_client import (
    SDV_CONTRACT_FIELDS,
    SDV_RATING_REGISTRY,
    SDV_REGISTRY_VERSION,
    SUPPORTED_HORIZON_METHODS,
    SUPPORTED_SDV_ALGORITHMS,
    SDAValidationError,
    validate_sdv_record,
    resolve_sdv_spec,
)

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "sdv_attribute_records.json"


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
