from django.db import models
from rdrf.models.definition.models import Registry
from registry.groups.models import CustomUser
from datetime import datetime
from rdrf.helpers.utils import generate_token
from django.core.urlresolvers import reverse

import logging

logger = logging.getLogger(__name__)

class ClinicianSignupRequest(models.Model):
    STATES = (("emailed", "Emailed"),      # clinician emailed
              ("signed-up", "Signed Up"),  # the clinician accepted the request and a user object was created
              ("created", "Created"),      # request created but nothing sent yet
              ("error", "Error"),          # error
              ("rejected", "Rejected"))    # the clinician received the request but rejected it
    
    registry = models.ForeignKey(Registry)
    patient_id = models.IntegerField()   # the patient id whose clinician it is ( had import issues with Patient)
    clinician_email = models.CharField(max_length=80)
    state = models.CharField(max_length=80, choices=STATES, default="created")
    token = models.CharField(max_length=80, default=generate_token, unique=True)
    clinician_other = models.ForeignKey("patients.ClinicianOther")  # this is the model the parent creates with data about the clinician`1
    clinician = models.ForeignKey(CustomUser, blank=True, null=True)
    emailed_date = models.DateTimeField(null=True)
    signup_date = models.DateTimeField(null=True)
    speciality = models.CharField(max_length=80, blank=True, null=True)

    def send_request(self):
        self._send_email()
        self.state = "emailed"
        self.emailed_date = datetime.now()
        self.save()

    def _send_email(self):
        from rdrf.services.io.notifications.email_notification import process_notification
        from rdrf.events.events import EventType
        from registry.patients.models import Patient
        from registry.patients.models import ParentGuardian
        self.speciality = "Brain Surgeon"
        patient = Patient.objects.get(id=self.patient_id)
        parent = ParentGuardian.objects.get(patient=patient)
        participant_name = "%s %s" % (parent.first_name, parent.last_name)
        patient_name = "%s" % patient

        template_data = {"speciality": self.speciality,
                         "clinician_last_name": self.clinician_other.clinician_name,
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
        site_url = "http://localhost:8000"
        return site_url + reverse("registration_register", args=(self.registry.code,)) + "?t=%s" % self.token

    @staticmethod
    def create(registry_model, patient_model, clinician_other, clinician_email):
        csr = ClinicianSignupRequest(registry=registry_model,
                                     patient_id=patient_model.pk,
                                     clinician_other=clinician_other,
                                     clinician_email=clinician_email)
        csr.save()
        logger.debug("created ClinicianSignUpRequest OK")
        return csr
