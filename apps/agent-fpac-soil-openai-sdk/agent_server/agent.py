from __future__ import annotations

import json
import logging
import math
from collections.abc import AsyncGenerator
from contextlib import AsyncExitStack
from functools import lru_cache
from itertools import pairwise
from pathlib import Path
from typing import TYPE_CHECKING

import mlflow
from agents import (
    Agent,
    ModelSettings,
    Runner,
    set_default_openai_api,
    set_default_openai_client,
)
from agents.exceptions import UserError
from agents.mcp.server import MCPServerStreamableHttp
from agents.tracing import set_trace_processors
from databricks.sdk import WorkspaceClient
from databricks_openai import AsyncDatabricksOpenAI
from databricks_openai.agents import McpServer
from mcp.shared.exceptions import McpError
from mlflow.genai.agent_server import invoke, stream
from mlflow.types.responses import (
    ResponsesAgentRequest,
    ResponsesAgentResponse,
    ResponsesAgentStreamEvent,
)
from openai import AsyncOpenAI
from openai.types.shared import Reasoning

from agent_server.aoi_context import (
    ActiveAoi,
    bind_active_aoi,
    instruction_note,
    read_active_aoi,
)
from agent_server.config import (
    McpServerLookupError,
    agent_model,
    fpac_mcp_timeout_seconds,
    fpac_mcp_url,
    load_system_prompt,
    local_dev_enabled,
    local_llm_base_url,
    local_mlflow_tracing_enabled,
    local_mlflow_tracking_uri,
    uses_reasoning_effort_none,
)
from agent_server.history import normalize_history_items
from agent_server.site_assessment_gate import bind_site_assessment_gate
from agent_server.site_assessment_tools import create_site_assessment_tools
from agent_server.utils import get_session_id, process_agent_stream_events

if TYPE_CHECKING:
    from agent_server.corridor_context import ActiveCorridor

logger = logging.getLogger(__name__)

set_default_openai_api("chat_completions")
set_trace_processors([])  # MLflow's OpenAI Agents processor is installed only by explicit opt-in.
if not local_dev_enabled():
    mlflow.openai.autolog()
logging.getLogger("mlflow.utils.autologging_utils").setLevel(logging.ERROR)


TOOLS_UNAVAILABLE_NOTE = (
    "The fpac-soil-mcp tools are unavailable for this request. Tell the user you cannot run "
    "the screening right now; do not answer from memory."
)


FPAC_MCP_SERVER_NAME = "fpac-soil-mcp"
SITE_ASSESSMENT_CRITERIA_URI = "fppa://site-assessment-criteria"
SITE_ASSESSMENT_RESOURCE_UNAVAILABLE_NOTE = (
    "The validated Site Assessment criteria resource is unavailable or invalid for this turn. "
    "Do not conduct or score the Site Assessment interview from memory; tell the user the "
    "criteria are unavailable. Other available preliminary screening may continue."
)
RESOURCE_READ_USER_ERROR_PREFIX = "Failed to read resource on MCP server "
SITE_ASSESSMENT_CONTEXT_PREFIX = (
    "Authoritative, validated Site Assessment criteria resource "
    f"({SITE_ASSESSMENT_CRITERIA_URI}; use these questions and bands only):\n```json\n"
)


