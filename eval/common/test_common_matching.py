"""Unit tests for eval/common/matching.py."""

import pytest

from common.matching import keywords_present, normalize_text, tool_matches


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
