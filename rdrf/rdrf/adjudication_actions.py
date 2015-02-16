from rdrf.notifications import Notifier


class AdjudicationAction(object):
    def __init__(self, adjudication):
        self.adjudication = adjudication
        self.notifier = Notifier()

    def run(self):
        self._send_notification()
        self._send_email()

    def _send_notification(self):
        message = self.adjudication.decision.summary
        self.notifier.send_system_notification(self.adjudication.definition.adjudicator_username,
                                               self.adjudication.requesting_username,
                                               message)

    def _send_email(self):
        from registry.patients.models import Patient
        email_subject = "An Adjudication you requested has been completed"
        email_body = """
            Dear %s user %s,
            You request for adjudication has been decided by user %s.
            The result is:

            %s

            """ % (self.adjudication.definition.registry,
                   self.adjudication.requesting_username,
                   self.adjudication.definition.adjudicator_username,
                   self.adjudication.decision.summary)

        self.notifier.send_email_to_username(self.adjudication.requesting_username,
                                             email_subject,
                                             email_body)

