"""Unit tests for eval/common/matching.py."""

import pytest

from common.dataset import load_cases
from common.matching import _keyword_form, keywords_present, normalize_text, tool_matches


def _digit_edged_dataset_keywords() -> list[str]:
    keywords = {kw for case in load_cases() for kw in case["expected_keywords"]}
    return sorted(
        kw for kw in keywords if _keyword_form(kw)[:1].isdigit() or _keyword_form(kw)[-1:].isdigit()
    )


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("AD\u20111006", "AD-1006"),
        ("NRCS\u2013CPA\u2014106", "NRCS-CPA-106"),
        ("minus\u2212sign", "minus-sign"),
        ("7\u00a0CFR", "7 CFR"),
        ("thin\u2009space", "thin space"),
        ("narrow\u202fspace", "narrow space"),
        ("\u00a7 658.4", "\u00a7 658.4"),
    ],
)
def test_normalize_text_maps_unicode_dashes_and_spaces(raw, expected):
    assert normalize_text(raw) == expected


def test_tool_matches_exact_name():
    assert tool_matches("list_farmland_classes", {"list_farmland_classes"})


@pytest.mark.parametrize(
    "called",
    [
        "fpac-soil_list_farmland_classes",
        "fpac-soil:list_farmland_classes",
        "mcp_fpac-soil_list_farmland_classes",
    ],
)
def test_tool_matches_client_prefixed_names(called):
    assert tool_matches("list_farmland_classes", [called])


@pytest.mark.parametrize(
    ("expected", "called"),
    [
        ("get_farmland_classification_by_point", "get_farmland_classification_by_point_v2"),
        ("get_farmland_classification_by_point", "get_farmland_classification_by_mukey"),
        ("by_point", "getby_point"),
        ("tool", "server_tool_extra"),
    ],
)
def test_tool_matches_rejects_non_matching_names(expected, called):
    assert not tool_matches(expected, [called])


def test_tool_matches_empty_and_generator_inputs():
    assert not tool_matches("list_farmland_classes", [])
    assert tool_matches("x", (name for name in ["a", "srv_x"]))


def test_keywords_present_is_case_insensitive_over_normalized_text():
    ok, missing = keywords_present(
        "See form ad\u20111006 and 7\u00a0cfr part 658", ["AD-1006", "7 CFR"]
    )
    assert ok
    assert missing == []


def test_keywords_present_reports_missing_keywords_in_order():
    ok, missing = keywords_present("Prime farmland", ["NRCS-CPA-106", "prime", "AD-1006"])
    assert not ok
    assert missing == ["NRCS-CPA-106", "AD-1006"]


def test_keywords_present_with_no_keywords_passes():
    assert keywords_present("anything", []) == (True, [])


@pytest.mark.parametrize(
    "text",
    [
        "under 7 CFR Part 658",
        "criteria under 7 CFR \u00a7 658.5",
        "exempt under 7 CFR \u00a7658.2(a)",
        "see 7 CFR \u00a7\u00a7 658.4-658.5",
        "see 7 C.F.R. part 658",
        "7 CFR Sec. 658.4",
        "7 CFR section 658.4",
        "7 CFR 658",
    ],
)
def test_keywords_present_treats_cfr_part_and_section_forms_as_equal(text):
    assert keywords_present(text, ["7 CFR Part 658"]) == (True, [])


@pytest.mark.parametrize(
    "text",
    [
        "under 7 CFR Part 657",
        "under 7 CFR \u00a7 657.5",
        "Section 658 of the regulations",
        "\u00a7 658.5",
    ],
)
def test_keywords_present_cfr_equivalence_still_requires_title_and_part(text):
    assert keywords_present(text, ["7 CFR Part 658"]) == (False, ["7 CFR Part 658"])


def test_keywords_present_bare_cfr_keyword_matches_section_citation():
    assert keywords_present("criteria under 7 CFR \u00a7 658.5", ["7 CFR"]) == (True, [])


@pytest.mark.parametrize(
    ("keyword", "text"),
    [
        ("7 CFR", "under 27 CFR Part 658"),
        ("7 CFR Part 658", "under 7 CFR Part 6580"),
        ("409406", "map unit 4094061"),
        ("160", "a threshold of 1600 points"),
        ("AD-1006", "form AD-10060"),
    ],
)
def test_keywords_present_rejects_numbers_extended_at_digit_edges(keyword, text):
    assert keywords_present(text, [keyword]) == (False, [keyword])


@pytest.mark.parametrize(
    ("keyword", "text"),
    [
        ("7 CFR Part 658", "criteria under 7 CFR \u00a7 658.5"),
        ("7 CFR Part 658", "see 7 C.F.R. 658"),
        ("160", "a total score of 160."),
        ("658.5(c)", "factors in \u00a7 658.5(c) apply"),
    ],
)
def test_keywords_present_allows_non_digit_neighbors_at_digit_edges(keyword, text):
    assert keywords_present(text, [keyword]) == (True, [])


def test_dataset_has_digit_edged_keywords():
    assert len(_digit_edged_dataset_keywords()) >= 8


@pytest.mark.parametrize("keyword", _digit_edged_dataset_keywords())
def test_digit_edged_dataset_keywords_match_inside_a_sentence(keyword):
    assert keywords_present(f"See {keyword} here.", [keyword]) == (True, [])
