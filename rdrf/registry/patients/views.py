from django.http import HttpResponse


def update_session(request):
    key = request.POST["key"]
    value = request.POST["value"]
    request.session[key] = value
    return HttpResponse('ok')
