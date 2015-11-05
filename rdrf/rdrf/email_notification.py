from django.core.mail import send_mail
from rdrf.models import EmailNotification
from registry.groups.models import CustomUser

import logging

logger = logging.getLogger("registry_log")


class RdrfEmailException(Exception):
    pass


class RdrfEmail(object):

    def __init__(self, reg_code, description):
        self.email_from = None
        self.recipient = []
        self.subject = None
        self.body = None

        self.reg_code = reg_code
        self.description = description

    def send(self):
        try:
            self._get_email_notification()
            send_mail(self.subject, self.body, self.email_from, self.recipient)
            logger.info("Sent email %s" % self.description)
        except RdrfEmailException:
            logger.warning("No notification available for %s (%s)" % (self.reg_code, self.description))
        except Exception:
            logger.error("Email has failed to send")

    def _get_email_notification(self):
        try:
            email_note = EmailNotification.objects.get(registry__code=self.reg_code, description=self.description)
            self.email_from = email_note.email_from
            self.subject = email_note.subject
            self.body = email_note.body
            
            if email_note.recipient:
                self.recipient.append(email_note.recipient)
            if email_note.group_recipient:
                self.recipient = self.recipient + self._get_group_emails(email_note.group_recipient)
            
        except EmailNotification.DoesNotExist:
            raise RdrfEmailException()

    def _get_group_emails(self, group):
        user_emails = []
        users = CustomUser.objects.filter(groups__in=[group])
        
        for user in users:
           user_emails.append(user.email)
        
        return user_emails
