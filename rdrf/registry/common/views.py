from django.http import HttpResponseServerError
from django.http import HttpResponseNotFound
from django.http import HttpResponseRedirect
from django.template.context_processors import csrf
from django.contrib.auth.decorators import login_required

@login_required
def patient_report(request):
    from django.http import HttpResponse
    from django.conf import settings
    from datetime import datetime
    import csv
    from registry.common.reports import PatientReport

    if not request.user.is_superuser:
        return HttpResponseRedirect('/')

    response = HttpResponse(content_type="text/csv")
    writer = csv.writer(response)

    report = PatientReport()
    report.write_with(writer)

    app_name = settings.INSTALL_NAME
    report_name = report.NAME
    run_date = datetime.now().strftime('%b-%d-%I%M%p-%G')

    response[
        'Content-Disposition'] = 'attachment; filename=%s_%s_%s.csv' % (app_name, report_name, run_date)

    return response
