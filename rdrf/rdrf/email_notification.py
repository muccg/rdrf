from django.core.mail import send_mail
from rdrf.models import EmailNotification, EmailTemplate, EmailNotificationHistory
from registry.groups.models import CustomUser
from django.template import Context, Template

import json
import logging

logger = logging.getLogger("registry_log")


class RdrfEmailException(Exception):
    pass


class RdrfEmail(object):

    _DEFAULT_LANGUAGE = "en"

    def __init__(self, reg_code=None, description=None, language="en", email_notification=None):
        self.email_from = None
        self.recipient = []
        self.email_templates = []
        self.language = language
        self.template_data = {}

        self.reg_code = reg_code
        self.description = description
        
        self.email_notification = email_notification

    def send(self):
        try:
            self._get_email_notification()
            email_subject, email_body = self._get_email_template()
            
            send_mail(email_subject, email_body, self.email_from, self.recipient)
            logger.info("Sent email %s" % self.description)
            
            self._save_notification_record()
            logger.info("Email %s saved in history table" % self.description)
        except RdrfEmailException:
            logger.warning("No notification available for %s (%s)" % (self.reg_code, self.description))
        except Exception as e:
            logger.error("Email has failed to send - %s" % e)

    def _get_email_notification(self):
        try:
            if self.email_notification:
                email_note = self.email_notification
            else:
                email_note = EmailNotification.objects.get(registry__code=self.reg_code, description=self.description)
            self.email_notification = email_note
            self.email_from = email_note.email_from
            try:
                self.email_templates = email_note.email_templates.get(language=self.language)
            except EmailTemplate.DoesNotExist:
                self.email_templates = email_note.email_templates.get(language=self._DEFAULT_LANGUAGE)
            
            if email_note.recipient:
                recipient = self._get_recipient_template(email_note.recipient)
                self.recipient.append(recipient)
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

    def _get_recipient_template(self, recipient):
        context = Context(self.template_data)
        recipient_template = Template(recipient)
        
        return recipient_template.render(context)
    
    def _get_email_template(self):
        email_template = self.email_templates
        context = Context(self.template_data)
        
        template_subject = Template(email_template.subject)
        template_body = Template(email_template.body)
        
        template_subject = template_subject.render(context)
        template_body = template_body.render(context)
        
        return template_subject, template_body


    def _save_notification_record(self):
        _template_data = {}
        
        for key, value in self.template_data.iteritems():
            if value:
                _template_data[key] = {
                    "app": value._meta.app_label,
                    "model": value.__class__.__name__,
                    "id": value.id
                }
    
        enh = EmailNotificationHistory(
            language=self.language,
            email_notification=self.email_notification,
            template_data=json.dumps(_template_data)
        )
        enh.save()

    def append(self, key, obj):
        self.template_data[key] = obj
        return self

    def process_notification(reg_code=None, description=None, language="en", template_data = {}):
        notes = EmailNotification.objects.filter(registry__code=reg_code, description=description)
        for note in notes:
            email = RdrfEmail(language=language, email_notification=note)
            email.template_data = template_data
            email.send()