def _is_finite_number(value: object) -> bool:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _site_assessment_criteria_context(result: object) -> str:
    """Validate the MCP resource envelope and return its authoritative JSON as context."""
    contents = getattr(result, "contents", None)
    if not isinstance(contents, list):
        raise TypeError("Site Assessment resource has no content list.")
    text = next(
        (
            getattr(item, "text", None)
            for item in contents
            if isinstance(getattr(item, "text", None), str)
        ),
        None,
    )
    if text is None:
        raise ValueError("Site Assessment resource has no text content.")
    payload = json.loads(text)
    if not isinstance(payload, dict) or payload.get("schema_version") != "1.0":
        raise ValueError("Site Assessment resource has an unsupported schema.")
    criteria = payload.get("criteria")
    if not isinstance(criteria, list):
        raise TypeError("Site Assessment resource criteria must be a list.")
    if len(criteria) != 12:
        raise ValueError("Site Assessment resource must contain 12 criteria.")
    numbers: list[int] = []
    for criterion in criteria:
        if not isinstance(criterion, dict):
            raise TypeError("Site Assessment criterion is malformed.")
        number = criterion.get("criterion_number")
        bands = criterion.get("bands")
        answer_type = criterion.get("answer_type")
        max_points = criterion.get("max_points")
        if not isinstance(number, int) or isinstance(number, bool):
            raise TypeError("Site Assessment criterion number is malformed.")
        if answer_type not in {"percentage", "qualitative"}:
            raise ValueError("Site Assessment criterion answer type is unsupported.")
        if not _is_finite_number(max_points) or max_points < 0:
            raise ValueError("Site Assessment criterion maximum points are malformed.")
        question = criterion.get("question")
        citation = criterion.get("citation")
        if not isinstance(question, str) or not isinstance(citation, str):
            raise TypeError("Site Assessment question or citation is malformed.")
        if not question.strip() or not citation.strip():
            raise ValueError("Site Assessment question or citation is empty.")
        if not isinstance(bands, list):
            raise TypeError("Site Assessment scoring bands must be a list.")
        if not bands:
            raise ValueError("Site Assessment criterion has no scoring bands.")
        band_ids: set[str] = set()
        percentage_ranges: list[tuple[float, float | None, bool, bool, float]] = []
        for band in bands:
            if not isinstance(band, dict):
                raise TypeError("Site Assessment scoring band is malformed.")
            band_id = band.get("id")
            label = band.get("label")
            points = band.get("points")
            if not isinstance(band_id, str) or not band_id.strip():
                raise ValueError("Site Assessment scoring band ID is empty or malformed.")
            if band_id in band_ids:
                raise ValueError("Site Assessment scoring band IDs must be unique.")
            band_ids.add(band_id)
            if not isinstance(label, str) or not label.strip():
                raise ValueError("Site Assessment scoring band label is empty or malformed.")
            if "points" not in band or (
                points is not None
                and (not _is_finite_number(points) or points < 0 or points > max_points)
            ):
                raise ValueError("Site Assessment scoring band points are malformed.")

            bounds: dict[str, float] = {}
            for bound_name in ("min", "max"):
                if bound_name in band:
                    bound = band[bound_name]
                    if not _is_finite_number(bound) or bound < 0:
                        raise ValueError("Site Assessment scoring band bounds are malformed.")
                    bounds[bound_name] = float(bound)
            for bound_name, inclusive_name in (
                ("min", "min_inclusive"),
                ("max", "max_inclusive"),
            ):
                if inclusive_name in band and (
                    bound_name not in bounds or type(band[inclusive_name]) is not bool
                ):
                    raise ValueError("Site Assessment scoring band inclusivity is malformed.")

            if answer_type == "qualitative":
                if bounds or "min_inclusive" in band or "max_inclusive" in band:
                    raise ValueError(
                        "Qualitative Site Assessment bands cannot define numeric bounds."
                    )
            elif points is None:
                if bounds or "min_inclusive" in band or "max_inclusive" in band:
                    raise ValueError("Unscored percentage bands cannot define numeric bounds.")
            else:
                if "min" not in bounds:
                    raise ValueError("Scored percentage bands must define a lower bound.")
                lower = bounds["min"]
                upper = bounds.get("max")
                if upper is not None and lower > upper:
                    raise ValueError("Site Assessment scoring band bounds are reversed.")
                percentage_ranges.append(
                    (
                        lower,
                        upper,
                        band.get("min_inclusive", True),
                        band.get("max_inclusive", False),
                        float(points),
                    )
                )
        if answer_type == "percentage":
            percentage_ranges.sort(key=lambda bounds: bounds[0])
            if percentage_ranges and (
                not math.isclose(percentage_ranges[0][0], 0) or not percentage_ranges[0][2]
            ):
                raise ValueError("Percentage scoring bands must include zero.")
            for previous, current in pairwise(percentage_ranges):
                previous_max = previous[1]
                if previous_max is None:
                    raise ValueError("Percentage scoring bands cannot follow an unbounded band.")
                if not math.isclose(previous_max, current[0], rel_tol=0, abs_tol=1e-9):
                    raise ValueError("Percentage scoring band bounds contain a gap or overlap.")
                if previous[3] == current[2]:
                    raise ValueError("Adjacent percentage scoring bands have inconsistent bounds.")
                if current[4] < previous[4]:
                    raise ValueError("Percentage scoring band points do not follow their bounds.")
        numbers.append(number)
    if sorted(numbers) != list(range(1, 13)):
        raise ValueError("Site Assessment resource criterion numbers are incomplete.")
    return (
        f"{SITE_ASSESSMENT_CONTEXT_PREFIX}{json.dumps(payload, ensure_ascii=False, indent=2)}\n```"
    )


def _site_assessment_payload_from_context(context: str | None) -> dict | None:
    """Recover the payload only from the context string built by the validated resource path."""
    if not context or not context.startswith(SITE_ASSESSMENT_CONTEXT_PREFIX):
        return None
    serialized, separator, _ = context[len(SITE_ASSESSMENT_CONTEXT_PREFIX) :].partition("\n```")
    if not separator:
        return None
    payload = json.loads(serialized)
    if not isinstance(payload, dict) or not isinstance(payload.get("criteria"), list):
        return None
    return payload


