"""Shared Foundry SDK helpers for multi-channel agent access.

Used by both the web chat app and the Teams bot to call the Foundry agent.
Each channel acquires the user's Azure AD token independently, then uses
these helpers to interact with the Foundry Responses API.

Sub-agent pattern
-----------------
Use ``call_sub_agent`` to delegate a discrete task to an agent running in a
fresh, isolated thread.  Only the distilled text answer returns to the caller;
all intermediate tool calls stay in the sub-agent's own context and never
pollute the parent thread.

Context compaction
------------------
Pass ``max_prompt_tokens`` to ``call_agent`` to tell the Foundry runtime to
truncate the prompt when it would exceed that budget.  This keeps long
conversations from consuming unbounded tokens without requiring any change to
the agent definition.
"""

import asyncio
import logging
import os
import uuid

from azure.core.credentials import AccessToken

logger = logging.getLogger(__name__)

# Maximum sub-agent nesting depth.  Calls that would exceed this are short-
# circuited and return an explanatory string instead.  This prevents a prompt
# agent from accidentally delegating to itself in a loop.
MAX_SUB_AGENT_DEPTH = int(os.environ.get("MAX_SUB_AGENT_DEPTH", "1"))


class UserTokenCredential:
    """TokenCredential that wraps a user-provided access token.

    The Foundry SDK's AIProjectClient needs a TokenCredential. This class
    wraps the user's Azure AD access token so the agent calls carry the
    user's identity -- enabling end-to-end identity propagation.
    """

    def __init__(self, token: str):
        self._token = token

    def get_token(self, *scopes, **kwargs):
        return AccessToken(self._token, 0)


def create_foundry_client(access_token: str, project_endpoint: str = None):
    """Create an AIProjectClient authenticated with the user's token.

    Args:
        access_token: User's Azure AD bearer token
        project_endpoint: Override for AI_FOUNDRY_PROJECT_ENDPOINT env var
    """
    from azure.ai.projects import AIProjectClient

    endpoint = project_endpoint or os.environ.get("AI_FOUNDRY_PROJECT_ENDPOINT", "")
    if not endpoint:
        raise ValueError("AI_FOUNDRY_PROJECT_ENDPOINT not configured")

    credential = UserTokenCredential(access_token)
    return AIProjectClient(endpoint=endpoint, credential=credential)


def parse_output_items(output_items, request_id: str = ""):
    """Parse Responses API output items into a structured result.

    Returns:
        dict with keys: type, text, approval_required, approval_ids
    """
    result = {
        "type": "text",
        "text": "",
        "approval_required": False,
        "approval_ids": [],
        "tool_calls": [],
    }

    for item in output_items:
        item_type = getattr(item, "type", "unknown")

        if item_type == "mcp_approval_request":
            result["type"] = "approval_required"
            result["approval_required"] = True
            tool_name = getattr(item, "name", "")
            tool_args = getattr(item, "arguments", {})
            result["approval_ids"].append({
                "id": getattr(item, "id", ""),
                "name": tool_name,
                "server_label": getattr(item, "server_label", ""),
                "arguments": tool_args,
            })
            logger.info(
                "tool_approval_requested request_id=%s tool=%s server=%s args=%s",
                request_id, tool_name,
                getattr(item, "server_label", ""),
                str(tool_args)[:300],
            )

        elif item_type == "mcp_call":
            tool_name = getattr(item, "name", "")
            tool_args = getattr(item, "arguments", {})
            tool_error = getattr(item, "error", None)
            logger.info(
                "tool_call request_id=%s tool=%s args=%s error=%s",
                request_id, tool_name,
                str(tool_args)[:300],
                str(tool_error)[:200] if tool_error else None,
            )
            result["tool_calls"].append({
                "name": tool_name,
                "arguments": tool_args,
                "error": str(tool_error) if tool_error else None,
                "output": getattr(item, "output", None),
            })

        elif item_type == "memory_search_call":
            # Memory data lives in model_extra (Pydantic extra fields)
            extra = getattr(item, "model_extra", {}) or {}
            memories = extra.get("memories", []) or []
            status = getattr(item, "status", "")
            mem_id = getattr(item, "id", "")

            # Format memory results for display
            mem_entries = []
            for mem in memories:
                if isinstance(mem, dict):
                    mem_entries.append(mem)
                elif hasattr(mem, "model_dump"):
                    mem_entries.append(mem.model_dump())
                else:
                    mem_entries.append({"text": str(mem)[:300]})

            mem_count = len(mem_entries)
            mem_output = ""
            if mem_entries:
                lines = []
                for m in mem_entries[:10]:
                    text = m.get("text", m.get("content", m.get("summary", "")))
                    mtype = m.get("type", "")
                    if text:
                        lines.append(f"[{mtype}] {str(text)[:200]}" if mtype else str(text)[:200])
                    else:
                        lines.append(str(m)[:200])
                mem_output = "\n".join(lines)

            logger.info(
                "memory_call request_id=%s id=%s status=%s results=%d",
                request_id, mem_id, status, mem_count,
            )
            result["tool_calls"].append({
                "name": "memory_search",
                "arguments": {"status": status, "id": mem_id},
                "error": None,
                "output": mem_output or f"{mem_count} memory results",
            })

        elif item_type == "message":
            content = getattr(item, "content", [])
            for c in content:
                if hasattr(c, "text"):
                    result["text"] += c.text

    return result


