"""Tests for per-strategy SDV query builders (Wave 3)."""

from __future__ import annotations

import sqlite3

import pytest

from fpac_soil_mcp.sda_client import (
    SDV_RATING_REGISTRY,
    SDAValidationError,
    build_sdv_county_max_query,
    build_sdv_rating_query,
)


class TestCointerpWeightedAverage:
    """cointerp + Weighted Average (NCCPI-style)."""

    def test_rating_query_contains_table_and_rule(self) -> None:
        spec = SDV_RATING_REGISTRY["nccpi"]
        sql = build_sdv_rating_query(spec, ["1001"])
        assert "cointerp" in sql
        assert "ci.interphr AS rating" in sql
        assert "NCCPI - National Commodity Crop Productivity Index" in sql

    def test_rating_query_has_left_join(self) -> None:
        spec = SDV_RATING_REGISTRY["nccpi"]
        sql = build_sdv_rating_query(spec, ["1001"])
        assert "LEFT JOIN cointerp" in sql

    def test_rating_query_has_sentinel_predicate(self) -> None:
        spec = SDV_RATING_REGISTRY["nccpi"]
        sql = build_sdv_rating_query(spec, ["1001"])
        assert "rating IS NOT NULL AND rating NOT IN" in sql
        assert "99" in sql and "999" in sql

    def test_rating_query_has_misc_area_filter(self) -> None:
        spec = SDV_RATING_REGISTRY["nccpi"]
        sql = build_sdv_rating_query(spec, ["1001"])
        assert "miscellaneous area" in sql

    def test_rating_query_rounds_to_precision(self) -> None:
        spec = SDV_RATING_REGISTRY["nccpi"]
        sql = build_sdv_rating_query(spec, ["1001"])
        assert "ROUND(" in sql
        assert ", 3)" in sql

    def test_county_max_query(self) -> None:
        spec = SDV_RATING_REGISTRY["nccpi"]
        sql = build_sdv_county_max_query(spec, "IL019")
        assert "MAX(ci.interphr)" in sql
        assert "IL019" in sql
        assert "miscellaneous area" in sql

    def test_county_max_validates_areasymbol(self) -> None:
        spec = SDV_RATING_REGISTRY["nccpi"]
        with pytest.raises(SDAValidationError):
            build_sdv_county_max_query(spec, "'; DROP TABLE--")


