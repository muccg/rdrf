from django.core.mail import send_mail
from rdrf.models import EmailNotification


class RdrfEmail(object):

    def __init__(self, reg_code, description):
        self.recipient = None
        self.subject = None
        self.body = None

        self.reg_code = reg_code
        self.description = description
        

    def send(self):
        self._get_email_notification()
        send_mail(self.subject, self.body, 'no-reply@rdrf.com.au', [self.recipient])
        
    def _get_email_notification(self):
        try:
            email_note = EmailNotification.objects.get(registry__code="fkrp", description="other-clinician")
            self.recipient = email_note.recipient
            self.subject = email_note.subject
            self.body = email_note.body
        except EmailNotification.DoesNotExist:
            pass