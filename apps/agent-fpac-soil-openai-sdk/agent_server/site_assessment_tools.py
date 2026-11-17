"""Function tools for a resource-backed Site Assessment interview."""

from __future__ import annotations

import json
from typing import Any, Literal

from agents import FunctionTool, function_tool


def create_site_assessment_tools(criteria_payload: dict[str, Any]) -> list[FunctionTool]:
    """Create interview tools from criteria already validated by the MCP resource path."""
    criteria = {item["criterion_number"]: item for item in criteria_payload["criteria"]}

    @function_tool(
        name_override="get_site_assessment_question",
        failure_error_function=None,
        description_override=(
            "Before presenting each Site Assessment criterion, call this tool with its number. "
            "Return that authoritative question, citation, resource-defined answer choices, "
            "and point schedule. Do not compose or reuse questions or choices from memory."
        ),
    )
    async def get_site_assessment_question(criterion_number: int) -> str:
        criterion = criteria.get(criterion_number)
        if criterion is None:
            raise ValueError("criterion_number must identify a Site Assessment criterion.")
        return json.dumps(
            {
                "criterion_number": criterion["criterion_number"],
                "name": criterion["name"],
                "question": criterion["question"],
                "citation": criterion["citation"],
                "answer_type": criterion["answer_type"],
                "choices": criterion["bands"],
                "max_points": criterion["max_points"],
                "requires_rationale": criterion["requires_rationale"],
                "requires_verification": criterion["requires_verification"],
            },
            ensure_ascii=False,
        )

    @function_tool(
        name_override="record_site_assessment_answer",
        failure_error_function=None,
        description_override=(
            "Record one Site Assessment answer using a choice from the authoritative "
            "criteria resource. Do not provide points; points come only from that resource."
        ),
    )
    async def record_site_assessment_answer(
        criterion_number: int,
        answer_state: Literal["answered", "unknown", "skipped"],
        answer: str | float | None,
        evidence: str = "",
        comment: str = "",
        provenance: Literal["user", "agent", "tool"] = "user",
        is_verified: bool = False,
        source_provenance: list[str] | None = None,
        justification: str = "",
    ) -> str:
        """Record one choice and its evidence/provenance; points are registry-derived."""
        criterion = criteria.get(criterion_number)
        if criterion is None:
            raise ValueError("criterion_number must identify a Site Assessment criterion.")

        selected_band = None
        if answer_state == "answered":
            if answer is None:
                raise ValueError("An answered criterion requires an answer.")
            selected_band = _find_band(criterion, answer)
            if selected_band is None:
                raise ValueError("Answer must match a resource-defined Site Assessment choice.")
        elif answer is not None:
            raise ValueError("Unknown or skipped answers must not include a criterion value.")
        elif answer_state == "unknown":
            selected_band = next(
                (band for band in criterion["bands"] if band["id"] == "unknown"),
                None,
            )

        record = {
            "type": "site_assessment_answer",
            "criterion_number": criterion_number,
            "answer_state": answer_state,
            "answer": selected_band["id"] if selected_band is not None else None,
            "selected_band": selected_band,
            "points": selected_band["points"] if selected_band is not None else None,
            "evidence": evidence,
            "comment": comment,
            "provenance": provenance,
            "is_verified": is_verified,
            "source_provenance": source_provenance or [],
            "justification": justification,
        }
        return json.dumps(record, ensure_ascii=False)

    return [
        _reject_unknown_parameters(get_site_assessment_question, {"criterion_number"}),
        _reject_unknown_parameters(
            record_site_assessment_answer,
            {
                "criterion_number",
                "answer_state",
                "answer",
                "evidence",
                "comment",
                "provenance",
                "is_verified",
                "source_provenance",
                "justification",
            },
        ),
    ]


def _reject_unknown_parameters(tool: FunctionTool, allowed_parameters: set[str]) -> FunctionTool:
    invoke_tool = tool.on_invoke_tool

    async def invoke(context: Any, raw_arguments: str) -> Any:
        arguments = json.loads(raw_arguments)
        if not isinstance(arguments, dict) or set(arguments) - allowed_parameters:
            raise ValueError("Tool arguments contain unsupported fields.")
        return await invoke_tool(context, raw_arguments)

    tool.on_invoke_tool = invoke
    return tool


def _find_band(criterion: dict[str, Any], answer: str | float) -> dict[str, Any] | None:
    normalized = str(answer).strip().casefold()
    named_band = next(
        (
            band
            for band in criterion["bands"]
            if normalized in {band["id"].casefold(), band["label"].strip().casefold()}
        ),
        None,
    )
    if named_band is not None or criterion["answer_type"] == "qualitative":
        return named_band

    try:
        value = float(answer)
    except (TypeError, ValueError):
        return None
    for band in criterion["bands"]:
        if band["points"] is None or "min" not in band:
            continue
        lower = band["min"]
        upper = band.get("max")
        lower_matches = value > lower or (band.get("min_inclusive", True) and value == lower)
        upper_matches = (
            upper is None or value < upper or (band.get("max_inclusive", False) and value == upper)
        )
        if lower_matches and upper_matches:
            return band
    return None