class TestCointerpDominantCondition:
    """cointerp + Dominant Condition (Storie-style, D5)."""

    def test_rating_query_contains_window_function(self) -> None:
        spec = SDV_RATING_REGISTRY["storie"]
        sql = build_sdv_rating_query(spec, ["1001"])
        assert "ROW_NUMBER()" in sql
        assert "PARTITION BY mukey" in sql

    def test_rating_query_keeps_unrated_components_in_totals(self) -> None:
        """LEFT JOIN keeps unrated components in total_pct and all-unrated map units."""
        spec = SDV_RATING_REGISTRY["storie"]
        sql = build_sdv_rating_query(spec, ["1001"])
        assert "LEFT JOIN cointerp AS ci" in sql
        assert "FROM mu_totals AS t" in sql
        assert "LEFT JOIN classes AS d ON d.mukey = t.mukey AND d.rn = 1" in sql

    def test_sentinel_screen_uses_source_column_not_alias(self) -> None:
        """Regression: a select alias in the same WHERE is invalid T-SQL (live SDA 400)."""
        spec = SDV_RATING_REGISTRY["storie"]
        for sql in (
            build_sdv_rating_query(spec, ["1001"]),
            build_sdv_county_max_query(spec, "CA077"),
        ):
            assert "ci.interphr IS NOT NULL AND ci.interphr NOT IN" in sql
            assert "rating IS NOT NULL AND rating NOT IN" not in sql

    def test_rating_query_groups_by_rounded_class(self) -> None:
        spec = SDV_RATING_REGISTRY["storie"]
        sql = build_sdv_rating_query(spec, ["1001"])
        assert "ROUND(ci.interphr, 3) END AS rating_val" in sql
        assert "GROUP BY mukey, rating_val" in sql

    def test_rating_query_has_tiebreak_asc(self) -> None:
        """Storie tiebreakrule=-1: lower value wins ties (ASC)."""
        spec = SDV_RATING_REGISTRY["storie"]
        sql = build_sdv_rating_query(spec, ["1001"])
        assert "ORDER BY SUM(comppct_r) DESC, rating_val ASC" in sql

    def test_rating_query_has_storie_rule(self) -> None:
        spec = SDV_RATING_REGISTRY["storie"]
        sql = build_sdv_rating_query(spec, ["1001"])
        assert "AGR - California Revised Storie Index" in sql

    def test_rating_query_has_dominant_condition_filter(self) -> None:
        spec = SDV_RATING_REGISTRY["storie"]
        sql = build_sdv_rating_query(spec, ["1001"])
        assert "d.rn = 1" in sql
        assert "d.class_pct AS dominant_pct" in sql

    def test_county_max_query_uses_dominant_condition(self) -> None:
        spec = SDV_RATING_REGISTRY["storie"]
        sql = build_sdv_county_max_query(spec, "CA077")
        assert "ROW_NUMBER()" in sql
        assert "MAX(rating_val)" in sql
        assert "WHERE rn = 1" in sql

    def test_tiebreak_rule_1_orders_desc(self) -> None:
        """tiebreakrule=1 on a Dominant Condition spec: higher value wins ties (DESC)."""
        import dataclasses

        spec = dataclasses.replace(SDV_RATING_REGISTRY["storie"], tiebreak_rule=1)
        sql = build_sdv_rating_query(spec, ["1001"])
        assert "rating_val DESC" in sql
        assert "rating_val ASC" not in sql

    def test_raw_rows_group_and_break_storie_ties(self) -> None:
        db = sqlite3.connect(":memory:")
        db.executescript(
            """
            CREATE TABLE legend (lkey TEXT, areasymbol TEXT);
            CREATE TABLE mapunit (mukey TEXT, lkey TEXT, musym TEXT, muname TEXT);
            CREATE TABLE component (cokey TEXT, mukey TEXT, comppct_r INTEGER, compkind TEXT);
            CREATE TABLE cointerp (cokey TEXT, ruledepth INTEGER, mrulename TEXT, interphr REAL);
            INSERT INTO legend VALUES ('L1', 'CA077');
            INSERT INTO mapunit VALUES ('1', 'L1', 'A', 'Storie tie');
            INSERT INTO component VALUES
                ('c1', '1', 40, 'series'),
                ('c2', '1', 40, 'series'),
                ('c3', '1', 20, 'series');
            INSERT INTO cointerp VALUES
                ('c1', 0, 'AGR - California Revised Storie Index (CA)', 0.4),
                ('c2', 0, 'AGR - California Revised Storie Index (CA)', 0.2),
                ('c3', 0, 'AGR - California Revised Storie Index (CA)', 0.2);
            """
        )
        sql = build_sdv_rating_query(SDV_RATING_REGISTRY["storie"], ["1"])
        row = db.execute(sql).fetchone()
        assert row[4:] == (pytest.approx(0.2), 60, 100, 100)


