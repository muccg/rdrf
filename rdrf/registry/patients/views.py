from django.http import HttpResponseRedirect
from django.views.generic import View
from django.http import HttpResponse, HttpResponseNotAllowed
from django.views.decorators.csrf import ensure_csrf_cookie


from models import Patient
#from registry.groups.models import User

import json

from django.contrib.auth import get_user_model

def update_session(request):
    #if not request.is_ajax() or not request.method=='POST':
    #    return HttpResponseNotAllowed(['POST'])

    key = request.POST["key"]
    value = request.POST["value"]

    request.session[key] = value
    return HttpResponse('ok')
