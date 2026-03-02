"""
Pravaha AI Agent — agentic loop powered by Claude claude-sonnet-4-6 with tool use.

Flow:
  1. Load conversation history from DB
  2. Send message + history to Claude with tool definitions
  3. If Claude calls tools → execute them → loop back
  4. On end_turn → persist exchange → return final text + tools used
"""
import re
import logging

import helpers

from . import tools as agent_tools
from .models import ConversationMessage

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Lazy Anthropic client (avoids import-time API key errors)
# ─────────────────────────────────────────────
_client = None


def _get_client():
    global _client
    if _client is None:
        import anthropic
        _client = anthropic.Anthropic(
            api_key=helpers.config("ANTHROPIC_API_KEY", default=None)
        )
    return _client


# ─────────────────────────────────────────────
# System prompt
# ─────────────────────────────────────────────
SYSTEM_PROMPT = """\
You are *Pravaha*, a sophisticated AI assistant embedded in Slack.
You are highly capable, creative, and deeply helpful.

You have access to powerful tools:
• *Web Search* — find current information, news, docs, anything recent
• *Python Execution* — run code to solve problems, do calculations, verify snippets
• *Knowledge Base* — search internal company documents via semantic RAG
• *Slack History* — read recent channel messages to understand context
• *Weather* — real-time conditions for any city in the world
• *Date/Time* — precise date and time in any timezone
• *URL Reader* — fetch and read any web page or article

Core principles:
- Give real, direct answers — not vague suggestions
- Proactively use tools when they improve accuracy
- For code questions, *run the code* to verify it works before sharing
- For recent facts or news, *search the web* rather than guessing
- Format responses clearly using Slack mrkdwn (*bold*, _italic_, `code`, ```blocks```)
- Be honest about uncertainty; offer to investigate further
- Keep a conversational, professional tone
"""

# ─────────────────────────────────────────────
# Tool schemas for the Anthropic API
# ─────────────────────────────────────────────
TOOLS = [
    {
        "name": "search_web",
        "description": (
            "Search the web for current information, news, documentation, or facts. "
            "Use this whenever up-to-date information is needed beyond training data."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Specific search query. More specific = better results.",
                }
            },
            "required": ["query"],
        },
    },
    {
        "name": "execute_python",
        "description": (
            "Execute Python code and return stdout/stderr. Use for calculations, "
            "data processing, algorithm demos, or verifying code works correctly."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code to run. May use stdlib and installed packages.",
                }
            },
            "required": ["code"],
        },
    },
    {
        "name": "query_knowledge_base",
        "description": (
            "Search the internal knowledge base for org-specific docs, "
            "previously indexed content, or internal documentation."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The question or topic to look up in the knowledge base.",
                }
            },
            "required": ["question"],
        },
    },
    {
        "name": "get_current_datetime",
        "description": "Get the current date and time, optionally in a specific timezone.",
        "input_schema": {
            "type": "object",
            "properties": {
                "timezone": {
                    "type": "string",
                    "description": (
                        "Timezone name, e.g. 'US/Eastern', 'Europe/London', "
                        "'Asia/Kolkata'. Defaults to UTC."
                    ),
                    "default": "UTC",
                }
            },
        },
    },
    {
        "name": "get_weather",
        "description": "Get real-time weather conditions for any location worldwide.",
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City name or region, e.g. 'Mumbai', 'New York', 'Tokyo'.",
                }
            },
            "required": ["location"],
        },
    },
    {
        "name": "get_slack_channel_history",
        "description": (
            "Retrieve recent messages from the current Slack channel. "
            "Use to understand ongoing discussions or find earlier context."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "channel_id": {
                    "type": "string",
                    "description": "The Slack channel ID.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of messages to retrieve (1-20). Default: 10.",
                    "default": 10,
                },
            },
            "required": ["channel_id"],
        },
    },
    {
        "name": "fetch_url_content",
        "description": (
            "Fetch and extract readable text from any URL. "
            "Use to read articles, GitHub repos, documentation pages, etc."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Full URL including https://",
                }
            },
            "required": ["url"],
        },
    },
]


