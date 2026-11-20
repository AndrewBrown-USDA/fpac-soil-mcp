import asyncio
import json

import pytest
from agent_server.agent import (
    _site_assessment_criteria_context,
    _site_assessment_payload_from_context,
)
from agent_server.site_assessment_gate import (
    SiteAssessmentGateError,
    _band_for_fact,
    _canonical_answers,
    validate_site_assessment_call,
)
from agent_server.site_assessment_tools import (
    _representative_value,
    create_site_assessment_tools,
)
from agents.tool import ToolContext


def _payload(valid_site_assessment_criteria_resource):
    context = _site_assessment_criteria_context(valid_site_assessment_criteria_resource)
    return _site_assessment_payload_from_context(context)


def _tools(valid_site_assessment_criteria_resource):
    """The question and answer tools."""
    return create_site_assessment_tools(_payload(valid_site_assessment_criteria_resource))[:2]


def _named_tools(payload, history=None):
    return {tool.name: tool for tool in create_site_assessment_tools(payload, history)}


def _invoke_raw(tool, serialized):
    context = ToolContext(
        {},
        tool_name=tool.name,
        tool_call_id="test-call",
        tool_arguments=serialized,
    )
    return asyncio.run(tool.on_invoke_tool(context, serialized))


def _invoke(tool, arguments):
    return json.loads(_invoke_raw(tool, json.dumps(arguments)))


def _invoke_error(tool, arguments):
    # Tool failures come back as the tool result so the run continues (trace 9223a54c).
    result = _invoke_raw(tool, json.dumps(arguments))
    assert isinstance(result, str)
    assert result.startswith("Site Assessment tool error: ")
    return result


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
    assert record["answer"] is None
    if answer_state == "unknown":
        assert record["selected_band"]["id"] == "unknown"
    else:
        assert record["selected_band"] is None


