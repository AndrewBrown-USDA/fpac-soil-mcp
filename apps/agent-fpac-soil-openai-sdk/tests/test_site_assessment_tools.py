import asyncio
import json

import pytest
from agent_server.agent import (
    _site_assessment_criteria_context,
    _site_assessment_payload_from_context,
)
from agent_server.site_assessment_tools import create_site_assessment_tools
from agents.tool import ToolContext


def _tools(valid_site_assessment_criteria_resource):
    context = _site_assessment_criteria_context(valid_site_assessment_criteria_resource)
    payload = _site_assessment_payload_from_context(context)
    return create_site_assessment_tools(payload)


def _invoke(tool, arguments):
    serialized = json.dumps(arguments)
    context = ToolContext(
        {},
        tool_name=tool.name,
        tool_call_id="test-call",
        tool_arguments=serialized,
    )
    return json.loads(asyncio.run(tool.on_invoke_tool(context, serialized)))


def test_question_tool_returns_only_registry_defined_question_and_schedule(
    valid_site_assessment_criteria_resource,
):
    question_tool, answer_tool = _tools(valid_site_assessment_criteria_resource)

    question = _invoke(question_tool, {"criterion_number": 1})
    criterion = json.loads(valid_site_assessment_criteria_resource.contents[0].text)["criteria"][0]

    assert question["question"] == criterion["question"]
    assert question["citation"] == criterion["citation"]
    assert question["choices"] == criterion["bands"]
    assert question["max_points"] == criterion["max_points"]
    assert answer_tool.params_json_schema["additionalProperties"] is False
    assert "points" not in answer_tool.params_json_schema["properties"]


def test_answer_record_derives_points_and_preserves_provenance(
    valid_site_assessment_criteria_resource,
):
    _, answer_tool = _tools(valid_site_assessment_criteria_resource)

    record = _invoke(
        answer_tool,
        {
            "criterion_number": 1,
            "answer_state": "answered",
            "answer": 24.0,
            "evidence": "user measurement",
            "comment": "field note",
            "provenance": "user",
        },
    )

    assert record["type"] == "site_assessment_answer"
    assert record["answer"] == record["selected_band"]["id"] == "range_20_90_1"
    assert record["selected_band"]["id"] == "range_20_90_1"
    assert record["points"] == record["selected_band"]["points"] == 1
    assert record["evidence"] == "user measurement"
    assert record["comment"] == "field note"
    assert record["provenance"] == "user"


def test_answer_record_accepts_card_band_id_and_keeps_canonical_answer(
    valid_site_assessment_criteria_resource,
):
    _, answer_tool = _tools(valid_site_assessment_criteria_resource)

    record = _invoke(
        answer_tool,
        {
            "criterion_number": 1,
            "answer_state": "answered",
            "answer": "range_20_90_1",
            "evidence": "verified local trial evidence",
            "comment": "card submitted the registry band ID",
            "provenance": "user",
        },
    )

    assert record["answer"] == "range_20_90_1"
    assert record["selected_band"]["id"] == "range_20_90_1"
    assert record["points"] == 1


def test_answer_record_preserves_verification_sources_and_justification(
    valid_site_assessment_criteria_resource,
):
    _, answer_tool = _tools(valid_site_assessment_criteria_resource)

    record = _invoke(
        answer_tool,
        {
            "criterion_number": 1,
            "answer_state": "answered",
            "answer": 24.0,
            "evidence": "field observation",
            "comment": "checked with the assessor",
            "provenance": "user",
            "is_verified": True,
            "source_provenance": ["county land-use map", "field record"],
            "justification": "These sources establish the reported percentage.",
        },
    )

    assert record["is_verified"] is True
    assert record["source_provenance"] == ["county land-use map", "field record"]
    assert record["justification"] == "These sources establish the reported percentage."


@pytest.mark.parametrize(
    ("answer_state", "provenance"),
    [("unknown", "agent"), ("skipped", "tool")],
)
def test_unknown_and_skipped_states_are_structured_records(
    valid_site_assessment_criteria_resource, answer_state, provenance
):
    _, answer_tool = _tools(valid_site_assessment_criteria_resource)

    record = _invoke(
        answer_tool,
        {
            "criterion_number": 1,
            "answer_state": answer_state,
            "answer": None,
            "evidence": "",
            "comment": "",
            "provenance": provenance,
        },
    )

    assert record["answer_state"] == answer_state
    assert record["provenance"] == provenance
    if answer_state == "unknown":
        assert record["selected_band"]["id"] == "unknown"
        assert record["points"] is None
    else:
        assert record["selected_band"] is None
        assert record["points"] is None


@pytest.mark.parametrize(
    ("answer_state", "answer"),
    [
        ("unknown", "unknown"),
        ("unknown", " Unknown "),
        ("unknown", ""),
        ("skipped", "skipped"),
        ("skipped", ""),
    ],
)
def test_unknown_and_skipped_accept_placeholder_answer(
    valid_site_assessment_criteria_resource, answer_state, answer
):
    # Trace 9223a54c: the model sent answer="unknown" with answer_state="unknown"; the
    # tool raised, the run aborted, and the unanswered tool call broke later turns.
    _, answer_tool = _tools(valid_site_assessment_criteria_resource)

    record = _invoke(
        answer_tool,
        {
            "criterion_number": 1,
            "answer_state": answer_state,
            "answer": answer,
            "evidence": "",
            "comment": "User stated only below average.",
            "provenance": "user",
        },
    )

    assert record["answer_state"] == answer_state
    assert record["points"] is None
    if answer_state == "unknown":
        assert record["selected_band"]["id"] == "unknown"
    else:
        assert record["selected_band"] is None
        assert record["answer"] is None


@pytest.mark.parametrize(
    ("answer_state", "answer"),
    [
        ("unknown", "below_20"),
        ("unknown", 24.0),
        ("skipped", "unknown"),
        ("skipped", 24.0),
    ],
)
def test_unknown_and_skipped_still_reject_real_values(
    valid_site_assessment_criteria_resource, answer_state, answer
):
    _, answer_tool = _tools(valid_site_assessment_criteria_resource)
    with pytest.raises(ValueError, match="must not include a criterion value"):
        _invoke(
            answer_tool,
            {
                "criterion_number": 1,
                "answer_state": answer_state,
                "answer": answer,
                "evidence": "",
                "comment": "",
                "provenance": "user",
            },
        )


def test_answer_tool_rejects_non_resource_choice(valid_site_assessment_criteria_resource):
    _, answer_tool = _tools(valid_site_assessment_criteria_resource)
    with pytest.raises(ValueError, match="resource-defined"):
        _invoke(
            answer_tool,
            {
                "criterion_number": 1,
                "answer_state": "answered",
                "answer": -1,
                "evidence": "",
                "comment": "",
                "provenance": "user",
            },
        )


def test_answer_tool_rejects_model_supplied_points(valid_site_assessment_criteria_resource):
    _, answer_tool = _tools(valid_site_assessment_criteria_resource)
    arguments = {
        "criterion_number": 1,
        "answer_state": "answered",
        "answer": 24.0,
        "evidence": "",
        "comment": "",
        "provenance": "user",
        "points": 100,
    }

    with pytest.raises((TypeError, ValueError)):
        _invoke(answer_tool, arguments)
