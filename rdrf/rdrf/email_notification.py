from django.core.mail import send_mail
from rdrf.models import EmailNotification, EmailTemplate
from registry.groups.models import CustomUser
from django.template import Context, Template

import logging

logger = logging.getLogger("registry_log")


class RdrfEmailException(Exception):
    pass


class RdrfEmail(object):

    def __init__(self, reg_code, description, language="en"):
        self.email_from = None
        self.recipient = []
        self.email_templates = []
        self.language = language
        self.template_data = {}

        self.reg_code = reg_code
        self.description = description

    def send(self):
        try:
            self._get_email_notification()
            email_subject, email_body = self._get_email_template()
            send_mail(email_subject, email_body, self.email_from, self.recipient)
            logger.info("Sent email %s" % self.description)
        except RdrfEmailException:
            logger.warning("No notification available for %s (%s)" % (self.reg_code, self.description))
        except Exception as e:
            logger.error("Email has failed to send - %s" % e)

    def _get_email_notification(self):
        try:
            email_note = EmailNotification.objects.get(registry__code=self.reg_code, description=self.description)
            self.email_from = email_note.email_from
            self.email_templates = email_note.email_templates.get(language=self.language)
            
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

    def _get_email_template(self):
        email_template = self.email_templates
        context = Context(self.template_data)
        
        template_subject = Template(email_template.subject)
        template_body = Template(email_template.body)
        
        template_subject = template_subject.render(context)
        template_body = template_body.render(context)
        
        return template_subject, template_body

    def append(self, key, obj):
        self.template_data[key] = obj
        return self