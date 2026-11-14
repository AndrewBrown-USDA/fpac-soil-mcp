"""Confirm-only validation for Site Assessment LESA calls."""

from __future__ import annotations

import json
import math
from collections.abc import Iterator
from typing import Any

from databricks_openai.agents import McpServer
from mcp.types import CallToolResult, TextContent

CALCULATE_TOOL = "calculate_preliminary_lesa"


class SiteAssessmentGateError(ValueError):
    """A Site Assessment call has no matching user-confirmed summary."""


def bind_site_assessment_gate(
    server: McpServer,
    history_items: list[dict[str, Any]],
    criteria_payload: dict[str, Any] | None,
) -> McpServer:
    """Guard site LESA calls at the MCP boundary; leave corridor calls unchanged."""
    original = server.call_tool

    async def call_tool(
        tool_name: str, arguments: dict[str, Any] | None, **kwargs: Any
    ) -> CallToolResult:
        if tool_name != CALCULATE_TOOL:
            return await original(tool_name, arguments, **kwargs)
        try:
            validated_arguments = validate_site_assessment_call(
                tool_name, arguments, history_items, criteria_payload
            )
        except SiteAssessmentGateError as exc:
            return CallToolResult(
                content=[TextContent(type="text", text=str(exc))],
                isError=True,
            )
        return await original(tool_name, validated_arguments, **kwargs)

    server.call_tool = call_tool
    return server


