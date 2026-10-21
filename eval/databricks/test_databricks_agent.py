"""Offline tests for the T1 agent (eval/databricks/agent.py).

A scripted fake OpenAI client stands in for the model endpoint, and only static MCP tools,
resources, and prompts are exercised, so no test makes a network call. MLflow traces go to a
throwaway local sqlite store.
"""

from __future__ import annotations

import json
import os
from types import SimpleNamespace
from typing import Any

import pytest

mlflow = pytest.importorskip("mlflow")

from agent import (
    DEFAULT_PROMPT_VERSION,
    GET_PROMPT,
    READ_RESOURCE,
    available_prompt_versions,
    build_agent,
    chat_params,
    load_system_prompt,
)

from fpac_soil_mcp.constants import REGULATORY_NOTICE


@pytest.fixture(scope="module", autouse=True)
def local_mlflow(tmp_path_factory: pytest.TempPathFactory):
    previous = os.environ.get("MLFLOW_ENABLE_ASYNC_TRACE_LOGGING")
    os.environ["MLFLOW_ENABLE_ASYNC_TRACE_LOGGING"] = "false"
    db = tmp_path_factory.mktemp("mlflow") / "mlflow.db"
    mlflow.set_tracking_uri(f"sqlite:///{db}")
    mlflow.set_experiment("t1-agent-tests")
    yield
    mlflow.set_tracking_uri(None)
    if previous is None:
        os.environ.pop("MLFLOW_ENABLE_ASYNC_TRACE_LOGGING", None)
    else:
        os.environ["MLFLOW_ENABLE_ASYNC_TRACE_LOGGING"] = previous


def _tool_call(index: int, name: str, arguments: Any) -> SimpleNamespace:
    raw = arguments if isinstance(arguments, str) else json.dumps(arguments)
    return SimpleNamespace(id=f"call_{index}", function=SimpleNamespace(name=name, arguments=raw))


class FakeLLM:
    """Scripted Chat Completions client. Steps: ("tools", [(name, args), ...]) or ("text", s).

    The last step repeats once the script is exhausted.
    """

    def __init__(self, *steps: tuple[str, Any]) -> None:
        self.steps = list(steps)
        self.calls: list[dict[str, Any]] = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs: Any) -> SimpleNamespace:
        self.calls.append(kwargs)
        kind, payload = self.steps[min(len(self.calls), len(self.steps)) - 1]
        if kind == "text":
            message = SimpleNamespace(content=payload, tool_calls=None)
        else:
            calls = [_tool_call(i, name, args) for i, (name, args) in enumerate(payload)]
            message = SimpleNamespace(content=None, tool_calls=calls)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def _run(llm: FakeLLM, request: str = "question", **kwargs: Any):
    predict = build_agent("databricks-gpt-5-6-luna", client=llm, **kwargs)
    answer = predict(request)
    trace = mlflow.get_trace(mlflow.get_last_active_trace_id())
    return answer, trace


def _tool_spans(trace) -> list:
    return [span for span in trace.data.spans if span.span_type == "TOOL"]


def test_v1_prompt_is_available_and_loads() -> None:
    assert "v1" in available_prompt_versions()
    forced = load_system_prompt("v1")
    unforced = load_system_prompt("v1", force_tool_use=False)

    assert "preliminary screening" in forced
    assert "You MUST call" in forced
    assert "You MUST call" not in unforced
    assert "[forced-tool]" not in forced + unforced
    assert "[/forced-tool]" not in forced + unforced


def test_v2_prompt_is_v1_without_the_resource_example_line() -> None:
    assert available_prompt_versions()[:2] == ["v1", "v2"]
    assert DEFAULT_PROMPT_VERSION == "v2"
    v1, v2 = load_system_prompt("v1"), load_system_prompt("v2")

    assert "fppa://regulatory-notice" in v1
    assert "fppa://regulatory-notice" not in v2
    removed = [line for line in v1.splitlines() if line not in v2.splitlines()]
    assert len(removed) == 1
    assert removed[0].startswith("Use read_resource")


def test_unknown_prompt_version_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown system prompt version 'v99'"):
        load_system_prompt("v99")
    with pytest.raises(ValueError):
        build_agent("m", client=FakeLLM(("text", "x")), system_prompt_version="v99")


def test_chat_params_are_deterministic_and_model_aware() -> None:
    assert chat_params("databricks-gpt-5-6-luna") == {"temperature": 0, "reasoning_effort": "none"}
    assert chat_params("databricks-claude-haiku-4-5") == {"temperature": 0}


