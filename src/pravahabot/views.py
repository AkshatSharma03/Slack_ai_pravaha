import json
import requests
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from pprint import pprint
import helpers


SLACK_BOT_OAUTH_TOKEN =helpers.config('SLACK_BOT_OAUTH_TOKEN', default =None,cast=str)
# Create your views here.
def send_message(message, channel_id = None):
    url = "https://slack.com/api/chat.postMessage"
    headers ={
        "Content-Type": "application/json; charset-utf-8",
        "Authorization": f"Bearer {SLACK_BOT_OAUTH_TOKEN} ",
        "Accept": "application/json"
    }
    data ={
        "channel": channel_id,
        "text": message
    }
    return requests.post(url, json=data, headers=headers)
    
# {
#   "channel": "YOUR_CHANNEL_ID",
#   "text": "Hello world :tada:"
# }

#CSRF Exempt
@require_POST
@csrf_exempt
def slack_events_endpoint(request):
    json_data ={}
    try:
        json_data = json.loads(request.body.decode('utf-8'))
    except Exception as e:
        pass
    data_type = json_data.get('type')
    print(data_type,json_data.keys(), json_data)
    allowed_data_type =[
        "url_verification",
        "event_callback"
    ]
    if data_type not in allowed_data_type:
        return HttpResponse("Not Allowed", status=400)
    if data_type == "url_verification":
        challenge = json_data.get('challenge')
    # print(json_data.get('challenge'))
    
        if challenge is None:
            return HttpResponse("Not Allowed", status=400)
        return HttpResponse(challenge, status=200)
    elif data_type =="event_callback":
        event = json_data.get('event') or {}
        pprint(event)
        blocks = event.get('blocks')
        msg_text = event.get('text')
        # user_id = event.get('user)
        channel_id = event.get('channel')
        r = send_message(msg_text, channel_id=channel_id)
        return HttpResponse("Success", status=200)
    return HttpResponse("Success", status=200)
