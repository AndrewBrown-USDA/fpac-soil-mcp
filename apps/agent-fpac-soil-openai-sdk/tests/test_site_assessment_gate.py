import json

import pytest
from agent_server.site_assessment_gate import (
    SiteAssessmentGateError,
    validate_site_assessment_call,
)


def _criteria(valid_site_assessment_criteria_resource):
    return json.loads(valid_site_assessment_criteria_resource.contents[0].text)


def _answer(resource, state="answered", band_id="range_20_90_1"):
    criteria = json.loads(resource.contents[0].text)
    band = next(band for band in criteria["criteria"][0]["bands"] if band["id"] == band_id)
    return {
        "type": "site_assessment_answer",
        "criterion_number": 1,
        "answer_state": state,
        "answer": band_id if state == "answered" else None,
        "selected_band": band if state != "skipped" else None,
        "points": band["points"] if state == "answered" else None,
        "evidence": "observed",
        "comment": "",
        "provenance": "user",
    }


def _call_args(fact):
    return {
        "project_type": "site",
        "site_assessment_inputs": {"criteria_facts": {"1": {"percentage": fact}}},
    }


def _history(*answers, confirmed=True):
    summary = {
        "type": "site_assessment_confirmed_summary",
        "confirmed": confirmed,
        "answers": list(answers),
    }
    return [{"role": "user", "content": json.dumps(summary)}]


def test_matching_confirmation_validates_answer_against_submitted_fact(
    valid_site_assessment_criteria_resource,
):
    arguments = _call_args(24)

    result = validate_site_assessment_call(
        "calculate_preliminary_lesa",
        arguments,
        _history(_answer(valid_site_assessment_criteria_resource)),
        _criteria(valid_site_assessment_criteria_resource),
    )

    assert result == arguments


@pytest.mark.parametrize(
    "case",
    [
        "missing-confirmation",
        "absent-site-assessment-inputs",
    ],
)
def test_missing_confirmation_or_absent_inputs_are_rejected(
    valid_site_assessment_criteria_resource, case
):
    arguments = _call_args(24) if case == "missing-confirmation" else {"project_type": "site"}
    history = (
        []
        if case == "missing-confirmation"
        else _history(_answer(valid_site_assessment_criteria_resource))
    )
    with pytest.raises(SiteAssessmentGateError):
        validate_site_assessment_call(
            "calculate_preliminary_lesa",
            arguments,
            history,
            _criteria(valid_site_assessment_criteria_resource),
        )


@pytest.mark.parametrize(
    ("state", "fact"),
    [("unknown", "unknown"), ("skipped", "skipped")],
)
def test_matching_unknown_or_skipped_only_summary_is_allowed(
    valid_site_assessment_criteria_resource, state, fact
):
    answer = _answer(
        valid_site_assessment_criteria_resource,
        state=state,
        band_id="unknown" if state == "unknown" else "below_20",
    )

    result = validate_site_assessment_call(
        "calculate_preliminary_lesa",
        _call_args(fact),
        _history(answer),
        _criteria(valid_site_assessment_criteria_resource),
    )

    assert result["site_assessment_inputs"]["criteria_facts"]["1"] == {"percentage": fact}


def test_stale_answer_and_unconfirmed_summary_are_rejected(
    valid_site_assessment_criteria_resource,
):
    with pytest.raises(SiteAssessmentGateError):
        validate_site_assessment_call(
            "calculate_preliminary_lesa",
            _call_args(24),
            _history(_answer(valid_site_assessment_criteria_resource, band_id="range_20_90_2")),
            _criteria(valid_site_assessment_criteria_resource),
        )
    with pytest.raises(SiteAssessmentGateError):
        validate_site_assessment_call(
            "calculate_preliminary_lesa",
            _call_args("skipped"),
            _history(
                _answer(
                    valid_site_assessment_criteria_resource,
                    state="unknown",
                    band_id="unknown",
                )
            ),
            _criteria(valid_site_assessment_criteria_resource),
        )
    with pytest.raises(SiteAssessmentGateError):
        validate_site_assessment_call(
            "calculate_preliminary_lesa",
            _call_args(24),
            _history(_answer(valid_site_assessment_criteria_resource), confirmed=False),
            _criteria(valid_site_assessment_criteria_resource),
        )


def test_assistant_authored_summary_is_not_user_confirmation(
    valid_site_assessment_criteria_resource,
):
    history = _history(_answer(valid_site_assessment_criteria_resource))
    history[0]["role"] = "assistant"

    with pytest.raises(SiteAssessmentGateError):
        validate_site_assessment_call(
            "calculate_preliminary_lesa",
            _call_args(24),
            history,
            _criteria(valid_site_assessment_criteria_resource),
        )


def test_model_supplied_points_do_not_override_registry_band_points(
    valid_site_assessment_criteria_resource,
):
    answer = _answer(valid_site_assessment_criteria_resource)
    answer["points"] = 900
    answer["selected_band"]["points"] = 900
    arguments = _call_args(24)

    result = validate_site_assessment_call(
        "calculate_preliminary_lesa",
        arguments,
        _history(answer),
        _criteria(valid_site_assessment_criteria_resource),
    )

    assert result["site_assessment_inputs"] == {"criteria_facts": {"1": {"percentage": 24}}}


def test_model_supplied_point_overrides_are_rejected(
    valid_site_assessment_criteria_resource,
):
    answer = _answer(valid_site_assessment_criteria_resource)
    arguments = _call_args(24)
    arguments["site_assessment_inputs"]["criteria_inputs"] = {"1": {"awarded_points": 900}}

    with pytest.raises(SiteAssessmentGateError):
        validate_site_assessment_call(
            "calculate_preliminary_lesa",
            arguments,
            _history(answer),
            _criteria(valid_site_assessment_criteria_resource),
        )


def test_corridor_calculation_is_outside_the_site_assessment_gate(
    valid_site_assessment_criteria_resource,
):
    arguments = {"project_type": "corridor"}

    assert (
        validate_site_assessment_call(
            "calculate_preliminary_lesa",
            arguments,
            [],
            _criteria(valid_site_assessment_criteria_resource),
        )
        == arguments
    )
