"""
Celery tasks for Pravaha.

process_slack_message — handles app_mention and DM events
process_slash_command — handles /pravaha slash command responses
"""
import logging

import slacky
from celery import shared_task

from . import agent
from . import blocks as block_builder

logger = logging.getLogger(__name__)

_THINKING_EMOJI = "brain"  # Reaction added while the agent works


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def process_slack_message(
    self,
    message,
    channel_id,
    user_id,
    msg_ts,
    thread_ts=None,
    conversation_id=None,
):
    """
    Run the agent for an incoming Slack message and post the reply.

    UX flow:
      1. Add 🧠 reaction (visible "thinking" indicator)
      2. Run agent (may call multiple tools in a loop)
      3. Send rich Block Kit reply in the message thread
      4. Remove 🧠 reaction
    """
    if conversation_id is None:
        conversation_id = thread_ts or msg_ts

    try:
        # Show "thinking" indicator
        slacky.add_reaction(channel_id, msg_ts, _THINKING_EMOJI)

        response_text, tools_used = agent.run_agent(
            message=message,
            conversation_id=conversation_id,
            channel_id=channel_id,
            user_id=user_id,
        )

        payload = block_builder.build_agent_response(
            response_text=response_text,
            user_id=user_id,
            tools_used=tools_used,
        )

        slacky.send_message(
            message=payload["text"],
            channel_id=channel_id,
            thread_ts=thread_ts or msg_ts,
            blocks=payload["blocks"],
        )

    except Exception as exc:
        logger.error("process_slack_message failed: %s", exc, exc_info=True)
        err_payload = block_builder.build_error_message(
            user_id=user_id, error=str(exc)[:120]
        )
        try:
            slacky.send_message(
                message=err_payload["text"],
                channel_id=channel_id,
                thread_ts=thread_ts or msg_ts,
                blocks=err_payload["blocks"],
            )
        except Exception:
            pass
        raise self.retry(exc=exc)

    finally:
        # Always remove the thinking reaction
        try:
            slacky.remove_reaction(channel_id, msg_ts, _THINKING_EMOJI)
        except Exception:
            pass


@shared_task(bind=True, max_retries=2, default_retry_delay=5)
def process_slash_command(
    self,
    message,
    channel_id,
    user_id,
    response_url,
    conversation_id,
):
    """
    Run the agent for a /pravaha slash command and post via response_url.
    """
    try:
        response_text, tools_used = agent.run_agent(
            message=message,
            conversation_id=conversation_id,
            channel_id=channel_id,
            user_id=user_id,
        )

        payload = block_builder.build_agent_response(
            response_text=response_text,
            user_id=user_id,
            tools_used=tools_used,
        )

        slacky.send_slash_response(
            response_url=response_url,
            message=payload["text"],
            blocks=payload["blocks"],
        )

    except Exception as exc:
        logger.error("process_slash_command failed: %s", exc, exc_info=True)
        err_payload = block_builder.build_error_message(
            user_id=user_id, error=str(exc)[:120]
        )
        try:
            slacky.send_slash_response(
                response_url=response_url,
                message=err_payload["text"],
                blocks=err_payload["blocks"],
            )
        except Exception:
            pass
        raise self.retry(exc=exc)