@lru_cache(maxsize=1)
def configure_openai_client():
    """Configure the Databricks client once, when a real request needs it."""
    if local_dev_enabled():
        client = AsyncOpenAI(base_url=local_llm_base_url(), api_key="local-dev")
        set_default_openai_client(client)
        return client
    # This works for all Databricks models other than GPT-OSS, which uses a
    # slightly different API. AI Gateway routes UC model service names through
    # /ai-gateway/mlflow/v1.
    client = AsyncDatabricksOpenAI(use_ai_gateway=True)
    set_default_openai_client(client)
    return client


def configure_local_mlflow_tracing() -> bool:
    """Enable a local file-backed MLflow experiment only when explicitly requested."""
    global _local_mlflow_configured_uri
    if not local_dev_enabled() or not local_mlflow_tracing_enabled():
        return False
    tracking_uri = local_mlflow_tracking_uri()
    if tracking_uri.startswith("sqlite:///"):
        db_path = Path(tracking_uri.removeprefix("sqlite:///"))
        db_path.parent.mkdir(parents=True, exist_ok=True)
    if _local_mlflow_configured_uri == tracking_uri:
        return True
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment("fpac-soil-local")
    mlflow.openai.autolog()
    _local_mlflow_configured_uri = tracking_uri
    return True


_local_mlflow_configured_uri: str | None = None


def _update_trace_session(session_id: str | None) -> None:
    if session_id and (not local_dev_enabled() or local_mlflow_tracing_enabled()):
        mlflow.update_current_trace(metadata={"mlflow.trace.session": session_id})


def init_fpac_mcp_server(workspace_client: WorkspaceClient | None = None):
    """Build the client for the deployed fpac-soil-mcp server."""
    url = fpac_mcp_url(
        (lambda name: workspace_client.apps.get(name=name).url)
        if workspace_client is not None
        else None
    )
    if local_dev_enabled():
        return MCPServerStreamableHttp(
            name=FPAC_MCP_SERVER_NAME,
            params={"url": url, "timeout": fpac_mcp_timeout_seconds()},
        )
    return McpServer(
        # FPAC_MCP_APP (the ``mcp_server`` resource) resolves through the Apps API.
        url=url,
        name=FPAC_MCP_SERVER_NAME,
        workspace_client=workspace_client,
        timeout=fpac_mcp_timeout_seconds(),
    )


async def connect_healthy_mcp_servers(
    stack: AsyncExitStack, servers: list[McpServer]
) -> tuple[list[McpServer], list[str]]:
    """Connect each MCP server and verify it can actually list its tools.

    The Agents SDK lists each server's tools lazily inside ``Runner.run``, so a server that
    connects but fails at list time (e.g. an unauthorized Genie space) would otherwise crash
    the whole request — including unrelated turns. We list tools here, per server: healthy
    servers are kept; any that fails to connect OR to list is dropped and its name returned,
    so the agent runs with whatever is available instead of erroring out.

    Returns (healthy_servers, unavailable_names).
    """
    healthy: list[McpServer] = []
    unavailable: list[str] = []
    for server in servers:
        name = getattr(server, "name", "MCP server")
        try:
            connected = await stack.enter_async_context(server)
            await connected.list_tools()  # forces the connectivity + authorization check now
            healthy.append(connected)
        except Exception:
            logger.warning("MCP server %r unavailable; continuing without it.", name, exc_info=True)
            unavailable.append(name)
    return healthy, unavailable


def create_agent(
    mcp_servers: list[McpServer] | None = None,
    *,
    tools_unavailable: bool = False,
    aoi_note: str | None = None,
    corridor_note: str | None = None,
    site_assessment_context: str | None = None,
) -> Agent:
    """Build the FPAC Soil agent.

    The model comes from ``AGENT_MODEL``. GPT-5 models get ``reasoning_effort="none"``,
    which they need for tool calling. When ``tools_unavailable`` is set, the instructions
    tell the model to say so instead of answering from memory. ``aoi_note`` describes the
    map AOI attached to the conversation (ADR 0016); ``site_assessment_context`` is the
    validated criteria resource read from the MCP server for this turn.
    """
    configure_local_mlflow_tracing()
    model = agent_model()
    instructions = load_system_prompt()
    if tools_unavailable:
        instructions = f"{instructions}\n\n{TOOLS_UNAVAILABLE_NOTE}"
    else:
        if site_assessment_context:
            instructions = f"{instructions}\n\n{site_assessment_context}"
        if aoi_note:
            instructions = f"{instructions}\n\n{aoi_note}"
        if corridor_note:
            instructions = f"{instructions}\n\n{corridor_note}"
    if uses_reasoning_effort_none(model):
        model_settings = ModelSettings(reasoning=Reasoning(effort="none"))
    else:
        model_settings = ModelSettings()
    site_assessment_payload = None
    if not tools_unavailable:
        site_assessment_payload = _site_assessment_payload_from_context(site_assessment_context)
    tools = (
        create_site_assessment_tools(site_assessment_payload)
        if site_assessment_payload is not None
        else []
    )
    return Agent(
        name="FPAC Soil Agent",
        instructions=instructions,
        model=model,
        tools=tools,
        mcp_servers=mcp_servers or [],
        model_settings=model_settings,
    )