class TestComponentWeightedAverage:
    """component + Weighted Average (CPI-style)."""

    def test_rating_query_contains_column(self) -> None:
        spec = SDV_RATING_REGISTRY["cpi"]
        sql = build_sdv_rating_query(spec, ["1001"])
        assert "c.cropprodindex" in sql
        assert "CAST(c.cropprodindex AS float)" in sql

    def test_rating_query_has_comppct_weighting(self) -> None:
        spec = SDV_RATING_REGISTRY["cpi"]
        sql = build_sdv_rating_query(spec, ["1001"])
        assert "comppct_r" in sql
        assert "SUM" in sql
        assert "NULLIF" in sql

    def test_rating_query_has_misc_area_filter(self) -> None:
        spec = SDV_RATING_REGISTRY["cpi"]
        sql = build_sdv_rating_query(spec, ["1001"])
        assert "miscellaneous area" in sql

    def test_county_max_query(self) -> None:
        spec = SDV_RATING_REGISTRY["cpi"]
        sql = build_sdv_county_max_query(spec, "MN167")
        assert "MAX(CAST(c.cropprodindex AS float))" in sql
        assert "MN167" in sql

    def test_nulls_as_zero_only_when_map_unit_has_a_rating(self) -> None:
        """D12: null CPI counts as 0 beside rated components; all-null stays unrated."""
        db = sqlite3.connect(":memory:")
        db.executescript(
            """
            CREATE TABLE legend (lkey TEXT, areasymbol TEXT);
            CREATE TABLE mapunit (mukey TEXT, lkey TEXT, musym TEXT, muname TEXT);
            CREATE TABLE component (
                mukey TEXT, comppct_r INTEGER, compkind TEXT, cropprodindex INTEGER
            );
            INSERT INTO legend VALUES ('L1', 'MN167');
            INSERT INTO mapunit VALUES
                ('1', 'L1', 'A', 'All rated'),
                ('2', 'L1', 'B', 'Partly rated'),
                ('3', 'L1', 'C', 'No ratings'),
                ('4', 'L1', 'D', 'Sentinel and null');
            INSERT INTO component VALUES
                ('1', 60, 'series', 80), ('1', 40, 'series', 60),
                ('2', 80, 'series', 90), ('2', 20, 'inclusion', NULL),
                ('2', 10, 'miscellaneous area', NULL),
                ('3', 70, 'series', NULL), ('3', 30, 'series', NULL),
                ('4', 50, 'series', 999), ('4', 50, 'series', NULL);
            """
        )
        sql = build_sdv_rating_query(SDV_RATING_REGISTRY["cpi"], ["1", "2", "3", "4"])
        rows = {r[0]: r[4:] for r in db.execute(sql)}
        assert rows["1"] == (pytest.approx(72.0), 100, 100)
        assert rows["2"] == (pytest.approx(72.0), 80, 100)
        assert rows["3"] == (None, 0, 100)
        assert rows["4"] == (None, 0, 100)


class TestMapunitNoAggregation:
    """mapunit + No Aggregation Necessary (CSR2-style)."""

    def test_rating_query_contains_column(self) -> None:
        spec = SDV_RATING_REGISTRY["csr2"]
        sql = build_sdv_rating_query(spec, ["1001"])
        assert "m.iacornsr" in sql
        assert "CAST(m.iacornsr AS float)" in sql

    def test_rating_query_has_no_join(self) -> None:
        spec = SDV_RATING_REGISTRY["csr2"]
        sql = build_sdv_rating_query(spec, ["1001"])
        # mapunit query should not join component or cointerp
        assert "INNER JOIN component" not in sql
        assert "cointerp" not in sql

    def test_rating_query_rated_pct_is_100(self) -> None:
        spec = SDV_RATING_REGISTRY["csr2"]
        sql = build_sdv_rating_query(spec, ["1001"])
        assert "100.0" in sql

    def test_county_max_query(self) -> None:
        spec = SDV_RATING_REGISTRY["csr2"]
        sql = build_sdv_county_max_query(spec, "IA169")
        assert "MAX(CAST(m.iacornsr AS float))" in sql
        assert "IA169" in sql

    def test_county_max_has_no_component_join(self) -> None:
        spec = SDV_RATING_REGISTRY["csr2"]
        sql = build_sdv_county_max_query(spec, "IA169")
        assert "INNER JOIN component" not in sql


