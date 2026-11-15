"""Tests for 7 CFR § 658.5(c) Corridor Site Assessment and LESA scoring rules engine."""

import pytest
from pydantic import ValidationError

from fpac_soil_mcp.domain.lesa import (
    CORRIDOR_CRITERIA_MAX_POINTS,
    CORRIDOR_CRITERIA_NAMES,
    CRITERION_EVALUATORS,
    LESA_THRESHOLD_SCORE,
    MAX_LAND_EVALUATION_SCORE,
    MAX_SITE_ASSESSMENT_SCORE,
    MAX_TOTAL_LESA_SCORE,
    CriterionEvaluation,
    FarmSizeCriterionEvaluator,
    StandardCriterionEvaluator,
    ZeroedCriterionEvaluator,
    calculate_criterion_7_score,
    evaluate_corridor_lesa,
    evaluate_corridor_site_assessment,
)


def test_corridor_statutory_criteria_point_limits():
    """Verify statutory point maximums under 7 CFR § 658.5(c)."""
    assert CORRIDOR_CRITERIA_MAX_POINTS[1] == 15
    assert CORRIDOR_CRITERIA_MAX_POINTS[2] == 10
    assert CORRIDOR_CRITERIA_MAX_POINTS[3] == 20
    assert CORRIDOR_CRITERIA_MAX_POINTS[4] == 20
    assert CORRIDOR_CRITERIA_MAX_POINTS[5] == 0  # Zeroed out
    assert CORRIDOR_CRITERIA_MAX_POINTS[6] == 0  # Zeroed out
    assert CORRIDOR_CRITERIA_MAX_POINTS[7] == 10
    assert CORRIDOR_CRITERIA_MAX_POINTS[8] == 25  # Adjusted from 10 to 25
    assert CORRIDOR_CRITERIA_MAX_POINTS[9] == 5
    assert CORRIDOR_CRITERIA_MAX_POINTS[10] == 20
    assert CORRIDOR_CRITERIA_MAX_POINTS[11] == 25  # Adjusted from 10 to 25
    assert CORRIDOR_CRITERIA_MAX_POINTS[12] == 10

    # Total sum of max points must equal 160
    assert sum(CORRIDOR_CRITERIA_MAX_POINTS.values()) == MAX_SITE_ASSESSMENT_SCORE
    assert MAX_SITE_ASSESSMENT_SCORE == 160
    assert MAX_LAND_EVALUATION_SCORE == 100
    assert MAX_TOTAL_LESA_SCORE == 260
    assert LESA_THRESHOLD_SCORE == 160


def test_criterion_evaluation_validation():
    """Verify validation and point clamping for individual criteria."""
    # Valid criterion
    crit1 = CriterionEvaluation(
        criterion_number=1,
        name=CORRIDOR_CRITERIA_NAMES[1],
        max_points=15,
        awarded_points=12.0,
        justification="80% non-urban land in 1-mile buffer",
    )
    assert crit1.awarded_points == 12.0

    # Zeroed criterion
    crit5 = CriterionEvaluation(
        criterion_number=5,
        name=CORRIDOR_CRITERIA_NAMES[5],
        max_points=0,
        awarded_points=0.0,
        is_statutorily_zeroed=True,
    )
    assert crit5.awarded_points == 0.0

    # Exceeding max points raises ValidationError
    with pytest.raises(ValidationError):
        CriterionEvaluation(
            criterion_number=1,
            name=CORRIDOR_CRITERIA_NAMES[1],
            max_points=15,
            awarded_points=20.0,
        )

    # Negative points raises ValidationError
    with pytest.raises(ValidationError):
        CriterionEvaluation(
            criterion_number=1,
            name=CORRIDOR_CRITERIA_NAMES[1],
            max_points=15,
            awarded_points=-2.0,
        )


def test_criterion_7_farm_size_calculation():
    """Test Criterion 7 farm size ratio compared to NASS county average."""
    # Farm > 100% of county average -> 10 pts
    pts, desc = calculate_criterion_7_score(
        project_farm_acres=350.0, county_average_farm_acres=200.0
    )
    assert pts == 10.0
    assert "as large as or larger than average" in desc.lower()

    # Farm exactly 100% of county average -> 10 pts
    pts, desc = calculate_criterion_7_score(
        project_farm_acres=200.0, county_average_farm_acres=200.0
    )
    assert pts == 10.0
    assert "100.0% of county average" in desc

    # Farm 40% below the county average -> 2 pts (one deduction per complete 5%)
    pts, desc = calculate_criterion_7_score(
        project_farm_acres=120.0, county_average_farm_acres=200.0
    )
    assert pts == 2.0
    assert "60% to less than 65% of county average" in desc

    # Farm 50% or more below the county average -> 0 pts
    pts, desc = calculate_criterion_7_score(
        project_farm_acres=40.0, county_average_farm_acres=200.0
    )
    assert pts == 0.0
    assert "50% or more below average" in desc

    with pytest.raises(ValueError, match="county_average_farm_acres must be positive"):
        calculate_criterion_7_score(project_farm_acres=100.0, county_average_farm_acres=0.0)


