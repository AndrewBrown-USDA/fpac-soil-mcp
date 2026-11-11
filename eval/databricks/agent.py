"""T1 in-process agent: Chat Completions over the in-memory FastMCP server, traced with MLflow.

Implements contract C4 in `planning/EXECUTION_PLAN_33.md`. The server under test is the
checked-out code (`create_mcp_server`); upstream SDA/TIGERweb/NASS calls still go live.

`mlflow`, `openai`, and `databricks.sdk` are imported lazily so this module imports
without the `eval-databricks` dependency group.

Tracing and privacy: the root AGENT span (``@mlflow.trace`` on ``predict``) records the
plain-text request and the plain-text answer. It does not pass through ``_sanitize``,
because ``privacy.sanitize_public_payload`` drops prohibited *keys* and has nothing to
strip from a plain string. TOOL spans carry structured arguments and results and are
always sanitized. T1 must only be run on known synthetic or public cases, never on
producer data.
"""

from __future__ import annotations

import asyncio
import contextvars
import json
import re
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from common.dataset import case_forces_tool_use

from fpac_soil_mcp.app import create_mcp_server
from fpac_soil_mcp.privacy import sanitize_public_payload
from fpac_soil_mcp.prompts.fppa_prompts import FPPA_POLICY_BLOCK

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
_PROMPT_FILE = re.compile(r"^system_prompt_(v\d+)\.txt$")
_FORCED_BLOCK = re.compile(r"\[forced-tool\]\n?(.*?)\[/forced-tool\]\n?", re.DOTALL)

READ_RESOURCE = "read_resource"
GET_PROMPT = "get_prompt"


# v1 named fppa://regulatory-notice as an example resource, which led the agent to
# re-read the notice on every row; v2 drops that line (tool descriptions list URIs).
DEFAULT_PROMPT_VERSION = "v3"


def available_prompt_versions() -> list[str]:
    """Return system prompt versions present in `prompts/` (e.g. ``["v1"]``)."""
    versions = [m.group(1) for p in PROMPTS_DIR.iterdir() if (m := _PROMPT_FILE.match(p.name))]
    return sorted(versions, key=lambda v: int(v[1:]))


def load_system_prompt(
    version: str = DEFAULT_PROMPT_VERSION, *, force_tool_use: bool = True
) -> str:
    """Load a versioned system prompt; drop the ``[forced-tool]`` block when not forcing."""
    if version not in available_prompt_versions():
        raise ValueError(
            f"Unknown system prompt version {version!r}; "
            f"available: {', '.join(available_prompt_versions())}"
        )
    text = (PROMPTS_DIR / f"system_prompt_{version}.txt").read_text(encoding="utf-8")
    marker = "{{FPPA_POLICY_BLOCK}}"
    if text.count(marker) != 1:
        raise ValueError(f"Prompt {version!r} must contain exactly one {marker} marker.")
    text = text.replace(marker, FPPA_POLICY_BLOCK.strip())
    replacement = (lambda m: m.group(1)) if force_tool_use else ""
    return _FORCED_BLOCK.sub(replacement, text).strip()


def chat_params(model: str) -> dict[str, Any]:
    """Deterministic sampling params for the agent model (D11).

    GPT-5 family endpoints reject function tools on Chat Completions unless reasoning is
    disabled, so ``reasoning_effort="none"`` is added for them.
    """
    params: dict[str, Any] = {"temperature": 0}
    if "gpt-5" in model:
        params["reasoning_effort"] = "none"
    return params


def _sanitize(payload: dict[str, Any]) -> dict[str, Any]:
    return sanitize_public_payload(payload).sanitized_payload


def _jsonable(value: Any) -> bool:
    try:
        json.dumps(value)
    except (TypeError, ValueError):
        return False
    return True


def _content_text(content: Any) -> str:
    items = content if isinstance(content, list) else [content]
    return "\n".join(str(getattr(item, "text", "") or "") for item in items if item is not None)


def _tool_result(result: Any) -> Any:
    """C4 result: structured_content, else JSON-able data, else joined text content."""
    if result.structured_content is not None:
        return result.structured_content
    if result.data is not None and _jsonable(result.data):
        return result.data
    return _content_text(result.content)


def _synthetic_tool_specs(resource_uris: list[str], prompt_names: list[str]) -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": READ_RESOURCE,
                "description": "Read an MCP resource by URI. Available: "
                + ", ".join(resource_uris),
                "parameters": {
                    "type": "object",
                    "properties": {"uri": {"type": "string", "description": "Resource URI"}},
                    "required": ["uri"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": GET_PROMPT,
                "description": "Render an MCP prompt template by name. Available: "
                + ", ".join(prompt_names),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Prompt name"},
                        "arguments": {
                            "type": "object",
                            "description": "Prompt arguments (string values)",
                        },
                    },
                    "required": ["name"],
                },
            },
        },
    ]


async def _discover(client: Any) -> tuple[list[dict], set[str]]:
    tools = await client.list_tools()
    resources = [str(r.uri) for r in await client.list_resources()]
    prompts = [p.name for p in await client.list_prompts()]
    specs = [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": tool.input_schema or {"type": "object", "properties": {}},
            },
        }
        for tool in tools
    ]
    return specs + _synthetic_tool_specs(resources, prompts), {tool.name for tool in tools}


