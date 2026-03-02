"""
Slack Block Kit message builders for Pravaha.

Produces rich, formatted payloads with:
  • Proper Slack mrkdwn sections (split at 2900-char limit)
  • A divider
  • A context footer listing tools used + branding
"""

TOOL_LABELS = {
    "search_web": "🔍 Web Search",
    "execute_python": "🐍 Code",
    "query_knowledge_base": "📚 Knowledge Base",
    "get_current_datetime": "🕐 Date/Time",
    "get_weather": "🌤 Weather",
    "get_slack_channel_history": "💬 Channel History",
    "fetch_url_content": "🌐 URL Fetch",
}

_SECTION_LIMIT = 2900  # Slack's per-section text cap


def _split_text(text: str) -> list:
    """Split text into Slack-section-safe chunks (≤ 2900 chars)."""
    if len(text) <= _SECTION_LIMIT:
        return [text]

    chunks = []
    while text:
        if len(text) <= _SECTION_LIMIT:
            chunks.append(text)
            break
        # Prefer splitting on a newline boundary
        split_at = text.rfind("\n", 0, _SECTION_LIMIT)
        if split_at <= 0:
            split_at = text.rfind(" ", 0, _SECTION_LIMIT)
        if split_at <= 0:
            split_at = _SECTION_LIMIT
        chunks.append(text[:split_at].rstrip())
        text = text[split_at:].lstrip()
    return chunks


def build_agent_response(
    response_text: str,
    user_id: str = None,
    tools_used: list = None,
) -> dict:
    """
    Build a Block Kit payload for an agent response.

    Returns a dict with 'text' (notification fallback) and 'blocks'.
    """
    blocks = []

    # Prepend @mention
    if user_id:
        response_text = f"<@{user_id}>\n{response_text}"

    # One section block per chunk
    for chunk in _split_text(response_text):
        blocks.append(
            {"type": "section", "text": {"type": "mrkdwn", "text": chunk}}
        )

    blocks.append({"type": "divider"})

    # Footer: tools used + branding
    footer_parts = []
    if tools_used:
        unique = list(dict.fromkeys(tools_used))  # dedupe, preserve order
        labels = [TOOL_LABELS.get(t, t) for t in unique]
        footer_parts.append("🔧 " + "  ·  ".join(labels))
    footer_parts.append("*Pravaha* AI Agent")

    blocks.append(
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": "  |  ".join(footer_parts)}
            ],
        }
    )

    fallback = (
        response_text[:200] + "…" if len(response_text) > 200 else response_text
    )
    return {"text": fallback, "blocks": blocks}


def build_error_message(user_id: str = None, error: str = None) -> dict:
    """Build a compact error block."""
    mention = f"<@{user_id}> " if user_id else ""
    text = f"{mention}❌ Something went wrong: `{error or 'Unknown error'}`"
    return {
        "text": text,
        "blocks": [
            {"type": "section", "text": {"type": "mrkdwn", "text": text}}
        ],
    }
