from django.utils.dateformat import DateFormat
from registry.common.report_utils import SimpleReport
from registry.patients.models import Patient
from django.conf import settings


class PatientReport(SimpleReport):
    NAME = "PatientReport"

    SPEC = [["Patient ID", lambda patient: patient.pk],
            ["Given Names", "given_names"],
            ["Family Name", "family_name"],
            ["DOB", "date_of_birth", lambda date_value: DateFormat(date_value).format('d-m-Y')],
            ["Registry Type", lambda patient: settings.INSTALL_NAME],
            ["Jurisdiction", "working_group.name"],
            ]

    #QUERY = "Patient.objects.all().filter(active=True)"

    def query(self):
        return Patient.objects.all().filter(active=True)
