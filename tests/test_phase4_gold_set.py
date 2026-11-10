"""Deterministic Phase 4 gold-set contract tests."""

from __future__ import annotations

from eval.common.dataset import load_gold_set
from eval.common.matching import match_expected


def test_gold_set_has_stable_order_and_unique_ids() -> None:
    cases = load_gold_set()
    ids = [case["id"] for case in cases]
    assert ids == [
        "strategy-cointerp",
        "strategy-mapunit",
        "strategy-component",
        "strategy-chorizon",
        "strategy-cocropyld",
        "multi-county-selected-property",
        "partial-rated-coverage",
        "urban-partial-overlap",
        "missing-subjective-inputs",
        "upstream-failure",
    ]
    assert len(ids) == len(set(ids))


def test_gold_set_covers_phase4_exit_criteria() -> None:
    categories = {case["category"] for case in load_gold_set()}
    assert categories == {
        "source-table-strategy",
        "aggregation",
        "coverage",
        "subjective-inputs",
        "failure-semantics",
    }


def test_gold_set_matcher_distinguishes_exact_tolerance_and_indeterminate() -> None:
    assert match_expected(
        {"rating": 71.004}, {"path": "rating", "approx": {"value": 71.0, "abs_tol": 0.01}}
    )[0]
    assert not match_expected(
        {"rating": 71.02}, {"path": "rating", "approx": {"value": 71.0, "abs_tol": 0.01}}
    )[0]
    assert match_expected({"rating": None}, {"path": "rating", "is_null": True})[0]
    assert not match_expected({"rating": 0}, {"path": "rating", "is_null": True})[0]


def test_gold_set_cases_have_machine_checkable_expectations() -> None:
    for case in load_gold_set():
        assert case["expectations"]
        assert all(
            match_expected({}, expectation)[1].endswith(": missing")
            for expectation in case["expectations"]
        )