@pytest.mark.parametrize("answer_state", ["unknown", "skipped"])
def test_unknown_and_skipped_records_pass_the_confirmation_gate(
    valid_site_assessment_criteria_resource, answer_state
):
    # The gate rejects unknown records whose answer is not null, as the card sends.
    context = _site_assessment_criteria_context(valid_site_assessment_criteria_resource)
    payload = _site_assessment_payload_from_context(context)
    answer_tool = _named_tools(payload)["record_site_assessment_answer"]

    record = _invoke(
        answer_tool,
        {"criterion_number": 1, "answer_state": answer_state, "answer": None},
    )

    assert _canonical_answers([record], payload)[1]["answer_state"] == answer_state


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
    message = _invoke_error(
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
    assert "must not include a criterion value" in message


def test_answer_tool_rejects_non_resource_choice(valid_site_assessment_criteria_resource):
    _, answer_tool = _tools(valid_site_assessment_criteria_resource)
    message = _invoke_error(
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
    assert "resource-defined" in message


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

    assert "unsupported fields" in _invoke_error(answer_tool, arguments)


def test_question_tool_reports_unknown_criterion_to_the_model(
    valid_site_assessment_criteria_resource,
):
    question_tool, _ = _tools(valid_site_assessment_criteria_resource)

    message = _invoke_error(question_tool, {"criterion_number": 99})

    assert "must identify a Site Assessment criterion" in message


def test_answer_tool_reports_invalid_arguments_to_the_model(
    valid_site_assessment_criteria_resource,
):
    _, answer_tool = _tools(valid_site_assessment_criteria_resource)

    message = _invoke_error(
        answer_tool,
        {"criterion_number": 1, "answer_state": "not-a-state", "answer": None},
    )

    assert "record_site_assessment_answer" in message


def test_answer_tool_reports_non_object_arguments_to_the_model(
    valid_site_assessment_criteria_resource,
):
    _, answer_tool = _tools(valid_site_assessment_criteria_resource)

    result = _invoke_raw(answer_tool, "not json")

    assert result.startswith("Site Assessment tool error: ")


def _answered_band(criterion):
    return next(
        band
        for band in criterion["bands"]
        if band["points"] is not None and band["id"] not in {"unknown", "skipped"}
    )


def _unknown_and_skipped_numbers(payload):
    unknown = next(
        criterion["criterion_number"]
        for criterion in payload["criteria"]
        if any(band["id"] == "unknown" for band in criterion["bands"])
    )
    skipped = next(
        criterion["criterion_number"]
        for criterion in reversed(payload["criteria"])
        if criterion["criterion_number"] != unknown
    )
    return unknown, skipped


def _answer_arguments(payload, number, unknown, skipped):
    criterion = next(c for c in payload["criteria"] if c["criterion_number"] == number)
    if number == unknown:
        return {"criterion_number": number, "answer_state": "unknown", "answer": None}
    if number == skipped:
        return {"criterion_number": number, "answer_state": "skipped", "answer": None}
    return {
        "criterion_number": number,
        "answer_state": "answered",
        "answer": _answered_band(criterion)["id"],
        "evidence": "observed",
    }


def _record_all(tools, payload):
    unknown, skipped = _unknown_and_skipped_numbers(payload)
    return [
        _invoke(
            tools["record_site_assessment_answer"],
            _answer_arguments(payload, criterion["criterion_number"], unknown, skipped),
        )
        for criterion in payload["criteria"]
    ]


def _calculate_arguments(summary):
    return {"project_type": "site", "site_assessment_inputs": summary["calculation_inputs"]}


def test_summary_names_criteria_without_a_recorded_answer(
    valid_site_assessment_criteria_resource,
):
    payload = _payload(valid_site_assessment_criteria_resource)
    tools = _named_tools(payload)
    unknown, skipped = _unknown_and_skipped_numbers(payload)
    _invoke(tools["record_site_assessment_answer"], _answer_arguments(payload, 1, unknown, skipped))

    result = _invoke_error(tools["show_site_assessment_summary"], {})

    assert "Criteria without a recorded answer: 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12." in result


def test_card_confirmation_of_the_summary_passes_the_calculation_gate(
    valid_site_assessment_criteria_resource,
):
    # Session 5595f300: all 12 answers were recorded, but the model wrote a markdown
    # summary, so no card could confirm it and every calculation was refused.
    payload = _payload(valid_site_assessment_criteria_resource)
    tools = _named_tools(payload)
    records = _record_all(tools, payload)

    summary = _invoke(tools["show_site_assessment_summary"], {})

    assert summary["type"] == "site_assessment_confirmed_summary"
    assert summary["confirmed"] is False
    assert summary["answers"] == records
    assert list(summary["calculation_inputs"]["criteria_facts"]) == [
        str(number) for number in range(1, 13)
    ]
    # The card's Confirm sends the summary back as a user message with confirmed true.
    confirmation = {"role": "user", "content": json.dumps({**summary, "confirmed": True})}
    arguments = _calculate_arguments(summary)

    assert (
        validate_site_assessment_call(
            "calculate_preliminary_lesa", arguments, [confirmation], payload
        )
        == arguments
    )


def test_summary_tool_output_alone_is_not_a_confirmation(
    valid_site_assessment_criteria_resource,
):
    payload = _payload(valid_site_assessment_criteria_resource)
    tools = _named_tools(payload)
    _record_all(tools, payload)
    output = _invoke_raw(tools["show_site_assessment_summary"], "{}")
    history = [
        {"role": "user", "content": "confirm"},
        {
            "type": "function_call",
            "call_id": "call_summary",
            "name": "show_site_assessment_summary",
            "arguments": "{}",
        },
        {"type": "function_call_output", "call_id": "call_summary", "output": output},
    ]

    with pytest.raises(SiteAssessmentGateError, match="press Confirm"):
        validate_site_assessment_call(
            "calculate_preliminary_lesa",
            _calculate_arguments(json.loads(output)),
            history,
            payload,
        )


def test_summary_reads_answers_recorded_in_earlier_turns(
    valid_site_assessment_criteria_resource,
):
    payload = _payload(valid_site_assessment_criteria_resource)
    records = _record_all(_named_tools(payload), payload)
    criterion1 = payload["criteria"][0]
    replacement_band = next(
        band
        for band in criterion1["bands"]
        if band["points"] is not None and band["id"] != records[0]["answer"]
    )
    replacement = _invoke(
        _named_tools(payload)["record_site_assessment_answer"],
        {
            "criterion_number": 1,
            "answer_state": "answered",
            "answer": replacement_band["id"],
        },
    )
    history = []
    for index, record in enumerate([*records, replacement]):
        call_id = f"call_{index}"
        output = json.dumps(record)
        if index == 0:
            # Replayed outputs can also arrive as a list of text parts.
            output = [{"type": "input_text", "text": output}]
        history += [
            {
                "type": "function_call",
                "call_id": call_id,
                "name": "record_site_assessment_answer",
                "arguments": "{}",
            },
            {"type": "function_call_output", "call_id": call_id, "output": output},
        ]
    # Answer-shaped output from any other tool is not a recorded answer.
    decoy = {**replacement, "criterion_number": 2}
    history += [
        {
            "type": "function_call",
            "call_id": "call_other",
            "name": "get_site_assessment_question",
            "arguments": "{}",
        },
        {"type": "function_call_output", "call_id": "call_other", "output": json.dumps(decoy)},
    ]

    summary = _invoke(_named_tools(payload, history)["show_site_assessment_summary"], {})

    assert summary["answers"] == [replacement, *records[1:]]


def test_summary_rejects_arguments(valid_site_assessment_criteria_resource):
    payload = _payload(valid_site_assessment_criteria_resource)
    tools = _named_tools(payload)
    _record_all(tools, payload)

    result = _invoke_raw(tools["show_site_assessment_summary"], json.dumps({"answers": []}))

    assert result.startswith("Site Assessment tool error: ")


def test_every_percentage_band_value_maps_back_to_its_band(
    valid_site_assessment_criteria_resource,
):
    payload = _payload(valid_site_assessment_criteria_resource)
    checked = 0
    for criterion in payload["criteria"]:
        if criterion["answer_type"] != "percentage":
            continue
        for band in criterion["bands"]:
            if band["points"] is None or "min" not in band:
                continue
            fact = {"value": _representative_value(band)}
            matched = _band_for_fact(payload, criterion["criterion_number"], fact)
            assert matched is not None and matched["id"] == band["id"], (
                criterion["criterion_number"],
                band["id"],
                fact,
            )
            checked += 1
    assert checked > 0
