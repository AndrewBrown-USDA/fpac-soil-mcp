"""Unit and benchmark tests for Land Evaluation (LE) and LESA calculation engine.

Tests relative rating normalization, area-weighting mathematics, unrated map unit filtering,
Site Assessment (AD-1006 vs CPA-106) rules, 160-point statutory threshold triggers, and
validates against the standard le_benchmarks.json fixture cases.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from fpac_soil_mcp.lesa import (
    calculate_area_weighted_le,
    calculate_composite_le,
    calculate_county_farmland_percentile,
    calculate_criterion_7_score,
    calculate_relative_ratings,
    evaluate_land_evaluation,
    evaluate_lesa,
    evaluate_lesa_threshold,
    evaluate_site_assessment,
    get_criterion_evaluators,
)
from fpac_soil_mcp.models import (
    LandEvaluationSummary,
    MapUnitProductivityRating,
    ProductivityIndexType,
    SiteAssessmentSummary,
)


@pytest.fixture
def le_benchmarks() -> list[dict[str, Any]]:
    """Load the LE / LESA benchmark test cases fixture."""
    fixture_path = Path(__file__).parent / "fixtures" / "le_benchmarks.json"
    with open(fixture_path, encoding="utf-8") as f:
        data = json.load(f)
    return data["cases"]


class TestRelativeRatingNormalization:
    """Test normalization of raw ratings into relative ratings (RR_i = raw / county_max)."""

    def test_nccpi_normalization(self) -> None:
        ratings = [
            {"mukey": "1001", "musym": "A", "raw_rating": 0.85},
            {"mukey": "1002", "musym": "B", "raw_rating": 0.68},
        ]
        results = calculate_relative_ratings(ratings, county_max=0.94)
        assert len(results) == 2
        assert results[0].is_rated is True
        assert results[0].normalized_relative_rating == pytest.approx(0.9043, abs=1e-4)
        assert results[1].normalized_relative_rating == pytest.approx(0.7234, abs=1e-4)
        assert results[0].county_max_rating == 0.94

    def test_csr2_normalization(self) -> None:
        ratings = [
            {"mukey": "406439", "musym": "138B", "raw_rating": 89.0},
            {"mukey": "406450", "musym": "107", "raw_rating": 86.0},
        ]
        results = calculate_relative_ratings(ratings, county_max=100.0)
        assert results[0].normalized_relative_rating == 0.89
        assert results[1].normalized_relative_rating == 0.86

    def test_cpi_normalization(self) -> None:
        ratings = [
            {"mukey": "415201", "musym": "L83A", "raw_rating": 93.0},
            {"mukey": "415205", "musym": "L85A", "raw_rating": 96.0},
        ]
        results = calculate_relative_ratings(ratings, county_max=100.0)
        assert results[0].normalized_relative_rating == 0.93
        assert results[1].normalized_relative_rating == 0.96

    def test_storie_normalization(self) -> None:
        ratings = [
            {"mukey": "462001", "musym": "HdA", "raw_rating": 95.0},
            {"mukey": "462008", "musym": "SjA", "raw_rating": 52.0},
        ]
        results = calculate_relative_ratings(ratings, county_max=100.0)
        assert results[0].normalized_relative_rating == 0.95
        assert results[1].normalized_relative_rating == 0.52

    def test_rating_clamped_to_one(self) -> None:
        ratings = [{"mukey": "1001", "raw_rating": 105.0}]
        results = calculate_relative_ratings(ratings, county_max=100.0)
        assert results[0].normalized_relative_rating == 1.0


class TestUnratedAndSentinelFiltering:
    """Test handling of nulls, negative sentinels, 999 sentinels, and unrated units."""

    def test_explicit_unrated_flag(self) -> None:
        ratings = [
            {
                "mukey": "99901",
                "musym": "W",
                "raw_rating": None,
                "is_rated": False,
                "unrated_reason": "Water body",
            }
        ]
        results = calculate_relative_ratings(ratings, county_max=100.0)
        assert len(results) == 1
        assert results[0].is_rated is False
        assert results[0].normalized_relative_rating is None
        assert results[0].unrated_reason == "Water body"

    def test_null_and_empty_raw_rating(self) -> None:
        ratings = [
            {"mukey": "101", "raw_rating": None},
            {"mukey": "102", "raw_rating": ""},
        ]
        results = calculate_relative_ratings(ratings, county_max=100.0)
        assert results[0].is_rated is False
        assert results[1].is_rated is False
        assert "Missing or unavailable" in (results[0].unrated_reason or "")

    def test_non_numeric_raw_rating(self) -> None:
        ratings = [{"mukey": "101", "raw_rating": "NOT_A_NUMBER"}]
        results = calculate_relative_ratings(ratings, county_max=100.0)
        assert results[0].is_rated is False
        assert "Non-numeric" in (results[0].unrated_reason or "")

    def test_invalid_county_max(self) -> None:
        ratings = [{"mukey": "101", "raw_rating": 80.0}]
        results = calculate_relative_ratings(ratings, county_max=-1.0)
        assert results[0].is_rated is False
        assert results[0].normalized_relative_rating is None

    def test_sentinel_values(self) -> None:
        ratings = [
            {"mukey": "101", "raw_rating": -1.0},
            {"mukey": "102", "raw_rating": 999.0},
            {"mukey": "103", "raw_rating": -999.0},
            {"mukey": "104", "raw_rating": 99.0, "is_rated": False},
        ]
        results = calculate_relative_ratings(ratings, county_max=100.0)
        for r in results:
            assert r.is_rated is False
            assert (
                "unrated" in (r.unrated_reason or "").lower()
                or "sentinel" in (r.unrated_reason or "").lower()
            )
            assert r.normalized_relative_rating is None

    def test_nccpi_out_of_range_sentinel(self) -> None:
        ratings = [
            {"mukey": "101", "raw_rating": 99.0},
            {"mukey": "102", "raw_rating": 999.0},
        ]
        results = calculate_relative_ratings(ratings, county_max=0.94)
        for r in results:
            assert r.is_rated is False
            assert r.normalized_relative_rating is None


class TestAreaWeightingAndAggregation:
    """Test area-weighting LE mathematics and composite rounding."""

    def test_calculate_area_weighted_le(self) -> None:
        # Map units: (RR, acres)
        pairs = [(0.89, 45.0), (0.86, 35.0), (0.32, 20.0)]
        # Weighted sum = 0.89*45 + 0.86*35 + 0.32*20 = 40.05 + 30.10 + 6.40 = 76.55
        # Total acres = 100.0
        # AOI RR = 0.7655, candidate LE = round(76.55) = 77
        aoi_rr, candidate_le = calculate_area_weighted_le(pairs)
        assert aoi_rr == 0.7655
        assert candidate_le == 77

    def test_calculate_area_weighted_le_empty(self) -> None:
        assert calculate_area_weighted_le([]) == (0.0, 0)
        assert calculate_area_weighted_le([(0.8, 0.0)]) == (0.0, 0)

    def test_calculate_composite_le_iterable(self) -> None:
        pairs = [(80.0, 10.0), (90.0, 10.0)]
        assert calculate_composite_le(pairs) == 85.0

    def test_calculate_composite_le_scalar(self) -> None:
        assert calculate_composite_le(1700.0, 20.0) == 85.0

    def test_calculate_composite_le_invalid_args(self) -> None:
        with pytest.raises(TypeError, match="requires an iterable"):
            calculate_composite_le(100.0)  # type: ignore[call-overload]
        with pytest.raises(TypeError, match="requires a weighted sum and total weight"):
            calculate_composite_le([(10, 20)], 30)  # type: ignore[call-overload]

    def test_calculate_county_farmland_percentile(self) -> None:
        distribution = [
            {"rating": 0.9, "acres": 200.0},
            {"rating": 0.8, "acres": 300.0},
            {"rating": 0.7, "acres": 500.0},
        ]
        # Total acres = 1000.0
        # AOI RR = 0.75 -> qualifying (>= 0.75) are 0.9 (200) + 0.8 (300) = 500 acres = 50.0%
        percentile = calculate_county_farmland_percentile(0.75, distribution)
        assert percentile == 50.0

    def test_calculate_county_farmland_percentile_excludes_unrated_acres(self) -> None:
        distribution = [
            {"rating": 0.9, "acres": 200.0},
            {"rating": 0.8, "acres": 300.0},
            {"rating": 0.7, "acres": 500.0},
            {"rating": None, "acres": 400.0},  # unrated/water tract
            {"rating": 99.0, "acres": 100.0},  # sentinel tract
        ]
        # Total rated acres = 1000.0 (unrated 400 + 100 ignored in denominator)
        # Qualifying = 500.0 -> 50.0%
        percentile = calculate_county_farmland_percentile(0.75, distribution)
        assert percentile == 50.0

    def test_calculate_county_farmland_percentile_empty(self) -> None:
        assert calculate_county_farmland_percentile(0.75, None) is None
        assert calculate_county_farmland_percentile(0.75, []) is None
        assert calculate_county_farmland_percentile(0.75, [{"rating": 0.8, "acres": 0.0}]) is None


class TestLandEvaluationEvaluation:
    """Test evaluate_land_evaluation end-to-end integration."""

    def test_evaluate_land_evaluation_mixed_rated_unrated(self) -> None:
        ratings = [
            MapUnitProductivityRating(
                mukey="1",
                raw_rating=0.89,
                normalized_relative_rating=0.9468,
                is_rated=True,
            ),
            MapUnitProductivityRating(
                mukey="2",
                raw_rating=0.86,
                normalized_relative_rating=0.9149,
                is_rated=True,
            ),
            MapUnitProductivityRating(
                mukey="3",
                raw_rating=None,
                normalized_relative_rating=None,
                is_rated=False,
                unrated_reason="Water feature",
            ),
        ]
        acreages = {"1": 50.0, "2": 30.0, "3": 20.0}
        summary = evaluate_land_evaluation(
            ratings,
            acreages=acreages,
            productivity_index=ProductivityIndexType.NCCPI,
        )
        assert summary.total_acreage == 100.0
        assert summary.rated_acreage == 80.0
        assert summary.unrated_acreage == 20.0
        assert summary.coverage_percent == 80.0
        # Weighted RR = (0.9468*50 + 0.9149*30) / 80 = (47.34 + 27.447) / 80 = 74.787 / 80 = 0.9348
        assert summary.aoi_relative_rating == 0.9348
        assert summary.candidate_le_score == 93.48
        assert len(summary.notices) >= 1
        assert "unrated: Water feature" in summary.notices[0]

    def test_evaluate_land_evaluation_no_rated_units(self) -> None:
        ratings = [
            MapUnitProductivityRating(
                mukey="1",
                raw_rating=None,
                normalized_relative_rating=None,
                is_rated=False,
                unrated_reason="Pits/Quarries",
            )
        ]
        summary = evaluate_land_evaluation(
            ratings,
            acreages={"1": 25.0},
        )
        assert summary.rated_acreage == 0.0
        assert summary.unrated_acreage == 25.0
        assert summary.coverage_percent == 0.0
        assert summary.aoi_relative_rating == 0.0
        assert summary.candidate_le_score == 0.0
        assert any("No rated soil map units found" in n for n in summary.notices)


class TestSiteAssessmentRules:
    """Test Site Assessment (Form AD-1006 vs NRCS-CPA-106) scoring rules."""

    def test_criterion_7_farm_size_tiers(self) -> None:
        # > 100% of county avg (10 pts)
        pts, desc = calculate_criterion_7_score(
            project_farm_acres=250.0, county_average_farm_acres=200.0
        )
        assert pts == 10.0
        assert ">=100%" in desc

        # 50% - 99% of county avg (5 pts)
        pts, desc = calculate_criterion_7_score(
            project_farm_acres=150.0, county_average_farm_acres=200.0
        )
        assert pts == 5.0
        assert "50%-99%" in desc

        # < 50% of county avg (0 pts)
        pts, desc = calculate_criterion_7_score(
            project_farm_acres=80.0, county_average_farm_acres=200.0
        )
        assert pts == 0.0
        assert "<50%" in desc

        # Invalid county average
        pts, desc = calculate_criterion_7_score(
            project_farm_acres=100.0, county_average_farm_acres=0.0
        )
        assert pts == 0.0
        assert "Invalid or unavailable" in desc

    def test_site_vs_corridor_evaluators(self) -> None:
        site_evals = get_criterion_evaluators("site")
        corridor_evals = get_criterion_evaluators("corridor")

        # In Form AD-1006 (Site), criteria 5 & 6 have 15 max points
        assert site_evals[5].max_points == 15
        assert site_evals[6].max_points == 15
        assert site_evals[8].max_points == 10
        assert site_evals[11].max_points == 10

        # In Form NRCS-CPA-106 (Corridor), criteria 5 & 6 are zeroed; 8 & 11 are 25 max points
        assert corridor_evals[5].max_points == 0
        assert corridor_evals[6].max_points == 0
        assert corridor_evals[8].max_points == 25
        assert corridor_evals[11].max_points == 25

        # Verify total possible max points equals 160 for both forms
        assert sum(e.max_points for e in site_evals.values()) == 160
        assert sum(e.max_points for e in corridor_evals.values()) == 160

    def test_corridor_zeroed_criteria_evaluation(self) -> None:
        # Attempting to assign points to criteria 5 or 6 in a corridor project must be clamped to 0
        inputs = {
            5: {"awarded_points": 15.0},
            6: {"awarded_points": 15.0},
            8: {"awarded_points": 20.0},
        }
        sa = evaluate_site_assessment(inputs, project_type="corridor")
        c5 = next(c for c in sa.criteria if c.criterion_number == 5)
        c6 = next(c for c in sa.criteria if c.criterion_number == 6)
        c8 = next(c for c in sa.criteria if c.criterion_number == 8)

        assert c5.awarded_points == 0.0
        assert c5.is_statutorily_zeroed is True
        assert c6.awarded_points == 0.0
        assert c6.is_statutorily_zeroed is True
        assert c8.awarded_points == 20.0
        assert c8.max_points == 25


class TestLESAThresholdEvaluation:
    """Test 160-point statutory threshold triggers and determinations."""

    def test_threshold_exceeded_site(self) -> None:
        exceeded, det, actions = evaluate_lesa_threshold(168.55, project_type="site")
        assert exceeded is True
        assert "EQUALS OR EXCEEDS STATUTORY THRESHOLD (160)" in det
        assert any("Form AD-1006" in a for a in actions)
        assert any("avoid or minimize" in a for a in actions)

    def test_threshold_exceeded_corridor(self) -> None:
        exceeded, det, actions = evaluate_lesa_threshold(160.0, project_type="corridor")
        assert exceeded is True
        assert "EQUALS OR EXCEEDS STATUTORY THRESHOLD (160)" in det
        assert any("Form NRCS-CPA-106" in a for a in actions)

    def test_threshold_not_exceeded(self) -> None:
        exceeded, det, actions = evaluate_lesa_threshold(138.88, project_type="site")
        assert exceeded is False
        assert "IS BELOW STATUTORY THRESHOLD (160)" in det
        assert any("Retain this preliminary screening score" in a for a in actions)


class TestUnifiedLESARouter:
    """Test evaluate_lesa router integrating LE and SA."""

    def test_evaluate_lesa_with_summaries(self) -> None:
        le_summary = LandEvaluationSummary(
            productivity_index=ProductivityIndexType.CSR2,
            aoi_relative_rating=0.7655,
            candidate_le_score=76.55,
            rated_acreage=100.0,
            unrated_acreage=0.0,
            total_acreage=100.0,
            coverage_percent=100.0,
        )
        sa_summary = SiteAssessmentSummary(
            total_points=92.0,
            criteria=[],
        )
        resp = evaluate_lesa(
            project_name="Story County Site",
            land_evaluation=le_summary,
            site_assessment=sa_summary,
            project_type="site",
        )
        assert resp.total_lesa_score == 168.55
        assert resp.mandatory_alternatives_required is True
        assert resp.project_type == "site"
        assert resp.land_evaluation.candidate_le_score == 76.55

    def test_evaluate_lesa_with_numeric_scores(self) -> None:
        resp = evaluate_lesa(
            project_name="Numeric Input Test",
            land_evaluation=70.0,
            site_assessment=80.0,
            project_type="site",
        )
        assert resp.total_lesa_score == 150.0
        assert resp.mandatory_alternatives_required is False
        assert resp.land_evaluation.candidate_le_score == 70.0
        assert resp.site_assessment.total_points == 80.0


class TestBenchmarkSuiteValidation:
    """Validate calculation against all 6 benchmark cases in tests/fixtures/le_benchmarks.json."""

    def test_benchmark_cases(self, le_benchmarks: list[dict[str, Any]]) -> None:
        for case in le_benchmarks:
            case_id = case["id"]
            proj_type = case["project_type"]
            idx_name = case["productivity_index"]
            county_max = case["county_max_rating"]
            map_units = case["map_units"]
            expected_le = case["expected_evaluation"]
            expected_lesa = case["expected_lesa_summary"]
            sa_data = case.get("site_assessment", {})

            # 1. Test Map Unit Relative Rating Calculation
            rated_objects = calculate_relative_ratings(map_units, county_max=county_max)
            for idx, mu in enumerate(map_units):
                res_obj = rated_objects[idx]
                assert res_obj.is_rated == mu["is_rated"], (
                    f"Failed is_rated match in {case_id} mukey {mu['mukey']}"
                )
                if mu["is_rated"]:
                    assert res_obj.normalized_relative_rating == pytest.approx(
                        mu["normalized_relative_rating"], abs=1e-4
                    ), f"Failed relative rating in {case_id} mukey {mu['mukey']}"

            # 2. Test LE Summary Evaluation
            acreages = {mu["mukey"]: mu["acres"] for mu in map_units}
            le_sum = evaluate_land_evaluation(
                rated_objects,
                acreages=acreages,
                productivity_index=idx_name,
            )

            assert le_sum.rated_acreage == pytest.approx(expected_le["rated_acreage"], abs=1e-2)
            assert le_sum.unrated_acreage == pytest.approx(expected_le["unrated_acreage"], abs=1e-2)
            assert le_sum.total_acreage == pytest.approx(expected_le["total_acreage"], abs=1e-2)
            assert le_sum.coverage_percent == pytest.approx(
                expected_le["coverage_percent"], abs=1e-2
            )
            assert le_sum.aoi_relative_rating == pytest.approx(
                expected_le["aoi_relative_rating"], abs=1e-4
            )
            assert le_sum.candidate_le_score == pytest.approx(
                expected_le["candidate_le_score"], abs=1e-2
            )

            # 3. Test Full LESA Evaluation & Threshold Evaluation
            resp = evaluate_lesa(
                project_name=case["name"],
                land_evaluation=le_sum,
                site_assessment=sa_data.get("total_sa_score", 0.0),
                project_type=proj_type,
            )

            assert resp.total_lesa_score == pytest.approx(
                expected_lesa["total_lesa_score"], abs=1e-2
            )
            assert (
                resp.mandatory_alternatives_required
                == expected_lesa["mandatory_alternatives_required"]
            )

    def test_site_assessment_criterion_validation_bounds(self) -> None:
        from pydantic import ValidationError

        from fpac_soil_mcp.models import SiteAssessmentCriterion

        # Valid bounds
        c = SiteAssessmentCriterion(
            criterion_number=1,
            name="Valid Criterion",
            max_points=15.0,
            awarded_points=10.0,
        )
        assert c.awarded_points == 10.0

        # Max points negative or zero
        with pytest.raises(ValidationError, match="max_points cannot be negative"):
            SiteAssessmentCriterion(
                criterion_number=1,
                name="Invalid",
                max_points=-5.0,
                awarded_points=0.0,
            )

        # Awarded points exceeding max points
        with pytest.raises(ValidationError, match="awarded_points .* cannot exceed max_points"):
            SiteAssessmentCriterion(
                criterion_number=1,
                name="Invalid",
                max_points=10.0,
                awarded_points=15.0,
            )

        # Awarded points negative
        with pytest.raises(ValidationError, match="awarded_points cannot be negative"):
            SiteAssessmentCriterion(
                criterion_number=1,
                name="Invalid",
                max_points=10.0,
                awarded_points=-1.0,
            )
