import pytest

from fpac_soil_mcp.corridor_analysis import _feature_ratings
from fpac_soil_mcp.lesa import calculate_relative_ratings, evaluate_land_evaluation
from fpac_soil_mcp.sda_client import PRODUCTIVITY_PROVENANCE


@pytest.mark.parametrize(
    ("index", "county_max", "raw_rating", "expected_relative"),
    [
        ("nccpi", 1.0, 0.8, 0.8),
        ("csr2", 100.0, 80.0, 0.8),
        ("cpi", 100.0, 75.0, 0.75),
        ("storie", 100.0, 60.0, 0.6),
    ],
)
def test_selected_property_normalizes_against_property_specific_maximum(
    index, county_max, raw_rating, expected_relative
):
    result = calculate_relative_ratings(
        [{"mukey": "a", "raw_rating": raw_rating, "is_rated": True}],
        county_max,
    )
    assert result[0].normalized_relative_rating == pytest.approx(expected_relative)

    feature = _feature_ratings(
        {"a": {"numeric_rating": raw_rating, "is_rated": True}},
        index,
    )
    assert feature["a"]["productivity_rating_source"] == PRODUCTIVITY_PROVENANCE[index]


def test_multi_county_partial_coverage_preserves_selected_property_and_caveats():
    summary = evaluate_land_evaluation(
        [
            {
                "mukey": "ia-1",
                "normalized_relative_rating": 0.8,
                "is_rated": True,
                "acres": 10.0,
                "productivity_rating_source": "SDA:MAPUNIT_IACORNSR",
                "caveats": ["County maximum is property-specific."],
            },
            {
                "mukey": "ia-2",
                "normalized_relative_rating": None,
                "is_rated": False,
                "acres": 5.0,
                "unrated_reason": "Partial rated coverage",
            },
            {
                "mukey": "il-1",
                "normalized_relative_rating": 0.6,
                "is_rated": True,
                "acres": 5.0,
                "productivity_rating_source": "SDA:MAPUNIT_IACORNSR",
            },
        ],
        productivity_index="csr2",
    )

    assert summary.productivity_index.value == "CSR2"
    assert summary.rated_acreage == 15.0
    assert summary.unrated_acreage == 5.0
    assert summary.coverage_percent == 75.0
    assert "County maximum is property-specific." in summary.notices
    assert "Productivity rating provenance: SDA:MAPUNIT_IACORNSR" in summary.notices