async def _connect_fpac_agent(
    stack: AsyncExitStack,
    aoi: ActiveAoi | None = None,
    history_items: list[dict] | None = None,
    corridor: ActiveCorridor | None = None,
) -> Agent:
    from agent_server.corridor_context import bind_active_corridor
    from agent_server.corridor_context import instruction_note as corridor_instruction_note

    # WorkspaceClient() authenticates as the app's service principal, not the user.
    # connect_healthy_mcp_servers drops a server that fails (and logs the warning with its
    # traceback), so the request still runs.
    try:
        server = init_fpac_mcp_server(None if local_dev_enabled() else WorkspaceClient())
    except McpServerLookupError as exc:
        # Same outcome as an unreachable server: the turn runs without tools.
        logger.warning("MCP server lookup failed: %s", exc)
        return create_agent(mcp_servers=[], tools_unavailable=True)
    if aoi is not None:
        bind_active_aoi(server, aoi)
    if corridor is not None:
        bind_active_corridor(server, corridor)
    servers, unavailable = await connect_healthy_mcp_servers(stack, [server])
    if unavailable:
        logger.info("MCP servers unavailable for this request: %s", ", ".join(unavailable))
        return create_agent(mcp_servers=servers, tools_unavailable=True)
    site_assessment_context = None
    try:
        resource = await server.read_resource(SITE_ASSESSMENT_CRITERIA_URI)
    except McpError:
        logger.warning(
            "Site Assessment resource request failed; interview disabled for this turn.",
            exc_info=True,
        )
        site_assessment_context = SITE_ASSESSMENT_RESOURCE_UNAVAILABLE_NOTE
    except UserError as exc:
        if not str(exc).startswith(RESOURCE_READ_USER_ERROR_PREFIX):
            raise
        logger.warning(
            "Site Assessment resource transport failed; interview disabled for this turn.",
            exc_info=True,
        )
        site_assessment_context = SITE_ASSESSMENT_RESOURCE_UNAVAILABLE_NOTE
    else:
        try:
            site_assessment_context = _site_assessment_criteria_context(resource)
        except (TypeError, ValueError):
            logger.warning(
                "Validated Site Assessment criteria unavailable; interview disabled for this turn.",
                exc_info=True,
            )
            site_assessment_context = SITE_ASSESSMENT_RESOURCE_UNAVAILABLE_NOTE
    bind_site_assessment_gate(
        server,
        history_items or [],
        _site_assessment_payload_from_context(site_assessment_context),
    )
    if corridor is not None:
        return create_agent(
            mcp_servers=servers,
            aoi_note=instruction_note(aoi) if aoi is not None else None,
            corridor_note=corridor_instruction_note(corridor),
            site_assessment_context=site_assessment_context,
        )
    if aoi is not None:
        return create_agent(
            mcp_servers=servers,
            aoi_note=instruction_note(aoi),
            site_assessment_context=site_assessment_context,
        )
    return create_agent(
        mcp_servers=servers,
        tools_unavailable=bool(unavailable),
        site_assessment_context=site_assessment_context,
    )


@invoke()
async def invoke_handler(request: ResponsesAgentRequest) -> ResponsesAgentResponse:
    _update_trace_session(get_session_id(request))
    configure_openai_client()
    messages = normalize_history_items([i.model_dump() for i in request.input])
    from agent_server.corridor_context import read_active_corridor

    # The AsyncExitStack keeps the MCP server open for the whole request.
    async with AsyncExitStack() as stack:
        agent = await _connect_fpac_agent(
            stack,
            read_active_aoi(request),
            messages,
            corridor=read_active_corridor(request),
        )
        result = await Runner.run(agent, messages)
        return ResponsesAgentResponse(output=[item.to_input_item() for item in result.new_items])


@stream()
async def stream_handler(
    request: ResponsesAgentRequest,
) -> AsyncGenerator[ResponsesAgentStreamEvent, None]:
    _update_trace_session(get_session_id(request))
    configure_openai_client()
    messages = normalize_history_items([i.model_dump() for i in request.input])
    from agent_server.corridor_context import read_active_corridor

    # The AsyncExitStack keeps the MCP server open for the whole request.
    async with AsyncExitStack() as stack:
        agent = await _connect_fpac_agent(
            stack,
            read_active_aoi(request),
            messages,
            corridor=read_active_corridor(request),
        )
        result = Runner.run_streamed(agent, input=messages)

        async for event in process_agent_stream_events(result.stream_events()):
            yield event
