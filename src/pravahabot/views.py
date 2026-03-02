"""
Pravaha — Slack event and slash-command endpoints.

Handles:
  • URL verification (Slack handshake)
  • app_mention events  (someone @-mentions the bot in a channel)
  • Direct messages     (channel ID starts with 'D')
  • /pravaha slash command
"""
import json
import logging

from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .tasks import process_slack_message, process_slash_command

logger = logging.getLogger(__name__)

_ALLOWED_TYPES = {"url_verification", "event_callback"}


def _is_bot_event(event: dict) -> bool:
    """Return True for bot-originated events (prevents reply loops)."""
    return bool(
        event.get("bot_id")
        or event.get("subtype") in {"bot_message", "message_changed", "message_deleted"}
    )


@csrf_exempt
@require_POST
def slack_events_endpoint(request):
    """Main Slack Events API receiver."""
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return HttpResponse("Bad Request", status=400)

    data_type = payload.get("type")
    if data_type not in _ALLOWED_TYPES:
        return HttpResponse("Not Allowed", status=400)

    # ── URL verification handshake ─────────────────────────────────────────
    if data_type == "url_verification":
        challenge = payload.get("challenge")
        if not challenge:
            return HttpResponse("Missing challenge", status=400)
        return HttpResponse(challenge, content_type="text/plain")

    # ── Event callbacks ────────────────────────────────────────────────────
    event = payload.get("event", {})
    if _is_bot_event(event):
        return HttpResponse("OK", status=200)

    event_type = event.get("type")
    channel_id = event.get("channel", "")

    is_mention = event_type == "app_mention"
    is_dm = event_type == "message" and channel_id.startswith("D")

    if not (is_mention or is_dm):
        return HttpResponse("OK", status=200)

    msg_text = event.get("text", "").strip()
    if not msg_text:
        return HttpResponse("OK", status=200)

    user_id = event.get("user")
    msg_ts = event.get("ts")
    thread_ts = event.get("thread_ts")

    # Conversation memory scope:
    #   DMs  → persistent per-DM channel (whole DM is one conversation)
    #   Threads → scoped to the thread
    #   Top-level channel messages → each message starts its own thread
    if channel_id.startswith("D"):
        conversation_id = channel_id
    else:
        conversation_id = thread_ts or msg_ts

    process_slack_message.apply_async(
        kwargs={
            "message": msg_text,
            "channel_id": channel_id,
            "user_id": user_id,
            "msg_ts": msg_ts,
            "thread_ts": thread_ts,
            "conversation_id": conversation_id,
        },
        countdown=0,
    )
    return HttpResponse("OK", status=200)


@csrf_exempt
@require_POST
def slack_slash_endpoint(request):
    """
    Handle /pravaha <query> slash commands.

    Slack requires a response within 3 s; we reply immediately with
    an acknowledgement and do the real work in a Celery task.
    """
    command = request.POST.get("command", "/pravaha")
    text = request.POST.get("text", "").strip()
    user_id = request.POST.get("user_id")
    channel_id = request.POST.get("channel_id")
    response_url = request.POST.get("response_url")

    if not text:
        return JsonResponse(
            {
                "response_type": "ephemeral",
                "text": (
                    f"Usage: `{command} <your question>`\n"
                    f"Example: `{command} What is the capital of France?`"
                ),
            }
        )

    # Each slash command session is keyed to the user for continuity
    conversation_id = f"slash_{user_id}"

    process_slash_command.apply_async(
        kwargs={
            "message": text,
            "channel_id": channel_id,
            "user_id": user_id,
            "response_url": response_url,
            "conversation_id": conversation_id,
        },
        countdown=0,
    )

    return JsonResponse(
        {"response_type": "in_channel", "text": "⏳ _Pravaha is thinking…_"}
    )
