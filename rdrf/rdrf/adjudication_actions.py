from rdrf.notifications import Notifier
import logging

logger = logging.getLogger("registry_log")


class AdjudicationAction(object):

    def __init__(self, adjudication):
        self.adjudication = adjudication
        self.notifier = Notifier()
        self.system_notify_failed = False
        self.email_notify_failed = False

    def run(self, request):
        try:
            self._send_notification()
        except Exception, ex:
            logger.error("Could not send system notification for %s: %s" % (self.adjudication, ex))
            self.system_notify_failed = True

        try:
            self._send_email(request)
        except Exception, ex:
            logger.error("could not send email notification for %s back to requestor: %s" % (self.adjudication, ex))
            self.email_notify_failed = True

    def _send_notification(self):
        message = self.adjudication.decision.summary
        self.notifier.send_system_notification(self.adjudication.definition.adjudicator_username,
                                               self.adjudication.requesting_username,
                                               message)

    def _send_email(self, request):
        from django.core.urlresolvers import reverse
        from registry.patients.models import Patient
        from rdrf.utils import get_full_link
        email_subject = "An Adjudication you requested has been completed"
        patient_id = self.adjudication.patient_id
        patient = Patient.objects.get(pk=patient_id)
        patient_link = get_full_link(request,
                                     reverse('admin:patients_patient_change', args=(patient_id,)),
                                     login_link=True)
        email_body = """
            Dear %s user %s,
            You request for adjudication %s of %s has been decided by user %s.
            The result is:

            %s

            Visit %s to update the patient.

            """ % (self.adjudication.definition.registry,
                   self.adjudication.requesting_username,
                   self.adjudication.definition.display_name,
                   patient,
                   self.adjudication.definition.adjudicator_username,
                   self.adjudication.decision.summary,
                   patient_link)

        self.notifier.send_email_to_username(self.adjudication.requesting_username,
                                             email_subject,
                                             email_body)