# ─────────────────────────────────────────────
# Tool dispatcher
# ─────────────────────────────────────────────
def _execute_tool(tool_name: str, tool_input: dict, channel_id: str = None) -> str:
    """Route a tool call to the appropriate implementation."""
    try:
        if tool_name == "search_web":
            return agent_tools.search_web(tool_input["query"])

        if tool_name == "execute_python":
            return agent_tools.execute_python(tool_input["code"])

        if tool_name == "query_knowledge_base":
            return agent_tools.query_knowledge_base(tool_input["question"])

        if tool_name == "get_current_datetime":
            return agent_tools.get_current_datetime(tool_input.get("timezone", "UTC"))

        if tool_name == "get_weather":
            return agent_tools.get_weather(tool_input["location"])

        if tool_name == "get_slack_channel_history":
            cid = tool_input.get("channel_id") or channel_id
            limit = min(int(tool_input.get("limit", 10)), 20)
            return agent_tools.get_slack_channel_history(cid, limit)

        if tool_name == "fetch_url_content":
            return agent_tools.fetch_url_content(tool_input["url"])

        return f"Unknown tool: {tool_name}"

    except Exception as e:
        logger.warning(f"Tool '{tool_name}' raised: {e}", exc_info=True)
        return f"Tool '{tool_name}' error: {str(e)}"


# ─────────────────────────────────────────────
# Conversation memory helpers
# ─────────────────────────────────────────────
def _load_history(conversation_id: str, channel_id: str) -> list:
    """Return the last 20 messages for this conversation as Claude-compatible dicts."""
    qs = ConversationMessage.objects.filter(
        thread_ts=conversation_id,
        channel_id=channel_id,
    ).order_by("-created_at")[:20]

    return [
        {"role": msg.role, "content": msg.content}
        for msg in reversed(list(qs))
    ]


def _save_exchange(
    conversation_id: str,
    channel_id: str,
    user_id: str,
    user_message: str,
    assistant_response: str,
) -> None:
    """Persist the user message and agent reply to the DB."""
    ConversationMessage.objects.create(
        thread_ts=conversation_id,
        channel_id=channel_id,
        user_id=user_id,
        role="user",
        content=user_message,
    )
    ConversationMessage.objects.create(
        thread_ts=conversation_id,
        channel_id=channel_id,
        user_id=None,
        role="assistant",
        content=assistant_response,
    )


# ─────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────
def strip_bot_mention(text: str) -> str:
    """Remove Slack-style bot mention tokens like <@U123BOT> from text."""
    return re.sub(r"<@[A-Z0-9]+>", "", text).strip()


def run_agent(
    message: str,
    conversation_id: str,
    channel_id: str,
    user_id: str = None,
) -> tuple:
    """
    Run the agentic loop for one user turn.

    Returns:
        (response_text: str, tools_used: list[str])
    """
    client = _get_client()
    clean_message = strip_bot_mention(message)

    history = _load_history(conversation_id, channel_id)
    messages = history + [{"role": "user", "content": clean_message}]

    tools_used: list[str] = []
    MAX_ITERATIONS = 10

    for _ in range(MAX_ITERATIONS):
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        tool_uses = [b for b in response.content if b.type == "tool_use"]

        # No more tool calls → final answer
        if response.stop_reason == "end_turn" or not tool_uses:
            text_parts = [b.text for b in response.content if b.type == "text"]
            final_text = "\n".join(text_parts).strip() or "Done."
            _save_exchange(
                conversation_id, channel_id, user_id, clean_message, final_text
            )
            return final_text, tools_used

        # Execute all requested tools
        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for tool_use in tool_uses:
            tools_used.append(tool_use.name)
            result = _execute_tool(tool_use.name, tool_use.input, channel_id=channel_id)
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": str(result),
                }
            )

        messages.append({"role": "user", "content": tool_results})

    # Safety net: ask Claude to summarise with what it has
    logger.warning("Agent hit max iterations; requesting forced final answer.")
    final_resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=messages
        + [
            {
                "role": "user",
                "content": (
                    "Please provide your final answer based on everything gathered so far."
                ),
            }
        ],
    )
    text_parts = [b.text for b in final_resp.content if b.type == "text"]
    final_text = "\n".join(text_parts).strip() or "Task completed."
    _save_exchange(conversation_id, channel_id, user_id, clean_message, final_text)
    return final_text, tools_used
