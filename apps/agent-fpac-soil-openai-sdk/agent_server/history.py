"""Conversation-history normalization helpers.

Kept dependency-free (no Databricks SDK / MLflow imports) so it can be unit
tested in isolation. This file is copied verbatim across the OpenAI Agents SDK
templates (agent-openai-agents-sdk, agent-openai-agents-sdk-multiagent,
agent-openai-advanced) — keep the copies in sync.
"""

from typing import Any


def sanitize_custom_inputs(custom_inputs: Any) -> dict[str, str]:
    """Keep only opaque session metadata out of model-visible request data.

    AOI geometry is intentionally not accepted here. The handler may use the
    returned opaque identifier for correlation, but pre-trace redaction still
    requires a platform-level boundary before the decorated handler runs.
    """
    if not isinstance(custom_inputs, dict):
        return {}
    session_id = custom_inputs.get("session_id")
    if isinstance(session_id, str) and session_id:
        return {"session_id": session_id}
    return {}


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
