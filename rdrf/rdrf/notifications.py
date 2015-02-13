from django.core.exceptions import ImproperlyConfigured
from django.db.models import get_app
import logging
from rdrf.utils import get_user, get_users


logger = logging.getLogger("registry_log")


class NotificationChannel:
    EMAIL = "email"
    SYSTEM = "system"
    SMS = "sms"


class Notifier(object):
    def send_system_notification(self, from_user_name, to_username, message, link=""):
        from rdrf.models import Notification
        notification = Notification()
        notification.from_username = from_user_name
        notification.to_username = to_username
        notification.message = message
        notification.save()
