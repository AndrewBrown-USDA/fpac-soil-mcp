"""Conversation-history normalization helpers.

Kept dependency-free (no Databricks SDK / MLflow imports) so it can be unit
tested in isolation. This file is copied verbatim across the OpenAI Agents SDK
templates (agent-openai-agents-sdk, agent-openai-agents-sdk-multiagent,
agent-openai-advanced) — keep the copies in sync.
"""


def normalize_history_items(messages: list[dict]) -> list[dict]:
    """Normalize replayed assistant history items before passing them to Runner.run.

    Newer openai-agents converters only accept a typed assistant history item
    (``{"type": "message", "role": "assistant", ...}``) when it carries an
    ``id``, but clients replay the prior assistant turn without one: the
    built-in chat UI sends an id-less ``content`` list of ``output_text``
    parts, and MLflow evaluation sends plain-string ``content`` (MLflow's
    ``ResponsesAgentRequest`` has no ``id`` field, so any client-supplied id is
    stripped). Those items match no converter branch and raise
    ``UserError: Unhandled item type or structure`` on the second and later
    prompts.

    Collapse both shapes to the easy-input ``{"role", "content"}`` form, which
    every SDK version recognizes without an id. Multiple ``output_text``
    segments are joined with ``"\\n"`` to match the SDK converter's own
    behavior. Items that do carry an ``id`` alongside a content list are left
    untouched so the SDK's native handling (including ``refusal`` parts) still
    applies.
    """
    normalized: list[dict] = []
    for m in messages:
        if m.get("type") != "message" or m.get("role") != "assistant":
            normalized.append(m)
            continue
        content = m.get("content")
        if isinstance(content, str):
            normalized.append({"role": "assistant", "content": content})
        elif isinstance(content, list) and "id" not in m:
            text = "\n".join(
                part.get("text", "")
                for part in content
                if isinstance(part, dict) and part.get("type") == "output_text"
            )
            normalized.append({"role": "assistant", "content": text})
        else:
            normalized.append(m)
    return normalized


# Local addition (not in the upstream template copies).
ORPHAN_TOOL_CALL_OUTPUT = (
    "No result was recorded for this tool call because the earlier turn ended before "
    "the tool returned. Treat the call as not completed."
)


def repair_orphan_tool_calls(messages: list[dict]) -> list[dict]:
    """Add a placeholder output after each replayed ``function_call`` that has none.

    When a turn aborts mid-tool (for example a tool raised), the chat UI still replays
    the ``function_call`` but has no ``function_call_output`` for it. Chat Completions
    providers then reject every later request with HTTP 400 (an assistant
    ``tool_calls`` message must be followed by a tool message for each id), so the
    conversation cannot recover. Answered calls and all other items are unchanged.
    """
    answered = {m.get("call_id") for m in messages if m.get("type") == "function_call_output"}
    repaired: list[dict] = []
    for m in messages:
        repaired.append(m)
        call_id = m.get("call_id")
        if (
            m.get("type") == "function_call"
            and isinstance(call_id, str)
            and call_id
            and call_id not in answered
        ):
            repaired.append(
                {
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": ORPHAN_TOOL_CALL_OUTPUT,
                }
            )
            answered.add(call_id)
    return repaired
