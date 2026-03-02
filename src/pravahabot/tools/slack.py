"""Slack-native tools — channel history, etc."""
import requests
import helpers


def get_slack_channel_history(channel_id: str, limit: int = 10) -> str:
    """Fetch the most recent messages from a Slack channel."""
    try:
        token = helpers.config("SLACK_BOT_OAUTH_TOKEN", default=None)
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        response = requests.get(
            "https://slack.com/api/conversations.history",
            headers=headers,
            params={"channel": channel_id, "limit": min(limit, 20)},
            timeout=10,
        )
        data = response.json()

        if not data.get("ok"):
            return f"Failed to read channel history: {data.get('error', 'unknown error')}"

        messages = data.get("messages", [])
        if not messages:
            return "No recent messages found in this channel."

        lines = []
        for msg in reversed(messages):
            # Skip bot messages in history display
            if msg.get("bot_id") or msg.get("subtype") == "bot_message":
                continue
            user = msg.get("user", "unknown")
            text = msg.get("text", "").strip()
            if text:
                lines.append(f"<@{user}>: {text}")

        if not lines:
            return "No human messages found in recent channel history."
        return "Recent channel history:\n\n" + "\n".join(lines)

    except Exception as e:
        return f"Failed to fetch channel history: {str(e)}"