class TestChorizonWeightedSum:
    """chorizon + Weighted Average + horizon Weighted Sum (D6, 0-100 cm)."""

    def test_rating_query_clips_to_100cm(self) -> None:
        spec = SDV_RATING_REGISTRY["aws_0_100"]
        sql = build_sdv_rating_query(spec, ["1001"])
        assert "chorizon" in sql
        assert "hzdepb_r" in sql
        assert "hzdept_r" in sql
        # Depth clipping at 100 cm
        assert "100" in sql

    def test_rating_query_uses_awc_r(self) -> None:
        spec = SDV_RATING_REGISTRY["aws_0_100"]
        sql = build_sdv_rating_query(spec, ["1001"])
        assert "awc_r" in sql

    def test_rating_query_excludes_nulls(self) -> None:
        spec = SDV_RATING_REGISTRY["aws_0_100"]
        sql = build_sdv_rating_query(spec, ["1001"])
        assert "LEFT JOIN hz_weighted" in sql
        assert "attr_sum IS NOT NULL" in sql

    def test_rating_query_has_misc_area_filter(self) -> None:
        spec = SDV_RATING_REGISTRY["aws_0_100"]
        sql = build_sdv_rating_query(spec, ["1001"])
        assert "miscellaneous area" in sql

    def test_rating_query_preserves_partial_and_all_null_coverage(self) -> None:
        db = sqlite3.connect(":memory:")
        db.executescript(
            """
            CREATE TABLE legend (lkey TEXT, areasymbol TEXT);
            CREATE TABLE mapunit (mukey TEXT, lkey TEXT, musym TEXT, muname TEXT);
            CREATE TABLE component (cokey TEXT, mukey TEXT, comppct_r INTEGER, compkind TEXT);
            CREATE TABLE chorizon (cokey TEXT, hzdept_r INTEGER, hzdepb_r INTEGER, awc_r REAL);
            INSERT INTO legend VALUES ('L1', 'IL019');
            INSERT INTO mapunit VALUES
                ('1', 'L1', 'A', 'Partly rated'),
                ('2', 'L1', 'B', 'No ratings');
            INSERT INTO component VALUES
                ('c1', '1', 60, 'series'),
                ('c2', '1', 40, 'series'),
                ('c3', '2', 100, 'series');
            INSERT INTO chorizon VALUES
                ('c1', 0, 100, 0.2),
                ('c2', 0, 100, NULL),
                ('c3', 0, 100, NULL);
            """
        )
        sql = build_sdv_rating_query(SDV_RATING_REGISTRY["aws_0_100"], ["1", "2"])
        rows = {r[0]: r[4:] for r in db.execute(sql)}
        assert rows["1"] == (pytest.approx(20.0), 60, 100)
        assert rows["2"] == (None, 0, 100)

    def test_raw_rows_clip_horizons_to_fixed_depth(self) -> None:
        db = sqlite3.connect(":memory:")
        db.executescript(
            """
            CREATE TABLE legend (lkey TEXT, areasymbol TEXT);
            CREATE TABLE mapunit (mukey TEXT, lkey TEXT, musym TEXT, muname TEXT);
            CREATE TABLE component (cokey TEXT, mukey TEXT, comppct_r INTEGER, compkind TEXT);
            CREATE TABLE chorizon (cokey TEXT, hzdept_r INTEGER, hzdepb_r INTEGER, awc_r REAL);
            INSERT INTO legend VALUES ('L1', 'IL019');
            INSERT INTO mapunit VALUES ('1', 'L1', 'A', 'Clipped horizons');
            INSERT INTO component VALUES ('c1', '1', 100, 'series');
            INSERT INTO chorizon VALUES
                ('c1', -10, 10, 0.1),
                ('c1', 10, 150, 0.2),
                ('c1', 150, 200, 0.9),
                ('c1', 0, 100, NULL);
            """
        )
        sql = build_sdv_rating_query(SDV_RATING_REGISTRY["aws_0_100"], ["1"])
        row = db.execute(sql).fetchone()
        assert row[4:] == (pytest.approx(19.0), 100, 100)

    def test_county_max_query(self) -> None:
        spec = SDV_RATING_REGISTRY["aws_0_100"]
        sql = build_sdv_county_max_query(spec, "IL019")
        assert "MAX(mukey_rating)" in sql
        assert "IL019" in sql


