from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, FileResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.generic import View
from django.http import Http404
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
        if consent.form and consent.form.file:
            response = FileResponse(consent.form.file, content_type='application/octet-stream')
            response['Content-disposition'] = "filename=%s" % consent.filename
            return response
        raise Http404("The file %s (consent %s) was not found" % (consent.filename, consent_id))