def test_agent_calls_tool_then_answers_with_c4_trace() -> None:
    llm = FakeLLM(("tools", [("explain_fppa_screening_scope", {})]), ("text", "Final answer."))
    answer, trace = _run(llm, "Explain FPPA scope.")

    assert answer == "Final answer."
    root = next(span for span in trace.data.spans if span.parent_id is None)
    assert root.span_type == "AGENT"
    assert root.name == "fpac_soil_agent"

    spans = _tool_spans(trace)
    assert len(spans) == 1
    span = spans[0]
    assert span.name == "explain_fppa_screening_scope"
    assert span.parent_id == root.span_id
    assert span.inputs == {}
    assert set(span.outputs) == {"result", "is_error"}
    assert span.outputs["is_error"] is False
    assert span.outputs["result"]["regulatory_notice"] == REGULATORY_NOTICE

    first = llm.calls[0]
    assert first["model"] == "databricks-gpt-5-6-luna"
    assert first["temperature"] == 0
    assert first["reasoning_effort"] == "none"
    assert first["messages"][0] == {"role": "system", "content": load_system_prompt("v2")}
    assert first["messages"][1] == {"role": "user", "content": "Explain FPPA scope."}
    names = {spec["function"]["name"] for spec in first["tools"]}
    assert {READ_RESOURCE, GET_PROMPT, "get_farmland_classification_by_point"} <= names
    assert len(names) == 12

    tool_message = llm.calls[1]["messages"][-1]
    assert tool_message["role"] == "tool"
    assert tool_message["tool_call_id"] == "call_0"
    assert json.loads(tool_message["content"])["regulatory_notice"] == REGULATORY_NOTICE


def test_agent_span_shape_is_pinned() -> None:
    """AGENT root records plain request/answer text; TOOL spans hang off it (D1, K4)."""
    request = "Explain FPPA scope for a synthetic case."
    llm = FakeLLM(
        ("tools", [("explain_fppa_screening_scope", {}), ("list_farmland_classes", {})]),
        ("text", "Pinned final answer."),
    )
    answer, trace = _run(llm, request)

    root = next(span for span in trace.data.spans if span.parent_id is None)
    assert root.name == "fpac_soil_agent"
    assert root.span_type == "AGENT"
    assert request in json.dumps(root.inputs)
    assert answer == "Pinned final answer."
    assert answer in json.dumps(root.outputs)

    spans = _tool_spans(trace)
    assert [span.name for span in spans] == [
        "explain_fppa_screening_scope",
        "list_farmland_classes",
    ]
    assert all(span.parent_id == root.span_id for span in spans)


def test_read_resource_and_get_prompt_dispatch() -> None:
    llm = FakeLLM(
        (
            "tools",
            [
                (READ_RESOURCE, {"uri": "fppa://regulatory-notice"}),
                (GET_PROMPT, {"name": "fppa_screening_assistant", "arguments": {}}),
            ],
        ),
        ("text", "done"),
    )
    _, trace = _run(llm)

    resource_span, prompt_span = _tool_spans(trace)
    assert resource_span.name == READ_RESOURCE
    assert resource_span.inputs == {"uri": "fppa://regulatory-notice"}
    assert resource_span.outputs["is_error"] is False
    assert "7 CFR Part 657" in resource_span.outputs["result"]
    assert prompt_span.name == GET_PROMPT
    assert prompt_span.outputs["is_error"] is False
    assert prompt_span.outputs["result"][0]["content"]


def test_max_turns_is_honored() -> None:
    llm = FakeLLM(("tools", [("list_farmland_classes", {})]))
    answer, trace = _run(llm, max_turns=2)

    assert answer == ""
    assert len(llm.calls) == 2
    assert len(_tool_spans(trace)) == 2
    assert trace.info.tags.get("max_turns_reached") == "true"


def test_tool_errors_are_returned_to_the_model_not_raised() -> None:
    llm = FakeLLM(
        ("tools", [("no_such_tool", {"x": 1}), ("list_farmland_classes", "{not json")]),
        ("text", "recovered"),
    )
    answer, trace = _run(llm)

    assert answer == "recovered"
    unknown, bad_json = _tool_spans(trace)
    assert unknown.outputs == {"result": "Unknown tool: no_such_tool", "is_error": True}
    assert bad_json.outputs["is_error"] is True
    assert bad_json.outputs["result"].startswith("Invalid JSON arguments")


def test_span_payloads_are_sanitized() -> None:
    llm = FakeLLM(
        ("tools", [("no_such_tool", {"email": "person@example.com", "mukey": "1"})]),
        ("text", "ok"),
    )
    _, trace = _run(llm)

    (span,) = _tool_spans(trace)
    assert span.inputs == {"mukey": "1"}
