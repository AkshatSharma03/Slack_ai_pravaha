import json
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
# Create your views here.
#CSRF Exempt
@csrf_exempt
def slack_events_endpoint(request):
    json_data ={}
    try:
        json_data = json.loads(request.body.decode('utf-8'))
    except:
        pass
    data_type = json_data.get('type')
    if data_type != "url_verification":
        return HttpResponse("Not Allowed", status=400)
    # print(json_data.get('challenge'))
    challenge = json_data.get('challenge')
    if challenge is None:
        return HttpResponse("Not Allowed", status=400)
    
    # print(request.body, request.method)
    return HttpResponse(challenge, status=200)