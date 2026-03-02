"""
Slack API client for Pravaha.

Functions:
  send_message        — post a message (plain text or Block Kit blocks)
  add_reaction        — add an emoji reaction to a message
  remove_reaction     — remove an emoji reaction from a message
  send_slash_response — send a delayed response to a slash command
"""
import requests
import helpers

_SLACK_BOT_TOKEN = helpers.config("SLACK_BOT_OAUTH_TOKEN", default=None, cast=str)


def _auth_headers() -> dict:
    return {
        "Content-Type": "application/json; charset=utf-8",
        "Authorization": f"Bearer {_SLACK_BOT_TOKEN}",
        "Accept": "application/json",
    }


def send_message(
    message: str = None,
    channel_id: str = None,
    user_id: str = None,
    thread_ts: str = None,
    blocks: list = None,
    unfurl_links: bool = False,
) -> requests.Response:
    """
    Post a message to a Slack channel.

    If `blocks` is provided, it is sent as a Block Kit payload and
    `message` is used only as the notification fallback text.
    If no `blocks`, the message is sent as plain mrkdwn text (with
    optional <@user_id> mention prepended).
    """
    data: dict = {
        "channel": channel_id,
        "unfurl_links": unfurl_links,
        "unfurl_media": False,
    }

    if blocks:
        data["blocks"] = blocks
        data["text"] = message or ""
    else:
        text = message or ""
        if user_id:
            text = f"<@{user_id}> {text}"
        data["text"] = text.strip()

    if thread_ts:
        data["thread_ts"] = thread_ts

    return requests.post(
        "https://slack.com/api/chat.postMessage",
        json=data,
        headers=_auth_headers(),
        timeout=10,
    )


def add_reaction(channel_id: str, timestamp: str, emoji: str) -> requests.Response:
    """Add an emoji reaction to a Slack message."""
    return requests.post(
        "https://slack.com/api/reactions.add",
        json={"channel": channel_id, "timestamp": timestamp, "name": emoji},
        headers=_auth_headers(),
        timeout=10,
    )


def remove_reaction(channel_id: str, timestamp: str, emoji: str) -> requests.Response:
    """Remove an emoji reaction from a Slack message."""
    return requests.post(
        "https://slack.com/api/reactions.remove",
        json={"channel": channel_id, "timestamp": timestamp, "name": emoji},
        headers=_auth_headers(),
        timeout=10,
    )


def send_slash_response(
    response_url: str, message: str, blocks: list = None
) -> requests.Response:
    """
    Send a delayed response to a Slack slash command via the response_url.
    Must be called within 30 minutes of the original command.
    """
    data: dict = {"response_type": "in_channel", "text": message}
    if blocks:
        data["blocks"] = blocks
    return requests.post(
        response_url,
        json=data,
        headers={"Content-Type": "application/json"},
        timeout=10,
    )