def test_calculate_composite_le_supports_iterable_and_scalar_forms():
    from fpac_soil_mcp.domain.lesa import calculate_composite_le

    assert calculate_composite_le([(80.0, 2.0), (100.0, 3.0)]) == 92.0
    assert calculate_composite_le(460.0, 5.0) == 92.0
    assert calculate_composite_le([]) is None
    assert calculate_composite_le(460.0, 0.0) is None


def test_evaluate_corridor_site_assessment_full():
    """Test full site assessment evaluation with manual and automated inputs."""
    criteria_inputs = {
        1: {
            "awarded_points": 15.0,
            "justification": "Rural corridor, 95% non-urban in 1 mi",
            "is_automated": True,
        },
        2: {
            "awarded_points": 8.0,
            "justification": "80% perimeter in active farmland",
            "is_automated": True,
        },
        3: {"awarded_points": 18.0, "justification": "NASS CDL indicates 90% cultivated row crops"},
        4: {
            "awarded_points": 10.0,
            "justification": "General agricultural zoning, no active easement",
        },
        5: {"awarded_points": 15.0},  # Attempt to award points to zeroed criterion
        6: {"awarded_points": 10.0},  # Attempt to award points to zeroed criterion
        8: {
            "awarded_points": 22.0,
            "justification": "Bisects 4 parcels creating 60 acres of remnant triangular corners",
        },
        9: {
            "awarded_points": 5.0,
            "justification": "Full grain elevator and implement dealer network within 5 miles",
        },
        10: {
            "awarded_points": 15.0,
            "justification": "Center pivot irrigation systems and tile drainage impacted",
        },
        11: {
            "awarded_points": 20.0,
            "justification": "Corridor eliminates substantial commercial farm footprint",
        },
        12: {
            "awarded_points": 5.0,
            "justification": "Compatible with overhead power line easements",
        },
    }

    # County average is 150 ac, affected farm is 250 ac -> Criterion 7 will yield 10 pts
    sa_summary = evaluate_corridor_site_assessment(
        criteria_inputs=criteria_inputs,
        project_farm_acres=250.0,
        county_average_farm_acres=150.0,
    )

    assert sa_summary.total_sa_points <= 160.0
    assert sa_summary.max_sa_points == 160
    assert len(sa_summary.criteria) == 12

    # Check criteria 5 and 6 are strictly zeroed
    crit5 = next(c for c in sa_summary.criteria if c.criterion_number == 5)
    assert crit5.awarded_points == 0.0
    assert crit5.is_statutorily_zeroed is True

    crit6 = next(c for c in sa_summary.criteria if c.criterion_number == 6)
    assert crit6.awarded_points == 0.0
    assert crit6.is_statutorily_zeroed is True

    # Check criterion 7 automated from farm size
    crit7 = next(c for c in sa_summary.criteria if c.criterion_number == 7)
    assert crit7.awarded_points == 10.0
    assert crit7.is_automated is True

    # Check criterion 8 and 11 adjusted maximums
    crit8 = next(c for c in sa_summary.criteria if c.criterion_number == 8)
    assert crit8.max_points == 25
    assert crit8.awarded_points == 22.0

    crit11 = next(c for c in sa_summary.criteria if c.criterion_number == 11)
    assert crit11.max_points == 25
    assert crit11.awarded_points == 20.0

    # Total SA points: 15 + 8 + 18 + 10 + 0 + 0 + 10 + 22 + 5 + 15 + 20 + 5 = 128.0
    assert sa_summary.total_sa_points == 128.0


def test_lesa_threshold_evaluation_below_160():
    """Test combined LESA score < 160 requiring no further review."""
    sa_summary = evaluate_corridor_site_assessment(
        criteria_inputs={
            1: {"awarded_points": 5.0, "justification": "Urban fringe"},
            2: {"awarded_points": 4.0, "justification": "Low farm perimeter"},
            8: {"awarded_points": 5.0, "justification": "Minor remnants"},
        }
    )
    # Total SA is 5 + 4 + 5 = 14.0
    assert sa_summary.total_sa_points == 14.0

    # LE score of 72.0 -> Total = 86.0 (< 160)
    lesa_res = evaluate_corridor_lesa(land_evaluation_score=72.0, site_assessment=sa_summary)

    assert lesa_res.land_evaluation_score == 72.0
    assert lesa_res.total_lesa_score == 86.0
    assert lesa_res.threshold_exceeded is False
    assert "IS BELOW 160" in lesa_res.statutory_determination
    assert any("administrative record" in act for act in lesa_res.recommended_actions)
    assert any("NRCS-CPA-106" in act for act in lesa_res.recommended_actions)


