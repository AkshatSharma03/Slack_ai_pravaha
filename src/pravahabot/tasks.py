from celery import shared_task
import slacky
from . import utils
from . import ai, utils
@shared_task
def slack_message_task(message, channel_id=None, user_id=None, thread_ts=None):
    # Get the response from OpenAI
    # openai_msg = utils.chat_with_openai(message, raw=False)
    # print(f"Original message: {message}, OpenAI response: {openai_msg}")
    pdf_ai_msg = ai.query(message, raw=False)
    # Send the OpenAI response to Slack
    r = slacky.send_message(pdf_ai_msg, channel_id=channel_id, user_id=user_id, thread_ts=thread_ts)
    return r.status_code

# import slacky
# from celery import shared_task

# from . import ai, utils


# @shared_task
# def slack_message_task(message, channel_id=None, user_id=None, thread_ts=None):
#     openai_msg = utils.chat_with_openai(message, raw=False)
#     print(message, openai_msg)
#     # pdf_ai_msg = ai.query(message, raw=False)
#     r = slacky.send_message(message, channel_id=channel_id, user_id=user_id, thread_ts=thread_ts)
#     return r.status_code