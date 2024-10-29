import json 
import requests
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from pprint import pprint
import slacky

from .tasks import slack_message_task

@csrf_exempt
@require_POST
def slack_events_endpoint(request):
    json_data = {}
    try:
        json_data = json.loads(request.body.decode('utf-8'))
    except Exception as e:
        pass
    data_type = json_data.get('type')
    print(data_type, json_data.keys(), json_data)
    allowed_data_type = [
        "url_verification",
        "event_callback"
    ]
    if data_type not in allowed_data_type:
        return HttpResponse("Not Allowed", status=400)
    if data_type == "url_verification":
        challenge = json_data.get('challenge')
        if challenge is None:
            return HttpResponse("Not Allowed", status=400)
        return HttpResponse(challenge, status=200)
    elif data_type == "event_callback":
        event = json_data.get('event') or {}
        try:
            msg_text = event['blocks'][0]['elements'][0]['elements'][1]['text']
        except:
            msg_text = event.get('text')
        user_id = event.get('user')
        channel_id = event.get('channel')
        msg_ts = event.get('ts')
        thread_ts = event.get('thread_ts')  or msg_ts
        # r = slacky.send_message(msg_text, channel_id=channel_id, user_id=user_id, thread_ts=thread_ts)
        # slack_message_task.delay("Working...", channel_id=channel_id, user_id=user_id, thread_ts=thread_ts)
        slack_message_task.apply_async(kwargs={
                "message": f"{msg_text}", 
                "channel_id": channel_id,
                "user_id": user_id}, countdown=0)
        return HttpResponse("Success", status=200)
    return HttpResponse("Success", status=200)
# import json
# import requests
# from django.http import HttpResponse
# from django.views.decorators.csrf import csrf_exempt
# from django.views.decorators.http import require_POST

# from pprint import pprint

# import slacky
# from .tasks import slack_message_task

# # SLACK_BOT_OAUTH_TOKEN =helpers.config('SLACK_BOT_OAUTH_TOKEN', default =None,cast=str)
# # # Create your views here.
# # def send_message(message, channel_id = None, user_id =None):
# #     url = "https://slack.com/api/chat.postMessage"
# #     headers ={
# #         "Content-Type": "application/json; charset-utf-8",
# #         "Authorization": f"Bearer {SLACK_BOT_OAUTH_TOKEN} ",
# #         "Accept": "application/json"
# #     }
# #     if user_id is not None:
# #         message = f"<@{user_id}> {message}"
# #     data ={
# #         "channel": channel_id,
# #         "text": f"{message}".strip()
# #     }
# #     return requests.post(url, json=data, headers=headers)
    
# # {
# #   "channel": "YOUR_CHANNEL_ID",
# #   "text": "Hello world :tada:"
# # }

# #CSRF Exempt
# @require_POST
# @csrf_exempt
# def slack_events_endpoint(request):
#     json_data ={}
#     try:
#         json_data = json.loads(request.body.decode('utf-8'))
#     except Exception as e:
#         pass
#     data_type = json_data.get('type')
#     print(data_type,json_data.keys(), json_data)
#     allowed_data_type =[
#         "url_verification",
#         "event_callback"
#     ]
#     if data_type not in allowed_data_type:
#         return HttpResponse("Not Allowed", status=400)
#     if data_type == "url_verification":
#         challenge = json_data.get('challenge')
#     # print(json_data.get('challenge'))
    
#         if challenge is None:
#             return HttpResponse("Not Allowed", status=400)
#         return HttpResponse(challenge, status=200)
#     elif data_type == "event_callback":
#             event = json_data.get('event') or {}
#             pprint(event)
#     try:
#         # Extract the text from the message
#         msg_text = event['blocks'][0]['elements'][0]['elements'][1]['text']
#     except (IndexError, KeyError, TypeError):
#         # Fallback if the structured path doesn't work
#         msg_text = event.get('text', '').strip()
    

#     # Extract the channel ID
#     user_id = event.get('user')
#     channel_id = event.get('channel')
#     msg_ts = event.get('ts')
#     thread_ts = event.get('thread_ts') or msg_ts
#     # Send the response message back to the same channel
#     # if channel_id and msg_text:
#     #     r = slacky.send_message(msg_text, channel_id=channel_id, user_id=user_id, thread_ts=thread_ts)
    
#     # return HttpResponse("Success", status=200)
#     slack_message_task.delay(msg_text, channel_id=channel_id, user_id=user_id, thread_ts=thread_ts)
#     # elif data_type =="event_callback":
#     #     event = json_data.get('event') or {}
#     #     pprint(event)
#     #     try:

#     #         msg_text = event['blocks'][0]['elements'][0]['elements'][1]
#     #         ['text']
 

#     #     except (IndexError, KeyError, TypeError):
#     #     # Fallback if the structured path doesn't work
#     #      msg_text = event.get('text', '').strip()

#     #     # user_id = event.get('user)
#     #     channel_id = event.get('channel')
#     #     r = send_message(msg_text, channel_id=channel_id)
#     #     return HttpResponse("Success", status=200)
#     # return HttpResponse("Success", status=200)