def test_lesa_evaluation_when_le_is_none():
    """Verify LESA evaluation handles missing/unmapped LE without false below-threshold finding."""
    sa_summary = evaluate_corridor_site_assessment(
        criteria_inputs={
            1: {"awarded_points": 10.0, "justification": "Rural"},
            2: {"awarded_points": 8.0, "justification": "Surrounded by farm"},
        }
    )
    assert sa_summary.total_sa_points == 18.0

    lesa_res = evaluate_corridor_lesa(land_evaluation_score=None, site_assessment=sa_summary)

    assert lesa_res.land_evaluation_score is None
    assert lesa_res.total_lesa_score is None
    assert lesa_res.threshold_exceeded is None
    assert "LAND EVALUATION (LE) SCORE UNAVAILABLE" in lesa_res.statutory_determination
    assert any(
        "Obtain official Land Evaluation (LE) score" in act for act in lesa_res.recommended_actions
    )


def test_strategy_evaluator_dispatch():
    """Verify strategy evaluators work as standalone classes and via registry."""
    # Zeroed Evaluator
    zero_eval = ZeroedCriterionEvaluator(5)
    res5 = zero_eval.evaluate(crit_input={"awarded_points": 10.0})
    assert res5.awarded_points == 0.0
    assert res5.is_statutorily_zeroed is True

    # Farm Size Evaluator automated
    farm_eval = FarmSizeCriterionEvaluator(7)
    res7_auto = farm_eval.evaluate(
        project_farm_acres=300.0,
        county_average_farm_acres=200.0,
    )
    assert res7_auto.awarded_points == 10.0
    assert res7_auto.is_automated is True

    # Farm Size Evaluator manual
    res7_man = farm_eval.evaluate(
        crit_input={"awarded_points": 8.0, "justification": "Manual evaluation"}
    )
    assert res7_man.awarded_points == 8.0
    assert res7_man.justification == "Manual evaluation"

    # Standard Evaluator clamping
    std_eval = StandardCriterionEvaluator(1)
    res1 = std_eval.evaluate(crit_input={"awarded_points": 25.0})
    assert res1.awarded_points == 15.0  # Clamped to max 15

    # Check registry mappings
    assert isinstance(CRITERION_EVALUATORS[5], ZeroedCriterionEvaluator)
    assert isinstance(CRITERION_EVALUATORS[6], ZeroedCriterionEvaluator)
    assert isinstance(CRITERION_EVALUATORS[7], FarmSizeCriterionEvaluator)
    assert isinstance(CRITERION_EVALUATORS[1], StandardCriterionEvaluator)
    assert isinstance(CRITERION_EVALUATORS[8], StandardCriterionEvaluator)
    assert CRITERION_EVALUATORS[8].max_points == 25


def test_lesa_threshold_evaluation_above_160():
    """Test 160+ scores receive the regulatory protection-consideration guidance."""
    # LE score of 85.0
    # SA score of 95.0 -> Total = 180.0 (>= 160)
    criteria_inputs = {
        1: {"awarded_points": 15.0, "justification": "Prime ag district"},
        2: {"awarded_points": 10.0, "justification": "100% ag perimeter"},
        3: {"awarded_points": 20.0, "justification": "Continuous corn-soy rotation"},
        4: {"awarded_points": 15.0, "justification": "Ag security area"},
        8: {"awarded_points": 20.0, "justification": "Substantial remnant parcels"},
        11: {"awarded_points": 15.0, "justification": "Major regional impact"},
    }
    sa_summary = evaluate_corridor_site_assessment(criteria_inputs=criteria_inputs)
    assert sa_summary.total_sa_points == 95.0

    lesa_res = evaluate_corridor_lesa(land_evaluation_score=85.0, site_assessment=sa_summary)

    assert lesa_res.land_evaluation_score == 85.0
    assert lesa_res.total_lesa_score == 180.0
    assert lesa_res.threshold_exceeded is True
    assert "IS 160 OR MORE" in lesa_res.statutory_determination
    assert any("USDA recommends" in act for act in lesa_res.recommended_actions)
    assert any("convert fewer acres" in act for act in lesa_res.recommended_actions)
    assert any("Form NRCS-CPA-106" in act for act in lesa_res.recommended_actions)
