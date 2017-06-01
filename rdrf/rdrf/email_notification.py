from django.core.mail import send_mail
from rdrf.models import EmailNotification, EmailTemplate, EmailNotificationHistory
from registry.groups.models import CustomUser
from django.template import Context, Template

import json
import logging

logger = logging.getLogger(__name__)

class RdrfEmailException(Exception):
    pass


class RdrfEmail(object):

    _DEFAULT_LANGUAGE = "en"

    def __init__(self, reg_code=None, description=None, email_notification=None, language=None):
        self.email_from = None
        self.recipients = []
        self.email_templates = []
        self.template_data = {}

        self.reg_code = reg_code
        self.description = description
        self.language = language # used to only send to subset of languages by EmailNotificationHistory resend

        if email_notification:
            self.email_notification = email_notification
            self.reg_code = self.email_notification.registry.code
            self.description = self.email_notification.description
            
        else:
            self.email_notification = self._get_email_notification()
            

    def send(self):
        try:
            notification_record_saved = []
            recipients = self._get_recipients()
            if len(recipients) == 0:
                # If the recipient template does not evaluate to a valid email address this will be
                # true
                return
            for recipient in self._get_recipients():
                language = self._get_preferred_language(recipient)
                if self.language and self.language != language:
                    # skip recipients with diff language
                    # this is used in resend when we resend per language template
                    continue
                    
                email_subject, email_body = self._get_email_subject_and_body(language)
                logger.debug("email_subject = %s" % email_subject)
                logger.debug("email_body = %s" % email_body)
                send_mail(email_subject, email_body, self.email_notification.email_from, [recipient], html_message=email_body)
                if language not in notification_record_saved: 
                    self._save_notification_record(language)
                    notification_record_saved.append(language)
            logger.info("Sent email(s) %s" % self.description)
            logger.info("Email %s saved in history table" % self.description)
        except RdrfEmailException as rdrfex:
            logger.debug("RdrfEmailException: %s" % rdrfex)
            logger.warning("No notification available for %s (%s)" % (self.reg_code, self.description))
        except Exception as e:
            logger.exception("Email has failed to send")


    def _get_preferred_language(self, email_address):
        user_model = self._get_user_from_email(email_address)
        return user_model.preferred_language

    def _get_user_from_email(self, email_address):
        try:
            return CustomUser.objects.get(email=email_address)
        except CustomUser.DoesNotExist:
            raise RdrfEmailException("No user with email address %s" % email_address)
        except CustomUser.MultipleObjectsReturned:
            raise RdrfEmailException("More than one user with email address %s" % email_address)

    def _get_recipients(self):
        recipients = []
        if self.email_notification.recipient:
            recipient = self._get_recipient_template(self.email_notification.recipient)
            recipients.append(recipient)
        if self.email_notification.group_recipient:
            group_emails = self._get_group_emails(self.email_notification.group_recipient)
            recipients.extend(group_emails)

        # NB If a patient registers as a patient ( not a parent)
        # and a parent template is registered against the account verified
        # event , the recipient template will evaulate to an empty string ..
        
        return [r for r in recipients  if self._valid_email(r)]

    def _valid_email(self, s):
        return "@" in s
    
    def _get_email_subject_and_body(self, language):
        try:
            email_template = self.email_notification.email_templates.get(language=language)
        except EmailTemplate.DoesNotExist:
            try:
                email_template = self.email_notification.email_templates.get(language=self._DEFAULT_LANGUAGE)
            except EmailTemplate.DoesNotExist:
                raise RdrfEmailException("Can't find any email templates for Email notification %s" % self.email_notification.id)

        context = Context(self.template_data)

        template_subject = Template(email_template.subject)
        template_body = Template(email_template.body)

        template_subject = template_subject.render(context)
        template_body = template_body.render(context)

        return template_subject, template_body

    def _get_email_notification(self):
        try:
            return EmailNotification.objects.get(registry__code=self.reg_code, description=self.description)
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

    def _save_notification_record(self, language):
        _template_data = {}

        for key, value in self.template_data.items():
            if value:
                _template_data[key] = {
                    "app": value._meta.app_label,
                    "model": value.__class__.__name__,
                    "id": value.id
                }

        enh = EmailNotificationHistory(
            language=language,
            email_notification=self.email_notification,
            template_data=json.dumps(_template_data)
        )
        enh.save()

    def append(self, key, obj):
        self.template_data[key] = obj
        return self


def process_notification(reg_code=None, description=None, template_data={}):
    logger.debug("process_notification %s %s %s" % (reg_code,
                                                    description,
                                                    template_data))
    
    notes = EmailNotification.objects.filter(registry__code=reg_code, description=description)
    for note in notes:
        if note.disabled:
            logger.warning("Email %s disabled" % note)

        logger.info("Sending email %s" % note)
        email = RdrfEmail(email_notification=note)
        email.template_data = template_data
        email.send()
