from django.core.exceptions import ImproperlyConfigured
from django.db.models import get_app
import logging
from rdrf.utils import get_user, get_users
from django.conf import settings

logger = logging.getLogger("registry_log")

class Notifier(object):
    def send_system_notification(self, from_user_name, to_username, message, link=""):
        from rdrf.models import Notification
        notification = Notification()
        notification.from_username = from_user_name
        notification.to_username = to_username
        notification.message = message
        notification.link = link
        notification.save()

    def send_email(self, to_email, subject, body, message_type="System Email", from_email=settings.DEFAULT_FROM_EMAIL):
        try:
            from django.core.mail import send_mail
            send_mail(subject, body, from_email,
                      [to_email], fail_silently=False)
            logger.info("Notification Email: %s from %s to %s with subject %s sent OK" % (message_type,
                                                                                          from_email,
                                                                                          to_email,
                                                                                          subject))
        except Exception, ex:
            logger.error("Notification Email: %s from %s to %s with subject %s FAILED: %s" % (message_type,
                                                                                              from_email,
                                                                                              to_email,
                                                                                              subject,
                                                                                              ex))