async def call_agent(access_token: str, message: str, previous_response_id: str = None,
                     agent_name: str = None, project_endpoint: str = None,
                     timeout: float = 120, max_prompt_tokens: int = None) -> dict:
    """Send a message to the Foundry agent and return the parsed response.

    Args:
        access_token: User's Azure AD bearer token
        message: User message text
        previous_response_id: For multi-turn conversations
        agent_name: Agent name (default: from AGENT_NAME env var)
        project_endpoint: Override for AI_FOUNDRY_PROJECT_ENDPOINT env var
        timeout: Request timeout in seconds
        max_prompt_tokens: If set, asks the Foundry runtime to truncate the
            prompt to stay within this token budget.  Useful for long-running
            conversations where the accumulated tool-call history would
            otherwise exhaust the model's context window.  The runtime drops
            the oldest messages first (sliding-window behaviour).

    Returns:
        dict with keys: response_id, request_id, type, text,
                        approval_required, approval_ids
    """
    request_id = str(uuid.uuid4())
    agent_name = agent_name or os.environ.get("AGENT_NAME", "salesforce-assistant")

    logger.info("agent_call request_id=%s agent=%s max_prompt_tokens=%s",
                request_id, agent_name, max_prompt_tokens)

    project_client = create_foundry_client(access_token, project_endpoint)
    openai_client = project_client.get_openai_client()

    try:
        kwargs = {
            "input": message,
            "extra_body": {"agent_reference": {"name": agent_name, "type": "agent_reference"}},
        }
        if previous_response_id:
            kwargs["previous_response_id"] = previous_response_id
        if max_prompt_tokens:
            # truncation_strategy is part of the Responses API spec; spread
            # preserves any existing extra_body keys (e.g. agent_reference).
            # If the caller already set truncation_strategy it will be
            # overridden by this value — max_prompt_tokens takes precedence.
            existing = kwargs.get("extra_body", {})
            if "truncation_strategy" in existing:
                logger.debug(
                    "agent_call overriding existing truncation_strategy with max_prompt_tokens=%d",
                    max_prompt_tokens,
                )
            kwargs["extra_body"] = {
                **existing,
                "truncation_strategy": {
                    "type": "last_messages",
                    "max_prompt_tokens": max_prompt_tokens,
                },
            }

        response = await asyncio.wait_for(
            asyncio.to_thread(openai_client.responses.create, **kwargs),
            timeout=timeout,
        )

        output_items = getattr(response, "output", [])
        output_types = [getattr(item, "type", "unknown") for item in output_items]
        logger.info(
            "agent_output request_id=%s types=%s count=%d",
            request_id, output_types, len(output_items),
        )

        parsed = parse_output_items(output_items, request_id)

        if not parsed["text"]:
            parsed["text"] = getattr(response, "output_text", "") or ""

        # Extract token usage if available
        usage = getattr(response, "usage", None)
        usage_dict = None
        if usage:
            usage_dict = {
                "input_tokens": getattr(usage, "input_tokens", 0),
                "output_tokens": getattr(usage, "output_tokens", 0),
                "total_tokens": getattr(usage, "total_tokens", 0),
            }
            logger.info(
                "agent_usage request_id=%s input=%d output=%d total=%d",
                request_id, usage_dict["input_tokens"],
                usage_dict["output_tokens"], usage_dict["total_tokens"],
            )

        logger.info(
            "agent_response request_id=%s response_id=%s type=%s text_preview=%s",
            request_id, response.id, parsed["type"], (parsed["text"] or "")[:200],
        )

        return {
            "response_id": response.id,
            "request_id": request_id,
            **parsed,
            **({"usage": usage_dict} if usage_dict else {}),
        }
    finally:
        openai_client.close()


