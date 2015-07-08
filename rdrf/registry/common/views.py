from django.http import HttpResponseServerError
from django.http import HttpResponseNotFound
from django.http import HttpResponseRedirect
from django.core.context_processors import csrf
from django.contrib.auth.decorators import login_required

from django.shortcuts import render_to_response
import os


def _getHTMLFormattedReuest(request, message="Disease Registry Default Page not found"):
    """
    Formats the request for display on debug pages.
    """
    return "<h1>{0}</h1> <pre>{1}</pre>".format(message, str(request))


def debug_handler404(request):
    """
    Returns simple 404 response with rendered request
    """
    return HttpResponseNotFound(_getHTMLFormattedReuest(request))


def debug_handler500(request):
    """
    Returns simple 500 response with rendered request
    """
    return HttpResponseServerError(_getHTMLFormattedReuest(request, "Disease Registry Default Server Error"))


def handler404(request):
    return render_to_response("404.html")


def handler500(request):
    return render_to_response("500.html")

# These views are for test and validation purposes.
# with debug = False, static data is not being served by django so the following views
# are provided to render nice test error pages which are not available in debug mode.


def test404(request):
    context = {}
    context.update(csrf(request))
    return render_to_response("404.html", context)


def test500(request):
    context = {}
    context.update(csrf(request))
    return render_to_response("500.html", context)


@login_required
def patient_report(request):
    from django.http import HttpResponse
    from django.conf import settings
    from datetime import datetime
    import csv
    from registry.common.reports import PatientReport

    if not request.user.is_superuser:
        return HttpResponseRedirect('/')

    response = HttpResponse(mimetype="text/csv")
    writer = csv.writer(response)

    report = PatientReport()
    report.write_with(writer)

    app_name = settings.INSTALL_NAME
    report_name = report.NAME
    run_date = datetime.now().strftime('%b-%d-%I%M%p-%G')

    response[
        'Content-Disposition'] = 'attachment; filename=%s_%s_%s.csv' % (app_name, report_name, run_date)

    return response
