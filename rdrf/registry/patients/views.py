import os.path
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, FileResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.generic import View
from .models import PatientConsent

def update_session(request):
    key = request.POST["key"]
    value = request.POST["value"]
    request.session[key] = value
    return HttpResponse('ok')


class ConsentFileView(View):
    @method_decorator(login_required)
    def get(self, request, consent_id=None, filename=""):
        consent = get_object_or_404(PatientConsent, pk=consent_id)
        response = FileResponse(consent.form.file, content_type='application/octet-stream')
        response['Content-disposition'] = "filename=%s" % consent.filename
        return response
