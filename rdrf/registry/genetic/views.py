from django.core.context_processors import csrf
from django.shortcuts import render_to_response
from django.conf import settings
from django.core.urlresolvers import reverse

def entry(request):
    context = {}
    context.update(csrf(request))
    context["validate_sequence_url"] = reverse('admin:validate_sequence')
    context["CSRF_COOKIE_NAME"] = settings.CSRF_COOKIE_NAME
    return render_to_response("genetic/variation/index.html", context)
