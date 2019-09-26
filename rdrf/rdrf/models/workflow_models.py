from django.db import models
from rdrf.models.definition.models import Registry
from registry.groups.models import CustomUser
from datetime import datetime
from rdrf.helpers.utils import generate_token
from django.urls import reverse
from rdrf.events.events import EventType

import logging

logger = logging.getLogger(__name__)


class ClinicianSignupRequest(models.Model):
    STATES = (("emailed", "Emailed"),      # clinician emailed
              ("signed-up", "Signed Up"),  # the clinician accepted the request and a user object was created
              ("created", "Created"),      # request created but nothing sent yet
              ("error", "Error"),          # error
              ("rejected", "Rejected"))    # the clinician received the request but rejected it

    registry = models.ForeignKey(Registry, on_delete=models.CASCADE)
    patient_id = models.IntegerField()   # the patient id whose clinician it is ( had import issues with Patient)
    clinician_email = models.CharField(max_length=80)
    state = models.CharField(max_length=80, choices=STATES, default="created")
    token = models.CharField(max_length=80, default=generate_token, unique=True)
    clinician_other = models.ForeignKey("patients.ClinicianOther",
                                        on_delete=models.CASCADE)  # this is the model the parent creates with data about the clinician`1
    clinician = models.ForeignKey(CustomUser,
                                  blank=True,
                                  null=True,
                                  on_delete=models.SET_NULL)
    emailed_date = models.DateTimeField(null=True)
    signup_date = models.DateTimeField(null=True)

    def send_request(self):
        self._send_email()
        self.state = "emailed"
        self.emailed_date = datetime.now()
        self.save()

    def notify_participant_on_verification(self, diagnosis=""):
        from registry.patients.models import Patient
        patient = Patient.objects.get(id=self.patient_id)
        participants = self._get_participants(patient)
        event_type = EventType.PARTICIPANT_CLINICIAN_NOTIFICATION
        template_data = {
            "diagnosis": diagnosis,
            "clinician_name": self.clinican_other.clinician_name,
            "participants": participants,
            "patient_name": "%s" % patient,
        }

        from rdrf.services.io.notifications.email_notification import process_notification
        process_notification(self.registry.code,
                             event_type,
                             template_data)

    def _get_participants(self, patient):
        from registry.patients.models import ParentGuardian
        participants = ParentGuardian.objects.filter(patient=patient)
        return ",".join(["%s %s" % (pg.first_name, pg.last_name) for pg in participants])

    def _send_email(self):
        from rdrf.services.io.notifications.email_notification import process_notification
        from rdrf.events.events import EventType
        from registry.patients.models import Patient
        from registry.patients.models import ParentGuardian

        patient = Patient.objects.get(id=self.patient_id)
        try:
            parent = ParentGuardian.objects.get(patient=patient)
            participant_name = "%s %s" % (parent.first_name, parent.last_name)
        except ParentGuardian.DoesNotExist:
            participant_name = "No parent"

        patient_name = "%s %s" % (patient.given_names, patient.family_name)
        if self.clinician_other.speciality:
            speciality = self.clinician_other.speciality.name
        else:
            speciality = "Unspecified"

        template_data = {"speciality": speciality,
                         "clinician_last_name": self.clinician_other.clinician_last_name,
                         "participant_name": participant_name,
                         "clinician_email": self.clinician_other.clinician_email,
                         "patient_name": patient_name,
                         "registration_link": self._construct_registration_link()}

        process_notification(self.registry.code,
                             EventType.CLINICIAN_SIGNUP_REQUEST,
                             template_data)

    def _construct_registration_link(self):
        """
        Return a link which will be sent to a clinician to activate ( become a user)
        """
        from rdrf.helpers.utils import get_site

        site_url = get_site()
        return site_url + reverse("registration_register", args=(self.registry.code,)) + "?t=%s" % self.token

    @staticmethod
    def create(registry_model, patient_model, clinician_other, clinician_email):
        csr = ClinicianSignupRequest(registry=registry_model,
                                     patient_id=patient_model.pk,
                                     clinician_other=clinician_other,
                                     clinician_email=clinician_email)
        csr.save()
        return csr