async def approve_tools(access_token: str, previous_response_id: str,
                        approval_ids: list, approve: bool = True,
                        agent_name: str = None, project_endpoint: str = None,
                        timeout: float = 120) -> dict:
    """Approve or deny MCP tool calls and continue the conversation.

    Args:
        access_token: User's Azure AD bearer token
        previous_response_id: Response ID containing the approval request
        approval_ids: List of approval request IDs to approve/deny
        approve: True to approve, False to deny
        agent_name: Agent name (default: from AGENT_NAME env var)
        project_endpoint: Override for AI_FOUNDRY_PROJECT_ENDPOINT env var
        timeout: Request timeout in seconds

    Returns:
        dict with keys: response_id, type, text, approval_required, approval_ids, tool_calls
    """
    agent_name = agent_name or os.environ.get("AGENT_NAME", "salesforce-assistant")

    project_client = create_foundry_client(access_token, project_endpoint)
    openai_client = project_client.get_openai_client()

    try:
        try:
            from openai.types.responses.response_input_param import McpApprovalResponse
            approval_input = [
                McpApprovalResponse(
                    type="mcp_approval_response",
                    approve=approve,
                    approval_request_id=aid,
                )
                for aid in approval_ids
            ]
        except ImportError:
            approval_input = [
                {
                    "type": "mcp_approval_response",
                    "approve": approve,
                    "approval_request_id": aid,
                }
                for aid in approval_ids
            ]

        response = await asyncio.wait_for(
            asyncio.to_thread(
                openai_client.responses.create,
                previous_response_id=previous_response_id,
                input=approval_input,
                extra_body={"agent_reference": {"name": agent_name, "type": "agent_reference"}},
            ),
            timeout=timeout,
        )

        output_items = getattr(response, "output", [])
        parsed = parse_output_items(output_items, request_id="approve")

        if not parsed["text"]:
            parsed["text"] = getattr(response, "output_text", "") or ""

        usage = getattr(response, "usage", None)
        usage_dict = None
        if usage:
            usage_dict = {
                "input_tokens": getattr(usage, "input_tokens", 0),
                "output_tokens": getattr(usage, "output_tokens", 0),
                "total_tokens": getattr(usage, "total_tokens", 0),
            }

        return {
            "response_id": response.id,
            **parsed,
            **({"usage": usage_dict} if usage_dict else {}),
        }
    finally:
        openai_client.close()


async def call_sub_agent(
    access_token: str,
    task: str,
    agent_name: str = None,
    project_endpoint: str = None,
    depth: int = 0,
    max_depth: int = None,
    timeout: float = 60,
) -> str:
    """Invoke an agent in a fresh, isolated thread and return only its answer.

    Sub-agent pattern
    -----------------
    The sub-agent runs without any ``previous_response_id``, so it starts with
    a clean context.  All intermediate tool calls (schema lookups, SOQL
    queries, etc.) stay in that isolated thread and are never written back into
    the parent conversation.  Only the final text answer is returned.

    Recursion guard
    ---------------
    ``depth`` tracks the current nesting level.  When ``depth >= max_depth``
    the call is short-circuited and returns an explanatory string.  This
    prevents a prompt agent from entering an infinite delegation loop if it
    accidentally references itself as a tool.

    Args:
        access_token: User's Azure AD bearer token (propagated for identity).
        task: The self-contained task description for the sub-agent.
        agent_name: Sub-agent name.  Defaults to the value of ``AGENT_NAME``
            env var (same as the parent), which is fine for schema-discovery
            delegation.  Use a different name to delegate to a specialised agent.
        project_endpoint: Foundry project endpoint.  Defaults to env var.
        depth: Current delegation depth (0 = called directly by the app layer).
        max_depth: Maximum allowed nesting.  Defaults to ``MAX_SUB_AGENT_DEPTH``
            (env-configurable, default 1).
        timeout: Per-call timeout in seconds.

    Returns:
        The sub-agent's final text answer, or an error string if the recursion
        limit was hit or the call failed.
    """
    effective_max = max_depth if max_depth is not None else MAX_SUB_AGENT_DEPTH
    if depth >= effective_max:
        logger.warning(
            "sub_agent_depth_exceeded depth=%d max=%d task_preview=%s",
            depth, effective_max, task[:100],
        )
        return (
            f"[Sub-agent call blocked: maximum delegation depth ({effective_max}) reached. "
            "The task must be handled directly without further delegation.]"
        )

    logger.info(
        "sub_agent_call depth=%d agent=%s task_preview=%s",
        depth, agent_name or os.environ.get("AGENT_NAME", "salesforce-assistant"), task[:100],
    )

    try:
        result = await call_agent(
            access_token=access_token,
            message=task,
            agent_name=agent_name,
            project_endpoint=project_endpoint,
            timeout=timeout,
            # No previous_response_id — fresh isolated context.
            # The sub-agent starts from a clean slate and its tool-call
            # history is never merged back into the parent thread.
        )
        answer = result.get("text", "")
        logger.info(
            "sub_agent_done depth=%d answer_preview=%s",
            depth, answer[:200],
        )
        return answer or "[Sub-agent returned no text answer]"
    except Exception as exc:
        logger.error("sub_agent_error depth=%d error=%s", depth, exc)
        return f"[Sub-agent error: {exc}]"
