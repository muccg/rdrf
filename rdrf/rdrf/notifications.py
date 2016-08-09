import logging

from django.utils.translation import ugettext as _

from rdrf.utils import get_user
from django.conf import settings

logger = logging.getLogger(__name__)


class NotificationError(Exception):
    pass


class Notifier(object):

    def send_system_notification(self, from_user_name, to_username, message, link=""):
        from rdrf.models import Notification
        try:
            notification = Notification()
            notification.from_username = from_user_name
            notification.to_username = to_username
            notification.message = message
            notification.link = link
            notification.save()
        except Exception as ex:
            logger.error(
                _("Could not create notification for %(from_username)s to %(to_username)s with message %(message)s and link '%(link)s': %(ex)s") % {
                    "from_username": from_user_name,
                    "to_username": to_username,
                    "message": message,
                    "link": link,
                    "ex": ex})
            raise NotificationError(_("could not create notification"))

    def send_email(
            self,
            to_email,
            subject,
            body,
            message_type="System Email",
            from_email=settings.DEFAULT_FROM_EMAIL):
        try:
            from django.core.mail import send_mail
            send_mail(subject, body, from_email,
                      [to_email], fail_silently=False)

            logger.info(
                "Notification Email: %s from %s to %s with subject %s sent OK" %
                (message_type, from_email, to_email, subject))
            logger.debug("Email body =\n%s" % body)
        except Exception as ex:
            logger.error(
                "Notification Email: %s from %s to %s with subject %s FAILED: %s" %
                (message_type, from_email, to_email, subject, ex))
            logger.error("Email body =\n%s" % body)
            raise NotificationError("email failed")

    def send_email_to_username(self, username, subject, body, message_type="System Email",
                               from_email=settings.DEFAULT_FROM_EMAIL):
        to_user = get_user(username)
        if not to_user:
            raise NotificationError("Cannot send email to %s" % username)
        else:
            self.send_email(to_user.email, subject, body, message_type, from_email)