def validate_site_assessment_call(
    tool_name: str,
    arguments: dict[str, Any] | None,
    history_items: list[dict[str, Any]],
    criteria_payload: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Return unchanged arguments only when inputs match the latest confirmed summary."""
    if tool_name != CALCULATE_TOOL or (
        isinstance(arguments, dict) and arguments.get("project_type", "site") == "corridor"
    ):
        return arguments

    if not isinstance(arguments, dict) or criteria_payload is None:
        raise SiteAssessmentGateError(
            "Site Assessment confirmation and matching inputs are required before this calculation."
        )

    site_inputs = arguments.get("site_assessment_inputs")
    if not isinstance(site_inputs, dict):
        raise SiteAssessmentGateError(
            "Site Assessment inputs are required and must match a confirmed summary."
        )
    farm_acre_band = _criterion7_farm_acre_band(site_inputs, criteria_payload)
    criteria_facts = site_inputs.get("criteria_facts")
    if criteria_facts is None:
        criteria_facts = {}
    if not isinstance(criteria_facts, dict):
        raise SiteAssessmentGateError(
            "Resource-backed Site Assessment facts must be a criterion mapping."
        )
    if not criteria_facts and farm_acre_band is None:
        raise SiteAssessmentGateError(
            "Resource-backed Site Assessment facts are required to match the confirmed summary."
        )
    if site_inputs.get("criteria_inputs"):
        raise SiteAssessmentGateError(
            "Model-supplied Site Assessment points are not accepted; use resource-backed facts."
        )

    summary = _latest_summary(history_items)
    if summary is None or summary.get("confirmed") is not True:
        raise SiteAssessmentGateError(
            "Confirm the current Site Assessment summary before this calculation."
        )
    answers = summary.get("answers")
    if not isinstance(answers, list):
        raise SiteAssessmentGateError(
            "The confirmed Site Assessment summary has no valid answers array."
        )

    answer_by_number = _canonical_answers(answers, criteria_payload)
    facts_by_number = _normalize_fact_numbers(criteria_facts)
    expected_numbers = set(facts_by_number)
    if farm_acre_band is not None:
        criterion7_answer = answer_by_number.get(7)
        if (
            criterion7_answer is None
            or criterion7_answer["answer_state"] != "answered"
            or criterion7_answer["band_id"] != farm_acre_band["id"]
        ):
            raise SiteAssessmentGateError(
                "Farm-acre inputs must match a confirmed answered Criterion 7 band."
            )
        criterion7_fact = facts_by_number.get(7)
        if criterion7_fact is not None:
            fact_band = _band_for_fact(criteria_payload, 7, criterion7_fact)
            if fact_band is None or fact_band["id"] != farm_acre_band["id"]:
                raise SiteAssessmentGateError("Farm-acre and Criterion 7 fact inputs conflict.")
        expected_numbers.add(7)
    if set(answer_by_number) != expected_numbers:
        raise SiteAssessmentGateError(
            "Submitted Site Assessment inputs do not match the confirmed answers."
        )

    for number, answer in answer_by_number.items():
        fact = facts_by_number.get(number)
        if number == 7 and farm_acre_band is not None and fact is None:
            continue
        if fact is None:
            raise SiteAssessmentGateError(
                "Submitted Site Assessment inputs do not match the confirmed answers."
            )
        state = answer["answer_state"]
        if state == "answered":
            band = _band_for_fact(criteria_payload, number, fact)
            if band is None or band["id"] != answer["band_id"]:
                raise SiteAssessmentGateError(
                    "Submitted Site Assessment inputs do not match the confirmed answers."
                )
        elif state == "unknown":
            if _fact_status(fact) not in {
                "unknown",
                "unavailable",
                "not available",
                "not provided",
            }:
                raise SiteAssessmentGateError(
                    "Submitted Site Assessment inputs do not match the confirmed answer statuses."
                )
        elif _fact_status(fact) not in {"skipped", "skip"}:
            raise SiteAssessmentGateError(
                "Submitted Site Assessment inputs do not match the confirmed answer statuses."
            )

    return arguments


def _criterion7_farm_acre_band(
    site_inputs: dict[str, Any], criteria_payload: dict[str, Any]
) -> dict[str, Any] | None:
    project_acres = site_inputs.get("project_farm_acres")
    county_average = site_inputs.get("county_average_farm_acres")
    has_project_acres = project_acres is not None
    has_county_average = county_average is not None
    if has_project_acres != has_county_average:
        raise SiteAssessmentGateError(
            "project_farm_acres and county_average_farm_acres must be supplied together."
        )
    if not has_project_acres:
        return None
    if (
        not _is_finite_number(project_acres)
        or isinstance(project_acres, bool)
        or project_acres < 0
        or not _is_finite_number(county_average)
        or isinstance(county_average, bool)
        or county_average <= 0
    ):
        raise SiteAssessmentGateError("Farm-acre inputs must be finite and county acres positive.")
    try:
        percentage = project_acres / county_average * 100
    except OverflowError:
        raise SiteAssessmentGateError("Farm-acre ratio must be finite.") from None
    if not math.isfinite(percentage):
        raise SiteAssessmentGateError("Farm-acre ratio must be finite.")
    band = _band_for_fact(criteria_payload, 7, {"percentage": percentage})
    if band is None or band.get("points") is None:
        raise SiteAssessmentGateError(
            "Farm-acre inputs do not resolve to an available Criterion 7 registry band."
        )
    return band


def _is_finite_number(value: Any) -> bool:
    if not isinstance(value, int | float) or isinstance(value, bool):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _latest_summary(history_items: list[dict[str, Any]]) -> dict[str, Any] | None:
    summaries = [
        item
        for value in history_items
        if isinstance(value, dict) and value.get("role") == "user"
        for item in _walk_values(value)
        if isinstance(item, dict) and item.get("type") == "site_assessment_confirmed_summary"
    ]
    return summaries[-1] if summaries else None


def _walk_values(value: Any) -> Iterator[Any]:
    if isinstance(value, dict):
        yield value
        for nested in value.values():
            yield from _walk_values(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _walk_values(nested)
    elif isinstance(value, str):
        try:
            parsed = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return
        if isinstance(parsed, (dict, list)):
            yield from _walk_values(parsed)


def _canonical_answers(
    answers: list[Any], criteria_payload: dict[str, Any]
) -> dict[int, dict[str, Any]]:
    criteria = {
        criterion["criterion_number"]: criterion
        for criterion in criteria_payload.get("criteria", [])
        if isinstance(criterion, dict)
        and isinstance(criterion.get("criterion_number"), int)
        and not isinstance(criterion.get("criterion_number"), bool)
    }
    canonical: dict[int, dict[str, Any]] = {}
    for answer in answers:
        if not isinstance(answer, dict) or answer.get("type") != "site_assessment_answer":
            raise SiteAssessmentGateError(
                "The confirmed Site Assessment summary contains an invalid answer."
            )
        number = answer.get("criterion_number")
        if not isinstance(number, int) or isinstance(number, bool) or number not in criteria:
            raise SiteAssessmentGateError(
                "The confirmed Site Assessment summary contains an invalid criterion."
            )
        if number in canonical:
            raise SiteAssessmentGateError(
                "The confirmed Site Assessment summary contains duplicate criteria."
            )
        state = answer.get("answer_state")
        if state not in {"answered", "unknown", "skipped"}:
            raise SiteAssessmentGateError(
                "The confirmed Site Assessment summary contains an invalid answer status."
            )
        selected_band = answer.get("selected_band")
        band_id = None
        if state == "answered":
            if not isinstance(selected_band, dict):
                raise SiteAssessmentGateError(
                    "A confirmed answered criterion must select a resource-defined band."
                )
            band_id = selected_band.get("id")
            band = _band_by_id(criteria[number], band_id)
            if band is None or band_id in {"unknown", "skipped"} or answer.get("answer") != band_id:
                raise SiteAssessmentGateError(
                    "A confirmed answer must match a resource-defined band."
                )
        elif state == "unknown":
            if answer.get("answer") is not None:
                raise SiteAssessmentGateError("Unknown answers must not include a criterion value.")
            if not isinstance(selected_band, dict) or selected_band.get("id") != "unknown":
                raise SiteAssessmentGateError(
                    "Unknown answers must preserve the resource-defined unknown band."
                )
        elif answer.get("answer") is not None or selected_band is not None:
            raise SiteAssessmentGateError(
                "Skipped answers must preserve an empty selected band and value."
            )
        canonical[number] = {"answer_state": state, "band_id": band_id}
    if not canonical:
        raise SiteAssessmentGateError("The confirmed Site Assessment summary has no answers.")
    return canonical


def _normalize_fact_numbers(facts: dict[Any, Any]) -> dict[int, dict[str, Any]]:
    normalized: dict[int, dict[str, Any]] = {}
    for raw_number, fact in facts.items():
        try:
            number = int(raw_number)
        except (TypeError, ValueError):
            raise SiteAssessmentGateError(
                "Submitted Site Assessment facts contain an invalid criterion."
            ) from None
        if not 1 <= number <= 12 or number in normalized or not isinstance(fact, dict):
            raise SiteAssessmentGateError(
                "Submitted Site Assessment facts contain an invalid criterion."
            )
        normalized[number] = fact
    return normalized


def _fact_value(fact: dict[str, Any]) -> Any:
    for field in ("value", "answer", "percentage", "distance_miles", "category"):
        if field in fact and fact[field] is not None:
            return fact[field]
    return None


def _fact_status(fact: dict[str, Any]) -> str | None:
    value = _fact_value(fact)
    if not isinstance(value, str):
        return None
    return value.strip().casefold()


def _band_for_fact(
    criteria_payload: dict[str, Any], number: int, fact: dict[str, Any]
) -> dict[str, Any] | None:
    criteria = {
        criterion["criterion_number"]: criterion
        for criterion in criteria_payload.get("criteria", [])
        if isinstance(criterion, dict) and "criterion_number" in criterion
    }
    criterion = criteria.get(number)
    if criterion is None:
        return None
    value = _fact_value(fact)
    bands = criterion.get("bands")
    if not isinstance(bands, list):
        return None
    if criterion.get("answer_type") == "qualitative":
        normalized = str(value).strip().casefold()
        return next(
            (
                band
                for band in bands
                if isinstance(band, dict)
                and normalized
                in {
                    str(band.get("id", "")).casefold(),
                    str(band.get("label", "")).strip().casefold(),
                }
            ),
            None,
        )
    if isinstance(value, bool):
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numeric):
        return None
    for band in bands:
        if not isinstance(band, dict) or band.get("points") is None:
            continue
        lower = band.get("min")
        upper = band.get("max")
        if (
            lower is None
            or numeric < lower
            or (numeric == lower and not band.get("min_inclusive", True))
        ):
            continue
        if upper is not None and (
            numeric > upper or (numeric == upper and not band.get("max_inclusive", False))
        ):
            continue
        return band
    return None


def _band_by_id(criterion: dict[str, Any], band_id: Any) -> dict[str, Any] | None:
    bands = criterion.get("bands")
    if not isinstance(bands, list):
        return None
    return next(
        (band for band in bands if isinstance(band, dict) and band.get("id") == band_id),
        None,
    )