class TestCocropyldWeightedAverage:
    """cocropyld + Weighted Average (D7, crop filter, nulls-as-zero)."""

    def test_rating_query_has_crop_filter(self) -> None:
        spec = SDV_RATING_REGISTRY["nonirr_crop_yield"]
        sql = build_sdv_rating_query(spec, ["1001"], constraints={"cropname": "Corn"})
        assert "cocropyld" in sql
        assert "cropname = 'Corn'" in sql

    def test_rating_query_has_nulls_as_zero(self) -> None:
        spec = SDV_RATING_REGISTRY["nonirr_crop_yield"]
        sql = build_sdv_rating_query(spec, ["1001"], constraints={"cropname": "Corn"})
        assert "COALESCE" in sql

    def test_rating_query_has_mixed_unit_detection(self) -> None:
        spec = SDV_RATING_REGISTRY["nonirr_crop_yield"]
        sql = build_sdv_rating_query(spec, ["1001"], constraints={"cropname": "Corn"})
        assert "unit_count" in sql
        assert "yldunits_min" in sql
        assert "yldunits_max" in sql

    def test_missing_crop_raises(self) -> None:
        spec = SDV_RATING_REGISTRY["nonirr_crop_yield"]
        with pytest.raises(SDAValidationError, match="Crop name is required"):
            build_sdv_rating_query(spec, ["1001"])

    def test_county_max_query_has_crop_filter(self) -> None:
        spec = SDV_RATING_REGISTRY["nonirr_crop_yield"]
        sql = build_sdv_county_max_query(spec, "IL019", constraints={"cropname": "Corn"})
        assert "cropname = 'Corn'" in sql
        assert "IL019" in sql

    def test_county_max_missing_crop_raises(self) -> None:
        spec = SDV_RATING_REGISTRY["nonirr_crop_yield"]
        with pytest.raises(SDAValidationError, match="Crop name is required"):
            build_sdv_county_max_query(spec, "IL019")

    def test_raw_rows_weight_yields_and_detect_mixed_units(self) -> None:
        db = sqlite3.connect(":memory:")
        db.executescript(
            """
            CREATE TABLE legend (lkey TEXT, areasymbol TEXT);
            CREATE TABLE mapunit (mukey TEXT, lkey TEXT, musym TEXT, muname TEXT);
            CREATE TABLE component (cokey TEXT, mukey TEXT, comppct_r INTEGER, compkind TEXT);
            CREATE TABLE cocropyld (
                cokey TEXT, cropname TEXT, nonirryield_r REAL, yldunits TEXT
            );
            INSERT INTO legend VALUES ('L1', 'IL019');
            INSERT INTO mapunit VALUES
                ('1', 'L1', 'A', 'Single unit'),
                ('2', 'L1', 'B', 'Mixed units');
            INSERT INTO component VALUES
                ('c1', '1', 60, 'series'),
                ('c2', '1', 40, 'series'),
                ('c3', '2', 50, 'series'),
                ('c4', '2', 50, 'series');
            INSERT INTO cocropyld VALUES
                ('c1', 'Corn', 100, 'BU/A'),
                ('c2', 'Corn', 50, 'BU/A'),
                ('c3', 'Corn', 100, 'BU/A'),
                ('c4', 'Corn', 80, 'TON/A');
            """
        )
        sql = build_sdv_rating_query(
            SDV_RATING_REGISTRY["nonirr_crop_yield"], ["1", "2"], {"cropname": "Corn"}
        )
        rows = {r[0]: r[4:] for r in db.execute(sql)}
        assert rows["1"] == (pytest.approx(80.0), 100, 100, 1, "BU/A", "BU/A")
        assert rows["2"] == (pytest.approx(90.0), 100, 100, 2, "BU/A", "TON/A")


class TestValidation:
    """Input validation tests."""

    def test_invalid_mukeys_raise(self) -> None:
        spec = SDV_RATING_REGISTRY["nccpi"]
        with pytest.raises(SDAValidationError):
            build_sdv_rating_query(spec, ["abc'; DROP TABLE--"])

    def test_invalid_mukeys_empty(self) -> None:
        spec = SDV_RATING_REGISTRY["nccpi"]
        with pytest.raises(SDAValidationError):
            build_sdv_rating_query(spec, [])