async def _dispatch(client: Any, mcp_tools: set[str], name: str, args: dict) -> tuple[Any, bool]:
    """Run one tool call; return ``(result, is_error)``. Never raises."""
    try:
        if name == READ_RESOURCE:
            contents = await client.read_resource(str(args["uri"]))
            return _content_text(contents), False
        if name == GET_PROMPT:
            prompt_args = {k: str(v) for k, v in (args.get("arguments") or {}).items()}
            rendered = await client.get_prompt(str(args["name"]), prompt_args)
            messages = [
                {"role": str(m.role), "content": _content_text(m.content)}
                for m in rendered.messages
            ]
            return messages, False
        if name not in mcp_tools:
            return f"Unknown tool: {name}", True
        result = await client.call_tool(name, args, raise_on_error=False)
        return _tool_result(result), bool(result.is_error)
    except Exception as exc:  # noqa: BLE001 -- C4: tool errors go back to the model as text
        return f"{type(exc).__name__}: {exc}", True


def _parse_arguments(raw: str | None) -> tuple[dict, str | None]:
    try:
        parsed = json.loads(raw or "{}")
    except json.JSONDecodeError as exc:
        return {}, f"Invalid JSON arguments: {exc}"
    if not isinstance(parsed, dict):
        return {}, "Tool arguments must be a JSON object"
    return parsed, None


def _run_coroutine(coro_factory: Callable[[], Any]) -> Any:
    """Run a coroutine to completion, in a worker thread if a loop is already running."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro_factory())
    ctx = contextvars.copy_context()  # keep the active MLflow span for child spans
    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(ctx.run, lambda: asyncio.run(coro_factory())).result()


def _default_openai_client() -> Any:
    import warnings

    from databricks.sdk import WorkspaceClient

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        return WorkspaceClient().serving_endpoints.get_open_ai_client()


def build_agent(
    model: str,
    *,
    server_factory: Callable[[], Any] = create_mcp_server,
    client: Any = None,
    max_turns: int = 8,
    force_tool_use: bool = True,
    system_prompt_version: str = DEFAULT_PROMPT_VERSION,
) -> Callable[..., str]:
    """Build a traced ``predict(request) -> str`` for ``mlflow.genai.evaluate``."""
    import fastmcp
    import mlflow

    load_system_prompt(system_prompt_version, force_tool_use=force_tool_use)
    params = chat_params(model)
    llm = client if client is not None else _default_openai_client()

    async def run(
        request: str,
        case_force_tool_use: bool,
        max_tool_calls: int | None,
    ) -> str:
        system_prompt = load_system_prompt(
            system_prompt_version,
            force_tool_use=case_forces_tool_use(
                {"force_tool_use": case_force_tool_use, "max_tool_calls": max_tool_calls}
            ),
        )
        budget_exhausted = max_tool_calls is not None and max_tool_calls <= 0
        if budget_exhausted:
            system_prompt += (
                "\n\nThis evaluation case has a strict zero-call budget. Do not invoke MCP "
                "tools, read resources, or render prompts."
            )
        async with fastmcp.Client(server_factory()) as mcp:
            tool_specs, mcp_tools = await _discover(mcp)
            messages: list[dict[str, Any]] = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": request},
            ]
            calls_made = 0
            final_text = ""
            for _ in range(max_turns):
                # Withhold tools when the budget is exhausted so the model cannot call them.
                active_tools = None if budget_exhausted else tool_specs
                response = llm.chat.completions.create(
                    model=model, messages=messages, tools=active_tools, **params
                )
                message = response.choices[0].message
                final_text = message.content or ""
                tool_calls = list(message.tool_calls or [])
                if not tool_calls:
                    return final_text
                calls_made += len(tool_calls)
                if max_tool_calls is not None and calls_made >= max_tool_calls:
                    budget_exhausted = True
                messages.append(
                    {
                        "role": "assistant",
                        "content": message.content or "",
                        "tool_calls": [
                            {
                                "id": call.id,
                                "type": "function",
                                "function": {
                                    "name": call.function.name,
                                    "arguments": call.function.arguments or "{}",
                                },
                            }
                            for call in tool_calls
                        ],
                    }
                )
                for call in tool_calls:
                    name = call.function.name
                    args, arg_error = _parse_arguments(call.function.arguments)
                    with mlflow.start_span(name=name, span_type="TOOL") as span:
                        span.set_inputs(_sanitize(args))
                        if arg_error:
                            result, is_error = arg_error, True
                        else:
                            result, is_error = await _dispatch(mcp, mcp_tools, name, args)
                        span.set_outputs(_sanitize({"result": result, "is_error": is_error}))
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call.id,
                            "content": json.dumps(result, ensure_ascii=False, default=str),
                        }
                    )
            mlflow.update_current_trace(tags={"max_turns_reached": "true"})
            return final_text

    @mlflow.trace(name="fpac_soil_agent", span_type="AGENT")
    def predict(
        request: str,
        force_tool_use: bool = force_tool_use,
        max_tool_calls: int | None = None,
    ) -> str:
        return _run_coroutine(lambda: run(request, force_tool_use, max_tool_calls))

    return predict
